"""
Real identity-provider connectors for LDAP, OIDC, and SAML.

Each connector exposes two operations:
  • test_connection(config)  → {"status": "ok"|"error", "message": str}
  • fetch_users(config)      → list[{"email": str, "full_name": str}]
"""

import asyncio
import logging
import ssl
import xml.etree.ElementTree as ET
from typing import Any

import httpx

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  LDAP / Active Directory  (uses ldap3 — synchronous, run in thread)
# ═══════════════════════════════════════════════════════════════════════════════

def _ldap_connect(cfg: dict[str, Any]):
    """Return a bound ldap3 Connection or raise."""
    import ldap3
    from ldap3 import Server, Connection, ALL, SUBTREE, Tls  # noqa: F811

    server_url: str = cfg.get("server_url", "")
    use_ssl: bool = cfg.get("use_ssl", False)
    bind_dn: str = cfg.get("bind_dn", "")
    bind_password: str = cfg.get("bind_password", "")

    if not server_url:
        raise ValueError("server_url is required")

    tls_ctx = None
    if use_ssl:
        tls_ctx = Tls(validate=ssl.CERT_NONE)  # allow self-signed in corp envs

    server = Server(server_url, use_ssl=use_ssl, tls=tls_ctx, get_info=ALL, connect_timeout=10)
    conn = Connection(server, user=bind_dn or None, password=bind_password or None,
                      auto_bind=True, read_only=True, receive_timeout=15)
    return conn


def _ldap_search_users(cfg: dict[str, Any]) -> list[dict[str, str]]:
    """Synchronous: bind → search → return user dicts."""
    import ldap3

    conn = _ldap_connect(cfg)
    try:
        search_base = cfg.get("user_search_base") or cfg.get("base_dn", "")
        search_filter = cfg.get("user_search_filter", "(objectClass=person)")
        email_attr = cfg.get("email_attribute", "mail")
        name_attr = cfg.get("name_attribute", "displayName")

        if not search_base:
            raise ValueError("base_dn or user_search_base is required")

        conn.search(
            search_base=search_base,
            search_filter=search_filter,
            search_scope=ldap3.SUBTREE,
            attributes=[email_attr, name_attr, "sAMAccountName", "cn"],
            size_limit=1000,
        )

        users: list[dict[str, str]] = []
        for entry in conn.entries:
            email = str(entry[email_attr]) if email_attr in entry and entry[email_attr].value else None
            name = str(entry[name_attr]) if name_attr in entry and entry[name_attr].value else ""

            # Fallback: derive email from sAMAccountName + domain
            if not email:
                sam = str(entry["sAMAccountName"]) if "sAMAccountName" in entry and entry["sAMAccountName"].value else None
                if sam:
                    domain = _domain_from_base_dn(cfg.get("base_dn", ""))
                    email = f"{sam}@{domain}"
            if not name:
                name = str(entry["cn"]) if "cn" in entry and entry["cn"].value else ""

            if email and "@" in email:
                users.append({"email": email.lower().strip(), "full_name": name.strip()})

        return users
    finally:
        conn.unbind()


def _domain_from_base_dn(base_dn: str) -> str:
    parts = [p.split("=")[1] for p in base_dn.split(",") if p.strip().lower().startswith("dc=")]
    return ".".join(parts) if parts else "company.com"


async def ldap_test_connection(cfg: dict[str, Any]) -> dict[str, str]:
    try:
        conn = await asyncio.to_thread(_ldap_connect, cfg)
        info = conn.server.info
        conn.unbind()
        server_name = info.other.get("dnsHostName", [cfg.get("server_url", "")])[0] if info and hasattr(info, "other") else cfg.get("server_url", "")
        return {"status": "ok", "message": f"Successfully bound to {server_name}. Server is reachable."}
    except Exception as e:
        log.warning("LDAP test failed: %s", e)
        return {"status": "error", "message": f"LDAP connection failed: {e}"}


async def ldap_fetch_users(cfg: dict[str, Any]) -> list[dict[str, str]]:
    return await asyncio.to_thread(_ldap_search_users, cfg)


# ═══════════════════════════════════════════════════════════════════════════════
#  OIDC / SSO  (uses httpx — async native)
# ═══════════════════════════════════════════════════════════════════════════════

async def _oidc_discover(issuer_url: str) -> dict[str, Any]:
    """Fetch the OpenID Connect discovery document."""
    url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def _oidc_client_credentials_token(cfg: dict[str, Any]) -> str | None:
    """Get an access token via client_credentials grant (for admin/SCIM APIs)."""
    token_endpoint = cfg.get("token_endpoint", "")
    if not token_endpoint:
        disco = await _oidc_discover(cfg["issuer_url"])
        token_endpoint = disco.get("token_endpoint", "")
    if not token_endpoint:
        return None

    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        resp = await client.post(token_endpoint, data={
            "grant_type": "client_credentials",
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "scope": cfg.get("scopes", "openid email profile"),
        })
        resp.raise_for_status()
        return resp.json().get("access_token")


async def _oidc_fetch_users_scim(cfg: dict[str, Any], token: str) -> list[dict[str, str]]:
    """Fetch users via the SCIM /Users endpoint (Azure AD, Okta, etc.)."""
    scim_endpoint = cfg.get("scim_endpoint", "")
    if not scim_endpoint:
        # Common convention: {issuer}/scim/v2/Users
        scim_endpoint = cfg["issuer_url"].rstrip("/") + "/scim/v2/Users"

    users: list[dict[str, str]] = []
    email_claim = cfg.get("email_claim", "email")
    name_claim = cfg.get("name_claim", "name")
    next_url: str | None = scim_endpoint + "?count=100"

    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        while next_url:
            resp = await client.get(next_url, headers={"Authorization": f"Bearer {token}"})
            resp.raise_for_status()
            data = resp.json()

            for resource in data.get("Resources", []):
                email = _extract_scim_email(resource, email_claim)
                name = _extract_scim_name(resource, name_claim)
                if email and "@" in email:
                    users.append({"email": email.lower().strip(), "full_name": name.strip()})

            # Pagination
            start = data.get("startIndex", 1)
            per_page = data.get("itemsPerPage", 100)
            total = data.get("totalResults", 0)
            if start + per_page <= total:
                next_url = f"{scim_endpoint}?startIndex={start + per_page}&count=100"
            else:
                next_url = None

    return users


async def _oidc_fetch_users_userinfo(cfg: dict[str, Any], token: str) -> list[dict[str, str]]:
    """
    Fallback: some providers expose a users-list endpoint or management API.
    If SCIM is unavailable we try common patterns.
    """
    # Try Azure AD Graph / Microsoft Graph
    issuer = cfg.get("issuer_url", "")
    if "login.microsoftonline.com" in issuer or "sts.windows.net" in issuer:
        return await _fetch_azure_ad_users(cfg, token)

    # Try Okta /api/v1/users
    if ".okta.com" in issuer:
        return await _fetch_okta_users(cfg, token)

    # Generic — return empty with a note
    return []


async def _fetch_azure_ad_users(cfg: dict[str, Any], token: str) -> list[dict[str, str]]:
    """Microsoft Graph /users endpoint."""
    users: list[dict[str, str]] = []
    url: str | None = "https://graph.microsoft.com/v1.0/users?$top=999&$select=mail,displayName,userPrincipalName"
    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        while url:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            resp.raise_for_status()
            data = resp.json()
            for u in data.get("value", []):
                email = u.get("mail") or u.get("userPrincipalName", "")
                name = u.get("displayName", "")
                if email and "@" in email:
                    users.append({"email": email.lower().strip(), "full_name": name.strip()})
            url = data.get("@odata.nextLink")
    return users


async def _fetch_okta_users(cfg: dict[str, Any], token: str) -> list[dict[str, str]]:
    """Okta /api/v1/users endpoint."""
    issuer = cfg.get("issuer_url", "").rstrip("/")
    base = issuer.split("/oauth2")[0] if "/oauth2" in issuer else issuer
    users: list[dict[str, str]] = []
    url: str | None = f"{base}/api/v1/users?limit=200"
    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        while url:
            resp = await client.get(url, headers={"Authorization": f"SSWS {token}"})
            resp.raise_for_status()
            for u in resp.json():
                profile = u.get("profile", {})
                email = profile.get("email", "")
                name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
                if email:
                    users.append({"email": email.lower().strip(), "full_name": name})
            # Okta pagination via Link header
            link_header = resp.headers.get("Link", "")
            url = None
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip().strip("<>")
    return users


def _extract_scim_email(resource: dict, claim: str) -> str:
    """Extract email from a SCIM resource."""
    # Direct claim
    if claim in resource:
        return str(resource[claim])
    # SCIM emails array
    for em in resource.get("emails", []):
        if isinstance(em, dict) and em.get("primary"):
            return em.get("value", "")
    for em in resource.get("emails", []):
        if isinstance(em, dict):
            return em.get("value", "")
    return resource.get("userName", "")


def _extract_scim_name(resource: dict, claim: str) -> str:
    """Extract display name from a SCIM resource."""
    if claim in resource and isinstance(resource[claim], str):
        return resource[claim]
    if "displayName" in resource:
        return str(resource["displayName"])
    name_obj = resource.get("name", {})
    if isinstance(name_obj, dict):
        given = name_obj.get("givenName", "")
        family = name_obj.get("familyName", "")
        return f"{given} {family}".strip()
    return resource.get("userName", "")


async def oidc_test_connection(cfg: dict[str, Any]) -> dict[str, str]:
    try:
        issuer = cfg.get("issuer_url", "")
        if not issuer:
            return {"status": "error", "message": "issuer_url is required"}
        disco = await _oidc_discover(issuer)
        endpoints = [k for k in ("authorization_endpoint", "token_endpoint", "userinfo_endpoint") if k in disco]
        # Try getting a token if client credentials are provided
        token_msg = ""
        if cfg.get("client_id") and cfg.get("client_secret"):
            try:
                token = await _oidc_client_credentials_token(cfg)
                if token:
                    token_msg = " Client credentials token obtained successfully."
            except Exception:
                token_msg = " Warning: client_credentials grant failed — check scopes/permissions."
        return {
            "status": "ok",
            "message": f"OIDC discovery OK for {issuer}. Found endpoints: {', '.join(endpoints)}.{token_msg}",
        }
    except Exception as e:
        log.warning("OIDC test failed: %s", e)
        return {"status": "error", "message": f"OIDC connection failed: {e}"}


async def oidc_fetch_users(cfg: dict[str, Any]) -> list[dict[str, str]]:
    if not cfg.get("client_id") or not cfg.get("client_secret"):
        raise ValueError("client_id and client_secret are required for user import")

    token = await _oidc_client_credentials_token(cfg)
    if not token:
        raise ValueError("Could not obtain access token via client_credentials grant")

    # Try SCIM first
    try:
        users = await _oidc_fetch_users_scim(cfg, token)
        if users:
            return users
    except Exception as e:
        log.info("SCIM fetch failed, trying provider-specific API: %s", e)

    # Fallback to provider-specific APIs
    users = await _oidc_fetch_users_userinfo(cfg, token)
    if users:
        return users

    raise ValueError(
        "Could not fetch users. Ensure the client has SCIM or user-management API permissions. "
        "You can also provide a custom scim_endpoint in the config."
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  SAML 2.0  (metadata parsing via httpx + stdlib XML, import via SCIM)
# ═══════════════════════════════════════════════════════════════════════════════

_SAML_MD_NS = "urn:oasis:names:tc:SAML:2.0:metadata"
_SAML_DS_NS = "http://www.w3.org/2000/09/xmldsig#"


async def _saml_fetch_metadata(cfg: dict[str, Any]) -> dict[str, Any]:
    """Parse IdP metadata URL or inline XML to extract SSO URL + certificate."""
    metadata_url = cfg.get("metadata_url", "")
    metadata_xml = cfg.get("metadata_xml", "")

    if metadata_url:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(metadata_url)
            resp.raise_for_status()
            metadata_xml = resp.text

    if not metadata_xml:
        return {}

    root = ET.fromstring(metadata_xml)
    result: dict[str, Any] = {}

    # Entity ID
    result["entity_id"] = root.attrib.get("entityID", "")

    # SSO endpoints
    for sso in root.iter(f"{{{_SAML_MD_NS}}}SingleSignOnService"):
        binding = sso.attrib.get("Binding", "")
        if "HTTP-Redirect" in binding or "HTTP-POST" in binding:
            result.setdefault("sso_url", sso.attrib.get("Location", ""))

    # SLO endpoints
    for slo in root.iter(f"{{{_SAML_MD_NS}}}SingleLogoutService"):
        result.setdefault("slo_url", slo.attrib.get("Location", ""))

    # X.509 certificate
    for cert in root.iter(f"{{{_SAML_DS_NS}}}X509Certificate"):
        if cert.text:
            result["certificate"] = cert.text.strip()
            break

    return result


async def saml_test_connection(cfg: dict[str, Any]) -> dict[str, str]:
    try:
        sso_url = cfg.get("sso_url", "")
        metadata_url = cfg.get("metadata_url", "")

        if metadata_url:
            md = await _saml_fetch_metadata(cfg)
            if not md:
                return {"status": "error", "message": "Could not parse SAML metadata"}
            entity_id = md.get("entity_id", "unknown")
            has_sso = "sso_url" in md
            has_cert = "certificate" in md
            return {
                "status": "ok",
                "message": (
                    f"SAML metadata parsed. Entity ID: {entity_id}. "
                    f"SSO endpoint: {'found' if has_sso else 'missing'}. "
                    f"X.509 certificate: {'found' if has_cert else 'missing'}."
                ),
            }

        if sso_url:
            # Validate the SSO endpoint is reachable
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                resp = await client.head(sso_url)
            return {
                "status": "ok",
                "message": f"SAML SSO endpoint reachable at {sso_url} (HTTP {resp.status_code}).",
            }

        return {"status": "error", "message": "Provide either metadata_url or sso_url"}

    except Exception as e:
        log.warning("SAML test failed: %s", e)
        return {"status": "error", "message": f"SAML connection failed: {e}"}


async def saml_fetch_users(cfg: dict[str, Any]) -> list[dict[str, str]]:
    """
    SAML is an authentication protocol — it does not natively expose a user
    directory.  For bulk import we use the SCIM endpoint that most enterprise
    IdPs (Azure AD, Okta, OneLogin, etc.) expose alongside SAML.
    """
    scim_endpoint = cfg.get("scim_endpoint", "")
    scim_token = cfg.get("scim_token", "")
    if not scim_endpoint or not scim_token:
        raise ValueError(
            "SAML does not support user listing natively. "
            "Provide scim_endpoint and scim_token in the configuration to import users via SCIM. "
            "Most enterprise IdPs (Azure AD, Okta, OneLogin) support SCIM provisioning."
        )

    email_attr = cfg.get("email_attribute", "email")
    name_attr = cfg.get("name_attribute", "displayName")

    users: list[dict[str, str]] = []
    next_url: str | None = scim_endpoint.rstrip("/") + "/Users?count=100"

    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        while next_url:
            resp = await client.get(next_url, headers={"Authorization": f"Bearer {scim_token}"})
            resp.raise_for_status()
            data = resp.json()

            for resource in data.get("Resources", []):
                email = _extract_scim_email(resource, email_attr)
                name = _extract_scim_name(resource, name_attr)
                if email and "@" in email:
                    users.append({"email": email.lower().strip(), "full_name": name.strip()})

            start = data.get("startIndex", 1)
            per_page = data.get("itemsPerPage", 100)
            total = data.get("totalResults", 0)
            if start + per_page <= total:
                next_url = f"{scim_endpoint.rstrip('/')}/Users?startIndex={start + per_page}&count=100"
            else:
                next_url = None

    return users


# ═══════════════════════════════════════════════════════════════════════════════
#  Dispatcher (used by the API layer)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_provider(provider_type: str, config: dict[str, Any]) -> dict[str, str]:
    if provider_type == "ldap":
        return await ldap_test_connection(config)
    elif provider_type == "oidc":
        return await oidc_test_connection(config)
    elif provider_type == "saml":
        return await saml_test_connection(config)
    return {"status": "error", "message": f"Unknown provider type: {provider_type}"}


async def fetch_provider_users(provider_type: str, config: dict[str, Any]) -> list[dict[str, str]]:
    if provider_type == "ldap":
        return await ldap_fetch_users(config)
    elif provider_type == "oidc":
        return await oidc_fetch_users(config)
    elif provider_type == "saml":
        return await saml_fetch_users(config)
    raise ValueError(f"Unknown provider type: {provider_type}")

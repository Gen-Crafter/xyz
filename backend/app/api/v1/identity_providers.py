import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import require_admin
from app.models.db_models import IdentityProviderModel, UserModel

from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/identity-providers", tags=["Identity Providers"])


# ── Schemas ────────────────────────────────────────────────────────────────

class LdapConfig(BaseModel):
    server_url: str = ""          # ldap://ad.company.com:389
    use_ssl: bool = False
    base_dn: str = ""             # dc=company,dc=com
    bind_dn: str = ""             # cn=admin,dc=company,dc=com
    bind_password: str = ""
    user_search_base: str = ""    # ou=users,dc=company,dc=com
    user_search_filter: str = "(objectClass=person)"
    email_attribute: str = "mail"
    name_attribute: str = "displayName"
    group_search_base: str = ""
    admin_group_dn: str = ""      # cn=admins,ou=groups,dc=company,dc=com


class SamlConfig(BaseModel):
    entity_id: str = ""           # SP entity ID
    idp_entity_id: str = ""       # IdP entity ID
    metadata_url: str = ""        # IdP metadata URL (auto-discovers SSO, cert)
    sso_url: str = ""             # IdP SSO endpoint
    slo_url: str = ""             # IdP SLO endpoint
    certificate: str = ""         # X.509 cert (PEM)
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    email_attribute: str = "email"
    name_attribute: str = "displayName"
    sign_requests: bool = True
    want_assertions_signed: bool = True
    scim_endpoint: str = ""       # SCIM endpoint for bulk user import
    scim_token: str = ""          # Bearer token for SCIM API


class OidcConfig(BaseModel):
    issuer_url: str = ""          # https://accounts.google.com
    client_id: str = ""
    client_secret: str = ""
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    userinfo_endpoint: str = ""
    scopes: str = "openid email profile"
    email_claim: str = "email"
    name_claim: str = "name"
    redirect_uri: str = ""
    scim_endpoint: str = ""       # Optional: explicit SCIM endpoint for user import


class IdpCreate(BaseModel):
    name: str
    provider_type: str            # ldap | saml | oidc
    config: dict[str, Any] = {}


class IdpUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[dict[str, Any]] = None


class IdpResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    provider_type: str
    is_active: bool
    config: dict[str, Any]
    last_sync_at: Optional[datetime]
    last_sync_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ImportResult(BaseModel):
    total_found: int
    imported: int
    skipped: int
    errors: list[str]


def _to_response(m: IdentityProviderModel) -> IdpResponse:
    safe_config = dict(m.config) if m.config else {}
    for secret_key in ("bind_password", "client_secret", "certificate", "scim_token"):
        if secret_key in safe_config and safe_config[secret_key]:
            safe_config[secret_key] = "••••••••"
    return IdpResponse(
        id=str(m.id), tenant_id=str(m.tenant_id),
        name=m.name, provider_type=m.provider_type,
        is_active=m.is_active, config=safe_config,
        last_sync_at=m.last_sync_at, last_sync_count=m.last_sync_count,
        created_at=m.created_at, updated_at=m.updated_at,
    )


# ── CRUD ───────────────────────────────────────────────────────────────────

@router.get("", response_model=list[IdpResponse])
async def list_providers(
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IdentityProviderModel)
        .where(IdentityProviderModel.tenant_id == admin.tenant_id)
        .order_by(IdentityProviderModel.created_at.desc())
    )
    return [_to_response(m) for m in result.scalars().all()]


@router.post("", response_model=IdpResponse, status_code=201)
async def create_provider(
    body: IdpCreate,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.provider_type not in ("ldap", "saml", "oidc"):
        raise HTTPException(status_code=400, detail="provider_type must be ldap, saml, or oidc")

    m = IdentityProviderModel(
        tenant_id=admin.tenant_id,
        name=body.name,
        provider_type=body.provider_type,
        config=body.config,
        created_by=admin.id,
    )
    db.add(m)
    await db.flush()
    await db.refresh(m)
    return _to_response(m)


@router.patch("/{idp_id}", response_model=IdpResponse)
async def update_provider(
    idp_id: str,
    body: IdpUpdate,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IdentityProviderModel).where(IdentityProviderModel.id == uuid.UUID(idp_id))
    )
    m = result.scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Provider not found")
    if body.name is not None:
        m.name = body.name
    if body.is_active is not None:
        m.is_active = body.is_active
    if body.config is not None:
        existing = dict(m.config) if m.config else {}
        for k, v in body.config.items():
            if v != "••••••••":
                existing[k] = v
        m.config = existing
    await db.flush()
    await db.refresh(m)
    return _to_response(m)


@router.delete("/{idp_id}", status_code=204)
async def delete_provider(
    idp_id: str,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IdentityProviderModel).where(IdentityProviderModel.id == uuid.UUID(idp_id))
    )
    m = result.scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(m)
    await db.flush()


# ── Test Connection ────────────────────────────────────────────────────────

@router.post("/{idp_id}/test")
async def test_connection(
    idp_id: str,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IdentityProviderModel).where(IdentityProviderModel.id == uuid.UUID(idp_id))
    )
    m = result.scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Provider not found")

    from app.core.idp_connectors import test_provider
    return await test_provider(m.provider_type, m.config or {})


# ── Import / Sync Users ───────────────────────────────────────────────────

@router.post("/{idp_id}/import", response_model=ImportResult)
async def import_users(
    idp_id: str,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Import users from the configured identity provider.
    Uses real connectors: ldap3 for LDAP/AD, httpx for OIDC/SAML+SCIM.
    """
    result = await db.execute(
        select(IdentityProviderModel).where(IdentityProviderModel.id == uuid.UUID(idp_id))
    )
    m = result.scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Provider not found")

    from app.core.idp_connectors import fetch_provider_users

    try:
        fetched_users = await fetch_provider_users(m.provider_type, m.config or {})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch users from provider: {e}")

    imported = 0
    skipped = 0
    errors: list[str] = []
    default_password = pwd_ctx.hash("ChangeMe@123")

    for u in fetched_users:
        existing = await db.execute(
            select(UserModel).where(UserModel.email == u["email"])
        )
        if existing.scalars().first():
            skipped += 1
            continue
        try:
            new_user = UserModel(
                email=u["email"],
                full_name=u.get("full_name", ""),
                hashed_password=default_password,
                is_admin=False,
                tenant_id=admin.tenant_id,
            )
            db.add(new_user)
            await db.flush()
            imported += 1
        except Exception as e:
            errors.append(f"{u['email']}: {str(e)}")

    m.last_sync_at = datetime.now(timezone.utc)
    m.last_sync_count = imported
    await db.flush()

    return ImportResult(
        total_found=len(fetched_users),
        imported=imported,
        skipped=skipped,
        errors=errors,
    )

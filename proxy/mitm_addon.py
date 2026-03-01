"""
MITM Proxy Addon — module-level functions for mitmproxy 11.x compatibility.

Intercepts AI-bound HTTP traffic and routes it through the AI Governance
Proxy compliance pipeline before forwarding to the real server.

Usage:
  mitmdump -s mitm_addon.py --set api_url=http://api:8000
"""

import base64
import json
import re
import sys
import time

import httpx
from mitmproxy import http, ctx, tls, options

# ── Configuration ─────────────────────────────────────────────────────
API_URL = "http://api:8000"
_intercepted_count = 0
_blocked_count = 0
_redacted_count = 0
_LOG = "/tmp/mitm_addon.log"

AI_DOMAINS = {
    "api.openai.com",
    "chat.openai.com",
    "chatgpt.com",
    "api.anthropic.com",
    "claude.ai",
    "generativelanguage.googleapis.com",
    "api-inference.huggingface.co",
    "copilot.microsoft.com",
}

AI_PATH_PATTERNS = [
    re.compile(r"/v\d+/chat/completions"),
    re.compile(r"/v\d+/completions"),
    re.compile(r"/v\d+/messages"),
    re.compile(r"/v\d+/embeddings"),
    re.compile(r"/v\d+/models/.*/generate"),
]


def _log(msg: str):
    """Write to file + stderr for reliable logging inside mitmdump."""
    line = f"[AIGP] {msg}\n"
    try:
        with open(_LOG, "a") as f:
            f.write(line)
    except Exception:
        pass
    sys.stderr.write(line)
    sys.stderr.flush()


def _is_ai(flow: http.HTTPFlow) -> bool:
    host = flow.request.pretty_host
    if host in AI_DOMAINS:
        return True
    for pat in AI_PATH_PATTERNS:
        if pat.search(flow.request.path):
            return True
    return False


# ── mitmproxy lifecycle hooks (module-level) ──────────────────────────

def load(loader):
    loader.add_option("api_url", str, "http://api:8000", "AI Governance Proxy API URL")

    # Monkey-patch trigger_event to debug hook dispatch
    import functools
    mgr = ctx.master.addons
    _orig_trigger = mgr.trigger_event

    @functools.wraps(_orig_trigger)
    async def _patched_trigger(event):
        _log(f"trigger_event: {event.name} chain_len={len(mgr.chain)}")
        for i, addon in enumerate(mgr.chain):
            _log(f"  chain[{i}]: {type(addon).__name__} addons={hasattr(addon, 'addons')}")
        return await _orig_trigger(event)

    mgr.trigger_event = _patched_trigger
    _log("Patched trigger_event for debugging")


def configure(updated):
    global API_URL
    if "api_url" in updated:
        API_URL = ctx.options.api_url
        _log(f"API URL set to {API_URL}")


def running():
    _log("Addon running — hooks active")


def tls_clienthello(data: tls.ClientHelloData):
    """Only MITM AI domains; pass everything else through as-is."""
    sni = data.context.client.sni
    if sni and sni not in AI_DOMAINS:
        data.ignore_connection = True
    else:
        _log(f"TLS intercept: {sni}")


def http_connect(flow: http.HTTPFlow):
    _log(f"HTTP CONNECT: {flow.request.pretty_host}:{flow.request.port}")


def requestheaders(flow: http.HTTPFlow):
    _log(f"requestheaders: {flow.request.method} {flow.request.pretty_host}{flow.request.path}")


async def request(flow: http.HTTPFlow):
    """Intercept outbound requests to AI services."""
    global _intercepted_count, _blocked_count, _redacted_count

    if not _is_ai(flow):
        return

    _intercepted_count += 1
    host = flow.request.pretty_host
    path = flow.request.path
    source_ip = flow.client_conn.peername[0] if flow.client_conn.peername else "0.0.0.0"
    content_type = flow.request.headers.get("content-type", "")
    _log(f"Intercepted #{_intercepted_count}: {flow.request.method} {host}{path} from {source_ip}")

    # ── multipart / file uploads ──────────────────────────────────
    if "multipart/form-data" in content_type:
        await _handle_multipart(flow, host, path, source_ip)
        return

    # ── standard JSON payloads ────────────────────────────────────
    body = {}
    if flow.request.content:
        try:
            body = json.loads(flow.request.content.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {"raw": flow.request.content.decode("utf-8", errors="replace")[:2000]}

    payload = {
        "interception_id": f"MITM-{_intercepted_count}",
        "direction": "outbound",
        "source_ip": source_ip,
        "destination": host,
        "endpoint": path,
        "payload": body,
    }

    result = await _call_filter_api("/api/v1/filter/process", payload)
    if result is None:
        _log(f"Filter API returned None for #{_intercepted_count}, fail-open")
        return
    _apply_decision(flow, host, path, result)


async def response(flow: http.HTTPFlow):
    """Intercept AI responses and run full RAG+LLM compliance scan."""
    if not _is_ai(flow):
        return

    flow.response.headers["X-AI-Governance-Proxy"] = "active"

    # Parse the original request body (user prompt)
    request_body = {}
    if flow.request.content:
        try:
            request_body = json.loads(flow.request.content.decode("utf-8", errors="replace"))
        except Exception:
            request_body = {}

    # Parse the response body (AI output)
    response_body = {}
    if flow.response.content:
        try:
            response_body = json.loads(flow.response.content.decode("utf-8", errors="replace"))
        except Exception:
            response_body = {}

    # Convert to structured agent-request format for RAG+LLM scan
    agent_payload = _build_agent_request(flow, request_body, response_body)
    if agent_payload:
        scan_result = await _call_filter_api("/api/v1/agent-requests", agent_payload)
        if scan_result:
            status = scan_result.get("compliance_status", "CLEAN")
            violations = scan_result.get("violations", [])
            risk = scan_result.get("risk_score", 0)
            _log(f"[SCAN] {flow.request.pretty_host}: status={status} violations={len(violations)} risk={risk}")
            flow.response.headers["X-Governance-Status"] = status
            flow.response.headers["X-Governance-Risk"] = str(risk)
            flow.response.headers["X-Governance-Violations"] = str(len(violations))


# ── Build agent-request payload from raw traffic ─────────────────────

def _build_agent_request(flow: http.HTTPFlow, request_body: dict, response_body: dict) -> dict | None:
    """Convert raw intercepted AI traffic into structured agent-request format.

    Maps ChatGPT/Claude/etc API formats to the governance server's expected schema
    so the full RAG+LLM compliance pipeline can scan the content.
    """
    host = flow.request.pretty_host
    path = flow.request.path
    source_ip = flow.client_conn.peername[0] if flow.client_conn.peername else "unknown"

    # Extract user input from request
    user_input = _extract_user_input(request_body)
    if not user_input and not response_body:
        return None  # Nothing to scan

    # Extract AI response text
    ai_output = _extract_ai_output(response_body)

    # Build tool chain: treat the AI API call itself as a single "tool"
    tool_chain = [{
        "tool_name": f"{host}",
        "description": f"AI API call to {host}{path}",
        "sequence": 1,
        "input": {"prompt": user_input[:1000]} if user_input else {},
        "output": {"summary": ai_output[:1000]} if ai_output else {"summary": "No parseable output"},
        "reasoning": f"Outbound AI request intercepted by MITM proxy from {source_ip}",
        "duration_ms": int((flow.response.timestamp_end - flow.request.timestamp_start) * 1000) if flow.response.timestamp_end else 0,
        "status": "SUCCESS" if flow.response and flow.response.status_code == 200 else "FAILED",
    }]

    # Extract model name from request or response
    model = request_body.get("model", response_body.get("model", "unknown"))

    return {
        "request_id": f"MITM-{_intercepted_count}-{int(time.time())}",
        "title": f"Intercepted: {host}{path[:50]}",
        "source_app": f"mitm-{host}",
        "user_name": f"proxy-user@{source_ip}",
        "user_input": user_input[:2000] if user_input else "",
        "tool_chain": tool_chain,
        "final_output": {"summary": ai_output[:1000]} if ai_output else {"summary": "No output captured"},
        "metadata": {
            "model": model,
            "source_ip": source_ip,
            "destination": host,
            "endpoint": path,
            "intercepted_by": "mitm-proxy",
        },
    }


def _extract_user_input(body: dict) -> str:
    """Extract user prompt from various AI API request formats."""
    # OpenAI / ChatGPT format: {"messages": [{"role": "user", "content": "..."}]}
    messages = body.get("messages", [])
    if messages:
        user_msgs = [m.get("content", "") for m in messages
                     if isinstance(m, dict) and m.get("role") in ("user", "human")]
        if user_msgs:
            return "\n".join(str(m) for m in user_msgs if m)

    # Anthropic format: {"prompt": "..."}
    if body.get("prompt"):
        return str(body["prompt"])

    # Simple input field
    if body.get("input"):
        return str(body["input"])

    # Raw text in body
    if body.get("raw"):
        return str(body["raw"])

    return ""


def _extract_ai_output(body: dict) -> str:
    """Extract AI response text from various API response formats."""
    # OpenAI format: {"choices": [{"message": {"content": "..."}}]}
    choices = body.get("choices", [])
    if choices:
        parts = []
        for c in choices:
            msg = c.get("message", {})
            if msg.get("content"):
                parts.append(str(msg["content"]))
            # Function call outputs
            if msg.get("function_call"):
                parts.append(json.dumps(msg["function_call"]))
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    parts.append(json.dumps(tc))
        if parts:
            return "\n".join(parts)

    # Anthropic format: {"content": [{"text": "..."}]}
    content = body.get("content", [])
    if isinstance(content, list):
        texts = [c.get("text", "") for c in content if isinstance(c, dict)]
        if texts:
            return "\n".join(t for t in texts if t)

    # Simple text field
    if body.get("text"):
        return str(body["text"])

    # Completion format
    if body.get("completion"):
        return str(body["completion"])

    return ""


# ── Helper functions ──────────────────────────────────────────────────

async def _call_filter_api(endpoint: str, payload: dict) -> dict | None:
    # Agent-request scan uses RAG+LLM, needs longer timeout
    timeout = 180.0 if "agent-requests" in endpoint else 30.0
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{API_URL}{endpoint}", json=payload, timeout=timeout)
            result = resp.json()
            _log(f"Filter API → {endpoint}: decision={result.get('decision', 'N/A')}")
            return result
    except Exception as e:
        _log(f"Filter API FAILED ({endpoint}): {e}")
        return None


def _apply_decision(flow: http.HTTPFlow, host: str, path: str, result: dict):
    global _blocked_count, _redacted_count
    decision = result.get("decision", "ALLOW")
    justification = result.get("justification", "")
    _log(f"[{decision}] {host}{path} — {justification}")

    if decision == "BLOCK":
        _blocked_count += 1
        flow.response = http.Response.make(
            403,
            json.dumps({
                "error": "blocked_by_governance_proxy",
                "message": f"Request blocked by AI Governance Proxy: {justification}",
                "policies_triggered": result.get("policies_triggered", []),
                "interception_id": result.get("interception_id", ""),
            }).encode(),
            {"Content-Type": "application/json"},
        )
    elif decision == "REDACT":
        _redacted_count += 1
        redacted = result.get("redacted_payload")
        if redacted:
            flow.request.content = json.dumps(redacted).encode("utf-8")
            flow.request.headers["X-Governance-Redacted"] = "true"
        flow.request.headers["X-Governance-Action"] = "REDACT"
    elif decision == "AUDIT":
        flow.request.headers["X-Governance-Action"] = "AUDIT"
        flow.request.headers["X-Governance-Interception-ID"] = result.get("interception_id", "")
    else:
        flow.request.headers["X-Governance-Action"] = "ALLOW"


async def _handle_multipart(flow: http.HTTPFlow, host: str, path: str, source_ip: str):
    multipart = flow.request.multipart_form
    if not multipart:
        return

    worst_decision = "ALLOW"
    worst_justification = ""
    all_policies: list = []
    file_count = 0
    priority_map = {"BLOCK": 0, "REDACT": 1, "AUDIT": 2, "ALLOW": 3}

    for key, value in multipart.items():
        is_file = len(value) > 256 or key in ("file", "files", "attachment", "document", "image")
        if not is_file:
            try:
                text_val = value.decode("utf-8", errors="replace")
                if len(text_val) > 20:
                    payload = {
                        "interception_id": f"MITM-{_intercepted_count}-field-{key}",
                        "direction": "outbound",
                        "source_ip": source_ip,
                        "destination": host,
                        "endpoint": path,
                        "payload": {"messages": [{"role": "user", "content": text_val}]},
                    }
                    result = await _call_filter_api("/api/v1/filter/process", payload)
                    if result:
                        nd = result.get("decision", "ALLOW")
                        if priority_map.get(nd, 3) < priority_map.get(worst_decision, 3):
                            worst_decision = nd
                            worst_justification = result.get("justification", "")
                        all_policies = list(set(all_policies + result.get("policies_triggered", [])))
            except Exception:
                pass
            continue

        file_count += 1
        filename = key if "." in key else f"{key}.bin"
        _log(f"[FILE] Scanning: {filename} ({len(value)} bytes) → {host}{path}")

        file_payload = {
            "interception_id": f"MITM-FILE-{_intercepted_count}-{file_count}",
            "filename": filename,
            "content_base64": base64.b64encode(value).decode("ascii"),
            "content_type": "",
            "source_ip": source_ip,
            "destination": host,
            "endpoint": path,
        }
        result = await _call_filter_api("/api/v1/filter/process-file", file_payload)
        if result:
            nd = result.get("decision", "ALLOW")
            if priority_map.get(nd, 3) < priority_map.get(worst_decision, 3):
                worst_decision = nd
                worst_justification = result.get("justification", "")
            all_policies = list(set(all_policies + result.get("policies_triggered", [])))

    if worst_decision == "BLOCK":
        flow.response = http.Response.make(
            403,
            json.dumps({
                "error": "blocked_by_governance_proxy",
                "message": f"File upload blocked: {worst_justification}",
                "policies_triggered": all_policies,
            }).encode(),
            {"Content-Type": "application/json"},
        )
        _log(f"[BLOCK] File upload to {host}{path}")
    elif worst_decision == "REDACT":
        flow.request.headers["X-Governance-Action"] = "REDACT"
        flow.request.headers["X-Governance-File-Scanned"] = "true"
    else:
        flow.request.headers["X-Governance-Action"] = worst_decision
        flow.request.headers["X-Governance-File-Scanned"] = "true"

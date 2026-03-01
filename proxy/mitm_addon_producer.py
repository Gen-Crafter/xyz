"""
MITM Proxy Addon – intercepts ChatGPT (api.openai.com / chatgpt.com) traffic
and forwards request/response pairs to the governance API for storage.

Also sends structured agent-request payloads to the AI Governance Server
for RAG+LLM compliance scanning (PII, PHI, PCI-DSS, GDPR, HIPAA detection).
"""

import json
import time
import logging

import httpx
from mitmproxy import http, ctx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHATGPT_HOSTS = [
    "api.openai.com",
    "chatgpt.com",
    "chat.openai.com",
    "ab.chatgpt.com",
    "www.perplexity.ai",
    "perplexity.ai",
    "api.perplexity.ai",
    "gemini.google.com",
    "generativelanguage.googleapis.com",
    "chat.deepseek.com",
    "api.deepseek.com",
]

# Counter for unique request IDs
_intercepted_count = 0


class ChatGPTInterceptor:
    """Captures ChatGPT API traffic and sends it to the governance API."""

    def __init__(self):
        self.api_url: str = "http://api:8000"
        # ── Governance Server URL (VM1) for RAG+LLM compliance scanning ──
        self.governance_url: str = "http://api:8000"

    def load(self, loader):
        loader.add_option(
            name="api_url",
            typespec=str,
            default="http://api:8000",
            help="URL of the governance API to forward interceptions to",
        )
        loader.add_option(
            name="governance_url",
            typespec=str,
            default="http://api:8000",
            help="URL of the AI Governance Server for RAG+LLM compliance scanning",
        )

    def configure(self, updates):
        if "api_url" in updates:
            self.api_url = ctx.options.api_url
            logger.info("Governance API URL set to: %s", self.api_url)
        if "governance_url" in updates:
            self.governance_url = ctx.options.governance_url
            logger.info("Governance scan URL set to: %s", self.governance_url)

    def _is_chatgpt_traffic(self, host: str) -> bool:
        return any(host.endswith(h) for h in CHATGPT_HOSTS)

    def _safe_decode(self, raw: bytes, content_type: str | None = None) -> str | dict | None:
        if not raw:
            return None
        try:
            text = raw.decode("utf-8", errors="replace")
            if content_type and "json" in content_type:
                return json.loads(text)
            return text
        except (json.JSONDecodeError, UnicodeDecodeError):
            return raw.decode("utf-8", errors="replace")

    def response(self, flow: http.HTTPFlow):
        if not flow.request or not flow.response:
            return

        host = flow.request.pretty_host
        if not self._is_chatgpt_traffic(host):
            return

        req_content_type = flow.request.headers.get("content-type", "")
        res_content_type = flow.response.headers.get("content-type", "")

        payload = {
            "timestamp": time.time(),
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "host": host,
            "path": flow.request.path,
            "request_headers": dict(flow.request.headers),
            "request_body": self._safe_decode(flow.request.get_content(), req_content_type),
            "status_code": flow.response.status_code,
            "response_headers": dict(flow.response.headers),
            "response_body": self._safe_decode(flow.response.get_content(), res_content_type),
            "client_address": flow.client_conn.peername[0] if flow.client_conn.peername else None,
        }

        # Remove Authorization header value for safety (keep key to show it existed)
        if "authorization" in payload["request_headers"]:
            payload["request_headers"]["authorization"] = "[REDACTED]"
        if "Authorization" in payload["request_headers"]:
            payload["request_headers"]["Authorization"] = "[REDACTED]"

        logger.info(
            "Captured: %s %s -> %s",
            flow.request.method,
            flow.request.pretty_url,
            flow.response.status_code,
        )

        # ── 1) Forward raw intercept to local storage API ────────────
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    f"{self.api_url}/api/v1/intercepts",
                    json=payload,
                )
                if resp.status_code >= 400:
                    logger.error("API returned %s: %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.error("Failed to forward intercept to API: %s", exc)

        # ── 2) Send to Governance Server for RAG+LLM compliance scan ─
        self._send_to_governance(flow, payload)

    # ── Governance Server Integration ────────────────────────────────

    def _send_to_governance(self, flow: http.HTTPFlow, raw_payload: dict):
        """Convert intercepted traffic to structured agent-request format
        and send to the Governance Server for RAG+LLM compliance scanning."""
        global _intercepted_count
        _intercepted_count += 1

        host = raw_payload.get("host", "unknown")
        path = raw_payload.get("path", "/")
        source_ip = raw_payload.get("client_address", "unknown")
        request_body = raw_payload.get("request_body", {})
        response_body = raw_payload.get("response_body", {})

        # Ensure bodies are dicts for parsing
        if isinstance(request_body, str):
            try:
                request_body = json.loads(request_body)
            except (json.JSONDecodeError, TypeError):
                request_body = {"raw": request_body[:2000]}
        if not isinstance(request_body, dict):
            request_body = {}

        if isinstance(response_body, str):
            try:
                response_body = json.loads(response_body)
            except (json.JSONDecodeError, TypeError):
                response_body = {"raw": response_body[:2000]}
        if not isinstance(response_body, dict):
            response_body = {}

        # Extract user prompt
        user_input = self._extract_user_input(request_body)
        # Extract AI response
        ai_output = self._extract_ai_output(response_body)

        if not user_input and not ai_output:
            logger.debug("No content to scan for %s%s", host, path)
            return

        # Extract model name
        model = request_body.get("model", response_body.get("model", "unknown"))

        # Build structured agent-request payload
        agent_payload = {
            "request_id": f"MITM-{_intercepted_count}-{int(time.time())}",
            "title": f"Intercepted: {host}{path[:50]}",
            "source_app": f"mitm-{host}",
            "user_name": f"proxy-user@{source_ip}" if source_ip else "proxy-user",
            "user_input": user_input[:2000] if user_input else "",
            "tool_chain": [{
                "tool_name": host,
                "description": f"AI API call to {host}{path}",
                "sequence": 1,
                "input": {"prompt": user_input[:1000]} if user_input else {},
                "output": {"summary": ai_output[:1000]} if ai_output else {"summary": "No parseable output"},
                "reasoning": f"Outbound AI request intercepted by MITM proxy from {source_ip}",
                "duration_ms": 0,
                "status": "SUCCESS" if raw_payload.get("status_code", 0) == 200 else "FAILED",
            }],
            "final_output": {"summary": ai_output[:1000]} if ai_output else {"summary": "No output captured"},
            "metadata": {
                "model": model,
                "source_ip": source_ip,
                "destination": host,
                "endpoint": path,
                "intercepted_by": "mitm-proxy",
            },
        }

        try:
            with httpx.Client(timeout=180) as client:
                resp = client.post(
                    f"{self.governance_url}/api/v1/agent-requests",
                    json=agent_payload,
                )
                if resp.status_code < 400:
                    result = resp.json()
                    status = result.get("compliance_status", "CLEAN")
                    violations = result.get("violations", [])
                    risk = result.get("risk_score", 0)
                    logger.info(
                        "[GOVERNANCE] %s%s: status=%s violations=%d risk=%d",
                        host, path, status, len(violations), risk,
                    )
                else:
                    logger.error(
                        "[GOVERNANCE] API returned %s: %s",
                        resp.status_code, resp.text[:200],
                    )
        except Exception as exc:
            logger.error("[GOVERNANCE] Failed to send to governance server: %s", exc)

    def _extract_user_input(self, body: dict) -> str:
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

        # Raw text fallback
        if body.get("raw"):
            return str(body["raw"])

        return ""

    def _extract_ai_output(self, body: dict) -> str:
        """Extract AI response text from various API response formats."""
        # OpenAI format: {"choices": [{"message": {"content": "..."}}]}
        choices = body.get("choices", [])
        if choices:
            parts = []
            for c in choices:
                msg = c.get("message", {})
                if msg.get("content"):
                    parts.append(str(msg["content"]))
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


addons = [ChatGPTInterceptor()]

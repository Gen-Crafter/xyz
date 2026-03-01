from fastapi import APIRouter, Request
from app.models.schemas import ProxyStatus

router = APIRouter(prefix="/proxy", tags=["Proxy Management"])

# In-memory proxy state
_proxy_state = {
    "status": "active",
    "uptime_seconds": 0,
    "active_connections": 0,
    "total_intercepted": 0,
    "total_blocked": 0,
    "total_redacted": 0,
}


@router.get("/status", response_model=ProxyStatus)
async def get_proxy_status(request: Request):
    ai_endpoints = getattr(request.app.state, "ai_endpoints_count", 6)
    return ProxyStatus(
        ai_endpoints_monitored=ai_endpoints,
        **_proxy_state,
    )


@router.get("/pac", response_class=None)
async def get_pac_file():
    from fastapi.responses import Response
    pac_content = """function FindProxyForURL(url, host) {
    // Route AI traffic through compliance proxy
    if (shExpMatch(host, "api.openai.com") ||
        shExpMatch(host, "api.anthropic.com") ||
        shExpMatch(host, "*.openai.azure.com") ||
        shExpMatch(host, "generativelanguage.googleapis.com") ||
        shExpMatch(host, "api-inference.huggingface.co")) {
        return "PROXY localhost:8080";
    }
    return "DIRECT";
}"""
    return Response(content=pac_content, media_type="application/x-ns-proxy-autoconfig")


@router.post("/start")
async def start_proxy():
    _proxy_state["status"] = "active"
    return {"status": "started"}


@router.post("/stop")
async def stop_proxy():
    _proxy_state["status"] = "stopped"
    return {"status": "stopped"}


def increment_proxy_stat(stat: str, amount: int = 1):
    if stat in _proxy_state:
        _proxy_state[stat] += amount

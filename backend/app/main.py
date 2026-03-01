import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db, async_session
from app.services.context_detector import ContextDetector
from app.services.policy_engine import PolicyEngine
from app.services.filter_agent import FilterAgent
from app.services.rag_service import RAGService
from app.services.audit_service import AuditService
from app.services.llm_service import LlmService
from app.api.websocket import WebSocketManager

from app.api.v1 import proxy, context, filter, policies, endpoints, classifications, audit, rag, dashboard, agent_requests, dpdp, users, categories, identity_providers, mcp_deployments
from app.mcp_server import mcp as mcp_server, set_app_state as mcp_set_app_state

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Governance Proxy API...")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning("Database init failed (may not be available): %s", e)

    # Initialize LLM service (local Ollama — no auth required)
    llm_service = None
    try:
        llm_service = LlmService(settings)
        logger.info("LLM service initialized (Ollama model: %s at %s)",
                     settings.ollama_model, settings.ollama_base_url)
    except Exception as e:
        logger.warning("LLM service init failed (will retry on demand): %s", e)

    # Initialize services — wire LLM into context detector and RAG for synthesis
    rag_service = RAGService(llm_service=llm_service)
    policy_engine = PolicyEngine()
    context_detector = ContextDetector(rag_service=rag_service, llm_service=llm_service)
    filter_agent = FilterAgent(context_detector=context_detector, policy_engine=policy_engine)
    audit_service = AuditService()
    ws_manager = WebSocketManager()

    # Store on app state
    app.state.settings = settings
    app.state.rag_service = rag_service
    app.state.policy_engine = policy_engine
    app.state.context_detector = context_detector
    app.state.filter_agent = filter_agent
    app.state.audit_service = audit_service
    app.state.ws_manager = ws_manager
    app.state.llm = llm_service
    app.state.llm_service = llm_service

    # Seed default data
    try:
        async with async_session() as db:
            await policy_engine.seed_defaults(db)
            from app.api.v1.endpoints import seed_endpoints
            await seed_endpoints(db)
            from app.api.v1.classifications import seed_classification_rules
            await seed_classification_rules(db)
        logger.info("Default policies, endpoints, and classification rules seeded")
    except Exception as e:
        logger.warning("Seed failed (DB may not be available): %s", e)

    # Auto-ingest RAG documents
    try:
        result = await rag_service.ingest_regulation_texts()
        logger.info("RAG ingestion: %s", result)
    except Exception as e:
        logger.warning("RAG ingestion failed: %s", e)

    # Wire MCP server to backend services
    mcp_set_app_state(app.state)
    logger.info("MCP server initialized — tools available at /mcp")

    logger.info("AI Governance Proxy API ready")
    yield
    logger.info("Shutting down AI Governance Proxy API")


app = FastAPI(
    title="AI Governance Server API",
    description="Context-Aware Compliance Interception Layer for AI Agent Traffic",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(proxy.router, prefix="/api/v1")
app.include_router(context.router, prefix="/api/v1")
app.include_router(filter.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1")
app.include_router(endpoints.router, prefix="/api/v1")
app.include_router(classifications.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(agent_requests.router, prefix="/api/v1")
app.include_router(dpdp.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(identity_providers.router, prefix="/api/v1")
app.include_router(mcp_deployments.router, prefix="/api/v1")


# WebSocket endpoints
@app.websocket("/ws/interceptions")
async def ws_interceptions(websocket: WebSocket):
    await app.state.ws_manager.handle_connection("interceptions", websocket)


@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await app.state.ws_manager.handle_connection("alerts", websocket)


@app.websocket("/ws/stats")
async def ws_stats(websocket: WebSocket):
    await app.state.ws_manager.handle_connection("stats", websocket)


# Mount MCP Server (SSE transport) at /mcp
app.mount("/mcp", mcp_server.sse_app())


# Health check
@app.get("/health")
async def health():
    llm_ok = False
    if hasattr(app.state, "llm") and app.state.llm:
        llm_ok = app.state.llm.health()
    return {
        "status": "healthy",
        "service": "ai-governance-server",
        "llm_provider": "ollama",
        "llm_model": settings.ollama_model,
        "llm_healthy": llm_ok,
    }


@app.get("/")
async def root():
    return {
        "service": "AI Governance Server",
        "version": "1.0.0",
        "llm": f"Ollama ({settings.ollama_model})",
        "docs": "/docs",
        "health": "/health",
    }

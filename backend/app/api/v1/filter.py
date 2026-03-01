import uuid
import logging
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import ContextAnalysisRequest, ActionType
from app.core.database import get_db
from app.api.v1.proxy import increment_proxy_stat
from app.services.document_extractor import DocumentExtractor

logger = logging.getLogger("aigp.filter")
router = APIRouter(prefix="/filter", tags=["Filter Agent"])
_doc_extractor = DocumentExtractor()


@router.post("/process")
async def process_interception(payload: ContextAnalysisRequest, request: Request,
                               db: AsyncSession = Depends(get_db)):
    filter_agent = request.app.state.filter_agent
    audit_service = request.app.state.audit_service

    if not payload.interception_id:
        payload.interception_id = str(uuid.uuid4())
    # Ensure interception_id is a valid UUID for DB storage
    try:
        uuid.UUID(payload.interception_id)
    except (ValueError, AttributeError):
        payload.interception_id = str(uuid.uuid4())

    state = await filter_agent.process(payload)

    # Log to audit
    try:
        record = filter_agent.build_interception_record(state)
        await audit_service.log_interception(db, record)
    except Exception:
        pass

    # Update proxy stats
    increment_proxy_stat("total_intercepted")
    if state["decision"] == ActionType.BLOCK.value:
        increment_proxy_stat("total_blocked")
    elif state["decision"] == ActionType.REDACT.value:
        increment_proxy_stat("total_redacted")

    # Broadcast to WebSocket
    try:
        ws_manager = request.app.state.ws_manager
        await ws_manager.broadcast("interceptions", {
            "interception_id": state["interception_id"],
            "action": state["decision"],
            "destination": state.get("destination", ""),
            "source_ip": state.get("source_ip", ""),
            "risk_score": state.get("context_analysis", {}).get("risk_score", 0),
            "policies": state.get("applicable_policies", []),
            "processing_time_ms": state.get("processing_time_ms", 0),
        })
    except Exception:
        pass

    return {
        "interception_id": state["interception_id"],
        "decision": state["decision"],
        "justification": state["justification"],
        "policies_triggered": state.get("applicable_policies", []),
        "redacted_payload": state.get("redacted_payload"),
        "context_analysis": state.get("context_analysis"),
        "processing_time_ms": state.get("processing_time_ms", 0),
    }


@router.post("/process-file")
async def process_file_interception(payload: dict, request: Request,
                                    db: AsyncSession = Depends(get_db)):
    """Process an intercepted file attachment through the compliance pipeline.

    Expects:
        {
            "filename": "report.pdf",
            "content_base64": "<base64-encoded file content>",
            "content_type": "application/pdf",
            "source_ip": "10.0.1.x",
            "destination": "api.openai.com",
            "endpoint": "/v1/files",
            "interception_id": "MITM-FILE-1"
        }
    """
    import base64

    filename = payload.get("filename", "unknown")
    content_b64 = payload.get("content_base64", "")
    content_type = payload.get("content_type", "")

    # Decode file content
    try:
        file_bytes = base64.b64decode(content_b64)
    except Exception:
        return {"error": "Invalid base64 content", "decision": "ALLOW"}

    # Extract text from file
    extraction = _doc_extractor.extract(file_bytes, filename, content_type)
    extracted_text = extraction.get("text", "")

    if not extracted_text.strip():
        logger.info("No text extracted from %s (%s), allowing", filename, extraction.get("method"))
        return {
            "decision": "ALLOW",
            "justification": f"No readable text in {filename}",
            "extraction": extraction,
        }

    logger.info("Extracted %d chars from %s via %s", len(extracted_text), filename, extraction.get("method"))

    # Run extracted text through the standard compliance pipeline
    filter_agent = request.app.state.filter_agent
    audit_service = request.app.state.audit_service

    interception_id = payload.get("interception_id", str(uuid.uuid4()))
    try:
        uuid.UUID(interception_id)
    except (ValueError, AttributeError):
        interception_id = str(uuid.uuid4())

    analysis_request = ContextAnalysisRequest(
        interception_id=interception_id,
        direction="outbound",
        source_ip=payload.get("source_ip", "0.0.0.0"),
        destination=payload.get("destination", ""),
        endpoint=payload.get("endpoint", ""),
        payload={"messages": [{"role": "user", "content": extracted_text}]},
    )

    state = await filter_agent.process(analysis_request)

    # Log to audit
    try:
        record = filter_agent.build_interception_record(state)
        await audit_service.log_interception(db, record)
    except Exception:
        pass

    # Update proxy stats
    increment_proxy_stat("total_intercepted")
    if state["decision"] == ActionType.BLOCK.value:
        increment_proxy_stat("total_blocked")
    elif state["decision"] == ActionType.REDACT.value:
        increment_proxy_stat("total_redacted")

    # Broadcast to WebSocket
    try:
        ws_manager = request.app.state.ws_manager
        await ws_manager.broadcast("interceptions", {
            "interception_id": state["interception_id"],
            "action": state["decision"],
            "destination": state.get("destination", ""),
            "source_ip": state.get("source_ip", ""),
            "risk_score": state.get("context_analysis", {}).get("risk_score", 0),
            "policies": state.get("applicable_policies", []),
            "processing_time_ms": state.get("processing_time_ms", 0),
            "attachment": filename,
        })
    except Exception:
        pass

    return {
        "interception_id": state["interception_id"],
        "decision": state["decision"],
        "justification": state["justification"],
        "policies_triggered": state.get("applicable_policies", []),
        "context_analysis": state.get("context_analysis"),
        "processing_time_ms": state.get("processing_time_ms", 0),
        "extraction": extraction,
    }


@router.get("/stats")
async def get_filter_stats(request: Request, db: AsyncSession = Depends(get_db)):
    audit_service = request.app.state.audit_service
    return await audit_service.get_kpis(db)

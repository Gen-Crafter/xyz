import uuid
from fastapi import APIRouter, Request
from app.models.schemas import ContextAnalysisRequest, ContextAnalysisResult

router = APIRouter(prefix="/context", tags=["Context Detection"])


@router.post("/analyze", response_model=ContextAnalysisResult)
async def analyze_context(payload: ContextAnalysisRequest, request: Request):
    detector = request.app.state.context_detector
    if not payload.interception_id:
        payload.interception_id = str(uuid.uuid4())
    result = await detector.analyze(payload)
    return result


@router.post("/test", response_model=ContextAnalysisResult)
async def test_context(payload: ContextAnalysisRequest, request: Request):
    """Test context detection with sample data (no audit logging)."""
    detector = request.app.state.context_detector
    if not payload.interception_id:
        payload.interception_id = f"TEST-{uuid.uuid4().hex[:8]}"
    result = await detector.analyze(payload)
    return result

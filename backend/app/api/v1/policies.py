from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import PolicyCreate, PolicyResponse, PolicyTestRequest, PolicyTestResult, ActionType
from app.core.database import get_db

router = APIRouter(prefix="/policies", tags=["Policy Management"])


@router.get("", response_model=list[PolicyResponse])
async def list_policies(request: Request, db: AsyncSession = Depends(get_db)):
    engine = request.app.state.policy_engine
    return await engine.list_policies(db)


@router.post("", response_model=PolicyResponse)
async def create_policy(data: PolicyCreate, request: Request, db: AsyncSession = Depends(get_db)):
    engine = request.app.state.policy_engine
    return await engine.create_policy(db, data)


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    engine = request.app.state.policy_engine
    result = await engine.get_policy(db, policy_id)
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(policy_id: str, data: PolicyCreate, request: Request,
                        db: AsyncSession = Depends(get_db)):
    engine = request.app.state.policy_engine
    result = await engine.update_policy(db, policy_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


@router.delete("/{policy_id}")
async def delete_policy(policy_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    engine = request.app.state.policy_engine
    success = await engine.delete_policy(db, policy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"status": "deleted"}


@router.post("/{policy_id}/toggle", response_model=PolicyResponse)
async def toggle_policy(policy_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    engine = request.app.state.policy_engine
    result = await engine.toggle_policy(db, policy_id)
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


@router.post("/test", response_model=PolicyTestResult)
async def test_policy(data: PolicyTestRequest, request: Request):
    from app.models.schemas import ContextAnalysisRequest
    detector = request.app.state.context_detector
    engine = request.app.state.policy_engine

    analysis_request = ContextAnalysisRequest(
        interception_id="TEST",
        payload={"messages": [{"role": "user", "content": data.payload_text}]},
    )
    analysis = await detector.analyze(analysis_request)
    action, policy_ids, justification = engine.evaluate(analysis)

    return PolicyTestResult(
        triggered_policies=policy_ids,
        action=action,
        details=justification,
    )

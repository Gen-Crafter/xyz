import uuid
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import AIEndpointCreate, AIEndpointResponse
from app.models.db_models import AIEndpointModel
from app.core.database import get_db

router = APIRouter(prefix="/endpoints", tags=["AI Endpoint Configuration"])

DEFAULT_ENDPOINTS = [
    {"pattern": "api.openai.com/*", "provider": "OpenAI", "enabled": True, "default_action": "AUDIT"},
    {"pattern": "api.anthropic.com/*", "provider": "Anthropic", "enabled": True, "default_action": "AUDIT"},
    {"pattern": "generativelanguage.googleapis.com/*", "provider": "Google", "enabled": True, "default_action": "AUDIT"},
    {"pattern": "*.openai.azure.com/*", "provider": "Azure OpenAI", "enabled": True, "default_action": "AUDIT"},
    {"pattern": "api-inference.huggingface.co/*", "provider": "HuggingFace", "enabled": True, "default_action": "AUDIT"},
]


async def seed_endpoints(db: AsyncSession):
    result = await db.execute(select(AIEndpointModel))
    if result.scalars().first():
        return
    for ep in DEFAULT_ENDPOINTS:
        db.add(AIEndpointModel(**ep))
    await db.commit()


@router.get("", response_model=list[AIEndpointResponse])
async def list_endpoints(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIEndpointModel))
    rows = result.scalars().all()
    return [AIEndpointResponse(
        id=str(r.id), pattern=r.pattern, provider=r.provider or "",
        enabled=r.enabled, default_action=r.default_action or "AUDIT",
        created_at=r.created_at,
    ) for r in rows]


@router.post("", response_model=AIEndpointResponse)
async def create_endpoint(data: AIEndpointCreate, db: AsyncSession = Depends(get_db)):
    model = AIEndpointModel(
        pattern=data.pattern, provider=data.provider,
        enabled=data.enabled, default_action=data.default_action.value,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return AIEndpointResponse(
        id=str(model.id), pattern=model.pattern, provider=model.provider or "",
        enabled=model.enabled, default_action=model.default_action or "AUDIT",
        created_at=model.created_at,
    )


@router.put("/{endpoint_id}", response_model=AIEndpointResponse)
async def update_endpoint(endpoint_id: str, data: AIEndpointCreate,
                          db: AsyncSession = Depends(get_db)):
    row = await db.get(AIEndpointModel, endpoint_id)
    if not row:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    row.pattern = data.pattern
    row.provider = data.provider
    row.enabled = data.enabled
    row.default_action = data.default_action.value
    await db.commit()
    await db.refresh(row)
    return AIEndpointResponse(
        id=str(row.id), pattern=row.pattern, provider=row.provider or "",
        enabled=row.enabled, default_action=row.default_action or "AUDIT",
        created_at=row.created_at,
    )


@router.delete("/{endpoint_id}")
async def delete_endpoint(endpoint_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(AIEndpointModel, endpoint_id)
    if not row:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    await db.delete(row)
    await db.commit()
    return {"status": "deleted"}

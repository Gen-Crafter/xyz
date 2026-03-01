from typing import Optional
from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import AuditEntry
from app.core.database import get_db

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("", response_model=list[AuditEntry])
async def list_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = None,
):
    audit = request.app.state.audit_service
    return await audit.get_audit_logs(db, limit=limit, offset=offset, event_type=event_type)


@router.get("/export")
async def export_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(1000, le=10000),
):
    audit = request.app.state.audit_service
    entries = await audit.get_audit_logs(db, limit=limit)
    rows = []
    for e in entries:
        rows.append({
            "id": e.id,
            "interception_id": e.interception_id,
            "event_type": e.event_type,
            "details": str(e.details),
            "current_hash": e.current_hash,
            "created_at": e.created_at.isoformat() if e.created_at else "",
        })
    return {"entries": rows, "count": len(rows)}


@router.post("/verify")
async def verify_hash_chain(request: Request, db: AsyncSession = Depends(get_db)):
    audit = request.app.state.audit_service
    return await audit.verify_hash_chain(db)

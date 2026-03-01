import hashlib
import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import AuditLogModel, InterceptionModel
from app.models.schemas import AuditEntry, InterceptionRecord, ActionType


class AuditService:
    """Tamper-evident audit logging with SHA-256 hash chain."""

    def __init__(self):
        self._last_hash: Optional[str] = None

    def _compute_hash(self, previous_hash: Optional[str], event_type: str, details: dict) -> str:
        data = json.dumps({
            "previous_hash": previous_hash or "",
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()

    async def log_interception(self, db: AsyncSession, interception: InterceptionRecord):
        payload_hash = hashlib.sha256(
            json.dumps({"id": interception.id}, default=str).encode()
        ).hexdigest()

        model = InterceptionModel(
            id=interception.id if interception.id else None,
            source_ip=interception.source_ip,
            destination=interception.destination,
            endpoint=interception.endpoint,
            direction=interception.direction.value,
            payload_hash=payload_hash,
            data_classifications=interception.data_classifications,
            entities_detected=[e.model_dump() for e in interception.entities_detected],
            regulations_applicable=interception.regulations_applicable,
            risk_score=interception.risk_score,
            action_taken=interception.action_taken.value,
            policies_triggered=interception.policies_triggered,
            justification=interception.justification,
            processing_time_ms=interception.processing_time_ms,
        )
        db.add(model)
        await db.flush()

        # Audit log entry with hash chain
        details = {
            "action": interception.action_taken.value,
            "risk_score": interception.risk_score,
            "policies": interception.policies_triggered,
        }
        current_hash = self._compute_hash(self._last_hash, "INTERCEPTION", details)
        audit = AuditLogModel(
            interception_id=model.id,
            event_type="INTERCEPTION",
            details=details,
            previous_hash=self._last_hash,
            current_hash=current_hash,
        )
        db.add(audit)
        self._last_hash = current_hash
        await db.commit()

    async def log_event(self, db: AsyncSession, event_type: str, details: dict,
                        interception_id: Optional[str] = None):
        current_hash = self._compute_hash(self._last_hash, event_type, details)
        audit = AuditLogModel(
            interception_id=interception_id,
            event_type=event_type,
            details=details,
            previous_hash=self._last_hash,
            current_hash=current_hash,
        )
        db.add(audit)
        self._last_hash = current_hash
        await db.commit()

    async def get_audit_logs(self, db: AsyncSession, limit: int = 50,
                             offset: int = 0, event_type: Optional[str] = None) -> list[AuditEntry]:
        query = select(AuditLogModel).order_by(desc(AuditLogModel.created_at))
        if event_type:
            query = query.where(AuditLogModel.event_type == event_type)
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        rows = result.scalars().all()
        return [AuditEntry(
            id=r.id,
            interception_id=str(r.interception_id) if r.interception_id else None,
            event_type=r.event_type,
            details=r.details or {},
            previous_hash=r.previous_hash,
            current_hash=r.current_hash,
            created_at=r.created_at,
        ) for r in rows]

    async def get_interceptions(self, db: AsyncSession, limit: int = 50,
                                offset: int = 0, action: Optional[str] = None) -> list[InterceptionRecord]:
        query = select(InterceptionModel).order_by(desc(InterceptionModel.created_at))
        if action:
            query = query.where(InterceptionModel.action_taken == action)
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        rows = result.scalars().all()
        return [InterceptionRecord(
            id=str(r.id),
            source_ip=r.source_ip,
            destination=r.destination,
            endpoint=r.endpoint or "",
            direction=r.direction,
            data_classifications=r.data_classifications or [],
            entities_detected=[],
            regulations_applicable=r.regulations_applicable or [],
            risk_score=r.risk_score or 0,
            action_taken=ActionType(r.action_taken),
            policies_triggered=r.policies_triggered or [],
            justification=r.justification or "",
            processing_time_ms=r.processing_time_ms or 0,
            created_at=r.created_at,
        ) for r in rows]

    async def get_kpis(self, db: AsyncSession) -> dict:
        total = await db.execute(select(func.count(InterceptionModel.id)))
        blocked = await db.execute(
            select(func.count(InterceptionModel.id)).where(InterceptionModel.action_taken == "BLOCK"))
        redacted = await db.execute(
            select(func.count(InterceptionModel.id)).where(InterceptionModel.action_taken == "REDACT"))
        allowed = await db.execute(
            select(func.count(InterceptionModel.id)).where(InterceptionModel.action_taken == "ALLOW"))
        audited = await db.execute(
            select(func.count(InterceptionModel.id)).where(InterceptionModel.action_taken == "AUDIT"))
        avg_time = await db.execute(select(func.avg(InterceptionModel.processing_time_ms)))

        total_count = total.scalar() or 0
        blocked_count = blocked.scalar() or 0
        redacted_count = redacted.scalar() or 0
        allowed_count = allowed.scalar() or 0

        compliance_score = 100.0
        if total_count > 0:
            compliance_score = round((allowed_count / total_count) * 100, 1)

        return {
            "total_interceptions": total_count,
            "total_blocked": blocked_count,
            "total_redacted": redacted_count,
            "total_allowed": allowed_count,
            "total_audited": audited.scalar() or 0,
            "compliance_score": compliance_score,
            "avg_processing_time_ms": round(avg_time.scalar() or 0, 1),
        }

    async def verify_hash_chain(self, db: AsyncSession) -> dict:
        result = await db.execute(
            select(AuditLogModel).order_by(AuditLogModel.id).limit(1000))
        rows = result.scalars().all()
        valid = True
        broken_at = None
        for i, row in enumerate(rows):
            if i > 0 and row.previous_hash != rows[i - 1].current_hash:
                valid = False
                broken_at = row.id
                break
        return {"valid": valid, "entries_checked": len(rows), "broken_at": broken_at}

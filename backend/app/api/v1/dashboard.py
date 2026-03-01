from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import DashboardKPIs
from app.models.db_models import InterceptionModel
from app.core.database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/kpis", response_model=DashboardKPIs)
async def get_dashboard_kpis(request: Request, db: AsyncSession = Depends(get_db)):
    audit = request.app.state.audit_service
    kpis = await audit.get_kpis(db)
    policy_engine = request.app.state.policy_engine
    active_policies = len([p for p in policy_engine.get_all_policies_memory() if p.get("enabled")])

    return DashboardKPIs(
        total_interceptions=kpis.get("total_interceptions", 0),
        total_blocked=kpis.get("total_blocked", 0),
        total_redacted=kpis.get("total_redacted", 0),
        total_allowed=kpis.get("total_allowed", 0),
        total_audited=kpis.get("total_audited", 0),
        compliance_score=kpis.get("compliance_score", 100.0),
        active_policies=active_policies,
        active_endpoints=6,
        avg_processing_time_ms=kpis.get("avg_processing_time_ms", 0),
    )


@router.get("/interception-volume")
async def get_interception_volume(db: AsyncSession = Depends(get_db),
                                  hours: int = Query(24, ge=1, le=168)):
    """Return interception counts per hour for the given time range."""
    try:
        result = await db.execute(
            text("""
                SELECT date_trunc('hour', created_at) as hour,
                       action_taken,
                       COUNT(*) as count
                FROM interceptions
                WHERE created_at > NOW() - INTERVAL ':hours hours'
                GROUP BY hour, action_taken
                ORDER BY hour
            """).bindparams(hours=hours)
        )
        rows = result.fetchall()
        return [{"hour": str(r[0]), "action": r[1], "count": r[2]} for r in rows]
    except Exception:
        return []


@router.get("/action-breakdown")
async def get_action_breakdown(db: AsyncSession = Depends(get_db)):
    """Return count of each action type."""
    try:
        result = await db.execute(
            select(InterceptionModel.action_taken, func.count(InterceptionModel.id))
            .group_by(InterceptionModel.action_taken)
        )
        rows = result.fetchall()
        return [{"action": r[0], "count": r[1]} for r in rows]
    except Exception:
        return []


@router.get("/recent-interceptions")
async def get_recent_interceptions(request: Request, db: AsyncSession = Depends(get_db),
                                   limit: int = Query(20, le=100)):
    audit = request.app.state.audit_service
    records = await audit.get_interceptions(db, limit=limit)
    return [r.model_dump() for r in records]

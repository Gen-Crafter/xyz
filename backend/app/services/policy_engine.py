import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import (
    PolicyCreate, PolicyResponse, ActionType, PolicyConditions,
    ContextAnalysisResult, PolicyTestRequest, PolicyTestResult
)
from app.models.db_models import PolicyModel


# ─── Default policies shipped out-of-box ─────────────────────────────────────

DEFAULT_POLICIES: list[dict] = [
    {
        "id": "POL-HIPAA-PHI-001",
        "name": "Block PHI to External AI Services",
        "description": "Prevent Protected Health Information from being sent to AI services without BAA",
        "enabled": True,
        "priority": 1,
        "regulation": "HIPAA",
        "conditions": {"data_classifications": ["PHI"], "direction": "outbound", "destination_type": "external_ai"},
        "action": "BLOCK",
        "notification": {"notify_user": True, "notify_admin": True,
                         "message": "Request blocked: PHI detected. HIPAA prohibits sending PHI to external AI without a BAA."},
    },
    {
        "id": "POL-GDPR-PII-001",
        "name": "Block EU PII to Non-EU AI",
        "description": "Block EU citizen PII sent to non-EU AI services",
        "enabled": True,
        "priority": 2,
        "regulation": "GDPR",
        "conditions": {"data_classifications": ["PII"], "direction": "outbound", "destination_type": "external_ai"},
        "action": "REDACT",
        "redaction_strategy": {"method": "token_replacement", "config": {}},
        "notification": {"notify_user": True, "notify_admin": False,
                         "message": "PII was redacted from your request per GDPR policy."},
    },
    {
        "id": "POL-PCI-PAN-001",
        "name": "Redact Credit Card PAN",
        "description": "Mask credit card numbers in AI traffic",
        "enabled": True,
        "priority": 1,
        "regulation": "PCI-DSS",
        "conditions": {"data_classifications": ["PCI"], "patterns": ["CREDIT_CARD"]},
        "action": "REDACT",
        "redaction_strategy": {"method": "token_replacement", "config": {}},
        "notification": {"notify_user": True, "notify_admin": True,
                         "message": "Credit card data was redacted per PCI-DSS Requirement 3.4."},
    },
    {
        "id": "POL-PCI-CVV-001",
        "name": "Block CVV in AI Traffic",
        "description": "Block any traffic containing CVV/CVC data",
        "enabled": True,
        "priority": 1,
        "regulation": "PCI-DSS",
        "conditions": {"data_classifications": ["PCI"], "patterns": ["CVV"]},
        "action": "BLOCK",
        "notification": {"notify_user": True, "notify_admin": True,
                         "message": "Request blocked: CVV data detected. PCI-DSS prohibits CVV storage/transmission."},
    },
    {
        "id": "POL-GENERAL-001",
        "name": "Redact SSN in AI Traffic",
        "description": "Redact Social Security Numbers from AI requests",
        "enabled": True,
        "priority": 3,
        "regulation": "INTERNAL",
        "conditions": {"data_classifications": ["PII"], "patterns": ["SSN"]},
        "action": "REDACT",
        "redaction_strategy": {"method": "token_replacement", "config": {}},
        "notification": {"notify_user": True, "notify_admin": False,
                         "message": "SSN was redacted from your request."},
    },
    {
        "id": "POL-GENERAL-002",
        "name": "Block Secrets in AI Traffic",
        "description": "Block API keys and passwords from being sent to AI services",
        "enabled": True,
        "priority": 1,
        "regulation": "INTERNAL",
        "conditions": {"data_classifications": ["SECRET"], "patterns": ["API_KEY", "PASSWORD"]},
        "action": "BLOCK",
        "notification": {"notify_user": True, "notify_admin": True,
                         "message": "Request blocked: API key or password detected in AI traffic."},
    },
    {
        "id": "POL-KEYWORD-001",
        "name": "Block Confidential Product Codenames",
        "description": "Prevent unreleased product codenames and internal project names from being sent to external AI services",
        "enabled": True,
        "priority": 1,
        "regulation": "INTERNAL",
        "conditions": {"blocked_keywords": [
            "Project Orion", "Project Nebula", "Project Titan", "Project Helix",
            "PowerEdge XR9000", "Apex Nova", "Project Lightning",
        ]},
        "action": "BLOCK",
        "notification": {"notify_user": True, "notify_admin": True,
                         "message": "Request blocked: Confidential product codename detected. Internal-only information must not be shared with external AI services."},
    },
]


class PolicyEngine:
    """Manages compliance policies and evaluates interceptions against them."""

    def __init__(self):
        self._memory_policies: dict[str, dict] = {}
        for p in DEFAULT_POLICIES:
            self._memory_policies[p["id"]] = p

    # ─── In-memory operations (used when DB is unavailable) ──────────────

    def get_all_policies_memory(self) -> list[dict]:
        return list(self._memory_policies.values())

    def get_policy_memory(self, policy_id: str) -> Optional[dict]:
        return self._memory_policies.get(policy_id)

    # ─── DB operations ───────────────────────────────────────────────────

    async def seed_defaults(self, db: AsyncSession):
        for p in DEFAULT_POLICIES:
            existing = await db.get(PolicyModel, p["id"])
            if not existing:
                model = PolicyModel(**p)
                db.add(model)
        await db.commit()

    async def list_policies(self, db: AsyncSession) -> list[PolicyResponse]:
        result = await db.execute(select(PolicyModel).order_by(PolicyModel.priority))
        rows = result.scalars().all()
        return [self._to_response(r) for r in rows]

    async def get_policy(self, db: AsyncSession, policy_id: str) -> Optional[PolicyResponse]:
        row = await db.get(PolicyModel, policy_id)
        return self._to_response(row) if row else None

    async def create_policy(self, db: AsyncSession, data: PolicyCreate) -> PolicyResponse:
        if not data.id:
            data.id = f"POL-CUSTOM-{uuid.uuid4().hex[:8].upper()}"
        model = PolicyModel(
            id=data.id,
            name=data.name,
            description=data.description,
            enabled=data.enabled,
            priority=data.priority,
            regulation=data.regulation,
            conditions=data.conditions.model_dump(),
            action=data.action.value,
            redaction_strategy=data.redaction_strategy.model_dump() if data.redaction_strategy else None,
            notification=data.notification.model_dump() if data.notification else None,
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)
        self._memory_policies[model.id] = self._row_to_dict(model)
        return self._to_response(model)

    async def update_policy(self, db: AsyncSession, policy_id: str, data: PolicyCreate) -> Optional[PolicyResponse]:
        row = await db.get(PolicyModel, policy_id)
        if not row:
            return None
        row.name = data.name
        row.description = data.description
        row.enabled = data.enabled
        row.priority = data.priority
        row.regulation = data.regulation
        row.conditions = data.conditions.model_dump()
        row.action = data.action.value
        row.redaction_strategy = data.redaction_strategy.model_dump() if data.redaction_strategy else None
        row.notification = data.notification.model_dump() if data.notification else None
        row.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(row)
        self._memory_policies[row.id] = self._row_to_dict(row)
        return self._to_response(row)

    async def delete_policy(self, db: AsyncSession, policy_id: str) -> bool:
        row = await db.get(PolicyModel, policy_id)
        if not row:
            return False
        await db.delete(row)
        await db.commit()
        self._memory_policies.pop(policy_id, None)
        return True

    async def toggle_policy(self, db: AsyncSession, policy_id: str) -> Optional[PolicyResponse]:
        row = await db.get(PolicyModel, policy_id)
        if not row:
            return None
        row.enabled = not row.enabled
        row.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(row)
        self._memory_policies[row.id] = self._row_to_dict(row)
        return self._to_response(row)

    # ─── Policy evaluation ───────────────────────────────────────────────

    def evaluate(self, analysis: ContextAnalysisResult) -> tuple[ActionType, list[str], str]:
        """Evaluate analysis against all enabled policies. Returns (action, triggered_policy_ids, justification)."""
        triggered: list[tuple[int, str, ActionType, str]] = []

        policies = self.get_all_policies_memory()
        for pol in policies:
            if not pol.get("enabled", True):
                continue
            cond = pol.get("conditions", {})

            # Check data classification match
            required_cls = cond.get("data_classifications", [])
            if required_cls:
                if not any(c in analysis.data_classifications for c in required_cls):
                    continue

            # Check pattern match (entity types)
            required_patterns = cond.get("patterns", [])
            if required_patterns:
                entity_types = {e.type for e in analysis.entities_detected}
                if not any(p in entity_types for p in required_patterns):
                    continue

            # Check direction
            if cond.get("direction") and cond["direction"] != "outbound":
                continue

            action = ActionType(pol["action"])
            notification = pol.get("notification", {})
            msg = notification.get("message", "") if notification else ""
            triggered.append((pol.get("priority", 100), pol["id"], action, msg))

        if not triggered:
            return ActionType.ALLOW, [], "No policies triggered"

        # Sort by priority (lowest number = highest priority)
        triggered.sort(key=lambda x: x[0])

        # Most restrictive action wins: BLOCK > REDACT > AUDIT > ALLOW
        action_priority = {ActionType.BLOCK: 0, ActionType.REDACT: 1, ActionType.AUDIT: 2, ActionType.ALLOW: 3}
        best_action = ActionType.ALLOW
        for _, _, act, _ in triggered:
            if action_priority.get(act, 3) < action_priority.get(best_action, 3):
                best_action = act

        policy_ids = [t[1] for t in triggered]
        justifications = [t[3] for t in triggered if t[3]]
        justification = " | ".join(justifications) if justifications else f"Policies triggered: {', '.join(policy_ids)}"

        return best_action, policy_ids, justification

    # ─── Helpers ─────────────────────────────────────────────────────────

    def _to_response(self, row: PolicyModel) -> PolicyResponse:
        return PolicyResponse(
            id=row.id,
            name=row.name,
            description=row.description or "",
            enabled=row.enabled,
            priority=row.priority or 100,
            regulation=row.regulation or "",
            conditions=PolicyConditions(**row.conditions) if isinstance(row.conditions, dict) else PolicyConditions(),
            action=ActionType(row.action),
            created_by=row.created_by or "system",
            created_at=row.created_at or datetime.now(timezone.utc),
            updated_at=row.updated_at or datetime.now(timezone.utc),
        )

    def _row_to_dict(self, row: PolicyModel) -> dict:
        return {
            "id": row.id, "name": row.name, "description": row.description,
            "enabled": row.enabled, "priority": row.priority, "regulation": row.regulation,
            "conditions": row.conditions, "action": row.action,
            "redaction_strategy": row.redaction_strategy, "notification": row.notification,
        }

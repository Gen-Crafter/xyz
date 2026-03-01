import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.db_models import (
    DPDPSystemModel, DPDPDatasetModel, DPDPFieldModel,
    DPDPConsentModel, DPDPRightsRequestModel, DPDPBreachModel,
    DPDPRetentionPolicyModel, DPDPVendorModel, DPDPAuditEventModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dpdp", tags=["DPDP Compliance"])

# ── Placeholder tenant_id (replace with auth-context extraction later) ──────
DEMO_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ═══════════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class SystemCreate(BaseModel):
    name: str
    owner: str = ""
    description: str = ""
    purposes: List[str] = Field(default_factory=list)
    data_flow_tags: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"

class SystemOut(SystemCreate):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DatasetCreate(BaseModel):
    system_id: str
    name: str
    category: str = "general"
    pii_fields: List[str] = Field(default_factory=list)
    purposes: List[str] = Field(default_factory=list)

class DatasetOut(DatasetCreate):
    id: str
    risk_score: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConsentCreate(BaseModel):
    principal_id: str
    purpose: str
    version: str = "1.0"
    policy_text_hash: str = ""
    evidence_ref: str = ""

class ConsentOut(ConsentCreate):
    id: str
    status: str = "ACTIVE"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    withdrawn_at: Optional[datetime] = None

class RightsRequestCreate(BaseModel):
    principal_id: str
    request_type: str
    description: str = ""

class RightsRequestOut(RightsRequestCreate):
    id: str
    status: str = "OPEN"
    sla_due: Optional[datetime] = None
    assigned_to: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BreachCreate(BaseModel):
    title: str
    severity: str = "MEDIUM"
    description: str = ""
    impacted_records: int = 0
    data_categories: List[str] = Field(default_factory=list)

class BreachOut(BreachCreate):
    id: str
    status: str = "REPORTED"
    root_cause: str = ""
    remediation: str = ""
    notified_board: bool = False
    notified_principals: bool = False
    reported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RetentionPolicyCreate(BaseModel):
    name: str
    purpose: str = ""
    system_scope: str = "*"
    retention_days: int = 365
    legal_hold: bool = False
    auto_delete: bool = False

class RetentionPolicyOut(RetentionPolicyCreate):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VendorCreate(BaseModel):
    name: str
    service_type: str = ""
    data_shared: List[str] = Field(default_factory=list)
    dpa_status: str = "PENDING"
    transfer_basis: str = ""

class VendorOut(VendorCreate):
    id: str
    review_due: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AuditEventOut(BaseModel):
    id: int
    actor: str
    action: str
    entity_type: str
    entity_id: str
    details: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DashboardStats(BaseModel):
    total_systems: int = 0
    total_datasets: int = 0
    total_pii_fields: int = 0
    active_consents: int = 0
    withdrawn_consents: int = 0
    open_rights_requests: int = 0
    active_breaches: int = 0
    retention_policies: int = 0
    vendors: int = 0
    compliance_score: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

async def _emit_audit(db: AsyncSession, action: str, entity_type: str, entity_id: str, details: dict = {}):
    evt = DPDPAuditEventModel(
        tenant_id=DEMO_TENANT, actor="system", action=action,
        entity_type=entity_type, entity_id=str(entity_id), details=details,
    )
    db.add(evt)


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    t = DEMO_TENANT
    sys_count = (await db.execute(select(func.count()).select_from(DPDPSystemModel).where(DPDPSystemModel.tenant_id == t))).scalar() or 0
    ds_count = (await db.execute(select(func.count()).select_from(DPDPDatasetModel).where(DPDPDatasetModel.tenant_id == t))).scalar() or 0
    field_count = (await db.execute(select(func.count()).select_from(DPDPFieldModel).where(DPDPFieldModel.tenant_id == t))).scalar() or 0
    active_c = (await db.execute(select(func.count()).select_from(DPDPConsentModel).where(DPDPConsentModel.tenant_id == t, DPDPConsentModel.status == "ACTIVE"))).scalar() or 0
    withdrawn_c = (await db.execute(select(func.count()).select_from(DPDPConsentModel).where(DPDPConsentModel.tenant_id == t, DPDPConsentModel.status == "WITHDRAWN"))).scalar() or 0
    open_r = (await db.execute(select(func.count()).select_from(DPDPRightsRequestModel).where(DPDPRightsRequestModel.tenant_id == t, DPDPRightsRequestModel.status == "OPEN"))).scalar() or 0
    active_b = (await db.execute(select(func.count()).select_from(DPDPBreachModel).where(DPDPBreachModel.tenant_id == t, DPDPBreachModel.status != "RESOLVED"))).scalar() or 0
    ret_count = (await db.execute(select(func.count()).select_from(DPDPRetentionPolicyModel).where(DPDPRetentionPolicyModel.tenant_id == t))).scalar() or 0
    ven_count = (await db.execute(select(func.count()).select_from(DPDPVendorModel).where(DPDPVendorModel.tenant_id == t))).scalar() or 0

    score = min(100, 20 + (20 if active_c > 0 else 0) + (20 if ret_count > 0 else 0) + (20 if active_b == 0 else 0) + (20 if open_r == 0 else 10))

    return DashboardStats(
        total_systems=sys_count, total_datasets=ds_count, total_pii_fields=field_count,
        active_consents=active_c, withdrawn_consents=withdrawn_c,
        open_rights_requests=open_r, active_breaches=active_b,
        retention_policies=ret_count, vendors=ven_count,
        compliance_score=score,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Inventory — Systems
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/inventory/systems", response_model=List[SystemOut])
async def list_systems(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(DPDPSystemModel).where(DPDPSystemModel.tenant_id == DEMO_TENANT))).scalars().all()
    return [SystemOut(id=str(r.id), name=r.name, owner=r.owner, description=r.description,
                      purposes=r.purposes or [], data_flow_tags=r.data_flow_tags or [],
                      risk_level=r.risk_level, created_at=r.created_at) for r in rows]


@router.post("/inventory/systems", response_model=SystemOut, status_code=201)
async def create_system(body: SystemCreate, db: AsyncSession = Depends(get_db)):
    obj = DPDPSystemModel(tenant_id=DEMO_TENANT, **body.model_dump())
    db.add(obj)
    await db.flush()
    await _emit_audit(db, "system.created", "system", obj.id)
    return SystemOut(id=str(obj.id), **body.model_dump(), created_at=obj.created_at)


@router.delete("/inventory/systems/{system_id}", status_code=204)
async def delete_system(system_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(DPDPSystemModel).where(DPDPSystemModel.id == uuid.UUID(system_id)))
    await _emit_audit(db, "system.deleted", "system", system_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Inventory — Datasets
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/inventory/datasets", response_model=List[DatasetOut])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(DPDPDatasetModel).where(DPDPDatasetModel.tenant_id == DEMO_TENANT))).scalars().all()
    return [DatasetOut(id=str(r.id), system_id=str(r.system_id), name=r.name,
                       category=r.category, pii_fields=r.pii_fields or [],
                       purposes=r.purposes or [], risk_score=r.risk_score,
                       created_at=r.created_at) for r in rows]


@router.post("/inventory/datasets", response_model=DatasetOut, status_code=201)
async def create_dataset(body: DatasetCreate, db: AsyncSession = Depends(get_db)):
    obj = DPDPDatasetModel(tenant_id=DEMO_TENANT, system_id=uuid.UUID(body.system_id),
                           name=body.name, category=body.category,
                           pii_fields=body.pii_fields, purposes=body.purposes)
    db.add(obj)
    await db.flush()
    await _emit_audit(db, "dataset.created", "dataset", obj.id)
    return DatasetOut(id=str(obj.id), system_id=body.system_id, name=body.name,
                      category=body.category, pii_fields=body.pii_fields,
                      purposes=body.purposes, risk_score=0, created_at=obj.created_at)


# ═══════════════════════════════════════════════════════════════════════════════
# Consent Management
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/consents", response_model=List[ConsentOut])
async def list_consents(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(DPDPConsentModel).where(DPDPConsentModel.tenant_id == DEMO_TENANT))).scalars().all()
    return [ConsentOut(id=str(r.id), principal_id=r.principal_id, purpose=r.purpose,
                       version=r.version, status=r.status,
                       policy_text_hash=r.policy_text_hash, evidence_ref=r.evidence_ref,
                       captured_at=r.captured_at, withdrawn_at=r.withdrawn_at) for r in rows]


@router.post("/consents", response_model=ConsentOut, status_code=201)
async def capture_consent(body: ConsentCreate, db: AsyncSession = Depends(get_db)):
    obj = DPDPConsentModel(tenant_id=DEMO_TENANT, **body.model_dump())
    db.add(obj)
    await db.flush()
    await _emit_audit(db, "consent.captured", "consent", obj.id,
                      {"principal": body.principal_id, "purpose": body.purpose})
    return ConsentOut(id=str(obj.id), **body.model_dump(), status="ACTIVE", captured_at=obj.captured_at)


@router.post("/consents/{consent_id}/withdraw", response_model=ConsentOut)
async def withdraw_consent(consent_id: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(DPDPConsentModel).where(DPDPConsentModel.id == uuid.UUID(consent_id)))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Consent not found")
    row.status = "WITHDRAWN"
    row.withdrawn_at = datetime.now(timezone.utc)
    await db.flush()
    await _emit_audit(db, "consent.withdrawn", "consent", consent_id)
    return ConsentOut(id=str(row.id), principal_id=row.principal_id, purpose=row.purpose,
                      version=row.version, status=row.status,
                      policy_text_hash=row.policy_text_hash, evidence_ref=row.evidence_ref,
                      captured_at=row.captured_at, withdrawn_at=row.withdrawn_at)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Principal Rights
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/rights", response_model=List[RightsRequestOut])
async def list_rights_requests(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(DPDPRightsRequestModel).where(DPDPRightsRequestModel.tenant_id == DEMO_TENANT))).scalars().all()
    return [RightsRequestOut(id=str(r.id), principal_id=r.principal_id,
                             request_type=r.request_type, status=r.status,
                             description=r.description, sla_due=r.sla_due,
                             assigned_to=r.assigned_to, created_at=r.created_at) for r in rows]


@router.post("/rights", response_model=RightsRequestOut, status_code=201)
async def create_rights_request(body: RightsRequestCreate, db: AsyncSession = Depends(get_db)):
    sla = datetime.now(timezone.utc) + timedelta(days=30)
    obj = DPDPRightsRequestModel(tenant_id=DEMO_TENANT, principal_id=body.principal_id,
                                  request_type=body.request_type,
                                  description=body.description, sla_due=sla)
    db.add(obj)
    await db.flush()
    await _emit_audit(db, "rights.created", "rights_request", obj.id,
                      {"type": body.request_type, "principal": body.principal_id})
    return RightsRequestOut(id=str(obj.id), principal_id=body.principal_id,
                            request_type=body.request_type, description=body.description,
                            status="OPEN", sla_due=sla, created_at=obj.created_at)


@router.patch("/rights/{request_id}")
async def update_rights_request(request_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(DPDPRightsRequestModel).where(DPDPRightsRequestModel.id == uuid.UUID(request_id)))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Rights request not found")
    for k, v in body.items():
        if hasattr(row, k):
            setattr(row, k, v)
    await db.flush()
    await _emit_audit(db, "rights.updated", "rights_request", request_id, body)
    return {"status": "updated"}


# ═══════════════════════════════════════════════════════════════════════════════
# Breach Management
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/breaches", response_model=List[BreachOut])
async def list_breaches(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(DPDPBreachModel).where(DPDPBreachModel.tenant_id == DEMO_TENANT))).scalars().all()
    return [BreachOut(id=str(r.id), title=r.title, severity=r.severity, status=r.status,
                      description=r.description, impacted_records=r.impacted_records,
                      data_categories=r.data_categories or [], root_cause=r.root_cause,
                      remediation=r.remediation, notified_board=r.notified_board,
                      notified_principals=r.notified_principals,
                      reported_at=r.reported_at) for r in rows]


@router.post("/breaches", response_model=BreachOut, status_code=201)
async def create_breach(body: BreachCreate, db: AsyncSession = Depends(get_db)):
    obj = DPDPBreachModel(tenant_id=DEMO_TENANT, **body.model_dump())
    db.add(obj)
    await db.flush()
    await _emit_audit(db, "breach.reported", "breach", obj.id,
                      {"severity": body.severity, "records": body.impacted_records})
    return BreachOut(id=str(obj.id), **body.model_dump(), status="REPORTED", reported_at=obj.reported_at)


@router.patch("/breaches/{breach_id}")
async def update_breach(breach_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(DPDPBreachModel).where(DPDPBreachModel.id == uuid.UUID(breach_id)))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Breach not found")
    for k, v in body.items():
        if hasattr(row, k):
            setattr(row, k, v)
    await db.flush()
    await _emit_audit(db, "breach.updated", "breach", breach_id, body)
    return {"status": "updated"}


# ═══════════════════════════════════════════════════════════════════════════════
# Retention & Deletion
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/retention", response_model=List[RetentionPolicyOut])
async def list_retention_policies(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(DPDPRetentionPolicyModel).where(DPDPRetentionPolicyModel.tenant_id == DEMO_TENANT))).scalars().all()
    return [RetentionPolicyOut(id=str(r.id), name=r.name, purpose=r.purpose,
                               system_scope=r.system_scope, retention_days=r.retention_days,
                               legal_hold=r.legal_hold, auto_delete=r.auto_delete,
                               created_at=r.created_at) for r in rows]


@router.post("/retention", response_model=RetentionPolicyOut, status_code=201)
async def create_retention_policy(body: RetentionPolicyCreate, db: AsyncSession = Depends(get_db)):
    obj = DPDPRetentionPolicyModel(tenant_id=DEMO_TENANT, **body.model_dump())
    db.add(obj)
    await db.flush()
    await _emit_audit(db, "retention.created", "retention_policy", obj.id)
    return RetentionPolicyOut(id=str(obj.id), **body.model_dump(), created_at=obj.created_at)


@router.delete("/retention/{policy_id}", status_code=204)
async def delete_retention_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(DPDPRetentionPolicyModel).where(DPDPRetentionPolicyModel.id == uuid.UUID(policy_id)))
    await _emit_audit(db, "retention.deleted", "retention_policy", policy_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Vendor Compliance
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/vendors", response_model=List[VendorOut])
async def list_vendors(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(DPDPVendorModel).where(DPDPVendorModel.tenant_id == DEMO_TENANT))).scalars().all()
    return [VendorOut(id=str(r.id), name=r.name, service_type=r.service_type,
                      data_shared=r.data_shared or [], dpa_status=r.dpa_status,
                      transfer_basis=r.transfer_basis, review_due=r.review_due,
                      created_at=r.created_at) for r in rows]


@router.post("/vendors", response_model=VendorOut, status_code=201)
async def create_vendor(body: VendorCreate, db: AsyncSession = Depends(get_db)):
    obj = DPDPVendorModel(tenant_id=DEMO_TENANT, **body.model_dump())
    db.add(obj)
    await db.flush()
    await _emit_audit(db, "vendor.created", "vendor", obj.id)
    return VendorOut(id=str(obj.id), **body.model_dump(), created_at=obj.created_at)


@router.delete("/vendors/{vendor_id}", status_code=204)
async def delete_vendor(vendor_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(DPDPVendorModel).where(DPDPVendorModel.id == uuid.UUID(vendor_id)))
    await _emit_audit(db, "vendor.deleted", "vendor", vendor_id)


# ═══════════════════════════════════════════════════════════════════════════════
# DPDP Audit Events
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/audit", response_model=List[AuditEventOut])
async def list_dpdp_audit(limit: int = 100, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(DPDPAuditEventModel)
        .where(DPDPAuditEventModel.tenant_id == DEMO_TENANT)
        .order_by(DPDPAuditEventModel.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return [AuditEventOut(id=r.id, actor=r.actor, action=r.action,
                          entity_type=r.entity_type, entity_id=r.entity_id,
                          details=r.details or {}, created_at=r.created_at) for r in rows]

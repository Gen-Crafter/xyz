import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, Text, DateTime,
    ForeignKey, JSON, BigInteger, Index
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, INET, JSONB
from app.core.database import Base


class InterceptionModel(Base):
    __tablename__ = "interceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_ip = Column(String(45), nullable=False)
    destination = Column(Text, nullable=False)
    endpoint = Column(Text, default="")
    direction = Column(String(10), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    data_classifications = Column(ARRAY(String), default=[])
    entities_detected = Column(JSONB, default=[])
    regulations_applicable = Column(ARRAY(String), default=[])
    risk_score = Column(Integer, default=0)
    action_taken = Column(String(10), nullable=False)
    policies_triggered = Column(ARRAY(String), default=[])
    justification = Column(Text, default="")
    processing_time_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ── Multi-tenant Users ──────────────────────────────────────────────────────


class TenantModel(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_tenants_name", "name", unique=True),
    )


class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(320), nullable=False, unique=True, index=True)
    full_name = Column(String(200), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_users_tenant", "tenant_id"),
    )


class CategoryModel(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False)
    icon = Column(String(100), default="category")
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_categories_tenant", "tenant_id"),
        Index("idx_categories_slug_tenant", "slug", "tenant_id", unique=True),
    )


class IdentityProviderModel(Base):
    __tablename__ = "identity_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    provider_type = Column(String(20), nullable=False)  # ldap, saml, oidc
    is_active = Column(Boolean, default=True)
    config = Column(JSONB, nullable=False, default={})
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_count = Column(Integer, default=0)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_idp_tenant", "tenant_id"),
    )


class PolicyModel(Base):
    __tablename__ = "policies"

    id = Column(String(50), primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text, default="")
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)
    regulation = Column(String(20), default="")
    conditions = Column(JSONB, nullable=False)
    action = Column(String(10), nullable=False)
    redaction_strategy = Column(JSONB, nullable=True)
    notification = Column(JSONB, nullable=True)
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_policies_regulation", "regulation"),
        Index("idx_policies_enabled", "enabled"),
    )


class AIEndpointModel(Base):
    __tablename__ = "ai_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pattern = Column(Text, nullable=False)
    provider = Column(String(50), default="")
    enabled = Column(Boolean, default=True)
    default_action = Column(String(10), default="AUDIT")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MCPDeploymentModel(Base):
    """AI deployment registered for MCP-based compliance scanning."""
    __tablename__ = "mcp_deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    framework = Column(String(50), default="custom")      # langchain, crewai, autogen, openai, custom
    environment = Column(String(30), default="development") # development, staging, production
    api_key = Column(String(64), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    default_action = Column(String(10), default="AUDIT")   # AUDIT, BLOCK, ALLOW
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    total_scans = Column(Integer, default=0)
    total_violations = Column(Integer, default=0)
    config = Column(JSONB, nullable=False, default={})     # extra framework-specific config
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_mcp_deploy_tenant", "tenant_id"),
        Index("idx_mcp_deploy_api_key", "api_key", unique=True),
    )


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    interception_id = Column(UUID(as_uuid=True), ForeignKey("interceptions.id"), nullable=True)
    event_type = Column(String(50), nullable=False)
    details = Column(JSONB, default={})
    previous_hash = Column(String(64), nullable=True)
    current_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_audit_log_created", "created_at"),
    )


class ClassificationRuleModel(Base):
    __tablename__ = "classification_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    category = Column(String(20), nullable=False)
    pattern = Column(Text, nullable=True)
    keywords = Column(ARRAY(String), default=[])
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AgentRequestModel(Base):
    """Stores producer agent pipeline results for compliance monitoring."""
    __tablename__ = "agent_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(Text, nullable=False)
    source_app = Column(String(100), default="")
    user_name = Column(String(200), default="")
    industry = Column(String(100), default="")
    status = Column(String(20), default="COMPLETED")
    user_input = Column(Text, default="")
    tool_chain = Column(JSONB, default=[])
    final_output = Column(JSONB, default={})
    metadata_info = Column(JSONB, default={})
    # Compliance scan results
    compliance_status = Column(String(20), default="PENDING")  # PENDING, CLEAN, VIOLATION
    violations = Column(JSONB, default=[])
    data_classifications = Column(ARRAY(String), default=[])
    regulations_applicable = Column(ARRAY(String), default=[])
    risk_score = Column(Integer, default=0)
    policies_triggered = Column(ARRAY(String), default=[])
    recommended_action = Column(String(20), default="AUDIT")
    scan_summary = Column(Text, default="")
    processing_time_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_agent_requests_created", "created_at"),
        Index("idx_agent_requests_status", "compliance_status"),
        Index("idx_agent_requests_source_app", "source_app"),
    )


class BlockedAgentModel(Base):
    """Tracks agents (source_app) that have been blocked due to violations."""
    __tablename__ = "blocked_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_app = Column(String(100), nullable=False, unique=True, index=True)
    reason = Column(Text, default="")
    blocked_request_id = Column(String(100), default="")
    blocked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ── DPDP Compliance Models ───────────────────────────────────────────────────


class DPDPSystemModel(Base):
    """Registered systems/applications that process personal data."""
    __tablename__ = "dpdp_systems"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    owner = Column(String(200), default="")
    description = Column(Text, default="")
    purposes = Column(ARRAY(String), default=[])
    data_flow_tags = Column(ARRAY(String), default=[])
    risk_level = Column(String(20), default="LOW")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_dpdp_systems_tenant", "tenant_id"),
    )


class DPDPDatasetModel(Base):
    """Datasets within a system that may contain personal data."""
    __tablename__ = "dpdp_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    system_id = Column(UUID(as_uuid=True), ForeignKey("dpdp_systems.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(50), default="general")
    pii_fields = Column(ARRAY(String), default=[])
    purposes = Column(ARRAY(String), default=[])
    risk_score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_dpdp_datasets_tenant", "tenant_id"),
        Index("idx_dpdp_datasets_system", "system_id"),
    )


class DPDPFieldModel(Base):
    """Individual fields tagged with PII classification metadata."""
    __tablename__ = "dpdp_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("dpdp_datasets.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(200), nullable=False)
    data_type = Column(String(50), default="string")
    pii_type = Column(String(50), default="NONE")
    risk_score = Column(Integer, default=0)
    consent_required = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_dpdp_fields_dataset", "dataset_id"),
    )


class DPDPConsentModel(Base):
    """Consent records for data principals."""
    __tablename__ = "dpdp_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    principal_id = Column(String(200), nullable=False)
    purpose = Column(String(200), nullable=False)
    version = Column(String(50), default="1.0")
    status = Column(String(20), default="ACTIVE")
    policy_text_hash = Column(String(64), default="")
    evidence_ref = Column(Text, default="")
    captured_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_dpdp_consents_tenant", "tenant_id"),
        Index("idx_dpdp_consents_principal", "principal_id"),
        Index("idx_dpdp_consents_status", "status"),
    )


class DPDPRightsRequestModel(Base):
    """Data principal rights requests (access, correction, erasure, grievance, nomination)."""
    __tablename__ = "dpdp_rights_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    principal_id = Column(String(200), nullable=False)
    request_type = Column(String(30), nullable=False)
    status = Column(String(20), default="OPEN")
    description = Column(Text, default="")
    resolution = Column(Text, default="")
    sla_due = Column(DateTime(timezone=True), nullable=True)
    assigned_to = Column(String(200), default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_dpdp_rights_tenant", "tenant_id"),
        Index("idx_dpdp_rights_status", "status"),
    )


class DPDPBreachModel(Base):
    """Breach incidents tracked under DPDP."""
    __tablename__ = "dpdp_breaches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(300), nullable=False)
    severity = Column(String(20), default="MEDIUM")
    status = Column(String(20), default="REPORTED")
    description = Column(Text, default="")
    impacted_records = Column(Integer, default=0)
    data_categories = Column(ARRAY(String), default=[])
    root_cause = Column(Text, default="")
    remediation = Column(Text, default="")
    notified_board = Column(Boolean, default=False)
    notified_principals = Column(Boolean, default=False)
    regulator_packet_ref = Column(Text, default="")
    reported_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_dpdp_breaches_tenant", "tenant_id"),
        Index("idx_dpdp_breaches_status", "status"),
    )


class DPDPRetentionPolicyModel(Base):
    """Retention and deletion policies per purpose / system."""
    __tablename__ = "dpdp_retention_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    purpose = Column(String(200), default="")
    system_scope = Column(String(200), default="*")
    retention_days = Column(Integer, default=365)
    legal_hold = Column(Boolean, default=False)
    auto_delete = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_dpdp_retention_tenant", "tenant_id"),
    )


class DPDPVendorModel(Base):
    """Third-party vendors / data processors."""
    __tablename__ = "dpdp_vendors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    service_type = Column(String(100), default="")
    data_shared = Column(ARRAY(String), default=[])
    dpa_status = Column(String(20), default="PENDING")
    transfer_basis = Column(String(100), default="")
    review_due = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_dpdp_vendors_tenant", "tenant_id"),
    )


class DPDPAuditEventModel(Base):
    """DPDP-specific audit trail (1-year retention per Rule 6)."""
    __tablename__ = "dpdp_audit_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    actor = Column(String(200), default="system")
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), default="")
    entity_id = Column(String(200), default="")
    details = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_dpdp_audit_tenant", "tenant_id"),
        Index("idx_dpdp_audit_created", "created_at"),
    )

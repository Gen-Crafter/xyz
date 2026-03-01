from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    AUDIT = "AUDIT"


class Direction(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DataCategory(str, Enum):
    PII = "PII"
    PHI = "PHI"
    PCI = "PCI"
    CUSTOM = "CUSTOM"
    PUBLIC = "PUBLIC"


# ─── Entity Detection ────────────────────────────────────────────────────────

class DetectedEntity(BaseModel):
    type: str
    value: str
    position: list[int] = Field(default_factory=list)
    confidence: float = 1.0


class Violation(BaseModel):
    regulation: str
    section: str
    description: str
    severity: Severity


# ─── Intent Enum ────────────────────────────────────────────────────────────

class IntentType(str, Enum):
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    PREDICTION = "prediction"
    DECISION_SUPPORT = "decision_support"
    DOCUMENTATION = "documentation"
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    UNKNOWN = "unknown"


# ─── Step 1: Telemetry / Signal Collection ──────────────────────────────────

class TelemetrySignals(BaseModel):
    """Signals collected from the browser extension / client."""
    active_url: str = ""                          # e.g. chat.openai.com
    app_type: str = ""                            # external_ai | internal_ai | saas
    user_role: str = ""                           # HR | Doctor | Engineer | Finance
    device_time: Optional[str] = None             # e.g. "22:30"
    os: str = ""                                  # MacOS | Windows | Linux
    installed_tools: list[str] = Field(default_factory=list)  # ["Copilot", "Cursor"]
    prompt: str = ""                              # raw prompt text
    file_metadata: Optional[str] = None           # e.g. patient_record.pdf


# ─── Context Analysis ────────────────────────────────────────────────────────

class ContextAnalysisRequest(BaseModel):
    interception_id: str
    direction: Direction = Direction.OUTBOUND
    source_ip: str = "0.0.0.0"
    destination: str = ""
    endpoint: str = ""
    payload: dict = Field(default_factory=dict)
    signals: Optional[TelemetrySignals] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Step 5: Context Object (CIL Output) ───────────────────────────────────

class ContextObject(BaseModel):
    """The structured output of the Context Identification Layer."""
    context_id: str
    data_sensitivity: str = "NONE"                # PHI | PII | PCI | SECRET | NONE
    intent: IntentType = IntentType.UNKNOWN
    department: str = ""                          # oncology | HR | finance | engineering
    business_function: str = ""                   # HR | Finance | Clinical | Engineering
    data_processing_purpose: str = ""             # analytics | treatment | marketing
    llm_destination: str = ""                     # external | internal
    cross_border: bool = False
    regulatory_scope: list[str] = Field(default_factory=list)  # ["HIPAA_164.312", "GDPR_Art_5"]
    entities_detected: list[DetectedEntity] = Field(default_factory=list)
    confidence: float = 0.0


class ContextAnalysisResult(BaseModel):
    interception_id: str
    data_classifications: list[str] = Field(default_factory=list)
    entities_detected: list[DetectedEntity] = Field(default_factory=list)
    regulations_applicable: list[str] = Field(default_factory=list)
    violations: list[Violation] = Field(default_factory=list)
    risk_score: int = 0
    recommended_action: ActionType = ActionType.ALLOW
    confidence: float = 0.0
    rag_sources: list[str] = Field(default_factory=list)
    processing_time_ms: int = 0
    context_object: Optional[ContextObject] = None
    intent: IntentType = IntentType.UNKNOWN
    pipeline_stages: dict = Field(default_factory=dict)


# ─── Policy ──────────────────────────────────────────────────────────────────

class PolicyConditions(BaseModel):
    data_classifications: list[str] = Field(default_factory=list)
    direction: Optional[str] = None
    destination_type: Optional[str] = None
    patterns: list[str] = Field(default_factory=list)
    blocked_keywords: list[str] = Field(default_factory=list)


class PolicyNotification(BaseModel):
    notify_user: bool = True
    notify_admin: bool = True
    message: str = ""


class RedactionStrategy(BaseModel):
    method: str = "token_replacement"  # token_replacement, generalization, synthetic, hashing
    config: dict = Field(default_factory=dict)


class PolicyCreate(BaseModel):
    id: Optional[str] = None
    name: str
    description: str = ""
    enabled: bool = True
    priority: int = 100
    regulation: str = ""
    conditions: PolicyConditions
    action: ActionType
    redaction_strategy: Optional[RedactionStrategy] = None
    notification: Optional[PolicyNotification] = None


class PolicyResponse(PolicyCreate):
    created_by: str = "system"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyTestRequest(BaseModel):
    payload_text: str
    policy_ids: list[str] = Field(default_factory=list)


class PolicyTestResult(BaseModel):
    triggered_policies: list[str]
    action: ActionType
    details: str


# ─── AI Endpoint ─────────────────────────────────────────────────────────────

class AIEndpointCreate(BaseModel):
    pattern: str
    provider: str = ""
    enabled: bool = True
    default_action: ActionType = ActionType.AUDIT


class AIEndpointResponse(AIEndpointCreate):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Classification Rule ────────────────────────────────────────────────────

class ClassificationRuleCreate(BaseModel):
    name: str
    category: DataCategory
    pattern: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    enabled: bool = True


class ClassificationRuleResponse(ClassificationRuleCreate):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Audit Log ───────────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    id: int
    interception_id: Optional[str] = None
    event_type: str
    details: dict = Field(default_factory=dict)
    previous_hash: Optional[str] = None
    current_hash: str
    created_at: datetime


# ─── Interception ────────────────────────────────────────────────────────────

class InterceptionRecord(BaseModel):
    id: str
    source_ip: str
    destination: str
    endpoint: str = ""
    direction: Direction
    data_classifications: list[str] = Field(default_factory=list)
    entities_detected: list[DetectedEntity] = Field(default_factory=list)
    regulations_applicable: list[str] = Field(default_factory=list)
    risk_score: int = 0
    action_taken: ActionType
    policies_triggered: list[str] = Field(default_factory=list)
    justification: str = ""
    processing_time_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Dashboard ───────────────────────────────────────────────────────────────

class DashboardKPIs(BaseModel):
    total_interceptions: int = 0
    total_blocked: int = 0
    total_redacted: int = 0
    total_allowed: int = 0
    total_audited: int = 0
    compliance_score: float = 100.0
    active_policies: int = 0
    active_endpoints: int = 0
    avg_processing_time_ms: float = 0.0


class ProxyStatus(BaseModel):
    status: str = "active"
    uptime_seconds: int = 0
    active_connections: int = 0
    total_intercepted: int = 0
    total_blocked: int = 0
    total_redacted: int = 0
    ai_endpoints_monitored: int = 0


# ─── RAG ─────────────────────────────────────────────────────────────────────

# ─── Agent Request (Producer) ─────────────────────────────────────────────

class ToolExecution(BaseModel):
    tool_name: str
    description: str = ""
    sequence: int = 0
    input: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)
    reasoning: str = ""
    duration_ms: int = 0
    status: str = "SUCCESS"


class AgentRequestCreate(BaseModel):
    request_id: str
    title: str
    source_app: str = ""
    user_name: str = ""
    industry: str = ""
    status: str = "COMPLETED"
    user_input: str = ""
    tool_chain: list[ToolExecution] = Field(default_factory=list)
    final_output: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class ToolViolation(BaseModel):
    tool_name: str
    tool_sequence: int = 0
    field: str = ""  # "input" or "output"
    violation_type: str = ""  # PII, PHI, PCI, SECRET
    regulation: str = ""  # GDPR, HIPAA, PCI-DSS
    article: str = ""  # e.g. "GDPR Art. 6", "HIPAA §164.502"
    description: str = ""
    severity: Severity = Severity.MEDIUM
    entities: list[str] = Field(default_factory=list)


class AgentRequestResponse(BaseModel):
    id: str
    request_id: str
    title: str
    source_app: str = ""
    user_name: str = ""
    industry: str = ""
    status: str = "COMPLETED"
    user_input: str = ""
    tool_chain: list[dict] = Field(default_factory=list)
    final_output: dict = Field(default_factory=dict)
    metadata_info: dict = Field(default_factory=dict)
    compliance_status: str = "PENDING"
    violations: list[dict] = Field(default_factory=list)
    data_classifications: list[str] = Field(default_factory=list)
    regulations_applicable: list[str] = Field(default_factory=list)
    risk_score: int = 0
    policies_triggered: list[str] = Field(default_factory=list)
    scan_summary: str = ""
    processing_time_ms: int = 0
    created_at: Optional[datetime] = None


# ─── RAG ─────────────────────────────────────────────────────────────────────

class RAGIngestRequest(BaseModel):
    source: str = "all"  # all, local, remote


class RAGQueryRequest(BaseModel):
    query: str
    regulations_filter: list[str] = Field(default_factory=list)
    top_k: int = 5


class RAGQueryResult(BaseModel):
    query: str
    chunks: list[dict] = Field(default_factory=list)
    llm_synthesis: Optional[str] = None
    processing_time_ms: int = 0


class RAGCollectionStats(BaseModel):
    collection_name: str
    document_count: int
    embedding_dim: int = 384

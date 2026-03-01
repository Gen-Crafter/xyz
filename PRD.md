# Product Requirements Document (PRD)

## AI Governance Proxy — Context-Aware Compliance Interception Layer

---

## Document Control

| Attribute | Details |
|---|---|
| Document Version | 1.0 |
| Created Date | February 23, 2026 |
| Project Code | AIGP-HC-2026 |
| Classification | Internal — Hackathon Implementation |
| Parent Project | CAICL (Compliance-Aware Intelligent Control Layer) |
| Anaqua Reference | 147675 |

---

## 1. Executive Summary

Build a **transparent MITM (Man-In-The-Middle) proxy** that intercepts all AI agent traffic (ChatGPT, Copilot, custom LLM apps) flowing from enterprise VMs, applies real-time **context detection** using a RAG-powered compliance engine, and **filters or modifies** requests/responses that violate configured governance policies (GDPR, HIPAA, PCI-DSS).

The system provides a **management UI** to configure rules, policies, data classification mappings, and view real-time interception logs, audit trails, and compliance posture dashboards.

### Value Proposition

- **Transparent enforcement**: No application changes needed — the proxy sits at the network layer
- **AI-powered detection**: RAG + LLM pipeline detects nuanced compliance conflicts that regex/rule-based systems miss
- **Real-time filtering**: Sub-second interception, classification, and policy enforcement on live AI traffic
- **Centralized governance**: Single pane of glass to configure, monitor, and audit all AI interactions across the enterprise

### Architecture Overview (from Design Diagram)

```
┌───────────┐   ┌───────────┐
│  ChatGPT  │   │  AI Apps  │
└─────┬─────┘   └─────┬─────┘
      │               │
      └───────┬───────┘
              │
        ┌─────▼─────┐
        │   Agent   │  (Browser/Application in VM)
        └─────┬─────┘
              │
        ┌─────▼──────┐
        │   Proxy    │  (MITM - Intercepts all traffic)
        │   (PAC)    │
        └─────┬──────┘
              │
     ┌────────▼─────────┐
     │  Proxy Router    │
     │  (MITM Engine)   │
     └───┬─────────┬────┘
         │         │
   ┌─────▼───┐ ┌───▼──────────┐
   │   UI    │ │Context       │
   │ (Admin) │ │Detector      │
   └─────────┘ │(RAG + LLM)  │
               └───┬──────────┘
                   │
              ┌────▼─────┐
              │  Filter  │
              │  Agent   │
              └────┬─────┘
                   │
              ┌────▼─────┐
              │  Policy  │
              │  Engine  │
              └──────────┘
```

---

## 2. Problem Statement

### 2.1 Core Challenges

| Problem | Enterprise Impact |
|---|---|
| **Uncontrolled AI data leakage** | Employees paste PII/PHI/cardholder data into ChatGPT, Copilot, or custom AI tools — no interception point exists |
| **No visibility into AI interactions** | CISOs have zero insight into what data flows to external AI providers from enterprise VMs |
| **Reactive compliance** | Violations discovered weeks/months after occurrence; average detection time is 47 days |
| **Policy enforcement gap** | Rules exist on paper but no technical mechanism enforces them at the network layer for AI traffic |
| **Conflicting regulations** | GDPR right-to-erasure vs HIPAA 6-year retention; PCI-DSS masking vs GDPR explainability — manual resolution takes weeks |

### 2.2 Why a Proxy-Based Approach

Traditional endpoint DLP solutions fail for AI traffic because:

1. **AI prompts are natural language** — regex patterns miss contextual violations (e.g., "my patient John Smith has diabetes" doesn't match PII regex but clearly contains PHI)
2. **AI responses may contain reconstructed sensitive data** — the model could infer and return PII not present in the prompt
3. **New AI tools appear daily** — endpoint agents can't keep up; a proxy intercepts ALL traffic regardless of application
4. **Cloud-native AI services use HTTPS** — only MITM proxy can inspect encrypted payloads

---

## 3. Solution Architecture

### 3.1 Component Overview

#### 3.1.1 MITM Proxy Engine
- Intercepts HTTP/HTTPS traffic from VMs configured with PAC (Proxy Auto-Configuration)
- Performs TLS termination to inspect encrypted AI API calls
- Routes intercepted requests through the Context Detection pipeline
- Forwards clean/modified requests to destination or blocks them entirely

#### 3.1.2 Context Detector (RAG + LLM)
- Analyzes intercepted request/response payloads using a multi-stage pipeline:
  1. **Fast classifier** — regex + keyword scan for known patterns (SSN, credit card, medical codes)
  2. **Embedding similarity** — compare payload against known sensitive data patterns in ChromaDB
  3. **LLM analysis** — deep contextual analysis for nuanced violations (LangChain agent with tools)
- RAG knowledge base contains regulation texts (GDPR, HIPAA, PCI-DSS) for grounded analysis

#### 3.1.3 Filter Agent (LangGraph Workflow)
- Multi-step LangGraph state machine that decides action based on Context Detector output:
  - **ALLOW** — clean traffic, forward as-is
  - **REDACT** — mask/tokenize sensitive data, forward modified request
  - **BLOCK** — reject request entirely, return policy violation message to user
  - **AUDIT** — allow but flag for human review
- Each decision is logged with full justification chain

#### 3.1.4 Policy Engine
- Rule repository storing compliance policies in structured format
- Supports GDPR, HIPAA, PCI-DSS out of the box
- Custom policy creation via UI
- Policy evaluation against detected context to determine action

#### 3.1.5 Admin UI (Angular 20)
- Dashboard with real-time interception metrics
- Policy configuration CRUD (rules, data classifications, actions)
- Audit log viewer with search/filter
- RAG knowledge base management (ingest, browse, test queries)
- Compliance posture visualization

### 3.2 Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Proxy Engine** | mitmproxy 11+ (Python) | MITM HTTP/HTTPS interception with scriptable hooks |
| **Backend API** | FastAPI 0.115+ | REST API, WebSocket real-time events |
| **LLM Orchestration** | LangChain 0.3+ | Agent workflows, prompt templates, tool calling |
| **Agent Workflows** | LangGraph 0.3+ | Stateful filter agent with decision graph |
| **RAG Framework** | LlamaIndex 0.12+ | Document ingestion, indexing, retrieval pipelines |
| **Vector Database** | ChromaDB 1.5+ | Regulation embeddings, sensitive data pattern store |
| **Embedding Model** | sentence-transformers/all-MiniLM-L6-v2 | 384-dim local embeddings |
| **LLM** | Llama 3.3 70B (self-hosted) / local fallback | Policy reasoning, context analysis |
| **Frontend** | Angular 20 | Admin dashboard, policy management UI |
| **State Management** | Angular Signals + RxJS | Reactive state, real-time WebSocket streams |
| **UI Components** | Angular Material 19+ | Tables, dialogs, forms, cards |
| **Charts** | Apache ECharts 5.6+ | Compliance trends, interception volume, risk heatmaps |
| **Database** | PostgreSQL 17+ | Audit logs, policies, interception history |
| **Cache / PubSub** | Redis 7.4+ | Real-time event streaming, interception queue |
| **Deployment** | Docker Compose | Multi-container orchestration |

---

## 4. Functional Requirements

### 4.1 Module 1: Proxy Interception Engine

**Purpose**: Transparently intercept all HTTP/HTTPS traffic from configured VMs and route AI-related requests through the compliance pipeline.

#### 4.1.1 Core Capabilities

- **PAC-based configuration**: VMs use a PAC file to route traffic through the proxy — no app changes needed
- **TLS interception**: Generate and install a CA certificate for HTTPS inspection
- **AI endpoint detection**: Identify requests to known AI services (OpenAI, Anthropic, Google AI, Azure OpenAI, HuggingFace, custom endpoints)
- **Selective interception**: Only AI-related traffic goes through the compliance pipeline; other traffic passes through directly
- **Request/Response capture**: Full payload capture for both outbound prompts and inbound AI responses

#### 4.1.2 Supported AI Endpoints (Default)

```json
{
  "ai_endpoints": [
    {"pattern": "api.openai.com/*", "provider": "OpenAI"},
    {"pattern": "api.anthropic.com/*", "provider": "Anthropic"},
    {"pattern": "generativelanguage.googleapis.com/*", "provider": "Google"},
    {"pattern": "*.openai.azure.com/*", "provider": "Azure OpenAI"},
    {"pattern": "api-inference.huggingface.co/*", "provider": "HuggingFace"}
  ]
}
```

#### 4.1.3 API Specification

**Proxy Configuration Endpoint**: `GET /api/v1/proxy/pac`

Returns PAC file for VM auto-configuration:
```javascript
function FindProxyForURL(url, host) {
  // Route AI traffic through compliance proxy
  if (shExpMatch(host, "api.openai.com") ||
      shExpMatch(host, "api.anthropic.com") ||
      shExpMatch(host, "*.openai.azure.com")) {
    return "PROXY proxy-host:8080";
  }
  return "DIRECT";
}
```

**Proxy Status Endpoint**: `GET /api/v1/proxy/status`

```json
{
  "status": "active",
  "uptime_seconds": 86400,
  "active_connections": 12,
  "total_intercepted": 45892,
  "total_blocked": 234,
  "total_redacted": 1891,
  "ai_endpoints_monitored": 6
}
```

### 4.2 Module 2: Context Detector (RAG-Powered)

**Purpose**: Analyze intercepted AI traffic payloads to detect sensitive data, classify content, and identify compliance conflicts using a multi-stage RAG pipeline.

#### 4.2.1 Detection Pipeline (3 Stages)

**Stage 1 — Fast Scan (< 10ms)**
- Regex patterns for structured PII: SSN, credit cards, phone numbers, email, medical record numbers
- Keyword lists for sensitive terms: disease names, drug names, financial terms
- Output: list of detected entities with types and positions

**Stage 2 — Embedding Similarity (< 100ms)**
- Embed the payload text using sentence-transformers
- Query ChromaDB for similar sensitive data patterns
- Compare against known violation patterns stored in vector DB
- Output: similarity scores against known violation categories

**Stage 3 — LLM Contextual Analysis (< 2s)**
- LangChain agent with tools analyzes the full context
- Tools available to the agent:
  - `search_regulations` — RAG query against GDPR/HIPAA/PCI-DSS knowledge base
  - `classify_data` — determine data classification (PII, PHI, PCI, public)
  - `check_policy` — evaluate against active policies
  - `assess_risk` — calculate risk score for this interception
- Output: structured analysis with data classification, applicable regulations, risk score, recommended action

#### 4.2.2 RAG Knowledge Base

**Collections in ChromaDB:**

| Collection | Content | Chunks | Purpose |
|---|---|---|---|
| `regulations` | GDPR, HIPAA, PCI-DSS full texts | ~3,500 | Ground LLM analysis in actual regulation text |
| `violation_patterns` | Known violation examples | ~500 | Embedding similarity matching for fast detection |
| `policy_templates` | Pre-built policy templates | ~200 | Seed data for policy configuration |
| `sensitive_data_patterns` | PII/PHI/PCI data patterns | ~300 | Pattern library for context detection |

**Ingestion Pipeline (LlamaIndex)**:
1. Parse regulation PDFs/HTML using LlamaIndex document loaders
2. Chunk with `SentenceWindowNodeParser` (window_size=3, 512 tokens)
3. Generate embeddings with local sentence-transformers
4. Store in ChromaDB with metadata (regulation, article, section, category)
5. Build LlamaIndex `VectorStoreIndex` for retrieval

#### 4.2.3 API Specification

**Analyze Payload Endpoint**: `POST /api/v1/context/analyze`

Request:
```json
{
  "interception_id": "INT-20260223-001",
  "direction": "outbound",
  "source_ip": "10.0.1.45",
  "destination": "api.openai.com",
  "endpoint": "/v1/chat/completions",
  "payload": {
    "model": "gpt-4",
    "messages": [
      {
        "role": "user",
        "content": "Summarize the medical history for patient John Smith, DOB 03/15/1987, MRN 445129. He was diagnosed with Type 2 Diabetes (E11.9) and prescribed Metformin 500mg."
      }
    ]
  },
  "timestamp": "2026-02-23T11:30:00Z"
}
```

Response:
```json
{
  "interception_id": "INT-20260223-001",
  "analysis": {
    "data_classifications": ["PHI", "PII"],
    "entities_detected": [
      {"type": "PERSON_NAME", "value": "John Smith", "position": [48, 58]},
      {"type": "DATE_OF_BIRTH", "value": "03/15/1987", "position": [64, 74]},
      {"type": "MEDICAL_RECORD_NUMBER", "value": "445129", "position": [80, 86]},
      {"type": "ICD10_CODE", "value": "E11.9", "position": [121, 126]},
      {"type": "MEDICATION", "value": "Metformin 500mg", "position": [142, 157]}
    ],
    "regulations_applicable": ["HIPAA", "GDPR"],
    "violations": [
      {
        "regulation": "HIPAA",
        "section": "45 CFR §164.502",
        "description": "PHI transmitted to external AI service without BAA or patient authorization",
        "severity": "CRITICAL"
      },
      {
        "regulation": "GDPR",
        "section": "Article 9",
        "description": "Special category health data processed without explicit consent for AI processing",
        "severity": "HIGH"
      }
    ],
    "risk_score": 95,
    "recommended_action": "BLOCK",
    "confidence": 0.97,
    "rag_sources": [
      "HIPAA 45 CFR §164.502 - Uses and Disclosures",
      "GDPR Article 9 - Processing Special Categories of Data",
      "HIPAA 45 CFR §164.514 - De-identification Standard"
    ]
  },
  "processing_time_ms": 487
}
```

### 4.3 Module 3: Filter Agent (LangGraph Workflow)

**Purpose**: Execute policy-driven actions on intercepted traffic based on Context Detector output.

#### 4.3.1 Filter Decision Graph (LangGraph)

```
                    ┌─────────────┐
                    │  Intercept  │
                    │  Received   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Context   │
                    │  Detector   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Policy    │
               ┌────┤  Evaluator  ├────┐
               │    └──────┬──────┘    │
               │           │           │
        ┌──────▼──┐ ┌──────▼──┐ ┌──────▼──┐
        │  ALLOW  │ │ REDACT  │ │  BLOCK  │
        └──────┬──┘ └──────┬──┘ └──────┬──┘
               │           │           │
               │    ┌──────▼──┐        │
               │    │ Redact  │        │
               │    │ Engine  │        │
               │    └──────┬──┘        │
               │           │           │
        ┌──────▼───────────▼───────────▼──┐
        │          Audit Logger            │
        └──────────────┬──────────────────┘
                       │
                ┌──────▼──────┐
                │  Forward /  │
                │  Respond    │
                └─────────────┘
```

#### 4.3.2 Action Types

| Action | Description | Payload Modification |
|---|---|---|
| **ALLOW** | Traffic is compliant, forward as-is | None |
| **REDACT** | Sensitive data detected, mask and forward | Replace PII/PHI with tokens: `[REDACTED:NAME]`, `[REDACTED:DOB]`, etc. |
| **BLOCK** | Critical violation, reject request | Return 403 with policy violation message to the calling application |
| **AUDIT** | Borderline case, allow but flag | None (logged for human review) |

#### 4.3.3 Redaction Engine

Supports multiple redaction strategies:

- **Token replacement**: `John Smith` → `[REDACTED:PERSON_NAME]`
- **Generalization**: `03/15/1987` → `1987` (year only)
- **Synthetic substitution**: `John Smith` → `Jane Doe` (fake but realistic)
- **Hashing**: `MRN 445129` → `MRN SHA256:a3f2...`

Strategy is configurable per data type per policy.

#### 4.3.4 LangGraph State Definition

```python
from typing import TypedDict, Literal

class FilterState(TypedDict):
    interception_id: str
    payload: dict
    context_analysis: dict          # Output from Context Detector
    applicable_policies: list[dict]
    decision: Literal["ALLOW", "REDACT", "BLOCK", "AUDIT"]
    redacted_payload: dict | None
    justification: str
    audit_entry: dict
```

### 4.4 Module 4: Policy Engine

**Purpose**: Manage compliance rules that govern how the Filter Agent acts on detected context.

#### 4.4.1 Policy Data Model

```json
{
  "policy_id": "POL-HIPAA-PHI-001",
  "name": "Block PHI to External AI Services",
  "description": "Prevent Protected Health Information from being sent to AI services without BAA",
  "enabled": true,
  "priority": 1,
  "regulation": "HIPAA",
  "conditions": {
    "data_classifications": ["PHI"],
    "direction": "outbound",
    "destination_type": "external_ai",
    "has_baa": false
  },
  "action": "BLOCK",
  "redaction_strategy": null,
  "notification": {
    "notify_user": true,
    "notify_admin": true,
    "message": "This request was blocked because it contains Protected Health Information (PHI). HIPAA regulations prohibit sending PHI to external AI services without a Business Associate Agreement."
  },
  "created_at": "2026-02-23T10:00:00Z",
  "updated_at": "2026-02-23T10:00:00Z",
  "created_by": "admin"
}
```

#### 4.4.2 Default Policies (Shipped Out-of-Box)

| Policy ID | Regulation | Trigger | Action |
|---|---|---|---|
| POL-HIPAA-PHI-001 | HIPAA | PHI sent to external AI without BAA | BLOCK |
| POL-HIPAA-PHI-002 | HIPAA | PHI in AI response from non-covered entity | REDACT |
| POL-GDPR-PII-001 | GDPR | EU citizen PII sent to non-EU AI service | BLOCK |
| POL-GDPR-PII-002 | GDPR | PII without explicit consent for AI processing | REDACT |
| POL-GDPR-ART17-001 | GDPR | Data subject exercised right to erasure | BLOCK |
| POL-PCI-PAN-001 | PCI-DSS | Credit card PAN in any AI request | REDACT |
| POL-PCI-CVV-001 | PCI-DSS | CVV/CVC in any AI traffic | BLOCK |
| POL-PCI-PAN-002 | PCI-DSS | More than last-4 digits of PAN exposed | REDACT |
| POL-GENERAL-001 | Internal | SSN detected in any AI traffic | REDACT |
| POL-GENERAL-002 | Internal | Password/secret/API key in AI traffic | BLOCK |

#### 4.4.3 Policy CRUD API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/policies` | List all policies (paginated, filterable) |
| POST | `/api/v1/policies` | Create new policy |
| GET | `/api/v1/policies/{id}` | Get policy details |
| PUT | `/api/v1/policies/{id}` | Update policy |
| DELETE | `/api/v1/policies/{id}` | Delete policy |
| POST | `/api/v1/policies/{id}/toggle` | Enable/disable policy |
| POST | `/api/v1/policies/test` | Test policy against sample payload |

### 4.5 Module 5: Admin UI (Angular 20)

**Purpose**: Web-based management interface for configuring policies, monitoring interceptions, and viewing compliance posture.

#### 4.5.1 Views / Pages

**1. Dashboard (Home)**
- Real-time interception volume (line chart — last 24h)
- Action breakdown (pie chart — ALLOW / REDACT / BLOCK / AUDIT)
- Top violated policies (bar chart)
- Active connections count
- Compliance score gauge (% of traffic that required no intervention)
- Recent critical alerts feed

**2. Live Interception Monitor**
- Real-time scrolling feed of interceptions (WebSocket)
- Color-coded by action: green=ALLOW, yellow=REDACT, orange=AUDIT, red=BLOCK
- Expandable cards showing:
  - Source IP, destination, timestamp
  - Detected entities
  - Applicable policies triggered
  - Action taken with justification
  - Full request/response payload (redacted view)
- Filters: by action, regulation, source IP, time range

**3. Policy Management**
- CRUD interface for policies
- Policy form with:
  - Name, description, regulation
  - Condition builder (data classification, direction, destination)
  - Action selector (ALLOW/REDACT/BLOCK/AUDIT)
  - Redaction strategy config (if REDACT)
  - Notification settings
  - Priority ordering
- Policy testing: paste sample payload → see what policies trigger
- Import/export policies as JSON

**4. AI Endpoint Configuration**
- Manage list of monitored AI endpoints
- Add custom endpoints (internal AI services)
- Enable/disable per endpoint
- Configure per-endpoint default action

**5. Data Classification Rules**
- Configure what constitutes PII, PHI, PCI data
- Custom entity types
- Regex patterns + NER model configuration
- Test classification against sample text

**6. Audit Log**
- Searchable, filterable log of all interceptions
- Export as CSV/PDF for compliance auditors
- Retention policy configuration
- Tamper-evident hash chain verification

**7. RAG Knowledge Base**
- View ingested regulation documents
- Trigger manual ingestion
- Test RAG queries
- View chunk counts and embedding statistics

**8. Compliance Reports**
- Compliance posture over time (trend charts)
- Per-regulation breakdown
- Violation heat maps (by time of day, department, AI service)
- One-click exportable audit report
- Compliance score history

**9. Settings**
- Proxy configuration (port, TLS certificate management)
- LLM provider configuration (self-hosted model)
- Notification channels (email, Slack/Teams webhooks)
- User management and RBAC

#### 4.5.2 UI Architecture

```
src/
├── app/
│   ├── core/                      # Singleton services, guards, interceptors
│   │   ├── services/
│   │   │   ├── api.service.ts          # HTTP client wrapper
│   │   │   ├── websocket.service.ts    # WebSocket connection manager
│   │   │   ├── auth.service.ts         # Authentication
│   │   │   └── notification.service.ts # Toast/alert notifications
│   │   ├── guards/
│   │   │   └── auth.guard.ts
│   │   └── interceptors/
│   │       └── auth.interceptor.ts
│   ├── features/                  # Feature modules (lazy-loaded routes)
│   │   ├── dashboard/
│   │   │   ├── dashboard.component.ts
│   │   │   ├── widgets/
│   │   │   │   ├── interception-volume-chart.component.ts
│   │   │   │   ├── action-breakdown-chart.component.ts
│   │   │   │   ├── compliance-score-gauge.component.ts
│   │   │   │   └── critical-alerts-feed.component.ts
│   │   │   └── dashboard.routes.ts
│   │   ├── live-monitor/
│   │   │   ├── live-monitor.component.ts
│   │   │   ├── interception-card.component.ts
│   │   │   └── live-monitor.routes.ts
│   │   ├── policies/
│   │   │   ├── policy-list.component.ts
│   │   │   ├── policy-form.component.ts
│   │   │   ├── policy-test.component.ts
│   │   │   └── policies.routes.ts
│   │   ├── endpoints/
│   │   │   ├── endpoint-list.component.ts
│   │   │   └── endpoints.routes.ts
│   │   ├── classifications/
│   │   │   ├── classification-rules.component.ts
│   │   │   └── classifications.routes.ts
│   │   ├── audit-log/
│   │   │   ├── audit-log.component.ts
│   │   │   └── audit-log.routes.ts
│   │   ├── knowledge-base/
│   │   │   ├── knowledge-base.component.ts
│   │   │   ├── rag-query-tester.component.ts
│   │   │   └── knowledge-base.routes.ts
│   │   ├── reports/
│   │   │   ├── compliance-reports.component.ts
│   │   │   └── reports.routes.ts
│   │   └── settings/
│   │       ├── settings.component.ts
│   │       └── settings.routes.ts
│   ├── shared/                    # Shared components, pipes, directives
│   │   ├── components/
│   │   │   ├── sidebar.component.ts
│   │   │   ├── header.component.ts
│   │   │   ├── data-table.component.ts
│   │   │   └── severity-badge.component.ts
│   │   └── pipes/
│   │       ├── time-ago.pipe.ts
│   │       └── truncate.pipe.ts
│   ├── app.component.ts
│   ├── app.routes.ts
│   └── app.config.ts
├── assets/
├── environments/
└── styles.scss
```

---

## 5. Backend Architecture

### 5.1 Project Structure

```
governance-server/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── proxy.py           # Proxy management endpoints
│   │   │   │   ├── context.py         # Context detection endpoints
│   │   │   │   ├── filter.py          # Filter agent endpoints
│   │   │   │   ├── policies.py        # Policy CRUD endpoints
│   │   │   │   ├── endpoints.py       # AI endpoint config endpoints
│   │   │   │   ├── classifications.py # Data classification endpoints
│   │   │   │   ├── audit.py           # Audit log endpoints
│   │   │   │   ├── rag.py             # RAG management endpoints
│   │   │   │   ├── reports.py         # Compliance report endpoints
│   │   │   │   └── dashboard.py       # Dashboard KPI endpoints
│   │   │   └── websocket.py           # WebSocket handlers
│   │   ├── core/
│   │   │   ├── config.py              # Environment configuration
│   │   │   ├── database.py            # PostgreSQL connection
│   │   │   ├── redis.py               # Redis client
│   │   │   └── security.py            # Auth middleware
│   │   ├── services/
│   │   │   ├── proxy_service.py       # mitmproxy integration
│   │   │   ├── context_detector.py    # 3-stage detection pipeline
│   │   │   ├── filter_agent.py        # LangGraph filter workflow
│   │   │   ├── policy_engine.py       # Policy evaluation logic
│   │   │   ├── rag_service.py         # LlamaIndex RAG pipeline
│   │   │   ├── redaction_service.py   # Data redaction engine
│   │   │   ├── llm_service.py         # LLM client (self-hosted / local)
│   │   │   └── audit_service.py       # Audit logging with hash chain
│   │   ├── agents/
│   │   │   ├── context_agent.py       # LangChain agent for context analysis
│   │   │   ├── filter_graph.py        # LangGraph filter decision graph
│   │   │   └── tools/
│   │   │       ├── regulation_search.py    # RAG search tool
│   │   │       ├── data_classifier.py      # Classification tool
│   │   │       ├── policy_checker.py       # Policy evaluation tool
│   │   │       └── risk_assessor.py        # Risk scoring tool
│   │   ├── models/
│   │   │   ├── interception.py        # Interception Pydantic models
│   │   │   ├── policy.py              # Policy Pydantic models
│   │   │   ├── context.py             # Context analysis models
│   │   │   ├── audit.py               # Audit log models
│   │   │   └── endpoint.py            # AI endpoint config models
│   │   ├── proxy/
│   │   │   ├── mitm_addon.py          # mitmproxy addon script
│   │   │   └── pac_generator.py       # PAC file generator
│   │   └── db/
│   │       ├── init.sql               # PostgreSQL schema
│   │       └── migrations/            # Schema migrations
│   ├── data/
│   │   ├── regulations/               # GDPR/HIPAA/PCI-DSS source docs
│   │   ├── seed_policies/             # Default policy JSON files
│   │   └── patterns/                  # Sensitive data pattern libraries
│   ├── tests/
│   │   ├── test_context_detector.py
│   │   ├── test_filter_agent.py
│   │   ├── test_policy_engine.py
│   │   ├── test_rag_service.py
│   │   └── test_redaction.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/                           # Angular 20 app (structure above)
│   ├── angular.json
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

### 5.2 Key Service: Context Detector

```python
# Pseudocode for the 3-stage detection pipeline
class ContextDetector:
    def __init__(self, rag_service, llm_service, policy_engine):
        self.rag = rag_service          # LlamaIndex-based RAG
        self.llm = llm_service          # LangChain LLM wrapper
        self.policy = policy_engine
        self.fast_scanner = FastScanner()  # Regex + keyword

    async def analyze(self, interception: Interception) -> ContextAnalysis:
        payload_text = self._extract_text(interception.payload)

        # Stage 1: Fast scan (< 10ms)
        fast_results = self.fast_scanner.scan(payload_text)
        if fast_results.is_critical:
            return self._build_analysis(fast_results, stage="fast_scan")

        # Stage 2: Embedding similarity (< 100ms)
        embedding_results = await self.rag.similarity_search(
            payload_text, collection="violation_patterns", top_k=5
        )
        if embedding_results.max_score > 0.85:
            return self._build_analysis(
                fast_results, embedding_results, stage="embedding"
            )

        # Stage 3: LLM contextual analysis (< 2s)
        agent_result = await self.llm.analyze_context(
            payload_text,
            fast_scan=fast_results,
            embeddings=embedding_results,
            tools=["search_regulations", "classify_data", "check_policy"]
        )
        return self._build_analysis(
            fast_results, embedding_results, agent_result, stage="llm"
        )
```

### 5.3 Key Service: Filter Agent (LangGraph)

```python
# Pseudocode for the LangGraph filter workflow
from langgraph.graph import StateGraph, END

def build_filter_graph():
    graph = StateGraph(FilterState)

    graph.add_node("context_detect", context_detect_node)
    graph.add_node("policy_evaluate", policy_evaluate_node)
    graph.add_node("decide_action", decide_action_node)
    graph.add_node("redact", redact_node)
    graph.add_node("block", block_node)
    graph.add_node("audit_log", audit_log_node)

    graph.set_entry_point("context_detect")
    graph.add_edge("context_detect", "policy_evaluate")
    graph.add_conditional_edges("policy_evaluate", route_action, {
        "ALLOW": "audit_log",
        "REDACT": "redact",
        "BLOCK": "block",
        "AUDIT": "audit_log",
    })
    graph.add_edge("redact", "audit_log")
    graph.add_edge("block", "audit_log")
    graph.add_edge("audit_log", END)

    return graph.compile()
```

### 5.4 Database Schema (PostgreSQL)

```sql
-- Core tables
CREATE TABLE interceptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_ip INET NOT NULL,
    destination TEXT NOT NULL,
    endpoint TEXT,
    direction VARCHAR(10) NOT NULL,       -- 'outbound' or 'inbound'
    payload_hash VARCHAR(64) NOT NULL,     -- SHA-256 of original payload
    data_classifications TEXT[],           -- '{PHI,PII}'
    entities_detected JSONB,
    regulations_applicable TEXT[],
    risk_score INTEGER,
    action_taken VARCHAR(10) NOT NULL,     -- ALLOW/REDACT/BLOCK/AUDIT
    policies_triggered TEXT[],
    justification TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE policies (
    id VARCHAR(50) PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    regulation VARCHAR(20),
    conditions JSONB NOT NULL,
    action VARCHAR(10) NOT NULL,
    redaction_strategy JSONB,
    notification JSONB,
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ai_endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern TEXT NOT NULL,
    provider VARCHAR(50),
    enabled BOOLEAN DEFAULT TRUE,
    default_action VARCHAR(10) DEFAULT 'AUDIT',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    interception_id UUID REFERENCES interceptions(id),
    event_type VARCHAR(50) NOT NULL,
    details JSONB,
    previous_hash VARCHAR(64),            -- Hash chain for tamper evidence
    current_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE classification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(20) NOT NULL,        -- PII, PHI, PCI, CUSTOM
    pattern TEXT,                          -- Regex pattern
    keywords TEXT[],
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_interceptions_created ON interceptions(created_at DESC);
CREATE INDEX idx_interceptions_action ON interceptions(action_taken);
CREATE INDEX idx_interceptions_source ON interceptions(source_ip);
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);
CREATE INDEX idx_policies_regulation ON policies(regulation);
CREATE INDEX idx_policies_enabled ON policies(enabled);
```

---

## 6. Process Flow (End-to-End)

### Step 1: Data Entry & Classification
- All enterprise AI traffic flows into the proxy interception layer
- Data is automatically classified:
  - **PII** → GDPR applicable
  - **PHI** → HIPAA applicable
  - **Cardholder Data** → PCI-DSS applicable
- Classification uses both fast regex scan and LLM-powered NER

### Step 2: Automated Governance Enforcement
- Policy engine applies rule-based and AI-driven compliance controls
- Role-based access and encryption policies enforced dynamically
- Filter Agent executes the appropriate action (ALLOW/REDACT/BLOCK/AUDIT)

### Step 3: Lineage & Provenance Tracking
- Every interception, transformation (redaction), AI model usage, and data movement is logged
- Tamper-evident hash chain in audit log enables full traceability for regulatory accountability

### Step 4: Continuous Risk Assessment
- AI scans for:
  - PHI exposure risks
  - Payment data anomalies
  - Access violations
- Automated mitigation triggered (alerts, redaction, blocking)
- Risk scores calculated per source IP / department

### Step 5: Compliance & Audit Automation
- Controls mapped to regulatory frameworks:
  - GDPR Articles
  - HIPAA Security Rule
  - PCI-DSS Requirements
- Real-time compliance posture dashboard

### Step 6: Reporting & Certification
- One-click exportable audit trail
- Evidence package ready for regulators and auditors
- Continuous compliance score tracking

---

## 7. API Endpoint Summary

### Proxy Management
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/proxy/status` | Proxy engine status |
| GET | `/api/v1/proxy/pac` | PAC file for VM configuration |
| POST | `/api/v1/proxy/start` | Start proxy engine |
| POST | `/api/v1/proxy/stop` | Stop proxy engine |

### Context Detection
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/context/analyze` | Analyze a payload for compliance |
| POST | `/api/v1/context/test` | Test context detection with sample data |

### Filter Agent
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/filter/process` | Process interception through filter graph |
| GET | `/api/v1/filter/stats` | Filter action statistics |

### Policy Management
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/policies` | List all policies |
| POST | `/api/v1/policies` | Create policy |
| GET | `/api/v1/policies/{id}` | Get policy |
| PUT | `/api/v1/policies/{id}` | Update policy |
| DELETE | `/api/v1/policies/{id}` | Delete policy |
| POST | `/api/v1/policies/{id}/toggle` | Enable/disable |
| POST | `/api/v1/policies/test` | Test policy |

### AI Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/endpoints` | List monitored endpoints |
| POST | `/api/v1/endpoints` | Add endpoint |
| PUT | `/api/v1/endpoints/{id}` | Update endpoint |
| DELETE | `/api/v1/endpoints/{id}` | Remove endpoint |

### Data Classification
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/classifications` | List classification rules |
| POST | `/api/v1/classifications` | Add rule |
| PUT | `/api/v1/classifications/{id}` | Update rule |
| DELETE | `/api/v1/classifications/{id}` | Remove rule |
| POST | `/api/v1/classifications/test` | Test classification |

### Audit Log
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/audit` | Query audit logs (paginated) |
| GET | `/api/v1/audit/{id}` | Get audit entry details |
| GET | `/api/v1/audit/export` | Export as CSV/PDF |
| POST | `/api/v1/audit/verify` | Verify hash chain integrity |

### RAG Knowledge Base
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/rag/ingest` | Ingest regulation documents |
| GET | `/api/v1/rag/collections` | List ChromaDB collections |
| POST | `/api/v1/rag/query` | Test RAG query |
| GET | `/api/v1/rag/stats` | Collection statistics |

### Dashboard & Reports
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/dashboard/kpis` | Dashboard KPI metrics |
| GET | `/api/v1/dashboard/interception-volume` | Time-series interception data |
| GET | `/api/v1/dashboard/action-breakdown` | Action type distribution |
| GET | `/api/v1/reports/compliance` | Compliance posture report |
| GET | `/api/v1/reports/violations` | Violation summary report |
| GET | `/api/v1/reports/export` | Export full report |

### WebSocket
| Endpoint | Purpose |
|---|---|
| `ws://host/ws/interceptions` | Live interception feed |
| `ws://host/ws/alerts` | Critical alert notifications |
| `ws://host/ws/stats` | Real-time dashboard stats |

---

## 8. Non-Functional Requirements

### 8.1 Performance
| Metric | Target |
|---|---|
| Fast scan latency | < 10ms (P95) |
| Full pipeline latency (3-stage) | < 3s (P95) |
| Proxy throughput | 100 req/s concurrent |
| WebSocket event latency | < 200ms |
| RAG retrieval | < 1s for top-5 chunks |
| Dashboard load time | < 2s initial, < 500ms updates |

### 8.2 Security
- TLS 1.3 for all communications
- Proxy CA certificate management
- RBAC for UI access (admin, auditor, viewer roles)
- Audit log tamper-evidence via SHA-256 hash chain
- Secrets in environment variables only
- Redacted payloads never stored in plain text

### 8.3 Scalability
- Support 50+ concurrent proxy connections
- Store 1M+ interception records
- ChromaDB: 5,000+ regulation chunks
- Horizontal scaling: proxy and API can run as separate containers

### 8.4 Observability
- Prometheus metrics at `/metrics`
- Structured JSON logging
- Health check at `/health`
- Dashboard for system performance monitoring

---

## 9. Deployment (Docker Compose)

### Services

| Service | Image / Build | Port | Purpose |
|---|---|---|---|
| `api` | FastAPI (build) | 8000 | REST API + WebSocket |
| `proxy` | mitmproxy + addon (build) | 8080 | MITM proxy engine |
| `frontend` | Angular + nginx (build) | 4200 | Admin dashboard |
| `postgres` | postgres:17-alpine | 5432 | Persistent storage |
| `redis` | redis:7.4-alpine | 6379 | Pub/sub + cache |
| `chromadb` | chromadb/chroma:1.5.1 | 8001 | Vector database |

---

## 10. Demo Scenarios

### Demo 1: PHI Leak Prevention
1. User opens ChatGPT in VM browser (traffic goes through proxy)
2. User types: "Summarize medical history for patient John Smith, DOB 03/15/1987, MRN 445129"
3. Proxy intercepts → Context Detector identifies PHI (name, DOB, MRN, ICD codes)
4. Filter Agent evaluates POL-HIPAA-PHI-001 → action=BLOCK
5. User sees: "Request blocked — PHI detected. HIPAA regulations prohibit sending PHI to external AI services."
6. Admin UI shows: interception card in red, full audit trail

### Demo 2: PCI Data Redaction
1. Developer uses AI coding assistant in VM
2. Sends code snippet containing test credit card number: `4532-1234-5678-1234`
3. Proxy intercepts → Fast Scanner detects PAN (Luhn-valid credit card)
4. Filter Agent evaluates POL-PCI-PAN-001 → action=REDACT
5. Request forwarded with PAN replaced: `[REDACTED:PAN]`
6. AI assistant responds normally; no real card data was exposed
7. Admin UI shows: yellow REDACT card with before/after payloads

### Demo 3: Policy Configuration
1. Admin opens UI → Policies page
2. Creates new policy: "Block Social Security Numbers to any AI service"
3. Configures: data_classification=PII, pattern=SSN, action=BLOCK
4. Tests policy with sample payload containing SSN
5. Policy triggers correctly → saves and enables
6. Next interception containing SSN is blocked per new policy

---

## 11. Implementation Roadmap

### Phase 1: Foundation (Days 1-3)
- Project scaffolding (FastAPI + Angular 20)
- Docker Compose setup (all 6 services)
- PostgreSQL schema creation
- Basic API structure with health checks
- Angular app shell with routing and sidebar

### Phase 2: Core Pipeline (Days 4-7)
- mitmproxy addon with AI endpoint detection
- Context Detector Stage 1 (fast scan — regex patterns)
- LlamaIndex RAG ingestion pipeline for regulations
- ChromaDB integration
- Context Detector Stage 2 (embedding similarity)
- Policy engine with default policies

### Phase 3: AI Layer (Days 8-10)
- LangChain agent for context analysis (Stage 3)
- LangGraph filter decision graph
- Redaction engine (4 strategies)
- LLM integration (self-hosted / local fallback)
- End-to-end interception → analysis → action pipeline

### Phase 4: Frontend (Days 11-14)
- Dashboard with real-time charts (ECharts)
- Live interception monitor (WebSocket)
- Policy management CRUD
- Audit log viewer
- RAG knowledge base management
- Settings and configuration pages

### Phase 5: Polish & Demo (Days 15-17)
- Demo scenario preparation
- UI/UX refinement
- Performance optimization
- Documentation
- Demo recording

---

## 12. Success Metrics

| Metric | Target |
|---|---|
| PHI/PII detection accuracy | > 95% |
| False positive rate | < 5% |
| Proxy latency overhead | < 3s for AI requests |
| Policy enforcement accuracy | 100% for configured rules |
| Audit log completeness | 100% of interceptions logged |
| Dashboard real-time delay | < 500ms |
| Regulation coverage | GDPR + HIPAA + PCI-DSS |

---

## 13. Risk Mitigation

| Risk | Probability | Mitigation |
|---|---|---|
| MITM proxy TLS issues | Medium | Pre-generate CA cert; provide install instructions |
| LLM latency spikes | Medium | 3-stage pipeline allows fast path for obvious violations |
| False positives blocking legitimate traffic | High | Default to AUDIT for borderline cases; easy policy tuning |
| ChromaDB retrieval accuracy | Medium | Curate top-100 regulation chunks; test embeddings |
| mitmproxy stability under load | Low | Connection pooling; async processing; queue overflow to Redis |

---

## 14. Deliverables

### Code
- FastAPI backend with all 5 modules
- Angular 20 admin dashboard with 9 views
- mitmproxy addon for AI traffic interception
- LangChain agent + LangGraph workflow
- LlamaIndex RAG pipeline
- Docker Compose (6 services)
- Default policies and classification rules
- PostgreSQL schema with seed data
- Unit + integration tests

### Documentation
- This PRD
- README.md with setup instructions
- API documentation (FastAPI Swagger)
- Architecture diagrams
- Demo script with 3 scenarios

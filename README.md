# AI Governance Proxy — Context-Aware Compliance Interception Layer

Transparent MITM proxy that intercepts AI agent traffic (ChatGPT, Copilot, custom LLM apps), applies real-time **context detection** via RAG-powered compliance engine, and **filters/modifies** requests violating GDPR, HIPAA, PCI-DSS policies.

## Architecture

```
ChatGPT / AI Apps → Proxy (MITM) → Context Detector (RAG + LLM) → Filter Agent → Policy Engine
                                                                        ↓
                                                                   Admin UI (Angular)
```

| Layer | Technology |
|-------|-----------|
| **Proxy** | mitmproxy 11+ (Python) |
| **Backend** | FastAPI 0.115+, Python 3.12 |
| **LLM** | LangChain 0.3+, LangGraph 0.3+ |
| **RAG** | LlamaIndex 0.12+, ChromaDB 1.5+, sentence-transformers |
| **Frontend** | Angular 19+, Angular Material, dark theme |
| **Database** | PostgreSQL 17+, Redis 7.4+ |
| **Deployment** | Docker Compose |

## Services

| Service | URL | Purpose |
|---------|-----|--------|
| Frontend | http://localhost:4200 | Admin UI (Angular) |
| API | http://localhost:8000/docs | FastAPI backend + Swagger |
| MITM Proxy | localhost:8080 | Intercepts AI traffic |
| Ollama LLM | http://localhost:11434 | Local LLM (llama3.2:3b) |
| ChromaDB | http://localhost:8001 | Vector DB for RAG |
| PostgreSQL | localhost:5432 | Relational DB |
| Redis | localhost:6379 | Cache |

## Quick Start

### Docker Compose (recommended)

```bash
cd governance-server
docker compose up --build -d
```

### Local Development

**Backend:**
```bash
cd governance-server/backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd governance-server/frontend
npm install
ng serve
```

## Core API

### Proxy Management
- `GET /api/v1/proxy/status` — Proxy engine status
- `GET /api/v1/proxy/pac` — PAC file for VM configuration
- `POST /api/v1/proxy/start` / `stop` — Control proxy

### Context Detection
- `POST /api/v1/context/analyze` — Analyze payload for compliance
- `POST /api/v1/context/test` — Test detection with sample data

### Filter Agent
- `POST /api/v1/filter/process` — Process interception through full pipeline
- `GET /api/v1/filter/stats` — Filter statistics

### Policy Management (CRUD)
- `GET/POST /api/v1/policies` — List/create policies
- `GET/PUT/DELETE /api/v1/policies/{id}` — Read/update/delete
- `POST /api/v1/policies/{id}/toggle` — Enable/disable
- `POST /api/v1/policies/test` — Test policy against sample

### AI Projects
- `GET/POST /api/v1/endpoints` — Manage monitored AI projects

### Data Classification
- `GET/POST /api/v1/classifications` — Manage detection rules
- `POST /api/v1/classifications/test` — Test classification

### Audit Log
- `GET /api/v1/audit` — Query audit logs
- `GET /api/v1/audit/export` — Export logs
- `POST /api/v1/audit/verify` — Verify hash chain integrity

### RAG Knowledge Base
- `POST /api/v1/rag/ingest` — Ingest regulation documents
- `GET /api/v1/rag/collections` — Collection stats
- `POST /api/v1/rag/query` — Query regulations

### Dashboard
- `GET /api/v1/dashboard/kpis` — Dashboard metrics
- `GET /api/v1/dashboard/recent-interceptions` — Recent activity

### WebSockets
- `ws://localhost:8000/ws/interceptions` — Live interception feed
- `ws://localhost:8000/ws/alerts` — Critical alerts
- `ws://localhost:8000/ws/stats` — Real-time stats

## Default Policies

| ID | Regulation | Action | Trigger |
|----|-----------|--------|---------|
| POL-HIPAA-PHI-001 | HIPAA | BLOCK | PHI to external AI |
| POL-GDPR-PII-001 | GDPR | REDACT | PII to external AI |
| POL-PCI-PAN-001 | PCI-DSS | REDACT | Credit card PAN |
| POL-PCI-CVV-001 | PCI-DSS | BLOCK | CVV detected |
| POL-GENERAL-001 | Internal | REDACT | SSN detected |
| POL-GENERAL-002 | Internal | BLOCK | API keys/passwords |

## MITM Proxy — Runtime Traffic Interception

The MITM proxy (`mitmproxy`) runs on **port 8080** and intercepts real HTTP/HTTPS traffic to AI services. When a request matches a known AI domain (OpenAI, Anthropic, etc.), it sends the payload to the filter agent API for compliance checking before forwarding.

### How it works

```
User's Browser/App → mitmproxy:8080 → Filter Agent API → Decision
  ALLOW  → forward request to AI server as-is
  REDACT → replace sensitive data, then forward
  BLOCK  → return 403 to client, do NOT forward
  AUDIT  → forward as-is, log the interception
```

### Setup on client machines

**Option 1: System-wide proxy (env vars)**
```bash
export http_proxy=http://<VM_IP>:8080
export https_proxy=http://<VM_IP>:8080
```

**Option 2: PAC file (selective, browser only)**
```
Configure browser/OS proxy to: http://<VM_IP>:8000/api/v1/proxy/pac
```

**Option 3: Test with curl**
```bash
# This will be BLOCKED (PHI + PII detected)
curl -x http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Patient John Smith SSN 123-45-6789 MRN 445129"}]}' \
  http://api.openai.com/v1/chat/completions

# This will be ALLOWED (no sensitive data)
curl -x http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Write a Python sort function"}]}' \
  http://api.openai.com/v1/chat/completions
```

### HTTPS interception

For HTTPS traffic, install the mitmproxy CA certificate on client machines:
1. Set the proxy: `export http_proxy=http://<VM_IP>:8080`
2. Visit `http://mitm.it` in a browser
3. Download and install the certificate for your OS

### Intercepted AI domains

- `api.openai.com` (ChatGPT, GPT-4)
- `api.anthropic.com` (Claude)
- `copilot.microsoft.com` (Copilot)
- `generativelanguage.googleapis.com` (Gemini)
- `api-inference.huggingface.co` (HuggingFace)

## CIL Detection Pipeline

1. **Stage 1 — Signal Collection**: Browser telemetry signals (URL, role, device, tools)
2. **Stage 2 — Context Classification** (< 100ms): MiniLM embedding multi-label classifier
3. **Stage 3 — PII/NER Detection** (< 10ms): Regex patterns for SSN, credit cards, MRN, ICD codes
4. **Stage 4 — Intent Detection** (< 2s): Ollama LLM classifies intent type
5. **Stage 5 — Context Object Builder**: Structured CIL output with regulatory scope

## UI Pages

- **Dashboard** — KPIs, proxy status, recent activity
- **Live Monitor** — Real-time interception feed with WebSocket
- **Policies** — CRUD + policy testing
- **AI Projects** — Manage monitored agent deployments
- **Classifications** — Data detection rules + testing
- **Audit Log** — Tamper-evident log with hash chain verification
- **Knowledge Base** — RAG document management + query tester
- **Reports** — Compliance posture + export
- **Settings** — Proxy, LLM, database configuration + MITM proxy setup instructions

## MCP Server (Model Context Protocol)

The governance server exposes compliance tools via MCP at `/mcp` (SSE transport).
Any MCP-compatible AI agent can discover and invoke these tools automatically.

### MCP Tools

| Tool | Description |
|------|-------------|
| `scan_agent_request` | Full compliance scan of an agent's tool chain |
| `check_text` | Quick PII/sensitive data check on text |
| `list_policies` | List all active compliance policies |
| `get_compliance_status` | Aggregate compliance statistics |
| `is_agent_blocked` | Check if an agent is blocked before submitting |

### Agent Blocking

The governance server **intelligently blocks producers** that trigger compliance violations:
1. Producer submits request via MCP `scan_agent_request` tool
2. Governance server scans, detects violations, and records the request
3. If action = BLOCK, the agent is added to the blocked list
4. Response includes `agent_blocked: true` and `producer_action: STOP_ALL_QUERIES`
5. Producer MUST check `is_agent_blocked` before future submissions
6. Governance server always records all requests (even from blocked agents) for audit

### Producer Integration

Share with the producer team:
- **MCP endpoint**: `http://<GOVERNANCE_SERVER>:8000/mcp`
- **REST endpoint**: `POST http://<GOVERNANCE_SERVER>:8000/api/v1/agent-requests`
- **Block check**: MCP tool `is_agent_blocked` or `GET /api/v1/agent-requests/blocked/list`

# Producer Integration Contract — AI Governance Server

## Overview

The AI Governance Server provides compliance scanning for AI agent pipelines via two integration methods:

1. **MCP (Model Context Protocol)** — Recommended. AI agents auto-discover and invoke governance tools.
2. **REST API** — Direct HTTP integration for non-MCP producers.

---

## 1. MCP Integration (Recommended)

### What is MCP?

MCP (Model Context Protocol) is a standard protocol that allows AI agents to dynamically discover and invoke tools exposed by servers. Your agent framework (LangChain, CrewAI, AutoGen, Claude, etc.) connects to our MCP server and automatically sees our compliance tools — **zero custom code required**.

### MCP Server Endpoint

```
http://<GOVERNANCE_SERVER_HOST>:8000/mcp
```

Transport: **SSE (Server-Sent Events)**

### How Auto-Detection Works

1. Your producer agent connects to the MCP endpoint at startup
2. MCP protocol performs **tool discovery** — the agent sees all available tools:
   - `scan_agent_request` — Full compliance scan
   - `check_text` — Quick PII check
   - `list_policies` — View active policies
   - `get_compliance_status` — Aggregate stats
   - `is_agent_blocked` — Check if your agent is blocked
3. Your agent can invoke these tools naturally as part of its workflow
4. The governance server scans the request, returns results with block signals

### What to Share with the Producer Team

Provide the producer team with:

| Item | Value |
|------|-------|
| **MCP endpoint URL** | `http://<GOVERNANCE_SERVER_HOST>:8000/mcp` |
| **Transport** | SSE |
| **REST fallback URL** | `POST http://<GOVERNANCE_SERVER_HOST>:8000/api/v1/agent-requests` |
| **Block check URL** | `GET http://<GOVERNANCE_SERVER_HOST>:8000/api/v1/agent-requests/blocked/list` |
| **Swagger docs** | `http://<GOVERNANCE_SERVER_HOST>:8000/docs` |
| **This contract document** | `PRODUCER_CONTRACT.md` |

### Producer MCP Client Setup (Python Example)

```python
from mcp import ClientSession
from mcp.client.sse import sse_client

GOVERNANCE_MCP_URL = "http://<GOVERNANCE_SERVER_HOST>:8000/mcp"

async def connect_governance():
    async with sse_client(GOVERNANCE_MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Auto-discover all governance tools
            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])

            # Check if agent is blocked BEFORE submitting
            block_check = await session.call_tool(
                "is_agent_blocked",
                arguments={"source_app": "your-agent-name"}
            )
            print("Block status:", block_check.content[0].text)

            # Submit a request for compliance scanning
            result = await session.call_tool(
                "scan_agent_request",
                arguments={
                    "request_id": "REQ-001",
                    "title": "Customer Data Export",
                    "source_app": "your-agent-name",
                    "user_name": "John Doe",
                    "user_input": "Export customer records",
                    "tool_chain": [
                        {
                            "tool_name": "database_query",
                            "description": "Query customer database",
                            "sequence": 1,
                            "input": {"query": "SELECT * FROM customers"},
                            "output": {"summary": "Retrieved 500 customer records"},
                            "reasoning": "Fetching data for export",
                            "duration_ms": 200,
                            "status": "SUCCESS"
                        }
                    ],
                    "final_output": {"summary": "Export complete"}
                }
            )
            print("Scan result:", result.content[0].text)
```

### Producer Blocking Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ Producer Agent Workflow                                              │
│                                                                     │
│  1. Connect to MCP server                                           │
│  2. Call is_agent_blocked(source_app="my-agent")                    │
│     ├── blocked: false → CONTINUE to step 3                        │
│     └── blocked: true  → STOP. Do not submit any queries.          │
│                                                                     │
│  3. Execute your tool chain (DB queries, API calls, etc.)           │
│                                                                     │
│  4. Call scan_agent_request(...) with full tool chain results       │
│     ├── producer_action: "CONTINUE" → Safe. Proceed normally.      │
│     └── producer_action: "STOP_ALL_QUERIES"                        │
│         → Agent is NOW BLOCKED. Stop all future submissions.        │
│         → agent_blocked: true                                       │
│         → block_reason: "Auto-blocked: N violation(s)..."           │
│                                                                     │
│  5. On next iteration, go back to step 2 (check block status)      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. REST API Integration

### Endpoint

```
POST http://<GOVERNANCE_SERVER_HOST>:8000/api/v1/agent-requests
Content-Type: application/json
```

### Request Payload Schema (Contract)

```json
{
  "request_id": "REQ-1740465600000",
  "title": "Human-readable title describing the agent task",
  "source_app": "your-agent-name",
  "user_name": "Name of the user who initiated the request",
  "industry": "Healthcare",
  "status": "COMPLETED",
  "user_input": "The original user prompt or query that triggered the agent",
  "tool_chain": [
    {
      "tool_name": "tool_identifier",
      "description": "What this tool does",
      "sequence": 1,
      "input": {
        "key": "value — the input parameters passed to the tool"
      },
      "output": {
        "summary": "Human-readable summary of the tool output — THIS IS SCANNED FOR COMPLIANCE"
      },
      "reasoning": "Why the agent chose to invoke this tool",
      "duration_ms": 250,
      "status": "SUCCESS"
    }
  ],
  "final_output": {
    "summary": "Final result or output of the entire agent pipeline"
  },
  "metadata": {
    "model": "gpt-4",
    "total_tokens": 2500
  }
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `request_id` | string | **Yes** | Unique ID for this request (e.g., `REQ-` + timestamp) |
| `title` | string | **Yes** | Human-readable task title |
| `source_app` | string | **Yes** | Agent/deployment name (used for blocking & filtering) |
| `user_name` | string | Recommended | Name of the user who initiated the request |
| `industry` | string | Optional | Industry category. Auto-detected if not provided. Values: `Healthcare`, `Finance`, `Legal`, `Technology`, `Education`, `Retail`, `Government` |
| `status` | string | Optional | Pipeline status. Default: `COMPLETED` |
| `user_input` | string | **Yes** | The original user prompt that triggered the agent |
| `tool_chain` | array | **Yes** | List of tool executions in order (see below) |
| `final_output` | object | Optional | Final combined output of the pipeline |
| `metadata` | object | Optional | Extra metadata (model name, token count, etc.) |

### Tool Chain Item Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_name` | string | **Yes** | Identifier for the tool |
| `description` | string | Recommended | What the tool does |
| `sequence` | integer | **Yes** | Execution order (1, 2, 3...) |
| `input` | object | **Yes** | Input parameters passed to the tool |
| `output` | object | **Yes** | Output from the tool. **Must include `summary` key** — this is the primary field scanned for compliance. |
| `reasoning` | string | Optional | Why the agent invoked this tool (also scanned) |
| `duration_ms` | integer | Optional | Execution time in milliseconds |
| `status` | string | Optional | `SUCCESS`, `FAILURE`, etc. Default: `SUCCESS` |

### Response Schema

```json
{
  "id": "uuid",
  "request_id": "REQ-1740465600000",
  "title": "Customer Data Export",
  "source_app": "your-agent-name",
  "user_name": "John Doe",
  "industry": "Finance",
  "compliance_status": "VIOLATION",
  "violations": [
    {
      "tool_name": "database_query",
      "tool_sequence": 1,
      "field": "output",
      "violation_type": "PCI",
      "regulation": "PCI-DSS",
      "article": "PCI-DSS Req 3.4",
      "description": "Credit card numbers detected in tool output",
      "severity": "CRITICAL",
      "entities": ["CREDIT_CARD: 4532-****-****-6789"],
      "remediation": "Apply PCI tokenization — show only last 4 digits"
    }
  ],
  "data_classifications": ["PCI", "PII"],
  "regulations_applicable": ["GDPR", "PCI-DSS"],
  "risk_score": 85,
  "scan_summary": "Detected 3 violation(s) across 2 tool(s)...",
  "processing_time_ms": 1250,
  "recommended_action": "BLOCK",
  "policies_triggered": ["POL-PCI-PAN-001"],
  "agent_blocked": true,
  "block_reason": "Auto-blocked: 3 violation(s), risk score 85",
  "producer_action": "STOP_ALL_QUERIES"
}
```

### Key Response Fields for Producer

| Field | Values | Action Required |
|-------|--------|-----------------|
| `producer_action` | `CONTINUE` | Safe — continue normal operations |
| `producer_action` | `STOP_ALL_QUERIES` | **STOP immediately**. Agent is blocked. |
| `agent_blocked` | `true` / `false` | Whether the agent is now blocked |
| `block_reason` | string | Why the agent was blocked |
| `recommended_action` | `BLOCK` / `REDACT` / `AUDIT` | Governance recommendation |

---

## 3. Sample Requests

### Sample 1: Healthcare (will trigger HIPAA violations)

```json
{
  "request_id": "REQ-HC-001",
  "title": "Patient Record Summarization for Insurance",
  "source_app": "clinical-assistant",
  "user_name": "Dr. James Wilson",
  "user_input": "Summarize patient Maria Garcia treatment history for insurance claim",
  "tool_chain": [
    {
      "tool_name": "ehr_lookup",
      "description": "Query electronic health records",
      "sequence": 1,
      "input": { "patient_id": "P-44782", "fields": ["diagnosis", "medications"] },
      "output": { "summary": "Patient Maria Garcia, MRN 4478291, diagnosed with Type 2 Diabetes. Current prescription: Metformin 500mg, Lisinopril 10mg" },
      "reasoning": "Looking up complete medical history",
      "duration_ms": 250,
      "status": "SUCCESS"
    },
    {
      "tool_name": "email_sender",
      "description": "Send summary via email",
      "sequence": 2,
      "input": { "to": "claims@insurance-co.com", "subject": "Treatment Summary" },
      "output": { "summary": "Sent treatment summary with full PHI to external insurance email" },
      "reasoning": "Delivering to insurance company",
      "duration_ms": 200,
      "status": "SUCCESS"
    }
  ],
  "final_output": { "summary": "Treatment summary sent to insurance company via email" },
  "metadata": { "model": "gpt-4", "total_tokens": 3200 }
}
```

### Sample 2: Finance (will trigger PCI-DSS violations)

```json
{
  "request_id": "REQ-FIN-001",
  "title": "EU Customer Data Export to External Analytics",
  "source_app": "data-analytics-agent",
  "user_name": "Sarah Johnson",
  "user_input": "Export EU customer records including payment info for analytics",
  "tool_chain": [
    {
      "tool_name": "database_query",
      "description": "Query customer database",
      "sequence": 1,
      "input": { "query": "SELECT name, ssn, email, credit_card FROM customers WHERE region='EU'" },
      "output": { "summary": "Retrieved 1,247 records including SSN 234-56-7890 and credit card 4532-0151-2345-6789", "record_count": 1247 },
      "reasoning": "Querying all fields to fulfill export request",
      "duration_ms": 340,
      "status": "SUCCESS"
    }
  ],
  "final_output": { "summary": "Exported 1,247 EU customer records to external vendor" },
  "metadata": { "model": "gpt-4", "total_tokens": 4521 }
}
```

### Sample 3: Technology — Clean Request (no violations expected)

```json
{
  "request_id": "REQ-TECH-001",
  "title": "Generate Python Sorting Algorithm",
  "source_app": "code-assistant",
  "user_name": "Priya Patel",
  "user_input": "Write a function to sort a list of dictionaries by key",
  "tool_chain": [
    {
      "tool_name": "code_generator",
      "description": "Generate Python code",
      "sequence": 1,
      "input": { "language": "python", "task": "sort list of dicts by key" },
      "output": { "summary": "Generated type-hinted sort function with docstring" },
      "reasoning": "Standard coding task with no sensitive data",
      "duration_ms": 300,
      "status": "SUCCESS"
    }
  ],
  "final_output": { "summary": "Clean code generation — no compliance issues" },
  "metadata": { "model": "gpt-4o", "total_tokens": 800 }
}
```

---

## 4. Industry Auto-Detection

If the producer does NOT provide the `industry` field, the governance server automatically detects it from the content using keyword matching:

| Industry | Example Keywords |
|----------|-----------------|
| Healthcare | patient, diagnosis, treatment, medication, HIPAA, PHI, MRN |
| Finance | credit card, bank, loan, payment, PCI, account number |
| Legal | attorney, lawsuit, contract, compliance, GDPR |
| Technology | API key, password, deployment, Docker, cloud, AWS |
| Education | student, grade, transcript, enrollment, FERPA |
| Retail | customer, order, product, inventory, shipping |
| Government | citizen, SSN, federal, classified, FOIA |

**Recommendation**: Always provide `industry` explicitly for accuracy. If unknown, set to `""` and let auto-detection handle it.

---

## 5. Block Check API

Before submitting requests, producers can check if they are blocked:

**MCP Tool:**
```
is_agent_blocked(source_app="your-agent-name")
```

**REST API:**
```
GET http://<GOVERNANCE_SERVER_HOST>:8000/api/v1/agent-requests/deployments/list
```

Response includes `blocked: true/false` for each deployment.

---

## 6. Contact

For unblocking requests or integration questions, contact the governance server administrator.
Unblock API (admin only): `DELETE /api/v1/agent-requests/blocked/{source_app}`

"""
MCP Server — exposes AI Governance Proxy compliance tools via Model Context Protocol.

Any MCP-compatible AI agent (LangChain, CrewAI, Claude, etc.) can discover and invoke
these tools automatically — zero custom integration required.

Tools exposed:
  1. scan_agent_request  — Full compliance scan of an agent's tool chain
  2. check_text          — Quick PII/sensitive data check on arbitrary text
  3. list_policies       — List all active compliance policies
  4. get_compliance_status — Get compliance stats (total scans, violations, etc.)
"""

import json
import logging
import time
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("aigp.mcp")

# Create the MCP server instance
mcp = FastMCP(
    name="AI Governance Server",
    instructions=(
        "This MCP server provides compliance scanning tools for AI agent pipelines. "
        "Use 'scan_agent_request' to check an agent's full tool chain for PII, policy violations, "
        "and regulatory compliance issues. IMPORTANT: If the response contains "
        "'agent_blocked: true' or 'producer_action: STOP_ALL_QUERIES', the producer "
        "MUST stop sending further queries immediately. "
        "Use 'is_agent_blocked' to check if an agent is blocked before submitting. "
        "Use 'check_text' for quick text scanning. "
        "Use 'list_policies' to see active compliance policies."
    ),
)

# Reference to the FastAPI app state (set during startup)
_app_state = None


def set_app_state(state):
    """Called from main.py lifespan to wire MCP tools to backend services."""
    global _app_state
    _app_state = state
    logger.info("MCP server: app state wired — tools are live")


@mcp.tool(
    name="scan_agent_request",
    description=(
        "Scan an AI agent's complete tool chain for compliance violations. "
        "Detects PII (SSN, credit cards, API keys, passwords, health data), "
        "checks against HIPAA, GDPR, PCI-DSS, and internal policies, "
        "and returns violations with severity scores and remediation suggestions. "
        "Input: request_id, title, source_app, tool_chain (list of tool executions), "
        "user_input, final_output."
    ),
)
async def scan_agent_request(
    request_id: str,
    title: str,
    tool_chain: list[dict],
    source_app: str = "",
    user_name: str = "",
    user_input: str = "",
    final_output: dict | None = None,
    metadata: dict | None = None,
) -> str:
    """Run full compliance scan on an agent pipeline and store the result."""
    from app.models.schemas import AgentRequestCreate, ToolExecution
    from app.api.v1.agent_requests import _scan_agent_request
    from app.core.database import async_session
    from app.models.db_models import AgentRequestModel

    if not _app_state:
        return json.dumps({"error": "MCP server not initialized — backend services unavailable"})

    rag_service = getattr(_app_state, "rag_service", None)
    llm_service = getattr(_app_state, "llm_service", None)
    policy_engine = getattr(_app_state, "policy_engine", None)

    # Build the payload from MCP tool arguments
    tools = []
    for t in tool_chain:
        tools.append(ToolExecution(
            tool_name=t.get("tool_name", "unknown"),
            description=t.get("description", ""),
            sequence=t.get("sequence", 0),
            input=t.get("input", {}),
            output=t.get("output", {}),
            reasoning=t.get("reasoning", ""),
            duration_ms=t.get("duration_ms", 0),
            status=t.get("status", "SUCCESS"),
        ))

    payload = AgentRequestCreate(
        request_id=request_id,
        title=title,
        source_app=source_app,
        user_name=user_name,
        status="COMPLETED",
        user_input=user_input,
        tool_chain=tools,
        final_output=final_output or {},
        metadata=metadata or {},
    )

    # Check if agent is already blocked
    from app.models.db_models import BlockedAgentModel
    pre_blocked = False
    pre_blocked_reason = ""
    if source_app:
        try:
            from sqlalchemy import select as sa_select
            async with async_session() as check_db:
                result = await check_db.execute(
                    sa_select(BlockedAgentModel).where(BlockedAgentModel.source_app == source_app)
                )
                blocked_rec = result.scalar_one_or_none()
                if blocked_rec:
                    pre_blocked = True
                    pre_blocked_reason = blocked_rec.reason or "Previously blocked"
        except Exception as e:
            logger.warning("MCP block check failed: %s", e)

    # Detect industry from content
    from app.api.v1.agent_requests import _detect_industry
    full_text = user_input or ""
    for t in tool_chain:
        if isinstance(t.get("output"), dict):
            full_text += " " + t["output"].get("summary", "")
        full_text += " " + t.get("description", "") + " " + t.get("reasoning", "")
    if final_output:
        full_text += " " + json.dumps(final_output)
    detected_industry = _detect_industry(full_text)

    # Run the compliance scan (reuses existing backend logic)
    scan_result = await _scan_agent_request(payload, rag_service, llm_service)

    # Policy evaluation
    policies_triggered = []
    if policy_engine and scan_result.get("violations"):
        try:
            all_policies = policy_engine.get_all_policies_memory()
            for pol in all_policies:
                if not pol.get("enabled", True):
                    continue
                conds = pol.get("conditions", {})
                blocked_kw = conds.get("blocked_keywords", [])
                if blocked_kw:
                    full_text = (user_input + " " + json.dumps(tool_chain)).lower()
                    if any(kw.lower() in full_text for kw in blocked_kw):
                        policies_triggered.append(pol["id"])
                        if pol.get("action") == "BLOCK":
                            scan_result["recommended_action"] = "BLOCK"
                pol_cls = conds.get("data_classifications", [])
                if pol_cls and any(c in scan_result.get("data_classifications", []) for c in pol_cls):
                    policies_triggered.append(pol["id"])
        except Exception as e:
            logger.warning("MCP policy eval failed: %s", e)

    scan_result["policies_triggered"] = sorted(set(policies_triggered))

    # Store in DB (governance server ALWAYS records for monitoring/audit)
    try:
        async with async_session() as db:
            record = AgentRequestModel(
                request_id=payload.request_id,
                title=payload.title,
                source_app=payload.source_app,
                user_name=user_name,
                industry=detected_industry,
                status=payload.status,
                user_input=payload.user_input,
                tool_chain=[t.model_dump() for t in payload.tool_chain],
                final_output=payload.final_output,
                metadata_info=payload.metadata,
                compliance_status=scan_result["compliance_status"],
                violations=scan_result["violations"],
                data_classifications=scan_result["data_classifications"],
                regulations_applicable=scan_result["regulations_applicable"],
                risk_score=scan_result["risk_score"],
                policies_triggered=scan_result["policies_triggered"],
                recommended_action=scan_result["recommended_action"],
                scan_summary=scan_result["scan_summary"],
                processing_time_ms=scan_result["processing_time_ms"],
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            scan_result["id"] = str(record.id)

            # Auto-block agent if BLOCK action
            if scan_result["recommended_action"] == "BLOCK" and source_app and not pre_blocked:
                try:
                    block_record = BlockedAgentModel(
                        source_app=source_app,
                        reason=f"Auto-blocked: {len(scan_result['violations'])} violation(s). "
                               f"Risk score: {scan_result['risk_score']}. Action: BLOCK.",
                        blocked_request_id=request_id,
                    )
                    db.add(block_record)
                    await db.commit()
                    logger.warning("[MCP AGENT BLOCKED] %s auto-blocked after request %s",
                                  source_app, request_id)
                except Exception:
                    pass

            logger.info("[MCP] Stored agent request %s: %s", request_id, scan_result["compliance_status"])
    except Exception as e:
        logger.warning("MCP DB store failed: %s", e)
        scan_result["id"] = "not-stored"

    # Broadcast to WebSocket for live UI update
    try:
        ws_manager = getattr(_app_state, "ws_manager", None)
        if ws_manager:
            await ws_manager.broadcast("interceptions", {
                "type": "agent_request",
                "id": scan_result.get("id", ""),
                "request_id": request_id,
                "title": title,
                "source_app": source_app,
                "compliance_status": scan_result["compliance_status"],
                "risk_score": scan_result["risk_score"],
                "violations_count": len(scan_result["violations"]),
                "recommended_action": scan_result["recommended_action"],
            })
    except Exception:
        pass

    # Add block signal for producer
    is_blocked = pre_blocked or scan_result["recommended_action"] == "BLOCK"
    scan_result["agent_blocked"] = is_blocked
    scan_result["block_reason"] = pre_blocked_reason if pre_blocked else (
        f"Auto-blocked: {len(scan_result['violations'])} violation(s), risk score {scan_result['risk_score']}"
        if scan_result["recommended_action"] == "BLOCK" else ""
    )
    scan_result["producer_action"] = "STOP_ALL_QUERIES" if is_blocked else "CONTINUE"
    scan_result["industry"] = detected_industry
    scan_result["user_name"] = user_name

    return json.dumps(scan_result, default=str, indent=2)


@mcp.tool(
    name="check_text",
    description=(
        "Quick scan of arbitrary text for PII and sensitive data. "
        "Returns detected entities (SSN, credit cards, API keys, emails, etc.), "
        "data classifications, and applicable regulations. "
        "Use this for lightweight checks without storing results."
    ),
)
async def check_text(text: str) -> str:
    """Scan text for PII entities without storing to DB."""
    from app.api.v1.agent_requests import _scan_text_for_entities

    if not text or len(text.strip()) < 3:
        return json.dumps({"entities": [], "classifications": [], "message": "Text too short to scan"})

    entities, classifications = _scan_text_for_entities(text)

    # Map classifications to regulations
    cls_to_reg = {
        "PHI": ["HIPAA"], "PCI": ["PCI-DSS"], "PII": ["GDPR", "GLBA"],
        "SECRET": ["ISO 27001", "INTERNAL"],
    }
    regulations = set()
    for cls in classifications:
        regulations.update(cls_to_reg.get(cls, []))

    return json.dumps({
        "entities": entities,
        "classifications": sorted(classifications),
        "regulations_applicable": sorted(regulations),
        "entity_count": len(entities),
        "has_sensitive_data": len(entities) > 0,
    }, indent=2)


@mcp.tool(
    name="list_policies",
    description=(
        "List all active compliance policies in the governance proxy. "
        "Returns policy names, regulations, actions (BLOCK/REDACT/AUDIT), "
        "and conditions including blocked keywords."
    ),
)
async def list_policies() -> str:
    """Return all active compliance policies."""
    if not _app_state:
        return json.dumps({"error": "MCP server not initialized"})

    policy_engine = getattr(_app_state, "policy_engine", None)
    if not policy_engine:
        return json.dumps({"error": "Policy engine not available"})

    policies = policy_engine.get_all_policies_memory()
    result = []
    for p in policies:
        result.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "regulation": p.get("regulation"),
            "action": p.get("action"),
            "enabled": p.get("enabled", True),
            "conditions": p.get("conditions", {}),
        })

    return json.dumps({"policies": result, "count": len(result)}, indent=2)


@mcp.tool(
    name="get_compliance_status",
    description=(
        "Get aggregate compliance statistics: total agent scans, violations detected, "
        "clean requests, average risk score, and compliance percentage."
    ),
)
async def get_compliance_status() -> str:
    """Return aggregate compliance stats from the database."""
    from sqlalchemy import select, func
    from app.core.database import async_session
    from app.models.db_models import AgentRequestModel

    try:
        async with async_session() as db:
            total = (await db.execute(select(func.count(AgentRequestModel.id)))).scalar() or 0
            violations = (await db.execute(
                select(func.count(AgentRequestModel.id)).where(
                    AgentRequestModel.compliance_status == "VIOLATION"
                )
            )).scalar() or 0
            clean = (await db.execute(
                select(func.count(AgentRequestModel.id)).where(
                    AgentRequestModel.compliance_status == "CLEAN"
                )
            )).scalar() or 0
            avg_risk = (await db.execute(
                select(func.avg(AgentRequestModel.risk_score))
            )).scalar() or 0

            compliance_pct = round((clean / total) * 100, 1) if total > 0 else 100.0

            return json.dumps({
                "total_scans": int(total),
                "violations": int(violations),
                "clean": int(clean),
                "avg_risk_score": round(float(avg_risk), 1),
                "compliance_percentage": float(compliance_pct),
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Database query failed: {str(e)}"})


@mcp.tool(
    name="is_agent_blocked",
    description=(
        "Check if a specific agent (by source_app name) is currently blocked "
        "from submitting requests. Producers SHOULD call this before submitting "
        "new requests. Returns blocked status, reason, and when it was blocked. "
        "If blocked, the producer MUST NOT submit further queries."
    ),
)
async def is_agent_blocked(source_app: str) -> str:
    """Check if an agent is blocked. Producers should call this before submitting."""
    from app.core.database import async_session
    from app.models.db_models import BlockedAgentModel
    from sqlalchemy import select as sa_select

    if not source_app:
        return json.dumps({"error": "source_app is required", "blocked": False})

    try:
        async with async_session() as db:
            result = await db.execute(
                sa_select(BlockedAgentModel).where(BlockedAgentModel.source_app == source_app)
            )
            record = result.scalar_one_or_none()
            if record:
                return json.dumps({
                    "blocked": True,
                    "source_app": source_app,
                    "reason": record.reason or "Blocked due to compliance violations",
                    "blocked_at": record.blocked_at.isoformat() if record.blocked_at else None,
                    "blocked_request_id": record.blocked_request_id or "",
                    "producer_action": "STOP_ALL_QUERIES",
                    "message": f"Agent '{source_app}' is BLOCKED. Do NOT submit further queries.",
                }, indent=2)
            else:
                return json.dumps({
                    "blocked": False,
                    "source_app": source_app,
                    "producer_action": "CONTINUE",
                    "message": f"Agent '{source_app}' is clear to submit requests.",
                }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Block check failed: {str(e)}", "blocked": False})

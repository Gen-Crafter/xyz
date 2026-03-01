"""
Agent Request API — ingests producer agent pipeline results,
runs compliance scanning on each tool's input/output using RAG + LLM, and stores results.
Features: severity-weighted risk scoring, remediation suggestions, policy-linked
auto-blocking, audit trail integration, keyword-blocking.
"""

import time
import re
import uuid
import json
import logging
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, func, desc, cast, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, async_session
from app.models.db_models import AgentRequestModel, BlockedAgentModel
from app.models.schemas import AgentRequestCreate

logger = logging.getLogger("aigp.agent_requests")
router = APIRouter(prefix="/agent-requests", tags=["Agent Requests"])

# ─── Remediation suggestion map ──────────────────────────────────────────────

# ─── Industry detection keywords ─────────────────────────────────────────────

INDUSTRY_KEYWORDS = {
    "Healthcare": ["patient", "diagnosis", "treatment", "medication", "clinical", "hospital",
                   "medical", "health", "ehr", "hipaa", "phi", "prescription", "doctor",
                   "nurse", "surgery", "therapy", "lab result", "mrn", "icd", "radiology",
                   "pharmacy", "insurance claim", "medicare", "medicaid"],
    "Finance": ["credit card", "bank", "loan", "mortgage", "investment", "portfolio",
                "trading", "payment", "transaction", "pci", "account number", "routing",
                "iban", "swift", "fintech", "billing", "invoice", "revenue", "profit"],
    "Legal": ["attorney", "legal", "lawsuit", "litigation", "contract", "compliance",
              "regulation", "court", "settlement", "arbitration", "gdpr", "subpoena"],
    "Technology": ["api key", "password", "secret", "deployment", "infrastructure",
                   "kubernetes", "docker", "cloud", "aws", "azure", "gcp", "code",
                   "repository", "ci/cd", "devops", "software", "algorithm"],
    "Education": ["student", "grade", "transcript", "enrollment", "curriculum",
                  "teacher", "university", "school", "academic", "ferpa"],
    "Retail": ["customer", "order", "product", "inventory", "shipping", "e-commerce",
               "checkout", "cart", "warehouse", "supply chain"],
    "Government": ["citizen", "social security", "ssn", "federal", "state agency",
                   "classified", "clearance", "public record", "foia"],
}


def _detect_industry(text: str) -> str:
    """Detect industry from content using keyword matching. Returns best-match industry."""
    if not text:
        return ""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[industry] = score
    if not scores:
        return ""
    return max(scores, key=scores.get)


REMEDIATION_MAP = {
    ("HIPAA", "SSN"): "Apply HIPAA Safe Harbor de-identification: remove or generalize SSN before transmission.",
    ("HIPAA", "PHI_CONTEXT"): "Ensure a valid Business Associate Agreement (BAA) is in place before sharing PHI with external services.",
    ("HIPAA", "ICD10_CODE"): "De-identify medical codes per HIPAA Expert Determination method before external disclosure.",
    ("HIPAA", "MRN"): "Remove or pseudonymize Medical Record Numbers before sharing outside covered entity.",
    ("PCI-DSS", "CREDIT_CARD"): "Apply PCI tokenization or masking (show only last 4 digits) before any data transfer.",
    ("PCI-DSS", "CVV"): "Never store or transmit CVV data. Remove entirely from the payload.",
    ("GDPR", "PII"): "Obtain explicit consent or apply data minimization. Consider pseudonymization for EU citizen data.",
    ("GDPR", "EMAIL"): "Redact or hash email addresses when processing does not require direct identifiers.",
    ("GDPR", "PHONE"): "Anonymize phone numbers unless consent for processing is documented.",
    ("ISO 27001", "API_KEY"): "Rotate exposed API keys immediately. Store secrets in a vault, never in code or AI prompts.",
    ("ISO 27001", "PASSWORD"): "Rotate exposed password. Enforce secret scanning in CI/CD pipelines.",
    ("INTERNAL", "SECRET"): "Remove API keys and passwords. Use a secrets manager for credential injection.",
    ("INTERNAL", "BLOCKED_KEYWORD"): "Remove or rephrase content containing restricted keywords before submitting to AI services.",
}

def _get_remediation_fallback(regulation: str, entity_type: str, description: str = "") -> str:
    """Fast fallback: look up a remediation suggestion from the static map."""
    key = (regulation, entity_type)
    if key in REMEDIATION_MAP:
        return REMEDIATION_MAP[key]
    for (reg, _), remedy in REMEDIATION_MAP.items():
        if reg == regulation:
            return remedy
    if "block" in description.lower() or "prohibit" in description.lower():
        return "Block or redact the detected sensitive data before forwarding to external services."
    return "Review and redact sensitive data elements. Consult your compliance officer for specific guidance."


async def _llm_generate_remediations(violations: list[dict], llm_service, rag_service=None) -> None:
    """Use RAG context + LLM to generate contextual remediation suggestions for each violation.

    Flow:
      1. Query RAG knowledge base for relevant regulation excerpts per violation
      2. Include RAG context in the LLM prompt so remediations cite real regulations
      3. Fallback to static map only if both RAG and LLM are unavailable
    """
    if not violations:
        return

    # ── Step 1: Gather RAG context for the violations ─────────────────────
    rag_context = ""
    if rag_service:
        try:
            # Build a combined query from all violation regulations + descriptions
            regulations_mentioned = set()
            query_parts = []
            for v in violations:
                reg = v.get("regulation", "")
                if reg and reg not in ("UNKNOWN", "CUSTOM"):
                    regulations_mentioned.add(reg)
                query_parts.append(f"{reg} {v.get('description', '')} {' '.join(v.get('entities', [])[:2])}")

            rag_query = "Remediation guidance for: " + "; ".join(query_parts[:5])
            chunks = await rag_service.similarity_search(rag_query, "regulations", top_k=5)

            if chunks:
                context_parts = []
                for i, c in enumerate(chunks, 1):
                    source = c.get("source", "Unknown")
                    content = c.get("content", "")[:300]
                    context_parts.append(f"[{i}] ({source}): {content}")
                rag_context = "\n".join(context_parts)
                logger.info("RAG context retrieved for remediations: %d chunks", len(chunks))
        except Exception as e:
            logger.warning("RAG retrieval for remediations failed: %s", e)

    # ── Step 2: Build violation summary for LLM ───────────────────────────
    viol_lines = []
    for i, v in enumerate(violations):
        viol_lines.append(
            f"{i+1}. [{v.get('severity','HIGH')}] {v.get('regulation','UNKNOWN')} "
            f"{v.get('article','N/A')} — {v.get('description','')} "
            f"(tool: {v.get('tool_name','')}, entities: {', '.join(v.get('entities',[])[:3])})"
        )

    # ── Step 3: Call LLM with RAG context ─────────────────────────────────
    if not llm_service or not llm_service.llm:
        logger.info("LLM unavailable — using fallback remediations")
        _apply_fallback_remediations(violations)
        return

    system_prompt = (
        "You are a compliance remediation advisor. For each numbered violation below, "
        "provide a specific, actionable remediation in ONE short sentence (max 30 words).\n"
        f"Return ONLY a JSON array of exactly {len(violations)} strings. No markdown, no explanation.\n"
        "Be specific: mention techniques like tokenization, masking, encryption, "
        "pseudonymization, BAA agreements, data minimization. "
        "Cite regulation articles from the context when available."
    )

    user_msg = "Violations requiring remediation:\n" + "\n".join(viol_lines)
    if rag_context:
        user_msg += "\n\nRelevant Regulation Excerpts (use these for context):\n" + rag_context

    try:
        raw = await llm_service.analyze_text(user_msg, system_prompt, max_tokens=512)
        logger.info("LLM remediation raw response (%d chars): %s", len(raw), raw[:300])
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        # Try to find JSON array in the response
        start_idx = raw.find("[")
        end_idx = raw.rfind("]")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            raw = raw[start_idx:end_idx + 1]
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            # Apply LLM remediations to as many violations as possible
            for i, viol in enumerate(violations):
                if i < len(parsed) and parsed[i] and str(parsed[i]).strip():
                    viol["remediation"] = str(parsed[i]).strip()
                else:
                    _apply_single_fallback(viol)
            logger.info("LLM+RAG remediation applied to %d/%d violations",
                        min(len(parsed), len(violations)), len(violations))
            return
    except Exception as e:
        logger.warning("LLM remediation generation failed (using fallback): %s", e)

    _apply_fallback_remediations(violations)


def _apply_single_fallback(viol: dict) -> None:
    """Apply static-map fallback remediation to a single violation."""
    entity_type = "PII"
    if viol.get("entities"):
        first = viol["entities"][0]
        entity_type = first.split(":")[0].strip() if ":" in first else first
    viol["remediation"] = _get_remediation_fallback(
        viol.get("regulation", "UNKNOWN"), entity_type, viol.get("description", "")
    )


def _apply_fallback_remediations(violations: list[dict]) -> None:
    """Apply static-map fallback remediation to all violations."""
    for viol in violations:
        _apply_single_fallback(viol)


# ─── RAG + LLM powered violation scanning ─────────────────────────────────────

async def _rag_lookup_violations(text: str, rag_service) -> list[dict]:
    """Use RAG similarity search against compliance_rules collection to find applicable regulations."""
    if not rag_service or not text or len(text.strip()) < 5:
        return []
    try:
        chunks = await rag_service.similarity_search(text, "compliance_rules", top_k=3)
        results = []
        for chunk in chunks:
            if chunk.get("relevance_score", 0) < 0.25:
                continue
            meta = chunk.get("metadata", {})
            results.append({
                "regulation": meta.get("regulation", "UNKNOWN"),
                "article": meta.get("article", "N/A"),
                "category": meta.get("category", "CUSTOM"),
                "content": chunk.get("content", ""),
                "relevance": chunk.get("relevance_score", 0),
            })
        return results
    except Exception as e:
        logger.warning("RAG compliance lookup failed: %s", e)
        return []


async def _llm_analyze_violations(text: str, entity_summary: str, rag_context: str,
                                   llm_service) -> list[dict]:
    """Ask LLM to analyze detected entities against regulation context and produce violation details."""
    if not llm_service or not llm_service.llm:
        return []

    system_prompt = (
        "You are a compliance analysis engine. Given detected data entities and relevant regulation excerpts, "
        "determine which specific regulation articles are violated and why.\n"
        "Respond ONLY with a JSON array. Each element must have these keys:\n"
        '  "regulation": (e.g. "GDPR", "HIPAA", "PCI-DSS", "ISO 27001")\n'
        '  "article": (e.g. "Art. 9(1)", "§164.502(a)", "Req 3.4")\n'
        '  "description": (one sentence explaining the violation)\n'
        '  "severity": ("CRITICAL", "HIGH", or "MEDIUM")\n'
        "If no violations apply, return an empty array: []\n"
        "Do NOT include markdown fences. Output raw JSON only."
    )
    user_msg = (
        f"Detected entities in AI agent tool chain:\n{entity_summary}\n\n"
        f"Relevant regulation excerpts:\n{rag_context}\n\n"
        f"Original text snippet:\n{text[:500]}"
    )

    try:
        raw = await llm_service.analyze_text(user_msg, system_prompt, max_tokens=800)
        raw = raw.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except Exception as e:
        logger.debug("LLM violation analysis parse failed (will use RAG fallback): %s", e)
    return []


def _scan_text_for_entities(text: str) -> tuple[list[dict], set[str]]:
    """Use the PII detector to extract entities from text. Returns (entity_list, classifications)."""
    from app.services.context_detector import PIIDetector, ENTITY_TO_CLASSIFICATION
    detector = PIIDetector()
    entities, _ = detector.scan(text)
    results = []
    classifications = set()
    seen = set()
    for entity in entities:
        if entity.type in seen:
            continue
        seen.add(entity.type)
        cls = ENTITY_TO_CLASSIFICATION.get(entity.type, "CUSTOM")
        classifications.add(cls)
        results.append({
            "type": entity.type,
            "value": entity.value[:50],
            "classification": cls,
        })
    return results, classifications


async def _scan_text_for_violations(text: str, tool_name: str, sequence: int, field: str,
                                     rag_service, llm_service) -> list[dict]:
    """Scan text using PII regex + RAG lookup + LLM analysis for violation mapping."""
    violations = []
    if not text or len(text.strip()) < 5:
        return violations

    # Stage 1: Fast entity detection (regex-based)
    entities, classifications = _scan_text_for_entities(text)

    # Stage 2: RAG similarity search for applicable regulations
    rag_matches = await _rag_lookup_violations(text, rag_service)

    # Build entity summary for LLM
    entity_summary = "\n".join(
        f"- {e['type']} ({e['classification']}): {e['value']}" for e in entities
    ) if entities else "No specific entities detected via regex."

    rag_context = "\n".join(
        f"- [{m['regulation']} {m['article']}] (relevance {m['relevance']:.0%}): {m['content'][:200]}"
        for m in rag_matches
    ) if rag_matches else "No closely matching regulation excerpts found."

    # Stage 3: LLM analysis (if available and entities/rag matches exist)
    llm_violations = []
    if (entities or rag_matches) and llm_service and llm_service.llm:
        llm_violations = await _llm_analyze_violations(text, entity_summary, rag_context, llm_service)

    # Build violations from LLM response (filter out empty/invalid entries)
    if llm_violations:
        for lv in llm_violations:
            sev = lv.get("severity", "").strip().upper()
            reg = lv.get("regulation", "").strip()
            desc = lv.get("description", "").strip()
            if not sev or sev not in ("CRITICAL", "HIGH", "MEDIUM", "LOW") or not desc:
                continue
            violations.append({
                "tool_name": tool_name,
                "tool_sequence": sequence,
                "field": field,
                "violation_type": reg or "CUSTOM",
                "regulation": reg or "UNKNOWN",
                "article": f"{reg} {lv.get('article', 'N/A')}".strip(),
                "description": desc,
                "severity": sev,
                "entities": [f"{e['type']}: {e['value']}" for e in entities[:3]] if entities else ["LLM-detected"],
            })
    else:
        # Fallback: map entities to violations using RAG matches
        seen_regs = set()
        for entity in entities:
            best_match = None
            for m in rag_matches:
                entity_types_str = m.get("metadata", {}).get("entity_types", "") if isinstance(m, dict) else ""
                # Check if entity type appears in the RAG document's entity_types metadata
                if entity["type"] in (m.get("category", "") + " " + str(m.get("content", ""))):
                    best_match = m
                    break
            if not best_match and rag_matches:
                best_match = rag_matches[0]

            if best_match:
                reg_key = f"{best_match['regulation']}_{best_match['article']}"
                if reg_key not in seen_regs:
                    seen_regs.add(reg_key)
                    severity = "CRITICAL" if entity["classification"] in ("PHI", "PCI", "SECRET") else "HIGH"
                    violations.append({
                        "tool_name": tool_name,
                        "tool_sequence": sequence,
                        "field": field,
                        "violation_type": entity["classification"],
                        "regulation": best_match["regulation"],
                        "article": f"{best_match['regulation']} {best_match['article']}",
                        "description": best_match["content"][:150],
                        "severity": severity,
                        "entities": [f"{entity['type']}: {entity['value']}"],
                    })
            else:
                # Map classification to regulation when RAG has no match
                cls_to_reg = {
                    "PHI": "HIPAA", "PCI": "PCI-DSS", "PII": "GDPR",
                    "SECRET": "ISO 27001", "CREDENTIAL": "ISO 27001",
                }
                fallback_reg = cls_to_reg.get(entity["classification"], entity["classification"])
                violations.append({
                    "tool_name": tool_name,
                    "tool_sequence": sequence,
                    "field": field,
                    "violation_type": entity["classification"],
                    "regulation": fallback_reg,
                    "article": f"{fallback_reg} (auto-detected)",
                    "description": f"Detected {entity['type']} entity ({entity['classification']})",
                    "severity": "HIGH",
                    "entities": [f"{entity['type']}: {entity['value']}"],
                })

    return violations


async def _scan_agent_request(payload: AgentRequestCreate, rag_service, llm_service) -> dict:
    """Scan all tool chain inputs/outputs for compliance violations using RAG + LLM.

    PERFORMANCE: All text segments are scanned for entities via fast regex first,
    then a SINGLE batched LLM call analyzes all findings. This reduces LLM calls
    from N (per-segment) to exactly 2 (1 violation analysis + 1 remediation).
    """
    start = time.time()
    all_violations = []
    all_classifications = set()
    all_regulations = set()
    all_policies = set()

    # ── Stage 1: Fast regex entity detection on ALL segments (no LLM) ─────
    # Collect all text segments with their source metadata
    text_segments = []  # (text, tool_name, sequence, field)
    if payload.user_input:
        text_segments.append((payload.user_input, "user_input", 0, "input"))

    for tool in payload.tool_chain:
        input_text = json.dumps(tool.input) if isinstance(tool.input, dict) else str(tool.input)
        text_segments.append((input_text, tool.tool_name, tool.sequence, "input"))

        output_text = ""
        if isinstance(tool.output, dict):
            output_text = tool.output.get("summary", "") + " " + json.dumps(tool.output)
        else:
            output_text = str(tool.output)
        text_segments.append((output_text, tool.tool_name, tool.sequence, "output"))

        if tool.reasoning:
            text_segments.append((tool.reasoning, tool.tool_name, tool.sequence, "reasoning"))

    if payload.final_output:
        text_segments.append((json.dumps(payload.final_output), "final_output", 999, "output"))

    # Fast regex scan on each segment (< 10ms total, no LLM)
    segment_entities = []  # (entities, classifications, tool_name, sequence, field)
    all_entity_lines = []
    combined_text_for_rag = ""
    for text, tool_name, sequence, field in text_segments:
        if not text or len(text.strip()) < 5:
            continue
        entities, classifications = _scan_text_for_entities(text)
        if entities:
            segment_entities.append((entities, classifications, tool_name, sequence, field))
            for e in entities:
                all_entity_lines.append(
                    f"- [{tool_name}/{field}] {e['type']} ({e['classification']}): {e['value']}"
                )
        combined_text_for_rag += " " + text

    # ── Stage 2: Single RAG lookup with combined text (< 200ms) ───────────
    rag_matches = await _rag_lookup_violations(combined_text_for_rag[:2000], rag_service)
    rag_context = "\n".join(
        f"- [{m['regulation']} {m['article']}] (relevance {m['relevance']:.0%}): {m['content'][:200]}"
        for m in rag_matches
    ) if rag_matches else "No closely matching regulation excerpts found."

    # ── Stage 3: SINGLE batched LLM call for violation analysis ───────────
    entity_summary = "\n".join(all_entity_lines) if all_entity_lines else "No specific entities detected."
    llm_violations = []
    if (all_entity_lines or rag_matches) and llm_service and llm_service.llm:
        llm_violations = await _llm_analyze_violations(
            combined_text_for_rag[:1500], entity_summary, rag_context, llm_service
        )

    # Map LLM violations back to their source segments
    if llm_violations:
        for lv in llm_violations:
            sev = lv.get("severity", "").strip().upper()
            reg = lv.get("regulation", "").strip()
            desc = lv.get("description", "").strip()
            if not sev or sev not in ("CRITICAL", "HIGH", "MEDIUM", "LOW") or not desc:
                continue
            # Find which segment this violation maps to
            best_tool = "user_input"
            best_seq = 0
            best_field = "input"
            for entities, _, tool_name, sequence, field in segment_entities:
                for e in entities:
                    if e["type"].lower() in desc.lower() or e["classification"].lower() in reg.lower():
                        best_tool = tool_name
                        best_seq = sequence
                        best_field = field
                        break
            all_violations.append({
                "tool_name": best_tool,
                "tool_sequence": best_seq,
                "field": best_field,
                "violation_type": reg or "CUSTOM",
                "regulation": reg or "UNKNOWN",
                "article": f"{reg} {lv.get('article', 'N/A')}".strip(),
                "description": desc,
                "severity": sev,
                "entities": [f"{e['type']}: {e['value']}" for seg in segment_entities
                             for e in seg[0][:3]] if segment_entities else ["LLM-detected"],
            })
    else:
        # Fallback: map entities to violations using RAG matches (no LLM needed)
        for entities, classifications, tool_name, sequence, field in segment_entities:
            seen_regs = set()
            for entity in entities:
                best_match = None
                for m in rag_matches:
                    if entity["type"] in (m.get("category", "") + " " + str(m.get("content", ""))):
                        best_match = m
                        break
                if not best_match and rag_matches:
                    best_match = rag_matches[0]

                if best_match:
                    reg_key = f"{best_match['regulation']}_{best_match['article']}"
                    if reg_key not in seen_regs:
                        seen_regs.add(reg_key)
                        severity = "CRITICAL" if entity["classification"] in ("PHI", "PCI", "SECRET") else "HIGH"
                        all_violations.append({
                            "tool_name": tool_name,
                            "tool_sequence": sequence,
                            "field": field,
                            "violation_type": entity["classification"],
                            "regulation": best_match["regulation"],
                            "article": f"{best_match['regulation']} {best_match['article']}",
                            "description": best_match["content"][:150],
                            "severity": severity,
                            "entities": [f"{entity['type']}: {entity['value']}"],
                        })
                else:
                    cls_to_reg = {
                        "PHI": "HIPAA", "PCI": "PCI-DSS", "PII": "GDPR",
                        "SECRET": "ISO 27001", "CREDENTIAL": "ISO 27001",
                    }
                    fallback_reg = cls_to_reg.get(entity["classification"], entity["classification"])
                    all_violations.append({
                        "tool_name": tool_name,
                        "tool_sequence": sequence,
                        "field": field,
                        "violation_type": entity["classification"],
                        "regulation": fallback_reg,
                        "article": f"{fallback_reg} (auto-detected)",
                        "description": f"Detected {entity['type']} entity ({entity['classification']})",
                        "severity": "HIGH",
                        "entities": [f"{entity['type']}: {entity['value']}"],
                    })

    # ── Aggregate classifications & regulations ────────────────────────────
    for viol in all_violations:
        all_classifications.add(viol["violation_type"])
        all_regulations.add(viol["regulation"])

    # ── Severity-weighted risk scoring ─────────────────────────────────────
    severity_weights = {"CRITICAL": 30, "HIGH": 20, "MEDIUM": 10, "LOW": 5}
    weighted_score = 0
    for viol in all_violations:
        weighted_score += severity_weights.get(viol.get("severity", "MEDIUM"), 10)

    # Factor in data volume from tool outputs (e.g. record_count)
    data_volume_factor = 1.0
    for tool in payload.tool_chain:
        if isinstance(tool.output, dict):
            rc = tool.output.get("record_count", 0)
            if rc and int(rc) > 100:
                data_volume_factor = min(2.0, 1.0 + (int(rc) / 1000))
    weighted_score = int(weighted_score * data_volume_factor)

    # Also factor in unique entity count
    total_entities = sum(len(v.get("entities", [])) for v in all_violations)
    if total_entities > 5:
        weighted_score += (total_entities - 5) * 2

    risk_score = min(100, max(0, weighted_score))

    # ── Remediation suggestions per violation (RAG + LLM with fallback) ──
    await _llm_generate_remediations(all_violations, llm_service, rag_service)

    # ── Policy-linked evaluation ───────────────────────────────────────────
    recommended_action = "AUDIT"  # default
    if all_violations:
        has_critical = any(v["severity"] == "CRITICAL" for v in all_violations)
        has_high = any(v["severity"] == "HIGH" for v in all_violations)
        if has_critical or risk_score >= 80:
            recommended_action = "BLOCK"
        elif has_high or risk_score >= 50:
            recommended_action = "REDACT"

    compliance_status = "CLEAN" if not all_violations else "VIOLATION"

    if all_violations:
        unique_regs = sorted(all_regulations)
        unique_types = sorted(all_classifications)
        action_note = f" Recommended action: {recommended_action}."
        summary = (f"Detected {len(all_violations)} violation(s) across "
                   f"{len(set(v['tool_name'] for v in all_violations))} tool(s). "
                   f"Data types: {', '.join(unique_types)}. "
                   f"Regulations: {', '.join(unique_regs)}.{action_note}")
    else:
        summary = "No compliance violations detected."

    processing_time = int((time.time() - start) * 1000)

    return {
        "compliance_status": compliance_status,
        "violations": all_violations,
        "data_classifications": sorted(all_classifications),
        "regulations_applicable": sorted(all_regulations),
        "risk_score": risk_score,
        "policies_triggered": sorted(all_policies),
        "scan_summary": summary,
        "processing_time_ms": processing_time,
        "recommended_action": recommended_action,
    }


@router.post("")
async def ingest_agent_request(payload: AgentRequestCreate, request: Request,
                                db: AsyncSession = Depends(get_db)):
    """Ingest a producer agent pipeline result and run compliance scan.
    NOTE: Governance server ALWAYS accepts and records requests for monitoring/audit.
    If the agent is blocked, the response includes agent_blocked=true so the
    producer (via MCP) knows to stop submitting further queries."""

    # ── Check if agent is already blocked (for response metadata only) ────
    pre_blocked = False
    pre_blocked_reason = ""
    if payload.source_app:
        blocked = await db.execute(
            select(BlockedAgentModel).where(BlockedAgentModel.source_app == payload.source_app)
        )
        blocked_record = blocked.scalar_one_or_none()
        if blocked_record:
            pre_blocked = True
            pre_blocked_reason = blocked_record.reason or "Previously blocked due to compliance violations"
            logger.warning("[BLOCKED AGENT SUBMISSION] %s submitted despite being blocked — recording for audit",
                          payload.source_app)

    # ── Detect industry from content if not provided ─────────────────────
    full_text = payload.user_input or ""
    for tool in payload.tool_chain:
        if isinstance(tool.output, dict):
            full_text += " " + tool.output.get("summary", "")
        full_text += " " + tool.description + " " + tool.reasoning
    if payload.final_output:
        full_text += " " + json.dumps(payload.final_output)

    detected_industry = payload.industry or _detect_industry(full_text)

    rag_service = getattr(request.app.state, "rag_service", None)
    llm_service = getattr(request.app.state, "llm_service", None)

    # Run compliance scan using RAG + LLM
    scan_result = await _scan_agent_request(payload, rag_service, llm_service)

    # ── Policy-linked evaluation ────────────────────────────────────────
    policy_engine = getattr(request.app.state, "policy_engine", None)
    policies_triggered = []
    if policy_engine:
        try:
            all_policies = policy_engine.get_all_policies_memory()
            for pol in all_policies:
                if not pol.get("enabled", True):
                    continue
                conds = pol.get("conditions", {})
                pol_cls = conds.get("data_classifications", [])
                pol_patterns = conds.get("patterns", [])
                # Check keyword-blocking policies — scan each tool for ALL blocked keywords
                blocked_kw = conds.get("blocked_keywords", [])
                if blocked_kw:
                    policy_matched = False
                    # Build per-source text segments for accurate tool attribution
                    text_segments = []
                    if payload.user_input:
                        text_segments.append(("user_input", 0, "input", payload.user_input.lower()))
                    for tool in payload.tool_chain:
                        inp = json.dumps(tool.input or {}).lower()
                        out_raw = tool.output
                        out = ""
                        if isinstance(out_raw, dict):
                            out = (out_raw.get("summary", "") + " " + json.dumps(out_raw)).lower()
                        else:
                            out = str(out_raw or "").lower()
                        reasoning = (tool.reasoning or "").lower()
                        text_segments.append((tool.tool_name, tool.sequence, "input", inp))
                        text_segments.append((tool.tool_name, tool.sequence, "output", out))
                        if reasoning:
                            text_segments.append((tool.tool_name, tool.sequence, "reasoning", reasoning))
                    if payload.final_output:
                        text_segments.append(("final_output", 999, "output", json.dumps(payload.final_output).lower()))

                    # Collect keyword matches grouped by tool for concise violations
                    tool_kw_map: dict[str, dict] = {}  # tool_name -> {info + set of keywords}
                    for seg_tool, seg_seq, seg_field, seg_text in text_segments:
                        matched_kws = [kw for kw in blocked_kw if kw.lower() in seg_text]
                        if matched_kws:
                            if seg_tool not in tool_kw_map:
                                tool_kw_map[seg_tool] = {"seq": seg_seq, "field": seg_field, "keywords": set()}
                            tool_kw_map[seg_tool]["keywords"].update(matched_kws)

                    policy_matched = bool(tool_kw_map)
                    for t_name, info in tool_kw_map.items():
                        kw_list = sorted(info["keywords"])
                        scan_result["violations"].append({
                            "tool_name": t_name,
                            "tool_sequence": info["seq"],
                            "field": info["field"],
                            "violation_type": "INTERNAL",
                            "regulation": pol.get("regulation", "INTERNAL"),
                            "article": pol["id"],
                            "description": (
                                f"Blocked keyword(s) detected: {', '.join(kw_list)}. "
                                f"Policy: {pol['name']}"
                            ),
                            "severity": "CRITICAL",
                            "entities": [f"BLOCKED_KEYWORD: {kw}" for kw in kw_list],
                            "remediation": "",
                        })
                    if policy_matched:
                        policies_triggered.append(pol["id"])
                        if pol.get("action") == "BLOCK":
                            scan_result["recommended_action"] = "BLOCK"
                # Check classification-based policies
                if pol_cls and any(c in scan_result["data_classifications"] for c in pol_cls):
                    policies_triggered.append(pol["id"])
                    if pol.get("action") == "BLOCK" and scan_result["recommended_action"] != "BLOCK":
                        has_matching_pattern = not pol_patterns
                        if pol_patterns:
                            all_entity_types = set()
                            for v in scan_result["violations"]:
                                for e in v.get("entities", []):
                                    all_entity_types.add(e.split(":")[0].strip() if ":" in e else e)
                            has_matching_pattern = any(p in all_entity_types for p in pol_patterns)
                        if has_matching_pattern:
                            scan_result["recommended_action"] = "BLOCK"
        except Exception as e:
            logger.warning("Policy evaluation failed: %s", e)

    scan_result["policies_triggered"] = sorted(set(policies_triggered))
    if scan_result["recommended_action"] == "BLOCK":
        scan_result["compliance_status"] = "VIOLATION"

    # Generate RAG+LLM remediations for any policy-added violations that have empty remediation
    empty_rem_viols = [v for v in scan_result["violations"] if not v.get("remediation")]
    if empty_rem_viols:
        await _llm_generate_remediations(empty_rem_viols, llm_service, rag_service)

    # Recalculate summary & risk if policy evaluation added new violations
    if policies_triggered:
        all_v = scan_result["violations"]
        # Recompute risk score including keyword violations
        severity_weights = {"CRITICAL": 30, "HIGH": 20, "MEDIUM": 10, "LOW": 5}
        new_score = sum(severity_weights.get(v.get("severity", "MEDIUM"), 10) for v in all_v)
        scan_result["risk_score"] = min(100, max(scan_result["risk_score"], new_score))
        # Rebuild summary
        unique_types = sorted(set(v.get("violation_type", "") for v in all_v))
        unique_regs = sorted(set(v.get("regulation", "") for v in all_v))
        unique_tools = set(v.get("tool_name", "") for v in all_v)
        action_note = f" Recommended action: {scan_result['recommended_action']}."
        scan_result["scan_summary"] = (
            f"Detected {len(all_v)} violation(s) across {len(unique_tools)} tool(s). "
            f"Data types: {', '.join(unique_types)}. "
            f"Regulations: {', '.join(unique_regs)}.{action_note}"
        )
        # Add any new classifications/regulations
        scan_result["data_classifications"] = sorted(set(scan_result["data_classifications"]) | set(unique_types))
        scan_result["regulations_applicable"] = sorted(set(scan_result["regulations_applicable"]) | set(unique_regs))

    # Store in DB
    record = AgentRequestModel(
        request_id=payload.request_id,
        title=payload.title,
        source_app=payload.source_app,
        user_name=payload.user_name,
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

    # ── Audit trail integration ────────────────────────────────────────
    try:
        audit_service = getattr(request.app.state, "audit_service", None)
        if audit_service:
            async with async_session() as audit_db:
                await audit_service.log_event(
                    audit_db,
                    event_type="AGENT_SCAN",
                    details={
                        "agent_request_id": str(record.id),
                        "request_id": payload.request_id,
                        "title": payload.title,
                        "compliance_status": scan_result["compliance_status"],
                        "risk_score": scan_result["risk_score"],
                        "violations_count": len(scan_result["violations"]),
                        "recommended_action": scan_result["recommended_action"],
                        "policies_triggered": scan_result["policies_triggered"],
                        "regulations": scan_result["regulations_applicable"],
                    },
                )
    except Exception as e:
        logger.warning("Audit logging failed: %s", e)

    # Broadcast to WebSocket
    try:
        ws_manager = request.app.state.ws_manager
        await ws_manager.broadcast("interceptions", {
            "type": "agent_request",
            "id": str(record.id),
            "request_id": record.request_id,
            "title": record.title,
            "source_app": record.source_app,
            "compliance_status": record.compliance_status,
            "risk_score": record.risk_score,
            "violations_count": len(scan_result["violations"]),
            "data_classifications": scan_result["data_classifications"],
            "regulations_applicable": scan_result["regulations_applicable"],
            "processing_time_ms": scan_result["processing_time_ms"],
            "recommended_action": scan_result["recommended_action"],
            "policies_triggered": scan_result["policies_triggered"],
        })
    except Exception as e:
        logger.warning("WS broadcast failed: %s", e)

    # ── Auto-block agent if violations with BLOCK action ────────────────
    if scan_result["recommended_action"] == "BLOCK" and payload.source_app:
        try:
            existing_block = await db.execute(
                select(BlockedAgentModel).where(BlockedAgentModel.source_app == payload.source_app)
            )
            if not existing_block.scalar_one_or_none():
                block_record = BlockedAgentModel(
                    source_app=payload.source_app,
                    reason=f"Auto-blocked: {len(scan_result['violations'])} violation(s) detected. "
                           f"Risk score: {scan_result['risk_score']}. Action: BLOCK.",
                    blocked_request_id=payload.request_id,
                )
                db.add(block_record)
                await db.commit()
                logger.warning("[AGENT BLOCKED] %s auto-blocked after request %s",
                              payload.source_app, payload.request_id)
        except Exception as e:
            logger.warning("Auto-block failed: %s", e)

    logger.info("[%s] Agent request %s: %s — %s",
                scan_result["compliance_status"], payload.request_id, payload.title, scan_result["scan_summary"])

    # Determine final block status — blocked if pre_blocked OR newly blocked
    is_blocked = pre_blocked or scan_result["recommended_action"] == "BLOCK"

    return {
        "id": str(record.id),
        "request_id": record.request_id,
        "title": record.title,
        "source_app": record.source_app,
        "user_name": record.user_name,
        "industry": detected_industry,
        "compliance_status": scan_result["compliance_status"],
        "violations": scan_result["violations"],
        "data_classifications": scan_result["data_classifications"],
        "regulations_applicable": scan_result["regulations_applicable"],
        "risk_score": scan_result["risk_score"],
        "scan_summary": scan_result["scan_summary"],
        "processing_time_ms": scan_result["processing_time_ms"],
        "recommended_action": scan_result["recommended_action"],
        "policies_triggered": scan_result["policies_triggered"],
        "agent_blocked": is_blocked,
        "block_reason": pre_blocked_reason if pre_blocked else (
            f"Auto-blocked: {len(scan_result['violations'])} violation(s), risk score {scan_result['risk_score']}"
            if scan_result["recommended_action"] == "BLOCK" else ""
        ),
        "producer_action": "STOP_ALL_QUERIES" if is_blocked else "CONTINUE",
    }


@router.get("")
async def list_agent_requests(request: Request, limit: int = 50, offset: int = 0,
                               status: str = None, source_app: str = None,
                               db: AsyncSession = Depends(get_db)):
    """List agent requests with optional compliance status and deployment (source_app) filter."""
    query = select(AgentRequestModel).order_by(desc(AgentRequestModel.created_at))
    if status:
        query = query.where(AgentRequestModel.compliance_status == status)
    if source_app:
        query = query.where(AgentRequestModel.source_app == source_app)
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()

    return [{
        "id": str(r.id),
        "request_id": r.request_id,
        "title": r.title,
        "source_app": r.source_app,
        "user_name": r.user_name or "",
        "industry": r.industry or "",
        "status": r.status,
        "user_input": r.user_input,
        "tool_chain": r.tool_chain,
        "final_output": r.final_output,
        "metadata_info": r.metadata_info,
        "compliance_status": r.compliance_status,
        "violations": r.violations,
        "data_classifications": r.data_classifications or [],
        "regulations_applicable": r.regulations_applicable or [],
        "risk_score": r.risk_score,
        "policies_triggered": r.policies_triggered or [],
        "recommended_action": r.recommended_action or "AUDIT",
        "scan_summary": r.scan_summary,
        "processing_time_ms": r.processing_time_ms,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in records]


@router.get("/stats")
async def agent_request_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregate stats for agent requests."""
    total = await db.execute(select(func.count(AgentRequestModel.id)))
    violations = await db.execute(
        select(func.count(AgentRequestModel.id)).where(AgentRequestModel.compliance_status == "VIOLATION"))
    clean = await db.execute(
        select(func.count(AgentRequestModel.id)).where(AgentRequestModel.compliance_status == "CLEAN"))
    avg_risk = await db.execute(select(func.avg(AgentRequestModel.risk_score)))

    return {
        "total_requests": total.scalar() or 0,
        "total_violations": violations.scalar() or 0,
        "total_clean": clean.scalar() or 0,
        "avg_risk_score": round(avg_risk.scalar() or 0, 1),
    }


@router.get("/trends")
async def agent_request_trends(db: AsyncSession = Depends(get_db), days: int = 30):
    """Get trend analytics: violation frequency over time, top offending tools, repeat patterns."""
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # 1. Violation frequency by day
    result = await db.execute(
        select(AgentRequestModel).where(AgentRequestModel.created_at >= cutoff)
        .order_by(AgentRequestModel.created_at)
    )
    records = result.scalars().all()

    daily_counts: dict = {}
    for r in records:
        day = r.created_at.strftime("%Y-%m-%d") if r.created_at else "unknown"
        if day not in daily_counts:
            daily_counts[day] = {"date": day, "total": 0, "violations": 0, "clean": 0}
        daily_counts[day]["total"] += 1
        if r.compliance_status == "VIOLATION":
            daily_counts[day]["violations"] += 1
        else:
            daily_counts[day]["clean"] += 1
    daily_trend = sorted(daily_counts.values(), key=lambda x: x["date"])

    # 2. Top offending tools
    tool_violations: dict = {}
    for r in records:
        for v in (r.violations or []):
            tn = v.get("tool_name", "unknown")
            if tn not in tool_violations:
                tool_violations[tn] = {"tool_name": tn, "count": 0, "severities": {}}
            tool_violations[tn]["count"] += 1
            sev = v.get("severity", "MEDIUM")
            tool_violations[tn]["severities"][sev] = tool_violations[tn]["severities"].get(sev, 0) + 1
    top_tools = sorted(tool_violations.values(), key=lambda x: x["count"], reverse=True)[:10]

    # 3. Regulation breakdown
    reg_counts: dict = {}
    for r in records:
        for reg in (r.regulations_applicable or []):
            reg_counts[reg] = reg_counts.get(reg, 0) + 1
    regulation_breakdown = [{"regulation": k, "count": v} for k, v in
                            sorted(reg_counts.items(), key=lambda x: x[1], reverse=True)]

    # 4. Severity distribution
    sev_counts: dict = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for r in records:
        for v in (r.violations or []):
            sev = v.get("severity", "MEDIUM")
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
    severity_distribution = [{"severity": k, "count": v} for k, v in sev_counts.items()]

    # 5. Source app breakdown
    app_counts: dict = {}
    for r in records:
        app = r.source_app or "unknown"
        if app not in app_counts:
            app_counts[app] = {"source_app": app, "total": 0, "violations": 0}
        app_counts[app]["total"] += 1
        if r.compliance_status == "VIOLATION":
            app_counts[app]["violations"] += 1
    source_breakdown = sorted(app_counts.values(), key=lambda x: x["violations"], reverse=True)

    # 6. Risk score trend (avg per day)
    risk_trend = []
    for day_data in daily_trend:
        day_records = [r for r in records if r.created_at and r.created_at.strftime("%Y-%m-%d") == day_data["date"]]
        avg_risk = sum(r.risk_score or 0 for r in day_records) / max(1, len(day_records))
        risk_trend.append({"date": day_data["date"], "avg_risk": round(avg_risk, 1)})

    return {
        "daily_trend": daily_trend,
        "top_offending_tools": top_tools,
        "regulation_breakdown": regulation_breakdown,
        "severity_distribution": severity_distribution,
        "source_breakdown": source_breakdown,
        "risk_trend": risk_trend,
        "period_days": days,
        "total_scanned": len(records),
    }


@router.get("/{request_id}")
async def get_agent_request(request_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single agent request by request_id."""
    result = await db.execute(
        select(AgentRequestModel).where(AgentRequestModel.request_id == request_id))
    record = result.scalar_one_or_none()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent request not found")

    return {
        "id": str(record.id),
        "request_id": record.request_id,
        "title": record.title,
        "source_app": record.source_app,
        "user_name": record.user_name or "",
        "industry": record.industry or "",
        "status": record.status,
        "user_input": record.user_input,
        "tool_chain": record.tool_chain,
        "final_output": record.final_output,
        "metadata_info": record.metadata_info,
        "compliance_status": record.compliance_status,
        "violations": record.violations,
        "data_classifications": record.data_classifications or [],
        "regulations_applicable": record.regulations_applicable or [],
        "risk_score": record.risk_score,
        "policies_triggered": record.policies_triggered or [],
        "recommended_action": record.recommended_action or "AUDIT",
        "scan_summary": record.scan_summary,
        "processing_time_ms": record.processing_time_ms,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.get("/deployments/list")
async def list_deployments(db: AsyncSession = Depends(get_db)):
    """List all unique deployments (source_app names) with their request counts and block status."""
    result = await db.execute(
        select(
            AgentRequestModel.source_app,
            func.count(AgentRequestModel.id).label("total"),
            func.count(AgentRequestModel.id).filter(
                AgentRequestModel.compliance_status == "VIOLATION"
            ).label("violations"),
        ).where(AgentRequestModel.source_app != "")
        .group_by(AgentRequestModel.source_app)
        .order_by(desc(func.count(AgentRequestModel.id)))
    )
    rows = result.all()

    # Check which agents are blocked
    blocked_result = await db.execute(select(BlockedAgentModel.source_app))
    blocked_set = {r[0] for r in blocked_result.all()}

    return [{
        "source_app": row[0],
        "total_requests": row[1],
        "violations": row[2],
        "blocked": row[0] in blocked_set,
    } for row in rows]


@router.get("/blocked/list")
async def list_blocked_agents(db: AsyncSession = Depends(get_db)):
    """List all blocked agents."""
    result = await db.execute(
        select(BlockedAgentModel).order_by(desc(BlockedAgentModel.blocked_at))
    )
    records = result.scalars().all()
    return [{
        "id": str(r.id),
        "source_app": r.source_app,
        "reason": r.reason,
        "blocked_request_id": r.blocked_request_id,
        "blocked_at": r.blocked_at.isoformat() if r.blocked_at else None,
    } for r in records]


@router.post("/blocked/{source_app}")
async def block_agent(source_app: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Manually block an agent deployment."""
    existing = await db.execute(
        select(BlockedAgentModel).where(BlockedAgentModel.source_app == source_app)
    )
    if existing.scalar_one_or_none():
        return {"message": f"Agent '{source_app}' is already blocked"}

    record = BlockedAgentModel(
        source_app=source_app,
        reason="Manually blocked by administrator",
        blocked_request_id="manual",
    )
    db.add(record)
    await db.commit()
    return {"message": f"Agent '{source_app}' has been blocked", "source_app": source_app}


@router.delete("/blocked/{source_app}")
async def unblock_agent(source_app: str, db: AsyncSession = Depends(get_db)):
    """Unblock a previously blocked agent deployment."""
    result = await db.execute(
        select(BlockedAgentModel).where(BlockedAgentModel.source_app == source_app)
    )
    record = result.scalar_one_or_none()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Agent '{source_app}' is not blocked")

    await db.delete(record)
    await db.commit()
    return {"message": f"Agent '{source_app}' has been unblocked", "source_app": source_app}

"""
Context Identification Layer (CIL) — full pipeline:

  [Browser Extension / Telemetry Collector]
       ↓  Step 1 — Collect signals
  [Context Classification Engine]          ← embedding multi-label classifier
       ↓  Step 2 — Business function, purpose, cross-border
  [PII Detection Model (NER)]             ← regex + keyword fast scan
       ↓  Step 3 — Entity extraction
  [Intent Detection (LLM)]                ← Ollama local model
       ↓  Step 4 — Intent classification
  [Regulatory Control LLM]                ← Ollama local model
       ↓  Step 5 — Build Context Object
  [Policy Engine]
       ↓
  [Audit Log]
"""

import re
import time
import json
import logging
from typing import Optional
from app.models.schemas import (
    ContextAnalysisRequest, ContextAnalysisResult, ContextObject,
    DetectedEntity, Violation, ActionType, Severity, IntentType,
    TelemetrySignals,
)

logger = logging.getLogger(__name__)

# ─── Regex patterns for PII / NER fast scan ──────────────────────────────────

PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "CREDIT_CARD": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "PHONE": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "DATE_OF_BIRTH": r"\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b",
    "MEDICAL_RECORD_NUMBER": r"\b(?:MRN|mrn)[\s:#-]?\d{4,10}\b",
    "ICD10_CODE": r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b",
    "MEDICATION": r"\b(?:metformin|insulin|lisinopril|atorvastatin|amlodipine|omeprazole|levothyroxine|simvastatin|losartan|albuterol)\s*\d*\s*(?:mg|mcg|ml)?\b",
    "IP_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "API_KEY": r"\b(?:sk-|pk_|api[_-]?key)[A-Za-z0-9_-]{20,}\b",
    "AWS_KEY": r"(?:AKIA|ASIA)[A-Z0-9]{16}",
    "AWS_SECRET": r"(?i)(?:aws_secret_access_key|aws_secret)\s*[=:]\s*\S{20,}",
    "DB_CONNECTION_STRING": r"(?i)(?:postgresql|mysql|mongodb|redis)://[^\s]{10,}",
    "PRIVATE_KEY": r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----",
    "PASSWORD": r"(?i)(?:password|passwd|pwd)\s*[:=]\s*\S+",
    "PAN": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    "AADHAAR": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    "BANK_ACCOUNT": r"(?i)(?:account[_\s]?(?:number|no|num|#)?|a/c)[\s:\"]*(\d{9,18})\b",
    "IFSC": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
}

PHI_KEYWORDS = [
    "patient", "diagnosis", "medical history", "prescription", "treatment",
    "hospital", "physician", "nurse", "surgery", "clinical", "symptoms",
    "blood pressure", "heart rate", "lab results", "radiology", "pathology",
    "health record", "medical record", "pharmacy", "immunization",
    "discharge", "oncology", "cardiology",
]

PCI_KEYWORDS = [
    "credit card", "debit card", "cardholder", "cvv", "cvc", "expiration date",
    "card number", "pan", "payment", "transaction", "merchant", "billing",
]

PII_KEYWORDS = [
    "social security", "driver license", "passport number", "date of birth",
    "home address", "phone number", "email address", "full name",
]

FINANCIAL_KEYWORDS = [
    "pan", "aadhaar", "bank account", "account number", "ifsc",
    "kyc", "annual income", "credit score", "cibil", "loan",
    "npi", "glba", "non-public personal", "financial data",
]

ENTITY_TO_CLASSIFICATION = {
    "SSN": "PII", "EMAIL": "PII", "PHONE": "PII", "DATE_OF_BIRTH": "PII",
    "CREDIT_CARD": "PCI",
    "MEDICAL_RECORD_NUMBER": "PHI", "ICD10_CODE": "PHI", "MEDICATION": "PHI",
    "API_KEY": "SECRET", "AWS_KEY": "SECRET", "AWS_SECRET": "SECRET",
    "DB_CONNECTION_STRING": "SECRET", "PRIVATE_KEY": "SECRET", "PASSWORD": "SECRET",
    "PAN": "PII", "AADHAAR": "PII", "BANK_ACCOUNT": "PII", "IFSC": "PII",
    "FINANCIAL_CONTEXT": "PII",
}

CLASSIFICATION_TO_REGULATION = {
    "PII": ["GDPR"],
    "PHI": ["HIPAA", "GDPR"],
    "PCI": ["PCI-DSS"],
    "SECRET": ["INTERNAL"],
}

# Known external AI domains for destination classification
EXTERNAL_AI_DOMAINS = {
    "chat.openai.com", "api.openai.com", "bard.google.com",
    "claude.ai", "api.anthropic.com", "copilot.microsoft.com",
    "huggingface.co", "replicate.com",
}


def _luhn_check(number: str) -> bool:
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


# ─── Stage 1: PII Detection Model (NER) — regex + keyword fast scan ─────────

class PIIDetector:
    """PII / NER detection via regex patterns and keyword matching."""

    def scan(self, text: str) -> tuple[list[DetectedEntity], bool]:
        entities: list[DetectedEntity] = []
        is_critical = False
        text_lower = text.lower()

        for entity_type, pattern in PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group()
                if entity_type == "CREDIT_CARD":
                    clean = re.sub(r"[\s-]", "", value)
                    if not _luhn_check(clean):
                        continue
                    is_critical = True
                if entity_type in ("API_KEY", "PASSWORD"):
                    is_critical = True
                if entity_type == "AADHAAR":
                    clean = re.sub(r"[\s-]", "", value)
                    if len(clean) != 12 or not any(kw in text_lower for kw in ("aadhaar", "aadhar", "uid", "uidai")):
                        continue
                if entity_type == "BANK_ACCOUNT":
                    value = match.group(1) if match.lastindex else value
                entities.append(DetectedEntity(
                    type=entity_type, value=value,
                    position=[match.start(), match.end()], confidence=1.0,
                ))

        phi_score = sum(1 for kw in PHI_KEYWORDS if kw in text_lower)
        pci_score = sum(1 for kw in PCI_KEYWORDS if kw in text_lower)
        pii_score = sum(1 for kw in PII_KEYWORDS if kw in text_lower)

        if phi_score >= 2:
            entities.append(DetectedEntity(
                type="PHI_CONTEXT", value=f"PHI keywords detected ({phi_score})",
                confidence=min(1.0, phi_score / 5),
            ))
        if pci_score >= 2:
            entities.append(DetectedEntity(
                type="PCI_CONTEXT", value=f"PCI keywords detected ({pci_score})",
                confidence=min(1.0, pci_score / 5),
            ))
        if pii_score >= 2:
            entities.append(DetectedEntity(
                type="PII_CONTEXT", value=f"PII keywords detected ({pii_score})",
                confidence=min(1.0, pii_score / 5),
            ))

        fin_score = sum(1 for kw in FINANCIAL_KEYWORDS if kw in text_lower)
        if fin_score >= 2:
            entities.append(DetectedEntity(
                type="FINANCIAL_CONTEXT", value=f"Financial/NPI keywords detected ({fin_score})",
                confidence=min(1.0, fin_score / 5),
            ))

        return entities, is_critical


# ─── Stage 2: Context Classification Engine (embedding multi-label) ──────────

class ContextClassifier:
    """Multi-label context classifier using sentence-transformer embeddings.

    Predicts: business_function, data_processing_purpose, cross_border,
    internal vs external inference.
    Uses cosine similarity against label embeddings (zero-shot style).
    Falls back to LLM classification when available.
    """

    BUSINESS_FUNCTIONS = ["HR", "Finance", "Clinical", "Engineering", "Legal", "Marketing"]
    DATA_PURPOSES = ["analytics", "treatment", "marketing", "compliance", "support"]

    def __init__(self):
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning("Embedding model unavailable for classifier: %s", e)
        return self._embedder

    def classify(self, text: str, signals: Optional[TelemetrySignals] = None) -> dict:
        """Classify text into business function and data purpose using embeddings."""
        result = {
            "business_function": "Unknown",
            "data_processing_purpose": "unknown",
            "department": "unknown",
            "cross_border": False,
            "llm_destination": "external",
        }

        # Use signals if available
        if signals:
            if signals.user_role:
                role_map = {
                    "doctor": "Clinical", "nurse": "Clinical", "physician": "Clinical",
                    "hr": "HR", "recruiter": "HR",
                    "finance": "Finance", "accountant": "Finance",
                    "engineer": "Engineering", "developer": "Engineering",
                    "lawyer": "Legal", "legal": "Legal",
                    "marketing": "Marketing",
                }
                result["business_function"] = role_map.get(
                    signals.user_role.lower(), "Unknown"
                )
            if signals.active_url:
                domain = signals.active_url.lower().replace("https://", "").replace("http://", "").split("/")[0]
                result["llm_destination"] = "external" if domain in EXTERNAL_AI_DOMAINS else "internal"
            if signals.file_metadata:
                fm = signals.file_metadata.lower()
                if any(kw in fm for kw in ["patient", "medical", "clinical", "discharge"]):
                    result["business_function"] = "Clinical"
                    result["data_processing_purpose"] = "treatment"
                elif any(kw in fm for kw in ["invoice", "payment", "financial"]):
                    result["business_function"] = "Finance"
                    result["data_processing_purpose"] = "analytics"

        # Embedding-based classification
        embedder = self._get_embedder()
        if embedder and text:
            try:
                import numpy as np
                text_emb = embedder.encode([text])
                # Business function
                bf_labels = [f"This text is about {bf} department work" for bf in self.BUSINESS_FUNCTIONS]
                bf_embs = embedder.encode(bf_labels)
                bf_sims = np.dot(text_emb, bf_embs.T)[0]
                best_bf_idx = int(np.argmax(bf_sims))
                if bf_sims[best_bf_idx] > 0.3:
                    result["business_function"] = self.BUSINESS_FUNCTIONS[best_bf_idx]
                # Data purpose
                dp_labels = [f"The purpose of this data processing is {dp}" for dp in self.DATA_PURPOSES]
                dp_embs = embedder.encode(dp_labels)
                dp_sims = np.dot(text_emb, dp_embs.T)[0]
                best_dp_idx = int(np.argmax(dp_sims))
                if dp_sims[best_dp_idx] > 0.3:
                    result["data_processing_purpose"] = self.DATA_PURPOSES[best_dp_idx]
            except Exception as e:
                logger.warning("Embedding classification failed: %s", e)

        # Department inference from business function
        dept_map = {
            "Clinical": "clinical", "HR": "hr", "Finance": "finance",
            "Engineering": "engineering", "Legal": "legal", "Marketing": "marketing",
        }
        result["department"] = dept_map.get(result["business_function"], "unknown")

        return result


# ─── Main CIL Pipeline ──────────────────────────────────────────────────────

class ContextDetector:
    """Full Context Identification Layer pipeline.

    Stage 1: Collect signals (TelemetrySignals)
    Stage 2: Context Classification (embedding multi-label)
    Stage 3: PII Detection / NER (regex + keywords)
    Stage 4: Intent Detection (LLM via Ollama)
    Stage 5: Build Context Object (CIL output)
    → Policy Engine → Audit Log
    """

    def __init__(self, rag_service=None, llm_service=None):
        self.pii_detector = PIIDetector()
        self.context_classifier = ContextClassifier()
        self.rag = rag_service
        self.llm = llm_service

    def _extract_text(self, payload: dict, signals: Optional[TelemetrySignals] = None) -> str:
        """Extract readable text from various AI API payload formats."""
        texts = []
        if "messages" in payload:
            for msg in payload["messages"]:
                if isinstance(msg, dict) and "content" in msg:
                    texts.append(str(msg["content"]))
        if "prompt" in payload:
            texts.append(str(payload["prompt"]))
        if "input" in payload:
            texts.append(str(payload["input"]))
        if signals and signals.prompt:
            texts.append(signals.prompt)
        if not texts:
            texts.append(json.dumps(payload, default=str))
        return "\n".join(texts)

    def _derive_classifications(self, entities: list[DetectedEntity]) -> list[str]:
        classifications = set()
        for entity in entities:
            etype = entity.type.replace("_CONTEXT", "")
            if etype in ENTITY_TO_CLASSIFICATION:
                classifications.add(ENTITY_TO_CLASSIFICATION[etype])
            elif etype in ("PHI", "PCI", "PII"):
                classifications.add(etype)
        return sorted(classifications)

    def _derive_regulations(self, classifications: list[str]) -> list[str]:
        regs = set()
        for cls in classifications:
            for r in CLASSIFICATION_TO_REGULATION.get(cls, []):
                regs.add(r)
        return sorted(regs)

    def _derive_regulatory_scope(self, classifications: list[str]) -> list[str]:
        """Build specific regulatory scope identifiers like HIPAA_164.312, GDPR_Art_5."""
        scope = []
        for cls in classifications:
            if cls == "PHI":
                scope.extend(["HIPAA_164.502", "HIPAA_164.312"])
            if cls == "PII":
                scope.extend(["GDPR_Art_5", "GDPR_Art_6", "GDPR_Art_9"])
            if cls == "PCI":
                scope.extend(["PCI_DSS_Req_3", "PCI_DSS_Req_4"])
            if cls == "SECRET":
                scope.append("INTERNAL_SEC_POLICY")
        return sorted(set(scope))

    def _derive_violations(self, classifications: list[str], destination: str) -> list[Violation]:
        violations = []
        for cls in classifications:
            if cls == "PHI":
                violations.append(Violation(
                    regulation="HIPAA", section="45 CFR §164.502",
                    description=f"PHI transmitted to external AI service ({destination}) without BAA",
                    severity=Severity.CRITICAL,
                ))
            if cls == "PII":
                violations.append(Violation(
                    regulation="GDPR", section="Article 6",
                    description=f"PII sent to AI service ({destination}) without explicit consent",
                    severity=Severity.HIGH,
                ))
            if cls == "PCI":
                violations.append(Violation(
                    regulation="PCI-DSS", section="Requirement 3.4",
                    description=f"Cardholder data sent to AI service ({destination})",
                    severity=Severity.CRITICAL,
                ))
            if cls == "SECRET":
                violations.append(Violation(
                    regulation="INTERNAL", section="Security Policy",
                    description="API key or password detected in AI traffic",
                    severity=Severity.CRITICAL,
                ))
        return violations

    def _calculate_risk(self, violations: list[Violation]) -> int:
        score = 0
        weights = {"CRITICAL": 40, "HIGH": 25, "MEDIUM": 15, "LOW": 5}
        for v in violations:
            score += weights.get(v.severity.value, 10)
        return min(100, score)

    def _recommend_action(self, risk_score: int, is_critical: bool) -> ActionType:
        if is_critical or risk_score >= 80:
            return ActionType.BLOCK
        elif risk_score >= 50:
            return ActionType.REDACT
        elif risk_score >= 20:
            return ActionType.AUDIT
        return ActionType.ALLOW

    async def analyze(self, request: ContextAnalysisRequest) -> ContextAnalysisResult:
        """Run the full CIL pipeline."""
        start = time.time()
        stages: dict = {}
        signals = request.signals

        # ── Extract text ──────────────────────────────────────────────────
        payload_text = self._extract_text(request.payload, signals)

        # ── Stage 1: Signal collection ────────────────────────────────────
        t0 = time.time()
        signals_dict = signals.model_dump() if signals else {}
        stages["signal_collection"] = {
            "status": "ok",
            "signals_present": bool(signals),
            "time_ms": int((time.time() - t0) * 1000),
        }

        # ── Stage 2: Context Classification (embedding multi-label) ──────
        t0 = time.time()
        ctx_class = self.context_classifier.classify(payload_text, signals)
        stages["context_classification"] = {
            "status": "ok",
            "result": ctx_class,
            "time_ms": int((time.time() - t0) * 1000),
        }

        # ── Stage 3: PII Detection / NER ─────────────────────────────────
        t0 = time.time()
        entities, is_critical = self.pii_detector.scan(payload_text)
        stages["pii_detection"] = {
            "status": "ok",
            "entities_found": len(entities),
            "is_critical": is_critical,
            "time_ms": int((time.time() - t0) * 1000),
        }

        # ── Stage 2b: Embedding similarity (RAG) ─────────────────────────
        rag_sources = []
        if self.rag and entities:
            t0 = time.time()
            try:
                rag_result = await self.rag.similarity_search(
                    payload_text, collection_name="violation_patterns", top_k=5
                )
                rag_sources = [c.get("source", "") for c in rag_result if isinstance(c, dict)]
            except Exception:
                pass
            stages["rag_similarity"] = {
                "status": "ok",
                "sources_found": len(rag_sources),
                "time_ms": int((time.time() - t0) * 1000),
            }

        # ── Stage 4: Intent Detection (LLM) ──────────────────────────────
        t0 = time.time()
        intent_str = "unknown"
        if self.llm:
            try:
                intent_str = await self.llm.classify_intent(payload_text)
            except Exception as e:
                logger.warning("Intent detection failed: %s", e)
        intent = IntentType(intent_str) if intent_str in IntentType.__members__.values() else IntentType.UNKNOWN
        stages["intent_detection"] = {
            "status": "ok" if intent != IntentType.UNKNOWN else "fallback",
            "intent": intent.value,
            "time_ms": int((time.time() - t0) * 1000),
        }

        # ── Stage 4b: LLM context enrichment ─────────────────────────────
        if self.llm and not is_critical:
            t0 = time.time()
            try:
                llm_ctx = await self.llm.classify_context(
                    payload_text,
                    json.dumps(signals_dict) if signals_dict else "",
                )
                # Merge LLM results (override embedding results if LLM is confident)
                for key in ("business_function", "data_processing_purpose", "department",
                            "cross_border", "llm_destination"):
                    if llm_ctx.get(key) and llm_ctx[key] not in ("Unknown", "unknown", ""):
                        ctx_class[key] = llm_ctx[key]
            except Exception as e:
                logger.warning("LLM context enrichment failed: %s", e)
            stages["llm_context_enrichment"] = {
                "status": "ok",
                "time_ms": int((time.time() - t0) * 1000),
            }

        # ── Derive classifications, regulations, violations ───────────────
        classifications = self._derive_classifications(entities)
        regulations = self._derive_regulations(classifications)
        regulatory_scope = self._derive_regulatory_scope(classifications)
        violations = self._derive_violations(classifications, request.destination)
        risk_score = self._calculate_risk(violations)
        action = self._recommend_action(risk_score, is_critical)

        # ── Stage 5: Build Context Object (CIL Output) ───────────────────
        data_sensitivity = "NONE"
        if "PHI" in classifications:
            data_sensitivity = "PHI"
        elif "PCI" in classifications:
            data_sensitivity = "PCI"
        elif "PII" in classifications:
            data_sensitivity = "PII"
        elif "SECRET" in classifications:
            data_sensitivity = "SECRET"

        context_object = ContextObject(
            context_id=f"ctx_{request.interception_id}",
            data_sensitivity=data_sensitivity,
            intent=intent,
            department=ctx_class.get("department", ""),
            business_function=ctx_class.get("business_function", ""),
            data_processing_purpose=ctx_class.get("data_processing_purpose", ""),
            llm_destination=ctx_class.get("llm_destination", "external"),
            cross_border=ctx_class.get("cross_border", False),
            regulatory_scope=regulatory_scope,
            entities_detected=entities,
            confidence=0.95 if is_critical else max(0.5, min(0.95, risk_score / 100)),
        )

        elapsed_ms = int((time.time() - start) * 1000)
        stages["total_time_ms"] = elapsed_ms

        return ContextAnalysisResult(
            interception_id=request.interception_id,
            data_classifications=classifications,
            entities_detected=entities,
            regulations_applicable=regulations,
            violations=violations,
            risk_score=risk_score,
            recommended_action=action,
            confidence=context_object.confidence,
            rag_sources=rag_sources,
            processing_time_ms=elapsed_ms,
            context_object=context_object,
            intent=intent,
            pipeline_stages=stages,
        )

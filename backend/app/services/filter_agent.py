import uuid
import time
from typing import TypedDict, Literal, Optional
from app.models.schemas import (
    ContextAnalysisRequest, ContextAnalysisResult, ActionType,
    InterceptionRecord, Direction
)
from app.services.context_detector import ContextDetector
from app.services.policy_engine import PolicyEngine
from app.services.redaction_service import RedactionService


class FilterState(TypedDict):
    interception_id: str
    payload: dict
    payload_text: str
    source_ip: str
    destination: str
    endpoint: str
    direction: str
    context_analysis: Optional[dict]
    applicable_policies: list
    decision: str
    redacted_payload: Optional[dict]
    justification: str
    processing_time_ms: int


class FilterAgent:
    """
    Stateful filter pipeline that processes interceptions through:
    context detection → policy evaluation → action execution → audit.

    Uses a simple state-machine approach (LangGraph-style).
    When langgraph is available, this can be upgraded to a compiled StateGraph.
    """

    def __init__(self, context_detector: ContextDetector, policy_engine: PolicyEngine):
        self.detector = context_detector
        self.policy = policy_engine
        self.redactor = RedactionService()

    async def process(self, request: ContextAnalysisRequest) -> dict:
        start = time.time()

        state: FilterState = {
            "interception_id": request.interception_id or str(uuid.uuid4()),
            "payload": request.payload,
            "payload_text": "",
            "source_ip": request.source_ip,
            "destination": request.destination,
            "endpoint": request.endpoint,
            "direction": request.direction.value if hasattr(request.direction, 'value') else request.direction,
            "context_analysis": None,
            "applicable_policies": [],
            "decision": ActionType.ALLOW.value,
            "redacted_payload": None,
            "justification": "No issues detected",
            "processing_time_ms": 0,
        }

        # Step 1: Context Detection
        state = await self._context_detect(state, request)

        # Step 2: Policy Evaluation
        state = self._policy_evaluate(state)

        # Step 3: Execute Action
        state = self._execute_action(state)

        # Step 4: Finalize
        state["processing_time_ms"] = int((time.time() - start) * 1000)

        return state

    async def _context_detect(self, state: FilterState, request: ContextAnalysisRequest) -> FilterState:
        analysis = await self.detector.analyze(request)
        state["context_analysis"] = analysis.model_dump()
        return state

    def _policy_evaluate(self, state: FilterState) -> FilterState:
        if not state["context_analysis"]:
            return state

        analysis = ContextAnalysisResult(**state["context_analysis"])
        action, policy_ids, justification = self.policy.evaluate(analysis)

        state["decision"] = action.value
        state["applicable_policies"] = policy_ids
        state["justification"] = justification
        return state

    def _execute_action(self, state: FilterState) -> FilterState:
        decision = state["decision"]

        if decision == ActionType.REDACT.value:
            analysis = state["context_analysis"]
            if analysis and analysis.get("entities_detected"):
                from app.models.schemas import DetectedEntity
                entities = [DetectedEntity(**e) for e in analysis["entities_detected"]]
                state["redacted_payload"] = self.redactor.redact_payload(
                    state["payload"], entities, method="token_replacement"
                )
            else:
                state["redacted_payload"] = state["payload"]

        elif decision == ActionType.BLOCK.value:
            state["redacted_payload"] = None

        return state

    def build_interception_record(self, state: dict) -> InterceptionRecord:
        analysis = state.get("context_analysis") or {}
        return InterceptionRecord(
            id=state["interception_id"],
            source_ip=state.get("source_ip", "0.0.0.0"),
            destination=state.get("destination", ""),
            endpoint=state.get("endpoint", ""),
            direction=Direction(state.get("direction", "outbound")),
            data_classifications=analysis.get("data_classifications", []),
            entities_detected=[],
            regulations_applicable=analysis.get("regulations_applicable", []),
            risk_score=analysis.get("risk_score", 0),
            action_taken=ActionType(state["decision"]),
            policies_triggered=state.get("applicable_policies", []),
            justification=state.get("justification", ""),
            processing_time_ms=state.get("processing_time_ms", 0),
        )

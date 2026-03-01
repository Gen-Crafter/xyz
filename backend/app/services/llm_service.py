"""
LLM Service — uses local Ollama model running in Docker.

No authentication required. Connects to Ollama via langchain-ollama.
"""

import logging
from typing import Optional

import httpx

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def get_llm_model(settings: Settings, model_name: str = None) -> ChatOllama:
    """Create a LangChain ChatOllama instance pointing at the local Ollama server."""
    if not model_name:
        model_name = settings.ollama_model

    llm = ChatOllama(
        model=model_name,
        base_url=settings.ollama_base_url,
        temperature=settings.llm_temperature,
        num_predict=settings.llm_max_tokens,
        timeout=settings.llm_request_timeout_seconds,
    )
    return llm


class LlmService:
    """Orchestrates LLM interactions via local Ollama model."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._logger = logging.getLogger("aigp.llm")
        self._llm: Optional[ChatOllama] = None

        try:
            self._llm = get_llm_model(settings)
            self._logger.info("Initialized ChatOllama with model: %s at %s",
                              settings.ollama_model, settings.ollama_base_url)
        except Exception as e:
            self._logger.warning("LLM initialization failed (will retry on demand): %s", e)

    @property
    def llm(self) -> Optional[ChatOllama]:
        if self._llm is None:
            try:
                self._llm = get_llm_model(self.settings)
            except Exception as e:
                self._logger.error("LLM lazy init failed: %s", e)
        return self._llm

    def health(self) -> bool:
        """Check LLM health by pinging Ollama API."""
        try:
            resp = httpx.get(f"{self.settings.ollama_base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception as e:
            self._logger.error("LLM health check failed: %s", e)
            return False

    async def analyze_text(self, text: str, system_prompt: str = "",
                           max_tokens: int | None = None) -> str:
        """Text analysis via LLM. Use max_tokens to cap output length for faster responses."""
        try:
            if not self.llm:
                return ""
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=text))
            # Use a dedicated instance with lower num_predict for speed if specified
            if max_tokens and max_tokens < self.settings.llm_max_tokens:
                fast_llm = ChatOllama(
                    model=self.settings.ollama_model,
                    base_url=self.settings.ollama_base_url,
                    temperature=self.settings.llm_temperature,
                    num_predict=max_tokens,
                    timeout=self.settings.llm_request_timeout_seconds,
                )
                response = fast_llm.invoke(messages)
            else:
                response = self.llm.invoke(messages)
            return response.content if response.content else ""
        except Exception as e:
            self._logger.error("LLM analyze_text failed: %s", e)
            return ""

    async def classify_intent(self, prompt_text: str) -> str:
        """Classify the intent of a prompt using the LLM.

        Returns one of: summarization, translation, prediction,
        decision_support, documentation, code_generation, data_analysis, unknown
        """
        system = (
            "You are an intent classifier. Given a user prompt, respond with EXACTLY "
            "one word from this list: summarization, translation, prediction, "
            "decision_support, documentation, code_generation, data_analysis, unknown. "
            "No explanation, just the single word."
        )
        try:
            if not self.llm:
                return "unknown"
            messages = [SystemMessage(content=system), HumanMessage(content=prompt_text)]
            response = self.llm.invoke(messages)
            raw = (response.content or "unknown").strip().lower().split()[0]
            valid = {"summarization", "translation", "prediction", "decision_support",
                     "documentation", "code_generation", "data_analysis", "unknown"}
            return raw if raw in valid else "unknown"
        except Exception as e:
            self._logger.error("Intent classification failed: %s", e)
            return "unknown"

    async def classify_context(self, prompt_text: str, signals_json: str = "") -> dict:
        """Use the LLM to classify business function, data purpose, cross-border risk.

        Returns dict with keys: business_function, data_processing_purpose,
        department, cross_border, llm_destination.
        """
        system = (
            "You are a context classifier for AI governance. Given a prompt and optional "
            "telemetry signals, respond in EXACTLY this JSON format (no markdown, no explanation):\n"
            '{"business_function":"<HR|Finance|Clinical|Engineering|Legal|Marketing|Unknown>",'
            '"data_processing_purpose":"<analytics|treatment|marketing|compliance|support|unknown>",'
            '"department":"<oncology|cardiology|HR|finance|engineering|legal|unknown>",'
            '"cross_border":false,'
            '"llm_destination":"<external|internal>"}'
        )
        user_msg = f"Prompt: {prompt_text}"
        if signals_json:
            user_msg += f"\nSignals: {signals_json}"
        try:
            if not self.llm:
                return self._default_context()
            messages = [SystemMessage(content=system), HumanMessage(content=user_msg)]
            response = self.llm.invoke(messages)
            import json
            return json.loads(response.content.strip())
        except Exception as e:
            self._logger.error("Context classification failed: %s", e)
            return self._default_context()

    @staticmethod
    def _default_context() -> dict:
        return {
            "business_function": "Unknown",
            "data_processing_purpose": "unknown",
            "department": "unknown",
            "cross_border": False,
            "llm_destination": "external",
        }

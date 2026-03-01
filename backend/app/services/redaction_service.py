import re
import hashlib
import json
from app.models.schemas import DetectedEntity


FAKE_NAMES = ["Jane Doe", "John Roe", "Alex Johnson", "Sam Wilson"]
_fake_idx = 0


class RedactionService:
    """Redacts sensitive data from payloads using configurable strategies."""

    def redact_text(self, text: str, entities: list[DetectedEntity], method: str = "token_replacement") -> str:
        if method == "token_replacement":
            return self._token_replacement(text, entities)
        elif method == "generalization":
            return self._generalization(text, entities)
        elif method == "synthetic":
            return self._synthetic_substitution(text, entities)
        elif method == "hashing":
            return self._hashing(text, entities)
        return self._token_replacement(text, entities)

    def redact_payload(self, payload: dict, entities: list[DetectedEntity], method: str = "token_replacement") -> dict:
        payload_str = json.dumps(payload, default=str)
        redacted_str = self.redact_text(payload_str, entities, method)
        try:
            return json.loads(redacted_str)
        except json.JSONDecodeError:
            return payload

    def _token_replacement(self, text: str, entities: list[DetectedEntity]) -> str:
        sorted_entities = sorted(
            [e for e in entities if e.position and len(e.position) == 2],
            key=lambda e: e.position[0],
            reverse=True,
        )
        result = text
        for entity in sorted_entities:
            start, end = entity.position
            if start < len(result) and end <= len(result):
                token = f"[REDACTED:{entity.type}]"
                result = result[:start] + token + result[end:]

        # Fallback: replace by value for entities without positions
        for entity in entities:
            if not entity.position or len(entity.position) != 2:
                if entity.value and entity.value in result and not entity.type.endswith("_CONTEXT"):
                    result = result.replace(entity.value, f"[REDACTED:{entity.type}]")
        return result

    def _generalization(self, text: str, entities: list[DetectedEntity]) -> str:
        result = text
        for entity in entities:
            if entity.type == "DATE_OF_BIRTH" and entity.value:
                # Keep only year
                year_match = re.search(r"(19|20)\d{2}", entity.value)
                if year_match:
                    result = result.replace(entity.value, year_match.group())
            elif entity.type == "CREDIT_CARD" and entity.value:
                clean = re.sub(r"[\s-]", "", entity.value)
                masked = "****-****-****-" + clean[-4:]
                result = result.replace(entity.value, masked)
            elif entity.type in ("SSN",) and entity.value:
                result = result.replace(entity.value, "***-**-" + entity.value[-4:])
            elif entity.value and not entity.type.endswith("_CONTEXT"):
                result = result.replace(entity.value, f"[GENERALIZED:{entity.type}]")
        return result

    def _synthetic_substitution(self, text: str, entities: list[DetectedEntity]) -> str:
        global _fake_idx
        result = text
        for entity in entities:
            if entity.type == "PERSON_NAME" and entity.value:
                fake = FAKE_NAMES[_fake_idx % len(FAKE_NAMES)]
                _fake_idx += 1
                result = result.replace(entity.value, fake)
            elif entity.type == "EMAIL" and entity.value:
                result = result.replace(entity.value, "user@example.com")
            elif entity.type == "PHONE" and entity.value:
                result = result.replace(entity.value, "(555) 000-0000")
            elif entity.value and not entity.type.endswith("_CONTEXT"):
                result = result.replace(entity.value, f"[SYNTHETIC:{entity.type}]")
        return result

    def _hashing(self, text: str, entities: list[DetectedEntity]) -> str:
        result = text
        for entity in entities:
            if entity.value and not entity.type.endswith("_CONTEXT"):
                h = hashlib.sha256(entity.value.encode()).hexdigest()[:12]
                result = result.replace(entity.value, f"SHA256:{h}")
        return result

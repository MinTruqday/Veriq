import json
import math
import re
from collections import Counter
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.core.infrastructure.configuration import settings
from src.prompts.security import prompt_injection_detector
from src.schemas.guardrails import SecurityAssessment
from src.utils.huggingface import create_chat_model


class GuardrailsEngine:
    def __init__(self):
        self.llm = create_chat_model(settings.LLM_MODEL)

    @staticmethod
    def _entropy(value: str) -> float:
        if not value:
            return 0.0
        counts = Counter(value)
        length = len(value)
        return -sum((count / length) * math.log2(count / length) for count in counts.values())

    def _redact_structural_secrets(self, text: str) -> tuple[str, bool]:
        found = False
        def redact(match: re.Match) -> str:
            nonlocal found
            candidate = match.group(0)
            identifier = candidate.strip("\"'`,;:[]{}()")
            if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}", identifier):
                return candidate
            if re.fullmatch(r"[A-Z][A-Z0-9]{0,15}-[0-9a-fA-F]{32}", identifier):
                return candidate
            has_character_mix = bool(
                re.search(r"[A-Za-z]", candidate) and re.search(r"\d", candidate)
            )
            compact_ratio = sum(character.isalnum() for character in candidate) / len(candidate)
            credential_shape = (
                len(candidate) >= 32 and compact_ratio >= 0.85
            ) or (
                len(candidate) == 20
                and candidate.upper() == candidate
                and compact_ratio == 1.0
            )
            credential_uri = (
                "://" in candidate and "@" in candidate
            )
            if (
                has_character_mix
                and self._entropy(candidate) >= 3.5
                and (credential_shape or credential_uri)
            ):
                found = True
                return "[REDACTED]"
            return candidate

        sanitized = re.sub(r"(?<![\w])[^\s]{20,}(?![\w])", redact, text)
        return sanitized, found

    def _inspect_tool_payload(self, value: Any) -> tuple[Any, bool]:
        """Inspect values while keeping ordinary IDs, hashes, and provenance metadata intact."""
        sensitive = False
        if isinstance(value, dict):
            sanitized = {}
            for key, item in value.items():
                normalized_key = str(key).casefold()
                metadata = normalized_key.endswith(
                    ("_id", "_ref", "_hash", "_version", "_trace_id", "_run_id")
                )
                if metadata and isinstance(item, str):
                    sanitized[key] = item
                    continue
                sanitized[key], item_sensitive = self._inspect_tool_payload(item)
                sensitive = sensitive or item_sensitive
            return sanitized, sensitive
        if isinstance(value, list):
            sanitized = []
            for item in value:
                safe_item, item_sensitive = self._inspect_tool_payload(item)
                sanitized.append(safe_item)
                sensitive = sensitive or item_sensitive
            return sanitized, sensitive
        if isinstance(value, str):
            sanitized, found = self._redact_structural_secrets(value)
            return sanitized, found
        return value, False

    @staticmethod
    def _tool_payload_text(value: Any) -> list[str]:
        """Collect human-readable tool content without feeding opaque metadata to the classifier."""
        if isinstance(value, dict):
            values = []
            for key, item in value.items():
                normalized_key = str(key).casefold()
                if normalized_key.endswith(
                    ("_id", "_ref", "_hash", "_version", "_trace_id", "_run_id")
                ):
                    continue
                values.extend(GuardrailsEngine._tool_payload_text(item))
            return values
        if isinstance(value, list):
            return [
                text
                for item in value
                for text in GuardrailsEngine._tool_payload_text(item)
            ]
        if isinstance(value, str):
            return [value]
        return []

    async def async_inspect_tool_output(self, output: str) -> Dict[str, Any]:
        """Security-check JSON tool output without classifying project IDs as credentials."""
        try:
            payload = json.loads(output)
        except (TypeError, ValueError):
            return await self.async_inspect_input(output)
        sanitized_payload, sensitive = self._inspect_tool_payload(payload)
        sanitized_text = json.dumps(sanitized_payload, ensure_ascii=False, default=str)
        classifier_text = "\n".join(self._tool_payload_text(sanitized_payload))
        if not classifier_text.strip():
            return {
                "is_safe": True,
                "risk_score": 0.0,
                "threat_category": "sensitive_content" if sensitive else "none",
                "reason": "Sensitive values were redacted" if sensitive else "Tool output contains only structured metadata",
                "sanitized_text": sanitized_text,
                "redactions_applied": sensitive,
            }
        inspected = await self.async_inspect_input(classifier_text)
        inspected["sanitized_text"] = sanitized_text
        inspected["redactions_applied"] = sensitive
        return inspected

    def _deterministic_assessment(self, text: str) -> Dict[str, Any]:
        sanitized, credential_found = self._redact_structural_secrets(text)
        if credential_found:
            threat_category = "sensitive_content"
        else:
            threat_category = "none"
        unsafe = credential_found
        return {
            "is_safe": not unsafe,
            "risk_score": 1.0 if unsafe else 0.0,
            "threat_category": threat_category,
            "reason": (
                "Sensitive content redacted"
                if credential_found
                else "Passed structural security inspection"
            ),
            "sanitized_text": sanitized,
        }

    async def async_inspect_input(self, prompt: str) -> Dict[str, Any]:
        if not prompt or not prompt.strip():
            return {
                "is_safe": True,
                "risk_score": 0.0,
                "reason": "Empty input",
                "sanitized_text": "",
            }

        baseline = self._deterministic_assessment(prompt)
        if not baseline["is_safe"]:
            return baseline

        try:
            system_prompt = prompt_injection_detector(prompt)
            structured_llm = self.llm.with_structured_output(SecurityAssessment)
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
            assessment = await structured_llm.ainvoke(messages, max_tokens=256, temperature=0)
            return {
                "is_safe": assessment.is_safe,
                "risk_score": assessment.risk_score,
                "threat_category": assessment.threat_category,
                "reason": assessment.reason,
                "sanitized_text": baseline["sanitized_text"],
            }
        except Exception:
            logger.exception("AI safety classifier failed")
            return {
                "is_safe": False,
                "risk_score": 1.0,
                "threat_category": "classifier_unavailable",
                "reason": "Security classification unavailable",
                "sanitized_text": prompt,
            }

    def inspect_input(self, prompt: str) -> Dict[str, Any]:
        if not prompt or not prompt.strip():
            return {
                "is_safe": True,
                "risk_score": 0.0,
                "reason": "Empty input",
                "sanitized_text": "",
            }

        return self._deterministic_assessment(prompt)

    def inspect_output(self, response_text: str) -> Dict[str, Any]:
        if not response_text or not response_text.strip():
            return {
                "is_safe": True,
                "risk_score": 0.0,
                "reason": "Empty output",
                "sanitized_text": "",
            }

        return self._deterministic_assessment(response_text)

    validate_input = inspect_input
    validate_output = inspect_output


guardrails_engine = GuardrailsEngine()

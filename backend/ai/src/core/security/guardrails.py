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

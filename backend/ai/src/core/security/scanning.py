import asyncio
import re
from dataclasses import dataclass, field
from typing import List, Literal

from loguru import logger

from src.core.security.guardrails import guardrails_engine


@dataclass
class ScanResult:
    passed: bool
    risk_score: float
    sanitized_text: str
    blocked: bool = False
    violations: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExternalToolOutputScanResult:
    status: Literal["SAFE", "REDACTED", "BLOCKED"]
    sanitized_text: str | None
    reason_code: str | None = None


class SecurityHarness:
    def __init__(self):
        self.analyzer = None
        self.anonymizer = None
        self._pii_engine_initialized = False
        self._pii_engine_lock = asyncio.Lock()

    def _initialize_pii_engine(self):
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            from presidio_anonymizer import AnonymizerEngine
            from presidio_analyzer.nlp_engine import SpacyNlpEngine
            import spacy

            models = [
                {
                    "lang_code": "en",
                    "model_name": "en_core_web_sm",
                }
            ]
            provider = NlpEngineProvider(
                nlp_configuration={
                    "nlp_engine_name": "spacy",
                    "models": models,
                }
            )
            try:
                nlp_engine = provider.create_engine()
            except OverflowError:
                nlp_engine = SpacyNlpEngine(models=models)
                nlp_engine.nlp = {
                    model["lang_code"]: spacy.load(
                        model["model_name"], exclude=["tokenizer"]
                    )
                    for model in models
                }
            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            self.anonymizer = AnonymizerEngine()
            logger.info("Presidio security engines initialized")
        except ImportError:
            logger.warning("Presidio dependencies unavailable, using deterministic PII scanning")
        except Exception:
            logger.exception("Presidio initialization failed, using deterministic PII scanning")
        finally:
            self._pii_engine_initialized = True

    async def _ensure_pii_engine(self):
        if self._pii_engine_initialized:
            return
        async with self._pii_engine_lock:
            if not self._pii_engine_initialized:
                await asyncio.to_thread(self._initialize_pii_engine)

    async def _adetect_security_issues(
        self, text: str, allow_ai_review: bool = True
    ) -> tuple[str, List[str], bool]:
        await self._ensure_pii_engine()
        from langchain_core.messages import HumanMessage, SystemMessage

        from src.prompts.security import security_scan
        from src.schemas.security import SecurityEvaluation
        from src.utils.huggingface import create_chat_model

        violations = []
        baseline = (
            await guardrails_engine.async_inspect_input(text)
            if allow_ai_review
            else guardrails_engine.inspect_input(text)
        )
        sanitized = baseline.get("sanitized_text", text)
        category = baseline.get("threat_category", "none")
        blocked = not baseline.get("is_safe", True)
        if blocked:
            violations.append(category)

        if self.analyzer and self.anonymizer:
            try:
                results = self.analyzer.analyze(
                    text=sanitized,
                    entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "CRYPTO"],
                    language="en",
                )
                if results:
                    violations.append("pii_detected")
                    anonymized_result = self.anonymizer.anonymize(
                        text=sanitized, analyzer_results=results
                    )
                    sanitized = anonymized_result.text
            except Exception:
                logger.exception("Presidio scan failed")

        if not allow_ai_review or blocked:
            return sanitized, list(dict.fromkeys(violations)), blocked

        try:
            llm = create_chat_model()
            structured_llm = llm.with_structured_output(SecurityEvaluation)

            system_prompt = security_scan()

            result = await structured_llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=sanitized)]
            )
            if result.is_malicious:
                violations.append(result.reason[:60])
                blocked = True
            if result.has_credentials:
                violations.append("sensitive_content")
                blocked = True
            if result.has_pii and "pii_detected" not in violations:
                violations.append("pii_detected")
                if result.sanitized_text:
                    sanitized = result.sanitized_text
        except Exception:
            logger.exception("AI security tracing failed")
            violations.append("classification_unavailable")
            blocked = True

        return sanitized, violations, blocked

    def _anomaly_score(self, text: str) -> float:
        if not text:
            return 0.0
        special_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / max(
            len(text), 1
        )
        length_penalty = min(
            len(text) / 10000, 0.3
        )
        return min(special_ratio * 0.5 + length_penalty, 1.0)

    async def ascan_input(
        self, text: str, session_id: str = "", user_id: str = "", allow_ai_review: bool = True
    ) -> ScanResult:
        if not text or not text.strip():
            return ScanResult(passed=True, risk_score=0.0, sanitized_text=text or "")

        sanitized, violations, blocked = await self._adetect_security_issues(
            text, allow_ai_review=allow_ai_review
        )

        pii_violations = [v for v in violations if "pii" in v]

        anomaly = self._anomaly_score(text)
        risk_score = 1.0 if blocked else min(anomaly * 0.2, 1.0)

        if blocked:
            logger.warning("Unsafe content blocked")
            return ScanResult(
                passed=False,
                blocked=True,
                risk_score=1.0,
                sanitized_text=sanitized,
                violations=violations,
            )

        if pii_violations:
            logger.info("System automatically obscured and protected sensitive PII")

        return ScanResult(
            passed=True,
            blocked=False,
            risk_score=risk_score,
            sanitized_text=sanitized,
            violations=violations,
        )

    async def inspect_external_tool_output(self, text: str) -> ExternalToolOutputScanResult:
        if not isinstance(text, str) or not text.strip():
            return ExternalToolOutputScanResult(
                status="BLOCKED",
                sanitized_text=None,
                reason_code="EXTERNAL_TOOL_OUTPUT_INVALID",
            )
        await self._ensure_pii_engine()
        if not self.analyzer or not self.anonymizer:
            return ExternalToolOutputScanResult(
                status="BLOCKED",
                sanitized_text=None,
                reason_code="EXTERNAL_TOOL_PII_SCANNER_UNAVAILABLE",
            )
        baseline = guardrails_engine.inspect_input(text)
        if not baseline.get("is_safe", False):
            return ExternalToolOutputScanResult(
                status="BLOCKED",
                sanitized_text=None,
                reason_code="EXTERNAL_TOOL_SENSITIVE_CONTENT",
            )
        sanitized = baseline.get("sanitized_text", text)
        try:
            findings = self.analyzer.analyze(
                text=sanitized,
                entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "CRYPTO"],
                language="en",
            )
            if findings:
                sanitized = self.anonymizer.anonymize(
                    text=sanitized,
                    analyzer_results=findings,
                ).text
                return ExternalToolOutputScanResult(
                    status="REDACTED",
                    sanitized_text=sanitized,
                )
        except Exception:
            logger.exception("External tool output privacy inspection failed")
            return ExternalToolOutputScanResult(
                status="BLOCKED",
                sanitized_text=None,
                reason_code="EXTERNAL_TOOL_PII_SCAN_FAILED",
            )
        return ExternalToolOutputScanResult(
            status="SAFE",
            sanitized_text=sanitized,
        )

    async def ascan_output(self, text: str, session_id: str = "") -> str:
        if not text:
            return text
        baseline = guardrails_engine.inspect_output(text)
        text = baseline.get("sanitized_text", text)
        if not baseline.get("is_safe", True):
            raise PermissionError("output_credential_leak_blocked")
        sanitized, _, blocked = await self._adetect_security_issues(text, allow_ai_review=False)
        sanitized = re.sub(
            r"<(think|thought)>.*?</\1>",
            "",
            sanitized,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()
        if blocked:
            logger.error("System proactively blocked and neutralized credential leak risk")
            raise PermissionError("output_credential_leak_blocked")
        return sanitized


security = SecurityHarness()

import math
import time
from datetime import datetime, timezone
from uuid import uuid4

from loguru import logger

from src.schemas.evaluation import (
    TestabilityBenchmarkCandidate,
    TestabilityBenchmarkCase,
    TestabilityBenchmarkGoldCase,
    TestabilityBenchmarkRequest,
    TestabilityBenchmarkReport,
)
from src.schemas.inference import TestingAutomationRequest
from src.schemas.inference_requests import TestingEvidence
from src.services.ai_automation import generate_ai_automation
from src.agents.runner.automation_graph import extract_source_facts
from src.services.inference import model_metadata


class TestabilityBenchmarkService:
    """Score compiler outputs against caller-supplied experimental answer keys."""

    @staticmethod
    def _set_scores(expected: list[str], actual: list[str]) -> dict:
        expected_values = {value.strip() for value in expected if value.strip()}
        actual_values = {value.strip() for value in actual if value.strip()}
        matched = expected_values & actual_values
        return {
            "precision": (
                round(len(matched) / len(actual_values), 4)
                if actual_values else (0.0 if expected_values else None)
            ),
            "recall": (
                round(len(matched) / len(expected_values), 4)
                if expected_values else None
            ),
            "matched": sorted(matched),
            "unexpected": sorted(actual_values - expected_values),
            "missing": sorted(expected_values - actual_values),
        }

    @classmethod
    def _candidate_scores(cls, case, candidate) -> dict:
        quote_scores = cls._set_scores(case.expected_source_quotes, candidate.source_quotes)
        grounded_quotes = [quote for quote in candidate.source_quotes if quote and quote in case.source_text]
        expected_clarifications = (
            case.expected_clarification_categories or case.expected_clarification_codes
        )
        actual_clarifications = (
            candidate.clarification_categories or candidate.clarification_codes
        )
        clarification_scores = cls._set_scores(
            expected_clarifications, actual_clarifications
        )
        if case.expected_obligation_sources:
            predicted_obligations = candidate.obligation_evidence
            remaining_predictions = set(predicted_obligations)
            matched_obligations = []
            for expected_key, expected_quote in case.expected_obligation_sources.items():
                match = next(
                    (
                        key for key in remaining_predictions
                        if expected_quote in predicted_obligations[key]
                    ),
                    None,
                )
                if match is not None:
                    matched_obligations.append(expected_key)
                    remaining_predictions.remove(match)
            expected_count = len(case.expected_obligation_sources)
            predicted_count = len(predicted_obligations)
            obligation_scores = {
                "precision": (
                    round(len(matched_obligations) / predicted_count, 4)
                    if predicted_count else (0.0 if expected_count else None)
                ),
                "recall": round(len(matched_obligations) / expected_count, 4) if expected_count else None,
                "matched": sorted(matched_obligations),
                "unexpected": sorted(remaining_predictions),
                "missing": sorted(set(case.expected_obligation_sources) - set(matched_obligations)),
            }
        else:
            obligation_scores = cls._set_scores(case.expected_obligation_keys, candidate.obligation_keys)
        priority_scores = cls._clarification_priority_scores(
            case.expected_clarification_priorities or expected_clarifications,
            actual_clarifications,
        )
        clarified = {
            obligation
            for code in set(actual_clarifications)
            if code in expected_clarifications
            for obligation in case.expected_clarification_unlocks.get(code, [])
        }
        clarification_count = len(set(candidate.clarification_codes or actual_clarifications))
        return {
            "source_quote_validity": (
                round(len(grounded_quotes) / len(candidate.source_quotes), 4)
                if candidate.source_quotes else None
            ),
            "source_quote": quote_scores,
            "clarification": clarification_scores,
            "obligation": obligation_scores,
            "clarification_count": clarification_count,
            "clarification_priority": priority_scores,
            "gold_obligations_unlocked_per_clarification": (
                round(len(clarified) / clarification_count, 4)
                if clarification_count else None
            ),
        }

    @staticmethod
    def _clarification_priority_scores(expected: list[str], actual: list[str]) -> dict:
        """Score whether higher-priority gold clarifications are asked earlier."""
        expected_order = list(dict.fromkeys(value.strip() for value in expected if value.strip()))
        actual_order = list(dict.fromkeys(value.strip() for value in actual if value.strip()))
        if not expected_order:
            return {"ndcg": None, "first_relevant_rank": None}
        relevance = {value: len(expected_order) - index for index, value in enumerate(expected_order)}
        discounted_gain = sum(
            relevance.get(value, 0) / math.log2(index + 2)
            for index, value in enumerate(actual_order)
        )
        ideal_gain = sum(
            (len(expected_order) - index) / math.log2(index + 2)
            for index in range(len(expected_order))
        )
        first_relevant_rank = next(
            (index + 1 for index, value in enumerate(actual_order) if value in relevance),
            None,
        )
        return {
            "ndcg": round(discounted_gain / ideal_gain, 4) if ideal_gain else 1.0,
            "first_relevant_rank": first_relevant_rank,
        }

    async def evaluate(self, request: TestabilityBenchmarkRequest) -> TestabilityBenchmarkReport:
        """Compare the obligation-aware compiler with two explicit baselines."""
        cases = []
        clarification_scores = []
        compiler_scores = []
        direct_scores = []
        for case in request.cases:
            clarification = self._candidate_scores(
                case, case.clarification_without_obligation_planning
            )
            compiler = self._candidate_scores(case, case.compiler)
            direct = self._candidate_scores(case, case.direct_generation)
            clarification_scores.append(clarification)
            compiler_scores.append(compiler)
            direct_scores.append(direct)
            cases.append(
                {
                    "case_id": case.case_id,
                    "clarification_without_obligation_planning": clarification,
                    "compiler": compiler,
                    "direct_generation": direct,
                }
            )

        def average_metric(values, key):
            applicable = [value[key] for value in values if value[key] is not None]
            return round(sum(applicable) / len(applicable), 4) if applicable else None

        def aggregate(values):
            return {
                "source_quote_validity": average_metric(values, "source_quote_validity"),
                "source_quote_recall": average_metric(
                    [{"metric": value["source_quote"]["recall"]} for value in values],
                    "metric",
                ),
                "clarification_recall": average_metric(
                    [{"metric": value["clarification"]["recall"]} for value in values],
                    "metric",
                ),
                "obligation_recall": average_metric(
                    [{"metric": value["obligation"]["recall"]} for value in values],
                    "metric",
                ),
                "average_clarification_count": round(
                    sum(value["clarification_count"] for value in values) / len(values), 4
                ),
                "clarification_priority_ndcg": average_metric(
                    [{"metric": value["clarification_priority"]["ndcg"]} for value in values],
                    "metric",
                ),
                "gold_obligations_unlocked_per_clarification": average_metric(
                    [{"metric": value["gold_obligations_unlocked_per_clarification"]} for value in values],
                    "metric",
                ),
            }

        report = TestabilityBenchmarkReport(
            total_cases=len(cases),
            clarification_without_obligation_planning=aggregate(clarification_scores),
            compiler=aggregate(compiler_scores),
            direct_generation=aggregate(direct_scores),
            cases=cases,
        )
        logger.info("Testability compiler benchmark completed cases={}", report.total_cases)
        return report

    @staticmethod
    def _source_evidence(case, dataset_id):
        return [{
            "artifact_type": "benchmark_source",
            "artifact_id": f"{dataset_id}:{case.case_id}",
            "artifact_version_id": f"{dataset_id}:{case.case_id}:source-v1",
            "source": "document",
            "authority": "benchmark_answer_key_dataset",
            "text": case.source_text,
        }]

    @staticmethod
    def _candidate_from_blueprint(output):
        obligations = output.get("obligations", [])
        clarifications = output.get("clarifications", [])
        return TestabilityBenchmarkCandidate(
            source_quotes=list(dict.fromkeys(
                [item.get("source_quote", "") for item in obligations]
                + [item.get("source_quote", "") for item in clarifications]
            )),
            clarification_codes=[item.get("code", "") for item in clarifications],
            clarification_categories=[item.get("category", "") for item in clarifications],
            obligation_keys=[item.get("key", "") for item in obligations],
            obligation_evidence={
                str(item.get("key", "")): [str(item.get("source_quote", ""))]
                for item in obligations if item.get("key") and item.get("source_quote")
            },
        )

    @staticmethod
    def _candidate_from_clarification(output):
        return TestabilityBenchmarkCandidate(
            source_quotes=[
                item.get("source_quote", "") for item in output.get("clarifications", [])
            ],
            clarification_codes=[
                item.get("code", "") for item in output.get("clarifications", [])
            ],
            clarification_categories=[
                item.get("category", "") for item in output.get("clarifications", [])
            ],
        )

    @staticmethod
    def _candidate_from_direct_generation(output):
        cases = output.get("suggestions", [])
        quotes = []
        obligations = []
        obligation_evidence = {}
        for case in cases:
            obligations.extend(case.get("coverage_obligations", []))
            case_quotes = list(dict.fromkeys(
                item.get("quote", "") for item in case.get("evidence_quotes", [])
            ))
            quotes.extend(case_quotes)
            for obligation in case.get("coverage_obligations", []):
                obligation_evidence[str(obligation)] = case_quotes
        return TestabilityBenchmarkCandidate(
            source_quotes=list(dict.fromkeys(quotes)),
            obligation_keys=list(dict.fromkeys(obligations)),
            obligation_evidence=obligation_evidence,
        )

    async def _run_pipeline(self, capability, dataset_id, case, evidence, instruction):
        request = TestingAutomationRequest(
            capability=capability,
            project_id=f"benchmark:{dataset_id}",
            instruction=instruction,
            evidence=[TestingEvidence.model_validate(item) for item in evidence],
        )
        result = await generate_ai_automation(request)
        data = result.model_dump(mode="json")
        if data.get("status") != "SUCCESS":
            raise RuntimeError(
                ";".join(data.get("reason_codes") or data.get("warnings") or ["AI_PIPELINE_DEGRADED"])
            )
        return data

    @staticmethod
    def _verified_fact_evidence(facts):
        grouped = {}
        for fact in facts:
            reference = str(fact.get("artifact_version_id") or fact.get("artifact_id") or "")
            quote = str(fact.get("quote") or "").strip()
            if not reference or not quote:
                continue
            entry = grouped.setdefault(reference, {
                "artifact_type": fact.get("artifact_type") or "benchmark_source",
                "artifact_id": fact.get("artifact_id"),
                "artifact_version_id": fact.get("artifact_version_id"),
                "authority": fact.get("authority") or "benchmark_answer_key_dataset",
                "text": [],
            })
            if quote not in entry["text"]:
                entry["text"].append(quote)
        return [
            {**value, "text": "\n".join(value["text"])}
            for value in grouped.values()
        ]

    async def run_dataset(self, dataset_id: str, cases: list[TestabilityBenchmarkGoldCase]):
        """Run the actual extraction/compiler, clarification, and direct-test pipelines."""
        started = time.perf_counter()
        run_id = f"TBR-{uuid4().hex}"
        scored_cases = []
        failures = []
        raw_outputs = {}
        model_metadata_by_capability = {}

        def failure_code(error):
            value = str(error)
            if isinstance(error, RuntimeError) and value and all(
                character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_;-" for character in value
            ):
                return value[:160]
            return type(error).__name__

        for gold_case in cases:
            source_evidence = self._source_evidence(gold_case, dataset_id)
            compiler_candidate = TestabilityBenchmarkCandidate()
            clarification_candidate = TestabilityBenchmarkCandidate()
            direct_candidate = TestabilityBenchmarkCandidate()
            raw_outputs[gold_case.case_id] = {}

            try:
                extraction = await extract_source_facts({"evidence": source_evidence})
                verified = self._verified_fact_evidence(extraction.get("source_facts", []))
                if not verified:
                    raise RuntimeError("NO_VERIFIED_SOURCE_FACTS")
                fact_context = "\n".join(
                    f"[{item.get('artifact_version_id') or item.get('artifact_id')}] {item['text']}"
                    for item in verified
                )
                instruction = (
                    "Compile the testability blueprint only from these source facts. "
                    "Preserve exact evidence references and quotes.\n\n" + fact_context
                )
                output = await self._run_pipeline(
                    "testability_blueprint_compilation", dataset_id, gold_case,
                    verified, instruction,
                )
                compiler_candidate = self._candidate_from_blueprint(output)
                raw_outputs[gold_case.case_id]["compiler"] = output
                model_metadata_by_capability["compiler"] = output.get("model", {})
            except Exception as error:
                failures.append({
                    "case_id": gold_case.case_id,
                    "pipeline": "compiler",
                    "error_code": failure_code(error),
                })

            clarification_instruction = (
                "Ask evidence-grounded clarification questions for this source without first "
                "decomposing it into obligations. " + gold_case.task_instruction
            ).strip()
            try:
                output = await self._run_pipeline(
                    "clarification_baseline", dataset_id, gold_case,
                    source_evidence, clarification_instruction,
                )
                clarification_candidate = self._candidate_from_clarification(output)
                raw_outputs[gold_case.case_id]["clarification_without_obligation_planning"] = output
                model_metadata_by_capability["clarification_baseline"] = output.get("model", {})
            except Exception as error:
                failures.append({
                    "case_id": gold_case.case_id,
                    "pipeline": "clarification_without_obligation_planning",
                    "error_code": failure_code(error),
                })

            direct_instruction = (
                "Generate evidence-grounded test cases directly from the supplied source for "
                "all clearly testable behavior. Return source quotes and coverage obligations. "
                + gold_case.task_instruction
            ).strip()
            try:
                output = await self._run_pipeline(
                    "test_generation", dataset_id, gold_case,
                    source_evidence, direct_instruction,
                )
                direct_candidate = self._candidate_from_direct_generation(output)
                raw_outputs[gold_case.case_id]["direct_generation"] = output
                model_metadata_by_capability["test_generation"] = output.get("model", {})
            except Exception as error:
                failures.append({
                    "case_id": gold_case.case_id,
                    "pipeline": "direct_generation",
                    "error_code": failure_code(error),
                })

            scored_cases.append(TestabilityBenchmarkCase(
                **gold_case.model_dump(),
                compiler=compiler_candidate,
                clarification_without_obligation_planning=clarification_candidate,
                direct_generation=direct_candidate,
            ))

        report = await self.evaluate(TestabilityBenchmarkRequest(cases=scored_cases))
        report.run_id = run_id
        report.dataset_id = dataset_id
        report.pipeline_metadata = {
            "provider": model_metadata().get("provider"),
            "model": model_metadata().get("model"),
            "pipelines": [
                "verified_source_fact_extraction_plus_testability_blueprint_compilation",
                "clarification_baseline_without_obligation_planning",
                "direct_test_generation_with_grounding_review",
            ],
            "candidate_outputs": raw_outputs,
            "model_metadata_by_capability": model_metadata_by_capability,
        }
        report.pipeline_failures = failures
        report.duration_ms = round((time.perf_counter() - started) * 1000)
        report.execution_status = "PARTIAL" if failures else "COMPLETE"
        report.created_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Live testability benchmark completed run_id={} dataset_id={} cases={} pipeline_failures={}",
            run_id, dataset_id, report.total_cases, len(failures),
        )
        return report


testability_benchmark = TestabilityBenchmarkService()

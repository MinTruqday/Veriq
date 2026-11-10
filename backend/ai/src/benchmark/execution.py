import time
from datetime import datetime, timezone
from uuid import uuid4

from loguru import logger

from src.schemas.evaluation import (
    TestabilityBenchmarkCandidate,
    TestabilityBenchmarkCase,
    TestabilityBenchmarkGoldCase,
    TestabilityBenchmarkRequest,
)
from src.services.inference import model_metadata


class TestabilityBenchmarkExecution:
    """Execute real AI pipelines and collect their outcomes."""

    async def run_dataset(self, dataset_id: str, cases: list[TestabilityBenchmarkGoldCase], pipeline_order=None):
        """Run the actual extraction/compiler, clarification, and direct-test pipelines."""
        self.validate_cases_for_scoring(cases)
        available_pipelines = (
            "compiler",
            "clarification_without_obligation_planning",
            "direct_generation",
        )
        pipeline_order = tuple(pipeline_order or available_pipelines)
        if len(pipeline_order) != len(available_pipelines) or set(pipeline_order) != set(available_pipelines):
            raise ValueError("BENCHMARK_PIPELINE_ORDER_INVALID")
        started = time.perf_counter()
        run_id = f"TBR-{uuid4().hex}"
        scored_cases = []
        failures = []
        rejections = []
        raw_outputs = {}
        pipeline_outcomes = {}
        model_metadata_by_capability = {}

        def failure_code(error):
            value = str(error)
            if isinstance(error, RuntimeError) and value and all(
                character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_;-" for character in value
            ):
                return value[:160]
            return type(error).__name__

        def record_non_success(case_id, pipeline, output):
            reason_codes = output.get("reason_codes", [])
            provider_failure = any(
                "PROVIDER_UNAVAILABLE" in str(code)
                or "MODEL_CALL_FAILED" in str(code)
                for code in reason_codes
            ) or output.get("degraded_mode") == "DEGRADED_AI"
            record = {
                "case_id": case_id,
                "pipeline": pipeline,
                "reason_codes": reason_codes,
            }
            if provider_failure:
                failures.append({**record, "error_code": reason_codes[0] if reason_codes else "MODEL_CALL_FAILED"})
            else:
                rejections.append(record)

        def outcome_for(output):
            if output.get("status") == "SUCCESS":
                return "ACCEPTED"
            reason_codes = output.get("reason_codes", [])
            if output.get("degraded_mode") == "DEGRADED_AI" or any(
                "PROVIDER_UNAVAILABLE" in str(code)
                or "MODEL_CALL_FAILED" in str(code)
                for code in reason_codes
            ):
                return "FAILED"
            return "REJECTED"

        for gold_case in cases:
            source_evidence = self._source_evidence(gold_case, dataset_id)
            compiler_candidate = TestabilityBenchmarkCandidate()
            clarification_candidate = TestabilityBenchmarkCandidate()
            direct_candidate = TestabilityBenchmarkCandidate()
            raw_outputs[gold_case.case_id] = {}
            pipeline_outcomes[gold_case.case_id] = {}

            candidates = {
                "compiler": compiler_candidate,
                "clarification_without_obligation_planning": clarification_candidate,
                "direct_generation": direct_candidate,
            }
            for pipeline in pipeline_order:
                try:
                    candidate, output, capability = await self._run_benchmark_pipeline(
                        pipeline, dataset_id, gold_case, source_evidence
                    )
                    candidates[pipeline] = candidate
                    raw_outputs[gold_case.case_id][pipeline] = output
                    pipeline_outcomes[gold_case.case_id][pipeline] = outcome_for(output)
                    model_metadata_by_capability.setdefault(capability, {})[
                        gold_case.case_id
                    ] = output.get("model", {})
                    if output.get("status") != "SUCCESS":
                        record_non_success(gold_case.case_id, pipeline, output)
                except Exception as error:
                    pipeline_outcomes[gold_case.case_id][pipeline] = "FAILED"
                    failures.append({
                        "case_id": gold_case.case_id,
                        "pipeline": pipeline,
                        "error_code": failure_code(error),
                    })
            compiler_candidate = candidates["compiler"]
            clarification_candidate = candidates["clarification_without_obligation_planning"]
            direct_candidate = candidates["direct_generation"]

            scored_cases.append(TestabilityBenchmarkCase(
                **gold_case.model_dump(),
                compiler=compiler_candidate,
                clarification_without_obligation_planning=clarification_candidate,
                direct_generation=direct_candidate,
            ))

        report = await self.evaluate(TestabilityBenchmarkRequest(cases=scored_cases))
        pipeline_fields = {
            "compiler": "compiler",
            "clarification_without_obligation_planning": "clarification_without_obligation_planning",
            "direct_generation": "direct_generation",
        }
        report.pipeline_case_counts = {}
        for pipeline, report_field in pipeline_fields.items():
            outcomes = [items.get(pipeline) for items in pipeline_outcomes.values()]
            accepted_ids = {
                case_id for case_id, items in pipeline_outcomes.items()
                if items.get(pipeline) == "ACCEPTED"
            }
            report.pipeline_case_counts[pipeline] = {
                "attempted": len(outcomes),
                "accepted": outcomes.count("ACCEPTED"),
                "rejected": outcomes.count("REJECTED"),
                "failed": outcomes.count("FAILED"),
            }
            if accepted_ids:
                accepted_cases = [case for case in scored_cases if case.case_id in accepted_ids]
                accepted_report = await self.evaluate(
                    TestabilityBenchmarkRequest(cases=accepted_cases)
                )
                setattr(report, report_field, getattr(accepted_report, report_field))
                report.metric_case_counts[pipeline] = accepted_report.metric_case_counts[
                    report_field
                ]
            else:
                setattr(report, report_field, {
                    "source_quote_validity": None,
                    "source_quote_precision": None,
                    "source_quote_recall": None,
                    "source_quote_source_precision": None,
                    "source_quote_source_recall": None,
                    "clarification_precision": None,
                    "clarification_recall": None,
                    "obligation_precision": None,
                    "obligation_recall": None,
                    "average_clarification_count": None,
                    "clarification_priority_ndcg": None,
                    "gold_obligations_unlocked_per_clarification": None,
                })
                report.metric_case_counts[pipeline] = {
                    metric_name: 0
                    for metric_name in (
                        "source_quote_validity",
                        "source_quote_precision",
                        "source_quote_recall",
                        "source_quote_source_precision",
                        "source_quote_source_recall",
                        "clarification_precision",
                        "clarification_recall",
                        "obligation_precision",
                        "obligation_recall",
                        "average_clarification_count",
                        "clarification_priority_ndcg",
                        "gold_obligations_unlocked_per_clarification",
                    )
                }

        accepted_by_pipeline = {
            pipeline: {
                case_id
                for case_id, outcomes in pipeline_outcomes.items()
                if outcomes.get(pipeline) == "ACCEPTED"
            }
            for pipeline in pipeline_fields
        }
        comparison_pairs = (
            ("compiler", "direct_generation"),
            ("compiler", "clarification_without_obligation_planning"),
            ("direct_generation", "clarification_without_obligation_planning"),
        )
        report.paired_pipeline_comparisons = {}
        for left, right in comparison_pairs:
            common_case_ids = accepted_by_pipeline[left] & accepted_by_pipeline[right]
            comparison_key = f"{left}_vs_{right}"
            if not common_case_ids:
                report.paired_pipeline_comparisons[comparison_key] = {
                    "left_pipeline": left,
                    "right_pipeline": right,
                    "paired_case_count": 0,
                    "case_ids": [],
                    "left_metrics": None,
                    "right_metrics": None,
                    "left_metric_case_counts": {},
                    "right_metric_case_counts": {},
                }
                continue

            paired_cases = [
                case for case in scored_cases if case.case_id in common_case_ids
            ]
            paired_report = await self.evaluate(
                TestabilityBenchmarkRequest(cases=paired_cases)
            )
            report.paired_pipeline_comparisons[comparison_key] = {
                "left_pipeline": left,
                "right_pipeline": right,
                "paired_case_count": len(paired_cases),
                "case_ids": sorted(common_case_ids),
                "left_metrics": getattr(paired_report, pipeline_fields[left]),
                "right_metrics": getattr(paired_report, pipeline_fields[right]),
                "left_metric_case_counts": paired_report.metric_case_counts[left],
                "right_metric_case_counts": paired_report.metric_case_counts[right],
            }

        paired_cases = [
            case for case in scored_cases
            if pipeline_outcomes.get(case.case_id, {}).get("compiler") == "ACCEPTED"
            and pipeline_outcomes.get(case.case_id, {}).get(
                "clarification_without_obligation_planning"
            ) == "ACCEPTED"
        ]
        report.clarification_savings_paired_cases = len(paired_cases)
        if paired_cases:
            paired_report = await self.evaluate(
                TestabilityBenchmarkRequest(cases=paired_cases)
            )
            report.clarification_savings_vs_baseline = (
                paired_report.clarification_savings_vs_baseline
            )
        else:
            report.clarification_savings_vs_baseline = None
        report_pipeline_fields = {
            "compiler": "compiler",
            "clarification_without_obligation_planning": "clarification_without_obligation_planning",
            "direct_generation": "direct_generation",
        }
        for case in report.cases:
            outcomes = pipeline_outcomes.get(case["case_id"], {})
            case["pipeline_outcomes"] = outcomes
            for report_field, pipeline in report_pipeline_fields.items():
                if outcomes.get(pipeline) != "ACCEPTED":
                    case[report_field] = self._unscored_candidate_metrics()
        report.run_id = run_id
        report.dataset_id = dataset_id
        report.scenario_family_counts = {
            family: sum(case.scenario_family == family for case in cases)
            for family in (
                "COMPLETE",
                "MISSING_OR_AMBIGUOUS",
                "DUPLICATE_OR_CONFLICT",
            )
            if any(case.scenario_family == family for case in cases)
        }
        report.benchmark_design = {
            "answer_key_basis": "independently_reviewed_caller_supplied_answer_key",
            "interpretation": "Mô tả kết quả trên bộ dữ liệu và đáp án tham chiếu đã cung cấp; không tự chứng minh tính đúng tổng quát.",
        }
        report.pipeline_metadata = {
            "provider": model_metadata().get("provider"),
            "model": model_metadata().get("model"),
            "pipelines": [
                "verified_source_fact_extraction_plus_testability_blueprint_compilation",
                "clarification_baseline_without_obligation_planning",
                "direct_test_generation_with_grounding_review",
            ],
            "execution_order": list(pipeline_order),
            "candidate_outputs": raw_outputs,
            "model_metadata_by_capability": model_metadata_by_capability,
        }
        report.pipeline_failures = failures
        report.pipeline_rejections = rejections
        report.duration_ms = round((time.perf_counter() - started) * 1000)
        report.execution_status = "PARTIAL" if failures else "COMPLETE"
        report.created_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Live testability benchmark completed run_id={} dataset_id={} cases={} pipeline_failures={}",
            run_id, dataset_id, report.total_cases, len(failures),
        )
        return report

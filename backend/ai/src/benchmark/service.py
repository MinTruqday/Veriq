from src.schemas.evaluation import (
    TestabilityBenchmarkGoldCase,
    TestabilityBenchmarkMetricRepeatStats,
    TestabilityBenchmarkRepeatedReport,
)
from src.benchmark.execution import TestabilityBenchmarkExecution
from src.benchmark.pipelines import TestabilityBenchmarkPipelines
from src.benchmark.scoring import TestabilityBenchmarkScoring


class TestabilityBenchmarkService(
    TestabilityBenchmarkExecution,
    TestabilityBenchmarkScoring,
    TestabilityBenchmarkPipelines,
):
    """Coordinate Benchmark runs and summarize repeated measurements."""

    async def run_repeated_dataset(
        self,
        dataset_id: str,
        cases: list[TestabilityBenchmarkGoldCase],
        repetitions: int = 3,
        on_report=None,
    ) -> TestabilityBenchmarkRepeatedReport:
        if repetitions < 1 or repetitions > 5:
            raise ValueError("BENCHMARK_REPETITIONS_OUT_OF_RANGE")
        self.validate_cases_for_scoring(cases)

        reports = []
        repetition_failures = []
        pipeline_names = (
            "compiler",
            "clarification_without_obligation_planning",
            "direct_generation",
        )
        for repetition in range(1, repetitions + 1):
            try:
                rotation = (repetition - 1) % len(pipeline_names)
                pipeline_order = pipeline_names[rotation:] + pipeline_names[:rotation]
                report = await self.run_dataset(
                    dataset_id, cases, pipeline_order=pipeline_order
                )
            except Exception as error:
                repetition_failures.append({
                    "repetition_index": repetition,
                    "error_code": type(error).__name__.upper(),
                })
                continue
            report.pipeline_metadata = {
                **report.pipeline_metadata,
                "repetition_index": repetition,
                "requested_repetitions": repetitions,
            }
            reports.append(report)
            if on_report is not None:
                await on_report(report)

        return self.summarize_repeated_reports(
            dataset_id, repetitions, reports, repetition_failures
        )

    @staticmethod
    def summarize_repeated_reports(
        dataset_id, repetitions, reports, repetition_failures=None
    ):
        repetition_failures = repetition_failures or []
        metric_names = (
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

        metric_paths = {
            "source_quote_validity": ("source_quote_validity",),
            "source_quote_precision": ("source_quote", "precision"),
            "source_quote_recall": ("source_quote", "recall"),
            "source_quote_source_precision": ("source_quote", "source_reference", "precision"),
            "source_quote_source_recall": ("source_quote", "source_reference", "recall"),
            "clarification_precision": ("clarification", "precision"),
            "clarification_recall": ("clarification", "recall"),
            "obligation_precision": ("obligation", "precision"),
            "obligation_recall": ("obligation", "recall"),
            "average_clarification_count": ("clarification_count",),
            "clarification_priority_ndcg": ("clarification_priority", "ndcg"),
            "gold_obligations_unlocked_per_clarification": (
                "gold_obligations_unlocked_per_clarification",
            ),
        }

        def case_metric(case, pipeline_name, metric_name):
            value = (case.get(pipeline_name) or {})
            for key in metric_paths[metric_name]:
                if not isinstance(value, dict):
                    return None
                value = value.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            return float(value)

        def metric_statistics(values, case_ids=None):
            return TestabilityBenchmarkMetricRepeatStats(
                observed_runs=len(values),
                mean=round(statistics.fmean(values), 4) if values else None,
                population_stddev=(
                    round(statistics.pstdev(values), 4) if len(values) >= 2 else None
                ),
                minimum=round(min(values), 4) if values else None,
                maximum=round(max(values), 4) if values else None,
                paired_case_count=len(case_ids) if case_ids is not None else None,
                paired_case_ids=sorted(case_ids) if case_ids is not None else [],
            )

        def accepted_case_maps(pipeline_name):
            return [
                {
                    str(case.get("case_id")): case
                    for case in report.cases
                    if case.get("case_id")
                    and case.get("pipeline_outcomes", {}).get(pipeline_name) == "ACCEPTED"
                }
                for report in reports
            ]

        def common_ids(case_maps):
            if not case_maps:
                return set()
            return set.intersection(*(set(case_map) for case_map in case_maps))

        def run_metric_values(case_map, case_ids, pipeline_name, metric_name):
            values = [
                value
                for case_id in case_ids
                if (value := case_metric(case_map[case_id], pipeline_name, metric_name)) is not None
            ]
            return statistics.fmean(values) if values else None

        pipeline_statistics = {}
        for pipeline_name in (
            "compiler",
            "clarification_without_obligation_planning",
            "direct_generation",
        ):
            case_maps = accepted_case_maps(pipeline_name)
            stable_case_ids = common_ids(case_maps)
            metrics = {}
            for metric_name in metric_names:
                metric_case_ids = {
                    case_id
                    for case_id in stable_case_ids
                    if all(
                        case_metric(case_map[case_id], pipeline_name, metric_name)
                        is not None
                        for case_map in case_maps
                    )
                }
                values = [
                    value
                    for case_map in case_maps
                    if (value := run_metric_values(
                        case_map,
                        metric_case_ids,
                        pipeline_name,
                        metric_name,
                    )) is not None
                ]
                metrics[metric_name] = metric_statistics(values, metric_case_ids)
            pipeline_statistics[pipeline_name] = {
                "runs_with_scores": sum(
                    any(
                        case_metric(case, pipeline_name, metric_name) is not None
                        for case in case_map.values()
                        for metric_name in metric_names
                    )
                    for case_map in case_maps
                ),
                "stable_case_count": len(stable_case_ids),
                "stable_case_ids": sorted(stable_case_ids),
                "runs_with_failures": sum(
                    (report.pipeline_case_counts.get(pipeline_name) or {}).get("failed", 0) > 0
                    for report in reports
                ),
                "rejected_cases": sum(
                    (report.pipeline_case_counts.get(pipeline_name) or {}).get("rejected", 0)
                    for report in reports
                ),
                "failed_cases": sum(
                    (report.pipeline_case_counts.get(pipeline_name) or {}).get("failed", 0)
                    for report in reports
                ),
                "metrics": metrics,
            }

        savings_maps = []
        for report in reports:
            comparison = report.paired_pipeline_comparisons.get(
                "compiler_vs_clarification_without_obligation_planning", {}
            )
            accepted = set(comparison.get("case_ids") or [])
            savings_maps.append(
                {
                    str(case.get("case_id")): case
                    for case in report.cases
                    if case.get("case_id")
                    and str(case.get("case_id")) in accepted
                }
            )
        stable_savings_case_ids = {
            case_id
            for case_id in common_ids(savings_maps)
            if all(
                case_metric(case_map[case_id], "compiler", "average_clarification_count")
                is not None
                and case_metric(
                    case_map[case_id],
                    "clarification_without_obligation_planning",
                    "average_clarification_count",
                ) is not None
                for case_map in savings_maps
            )
        }
        repeated_savings = []
        for case_map in savings_maps:
            case_differences = []
            for case_id in stable_savings_case_ids:
                case = case_map[case_id]
                compiler_count = case_metric(case, "compiler", "average_clarification_count")
                baseline_count = case_metric(
                    case,
                    "clarification_without_obligation_planning",
                    "average_clarification_count",
                )
                if compiler_count is not None and baseline_count is not None:
                    case_differences.append(baseline_count - compiler_count)
            if case_differences:
                repeated_savings.append(statistics.fmean(case_differences))
        clarification_savings_statistics = metric_statistics(
            repeated_savings, stable_savings_case_ids
        )

        paired_pipeline_statistics = {}
        comparison_keys = sorted({
            key
            for report in reports
            for key in report.paired_pipeline_comparisons
        })
        for comparison_key in comparison_keys:
            report_observations = [
                (
                    report,
                    report.paired_pipeline_comparisons.get(
                        comparison_key,
                        {
                            "left_pipeline": comparison_key.split("_vs_", 1)[0],
                            "right_pipeline": comparison_key.split("_vs_", 1)[-1],
                            "paired_case_count": 0,
                            "case_ids": [],
                        },
                    ),
                )
                for report in reports
            ]
            observations = [observation for _, observation in report_observations]
            comparison_case_maps = [
                {
                    str(case.get("case_id")): case
                    for case in report.cases
                    if case.get("case_id")
                    and str(case.get("case_id")) in set(observation.get("case_ids") or [])
                }
                for report, observation in report_observations
            ]
            stable_comparison_case_ids = common_ids(comparison_case_maps)
            entry = {
                "left_pipeline": observations[0]["left_pipeline"],
                "right_pipeline": observations[0]["right_pipeline"],
                "observed_runs": len(reports) if stable_comparison_case_ids else 0,
                "requested_runs": len(observations),
                "stable_case_count": len(stable_comparison_case_ids),
                "stable_case_ids": sorted(stable_comparison_case_ids),
                "mean_paired_case_count": round(
                    statistics.fmean(
                        item["paired_case_count"]
                        for item in observations
                        if item.get("paired_case_count", 0) > 0
                    ),
                    4,
                ) if any(item.get("paired_case_count", 0) > 0 for item in observations) else None,
            }
            for side, pipeline_name in (
                ("left_metrics", entry["left_pipeline"]),
                ("right_metrics", entry["right_pipeline"]),
            ):
                entry[side] = {}
                for metric_name in metric_names:
                    metric_case_ids = {
                        case_id
                        for case_id in stable_comparison_case_ids
                        if all(
                            case_metric(case_map[case_id], pipeline_name, metric_name)
                            is not None
                            for case_map in comparison_case_maps
                        )
                    }
                    values = [
                        value
                        for case_map in comparison_case_maps
                        if (value := run_metric_values(
                            case_map,
                            metric_case_ids,
                            pipeline_name,
                            metric_name,
                        )) is not None
                    ]
                    entry[side][metric_name] = metric_statistics(
                        values, metric_case_ids
                    ).model_dump(mode="json")
            entry["paired_effects"] = {}
            for metric_name in metric_names:
                case_differences = []
                for case_id in stable_comparison_case_ids:
                    left_values = [
                        case_metric(case_map[case_id], entry["left_pipeline"], metric_name)
                        for case_map in comparison_case_maps
                    ]
                    right_values = [
                        case_metric(case_map[case_id], entry["right_pipeline"], metric_name)
                        for case_map in comparison_case_maps
                    ]
                    if all(value is not None for value in [*left_values, *right_values]):
                        case_differences.append(
                            statistics.fmean(left_values) - statistics.fmean(right_values)
                        )
                entry["paired_effects"][metric_name] = (
                    TestabilityBenchmarkService.paired_case_bootstrap_effect(
                        case_differences,
                        ":".join(
                            [
                                dataset_id,
                                comparison_key,
                                metric_name,
                                *sorted(stable_comparison_case_ids),
                            ]
                        ),
                    )
                )
            paired_pipeline_statistics[comparison_key] = entry

        completed = sum(report.execution_status == "COMPLETE" for report in reports)
        return TestabilityBenchmarkRepeatedReport(
            dataset_id=dataset_id,
            requested_repetitions=repetitions,
            completed_repetitions=completed,
            partial_repetitions=len(reports) - completed,
            failed_repetitions=len(repetition_failures),
            run_ids=[report.run_id for report in reports if report.run_id],
            repetition_failures=repetition_failures,
            pipeline_statistics=pipeline_statistics,
            paired_pipeline_statistics=paired_pipeline_statistics,
            clarification_savings_vs_baseline=clarification_savings_statistics,
            execution_status=(
                "COMPLETE"
                if completed == repetitions and not repetition_failures
                else "PARTIAL"
            ),
        )

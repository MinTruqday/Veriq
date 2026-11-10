import hashlib
import math
import random
import statistics

from src.schemas.evaluation import validate_unique_benchmark_case_ids


class TestabilityBenchmarkCoreScoring:
    """Shared validation and statistical helpers for Benchmark scoring."""

    @classmethod
    def paired_case_bootstrap_effect(cls, differences, seed_material):
        values = [
            float(value)
            for value in differences
            if isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        ]
        mean = statistics.fmean(values) if values else None
        if len(values) < 2:
            return {
                "case_count": len(values),
                "mean_left_minus_right": round(mean, 4) if mean is not None else None,
                "interval_low": None,
                "interval_high": None,
                "interval_method": "paired_case_percentile_bootstrap",
                "confidence_level": 0.95,
                "resamples": cls.PAIRED_BOOTSTRAP_RESAMPLES,
                "scope": "Biến động khi lấy mẫu lại các ca trong chính bộ dữ liệu này; không đo biến động giữa các lần gọi mô hình.",
            }

        seed = int.from_bytes(
            hashlib.sha256(str(seed_material).encode("utf-8")).digest()[:8], "big"
        )
        generator = random.Random(seed)
        sample_count = len(values)
        bootstrap_means = sorted(
            statistics.fmean(generator.choice(values) for _ in range(sample_count))
            for _ in range(cls.PAIRED_BOOTSTRAP_RESAMPLES)
        )

        def percentile(probability):
            position = probability * (len(bootstrap_means) - 1)
            lower_index = math.floor(position)
            upper_index = math.ceil(position)
            if lower_index == upper_index:
                return bootstrap_means[lower_index]
            weight = position - lower_index
            return (
                bootstrap_means[lower_index] * (1 - weight)
                + bootstrap_means[upper_index] * weight
            )

        return {
            "case_count": sample_count,
            "mean_left_minus_right": round(mean, 4),
            "interval_low": round(percentile(0.025), 4),
            "interval_high": round(percentile(0.975), 4),
            "interval_method": "paired_case_percentile_bootstrap",
            "confidence_level": 0.95,
            "resamples": cls.PAIRED_BOOTSTRAP_RESAMPLES,
            "scope": "Biến động khi lấy mẫu lại các ca trong chính bộ dữ liệu này; không đo biến động giữa các lần gọi mô hình và không xác nhận answer key.",
        }

    @staticmethod
    def validate_cases_for_scoring(cases):
        validate_unique_benchmark_case_ids(cases)
        for case in cases:
            case.validate_for_scoring()

    @staticmethod
    def _scoring_method():
        return {
            "version": "testability-benchmark-v3",
            "aggregation": (
                "Macro average: average each applicable case score equally; metrics with no "
                "defined gold value are null and omitted from that metric's denominator. "
                "The metric_case_counts field reports each pipeline metric's actual denominator."
            ),
            "source_quote_validity": (
                "Unique normalized candidate quotes that occur contiguously in one supplied source "
                "/ all unique normalized candidate quotes."
            ),
            "source_quote_source_precision_recall": (
                "When source-version gold mappings are provided, compare cited (quote, version) pairs; "
                "a citation is counted only if the quote occurs in the exact cited source version. "
                "Recall counts a gold quote covered when at least one permitted source version is cited. "
                "Null when the answer key has no source-version mapping."
            ),
            "source_quote_precision_recall": (
                "Set precision and recall over normalized candidate quotes and human-authored gold quotes."
            ),
            "clarification_precision_recall": (
                "Set precision and recall over predicted versus gold clarification categories; "
                "legacy exact codes are used when categories are absent from the answer key."
            ),
            "obligation_precision_recall": (
                "Set precision and recall over obligation keys. When the answer key includes source quotes, "
                "a match also requires grounded quote evidence and any specified source-version reference; "
                "a citation quote must occur in the exact source version it names."
            ),
            "clarification_count": (
                "Number of predicted clarification questions (codes when present, otherwise categories); "
                "this is a workload measure, not a quality score by itself."
            ),
            "clarification_priority_ndcg": (
                "Normalized DCG against the explicit answer-key priority order, with gain 2^relevance - 1 "
                "and log2(rank + 1) discount; null when no gold order is supplied."
            ),
            "gold_obligations_unlocked_per_clarification": (
                "Gold obligations linked to predicted gold clarification categories / predicted question count; "
                "does not assert that a user actually answered those questions."
            ),
            "clarification_savings_vs_baseline": (
                "Mean baseline question count minus compiler question count over only cases where both "
                "pipelines returned SUCCESS; the report records that paired-case denominator."
            ),
            "paired_pipeline_comparisons": (
                "Each pair is rescored on the intersection of cases accepted by both pipelines; "
                "compare only these entries when acceptance differs."
            ),
            "repeated_run_stable_cases": (
                "Repeated-run means and population standard deviations are recomputed on the exact "
                "case IDs accepted in every repetition for that pipeline or pipeline pair, then "
                "restricted per metric to cases with a defined score in every repetition. If there "
                "is no common applicable case, the repeated metric is null rather than mixing cohorts."
            ),
            "paired_effect_interval": (
                "The 95% percentile bootstrap resamples paired case IDs after averaging each paired "
                "case across completed repetitions. It describes case-sampling variability inside "
                "this dataset, not model-call variability, statistical significance, or generalization."
            ),
            "limitations": [
                "Answer-key quality still depends on human authorship and independent review.",
                "Macro averages and repeated-run population standard deviation are descriptive; they do not establish statistical significance.",
                "A benchmark result does not prove production correctness, generalization, or superiority outside this dataset.",
                "Pipeline failures and output rejections are reported separately from quality scores.",
                "Synthetic rule-generated cases are engineering checks and are not a substitute for independently reviewed real-world scenarios.",
            ],
        }

    @staticmethod
    def _unscored_candidate_metrics():
        return {
            "source_quote_validity": None,
            "source_quote": {
                "precision": None,
                "recall": None,
                "matched": [],
                "unexpected": [],
                "missing": [],
                "source_reference": {
                    "precision": None,
                    "recall": None,
                    "matched": [],
                    "unexpected": [],
                    "missing": [],
                },
            },
            "clarification": {
                "precision": None,
                "recall": None,
                "matched": [],
                "unexpected": [],
                "missing": [],
            },
            "obligation": {
                "precision": None,
                "recall": None,
                "matched": [],
                "unexpected": [],
                "missing": [],
            },
            "clarification_count": None,
            "clarification_priority": {"ndcg": None, "first_relevant_rank": None},
            "gold_obligations_unlocked_per_clarification": None,
        }

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

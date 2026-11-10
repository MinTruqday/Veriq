import math

from loguru import logger

from src.schemas.evaluation import TestabilityBenchmarkReport, TestabilityBenchmarkRequest


class TestabilityBenchmarkCaseScoring:
    """Per-case metrics and aggregate Benchmark reports."""

    @staticmethod
    def _case_source_texts(case) -> list[str]:
        if case.sources:
            return [source.text for source in case.sources if source.text.strip()]
        return [case.source_text] if case.source_text.strip() else []

    @classmethod
    def _candidate_scores(
        cls, case, candidate, *, score_obligations=True, score_clarifications=True
    ) -> dict:
        def non_empty_values(values):
            return [value.strip() for value in values if isinstance(value, str) and value.strip()]

        source_texts = cls._case_source_texts(case)
        source_text_by_ref = {
            source.artifact_version_id: source.text for source in case.sources
        }
        quote_scores = cls._source_quote_scores(
            case.expected_source_quotes,
            candidate.source_quotes,
        )
        quote_scores["source_reference"] = cls._source_quote_reference_scores(
            case, candidate
        )
        grounded_quotes = [
            quote for quote in candidate.source_quotes
            if cls._quote_is_grounded_in_one_source(quote, source_texts)
        ]
        unique_candidate_quotes = {
            cls._normalize_source_quote(quote)
            for quote in candidate.source_quotes
            if cls._normalize_source_quote(quote)
        }
        unique_grounded_quotes = {
            cls._normalize_source_quote(quote) for quote in grounded_quotes
        }
        expected_clarifications = (
            case.expected_clarification_categories or case.expected_clarification_codes
        )
        actual_clarifications = non_empty_values(candidate.clarification_categories)
        if not actual_clarifications:
            actual_clarifications = non_empty_values(candidate.clarification_codes)
        clarification_scores = (
            cls._set_scores(expected_clarifications, actual_clarifications)
            if score_clarifications else {"precision": None, "recall": None, "matched": [], "unexpected": [], "missing": []}
        )
        if not score_obligations:
            obligation_scores = {
                "precision": None, "recall": None, "matched": [], "unexpected": [], "missing": []
            }
        elif case.expected_obligation_sources:
            predicted_obligations = candidate.obligation_evidence
            predicted_keys = sorted(
                set(non_empty_values(candidate.obligation_keys))
                | set(non_empty_values(list(predicted_obligations)))
                | set(non_empty_values(list(candidate.obligation_citations)))
            )
            remaining_predictions = set(predicted_keys)
            predicted_count = len(remaining_predictions)
            expected_keys = sorted(case.expected_obligation_sources)
            grounded_unversioned = {}
            grounded_versioned = {}
            for predicted_key in predicted_keys:
                grounded_unversioned[predicted_key] = [
                    cls._normalize_source_quote(quote)
                    for quote in predicted_obligations.get(predicted_key, [])
                    if cls._quote_is_grounded_in_one_source(quote, source_texts)
                ]
                grounded_versioned[predicted_key] = [
                    (cls._normalize_source_quote(citation.quote), citation.source_ref)
                    for citation in candidate.obligation_citations.get(predicted_key, [])
                    if cls._quote_is_grounded_in_one_source(
                        citation.quote,
                        [source_text_by_ref[citation.source_ref]]
                        if citation.source_ref in source_text_by_ref
                        else source_texts if not case.sources else [],
                    )
                ]
            adjacency = []
            for expected_key in expected_keys:
                expected_quote = cls._normalize_source_quote(
                    case.expected_obligation_sources[expected_key]
                )
                expected_source_ref = case.expected_obligation_source_refs.get(expected_key)
                compatible_predictions = []
                for prediction_index, predicted_key in enumerate(predicted_keys):
                    if expected_source_ref:
                        is_compatible = any(
                            quote == expected_quote and source_ref == expected_source_ref
                            for quote, source_ref in grounded_versioned[predicted_key]
                        )
                    else:
                        is_compatible = any(
                            quote == expected_quote
                            for quote in grounded_unversioned[predicted_key]
                        )
                    if is_compatible:
                        compatible_predictions.append(prediction_index)
                adjacency.append(compatible_predictions)
            prediction_to_expected = cls._maximum_obligation_matching(
                adjacency, len(predicted_keys)
            )
            matched_prediction_to_expected = {
                predicted_keys[prediction_index]: expected_keys[expected_index]
                for prediction_index, expected_index in prediction_to_expected.items()
            }
            matched_obligations = list(matched_prediction_to_expected.values())
            remaining_predictions.difference_update(matched_prediction_to_expected)
            expected_count = len(case.expected_obligation_sources)
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
        priority_scores = (
            cls._clarification_priority_scores(
                case.expected_clarification_priorities,
                actual_clarifications,
            )
            if score_clarifications else {"ndcg": None, "first_relevant_rank": None}
        )
        clarified = {
            obligation
            for code in set(actual_clarifications)
            if code in expected_clarifications
            for obligation in case.expected_clarification_unlocks.get(code, [])
        }
        clarification_count = (
            len(non_empty_values(candidate.clarification_codes) or actual_clarifications)
            if score_clarifications else None
        )
        return {
            "source_quote_validity": (
                round(len(unique_grounded_quotes) / len(unique_candidate_quotes), 4)
                if unique_candidate_quotes else None
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
        relevance = {
            value: len(expected_order) - index
            for index, value in enumerate(expected_order)
        }
        discounted_gain = sum(
            (2 ** relevance.get(value, 0) - 1) / math.log2(index + 2)
            for index, value in enumerate(actual_order)
        )
        ideal_gain = sum(
            (2 ** (len(expected_order) - index) - 1) / math.log2(index + 2)
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
        self_review_before_scores = []
        self_reviewed_scores = []
        for case in request.cases:
            clarification = self._candidate_scores(
                case,
                case.clarification_without_obligation_planning,
                score_obligations=False,
            )
            compiler = self._candidate_scores(case, case.compiler)
            direct = self._candidate_scores(
                case, case.direct_generation, score_clarifications=False
            )
            clarification_scores.append(clarification)
            compiler_scores.append(compiler)
            direct_scores.append(direct)
            self_review_before = self._candidate_scores(
                case, case.blueprint_before_self_review, score_clarifications=True
            )
            self_reviewed = self._candidate_scores(
                case, case.blueprint_after_self_review, score_clarifications=True
            )
            self_review_before_scores.append(self_review_before)
            self_reviewed_scores.append(self_reviewed)
            cases.append(
                {
                    "case_id": case.case_id,
                    "scenario_family": case.scenario_family,
                    "clarification_without_obligation_planning": clarification,
                    "compiler": compiler,
                    "direct_generation": direct,
                    "blueprint_before_self_review": self_review_before,
                    "blueprint_after_self_review": self_reviewed,
                }
            )

        def average_metric(values, key):
            applicable = [value[key] for value in values if value[key] is not None]
            return round(sum(applicable) / len(applicable), 4) if applicable else None

        def aggregate(values):
            return {
                "source_quote_validity": average_metric(values, "source_quote_validity"),
                "source_quote_precision": average_metric(
                    [{"metric": value["source_quote"]["precision"]} for value in values],
                    "metric",
                ),
                "source_quote_recall": average_metric(
                    [{"metric": value["source_quote"]["recall"]} for value in values],
                    "metric",
                ),
                "source_quote_source_precision": average_metric(
                    [{"metric": value["source_quote"]["source_reference"]["precision"]} for value in values],
                    "metric",
                ),
                "source_quote_source_recall": average_metric(
                    [{"metric": value["source_quote"]["source_reference"]["recall"]} for value in values],
                    "metric",
                ),
                "clarification_precision": average_metric(
                    [{"metric": value["clarification"]["precision"]} for value in values],
                    "metric",
                ),
                "clarification_recall": average_metric(
                    [{"metric": value["clarification"]["recall"]} for value in values],
                    "metric",
                ),
                "obligation_precision": average_metric(
                    [{"metric": value["obligation"]["precision"]} for value in values],
                    "metric",
                ),
                "obligation_recall": average_metric(
                    [{"metric": value["obligation"]["recall"]} for value in values],
                    "metric",
                ),
                "average_clarification_count": average_metric(
                    [{"metric": value["clarification_count"]} for value in values],
                    "metric",
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

        def metric_case_counts(values):
            counts = {}
            for metric_name, path in metric_paths.items():
                applicable = []
                for value in values:
                    score = value
                    for key in path:
                        score = score.get(key) if isinstance(score, dict) else None
                    if score is not None:
                        applicable.append(score)
                counts[metric_name] = len(applicable)
            return counts

        report = TestabilityBenchmarkReport(
            total_cases=len(cases),
            clarification_without_obligation_planning=aggregate(clarification_scores),
            compiler=aggregate(compiler_scores),
            direct_generation=aggregate(direct_scores),
            blueprint_before_self_review=aggregate(self_review_before_scores),
            blueprint_after_self_review=aggregate(self_reviewed_scores),
            cases=cases,
            scenario_family_counts={
                family: sum(case.scenario_family == family for case in request.cases)
                for family in (
                    "COMPLETE",
                    "MISSING_OR_AMBIGUOUS",
                    "DUPLICATE_OR_CONFLICT",
                )
                if any(case.scenario_family == family for case in request.cases)
            },
            clarification_savings_vs_baseline=(
                round(
                    sum(
                        baseline["clarification_count"] - compiler["clarification_count"]
                        for baseline, compiler in zip(clarification_scores, compiler_scores)
                    ) / len(cases),
                    4,
                )
                if cases else None
            ),
            clarification_savings_paired_cases=len(cases),
            scoring_method=self._scoring_method(),
        )
        report.metric_case_counts = {
            "clarification_without_obligation_planning": metric_case_counts(clarification_scores),
            "compiler": metric_case_counts(compiler_scores),
            "direct_generation": metric_case_counts(direct_scores),
            "blueprint_before_self_review": metric_case_counts(self_review_before_scores),
            "blueprint_after_self_review": metric_case_counts(self_reviewed_scores),
        }
        report.benchmark_design = {
            "answer_key_basis": "caller_supplied_case_answer_key",
            "interpretation": "Descriptive only; not a correctness or superiority guarantee.",
        }
        logger.info("Testability compiler benchmark completed cases={}", report.total_cases)
        return report

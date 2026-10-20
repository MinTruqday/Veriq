from loguru import logger

from src.schemas.evaluation import TestabilityBenchmarkRequest, TestabilityBenchmarkReport


class TestabilityBenchmarkService:
    """Score compiler outputs against caller-supplied experimental answer keys."""

    @staticmethod
    def _set_scores(expected: list[str], actual: list[str]) -> dict:
        expected_values = {value.strip() for value in expected if value.strip()}
        actual_values = {value.strip() for value in actual if value.strip()}
        matched = expected_values & actual_values
        return {
            "precision": round(len(matched) / len(actual_values), 4) if actual_values else 0.0,
            "recall": round(len(matched) / len(expected_values), 4) if expected_values else 1.0,
            "matched": sorted(matched),
            "unexpected": sorted(actual_values - expected_values),
            "missing": sorted(expected_values - actual_values),
        }

    @classmethod
    def _candidate_scores(cls, case, candidate) -> dict:
        quote_scores = cls._set_scores(case.expected_source_quotes, candidate.source_quotes)
        grounded_quotes = [quote for quote in candidate.source_quotes if quote and quote in case.source_text]
        clarification_scores = cls._set_scores(
            case.expected_clarification_codes, candidate.clarification_codes
        )
        obligation_scores = cls._set_scores(case.expected_obligation_keys, candidate.obligation_keys)
        return {
            "source_quote_validity": round(
                len(grounded_quotes) / len(candidate.source_quotes), 4
            ) if candidate.source_quotes else 0.0,
            "source_quote": quote_scores,
            "clarification": clarification_scores,
            "obligation": obligation_scores,
            "clarification_count": len(
                {value.strip() for value in candidate.clarification_codes if value.strip()}
            ),
        }

    async def evaluate(self, request: TestabilityBenchmarkRequest) -> TestabilityBenchmarkReport:
        """Compare grounded compiler output with direct generation per supplied case."""
        cases = []
        compiler_scores = []
        direct_scores = []
        for case in request.cases:
            compiler = self._candidate_scores(case, case.compiler)
            direct = self._candidate_scores(case, case.direct_generation)
            compiler_scores.append(compiler)
            direct_scores.append(direct)
            cases.append(
                {"case_id": case.case_id, "compiler": compiler, "direct_generation": direct}
            )

        def aggregate(values):
            return {
                "source_quote_validity": round(
                    sum(value["source_quote_validity"] for value in values) / len(values), 4
                ),
                "source_quote_recall": round(
                    sum(value["source_quote"]["recall"] for value in values) / len(values), 4
                ),
                "clarification_recall": round(
                    sum(value["clarification"]["recall"] for value in values) / len(values), 4
                ),
                "obligation_recall": round(
                    sum(value["obligation"]["recall"] for value in values) / len(values), 4
                ),
                "average_clarification_count": round(
                    sum(value["clarification_count"] for value in values) / len(values), 4
                ),
            }

        report = TestabilityBenchmarkReport(
            total_cases=len(cases),
            compiler=aggregate(compiler_scores),
            direct_generation=aggregate(direct_scores),
            cases=cases,
        )
        logger.info("Testability compiler benchmark completed cases={}", report.total_cases)
        return report


testability_benchmark = TestabilityBenchmarkService()

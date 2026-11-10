from src.benchmark.scoring.cases import TestabilityBenchmarkCaseScoring
from src.benchmark.scoring.core import TestabilityBenchmarkCoreScoring
from src.benchmark.scoring.obligations import TestabilityBenchmarkObligationScoring
from src.benchmark.scoring.source_quotes import TestabilityBenchmarkSourceQuoteScoring


class TestabilityBenchmarkScoring(
    TestabilityBenchmarkCaseScoring,
    TestabilityBenchmarkObligationScoring,
    TestabilityBenchmarkSourceQuoteScoring,
    TestabilityBenchmarkCoreScoring,
):
    """Public scorer composed from focused scoring modules."""

    PAIRED_BOOTSTRAP_RESAMPLES = 10000


__all__ = ["TestabilityBenchmarkScoring"]

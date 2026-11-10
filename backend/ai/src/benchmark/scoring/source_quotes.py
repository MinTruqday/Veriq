import unicodedata


class TestabilityBenchmarkSourceQuoteScoring:
    """Source quotation scoring and source-version citation checks."""

    @staticmethod
    def _normalize_source_quote(value: str) -> str:
        normalized = unicodedata.normalize("NFC", str(value or ""))
        normalized = " ".join(normalized.split())
        return normalized.rstrip(".!?。！？").rstrip()

    @classmethod
    def _contains_quote_at_word_boundaries(cls, quote: str, source_text: str) -> bool:
        normalized_quote = cls._normalize_source_quote(quote).casefold()
        normalized_source = cls._normalize_source_quote(source_text).casefold()
        if not normalized_quote:
            return False

        def is_word_character(value):
            return value.isalnum() or value == "_"

        offset = 0
        while True:
            match_start = normalized_source.find(normalized_quote, offset)
            if match_start < 0:
                break
            match_end = match_start + len(normalized_quote)
            left_is_word = match_start > 0 and is_word_character(
                normalized_source[match_start - 1]
            )
            right_is_word = match_end < len(normalized_source) and is_word_character(
                normalized_source[match_end]
            )
            quote_starts_with_word = is_word_character(normalized_quote[0])
            quote_ends_with_word = is_word_character(normalized_quote[-1])
            if not (quote_starts_with_word and left_is_word) and not (
                quote_ends_with_word and right_is_word
            ):
                return True
            offset = match_start + 1
        return False

    @classmethod
    def _quote_is_grounded_in_one_source(cls, quote: str, source_texts: list[str]) -> bool:
        return any(
            cls._contains_quote_at_word_boundaries(quote, source_text)
            for source_text in source_texts
        )

    @classmethod
    def _source_quote_scores(cls, expected: list[str], actual: list[str]) -> dict:
        expected_values = list(dict.fromkeys(
            normalized
            for normalized in (
                cls._normalize_source_quote(value) for value in expected
            )
            if normalized
        ))
        actual_values = list(dict.fromkeys(
            normalized
            for normalized in (
                cls._normalize_source_quote(value) for value in actual
            )
            if normalized
        ))
        expected_set = {value for value in expected_values if value}
        actual_set = {value for value in actual_values if value}
        covered = {
            expected_quote
            for expected_quote in expected_set
            if any(
                cls._contains_quote_at_word_boundaries(expected_quote, actual_quote)
                for actual_quote in actual_set
            )
        }
        supporting = {
            actual_quote
            for actual_quote in actual_set
            if any(
                cls._contains_quote_at_word_boundaries(expected_quote, actual_quote)
                for expected_quote in expected_set
            )
        }
        return {
            "precision": (
                round(len(supporting) / len(actual_values), 4)
                if actual_values else (0.0 if expected_values else None)
            ),
            "recall": (
                round(len(covered) / len(expected_values), 4)
                if expected_values else None
            ),
            "matched": sorted(covered),
            "unexpected": sorted(actual_set - supporting),
            "missing": sorted(set(expected_values) - covered),
        }

    @classmethod
    def _source_quote_reference_scores(cls, case, candidate) -> dict:
        expected = {
            cls._normalize_source_quote(quote): set(source_refs)
            for quote, source_refs in case.expected_source_quote_sources.items()
            if cls._normalize_source_quote(quote) and source_refs
        }
        if not expected:
            return {
                "precision": None,
                "recall": None,
                "matched": [],
                "unexpected": [],
                "missing": [],
            }

        source_text_by_ref = {
            source.artifact_version_id: source.text for source in case.sources
        }
        actual = {
            (cls._normalize_source_quote(item.quote), item.source_ref)
            for item in candidate.source_quote_citations
            if cls._normalize_source_quote(item.quote) and item.source_ref
        }

        def citation_matches_gold(quote, source_ref):
            source_text = source_text_by_ref.get(source_ref)
            if source_text is None or not cls._quote_is_grounded_in_one_source(
                quote, [source_text]
            ):
                return False
            return any(
                source_ref in source_refs
                and cls._contains_quote_at_word_boundaries(gold_quote, quote)
                for gold_quote, source_refs in expected.items()
            )

        supported = {item for item in actual if citation_matches_gold(*item)}
        covered = {
            gold_quote
            for gold_quote, source_refs in expected.items()
            if any(
                source_ref in source_refs
                and cls._contains_quote_at_word_boundaries(gold_quote, quote)
                and citation_matches_gold(quote, source_ref)
                for quote, source_ref in actual
            )
        }
        return {
            "precision": round(len(supported) / len(actual), 4) if actual else 0.0,
            "recall": round(len(covered) / len(expected), 4),
            "matched": sorted(covered),
            "unexpected": sorted(actual - supported),
            "missing": sorted(set(expected) - covered),
        }

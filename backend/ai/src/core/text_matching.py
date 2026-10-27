def source_quote_spans(text: str, quote: str) -> list[tuple[int, int]]:
    if not isinstance(text, str) or not isinstance(quote, str) or not quote:
        return []

    def is_word_character(value):
        return value.isalnum() or value == "_"

    quote_starts_with_word = is_word_character(quote[0])
    quote_ends_with_word = is_word_character(quote[-1])
    spans = []
    cursor = 0
    while True:
        start = text.find(quote, cursor)
        if start < 0:
            return spans
        end = start + len(quote)
        left_is_word = start > 0 and is_word_character(text[start - 1])
        right_is_word = end < len(text) and is_word_character(text[end])
        if not (quote_starts_with_word and left_is_word) and not (
            quote_ends_with_word and right_is_word
        ):
            spans.append((start, end))
        cursor = start + 1

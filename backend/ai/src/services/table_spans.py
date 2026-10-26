import re


def _markdown_cells(content: str) -> list[tuple[int, int]]:
    boundaries = []
    escaped = False
    for index, character in enumerate(content):
        if character == "|" and not escaped:
            boundaries.append(index)
        if character == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    return list(zip(boundaries, boundaries[1:]))


def markdown_table_cell_spans(markdown: str) -> list[dict]:
    spans = []
    offset = 0
    row_index = 0
    for line in markdown.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        stripped = content.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = _markdown_cells(content)
            values = [content[left + 1 : right].strip() for left, right in cells]
            if values and not all(
                re.fullmatch(r":?-{3,}:?", value) for value in values
            ):
                for column_index, (left, right) in enumerate(cells):
                    raw_cell = content[left + 1 : right]
                    leading = len(raw_cell) - len(raw_cell.lstrip())
                    value = raw_cell.strip()
                    if value:
                        cell_start = offset + left + 1 + leading
                        spans.append(
                            {
                                "row_index": row_index,
                                "column_index": column_index,
                                "source_start": cell_start,
                                "source_end": cell_start + len(value),
                            }
                        )
                row_index += 1
        offset += len(line)
    return spans


def markdown_table_metadata(
    markdown: str,
    table_id: str | None = None,
    metadata_source: str | None = None,
) -> dict:
    cell_spans = markdown_table_cell_spans(markdown)
    data_rows = []
    for line in markdown.splitlines():
        content = line.rstrip("\r\n")
        stripped = content.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = _markdown_cells(content)
        values = [content[left + 1 : right].strip() for left, right in cells]
        if values and not all(re.fullmatch(r":?-{3,}:?", value) for value in values):
            data_rows.append(values)
    first_row = data_rows[0] if data_rows else []
    return {
        "table_id": table_id,
        "row_count": len(data_rows),
        "column_count": max((len(row) for row in data_rows), default=0),
        "column_headers": first_row,
        "metadata_source": metadata_source,
        "cell_spans": cell_spans,
    }

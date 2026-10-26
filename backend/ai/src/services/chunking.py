import json
import math
import re
from hashlib import sha256
from typing import Any, Dict, List, Optional, Sequence
from uuid import NAMESPACE_URL, uuid5

from loguru import logger

from src.services.embedding import embedder
from src.services.table_spans import markdown_table_metadata


class ChunkingService:
    def __init__(
        self,
        min_chars: int | None = None,
        target_chars: int | None = None,
        max_chars: int | None = None,
        semantic_threshold: float | None = None,
        soft_threshold: float | None = None,
    ):
        min_chars = min_chars or 200
        target_chars = target_chars or 900
        max_chars = max_chars or 1600
        semantic_threshold = semantic_threshold if semantic_threshold is not None else 0.55
        soft_threshold = soft_threshold if soft_threshold is not None else 0.72
        if not 0 < min_chars <= target_chars <= max_chars:
            raise ValueError("chunk_size_bounds_invalid")
        self.min_chars = min_chars
        self.target_chars = target_chars
        self.max_chars = max_chars
        self.semantic_threshold = semantic_threshold
        self.soft_threshold = soft_threshold
        logger.info("Initializing unified document ChunkingService")

    async def chunk_document(
        self, markdown: str, metadata: Dict, structure: Optional[Sequence[Any]] = None
    ) -> List[Dict]:
        units = self._structure_units(markdown, structure or [])
        if not units:
            return []

        try:
            semantic_groups = await self._semantic_refinement_batched(units)
            chunk_type = "docling_structure_semantic"
        except Exception as error:
            logger.warning(
                "Semantic refinement failed; preserving Docling boundaries ({})",
                type(error).__name__,
            )
            semantic_groups = self._structural_groups(units)
            chunk_type = "docling_structure_fallback"

        guarded_groups = self._size_guard(semantic_groups)
        return self._serialize_groups(guarded_groups, metadata, chunk_type)

    def _structure_units(self, markdown: str, structure: Sequence[Any]) -> List[Dict]:
        units = []
        image_only_units = []
        seen_blocks = set()
        section_path = []
        for index, item in enumerate(structure):
            if not isinstance(item, dict):
                dump = getattr(item, "model_dump", None)
                if not callable(dump):
                    raise ValueError("source_structure_block_invalid")
                item = dump(exclude_none=True)
            raw_text = str(item.get("text") or "")
            text = raw_text.strip()
            trim_start = len(raw_text) - len(raw_text.lstrip())
            block_id = item.get("block_id")
            item_type = str(item.get("type") or "text").casefold()
            if block_id and block_id in seen_blocks:
                continue
            if block_id:
                seen_blocks.add(block_id)
            level = item.get("level")
            if item_type in {"title", "section_header", "chapter", "heading"}:
                if level is None:
                    section_path = [(None, text)]
                else:
                    while section_path and (
                        section_path[-1][0] is None
                        or section_path[-1][0] >= level
                    ):
                        section_path.pop()
                    section_path.append((level, text))
            table_metadata = item.get("table_metadata")
            if item_type == "table":
                extracted_metadata = markdown_table_metadata(text, block_id)
                existing_metadata = (
                    table_metadata if isinstance(table_metadata, dict) else {}
                )
                table_metadata = {**extracted_metadata, **existing_metadata}
                cell_spans = existing_metadata.get("cell_spans") or extracted_metadata[
                    "cell_spans"
                ]
                if cell_spans:
                    table_metadata["cell_spans"] = [
                        {
                            **cell,
                            "source_start": cell["source_start"] - trim_start,
                            "source_end": cell["source_end"] - trim_start,
                        }
                        for cell in cell_spans
                    ]
                else:
                    table_metadata.pop("cell_spans", None)
                if not existing_metadata and not extracted_metadata["cell_spans"]:
                    table_metadata = None
            if not text:
                if item_type in {"picture", "image"} and item.get("image_metadata"):
                    image_only_units.append(
                        {
                            "block_id": block_id,
                            "parent_block_id": item.get("parent_block_id"),
                            "block_index": index,
                            "level": item.get("level"),
                            "type": item_type,
                            "extraction_status": item.get("extraction_status"),
                            "section_path": [heading for _, heading in section_path],
                            "locations": item.get("locations") or [],
                            "image_metadata": item.get("image_metadata"),
                        }
                    )
                continue
            units.append(
                {
                    "text": text,
                    "type": item_type,
                    "level": item.get("level"),
                    "page_no": item.get("page_no"),
                    "block_id": block_id,
                    "parent_block_id": item.get("parent_block_id"),
                    "block_index": index,
                    "extraction_status": item.get("extraction_status"),
                    "ocr_page_confidence": item.get("ocr_page_confidence"),
                    "section_path": [heading for _, heading in section_path],
                    "locations": item.get("locations")
                    or (
                        [{"page_no": item["page_no"], "bbox": None}]
                        if item.get("page_no") is not None
                        else []
                    ),
                    "table_metadata": table_metadata,
                    "image_metadata": item.get("image_metadata"),
                    "source_start": 0,
                    "source_end": len(text),
                    "hard_boundary": item_type in {"title", "section_header", "chapter", "heading"},
                }
            )
        if units:
            units_by_page = {}
            units_by_parent_page = {}
            units_without_page_by_parent = {}
            unit_pages_by_index = {}
            for unit in units:
                unit_pages = {
                    location.get("page_no")
                    for location in unit.get("locations", [])
                    if isinstance(location, dict)
                    and isinstance(location.get("page_no"), int)
                    and not isinstance(location.get("page_no"), bool)
                }
                if not unit_pages:
                    unit_page = unit.get("page_no")
                    if isinstance(unit_page, int) and not isinstance(unit_page, bool):
                        unit_pages.add(unit_page)
                unit_pages_by_index[unit["block_index"]] = unit_pages
                for page_no in unit_pages:
                    units_by_page.setdefault(page_no, []).append(unit)
                    parent_id = unit.get("parent_block_id")
                    if parent_id:
                        units_by_parent_page.setdefault((parent_id, page_no), []).append(unit)
                if not unit_pages and unit.get("parent_block_id"):
                    units_without_page_by_parent.setdefault(
                        unit["parent_block_id"], []
                    ).append(unit)

            for image_unit in image_only_units:
                image_pages = {
                    location.get("page_no")
                    for location in image_unit.get("locations", [])
                    if isinstance(location, dict)
                    and isinstance(location.get("page_no"), int)
                    and not isinstance(location.get("page_no"), bool)
                }
                if not image_pages:
                    image_page = image_unit.get("page_no")
                    if isinstance(image_page, int) and not isinstance(image_page, bool):
                        image_pages.add(image_page)
                parent_id = image_unit.get("parent_block_id")
                candidate_units = {}
                if image_pages:
                    for page_no in image_pages:
                        for unit in units_by_page.get(page_no, []):
                            candidate_units[unit["block_index"]] = unit
                        if parent_id:
                            for unit in units_by_parent_page.get((parent_id, page_no), []):
                                candidate_units[unit["block_index"]] = unit
                elif parent_id:
                    for unit in units_without_page_by_parent.get(parent_id, []):
                        candidate_units[unit["block_index"]] = unit

                candidates = []
                for unit in candidate_units.values():
                    same_page = bool(image_pages.intersection(
                        unit_pages_by_index[unit["block_index"]]
                    ))
                    same_parent = bool(
                        parent_id
                        and parent_id == unit.get("parent_block_id")
                        and (same_page or not image_pages)
                    )
                    candidates.append(
                        (
                            0 if same_parent else 1,
                            abs(unit["block_index"] - image_unit["block_index"]),
                            unit,
                        )
                    )
                if candidates:
                    nearest_unit = min(candidates, key=lambda item: (item[0], item[1]))[2]
                    nearest_unit.setdefault("related_images", []).append(image_unit)
            return units

        return [
            {
                "text": text,
                "type": item_type,
                "level": None,
                "page_no": None,
                "block_index": index,
                "source_start": 0,
                "source_end": len(text),
                "hard_boundary": item_type == "section_header",
            }
            for index, (text, item_type) in enumerate(self._markdown_units(markdown))
        ]

    def _markdown_units(self, markdown: str) -> List[tuple[str, str]]:
        units = []
        for part in re.split(r"\n\s*\n+", markdown):
            text = part.strip()
            if not text:
                continue
            item_type = "section_header" if re.match(r"^#{1,6}\s+", text) else "text"
            units.append((text, item_type))
        return units

    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        if len(left) != len(right) or not left:
            raise ValueError("semantic_embedding_dimension_mismatch")
        dot_product = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot_product / (left_norm * right_norm)

    def _semantic_refinement(
        self, units: List[Dict], embeddings: List[List[float]]
    ) -> List[List[Dict]]:
        groups: List[List[Dict]] = []
        current = [units[0]]
        current_length = len(units[0]["text"])

        for index, unit in enumerate(units[1:], start=1):
            similarity = self._cosine_similarity(embeddings[index - 1], embeddings[index])
            topic_changed = similarity < self.semantic_threshold
            soft_boundary = current_length >= self.target_chars and similarity < self.soft_threshold
            structure_boundary = unit["hard_boundary"]
            should_split = current_length >= self.min_chars and (
                structure_boundary or topic_changed or soft_boundary
            )
            if should_split:
                groups.append(current)
                current = [unit]
                current_length = len(unit["text"])
            else:
                current.append(unit)
                current_length += len(unit["text"]) + 2
        groups.append(current)
        return groups

    async def _semantic_refinement_batched(
        self, units: List[Dict]
    ) -> List[List[Dict]]:
        batch_size = getattr(embedder, "_batch_size", None)
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
            raise ValueError("semantic_embedding_batch_size_invalid")

        groups: List[List[Dict]] = []
        current = [units[0]]
        current_length = len(units[0]["text"])
        previous_embedding = None

        for batch_start in range(0, len(units), batch_size):
            batch_units = units[batch_start : batch_start + batch_size]
            embeddings = await embedder.embed_batch(
                [unit["text"] for unit in batch_units]
            )
            if len(embeddings) != len(batch_units):
                raise ValueError("semantic_embedding_count_mismatch")

            for unit, embedding in zip(batch_units, embeddings):
                if not isinstance(embedding, list) or not embedding:
                    raise ValueError("semantic_embedding_shape_invalid")
                if previous_embedding is not None:
                    similarity = self._cosine_similarity(previous_embedding, embedding)
                    topic_changed = similarity < self.semantic_threshold
                    soft_boundary = (
                        current_length >= self.target_chars
                        and similarity < self.soft_threshold
                    )
                    if current_length >= self.min_chars and (
                        unit["hard_boundary"] or topic_changed or soft_boundary
                    ):
                        groups.append(current)
                        current = [unit]
                        current_length = len(unit["text"])
                    else:
                        current.append(unit)
                        current_length += len(unit["text"]) + 2
                previous_embedding = embedding

        groups.append(current)
        return groups

    def _structural_groups(self, units: List[Dict]) -> List[List[Dict]]:
        groups: List[List[Dict]] = []
        current: List[Dict] = []
        current_length = 0
        for unit in units:
            if current and unit["hard_boundary"] and current_length >= self.min_chars:
                groups.append(current)
                current = []
                current_length = 0
            current.append(unit)
            current_length += len(unit["text"]) + (2 if current_length else 0)
        if current:
            groups.append(current)
        return groups

    def _size_guard(self, groups: List[List[Dict]]) -> List[List[Dict]]:
        guarded: List[List[Dict]] = []
        for group in groups:
            current: List[Dict] = []
            current_length = 0
            for unit in group:
                for bounded_unit in self._split_oversized_unit(unit):
                    projected = current_length + len(bounded_unit["text"]) + (2 if current else 0)
                    if current and projected > self.max_chars:
                        guarded.append(current)
                        current = [bounded_unit]
                        current_length = len(bounded_unit["text"])
                    else:
                        current.append(bounded_unit)
                        current_length = projected
            if current:
                guarded.append(current)
        return guarded

    def _split_oversized_unit(self, unit: Dict) -> List[Dict]:
        text = unit["text"]
        if len(text) <= self.max_chars:
            return [unit]
        if unit.get("type") == "table" and unit.get("table_metadata"):
            table_chunks = self._split_oversized_table(unit)
            if table_chunks:
                return table_chunks

        pieces = []
        start = 0
        while start < len(text):
            end = min(start + self.max_chars, len(text))
            if end < len(text):
                boundaries = list(re.finditer(r"(?<=[.!?。！？])\s+", text[start:end]))
                if boundaries:
                    end = start + boundaries[-1].end()
            raw = text[start:end]
            piece = raw.strip()
            if piece:
                offset = start + len(raw) - len(raw.lstrip())
                pieces.append(
                    {
                        **unit,
                        "text": piece,
                        "source_start": unit.get("source_start", 0) + offset,
                        "source_end": unit.get("source_start", 0) + offset + len(piece),
                    }
                )
            start = end
        return pieces

    def _split_oversized_table(self, unit: Dict) -> List[Dict]:
        lines = unit["text"].splitlines(keepends=True)
        table_entries = []
        source_cursor = 0
        for line in lines:
            line_start = source_cursor
            source_cursor += len(line)
            if line.strip():
                table_entries.append((line, line_start, line_start + len(line.rstrip("\r\n"))))
        if len(table_entries) < 3 or not all(
            line.strip().startswith("|") and line.strip().endswith("|")
            for line, _, _ in table_entries
        ):
            return []
        header_entries = table_entries[:2]
        data_entries = table_entries[2:]
        cell_spans = unit["table_metadata"].get("cell_spans") or markdown_table_metadata(
            unit["text"]
        )["cell_spans"]
        header = "".join(line for line, _, _ in header_entries)
        if not data_entries or len(header) + len(data_entries[0][0]) > self.max_chars:
            return []

        total_data_rows = len(data_entries)
        groups = []
        current_rows = []
        current_length = len(header)
        row_start = 1
        for row_index, row, source_start, source_end in (
            (index, *entry) for index, entry in enumerate(data_entries, start=1)
        ):
            row_length = len(row)
            if current_rows and current_length + row_length > self.max_chars:
                groups.append((row_start, row_index - 1, current_rows))
                current_rows = []
                row_start = row_index
                current_length = len(header)
            if len(header) + row_length > self.max_chars:
                return []
            current_rows.append((row, source_start, source_end))
            current_length += row_length
        if current_rows:
            groups.append((row_start, total_data_rows, current_rows))

        result = []
        for start_row, end_row, rows in groups:
            source_start = rows[0][1]
            source_end = rows[-1][2]
            rows_text = "".join(row for row, _, _ in rows)
            header_content_end = len(header.rstrip("\r\n"))
            rows_content_end = len(rows_text.rstrip("\r\n"))
            chunk_cell_spans = []
            header_source_start = header_entries[0][1]
            for cell in cell_spans:
                row_index = cell["row_index"]
                if row_index == 0:
                    chunk_cell_spans.append(
                        {
                            **cell,
                            "chunk_start": cell["source_start"] - header_source_start,
                            "chunk_end": cell["source_end"] - header_source_start,
                        }
                    )
                    continue
                if not start_row <= row_index <= end_row:
                    continue
                row_chunk_start = len(header)
                matching_row = None
                for current_row_index, (row, row_source_start, _) in enumerate(
                    rows, start=start_row
                ):
                    if current_row_index == row_index:
                        matching_row = (row_chunk_start, row_source_start)
                        break
                    row_chunk_start += len(row)
                if matching_row is None:
                    continue
                row_chunk_start, row_source_start = matching_row
                chunk_cell_spans.append(
                    {
                        **cell,
                        "chunk_start": row_chunk_start
                        + cell["source_start"]
                        - row_source_start,
                        "chunk_end": row_chunk_start
                        + cell["source_end"]
                        - row_source_start,
                    }
                )
            source_segments = [
                {
                    "role": "REPEATED_HEADER" if start_row > 1 else "HEADER",
                    "source_start": header_entries[0][1],
                    "source_end": header_entries[-1][2],
                    "chunk_start": 0,
                    "chunk_end": header_content_end,
                },
                {
                    "role": "DATA_ROWS",
                    "source_start": source_start,
                    "source_end": source_end,
                    "chunk_start": len(header),
                    "chunk_end": len(header) + rows_content_end,
                },
            ]
            result.append(
                {
                    **unit,
                    "text": header + rows_text,
                    "source_start": source_start,
                    "source_end": source_end,
                    "source_segments": source_segments,
                    "table_metadata": {
                        **unit["table_metadata"],
                        "cell_spans": chunk_cell_spans,
                        "data_row_start": start_row,
                        "data_row_end": end_row,
                        "header_repeated": start_row > 1,
                        "row_boundary_preserved": True,
                    },
                }
            )
        return result

    @staticmethod
    def _serialize_groups(groups: List[List[Dict]], metadata: Dict, chunk_type: str) -> List[Dict]:
        chunks = []
        for chunk_index, group in enumerate(groups):
            text = "\n\n".join(unit["text"] for unit in group)
            if not text.strip():
                continue
            identity = ":".join(
                [
                    str(metadata.get("document_id") or ""),
                    str(metadata.get("source_version") or ""),
                    str(metadata.get("index_generation") or ""),
                    str(chunk_index),
                    sha256(text.encode()).hexdigest(),
                ]
            )
            chunk_id = str(uuid5(NAMESPACE_URL, identity))
            source_spans = []
            cursor = 0
            for unit in group:
                table_metadata = unit.get("table_metadata")
                if table_metadata:
                    table_metadata = {**table_metadata}
                    table_metadata["cell_spans"] = [
                        {
                            **cell,
                            "chunk_start": cursor
                            + cell.get(
                                "chunk_start",
                                cell["source_start"] - unit.get("source_start", 0),
                            ),
                            "chunk_end": cursor
                            + cell.get(
                                "chunk_end",
                                cell["source_end"] - unit.get("source_start", 0),
                            ),
                        }
                        for cell in table_metadata.get("cell_spans", [])
                    ]
                source_spans.append(
                    {
                        "block_id": unit.get("block_id"),
                        "parent_block_id": unit.get("parent_block_id"),
                        "block_index": unit.get("block_index"),
                        "block_level": unit.get("level"),
                        "content_type": unit["type"],
                        "extraction_status": unit.get("extraction_status"),
                        "ocr_page_confidence": unit.get("ocr_page_confidence"),
                        "section_path": unit.get("section_path", []),
                        "locations": unit.get("locations", []),
                        "table_metadata": table_metadata,
                        "image_metadata": unit.get("image_metadata"),
                        "source_segments": [
                            {
                                **segment,
                                "chunk_start": cursor + segment["chunk_start"],
                                "chunk_end": cursor + segment["chunk_end"],
                            }
                            for segment in unit.get("source_segments", [])
                        ],
                        "source_start": unit.get("source_start", 0),
                        "source_end": unit.get("source_end", len(unit["text"])),
                        "offset_basis": (
                            "normalized_block_segments"
                            if unit.get("source_segments")
                            else "normalized_block"
                        ),
                        "chunk_start": cursor,
                        "chunk_end": cursor + len(unit["text"]),
                    }
                )
                for image in unit.get("related_images", []):
                    source_spans.append(
                        {
                            "block_id": image.get("block_id"),
                            "parent_block_id": image.get("parent_block_id"),
                            "block_index": image.get("block_index"),
                            "block_level": image.get("level"),
                            "content_type": image.get("type"),
                            "extraction_status": image.get("extraction_status"),
                            "section_path": image.get("section_path", []),
                            "locations": image.get("locations", []),
                            "image_metadata": image.get("image_metadata"),
                            "offset_basis": "chunk_anchor",
                            "chunk_start": cursor,
                            "chunk_end": cursor,
                        }
                    )
                cursor += len(unit["text"]) + 2
            page_numbers = sorted(
                {
                    location["page_no"]
                    for span in source_spans
                    for location in span["locations"]
                    if isinstance(location.get("page_no"), int)
                    and not isinstance(location.get("page_no"), bool)
                    and location["page_no"] > 0
                }
            )
            chunk_hash = sha256(text.encode("utf-8")).hexdigest()
            logical_identity = json.dumps(
                {
                    "project_id": metadata.get("project_id"),
                    "document_id": metadata.get("document_id"),
                    "artifact_type": metadata.get("artifact_type"),
                    "artifact_id": metadata.get("artifact_id"),
                    "artifact_version_id": metadata.get("artifact_version_id"),
                    "source_version": metadata.get("source_version"),
                    "source_hash": metadata.get("source_hash"),
                    "normalized_content_hash": metadata.get("normalized_content_hash"),
                    "chunk_hash": chunk_hash,
                    "source_spans": [
                        {
                            "block_id": span.get("block_id"),
                            "parent_block_id": span.get("parent_block_id"),
                            "block_index": span.get("block_index"),
                            "content_type": span.get("content_type"),
                            "section_path": span.get("section_path", []),
                            "locations": span.get("locations", []),
                            "source_start": span.get("source_start"),
                            "source_end": span.get("source_end"),
                            "table_metadata": span.get("table_metadata"),
                            "image_metadata": span.get("image_metadata"),
                        }
                        for span in source_spans
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            logical_chunk_id = str(uuid5(NAMESPACE_URL, logical_identity))
            chunks.append(
                {
                    "id": chunk_id,
                    "text": text,
                    "metadata": {
                        **metadata,
                        "chunk_id": chunk_id,
                        "logical_chunk_id": logical_chunk_id,
                        "chunk_hash": chunk_hash,
                        "chunk_index": chunk_index,
                        "char_count": len(text),
                        "word_count": len(text.split()),
                        "chunk_type": chunk_type,
                        "structure_types": list(dict.fromkeys(unit["type"] for unit in group)),
                        "source_spans": source_spans,
                        "page_numbers": page_numbers,
                        "page_start": min(page_numbers) if page_numbers else None,
                        "page_end": max(page_numbers) if page_numbers else None,
                    },
                }
            )
        return chunks


chunker = ChunkingService()

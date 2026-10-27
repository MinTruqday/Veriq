import hashlib
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)


DOCUMENT_INDEXED_ARTIFACT_TYPES = frozenset(
    {"requirement_document", "project_document", "source_document"}
)


def is_document_indexed_payload(metadata: dict) -> bool:
    artifact_type = str(metadata.get("artifact_type") or "").strip()
    if artifact_type in DOCUMENT_INDEXED_ARTIFACT_TYPES:
        return True
    return not artifact_type and any(
        str(metadata.get(field) or "").strip()
        for field in ("document_id", "source_document_id")
    )


class ProjectSourceLocation(BaseModel):
    model_config = ConfigDict(extra="allow")

    page_no: int | None = Field(default=None, ge=1, strict=True)
    bbox: dict[str, Any] | None = None


class ProjectSourceTableCellSpan(BaseModel):
    row_index: int = Field(ge=0, strict=True)
    column_index: int = Field(ge=0, strict=True)
    source_start: int = Field(ge=0, strict=True)
    source_end: int = Field(gt=0, strict=True)

    @model_validator(mode="after")
    def validate_source_range(self):
        if self.source_end <= self.source_start:
            raise ValueError("table_cell_source_range_invalid")
        return self


class ProjectSourceTableMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    table_id: str | None = None
    row_count: int | None = Field(default=None, ge=0)
    column_count: int | None = Field(default=None, ge=0)
    column_headers: list[str] = Field(default_factory=list)
    metadata_source: str | None = None
    cell_spans: list[ProjectSourceTableCellSpan] = Field(default_factory=list)


class ProjectSourceImageMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    image_id: str | None = None
    extracted_text_present: bool | None = None
    page_ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    asset_available: bool | None = None
    asset_status: str | None = None
    asset_key: str | None = None
    content_type: str | None = None
    content_sha256: str | None = None
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)


class ProjectSourceBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    block_id: str | None = None
    parent_block_id: str | None = None
    text: str = ""
    type: str = Field(min_length=1)
    level: int | None = Field(default=None, strict=True)
    page_no: int | None = Field(default=None, ge=1, strict=True)
    locations: list[ProjectSourceLocation] = Field(default_factory=list)
    extraction_status: Literal["EXTRACTED", "NO_TEXT_EXTRACTED"] | None = None
    ocr_page_confidence: float | None = Field(default=None, ge=0, le=1)
    table_metadata: ProjectSourceTableMetadata | None = None
    image_metadata: ProjectSourceImageMetadata | None = None


def validate_project_source_structure(
    value: Any, *, reuse_input_list: bool = False
) -> list[ProjectSourceBlock]:
    if reuse_input_list and isinstance(value, list):
        block_adapter = TypeAdapter(ProjectSourceBlock)
        blocks = value
        for index, block in enumerate(blocks):
            blocks[index] = block_adapter.validate_python(block)
    else:
        blocks = TypeAdapter(list[ProjectSourceBlock]).validate_python(value)
    for block in blocks:
        if block.table_metadata:
            for cell in block.table_metadata.cell_spans:
                if cell.source_end > len(block.text):
                    raise ValueError("source_structure_table_cell_out_of_range")
                if (
                    block.table_metadata.row_count is not None
                    and cell.row_index >= block.table_metadata.row_count
                ):
                    raise ValueError("source_structure_table_cell_row_invalid")
                if (
                    block.table_metadata.column_count is not None
                    and cell.column_index >= block.table_metadata.column_count
                ):
                    raise ValueError("source_structure_table_cell_column_invalid")
    known_block_ids = set()
    parent_by_block = {
        block.block_id.strip(): block.parent_block_id.strip()
        for block in blocks
        if block.block_id and block.block_id.strip() and block.parent_block_id and block.parent_block_id.strip()
    }
    for block in blocks:
        block_id = block.block_id.strip() if block.block_id else ""
        if block_id:
            if block_id in known_block_ids:
                raise ValueError("source_structure_block_id_ambiguous")
            known_block_ids.add(block_id)
    if any(block_id == parent_id for block_id, parent_id in parent_by_block.items()):
        raise ValueError("source_structure_block_cannot_parent_itself")

    completed = set()
    for start in known_block_ids:
        path = set()
        current = start
        while current in parent_by_block and current in known_block_ids:
            if current in path:
                raise ValueError("source_structure_parent_cycle")
            if current in completed:
                break
            path.add(current)
            parent_id = parent_by_block[current]
            if parent_id not in known_block_ids:
                break
            current = parent_id
        completed.update(path)
    return blocks


class ProjectArtifactIndexRequest(BaseModel):
    artifact_type: str = Field(min_length=1, max_length=100)
    artifact_id: str = Field(min_length=1, max_length=200)
    artifact_version_id: str = Field(min_length=1, max_length=200)
    title: str = Field(default="", max_length=500)
    text: str = Field(min_length=1)
    status: str = Field(default="ACTIVE", max_length=50)
    authority: str = Field(default="PROJECT_REFERENCE", max_length=100)
    version: Any = None
    module: str = Field(default="", max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_structure: list[ProjectSourceBlock] = Field(default_factory=list)

    @field_validator("authority")
    @classmethod
    def validate_authority(cls, value: str) -> str:
        if value not in {
            "APPROVED_SOURCE",
            "CONTROLLED_SOURCE",
            "PROJECT_REFERENCE",
            "SUPPLEMENTAL",
            "DRAFT",
            "UNVERIFIED",
        }:
            raise ValueError("AUTHORITY_INVALID")
        return value

    @model_validator(mode="after")
    def validate_source_structure_identity(self):
        validate_project_source_structure(self.source_structure)
        return self


class ProjectKnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)
    artifact_types: list[str] = Field(default_factory=list, max_length=20)
    limit: int = Field(default=20, ge=1, le=100)
    requester_id: str = Field(min_length=1, max_length=200)
    is_admin: bool = False


class ProjectChunkSourceLocation(BaseModel):
    page_no: int | None = Field(default=None, ge=1, strict=True)
    bbox: dict[str, Any] | None = None


class ProjectChunkTableCellSpan(ProjectSourceTableCellSpan):
    chunk_start: int = Field(ge=0, strict=True)
    chunk_end: int = Field(gt=0, strict=True)

    @model_validator(mode="after")
    def validate_chunk_range(self):
        if self.chunk_end <= self.chunk_start:
            raise ValueError("table_cell_chunk_range_invalid")
        if self.chunk_end - self.chunk_start != self.source_end - self.source_start:
            raise ValueError("table_cell_offset_mapping_invalid")
        return self


class ProjectChunkTableMetadata(BaseModel):
    table_id: str | None = None
    row_count: int | None = Field(default=None, ge=0)
    column_count: int | None = Field(default=None, ge=0)
    column_headers: list[str] = Field(default_factory=list)
    metadata_source: str | None = None
    data_row_start: int | None = Field(default=None, ge=1)
    data_row_end: int | None = Field(default=None, ge=1)
    header_repeated: bool | None = None
    row_boundary_preserved: bool | None = None
    cell_spans: list[ProjectChunkTableCellSpan] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_row_range(self):
        if (
            self.data_row_start is not None
            and self.data_row_end is not None
            and self.data_row_end < self.data_row_start
        ):
            raise ValueError("table_data_row_range_invalid")
        if (
            self.row_count is not None
            and self.data_row_end is not None
            and self.data_row_end >= self.row_count
        ):
            raise ValueError("table_data_row_range_exceeds_table")
        for cell in self.cell_spans:
            if (
                self.column_count is not None
                and cell.column_index >= self.column_count
            ):
                raise ValueError("table_cell_column_invalid")
            if (
                cell.row_index > 0
                and self.data_row_start is not None
                and cell.row_index < self.data_row_start
            ):
                raise ValueError("table_cell_row_before_chunk_range")
            if (
                cell.row_index > 0
                and self.data_row_end is not None
                and cell.row_index > self.data_row_end
            ):
                raise ValueError("table_cell_row_after_chunk_range")
        return self

class ProjectChunkImageMetadata(BaseModel):
    image_id: str | None = None
    extracted_text_present: bool | None = None
    page_ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    asset_available: bool | None = None
    asset_status: str | None = None
    asset_key: str | None = None
    content_type: str | None = None
    content_sha256: str | None = None
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)


class ProjectChunkTextSegment(BaseModel):
    role: str
    source_start: int = Field(ge=0, strict=True)
    source_end: int = Field(gt=0, strict=True)
    chunk_start: int = Field(ge=0, strict=True)
    chunk_end: int = Field(gt=0, strict=True)

    @model_validator(mode="after")
    def validate_offset_mapping(self):
        source_length = self.source_end - self.source_start
        chunk_length = self.chunk_end - self.chunk_start
        if source_length <= 0 or chunk_length <= 0 or source_length != chunk_length:
            raise ValueError("chunk_source_segment_offset_mapping_invalid")
        return self


class ProjectChunkSourceSpan(BaseModel):
    block_id: str | None = None
    parent_block_id: str | None = None
    ancestor_block_ids: list[str] = Field(default_factory=list)
    ancestor_chain_status: Literal["ROOT", "COMPLETE", "PARTIAL"] | None = None
    block_index: int | None = Field(default=None, strict=True)
    block_level: int | None = Field(default=None, strict=True)
    content_type: str | None = None
    extraction_status: str | None = None
    ocr_page_confidence: float | None = Field(default=None, ge=0, le=1)
    section_path: list[str] = Field(default_factory=list)
    locations: list[ProjectChunkSourceLocation] = Field(default_factory=list)
    table_metadata: ProjectChunkTableMetadata | None = None
    image_metadata: ProjectChunkImageMetadata | None = None
    source_segments: list[ProjectChunkTextSegment] = Field(default_factory=list)
    source_start: int | None = Field(default=None, strict=True)
    source_end: int | None = Field(default=None, strict=True)
    offset_basis: str | None = None
    chunk_start: int | None = Field(default=None, strict=True)
    chunk_end: int | None = Field(default=None, strict=True)

    @field_validator("block_id", "parent_block_id", mode="before")
    @classmethod
    def normalize_block_reference(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("ancestor_block_ids", mode="before")
    @classmethod
    def normalize_ancestor_block_ids(cls, value):
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise ValueError("qdrant_point_ancestor_block_id_invalid")
        return [item.strip() for item in value]

    @model_validator(mode="after")
    def validate_ancestor_chain(self):
        block_id = self.block_id.strip() if self.block_id else None
        parent_block_id = (
            self.parent_block_id.strip() if self.parent_block_id else None
        )
        ancestors = [value.strip() for value in self.ancestor_block_ids]
        if any(not value for value in ancestors):
            raise ValueError("qdrant_point_ancestor_block_id_blank")
        if len(ancestors) != len(set(ancestors)):
            raise ValueError("qdrant_point_ancestor_block_id_duplicate")
        if block_id and block_id in ancestors:
            raise ValueError("qdrant_point_ancestor_chain_cycle")
        if self.ancestor_chain_status == "ROOT":
            if not block_id or parent_block_id or ancestors:
                raise ValueError("qdrant_point_root_ancestor_chain_invalid")
        elif self.ancestor_chain_status == "COMPLETE":
            if (
                not block_id
                or not parent_block_id
                or not ancestors
                or ancestors[-1] != parent_block_id
            ):
                raise ValueError("qdrant_point_complete_ancestor_chain_invalid")
        elif self.ancestor_chain_status == "PARTIAL":
            if (
                not block_id
                or not parent_block_id
                or (ancestors and ancestors[-1] != parent_block_id)
            ):
                raise ValueError("qdrant_point_partial_ancestor_chain_invalid")
        return self


class ProjectArtifactChunkMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    document_id: str | None = None
    project_id: str | None = None
    artifact_type: str | None = None
    artifact_id: str | None = None
    artifact_version_id: str | None = None
    source_version: str | int | float | None = None
    source_hash: str | None = None
    normalized_content_hash: str | None = None
    title: str | None = None
    author: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    status: str | None = None
    authority: str | None = None
    version: str | int | float | None = None
    module: str | None = None
    page: str | int | None = None
    section: str | None = None
    component: str | None = None
    product_area: str | None = None
    release_id: str | None = None
    external_source_id: str | None = None
    approval_status: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    effective_from: str | None = None
    visibility: str | None = None
    owner_id: str | None = None
    creator_id: str | None = None
    shared_with: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    requirement_version_ids: list[str] = Field(default_factory=list)
    linked_requirement_version_ids: list[str] = Field(default_factory=list)
    acceptance_criterion_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    test_case_version_id: str | None = None
    test_case_version_ids: list[str] = Field(default_factory=list)
    test_run_id: str | None = None
    linked_test_result_id: str | None = None
    test_case_key: str | None = None
    test_case_type: str | None = None
    test_level: str | None = None
    test_kind: str | None = None
    expected_impact: str | None = None
    priority: str | None = None
    risk: str | None = None
    techniques: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    automation_status: str | None = None
    repository_node_id: str | None = None
    coverage_item_ids: list[str] = Field(default_factory=list)
    data_set_version_ids: list[str] = Field(default_factory=list)
    content_format: str | None = None
    content_type: str | None = None
    source_document_id: str | None = None
    parser_name: str | None = None
    parser_version: str | None = None
    ocr_enabled: bool | None = None
    ocr_language: str | None = None
    page_count: int | None = Field(default=None, strict=True)
    source_block_count: int | None = Field(default=None, strict=True)
    extraction_status: str | None = None
    unprocessed_block_count: int | None = None
    extraction_warning_count: int | None = None
    extraction_warning_codes: list[str] = Field(default_factory=list)
    extraction_method: str | None = None
    source_created_at: str | None = None
    source_updated_at: str | None = None
    summary_scope: str | None = None
    summary_sample_chunk_ids: list[str] = Field(default_factory=list)
    summary_sample_page_numbers: list[int] = Field(default_factory=list)
    summary_sample_char_count: int | None = None
    document_chunk_count: int | None = None
    index_generation: str | None = None
    document_index_contract_version: int | None = Field(default=None, ge=1, strict=True)
    indexing_attempt_id: str | None = None
    indexed_at: str | None = None
    embedding_model: str | None = None
    embedding_input_mode: Literal["TEXT", "TITLE_AND_TEXT"] | None = None
    embedding_input_hash: str | None = None
    chunk_id: str | None = None
    logical_chunk_id: str | None = None
    chunk_hash: str | None = None
    chunk_index: int | None = None
    chunk_type: str | None = None
    structure_types: list[str] = Field(default_factory=list)
    char_count: int | None = None
    word_count: int | None = None
    source_spans: list[ProjectChunkSourceSpan] = Field(default_factory=list)
    page_numbers: list[int] = Field(default_factory=list, strict=True)
    page_start: int | None = Field(default=None, strict=True)
    page_end: int | None = Field(default=None, strict=True)

    @field_validator("page_numbers", mode="before")
    @classmethod
    def validate_page_numbers_are_integers(cls, value):
        if not isinstance(value, list) or any(
            not isinstance(page, int) or isinstance(page, bool) or page < 1
            for page in value
        ):
            raise ValueError("qdrant_point_page_numbers_invalid")
        return value


def validate_qdrant_payload_integrity(payload: BaseModel) -> None:
    text = str(getattr(payload, "text", ""))
    if not text.strip():
        raise ValueError("qdrant_point_text_blank")
    chunk_hash = getattr(payload, "chunk_hash", None)
    if chunk_hash and chunk_hash != hashlib.sha256(text.encode("utf-8")).hexdigest():
        raise ValueError("qdrant_point_chunk_hash_mismatch")
    embedding_input_hash = getattr(payload, "embedding_input_hash", None)
    if embedding_input_hash:
        mode = getattr(payload, "embedding_input_mode", None)
        text_input = text
        titled_input = f"{getattr(payload, 'title', '') or ''} {text}"
        valid_hashes = {
            "TEXT": hashlib.sha256(text_input.encode("utf-8")).hexdigest(),
            "TITLE_AND_TEXT": hashlib.sha256(titled_input.encode("utf-8")).hexdigest(),
        }
        if mode not in valid_hashes:
            if embedding_input_hash not in valid_hashes.values():
                raise ValueError("qdrant_point_embedding_input_hash_mismatch")
        elif embedding_input_hash != valid_hashes[mode]:
            raise ValueError("qdrant_point_embedding_input_hash_mismatch")
    char_count = getattr(payload, "char_count", None)
    if char_count is not None and char_count != len(text):
        raise ValueError("qdrant_point_char_count_mismatch")
    word_count = getattr(payload, "word_count", None)
    if word_count is not None and word_count != len(text.split()):
        raise ValueError("qdrant_point_word_count_mismatch")
    page_numbers = getattr(payload, "page_numbers", []) or []
    if any(page < 1 for page in page_numbers):
        raise ValueError("qdrant_point_page_numbers_invalid")
    if page_numbers and page_numbers != sorted(set(page_numbers)):
        raise ValueError("qdrant_point_page_numbers_invalid")
    page_start = getattr(payload, "page_start", None)
    page_end = getattr(payload, "page_end", None)
    if page_start is not None and page_start < 1:
        raise ValueError("qdrant_point_page_range_invalid")
    if page_end is not None and page_end < 1:
        raise ValueError("qdrant_point_page_range_invalid")
    if page_start is not None and page_end is not None:
        if page_end < page_start:
            raise ValueError("qdrant_point_page_range_invalid")
        if page_numbers and (page_start != page_numbers[0] or page_end != page_numbers[-1]):
            raise ValueError("qdrant_point_page_range_mismatch")
    for span in getattr(payload, "source_spans", []) or []:
        if (span.source_start is None) != (span.source_end is None):
            raise ValueError("qdrant_point_source_range_invalid")
        if span.source_start is not None and (
            span.source_start < 0 or span.source_end < span.source_start
        ):
            raise ValueError("qdrant_point_source_range_invalid")
        if span.chunk_start is None or span.chunk_end is None:
            if span.table_metadata and span.table_metadata.cell_spans:
                raise ValueError("qdrant_point_table_cell_requires_chunk_range")
            continue
        if not 0 <= span.chunk_start <= span.chunk_end <= len(text):
            raise ValueError("qdrant_point_source_span_out_of_range")
        for segment in span.source_segments:
            if not span.chunk_start <= segment.chunk_start < segment.chunk_end <= span.chunk_end:
                raise ValueError("qdrant_point_source_segment_out_of_range")
        if span.table_metadata:
            for cell in span.table_metadata.cell_spans:
                if not span.chunk_start <= cell.chunk_start < cell.chunk_end <= span.chunk_end:
                    raise ValueError("qdrant_point_table_cell_out_of_range")


class ProjectArtifactQdrantPayload(ProjectArtifactChunkMetadata):
    model_config = ConfigDict(extra="allow")

    text: str = Field(min_length=1)
    embedding_input_mode: Literal["TITLE_AND_TEXT"] | None = None

    @model_validator(mode="after")
    def validate_point_content_and_source_ranges(self):
        validate_qdrant_payload_integrity(self)
        return self


class ProjectArtifactChunk(BaseModel):
    point_id: str
    text: str
    metadata: ProjectArtifactChunkMetadata


class ProjectArtifactChunkPage(BaseModel):
    project_id: str
    artifact_version_id: str
    items: list[ProjectArtifactChunk] = Field(default_factory=list)
    next_cursor: str | None = None


class QdrantPointPayload(ProjectArtifactChunkMetadata):
    model_config = ConfigDict(extra="allow")

    text: str = Field(min_length=1)
    embedding_input_mode: Literal["TEXT", "TITLE_AND_TEXT"] | None = None
    char_count: int | None = Field(default=None, ge=0)
    word_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_point_integrity(self):
        validate_qdrant_payload_integrity(self)
        if self.artifact_type in DOCUMENT_INDEXED_ARTIFACT_TYPES:
            required_values = (
                self.document_id,
                self.project_id,
                self.artifact_id,
                self.artifact_version_id,
                self.source_hash,
                self.normalized_content_hash,
                self.parser_name,
                self.index_generation,
                self.document_index_contract_version,
                self.extraction_status,
                self.extraction_method,
                self.embedding_model,
                self.embedding_input_mode,
                self.embedding_input_hash,
                self.chunk_id,
                self.logical_chunk_id,
                self.chunk_hash,
                self.chunk_type,
                self.chunk_index,
            )
            if any(value is None or value == "" for value in required_values):
                raise ValueError("qdrant_document_chunk_metadata_incomplete")
            for digest in (
                self.source_hash,
                self.normalized_content_hash,
                self.chunk_hash,
                self.embedding_input_hash,
            ):
                if len(digest) != 64 or any(
                    character not in "0123456789abcdef" for character in digest
                ):
                    raise ValueError("qdrant_document_digest_invalid")
            if self.index_generation and (
                len(self.index_generation) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in self.index_generation
                )
            ):
                raise ValueError("qdrant_document_index_generation_invalid")
            if self.chunk_type == "summary":
                if (
                    self.chunk_index != -1
                    or not self.summary_sample_chunk_ids
                    or any(not value.strip() for value in self.summary_sample_chunk_ids)
                    or len(set(self.summary_sample_chunk_ids))
                    != len(self.summary_sample_chunk_ids)
                ):
                    raise ValueError("qdrant_document_summary_lineage_missing")
            elif self.chunk_index < 0 or not self.source_spans:
                raise ValueError("qdrant_document_source_spans_missing")
            if self.chunk_type != "summary":
                for span in self.source_spans:
                    if (
                        span.source_start is not None
                        and span.source_end is not None
                        and span.source_start == span.source_end
                        and str(span.content_type or "").casefold()
                        not in {"image", "picture"}
                    ):
                        raise ValueError("qdrant_document_source_range_empty")
        return self

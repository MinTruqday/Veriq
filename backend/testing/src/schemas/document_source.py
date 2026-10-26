from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceLocation(BaseModel):
    page_no: int | None = Field(default=None, ge=1)
    bbox: dict[str, Any] | None = None


class SourceTableMetadata(BaseModel):
    table_id: str | None = None
    row_count: int | None = Field(default=None, ge=0)
    column_count: int | None = Field(default=None, ge=0)
    column_headers: list[str] = Field(default_factory=list)
    metadata_source: str | None = None


class SourceImageMetadata(BaseModel):
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


class SourceBlock(BaseModel):
    block_id: str | None = None
    parent_block_id: str | None = None
    text: str = ""
    type: str
    level: int | None = None
    page_no: int | None = Field(default=None, ge=1)
    locations: list[SourceLocation] = Field(default_factory=list)
    extraction_status: Literal["EXTRACTED", "NO_TEXT_EXTRACTED"]
    table_metadata: SourceTableMetadata | None = None
    image_metadata: SourceImageMetadata | None = None


class DocumentConversionResult(BaseModel):
    markdown: str = ""
    structure: list[SourceBlock] = Field(default_factory=list)
    page_count: int | None = Field(default=None, ge=1)
    unprocessed_blocks: list[dict[str, Any]] = Field(default_factory=list)
    extraction_warnings: list[dict[str, Any]] = Field(default_factory=list)
    parser: str | None = None
    parser_version: str | None = None
    ocr_enabled: bool = False
    ocr_language: str | None = None
    source_hash: str | None = None

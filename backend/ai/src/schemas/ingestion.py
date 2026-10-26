from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class IngestRequest(BaseModel):
    document_id: str = Field(
        description="Document identifier to index"
    )
    requester_id: Optional[str] = None
    is_admin: bool = False


class IngestResponse(BaseModel):
    document_id: str
    status: str
    chunks_count: int
    summary_generated: bool = False
    extraction_method: str = "local"
    quarantined_chunks: list[dict[str, Any]] = Field(default_factory=list)
    failed_chunks: list[dict[str, Any]] = Field(default_factory=list)
    unprocessed_blocks: list[dict[str, Any]] = Field(default_factory=list)
    extraction_warnings: list[dict[str, Any]] = Field(default_factory=list)
    index_cleanup_pending: list[str] = Field(default_factory=list)


class AttachmentConversionRequest(BaseModel):
    data: str = Field(min_length=1, max_length=35_000_000)
    filename: str = Field(default="attachment.pdf", min_length=1, max_length=255)
    ocr_language: str | None = Field(default=None, min_length=2, max_length=32)
    page_range: tuple[int, int] | None = None
    document_id: str | None = Field(default=None, min_length=1, max_length=200)
    project_id: str | None = Field(default=None, min_length=1, max_length=200)
    owner_id: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_page_range(self):
        if self.page_range and (
            self.page_range[0] < 1 or self.page_range[1] < self.page_range[0]
        ):
            raise ValueError("page_range_must_be_one_based_and_ordered")
        context_values = (self.document_id, self.project_id, self.owner_id)
        if any(context_values) and not all(context_values):
            raise ValueError("document_checkpoint_context_must_be_complete")
        if self.page_range is not None and self.document_id is not None:
            raise ValueError("page_range_and_document_checkpoint_context_are_mutually_exclusive")
        return self


class ConversionCheckpointCleanupRequest(BaseModel):
    document_id: str = Field(min_length=1, max_length=200)
    project_id: str = Field(min_length=1, max_length=200)
    owner_id: str = Field(min_length=1, max_length=200)
    source_hash: str = Field(pattern=r"^[a-fA-F0-9]{64}$")

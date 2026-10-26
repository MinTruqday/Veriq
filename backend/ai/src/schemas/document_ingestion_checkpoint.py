from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentIngestionPageCheckpoint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document_id: str = Field(min_length=1)
    project_id: str = ""
    owner_id: str = ""
    source_hash: str = Field(min_length=1)
    parser_name: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    parser_contract_version: int = Field(ge=1)
    ocr_language: str = ""
    page_no: int = Field(ge=1)
    page_count: int = Field(ge=1)
    markdown: str = ""
    structure: list[dict] = Field(default_factory=list)
    unprocessed_blocks: list[dict] = Field(default_factory=list)
    extraction_warnings: list[dict] = Field(default_factory=list)
    ocr_enabled: bool = False
    created_at: datetime
    expires_at: datetime

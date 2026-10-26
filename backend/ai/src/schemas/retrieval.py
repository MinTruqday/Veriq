from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ArtifactFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: Optional[str] = None
    artifact_type: Optional[str] = None
    artifact_id: Optional[str] = None
    artifact_version_id: Optional[str] = None
    module: Optional[str] = None
    status: Optional[str] = None
    authority: Optional[List[str]] = None
    source_type: Optional[str] = None
    source_version: Optional[str] = None
    content_type: Optional[str] = None


class RetrieveRequest(BaseModel):
    query: str = Field(
        min_length=1, max_length=10000
    )
    document_ids: Optional[List[str]] = None
    k: int = Field(
        default=5,
        ge=1,
        le=100,
    )
    query_vector_override: Optional[List[float]] = None
    requester_id: Optional[str] = None
    is_admin: bool = False
    metadata_filters: ArtifactFilters = Field(default_factory=ArtifactFilters)


class CrossDocRetrieveRequest(BaseModel):
    question: str = Field(
        min_length=1, max_length=10000
    )
    document_ids: List[str]
    k: int = Field(
        default=5,
        ge=1,
        le=100,
    )
    requester_id: Optional[str] = None
    is_admin: bool = False
    metadata_filters: ArtifactFilters = Field(default_factory=ArtifactFilters)


class RetrievedDocument(BaseModel):
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0


class CitationItem(BaseModel):
    point_id: str = ""
    chunk_id: str = ""
    document_id: str = ""
    title: str = ""
    chunk_index: Any = ""
    label: str = ""
    artifact_type: str = ""
    artifact_id: str = ""
    artifact_version_id: str = ""
    source_version: str | int | float | None = None
    page_numbers: List[int] = Field(default_factory=list)
    source_spans: List[Dict[str, Any]] = Field(default_factory=list)


class RetrieveResponse(BaseModel):
    documents: List[RetrievedDocument]
    citations: List[CitationItem] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)

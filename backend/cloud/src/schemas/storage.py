import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ShareAccess(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    role: Literal["editor"]


class ProtectedShareCreate(BaseModel):
    item_id: str = Field(min_length=1, max_length=128)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    expires_in_hours: int = Field(default=24, ge=1, le=720)


class StorageItemBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    parent_id: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    tags: List[str] = Field(default_factory=list, max_length=50)
    shared_with: List[ShareAccess] = Field(default_factory=list)
    is_shortcut: bool = False
    target_id: Optional[str] = None
    is_duplicate: Optional[bool] = False
    duplicate_of: Optional[str] = None
    environment_ready: Optional[bool] = False
    ai_processed: Optional[bool] = False
    entities: Optional[dict] = Field(default_factory=dict)
    broken_links: Optional[List[str]] = Field(default_factory=list)
    is_locked: bool = False
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None


class StorageItemCreate(StorageItemBase):
    is_folder: bool = False
    size: int = Field(default=0, ge=0, le=10 * 1024 * 1024 * 1024)
    mime_type: Optional[str] = None
    url: Optional[str] = None


class StorageItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    parent_id: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    tags: Optional[List[str]] = None
    is_trashed: Optional[bool] = None
    is_starred: Optional[bool] = None
    is_public: Optional[bool] = None
    share_token: Optional[str] = None
    shared_with: Optional[List[ShareAccess]] = None
    is_duplicate: Optional[bool] = None
    duplicate_of: Optional[str] = None
    environment_ready: Optional[bool] = None
    ai_processed: Optional[bool] = None
    entities: Optional[dict] = None
    broken_links: Optional[List[str]] = None

    is_locked: Optional[bool] = None
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None


class BulkActionRequest(BaseModel):
    action: str = Field(pattern=r"^(delete|move|copy)$")
    item_ids: List[str] = Field(min_length=1, max_length=100)
    target_parent_id: Optional[str] = None


class FileRequestCreate(BaseModel):
    target_folder_id: str = Field(min_length=1, max_length=128)
    password: Optional[str] = Field(default=None, max_length=128)
    expires_in_hours: int = Field(default=168, ge=1, le=720)
    description: Optional[str] = None


class FileRequestResponse(BaseModel):
    token: str
    target_folder_id: str
    owner_id: str
    description: Optional[str]
    expires_at: datetime
    is_protected: bool


class ItemActivityResponse(BaseModel):
    id: str
    item_id: str
    actor_id: str
    action: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime


class FileVersion(BaseModel):
    version_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    size: int = Field(ge=0, le=10 * 1024 * 1024 * 1024)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StorageItemInDB(StorageItemBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    owner_id: str
    is_folder: bool = False
    size: int = 0
    mime_type: Optional[str] = None
    url: Optional[str] = None
    is_trashed: bool = False
    is_starred: bool = False
    is_public: bool = False
    share_token: Optional[str] = None
    versions: List[FileVersion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StorageItemResponse(StorageItemBase):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str = Field(alias="_id")
    owner_id: str
    is_folder: bool
    size: int
    mime_type: Optional[str]
    url: Optional[str]
    color: Optional[str] = None
    is_trashed: bool
    is_starred: bool
    is_public: bool = False
    share_token: Optional[str] = None
    versions: List[FileVersion] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None


class StarredUpdateRequest(BaseModel):
    is_starred: bool


class TagColorUpdateRequest(BaseModel):
    tags: Optional[List[str]] = None
    color: Optional[str] = None


class InternalShareRequest(BaseModel):
    email: str
    role: Literal["editor"]


class CategoryBreakdown(BaseModel):
    count: int = 0
    size: int = 0
    percentage: float = 0.0


class QuotaAnalyticsResponse(BaseModel):
    total_quota_bytes: int
    used_quota_bytes: int
    free_quota_bytes: int
    usage_percentage: float
    total_files_count: int
    total_folders_count: int
    trashed_files_count: int
    trashed_bytes: int
    breakdown: dict


class FileVersionResponse(BaseModel):
    version_id: str
    url: str
    size: int
    created_at: datetime
    is_active: bool = False

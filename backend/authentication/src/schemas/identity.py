import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class KYC(str, Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class Creator(str, Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class SystemRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    system_role: SystemRole = SystemRole.USER
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    social_links: Optional[Dict[str, str]] = Field(default_factory=dict)
    pinned_documents: List[str] = Field(default_factory=list)
    bookmarks: List[str] = Field(default_factory=list)
    is_shadowbanned: bool = False
    permissions: List[str] = Field(default_factory=list)
    donation_link: Optional[str] = None
    kyc_status: KYC = KYC.NONE
    creator_status: Creator = Creator.NONE
    is_verified: bool = False
    storage_limit: int = Field(
        default=21474836480,
        le=107374182400,
    )

    @field_validator("kyc_status", "creator_status", mode="before")
    @classmethod
    def validate_enum_case(cls, v: Any):
        if isinstance(v, str):
            return v.upper()
        return v

    tos_accepted_at: Optional[datetime] = None
    welcome_message: Optional[str] = None
    blocked_users: List[str] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "mod_notifs": True,
            "auto_refresh": False,
            "auto_save": True,
            "default_visibility": "public",
        }
    )


class UserCreate(UserBase):
    password: str = Field(min_length=12, max_length=128)
    agreed_to_terms: bool

    @field_validator("agreed_to_terms")
    @classmethod
    def validate_terms(cls, value: bool):
        if not value:
            raise ValueError("Điều khoản sử dụng phải được chấp thuận")
        return value


class UserInDB(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    last_read_date: Optional[datetime] = None
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    is_kyc_verified: bool = False
    passkeys: List[Dict[str, Any]] = Field(default_factory=list)
    last_password_change: Optional[datetime] = None
    last_bank_update: Optional[datetime] = None


class UserResponse(UserBase):
    email: str
    id: str = Field(alias="_id")
    created_at: datetime
    has_passkey: bool = False


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_url: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    locale: Optional[str] = Field(default=None, min_length=2, max_length=20)
    timezone: Optional[str] = Field(default=None, min_length=2, max_length=100)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class EmailChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_email: EmailStr


class AccountDeactivate(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    confirmation: str = Field(pattern="^DEACTIVATE$")


class SettingsUpdate(BaseModel):
    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    privacy_mode: Optional[bool] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class VerifyCodeRequest(BaseModel):
    token: str = Field(min_length=6, max_length=128)


class EmailVerificationInput(BaseModel):
    token: str = Field(min_length=16, max_length=256)


class NotificationSettingsUpdate(BaseModel):
    enable_comment_notifications: bool = True
    enable_mention_notifications: bool = True
    enable_system_notifications: bool = True
    enable_email_digest: bool = False


class UpdateStatusRequest(BaseModel):
    is_active: bool


class ModerationActionRequest(BaseModel):
    reason: str
    duration_hours: Optional[int] = None


class NoteRequest(BaseModel):
    note: str


class PasskeyRequest(BaseModel):
    email: EmailStr


class PasskeyFinishRequest(BaseModel):
    email: EmailStr
    credential: dict

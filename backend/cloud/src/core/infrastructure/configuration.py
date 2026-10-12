import os
from typing import Optional

class Settings:
    PROJECT_NAME: str = os.environ["PROJECT_NAME"]
    VERSION: str = os.environ["VERSION"]
    INTERNAL_API_URL: str = os.environ["INTERNAL_API_URL"]
    SECRET_KEY: str = os.environ["SECRET_KEY"]
    CORS_ALLOWED_ORIGINS: str = os.environ["CORS_ALLOWED_ORIGINS"]
    MONGODB_URI: str = os.environ["MONGODB_URI"]
    REDIS_URI: str = os.environ["REDIS_URI"]
    OBJECT_STORAGE_ENDPOINT: str = os.environ["OBJECT_STORAGE_ENDPOINT"]
    OBJECT_STORAGE_ACCESS_KEY: str = os.environ["OBJECT_STORAGE_ACCESS_KEY"]
    OBJECT_STORAGE_SECRET_KEY: str = os.environ["OBJECT_STORAGE_SECRET_KEY"]
    OBJECT_STORAGE_PRIVATE_BUCKET: str = os.environ["OBJECT_STORAGE_PRIVATE_BUCKET"]
    OBJECT_STORAGE_PUBLIC_BUCKET: str = os.environ["OBJECT_STORAGE_PUBLIC_BUCKET"]
    OBJECT_STORAGE_LEGACY_BUCKET: str = os.environ["OBJECT_STORAGE_LEGACY_BUCKET"]
    OBJECT_STORAGE_REGION: str = os.environ["OBJECT_STORAGE_REGION"]
    OBJECT_STORAGE_PUBLIC_URL: Optional[str] = os.environ["OBJECT_STORAGE_PUBLIC_URL"]
    PLATFORM_SYSTEM_ID: str = os.environ["PLATFORM_SYSTEM_ID"]
    AUTHENTICATION_URL: str = os.environ["AUTHENTICATION_URL"]
    CLOUD_DB_NAME: str = os.environ["CLOUD_DB_NAME"]
    COMPRESSIBLE_TEXT_EXTENSIONS: str = os.environ["COMPRESSIBLE_TEXT_EXTENSIONS"]
    MAX_UPLOAD_SIZE_BYTES: int = int(os.environ["MAX_UPLOAD_SIZE_BYTES"])
    MIN_UPLOAD_SIZE_BYTES: int = int(os.environ["MIN_UPLOAD_SIZE_BYTES"])


settings = Settings()

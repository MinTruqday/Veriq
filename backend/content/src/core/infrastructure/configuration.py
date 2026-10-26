import os


class Settings:
    PROJECT_NAME: str = os.environ["PROJECT_NAME"]
    VERSION: str = os.environ["VERSION"]
    INTERNAL_API_URL: str = os.environ["INTERNAL_API_URL"]
    SECRET_KEY: str = os.environ["SECRET_KEY"]
    CORS_ALLOWED_ORIGINS: str = os.environ["CORS_ALLOWED_ORIGINS"]
    MONGODB_URI: str = os.environ["MONGODB_URI"]
    REDIS_URI: str = os.environ["REDIS_URI"]
    RABBITMQ_URI: str = os.environ["RABBITMQ_URI"]
    PLATFORM_SYSTEM_ID: str = os.environ["PLATFORM_SYSTEM_ID"]
    AUTHENTICATION_URL: str = os.environ["AUTHENTICATION_URL"]
    AI_URL: str = os.environ["AI_URL"]
    NOTIFICATION_URL: str = os.environ["NOTIFICATION_URL"]
    CONTENT_DB_NAME: str = os.environ["CONTENT_DB_NAME"]
    OBJECT_STORAGE_ENDPOINT: str = os.environ["OBJECT_STORAGE_ENDPOINT"]
    OBJECT_STORAGE_PUBLIC_URL: str = os.environ["OBJECT_STORAGE_PUBLIC_URL"]
    DOCUMENT_INDEXING_LEASE_SECONDS: int = int(
        os.getenv("DOCUMENT_INDEXING_LEASE_SECONDS", "180")
    )


settings = Settings()
if settings.DOCUMENT_INDEXING_LEASE_SECONDS < 2:
    raise ValueError("DOCUMENT_INDEXING_LEASE_SECONDS must be at least 2")

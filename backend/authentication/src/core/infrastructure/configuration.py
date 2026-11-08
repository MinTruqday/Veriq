import os
from typing import Optional

class Settings:
    VERSION: str = os.environ["VERSION"]
    SECRET_KEY: str = os.environ["SECRET_KEY"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"])
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ["REFRESH_TOKEN_EXPIRE_DAYS"])
    CORS_ALLOWED_ORIGINS: str = os.environ["CORS_ALLOWED_ORIGINS"]
    MONGODB_URI: str = os.environ["MONGODB_URI"]
    REDIS_URI: str = os.environ["REDIS_URI"]
    PASSKEY_RP_ID: str = os.environ["PASSKEY_RP_ID"]
    PASSKEY_RP_NAME: str = os.environ["PASSKEY_RP_NAME"]
    PASSKEY_ALLOWED_ORIGINS: str = os.environ["PASSKEY_ALLOWED_ORIGINS"]
    SMTP_HOST: str = os.environ["SMTP_HOST"]
    SMTP_PORT: int = int(os.environ["SMTP_PORT"])
    SMTP_USER: Optional[str] = os.environ["SMTP_USER"]
    SMTP_PASS: Optional[str] = os.environ["SMTP_PASS"]
    SENDER_EMAIL: Optional[str] = os.environ["SENDER_EMAIL"]
    SENDER_NAME: Optional[str] = os.environ["SENDER_NAME"]
    AUTHENTICATION_DB_NAME: str = os.environ["AUTHENTICATION_DB_NAME"]
    AI_INTERNAL_URL: str = os.environ["AI_INTERNAL_URL"]
    AUTHENTICATION_INTERNAL_URL: str = os.environ["AUTHENTICATION_INTERNAL_URL"]
    CLOUD_INTERNAL_URL: str = os.environ["CLOUD_INTERNAL_URL"]
    CONTENT_INTERNAL_URL: str = os.environ["CONTENT_INTERNAL_URL"]
    TESTING_INTERNAL_URL: str = os.environ["TESTING_INTERNAL_URL"]
    WORKER_INTERNAL_URL: str = os.environ["WORKER_INTERNAL_URL"]
    LLM_MODEL: str = os.environ["LLM_MODEL"]
    EMBEDDING_MODEL: str = os.environ["EMBEDDING_MODEL"]
    RERANKER_MODEL: str = os.environ["RERANKER_MODEL"]

settings = Settings()

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
    RABBITMQ_URI: str = os.environ["RABBITMQ_URI"]
    QDRANT_URL: str = os.environ["QDRANT_URL"]
    NEO4J_URI: str = os.environ["NEO4J_URI"]
    NEO4J_USER: str = os.environ["NEO4J_USER"]
    NEO4J_PASSWORD: str = os.environ["NEO4J_PASSWORD"]
    EMBEDDING_MODEL: str = os.environ["EMBEDDING_MODEL"]
    DOCKER_HOST: str = os.environ["DOCKER_HOST"]
    OBJECT_STORAGE_ENDPOINT: str = os.environ["OBJECT_STORAGE_ENDPOINT"]
    OBJECT_STORAGE_ACCESS_KEY: str = os.environ["OBJECT_STORAGE_ACCESS_KEY"]
    OBJECT_STORAGE_SECRET_KEY: str = os.environ["OBJECT_STORAGE_SECRET_KEY"]
    OBJECT_STORAGE_PRIVATE_BUCKET: str = os.environ["OBJECT_STORAGE_PRIVATE_BUCKET"]
    OBJECT_STORAGE_PUBLIC_BUCKET: str = os.environ["OBJECT_STORAGE_PUBLIC_BUCKET"]
    OBJECT_STORAGE_REGION: str = os.environ["OBJECT_STORAGE_REGION"]
    OBJECT_STORAGE_PUBLIC_URL: Optional[str] = os.environ["OBJECT_STORAGE_PUBLIC_URL"]
    HF_TOKEN: str = os.environ["HF_TOKEN"]
    HF_INFERENCE_URL: str = os.environ["HF_INFERENCE_URL"]
    PRIMARY_MODEL_URL: str = os.environ["PRIMARY_MODEL_URL"]
    PRIMARY_MODEL_HEALTH_URL: str = os.environ["PRIMARY_MODEL_HEALTH_URL"]
    LLM_MODEL: str = os.environ["LLM_MODEL"]
    MODEL_TIMEOUT_SECONDS: int = int(os.environ["MODEL_TIMEOUT_SECONDS"])
    RERANKER_MODEL: str = os.environ["RERANKER_MODEL"]
    NLI_MODEL_NAME: str = os.environ["NLI_MODEL_NAME"]
    PLATFORM_SYSTEM_ID: str = os.environ["PLATFORM_SYSTEM_ID"]
    AI_DB_NAME: str = os.environ["AI_DB_NAME"]
    AUTHENTICATION_URL: str = os.environ["AUTHENTICATION_URL"]
    CONTENT_URL: str = os.environ["CONTENT_URL"]
    DOCUMENT_INGESTION_CHECKPOINT_TTL_DAYS: int = int(
        os.getenv("DOCUMENT_INGESTION_CHECKPOINT_TTL_DAYS", "7")
    )
    DOCUMENT_SUMMARY_INPUT_CHAR_LIMIT: int = int(
        os.getenv("DOCUMENT_SUMMARY_INPUT_CHAR_LIMIT", "15000")
    )
    DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE: int = int(
        os.getenv("DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE", "4")
    )
    DOCUMENT_OCR_LANGUAGE: str = os.getenv("DOCUMENT_OCR_LANGUAGE", "iso:vi").strip()
    DOCUMENT_INDEXING_LEASE_SECONDS: int = int(
        os.getenv("DOCUMENT_INDEXING_LEASE_SECONDS", "180")
    )
    DOCUMENT_INDEXING_LEASE_HEARTBEAT_SECONDS: int = int(
        os.getenv("DOCUMENT_INDEXING_LEASE_HEARTBEAT_SECONDS", "45")
    )


settings = Settings()
if settings.DOCUMENT_INGESTION_CHECKPOINT_TTL_DAYS < 1:
    raise ValueError("DOCUMENT_INGESTION_CHECKPOINT_TTL_DAYS must be positive")
if settings.DOCUMENT_SUMMARY_INPUT_CHAR_LIMIT < 2000:
    raise ValueError("DOCUMENT_SUMMARY_INPUT_CHAR_LIMIT must be at least 2000")
if not 1 <= settings.DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE <= 32:
    raise ValueError("DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE must be between 1 and 32")
if not settings.DOCUMENT_OCR_LANGUAGE:
    raise ValueError("DOCUMENT_OCR_LANGUAGE must not be empty")
if settings.DOCUMENT_INDEXING_LEASE_SECONDS < 2:
    raise ValueError("DOCUMENT_INDEXING_LEASE_SECONDS must be at least 2")
if not (
    0
    < settings.DOCUMENT_INDEXING_LEASE_HEARTBEAT_SECONDS
    < settings.DOCUMENT_INDEXING_LEASE_SECONDS
):
    raise ValueError(
        "DOCUMENT_INDEXING_LEASE_HEARTBEAT_SECONDS must be positive and shorter than the lease"
    )

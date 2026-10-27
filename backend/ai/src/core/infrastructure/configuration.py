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
    FALLBACK_MODEL_URL: str = os.getenv("FALLBACK_MODEL_URL", "").strip()
    FALLBACK_MODEL_HEALTH_URL: str = os.getenv("FALLBACK_MODEL_HEALTH_URL", "").strip()
    FALLBACK_LLM_MODEL: str = os.getenv("FALLBACK_LLM_MODEL", "").strip()
    FALLBACK_MODEL_TOKEN: str = os.getenv("FALLBACK_MODEL_TOKEN", "").strip()
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
    DOCUMENT_INGESTION_MAX_DELIVERY_ATTEMPTS: int = int(
        os.getenv("DOCUMENT_INGESTION_MAX_DELIVERY_ATTEMPTS", "3")
    )
    DOCUMENT_SUMMARY_INPUT_CHAR_LIMIT: int = int(
        os.getenv("DOCUMENT_SUMMARY_INPUT_CHAR_LIMIT", "15000")
    )
    DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE: int = int(
        os.getenv("DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE", "4")
    )
    DOCUMENT_MAX_INGESTION_DIAGNOSTIC_DETAILS: int = int(
        os.getenv("DOCUMENT_MAX_INGESTION_DIAGNOSTIC_DETAILS", "100")
    )
    DOCUMENT_OCR_LANGUAGE: str = os.getenv("DOCUMENT_OCR_LANGUAGE", "iso:vi").strip()
    DOCUMENT_OCR_FALLBACK_MIN_CONFIDENCE: float = float(
        os.getenv("DOCUMENT_OCR_FALLBACK_MIN_CONFIDENCE", "0.5")
    )
    DOCUMENT_INDEX_CONTRACT_VERSION: int = int(
        os.getenv("DOCUMENT_INDEX_CONTRACT_VERSION", "2")
    )
    DOCUMENT_INDEXING_LEASE_SECONDS: int = int(
        os.getenv("DOCUMENT_INDEXING_LEASE_SECONDS", "180")
    )
    DOCUMENT_INDEXING_LEASE_HEARTBEAT_SECONDS: int = int(
        os.getenv("DOCUMENT_INDEXING_LEASE_HEARTBEAT_SECONDS", "45")
    )
    AI_AGENT_MAX_STEPS: int = int(os.getenv("AI_AGENT_MAX_STEPS", "8"))
    AI_AGENT_MAX_TOOL_CALLS: int = int(os.getenv("AI_AGENT_MAX_TOOL_CALLS", "6"))
    AI_AGENT_MAX_TOOL_ERRORS: int = int(os.getenv("AI_AGENT_MAX_TOOL_ERRORS", "2"))
    AI_AUTOMATION_MAX_RETRIES: int = int(os.getenv("AI_AUTOMATION_MAX_RETRIES", "2"))
    AI_AUTOMATION_RUN_TIMEOUT_SECONDS: int = int(
        os.getenv("AI_AUTOMATION_RUN_TIMEOUT_SECONDS", "900")
    )
    AI_AUTOMATION_TASK_TIMEOUT_SECONDS: int = int(
        os.getenv("AI_AUTOMATION_TASK_TIMEOUT_SECONDS", "840")
    )
    AI_MESSAGE_ACK_TIMEOUT_SECONDS: int = int(
        os.getenv("AI_MESSAGE_ACK_TIMEOUT_SECONDS", "960")
    )
    AI_AGENT_MAX_EVIDENCE_ITEMS: int = int(
        os.getenv("AI_AGENT_MAX_EVIDENCE_ITEMS", "100")
    )
    AI_QUEUE_RETRY_BASE_SECONDS: int = int(
        os.getenv("AI_QUEUE_RETRY_BASE_SECONDS", "15")
    )
    AI_QUEUE_RETRY_MAX_SECONDS: int = int(
        os.getenv("AI_QUEUE_RETRY_MAX_SECONDS", "300")
    )
    AI_QUEUE_RETRY_SCAN_SECONDS: int = int(
        os.getenv("AI_QUEUE_RETRY_SCAN_SECONDS", "5")
    )
    AI_AUTOMATION_RECOVERY_BATCH_SIZE: int = int(
        os.getenv("AI_AUTOMATION_RECOVERY_BATCH_SIZE", "100")
    )
    AI_DEAD_LETTER_MAX_REDRIVES: int = int(
        os.getenv("AI_DEAD_LETTER_MAX_REDRIVES", "3")
    )
    AI_TRACE_ENABLED: bool = os.getenv("AI_TRACE_ENABLED", "true").strip().lower() == "true"
    AI_TRACE_ENDPOINT: str = os.getenv(
        "AI_TRACE_ENDPOINT", "http://phoenix:6006/v1/traces"
    ).strip()
    AI_TRACE_PROJECT: str = os.getenv("AI_TRACE_PROJECT", "veriq-ai").strip()


settings = Settings()
fallback_configuration = (
    bool(settings.FALLBACK_MODEL_URL),
    bool(settings.FALLBACK_MODEL_HEALTH_URL),
    bool(settings.FALLBACK_LLM_MODEL),
)
if any(fallback_configuration) and not all(fallback_configuration):
    raise ValueError(
        "FALLBACK_MODEL_URL, FALLBACK_MODEL_HEALTH_URL, and FALLBACK_LLM_MODEL must be configured together"
    )
if settings.DOCUMENT_INGESTION_CHECKPOINT_TTL_DAYS < 1:
    raise ValueError("DOCUMENT_INGESTION_CHECKPOINT_TTL_DAYS must be positive")
if settings.DOCUMENT_INGESTION_MAX_DELIVERY_ATTEMPTS < 1:
    raise ValueError("DOCUMENT_INGESTION_MAX_DELIVERY_ATTEMPTS must be positive")
if settings.DOCUMENT_SUMMARY_INPUT_CHAR_LIMIT < 2000:
    raise ValueError("DOCUMENT_SUMMARY_INPUT_CHAR_LIMIT must be at least 2000")
if not 1 <= settings.DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE <= 32:
    raise ValueError("DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE must be between 1 and 32")
if not 1 <= settings.DOCUMENT_MAX_INGESTION_DIAGNOSTIC_DETAILS <= 10000:
    raise ValueError("DOCUMENT_MAX_INGESTION_DIAGNOSTIC_DETAILS must be between 1 and 10000")
if not settings.DOCUMENT_OCR_LANGUAGE:
    raise ValueError("DOCUMENT_OCR_LANGUAGE must not be empty")
if not 0 <= settings.DOCUMENT_OCR_FALLBACK_MIN_CONFIDENCE <= 1:
    raise ValueError("DOCUMENT_OCR_FALLBACK_MIN_CONFIDENCE must be between 0 and 1")
if settings.DOCUMENT_INDEX_CONTRACT_VERSION < 1:
    raise ValueError("DOCUMENT_INDEX_CONTRACT_VERSION must be positive")
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
if settings.AI_AGENT_MAX_STEPS < 1:
    raise ValueError("AI_AGENT_MAX_STEPS must be positive")
if settings.AI_AGENT_MAX_TOOL_CALLS < 1:
    raise ValueError("AI_AGENT_MAX_TOOL_CALLS must be positive")
if settings.AI_AGENT_MAX_TOOL_ERRORS < 0:
    raise ValueError("AI_AGENT_MAX_TOOL_ERRORS must not be negative")
if settings.AI_AUTOMATION_MAX_RETRIES < 0:
    raise ValueError("AI_AUTOMATION_MAX_RETRIES must not be negative")
if settings.AI_AUTOMATION_TASK_TIMEOUT_SECONDS <= 0:
    raise ValueError("AI_AUTOMATION_TASK_TIMEOUT_SECONDS must be positive")
if settings.AI_AUTOMATION_RUN_TIMEOUT_SECONDS <= settings.AI_AUTOMATION_TASK_TIMEOUT_SECONDS:
    raise ValueError("AI_AUTOMATION_RUN_TIMEOUT_SECONDS must exceed task timeout")
if settings.AI_MESSAGE_ACK_TIMEOUT_SECONDS <= settings.AI_AUTOMATION_RUN_TIMEOUT_SECONDS:
    raise ValueError("AI_MESSAGE_ACK_TIMEOUT_SECONDS must exceed run timeout")
if settings.AI_AGENT_MAX_EVIDENCE_ITEMS < 1:
    raise ValueError("AI_AGENT_MAX_EVIDENCE_ITEMS must be positive")
if settings.AI_QUEUE_RETRY_BASE_SECONDS < 1:
    raise ValueError("AI_QUEUE_RETRY_BASE_SECONDS must be positive")
if settings.AI_QUEUE_RETRY_MAX_SECONDS < settings.AI_QUEUE_RETRY_BASE_SECONDS:
    raise ValueError("AI_QUEUE_RETRY_MAX_SECONDS must be at least the base delay")
if settings.AI_QUEUE_RETRY_SCAN_SECONDS < 1:
    raise ValueError("AI_QUEUE_RETRY_SCAN_SECONDS must be positive")
if not 1 <= settings.AI_AUTOMATION_RECOVERY_BATCH_SIZE <= 1000:
    raise ValueError("AI_AUTOMATION_RECOVERY_BATCH_SIZE must be between 1 and 1000")
if settings.AI_DEAD_LETTER_MAX_REDRIVES < 1:
    raise ValueError("AI_DEAD_LETTER_MAX_REDRIVES must be positive")
if settings.AI_TRACE_ENABLED and (
    not settings.AI_TRACE_ENDPOINT.startswith(("http://", "https://"))
    or not settings.AI_TRACE_PROJECT
):
    raise ValueError("AI trace endpoint and project must be valid when tracing is enabled")

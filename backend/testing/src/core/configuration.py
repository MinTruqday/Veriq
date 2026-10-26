import os


def _positive_int_environment(name: str, default: str) -> int:
    value = int(os.environ.get(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


class Settings:
    PROJECT_NAME: str = os.environ["PROJECT_NAME"]
    VERSION: str = os.environ["VERSION"]
    SECRET_KEY: str = os.environ["SECRET_KEY"]
    CORS_ALLOWED_ORIGINS: str = os.environ["CORS_ALLOWED_ORIGINS"]
    MONGODB_URI: str = os.environ["MONGODB_URI"]
    TESTING_DB_NAME: str = os.environ["TESTING_DB_NAME"]
    AUTHENTICATION_URL: str = os.environ["AUTHENTICATION_URL"]
    AI_URL: str = os.environ["AI_URL"]
    CONTENT_URL: str = os.environ["CONTENT_URL"]
    WORKER_URL: str = os.environ["WORKER_URL"]
    CLOUD_URL: str = os.environ["CLOUD_URL"]
    MAX_UPLOAD_SIZE_BYTES: int = int(os.environ["MAX_UPLOAD_SIZE_BYTES"])
    DOCUMENT_PARSE_LEASE_SECONDS: int = _positive_int_environment(
        "DOCUMENT_PARSE_LEASE_SECONDS", "900"
    )
    DOCUMENT_PARSE_TIMEOUT_SECONDS: int = _positive_int_environment(
        "DOCUMENT_PARSE_TIMEOUT_SECONDS", "1800"
    )
    REQUIREMENT_DOCUMENT_PARSE_POLL_SECONDS: int = _positive_int_environment(
        "REQUIREMENT_DOCUMENT_PARSE_POLL_SECONDS", "3"
    )
    REQUIREMENT_DUPLICATE_SCAN_MAX_ITEMS: int = _positive_int_environment(
        "REQUIREMENT_DUPLICATE_SCAN_MAX_ITEMS", "500"
    )
    REQUIREMENT_DUPLICATE_SCAN_MAX_CRITERIA: int = _positive_int_environment(
        "REQUIREMENT_DUPLICATE_SCAN_MAX_CRITERIA", "10000"
    )
    MAINTENANCE_PROPOSAL_APPLY_LEASE_SECONDS: int = _positive_int_environment(
        "MAINTENANCE_PROPOSAL_APPLY_LEASE_SECONDS", "900"
    )
settings = Settings()

import os


class Settings:
    PROJECT_NAME: str = os.environ["PROJECT_NAME"]
    VERSION: str = os.environ["VERSION"]
    SECRET_KEY: str = os.environ["SECRET_KEY"]
    MONGODB_URI: str = os.environ["MONGODB_URI"]
    RABBITMQ_URI: str = os.environ["RABBITMQ_URI"]
    WORKER_DB_NAME: str = os.environ["WORKER_DB_NAME"]
    WORKER_QUEUE_NAME: str = os.environ["WORKER_QUEUE_NAME"]
    TESTING_URL: str = os.environ["TESTING_URL"].rstrip("/")
    WORKER_OUTBOX_POLL_SECONDS: float = float(os.getenv("WORKER_OUTBOX_POLL_SECONDS", "0.5"))
    WORKER_OUTBOX_LEASE_SECONDS: int = int(os.getenv("WORKER_OUTBOX_LEASE_SECONDS", "30"))
    WORKER_OUTBOX_MAX_BACKOFF_SECONDS: int = int(
        os.getenv("WORKER_OUTBOX_MAX_BACKOFF_SECONDS", "60")
    )
    WORKER_OUTBOX_RETENTION_DAYS: int = int(os.getenv("WORKER_OUTBOX_RETENTION_DAYS", "30"))
    WORKER_EXECUTION_LEASE_SECONDS: int = int(os.getenv("WORKER_EXECUTION_LEASE_SECONDS", "1800"))
    WORKER_EXECUTION_HEARTBEAT_SECONDS: int = int(os.getenv("WORKER_EXECUTION_HEARTBEAT_SECONDS", "30"))
    WORKER_EXECUTION_RECOVERY_POLL_SECONDS: float = float(
        os.getenv("WORKER_EXECUTION_RECOVERY_POLL_SECONDS", "5")
    )


settings = Settings()

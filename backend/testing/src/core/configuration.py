import os

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


settings = Settings()

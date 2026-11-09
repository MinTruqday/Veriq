import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.chunk import router as chunk
from src.api.download import router as download
from src.api.file import router as file_router
from src.api.file_request import router as file_request
from src.api.folder import router as folder
from src.api.internal import router as internal
from src.api.search import router as search
from src.api.share import router as share
from src.api.star import router as star
from src.api.storage import router as storage
from src.api.trash import router as trash
from src.api.upload import router as upload
from src.api.version import router as version
from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import close_db, database, init_db
from src.core.infrastructure.redis import redis
from src.core.storage import close_storage_client, get_storage_client, initialize_bucket

logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await initialize_bucket()
    logger.info("Cloud storage service provisioned and ready")
    yield
    await close_storage_client()
    await close_db()


app = FastAPI(title="Veriq Cloud", version=settings.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(storage)
app.include_router(upload)
app.include_router(folder)
app.include_router(file_router)
app.include_router(chunk)
app.include_router(download)
app.include_router(version)
app.include_router(trash)
app.include_router(share)
app.include_router(star)
app.include_router(search)
app.include_router(file_request)
app.include_router(internal)


@app.get("/suc-khoe", include_in_schema=False)
async def health_check():
    return {"status": "healthy", "service": "cloud"}


@app.get("/san-sang", include_in_schema=False)
async def readiness_check():
    if database.mongodb is None:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    try:
        await database.mongodb.admin.command("ping")
        await redis.ping()
        storage = await get_storage_client()
        await storage.head_bucket(Bucket=settings.OBJECT_STORAGE_PRIVATE_BUCKET)
    except Exception:
        logger.exception("Cloud readiness check failed")
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready", "service": "cloud"}

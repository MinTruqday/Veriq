import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.announcement import router as announcement_router
from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import close_db, database, init_db
from src.core.infrastructure.redis import redis
from src.core.middleware import add_trace_id_header, trace_id_filter

logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} {level} [{extra[trace_id]}] {message}",
    filter=trace_id_filter,
    level="INFO",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await redis.get_client().ping()
    logger.info("Notification service initialized")
    try:
        yield
    finally:
        await redis.aclose()
        await close_db()


app = FastAPI(title="Veriq Notification", version=settings.VERSION, lifespan=lifespan)
app.middleware("http")(add_trace_id_header)
origins = [origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=bool(origins),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(announcement_router)


@app.get("/suc-khoe")
async def health_check():
    return {"status": "healthy"}


@app.get("/san-sang")
async def readiness_check():
    checks = {}
    try:
        await database.mongodb.admin.command("ping")
        checks["mongodb"] = "ready"
    except Exception:
        checks["mongodb"] = "unavailable"
    try:
        checks["redis"] = "ready" if await redis.get_client().ping() else "unavailable"
    except Exception:
        checks["redis"] = "unavailable"
    ready = all(value == "ready" for value in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "degraded", "checks": checks},
    )

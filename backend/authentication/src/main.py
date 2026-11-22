from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.internal import router as internal_router
from src.api.platform import router as platform_router
from src.api.platform_controls import router as platform_controls_router
from src.api.session import router as session_router
from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import close_db, database, init_db
from src.core.infrastructure.redis import redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await redis.get_client().ping()
    logger.info("Authentication service initialized")
    try:
        yield
    finally:
        await redis.aclose()
        await close_db()


app = FastAPI(title="Veriq Authentication", version=settings.VERSION, lifespan=lifespan)
origins = [origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=bool(origins),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(session_router)
app.include_router(internal_router)
app.include_router(platform_router)
app.include_router(platform_controls_router)


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

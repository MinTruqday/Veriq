from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.document import router as document
from src.api.version import router as version
from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import close_db, database, init_db
from src.core.infrastructure.mq import mq
from src.core.infrastructure.redis import redis
from src.core.metrics import PrometheusMiddleware, metrics_endpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from src.services.document_ingestion_dispatcher import document_ingestion_dispatcher

    await document_ingestion_dispatcher.start()
    logger.info("Content management service provisioned and ready")
    try:
        yield
    finally:
        await document_ingestion_dispatcher.stop()
        await close_db()


app = FastAPI(title="Veriq Content", version=settings.VERSION, lifespan=lifespan)
app.add_middleware(PrometheusMiddleware, service_name="content")
app.add_route("/so-lieu", metrics_endpoint("content"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        settings.CORS_ALLOWED_ORIGINS.split(",") if settings.CORS_ALLOWED_ORIGINS else []
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(document)
app.include_router(version)


@app.get("/suc-khoe", include_in_schema=False)
async def health_check():
    return {"status": "healthy", "service": "content"}


@app.get("/san-sang", include_in_schema=False)
async def readiness_check():
    if database.mongodb is None:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    try:
        await database.mongodb.admin.command("ping")
        await redis.ping()
        if not await mq.health_check():
            raise RuntimeError("RabbitMQ is unavailable")
    except Exception:
        logger.exception("Content readiness check failed")
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready", "service": "content"}

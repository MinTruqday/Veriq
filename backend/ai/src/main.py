import hmac
import sys
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.automation import router as automation_router
from src.api.cache import router as cache_router
from src.api.embedding import router as embedding_router
from src.api.events import router as events
from src.api.indexing import indexing_router
from src.api.indexing import router as ingest
from src.api.inference import router as inference
from src.api.mcp import router as mcp_router
from src.api.projects import router as projects_router
from src.api.retrieval import router as retrieval_router
from src.core.dependency import require_system_admin
from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.core.metrics import PrometheusMiddleware, metrics_endpoint
from src.core.middleware import add_trace_id_header, trace_id_filter
from src.schemas.agent import AgentRunStatus
from src.services.agent_metrics import agentops
from src.services.evaluation import evaluation
from src.services.retrieval import initialize_retrieval

logger.remove()


def _safe_log_sink(message):
    from src.core.security.guardrails import guardrails_engine

    result = guardrails_engine.inspect_output(str(message))
    sys.stdout.write(result.get("sanitized_text", str(message)))


logger.add(
    _safe_log_sink,
    format="{time:YYYY-MM-DD HH:mm:ss} {level} [{extra[trace_id]}] {message}",
    filter=trace_id_filter,
    level="INFO",
    backtrace=False,
    diagnose=False,
)

retrieval_ready = False

app = FastAPI(title="Veriq AI", version=settings.VERSION)
app.add_middleware(PrometheusMiddleware, service_name="ai")
app.add_route("/so-lieu", metrics_endpoint("ai"))


@app.middleware("http")
async def internal_token_middleware(request: Request, call_next):
    if "/noi-bo/" in request.url.path:
        token = request.headers.get("X-Internal-Token")
        if (
            not token
            or not settings.SECRET_KEY
            or not hmac.compare_digest(token, settings.SECRET_KEY)
        ):
            return JSONResponse(
                status_code=403, content={"detail": {"code": "invalid_internal_token"}}
            )
    return await call_next(request)


app.middleware("http")(add_trace_id_header)
allowed_origins = (
    settings.CORS_ALLOWED_ORIGINS.split(",") if settings.CORS_ALLOWED_ORIGINS else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials="*" not in allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(inference)
app.include_router(automation_router)
app.include_router(mcp_router)
app.include_router(ingest)
app.include_router(events)
app.include_router(retrieval_router, prefix="/tri-thuc")
app.include_router(embedding_router, prefix="/tri-thuc/bieu-dien-vector")
app.include_router(indexing_router, prefix="/tri-thuc")
app.include_router(cache_router, prefix="/tri-thuc/bo-nho-dem")
app.include_router(projects_router, prefix="/tri-thuc")


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
        from src.core.infrastructure.redis import redis

        checks["redis"] = "ready" if await redis.get_client().ping() else "unavailable"
    except Exception:
        checks["redis"] = "unavailable"
    try:
        from src.core.infrastructure.mq import mq

        checks["rabbitmq"] = "ready" if await mq.health_check() else "unavailable"
    except Exception:
        checks["rabbitmq"] = "unavailable"
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{settings.QDRANT_URL.rstrip('/')}/collections")
        checks["qdrant"] = "ready" if response.status_code == 200 else "unavailable"
    except Exception:
        checks["qdrant"] = "unavailable"
    try:
        from src.knowledge.graph.client import graph_client

        checks["neo4j"] = "ready" if await graph_client.ready() else "unavailable"
    except Exception:
        checks["neo4j"] = "unavailable"
    checks["knowledge"] = "ready" if retrieval_ready else "unavailable"
    try:
        from src.services.conversion import document_parser

        checks["object_storage"] = (
            "ready" if await document_parser.storage_ready() else "unavailable"
        )
    except Exception:
        checks["object_storage"] = "unavailable"
    try:
        from src.utils.model_provider import model_client

        checks.update(await model_client.readiness())
    except Exception:
        checks["model"] = "unavailable"
    required_checks = {key: value for key, value in checks.items() if key != "model"}
    infrastructure_ready = all(value == "ready" for value in required_checks.values())
    model_ready = checks.get("model") == "ready"
    ready = infrastructure_ready and model_ready
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "degraded", "checks": checks},
    )


@app.get("/danh-gia/so-lieu")
async def agent_metrics():
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(
        content=agentops.get_prometheus_metrics(), media_type="text/plain; version=0.0.4"
    )


@app.get("/danh-gia/trang-thai", dependencies=[Depends(require_system_admin)])
async def agent_status():
    from src.repositories.memory import memory_repository

    return {
        "orchestration": {
            "active_runs": await memory_repository.count_runs(
                [
                    AgentRunStatus.PLANNING,
                    AgentRunStatus.RUNNING,
                    AgentRunStatus.VERIFYING,
                ]
            ),
        },
        "evaluation": evaluation.get_dashboard_metrics(),
    }


async def startup_event():
    logger.info("AI system initialized")
    try:
        from src.core.infrastructure.observability import initialize_tracing

        initialize_tracing()
    except Exception as error:
        logger.warning("AI trace initialization unavailable: {}", type(error).__name__)
    from src.prompts.testing import validate_prompt_contract_registry

    validate_prompt_contract_registry()
    try:
        from src.core.infrastructure.database import init_db

        await init_db()
    except Exception:
        logger.exception("MongoDB indexing error")
    global retrieval_ready
    retrieval_ready = False
    try:
        from src.utils.background import create_background_task

        create_background_task(initialize_ai_runtime_background(), "ai-runtime-warmup")
    except Exception:
        logger.exception("AI retrieval capability startup error")
    try:
        from src.runtime.events import cron_scheduler, event_processor

        await event_processor.start_worker()
        await cron_scheduler.start()
        logger.info("Event processor started")
    except Exception:
        logger.exception("Event processor startup error")
    try:
        from src.runtime.automation_worker import automation_worker

        await automation_worker.start()
        logger.info("AI automation worker started")
    except Exception:
        logger.exception("AI automation worker startup error")
    try:
        from src.runtime.document_ingestion_worker import document_ingestion_worker

        await document_ingestion_worker.start()
        logger.info("Durable document ingestion worker started")
    except Exception:
        logger.exception("Durable document ingestion worker startup error")


async def initialize_retrieval_background():
    global retrieval_ready
    try:
        await initialize_retrieval()
        retrieval_ready = True
        logger.info("AI retrieval capability initialized")
    except Exception:
        retrieval_ready = False
        logger.exception("AI retrieval capability startup error")


async def initialize_ai_runtime_background():
    try:
        from src.knowledge.graph.repository import graph_repository

        await graph_repository.ensure_schema()
        logger.info("Graph schema initialized")
    except Exception:
        logger.exception("Graph schema initialization error")
    try:
        from src.utils.model_provider import model_client

        if await model_client.warm_primary():
            logger.info("Configured model warmup completed")
        else:
            logger.warning("Primary model unavailable")
    except Exception:
        logger.exception("Primary model readiness startup error")
    await initialize_retrieval_background()


async def shutdown_event():
    global retrieval_ready
    retrieval_ready = False
    try:
        from src.runtime.document_ingestion_worker import document_ingestion_worker

        await document_ingestion_worker.stop()
    except Exception:
        logger.exception("Durable document ingestion worker shutdown failed")
    try:
        from src.utils.background import drain_background_tasks

        await drain_background_tasks()
    except Exception:
        logger.exception("Background task shutdown failed")
    try:
        from src.knowledge.graph.client import graph_client

        await graph_client.close()
    except Exception:
        logger.exception("Graph shutdown failed")
    try:
        from src.runtime.events import cron_scheduler, event_processor

        await cron_scheduler.stop()
        await event_processor.stop_worker()
    except Exception:
        logger.exception("Event processor shutdown failed")
    try:
        from src.runtime.automation_worker import automation_worker

        await automation_worker.stop()
    except Exception:
        logger.exception("AI automation worker shutdown failed")
    try:
        from src.core.infrastructure.redis import redis

        await redis.aclose()
    except Exception:
        logger.exception("Redis shutdown failed")
    try:
        from src.core.infrastructure.mq import mq

        await mq.aclose()
    except Exception:
        logger.exception("Message queue shutdown failed")
    try:
        from src.core.infrastructure.database import close_db

        await close_db()
    except Exception:
        logger.exception("Database shutdown failed")
    try:
        from src.core.infrastructure.observability import shutdown_tracing

        shutdown_tracing()
    except Exception as error:
        logger.warning("AI trace shutdown issue: {}", type(error).__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    await startup_event()
    try:
        yield
    finally:
        await shutdown_event()


app.router.lifespan_context = lifespan

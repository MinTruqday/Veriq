import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.clients.ai_automation import start_event_dispatcher, stop_event_dispatcher
from src.core.ai_streaming import AIStreamingMiddleware
from src.core.common import failure_metadata, new_id
from src.core.configuration import settings
from src.core.database import close_database, connect_database, database
from src.core.metrics import PrometheusMiddleware, metrics_endpoint
from src.modules.design.router import router as design_router
from src.modules.execution.router import router as execution_router
from src.modules.integrations.router import router as integrations_router
from src.modules.operations.router import router as operations_router
from src.modules.projects.router import router as projects_router
from src.modules.quality.router import router as quality_router
from src.modules.requirements.router import router as requirements_router
from src.modules.requirements.services.requirement_document_worker import (
    start_requirement_document_parse_worker,
    stop_requirement_document_parse_worker,
)
from src.repositories.project_access import project_access_repository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_database()
    await project_access_repository.migrate_legacy()
    await start_event_dispatcher()
    await start_requirement_document_parse_worker()
    yield
    await stop_requirement_document_parse_worker()
    await stop_event_dispatcher()
    await close_database()


app = FastAPI(title="Veriq", version=settings.VERSION, lifespan=lifespan)
app.add_middleware(AIStreamingMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_route("/so-lieu", metrics_endpoint)
origins = [origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def release_ai_automation_access_lease(request: Request, call_next):
    request_task = asyncio.current_task()
    lease_lost = asyncio.Event()

    async def maintain_leases():
        while True:
            await asyncio.sleep(15)
            leases = getattr(request.state, "ai_automation_leases", None) or []
            if not leases:
                continue
            from src.repositories.ai_automation_access import ai_automation_access_repository

            for scope_key, lease_id in leases:
                try:
                    alive = await ai_automation_access_repository.heartbeat(
                        scope_key, lease_id
                    )
                    if not alive:
                        logger.error(
                            "AI automation request lease disappeared scope=%s",
                            scope_key,
                        )
                        lease_lost.set()
                        if request_task and not request_task.done():
                            request_task.cancel()
                        return
                except Exception:
                    logger.exception(
                        "Failed to renew AI automation request lease scope=%s",
                        scope_key,
                    )
                    lease_lost.set()
                    if request_task and not request_task.done():
                        request_task.cancel()
                    return

    def lease_lost_response():
        code = "AI_AUTOMATION_ACCESS_LEASE_LOST"
        detail = {"code": code, "retryable": True}
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": code,
                    "message": "Không thể xác nhận quyền truy cập trong khi xử lý",
                    "details": {},
                },
                "trace_id": new_id("TRC"),
                **failure_metadata(code, 503, detail),
            },
        )

    heartbeat_task = asyncio.create_task(maintain_leases())
    try:
        response = await call_next(request)
        return lease_lost_response() if lease_lost.is_set() else response
    except asyncio.CancelledError:
        if not lease_lost.is_set():
            raise
        return lease_lost_response()
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        leases = getattr(request.state, "ai_automation_leases", None)
        if leases:
            from src.repositories.ai_automation_access import ai_automation_access_repository

            for lease in leases:
                try:
                    await ai_automation_access_repository.release(*lease)
                except Exception:
                    logger.exception("Failed to release AI automation request lease")


app.include_router(projects_router)
app.include_router(requirements_router)
app.include_router(execution_router)
app.include_router(design_router)
app.include_router(quality_router)
app.include_router(integrations_router)
app.include_router(operations_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, error: HTTPException):
    trace_id = new_id("TRC")
    detail = error.detail
    if isinstance(detail, dict):
        code = detail.get("code", "REQUEST_FAILED")
        details = {key: value for key, value in detail.items() if key != "code"}
        message = detail.get("message") or code
    else:
        code = "REQUEST_FAILED"
        details = {}
        message = str(detail)
    operation = failure_metadata(code, error.status_code, detail)
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {"code": code, "message": message, "details": details},
            "trace_id": trace_id,
            **operation,
        },
        headers=error.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, error: RequestValidationError):
    trace_id = new_id("TRC")
    issues = error.errors()
    locations = [tuple(str(part) for part in issue.get("loc", ())) for issue in issues]
    messages = [str(issue.get("msg", "")) for issue in issues]
    code = "VALIDATION_ERROR"
    if any("INVALID_RISK_MODEL" in message for message in messages) or any(
        "risk_model" in location for location in locations
    ):
        code = "INVALID_RISK_MODEL"
    elif any(
        location
        and location[-1] == "reason"
        and ("quality" in request.url.path or "quyet-dinh-chat-luong" in request.url.path)
        for location in locations
    ):
        code = "QUALITY_DECISION_REASON_REQUIRED"
    elif any(
        location and location[-1] == "owner_id" and "hoan-tat-kiem-thu" in request.url.path
        for location in locations
    ):
        code = "RESIDUAL_RISK_OWNER_REQUIRED"
    elif any(
        location
        and location[-1] in {"resolution", "resolution_ref"}
        and ("finding" in request.url.path or "giai-quyet" in request.url.path)
        for location in locations
    ):
        code = "ANALYSIS_FINDING_RESOLUTION_REQUIRED"
    operation = failure_metadata(code, 422)
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "error": {
                    "code": code,
                    "message": code
                    if code != "VALIDATION_ERROR"
                    else "Dữ liệu đầu vào không hợp lệ",
                    "details": {"issues": issues},
                },
                "trace_id": trace_id,
                **operation,
            }
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, error: Exception):
    trace_id = new_id("TRC")
    operation = failure_metadata("INTERNAL_SERVER_ERROR", 500)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Thao tác thất bại",
                "details": {},
            },
            "trace_id": trace_id,
            **operation,
        },
    )


@app.get("/suc-khoe", include_in_schema=False)
async def health():
    return {"status": "healthy", "service": "testing"}


@app.get("/san-sang", include_in_schema=False)
async def ready():
    try:
        if database.client is None:
            raise RuntimeError
        await database.client.admin.command("ping")
        return {"status": "ready", "service": "testing"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready", "service": "testing"})

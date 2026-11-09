import hmac
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import close_db, database, init_db
from src.core.infrastructure.mq import mq
from src.jobs.task import worker_runner
from src.schemas import DiscardJobRequest, TestingJobRequest
from src.services import WorkerJobService


def require_internal_token(x_internal_token: str = Header(default="")):
    if not (
        settings.SECRET_KEY
        and x_internal_token
        and hmac.compare_digest(x_internal_token, settings.SECRET_KEY)
    ):
        raise HTTPException(status_code=403, detail="Invalid internal token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        await worker_runner.start()
        yield
    finally:
        await worker_runner.close()
        await mq.aclose()
        await close_db()


app = FastAPI(title="Veriq Worker", version=settings.VERSION, lifespan=lifespan)


@app.get("/suc-khoe", include_in_schema=False)
async def health():
    return {"status": "healthy", "service": "worker"}


@app.get("/san-sang", include_in_schema=False)
async def ready():
    checks = {}
    try:
        await database.mongodb.admin.command("ping")
        checks["mongodb"] = "ready"
    except Exception:
        checks["mongodb"] = "unavailable"
    try:
        await mq.get_queue(settings.WORKER_QUEUE_NAME)
        checks["rabbitmq"] = "ready"
    except Exception:
        checks["rabbitmq"] = "unavailable"
    checks["consumers"] = "ready" if worker_runner.is_running() else "unavailable"
    ready_state = all(value == "ready" for value in checks.values())
    return JSONResponse(
        status_code=200 if ready_state else 503,
        content={
            "status": "ready" if ready_state else "degraded",
            "service": "worker",
            "checks": checks,
        },
    )


@app.post(
    "/xu-ly-nen/noi-bo/kiem-thu/tac-vu",
    dependencies=[Depends(require_internal_token)],
    status_code=202,
)
async def enqueue_testing_job(payload: TestingJobRequest):
    return await WorkerJobService.enqueue(payload)


@app.post(
    "/xu-ly-nen/noi-bo/tac-vu/{job_id}/thu-lai",
    dependencies=[Depends(require_internal_token)],
    status_code=202,
)
async def retry_job(job_id: str):
    return await WorkerJobService.retry(job_id)


@app.post("/xu-ly-nen/noi-bo/tac-vu/{job_id}/huy", dependencies=[Depends(require_internal_token)])
async def cancel_job(job_id: str):
    return await WorkerJobService.cancel(job_id)


@app.get("/xu-ly-nen/noi-bo/tac-vu/{job_id}", dependencies=[Depends(require_internal_token)])
async def get_job(job_id: str):
    return await WorkerJobService.get(job_id)


@app.get("/xu-ly-nen/noi-bo/tac-vu", dependencies=[Depends(require_internal_token)])
async def list_jobs(
    project_id: str = Query(default="", max_length=128),
    status: str = Query(default="", max_length=30),
    kind: str = Query(default="", max_length=200),
    limit: int = Query(default=200, ge=1, le=1000),
):
    return await WorkerJobService.list(project_id, status, kind, limit)


@app.get("/xu-ly-nen/noi-bo/tong-quan", dependencies=[Depends(require_internal_token)])
async def job_overview(project_id: str = Query(default="", max_length=128)):
    return await WorkerJobService.overview(project_id)


@app.post(
    "/xu-ly-nen/noi-bo/tac-vu/{job_id}/loai-bo",
    dependencies=[Depends(require_internal_token)],
)
async def discard_job(job_id: str, payload: DiscardJobRequest):
    return await WorkerJobService.discard(job_id, payload)

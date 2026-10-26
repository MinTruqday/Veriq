import asyncio
import hashlib
import hmac
import json
import os
import re
import tempfile
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from loguru import logger

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.mq import mq
from src.core.metrics import metrics_collector
from src.jobs.execution_lease import maintain_execution_lease, recover_expired_executions
from src.jobs.outbox import dispatch_worker_job_outbox
from src.repositories.jobs import worker_job_repository
from src.schemas import AutomationExecutionStatus, WorkerJobStatus

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
WORKER_CONTROLLED_ENVIRONMENT_KEYS = frozenset(
    {
        "PATH",
        "HOME",
        "TMPDIR",
        "NODE_PATH",
        "PLAYWRIGHT_BROWSERS_PATH",
        "NODE_OPTIONS",
        "PYTHONPATH",
        "PYTHONHOME",
        "BASH_ENV",
        "ENV",
        "IFS",
        "SHELLOPTS",
        "CDPATH",
    }
)


class PermanentTaskError(Exception):
    code = "permanent_task_error"


def validate_testing_job_response(response_body: dict) -> dict:
    if not isinstance(response_body, dict):
        raise PermanentTaskError("Testing job response must be an object")
    result = response_body.get("data")
    if not isinstance(result, dict):
        raise PermanentTaskError("Testing job response is missing its result")
    if result.get("status") == "FAILED":
        error_code = str(result.get("error_code") or "testing_job_failed")[:160]
        if result.get("retryable"):
            raise RuntimeError(error_code)
        raise PermanentTaskError(error_code)
    return result


def raise_for_testing_response(response) -> None:
    status_code = int(response.status_code)
    if 400 <= status_code < 500 and status_code not in {408, 425, 429}:
        raise PermanentTaskError(f"testing_api_http_{status_code}")
    response.raise_for_status()


def validate_identifier(value: str, field: str):
    if not IDENTIFIER_PATTERN.fullmatch(str(value or "")):
        raise PermanentTaskError(f"Invalid {field}")


async def handle_testing_job(payload: dict):
    job_id = str(payload.get("job_id") or "")
    requester_id = str(payload.get("requester_id") or "")
    requester_email = str(payload.get("requester_email") or "")
    validate_identifier(job_id, "job identifier")
    validate_identifier(requester_id, "requester identifier")
    job_payload = payload.get("payload")
    if not isinstance(job_payload, dict):
        raise PermanentTaskError("Testing job payload is required")
    if payload.get("_worker_claimed_for_delivery") is not True:
        lease_token = str(uuid4())
        now = datetime.now(timezone.utc)
        claimed = await worker_job_repository.claim_execution(
            job_id,
            lease_token,
            now,
            now + timedelta(seconds=settings.WORKER_EXECUTION_LEASE_SECONDS),
        )
        if not claimed:
            latest = await worker_job_repository.find_one({"_id": job_id}, {"status": 1})
            if not latest:
                raise PermanentTaskError("Worker job record is unavailable")
            if latest.get("status") != WorkerJobStatus.QUEUED:
                return
            raise RuntimeError("Worker job could not be claimed; retry message delivery")
        payload["_worker_claimed_for_delivery"] = True
        payload["_execution_lease_token"] = lease_token
    lease_token = payload.get("_execution_lease_token")
    if not isinstance(lease_token, str) or not lease_token:
        raise PermanentTaskError("Worker execution lease is unavailable")
    if payload.get("event") in {"automation.newman.requested", "automation.playwright.requested"}:
        runner = payload["event"].split(".")[1]
        result = (
            await run_newman(job_id, payload, job_payload)
            if runner == "newman"
            else await run_playwright(job_id, payload, job_payload)
        )
        completed_at = datetime.now(timezone.utc)
        finalized = await worker_job_repository.finalize_execution(
            job_id,
            lease_token,
            {
                "status": WorkerJobStatus.COMPLETED,
                "result": result,
                "completed_at": completed_at,
                "expire_at": completed_at + timedelta(days=30),
            },
        )
        if not finalized or finalized.matched_count != 1:
            raise PermanentTaskError("Worker execution lease was lost before completion")
        return result
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{settings.TESTING_URL}/kiem-thu/noi-bo/tac-vu/{payload.get('event')}",
            headers={
                "X-Internal-Token": settings.SECRET_KEY,
                "X-Requester-Id": requester_id,
                "X-Requester-Email": requester_email,
            },
            json={
                "job_id": job_id,
                "project_id": payload.get("project_id"),
                "artifact_version_id": payload.get("artifact_version_id"),
                "model_version": payload.get("model_version"),
                "payload": job_payload,
            },
        )
    raise_for_testing_response(response)
    result = validate_testing_job_response(response.json())
    completed_at = datetime.now(timezone.utc)
    finalized = await worker_job_repository.finalize_execution(
        job_id,
        lease_token,
        {
            "status": WorkerJobStatus.COMPLETED,
            "result": result,
            "completed_at": completed_at,
            "expire_at": completed_at + timedelta(days=30),
        },
    )
    if not finalized or finalized.matched_count != 1:
        raise PermanentTaskError("Worker execution lease was lost before completion")
    return result


async def run_newman(job_id, payload, job_payload):
    execution_id = str(job_payload.get("execution_id") or "")
    collection = job_payload.get("collection")
    validate_identifier(execution_id, "automation execution identifier")
    if not isinstance(collection, dict):
        raise PermanentTaskError("Postman collection is required")
    with tempfile.TemporaryDirectory(prefix="veriq-newman-") as directory:
        collection_path = f"{directory}/collection.json"
        report_path = f"{directory}/report.json"
        with open(collection_path, "w", encoding="utf-8") as stream:
            json.dump(collection, stream, ensure_ascii=False)
        command = [
            "newman",
            "run",
            collection_path,
            "--reporters",
            "json",
            "--reporter-json-export",
            report_path,
            "--timeout-request",
            "30000",
        ]
        environment = job_payload.get("environment")
        if isinstance(environment, dict) and environment:
            environment_path = f"{directory}/environment.json"
            with open(environment_path, "w", encoding="utf-8") as stream:
                json.dump(
                    {
                        "name": "Veriq",
                        "values": [
                            {"key": str(key), "value": str(value), "enabled": True}
                            for key, value in environment.items()
                            if value is not None
                        ],
                    },
                    stream,
                    ensure_ascii=False,
                )
            command.extend(["--environment", environment_path])
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env=automation_environment(directory),
        )
        try:
            return_code = await asyncio.wait_for(
                process.wait(), timeout=900
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return_code = 124
        try:
            with open(report_path, encoding="utf-8") as stream:
                report = json.load(stream)
        except (OSError, json.JSONDecodeError):
            report = {}
    run = report.get("run") if isinstance(report.get("run"), dict) else {}
    stats = run.get("stats") if isinstance(run.get("stats"), dict) else {}
    executions = run.get("executions") if isinstance(run.get("executions"), list) else []
    results = []
    for execution in executions[:100000]:
        item = execution.get("item") if isinstance(execution.get("item"), dict) else {}
        response = execution.get("response") if isinstance(execution.get("response"), dict) else {}
        assertions = (
            execution.get("assertions") if isinstance(execution.get("assertions"), list) else []
        )
        results.append(
            {
                "name": str(item.get("name") or "")[:500],
                "status_code": response.get("code"),
                "response_time_ms": response.get("responseTime"),
                "assertions": [
                    {
                        "name": str(assertion.get("assertion") or "")[:500],
                        "passed": not bool(assertion.get("error")),
                    }
                    for assertion in assertions[:1000]
                    if isinstance(assertion, dict)
                ],
            }
        )
    status = (
        AutomationExecutionStatus.COMPLETED
        if return_code == 0
        else AutomationExecutionStatus.FAILED
    )
    callback = automation_callback(
        execution_id,
        job_id,
        status,
        {"runner": "newman", "return_code": return_code, "stats": stats},
        results,
        ["Newman hoàn tất" if return_code == 0 else "Newman kết thúc với lỗi"],
    )
    await send_automation_result(callback)
    return {"execution_id": execution_id, "status": status, "summary": callback["summary"]}


def automation_environment(directory, values=None):
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": directory,
        "TMPDIR": directory,
        "NODE_PATH": "/usr/local/lib/node_modules",
        "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
    }
    if isinstance(values, dict):
        for key, value in values.items():
            normalized_key = str(key).upper()
            if (
                re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", str(key))
                and normalized_key not in WORKER_CONTROLLED_ENVIRONMENT_KEYS
                and not normalized_key.startswith(("LD_", "DYLD_"))
                and value is not None
            ):
                environment[str(key)] = str(value)
    return environment


def automation_callback(execution_id, job_id, status, summary, results, logs):
    signature_value = f"{execution_id}:{job_id}:{status}"
    return {
        "execution_id": execution_id,
        "operation_id": job_id,
        "status": status,
        "summary": summary,
        "results": results,
        "logs": logs,
        "artifact_refs": [],
        "context_signature": hmac.new(
            settings.SECRET_KEY.encode(), signature_value.encode(), hashlib.sha256
        ).hexdigest(),
    }


async def send_automation_result(callback):
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{settings.TESTING_URL}/noi-bo/kiem-thu/thuc-thi-tu-dong/ket-qua",
            headers={"X-Internal-Token": settings.SECRET_KEY},
            json=callback,
        )
        response.raise_for_status()


def playwright_results(report):
    output = []

    def visit_suite(suite):
        for spec in suite.get("specs", []) if isinstance(suite, dict) else []:
            for test in spec.get("tests", []) if isinstance(spec, dict) else []:
                attempts = test.get("results", []) if isinstance(test, dict) else []
                last = attempts[-1] if attempts else {}
                output.append(
                    {
                        "name": str(spec.get("title") or test.get("title") or "")[:500],
                        "status": str(last.get("status") or test.get("status") or "unknown")[:100],
                        "duration_ms": last.get("duration"),
                        "retry": last.get("retry"),
                    }
                )
        for child in suite.get("suites", []) if isinstance(suite, dict) else []:
            visit_suite(child)

    for suite in report.get("suites", []) if isinstance(report, dict) else []:
        visit_suite(suite)
    return output[:100000]


async def run_playwright(job_id, payload, job_payload):
    execution_id = str(job_payload.get("execution_id") or "")
    source = job_payload.get("source")
    language = str(job_payload.get("language") or "typescript")
    validate_identifier(execution_id, "automation execution identifier")
    if not isinstance(source, str) or not source.strip() or len(source) > 500000:
        raise PermanentTaskError("Approved Playwright source is required")
    suffix = "js" if language == "javascript" else "ts"
    with tempfile.TemporaryDirectory(prefix="veriq-playwright-") as directory:
        script_path = f"{directory}/veriq.spec.{suffix}"
        output_path = f"{directory}/test-results"
        with open(script_path, "w", encoding="utf-8") as stream:
            stream.write(source)
        os.symlink("/usr/local/lib/node_modules", f"{directory}/node_modules")
        process = await asyncio.create_subprocess_exec(
            "playwright",
            "test",
            script_path,
            "--reporter=json",
            "--workers=1",
            f"--output={output_path}",
            cwd=directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=automation_environment(directory, job_payload.get("environment")),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=900
            )
            return_code = process.returncode
        except TimeoutError:
            process.kill()
            stdout, stderr = await process.communicate()
            return_code = 124
        try:
            report = json.loads(stdout.decode("utf-8", errors="replace"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            report = {}
        results = playwright_results(report)
        stats = report.get("stats") if isinstance(report.get("stats"), dict) else {}
        error_present = bool(stderr.strip())
    status = (
        AutomationExecutionStatus.COMPLETED
        if return_code == 0
        else AutomationExecutionStatus.FAILED
    )
    callback = automation_callback(
        execution_id,
        job_id,
        status,
        {
            "runner": "playwright",
            "return_code": return_code,
            "stats": stats,
            "runner_error_present": error_present,
        },
        results,
        ["Playwright hoàn tất" if return_code == 0 else "Playwright kết thúc với lỗi"],
    )
    await send_automation_result(callback)
    return {"execution_id": execution_id, "status": status, "summary": callback["summary"]}


async def mark_failed(queue_name: str, payload: dict, error: Exception):
    message = str(error)[-1000:]
    job_id = str(payload.get("job_id") or "")
    if IDENTIFIER_PATTERN.fullmatch(job_id):
        completed_at = datetime.now(timezone.utc)
        values = {
            "status": WorkerJobStatus.FAILED,
            "error_code": getattr(error, "code", "worker_task_failed"),
            "error": message,
            "completed_at": completed_at,
            "expire_at": completed_at + timedelta(days=30),
        }
        lease_token = payload.get("_execution_lease_token")
        if isinstance(lease_token, str) and lease_token:
            await worker_job_repository.fail_execution(job_id, lease_token, values)
        else:
            await worker_job_repository.record(job_id, values, {"kind": queue_name})


class WorkerRunner:
    def __init__(self):
        self.tasks = []

    async def consume(self, queue_name: str, handler):
        while True:
            channel = None
            try:
                channel, queue = await mq.create_consumer_queue(queue_name)
                async with queue.iterator() as iterator:
                    async for message in iterator:
                        try:
                            try:
                                payload = json.loads(message.body.decode("utf-8"))
                                if not isinstance(payload, dict):
                                    raise PermanentTaskError("Task payload must be an object")
                            except (UnicodeDecodeError, json.JSONDecodeError, PermanentTaskError):
                                await message.reject(requeue=False)
                                continue
                            lease_task = None
                            job_id = str(payload.get("job_id") or "")
                            if IDENTIFIER_PATTERN.fullmatch(job_id):
                                lease_token = str(uuid4())
                                now = datetime.now(timezone.utc)
                                claimed = await worker_job_repository.claim_execution(
                                    job_id,
                                    lease_token,
                                    now,
                                    now + timedelta(
                                        seconds=settings.WORKER_EXECUTION_LEASE_SECONDS
                                    ),
                                )
                                if not claimed:
                                    latest = await worker_job_repository.find_one(
                                        {"_id": job_id}, {"status": 1}
                                    )
                                    if not latest:
                                        raise PermanentTaskError(
                                            "Worker job record is unavailable"
                                        )
                                    if latest and latest.get("status") != WorkerJobStatus.QUEUED:
                                        await message.ack()
                                        metrics_collector.change_queue_depth(queue_name, -1)
                                        continue
                                    raise RuntimeError("Worker job could not be claimed")
                                payload["_worker_claimed_for_delivery"] = True
                                payload["_execution_lease_token"] = lease_token
                                lease_task = asyncio.create_task(
                                    maintain_execution_lease(job_id, lease_token),
                                    name=f"worker:execution-lease:{job_id}",
                                )
                            failure = None
                            try:
                                for attempt in range(3):
                                    try:
                                        await handler(payload)
                                        failure = None
                                        break
                                    except PermanentTaskError as error:
                                        failure = error
                                        break
                                    except Exception as error:
                                        failure = error
                                        logger.exception("Worker task attempt failed")
                                        if attempt + 1 < 3:
                                            await asyncio.sleep(2**attempt)
                                if failure is None:
                                    await message.ack()
                                else:
                                    await mark_failed(queue_name, payload, failure)
                                    if isinstance(failure, PermanentTaskError):
                                        await message.ack()
                                    else:
                                        await message.reject(requeue=False)
                                metrics_collector.change_queue_depth(queue_name, -1)
                            finally:
                                if lease_task:
                                    lease_task.cancel()
                                    with suppress(asyncio.CancelledError, Exception):
                                        await lease_task
                        except Exception:
                            if not message.processed:
                                await message.reject(requeue=True)
                            raise
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Worker queue consumer cycle failed")
                await asyncio.sleep(2)
            finally:
                if channel and not channel.is_closed:
                    await channel.close()

    async def start(self):
        for attempt in range(1, 11):
            try:
                await mq.connect()
                break
            except Exception:
                if attempt == 10:
                    raise
                logger.warning("Worker message queue connection delayed attempt={}", attempt)
                await asyncio.sleep(min(attempt, 5))
        self.tasks = [
            asyncio.create_task(
                self.consume(settings.WORKER_QUEUE_NAME, handle_testing_job),
                name=f"worker:{settings.WORKER_QUEUE_NAME}",
            ),
            asyncio.create_task(
                dispatch_worker_job_outbox(),
                name="worker:job-outbox-dispatcher",
            ),
            asyncio.create_task(
                recover_expired_executions(),
                name="worker:execution-lease-recovery",
            ),
        ]

    async def close(self):
        for task in self.tasks:
            task.cancel()
        for task in self.tasks:
            with suppress(asyncio.CancelledError, Exception):
                await task
        self.tasks.clear()

    def is_running(self) -> bool:
        return bool(self.tasks and all(not task.done() for task in self.tasks))


worker_runner = WorkerRunner()

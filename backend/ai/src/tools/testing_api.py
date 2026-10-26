import json

import httpx

from src.core.infrastructure.configuration import settings
from src.tools.http_client import INTERNAL_API_URL, make_api_request


def headers(config):
    configurable = (config or {}).get("configurable", {})
    token = configurable.get("token")
    if not token:
        return None
    values = {"Authorization": token, "X-Internal-Token": settings.SECRET_KEY}
    automation_run_id = configurable.get("automation_run_id")
    if automation_run_id:
        values["X-AI-Automation-Run"] = str(automation_run_id)
    return values

async def call(method, path, config, payload=None, timeout=60):
    request_headers = headers(config)
    if not request_headers:
        return json.dumps({"status": "authentication_required"})
    try:
        response = await make_api_request(
            method,
            f"{INTERNAL_API_URL}/kiem-thu{path}",
            headers=request_headers,
            json=payload,
            timeout=timeout,
        )
    except httpx.HTTPStatusError as error:
        response = error.response
    try:
        body = response.json()
    except ValueError:
        body = {"error": {"code": "UPSTREAM_RESPONSE_INVALID"}}
    if response.status_code >= 400:
        error = body.get("error") or body.get("detail")
        if error is None:
            error = {
                "code": body.get("error_code") or "UPSTREAM_REQUEST_FAILED",
                "message": body.get("message") or body.get("description"),
            }
        if not isinstance(error, dict):
            error = {"code": "UPSTREAM_REQUEST_FAILED", "message": str(error)}
        return json.dumps(
            {
                "status": "qa_operation_failed",
                "upstream_status": response.status_code,
                "error": error,
            },
            ensure_ascii=False,
        )
    return json.dumps(body.get("data", body), ensure_ascii=False, default=str)

def parse(value):
    try:
        result = json.loads(value)
        return result if isinstance(result, dict) else None
    except (TypeError, json.JSONDecodeError):
        return None

class AutomationOperationError(RuntimeError):
    def __init__(self, reason_code):
        self.reason_code = str(reason_code or "AUTOMATION_STEP_FAILED")
        super().__init__(self.reason_code)

async def require_operation(method, path, config, payload=None, timeout=60):
    raw = await call(method, path, config, payload, timeout=timeout)
    try:
        result = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        result = None
    if not isinstance(result, (dict, list)) or isinstance(result, dict) and result.get("status") in {
        "authentication_required",
        "invalid_payload",
        "qa_operation_failed",
    }:
        error = (result or {}).get("error") if isinstance(result, dict) else None
        error_code = error.get("code") if isinstance(error, dict) else None
        raise AutomationOperationError(
            error_code
            or (result or {}).get("status")
            or "AUTOMATION_STEP_FAILED"
        )
    return result




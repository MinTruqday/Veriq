import json

import httpx
from loguru import logger

from src.core.infrastructure.configuration import settings
from src.tools.http_client import INTERNAL_API_URL, make_api_request


def safe_validation_issue_metadata(body, limit=20):
    if not isinstance(body, dict):
        return []
    error = body.get("error")
    details = body.get("detail")
    if isinstance(error, dict):
        error_details = error.get("details")
        if isinstance(error_details, dict) and isinstance(error_details.get("issues"), list):
            details = error_details["issues"]
    if not isinstance(details, list):
        return []
    issues = []
    for item in details[:limit]:
        if not isinstance(item, dict):
            continue
        location = item.get("loc")
        error_type = item.get("type")
        if not isinstance(location, (list, tuple)) or not isinstance(error_type, str):
            continue
        safe_location = [
            value[:120] if isinstance(value, str) else value
            for value in location
            if isinstance(value, (str, int)) and not isinstance(value, bool)
        ][:12]
        issues.append({"loc": safe_location, "type": error_type[:120]})
    return issues


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
        validation_issues = safe_validation_issue_metadata(body)
        if response.status_code == 422:
            upstream_error = body.get("error") if isinstance(body, dict) else None
            error_code = (
                upstream_error.get("code")
                if isinstance(upstream_error, dict)
                else None
            )
            logger.warning(
                "Testing API validation failure method={} path={} error_code={} issue_count={} issues={}",
                method.upper(),
                path.split("?", 1)[0][:240],
                str(error_code or "UNKNOWN")[:120],
                len(validation_issues),
                validation_issues,
            )
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




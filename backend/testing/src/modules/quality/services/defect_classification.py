from fastapi import HTTPException

from src.repositories.test_strategy import test_strategy_repository


def _configured_label(scale, requested, field):
    normalized = " ".join(str(requested or "").split()).casefold()
    for item in scale:
        label = " ".join(str(item.get("label") or "").split())
        if label.casefold() == normalized and label:
            return label
    raise HTTPException(
        status_code=422, detail={"code": "DEFECT_CLASSIFICATION_NOT_CONFIGURED", "field": field}
    )


async def resolve_defect_classification(project_id, severity, priority):
    strategy = await test_strategy_repository.active_approved(project_id, "APPROVED")
    risk_model = (strategy or {}).get("risk_model") or {}
    severity_scale = risk_model.get("severity_scale") or []
    priority_scale = risk_model.get("priority_scale") or []
    if not severity_scale or not priority_scale:
        raise HTTPException(
            status_code=409, detail={"code": "DEFECT_CLASSIFICATION_POLICY_REQUIRED"}
        )
    severity_values = _severity_fields(strategy, risk_model, severity_scale, severity)
    configured_priority = _configured_label(priority_scale, priority, "priority")
    return {**severity_values, "priority": configured_priority}


def _severity_fields(strategy, risk_model, severity_scale, severity):
    configured_severity = _configured_label(severity_scale, severity, "severity")
    blocking = {
        " ".join(str(value).split()).casefold()
        for value in risk_model.get("blocking_severities") or []
    }
    critical = {
        " ".join(str(value).split()).casefold()
        for value in risk_model.get("critical_severities") or []
    }
    return {
        "severity": configured_severity,
        "severity_blocks_release": configured_severity.casefold() in blocking,
        "severity_is_critical": configured_severity.casefold() in critical,
        "severity_strategy_id": strategy["_id"],
        "severity_strategy_version": strategy.get("version"),
    }


async def resolve_severity_classification(project_id, severity):
    strategy = await test_strategy_repository.active_approved(project_id, "APPROVED")
    risk_model = (strategy or {}).get("risk_model") or {}
    severity_scale = risk_model.get("severity_scale") or []
    if not severity_scale:
        raise HTTPException(
            status_code=409, detail={"code": "DEFECT_CLASSIFICATION_POLICY_REQUIRED"}
        )
    return _severity_fields(strategy, risk_model, severity_scale, severity)


async def resolve_priority_classification(project_id, priority):
    strategy = await test_strategy_repository.active_approved(project_id, "APPROVED")
    risk_model = (strategy or {}).get("risk_model") or {}
    if not risk_model.get("priority_scale"):
        raise HTTPException(
            status_code=409, detail={"code": "DEFECT_CLASSIFICATION_POLICY_REQUIRED"}
        )
    return {
        "priority": _configured_label(risk_model["priority_scale"], priority, "priority"),
        "priority_strategy_id": strategy["_id"],
        "priority_strategy_version": strategy.get("version"),
    }


def defect_is_blocking(defect):
    if "severity_blocks_release" in defect:
        return bool(defect.get("severity_blocks_release"))
    return str(defect.get("severity") or "").casefold() in {"blocker", "critical"}


def defect_is_critical(defect):
    if "severity_is_critical" in defect:
        return bool(defect.get("severity_is_critical"))
    return str(defect.get("severity") or "").casefold() == "critical"

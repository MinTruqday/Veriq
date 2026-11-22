def _severity_fields(severity):
    normalized = " ".join(str(severity or "").split()).casefold()
    critical = normalized == "critical"
    return {
        "severity": " ".join(str(severity or "").split()),
        "severity_blocks_release": normalized in {"blocker", "critical"},
        "severity_is_critical": critical,
    }


async def resolve_defect_classification(project_id, severity, priority):
    return {**_severity_fields(severity), "priority": " ".join(str(priority or "").split())}


async def resolve_severity_classification(project_id, severity):
    return _severity_fields(severity)


async def resolve_priority_classification(project_id, priority):
    return {"priority": " ".join(str(priority or "").split())}


def defect_is_blocking(defect):
    return bool(defect.get("severity_blocks_release"))


def defect_is_critical(defect):
    return bool(defect.get("severity_is_critical"))

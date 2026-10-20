import json

from fastapi import HTTPException
from langchain_core.runnables import RunnableConfig

from src.tools.testing import get_project_context


async def project_access(project_id, token, automation_run_id=None):
    configurable = {"token": f"Bearer {token}", "project_id": project_id}
    if automation_run_id:
        configurable["automation_run_id"] = automation_run_id
    config = RunnableConfig(configurable=configurable)
    raw = await get_project_context.ainvoke({"project_id": project_id}, config=config)
    try:
        context = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail={"code": "PROJECT_CONTEXT_INVALID"}) from error
    project = context.get("project") or {}
    membership = project.get("current_membership") or {}
    permissions = project.get("current_permissions") or []
    if not project.get("_id") or not membership.get("project_role"):
        raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
    roles = set(membership.get("project_roles") or [membership["project_role"]])
    effective_role = "QA" if "QA" in roles else membership["project_role"]
    return effective_role, permissions

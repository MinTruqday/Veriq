import json

from fastapi import HTTPException
from langchain_core.runnables import RunnableConfig

from src.tools.knowledge_tools import get_project_context


async def project_access(
    project_id, token, ai_run_id=None, preferred_role=None
):
    configurable = {"token": f"Bearer {token}", "project_id": project_id}
    if ai_run_id:
        configurable["ai_run_id"] = ai_run_id
    config = RunnableConfig(configurable=configurable)
    raw = await get_project_context.ainvoke({"project_id": project_id}, config=config)
    try:
        context = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail={"code": "PROJECT_CONTEXT_INVALID"}) from error
    project = context.get("project") or {}
    membership = project.get("current_membership") or {}
    permissions = project.get("current_permissions") or []
    membership_roles = membership.get("project_roles")
    if not isinstance(membership_roles, list):
        membership_roles = []
    primary_role = membership.get("project_role")
    normalized_primary_role = (
        primary_role.strip().upper()
        if isinstance(primary_role, str) and primary_role.strip()
        else None
    )
    if primary_role:
        membership_roles = [*membership_roles, primary_role]
    roles = sorted(
        {
            str(role).strip().upper()
            for role in membership_roles
            if isinstance(role, str) and role.strip()
        }
    )
    if not project.get("_id") or not roles:
        raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
    if preferred_role and preferred_role.strip().upper() not in roles:
        raise HTTPException(
            status_code=403,
            detail={"code": "PROJECT_ROLE_NOT_ACTIVE", "required_role": preferred_role},
        )
    effective_role = (
        preferred_role.strip().upper()
        if preferred_role
        else normalized_primary_role or roles[0]
    )
    return effective_role, permissions

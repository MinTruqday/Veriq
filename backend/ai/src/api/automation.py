import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependency import get_current_user, oauth2_scheme, verify_internal_token
from src.repositories.automation import automation_repository
from src.schemas.auth import CurrentUser, SystemRole
from src.schemas.automation import (
    AutomationAction,
    AutomationCancelRequest,
    AutomationClarificationResponseRequest,
    AutomationDefinitionPatch,
    AutomationDefinitionRequest,
    AutomationEventRequest,
    AutomationEventResponse,
    AutomationRetryRequest,
    AutomationRunRequest,
    AutomationStatus,
    AutomationTrigger,
    AutomationWorkflowRun,
    AutomationWorkflowSnapshot,
)
from src.services.automation import automation_service
from src.services.project_access import project_access

router = APIRouter(prefix="/tu-dong-hoa-ai", tags=["AI Automation"])

_MAX_WORKFLOW_RUNS = 200


def build_automation_workflow_snapshot(root, descendants, truncated=False):
    ordered = [root, *descendants]
    statuses = {run.status for run in ordered}
    active_statuses = {AutomationStatus.QUEUED, AutomationStatus.RUNNING}
    blocked_statuses = {
        AutomationStatus.AWAITING_INPUT,
        AutomationStatus.AWAITING_AUTHORIZATION,
    }
    terminal_statuses = {
        AutomationStatus.COMPLETED,
        AutomationStatus.DEGRADED,
        AutomationStatus.FAILED,
        AutomationStatus.CANCELLED,
    }
    if truncated:
        status = AutomationStatus.DEGRADED
    elif statuses & active_statuses:
        status = AutomationStatus.RUNNING
    elif AutomationStatus.DEGRADED in statuses:
        status = AutomationStatus.DEGRADED
    elif AutomationStatus.FAILED in statuses:
        status = AutomationStatus.FAILED
    elif AutomationStatus.AWAITING_AUTHORIZATION in statuses:
        status = AutomationStatus.AWAITING_AUTHORIZATION
    elif AutomationStatus.AWAITING_INPUT in statuses:
        status = AutomationStatus.AWAITING_INPUT
    elif AutomationStatus.CANCELLED in statuses:
        status = AutomationStatus.CANCELLED
    else:
        status = AutomationStatus.COMPLETED

    summaries = []
    for run in ordered:
        parent_id = (run.constraints or {}).get("parent_automation_run_id")
        summaries.append(
            AutomationWorkflowRun(
                automation_run_id=run.automation_run_id,
                parent_automation_run_id=parent_id,
                trigger=run.trigger,
                status=run.status,
                error_code=run.error_code,
                created_at=run.created_at,
                updated_at=run.updated_at,
            )
        )
    return AutomationWorkflowSnapshot(
        root_automation_run_id=root.automation_run_id,
        status=status,
        terminal=not truncated and statuses.issubset(terminal_statuses),
        succeeded=not truncated and all(
            item.status == AutomationStatus.COMPLETED for item in ordered
        ),
        truncated=truncated,
        run_count=len(ordered),
        active_count=sum(item.status in active_statuses for item in ordered),
        blocked_count=sum(item.status in blocked_statuses for item in ordered),
        failed_count=sum(
            item.status in {AutomationStatus.FAILED, AutomationStatus.DEGRADED}
            for item in ordered
        ),
        runs=summaries,
    )


async def _automation_workflow_snapshot(root):
    descendants = []
    visited = {root.automation_run_id}
    frontier = [root]
    truncated = False
    while frontier:
        parent = frontier.pop(0)
        remaining = _MAX_WORKFLOW_RUNS - len(visited)
        children = await automation_repository.list_child_runs(
            parent.automation_run_id,
            root.project_id,
            root.requester_user_id,
            remaining + 1,
        )
        if len(children) > remaining:
            truncated = True
            children = children[:remaining]
        for child in children:
            if child.project_id != root.project_id:
                truncated = True
                continue
            if child.automation_run_id in visited:
                continue
            visited.add(child.automation_run_id)
            descendants.append(child)
            frontier.append(child)
        if truncated:
            break
    return build_automation_workflow_snapshot(root, descendants, truncated)


async def _readable_run(run_id: str, token: str, user: CurrentUser):
    run = await automation_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    if user.system_role == SystemRole.ADMIN:
        return run
    _, permissions = await project_access(run.project_id, token)
    can_read_project_runs = "proposal.read" in permissions
    can_read_own_run = (
        run.requester_user_id == user.id and "automation.read" in permissions
    )
    if not can_read_project_runs and not can_read_own_run:
        raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
    return run


async def _controllable_run(run_id: str, token: str, user: CurrentUser):
    run = await _readable_run(run_id, token, user)
    if run.requester_user_id != user.id and user.system_role != SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail={"code": "AUTOMATION_CONTROL_DENIED"})
    return run


async def _controllable_definition(definition_id: str, token: str, user: CurrentUser):
    definition = await automation_repository.get_definition(definition_id)
    if not definition:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    if user.system_role == SystemRole.ADMIN:
        return definition
    role, permissions = await project_access(definition.project_id, token)
    if (
        definition.owner_user_id != user.id
        or role not in {"BA", "QA"}
        or "automation.create" not in permissions
    ):
        raise HTTPException(status_code=403, detail={"code": "AUTOMATION_DEFINITION_CONTROL_DENIED"})
    return definition


@router.post("/dinh-nghia", status_code=status.HTTP_201_CREATED)
async def create_automation_definition(
    payload: AutomationDefinitionRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    role, permissions = await project_access(payload.project_id, token)
    if "automation.create" not in permissions:
        raise HTTPException(status_code=403, detail={"code": "AUTOMATION_DEFINITION_DENIED"})
    return await automation_service.create_definition(payload, user.id, role, permissions)


@router.get("/triggers")
async def list_automation_triggers():
    return [
        trigger.value
        for trigger in AutomationTrigger
        if trigger != AutomationTrigger.MANUAL
    ]


@router.get("/hanh-dong")
async def list_automation_actions():
    return [action.value for action in AutomationAction]


@router.get("/du-an/{project_id}/dinh-nghia")
async def list_automation_definitions(
    project_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    if user.system_role != SystemRole.ADMIN:
        _, permissions = await project_access(project_id, token)
        if "automation.read" not in permissions:
            raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
    return await automation_repository.list_definitions(project_id)


@router.patch("/dinh-nghia/{definition_id}")
async def update_automation_definition(
    definition_id: str,
    payload: AutomationDefinitionPatch,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    definition = await _controllable_definition(definition_id, token, user)
    return await automation_service.update_definition(definition, payload)


@router.post(
    "/noi-bo/su-kien",
    dependencies=[Depends(verify_internal_token)],
    response_model=AutomationEventResponse,
)
async def receive_automation_event(payload: AutomationEventRequest):
    runs = await automation_service.enqueue_event(payload)
    if any(
        run.status == AutomationStatus.DEGRADED
        and run.error_code == "AUTOMATION_QUEUE_UNAVAILABLE"
        for run in runs
    ):
        raise HTTPException(
            status_code=503,
            detail={"code": "AUTOMATION_QUEUE_UNAVAILABLE"},
        )
    if not runs:
        return {
            "status": "suppressed",
            "reason_code": "AUTOMATION_TRIGGER_DISABLED",
            "runs": [],
        }
    return {"status": "accepted", "runs": runs}


@router.post(
    "/noi-bo/tai-lieu-yeu-cau/{document_id}/huy-luot-chay",
    dependencies=[Depends(verify_internal_token)],
)
async def cancel_requirement_document_runs(document_id: str):
    """Stop queued/retryable ingestion runs when Testing revokes AI-read access."""
    cancelled = await automation_service.cancel_document_ingestion_runs(document_id)
    return {"cancelled_run_count": cancelled}


@router.get(
    "/noi-bo/luot-chay/{automation_run_id}/trang-thai-thuc-thi",
    dependencies=[Depends(verify_internal_token)],
)
async def get_internal_run_execution_status(automation_run_id: str):
    run = await automation_repository.get_run(automation_run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    return {
        "project_id": run.project_id,
        "status": run.status,
        "revision": run.revision,
        "active": run.status in {AutomationStatus.QUEUED, AutomationStatus.RUNNING},
    }


@router.post("/luot-chay", status_code=status.HTTP_202_ACCEPTED)
async def create_automation_run(
    payload: AutomationRunRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    _, permissions = await project_access(payload.project_id, token)
    if "automation.create" not in permissions:
        raise HTTPException(status_code=403, detail={"code": "AUTOMATION_CAPABILITY_DENIED"})
    raise HTTPException(
        status_code=410,
        detail={"code": "DIRECT_AUTOMATION_RUN_RETIRED", "replacement": "noi-bo/su-kien"},
    )


@router.get("/luot-chay/{automation_run_id}")
async def get_automation_run(
    automation_run_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _readable_run(automation_run_id, token, user)
    latest_checkpoint = await automation_repository.latest_checkpoint(automation_run_id)
    clarifications = [
        item.model_dump(mode="json")
        for item in (latest_checkpoint.state_snapshot.uncertainties if latest_checkpoint and latest_checkpoint.state_snapshot else [])
    ]
    return {
        "run": run,
        "workflow": await _automation_workflow_snapshot(run),
        "checkpoints": await automation_repository.list_checkpoints(automation_run_id),
        "clarifications": clarifications,
        "receipt": await automation_repository.get_receipt(automation_run_id),
    }


@router.get("/luot-chay/{automation_run_id}/bang-chung")
async def get_automation_evidence(
    automation_run_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    await _readable_run(automation_run_id, token, user)
    return {
        "source_facts": await automation_repository.list_source_facts(automation_run_id),
        "receipt": await automation_repository.get_receipt(automation_run_id),
    }


@router.get("/du-an/{project_id}/luot-chay")
async def list_automation_runs(
    project_id: str,
    limit: int = 50,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    if user.system_role == SystemRole.ADMIN:
        requester_user_id = None
    else:
        _, permissions = await project_access(project_id, token)
        if "proposal.read" in permissions:
            requester_user_id = None
        elif "automation.read" in permissions:
            requester_user_id = user.id
        else:
            raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
    runs = await automation_repository.list_runs(
        project_id,
        max(1, min(limit, 100)),
        requester_user_id=requester_user_id,
    )
    payloads = [run.model_dump(mode="json") for run in runs]
    visible_run_count = min(len(runs), 10)
    if visible_run_count:
        workflows = await asyncio.gather(
            *(_automation_workflow_snapshot(run) for run in runs[:visible_run_count])
        )
        for index, workflow in enumerate(workflows):
            payloads[index]["workflow"] = workflow.model_dump(mode="json")
    return payloads


@router.get("/du-an/{project_id}/ho-so-kha-nang-kiem-thu")
async def list_project_testability_blueprints(
    project_id: str,
    limit: int = 50,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    if user.system_role != SystemRole.ADMIN:
        _, permissions = await project_access(project_id, token)
        if "requirement.read" not in permissions:
            raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
    versions = await automation_repository.list_project_blueprints(
        project_id, max(1, min(limit, 100))
    )
    return {
        "project_id": project_id,
        "current_version": versions[0].version if versions else None,
        "versions": versions,
    }


@router.post("/luot-chay/{automation_run_id}/uy-quyen-lai")
async def retry_automation_run(
    automation_run_id: str,
    payload: AutomationRetryRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _controllable_run(automation_run_id, token, user)
    return await automation_service.authorize_retry(run, payload.expected_revision)


@router.post("/luot-chay/{automation_run_id}/tra-loi-lam-ro")
async def answer_automation_clarification(
    automation_run_id: str,
    payload: AutomationClarificationResponseRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await automation_repository.get_run(automation_run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    if user.system_role != SystemRole.ADMIN:
        _, permissions = await project_access(run.project_id, token)
        if "requirement.update" not in permissions:
            raise HTTPException(
                status_code=403,
                detail={"code": "AUTOMATION_CLARIFICATION_PERMISSION_DENIED"},
            )
    updated = await automation_service.provide_clarification(run, payload, user.id)
    return {
        "automation_run_id": updated.automation_run_id,
        "status": updated.status,
        "revision": updated.revision,
        "error_code": updated.error_code,
    }


@router.post("/luot-chay/{automation_run_id}/huy")
async def cancel_automation_run(
    automation_run_id: str,
    payload: AutomationCancelRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _controllable_run(automation_run_id, token, user)
    return await automation_service.cancel(run, payload.expected_revision)

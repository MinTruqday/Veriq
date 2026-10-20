from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependency import get_current_user, oauth2_scheme, verify_internal_token
from src.repositories.automation import automation_repository
from src.schemas.auth import CurrentUser, SystemRole
from src.schemas.automation import (
    AutomationCancelRequest,
    AutomationDefinitionPatch,
    AutomationDefinitionRequest,
    AutomationEventRequest,
    AutomationRetryRequest,
    AutomationRunRequest,
    AutomationStatus,
    AutomationTrigger,
)
from src.services.automation import automation_service
from src.services.project_access import project_access


router = APIRouter(prefix="/tu-dong-hoa-ai", tags=["AI Automation"])


async def _readable_run(run_id: str, token: str, user: CurrentUser):
    run = await automation_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    if run.requester_user_id != user.id and user.system_role != SystemRole.ADMIN:
        _, permissions = await project_access(run.project_id, token)
        if "proposal.read" not in permissions:
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
    if definition.owner_user_id != user.id and user.system_role != SystemRole.ADMIN:
        await project_access(definition.project_id, token)
        raise HTTPException(status_code=403, detail={"code": "AUTOMATION_DEFINITION_CONTROL_DENIED"})
    return definition


@router.post("/dinh-nghia", status_code=status.HTTP_201_CREATED)
async def create_automation_definition(
    payload: AutomationDefinitionRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    role, permissions = await project_access(payload.project_id, token)
    return await automation_service.create_definition(payload, user.id, role, permissions)


@router.get("/triggers")
async def list_automation_triggers():
    return [trigger.value for trigger in AutomationTrigger]


@router.get("/du-an/{project_id}/dinh-nghia")
async def list_automation_definitions(
    project_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    await project_access(project_id, token)
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


@router.post("/noi-bo/su-kien", dependencies=[Depends(verify_internal_token)])
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
    return {"runs": runs}


@router.post("/luot-chay", status_code=status.HTTP_202_ACCEPTED)
async def create_automation_run(
    payload: AutomationRunRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    role, permissions = await project_access(payload.project_id, token)
    return await automation_service.create(payload, user.id, role, permissions)


@router.get("/luot-chay/{automation_run_id}")
async def get_automation_run(
    automation_run_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _readable_run(automation_run_id, token, user)
    return {
        "run": run,
        "checkpoints": await automation_repository.list_checkpoints(automation_run_id),
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
    await project_access(project_id, token)
    return await automation_repository.list_runs(project_id, max(1, min(limit, 100)))


@router.post("/luot-chay/{automation_run_id}/uy-quyen-lai")
async def retry_automation_run(
    automation_run_id: str,
    payload: AutomationRetryRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _controllable_run(automation_run_id, token, user)
    return await automation_service.authorize_retry(run, payload.expected_revision)


@router.post("/luot-chay/{automation_run_id}/huy")
async def cancel_automation_run(
    automation_run_id: str,
    payload: AutomationCancelRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _controllable_run(automation_run_id, token, user)
    return await automation_service.cancel(run, payload.expected_revision)

from fastapi import APIRouter, Depends, HTTPException

from src.core.dependency import get_current_user, oauth2_scheme, verify_internal_token
from src.repositories.ai_runs import ai_run_repository
from src.schemas.agent import AIRunRequest, RequirementDocumentRunRequest
from src.schemas.auth import CurrentUser, SystemRole
from src.schemas.ai_runs import (
    AIRunCancelRequest,
    AIRunAcceptedResponse,
    AIRunRetryRequest,
    AIRunStatus,
)
from src.services.ai_runs import ai_run_service
from src.services.agent_evidence import verified_tool_evidence
from src.services.project_access import project_access
from src.tools.registry import agent_available_tools, tool_access

router = APIRouter(prefix="/tac-nhan-ai", tags=["AI Runs"])


@router.get("/du-an/{project_id}/nang-luc")
async def list_ai_run_capabilities(
    project_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    _, permissions = await project_access(project_id, token)
    capabilities = []
    for tool in agent_available_tools(permissions).values():
        access = tool_access(tool)
        if not access:
            continue
        capabilities.append(
            {
                "name": access.name,
                "label": tool.metadata.get("label", access.name),
            }
        )
    return sorted(capabilities, key=lambda item: item["label"])


@router.post("/luot-chay", status_code=201)
async def create_user_ai_run(
    payload: AIRunRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    role, permissions = await project_access(payload.project_id, token)
    if any(item.project_id != payload.project_id for item in payload.evidence):
        raise HTTPException(status_code=422, detail={"code": "AGENT_EVIDENCE_PROJECT_MISMATCH"})
    return await ai_run_service.create_user_run(payload, user.id, role, permissions)


@router.post(
    "/noi-bo/yeu-cau-nhap-tai-lieu",
    dependencies=[Depends(verify_internal_token)],
    status_code=201,
    response_model=AIRunAcceptedResponse,
)
async def create_requirement_document_run(payload: RequirementDocumentRunRequest):
    run = await ai_run_service.create_requirement_document_run(payload)
    return {"status": "accepted", "runs": [run]}


async def _readable_run(run_id: str, token: str, user: CurrentUser):
    run = await ai_run_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    if user.system_role == SystemRole.ADMIN:
        return run
    _, permissions = await project_access(run.project_id, token)
    can_read_project_runs = "proposal.read" in permissions
    can_read_own_run = (
        run.requester_user_id == user.id and "requirement.read" in permissions
    )
    if not can_read_project_runs and not can_read_own_run:
        raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
    return run


async def _controllable_run(run_id: str, token: str, user: CurrentUser):
    run = await _readable_run(run_id, token, user)
    if run.requester_user_id != user.id and user.system_role != SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail={"code": "AI_RUN_CONTROL_DENIED"})
    return run


@router.post(
    "/noi-bo/tai-lieu-yeu-cau/{document_id}/huy-luot-chay",
    dependencies=[Depends(verify_internal_token)],
)
async def cancel_requirement_document_runs(document_id: str):
    """Stop queued/retryable ingestion runs when Testing revokes AI-read access."""
    cancelled = await ai_run_service.cancel_document_ingestion_runs(document_id)
    return {"cancelled_run_count": cancelled}


@router.get(
    "/noi-bo/luot-chay/{ai_run_id}/trang-thai-thuc-thi",
    dependencies=[Depends(verify_internal_token)],
)
async def get_internal_run_execution_status(ai_run_id: str):
    run = await ai_run_repository.get_run(ai_run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    return {
        "project_id": run.project_id,
        "status": run.status,
        "revision": run.revision,
        "active": run.status in {AIRunStatus.QUEUED, AIRunStatus.RUNNING},
        "user_requested": (run.constraints or {}).get("user_requested") is True,
        "requester_user_id": run.requester_user_id,
        "execution_user_id": run.execution_user_id,
        "trigger": getattr(run.trigger, "value", run.trigger),
        "intent": run.intent,
    }


@router.get("/luot-chay/{ai_run_id}")
async def get_ai_run(
    ai_run_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _readable_run(ai_run_id, token, user)
    return {
        "run": run,
        "checkpoints": await ai_run_repository.list_checkpoints(ai_run_id),
        "receipt": await ai_run_repository.get_receipt(ai_run_id),
    }


@router.get("/luot-chay/{ai_run_id}/bang-chung")
async def get_ai_run_evidence(
    ai_run_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _readable_run(ai_run_id, token, user)
    evidence_checkpoint = await ai_run_repository.latest_checkpoint_with_evidence(
        ai_run_id
    )
    return {
        "source_facts": await ai_run_repository.list_source_facts(ai_run_id),
        "tool_evidence": verified_tool_evidence(run, evidence_checkpoint),
        "receipt": await ai_run_repository.get_receipt(ai_run_id),
    }


@router.get("/du-an/{project_id}/luot-chay")
async def list_ai_runs(
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
        elif "requirement.read" in permissions:
            requester_user_id = user.id
        else:
            raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"})
    runs = await ai_run_repository.list_runs(
        project_id,
        max(1, min(limit, 100)),
        requester_user_id=requester_user_id,
    )
    return [run.model_dump(mode="json") for run in runs]


@router.post("/luot-chay/{ai_run_id}/uy-quyen-lai")
async def retry_ai_run(
    ai_run_id: str,
    payload: AIRunRetryRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _controllable_run(ai_run_id, token, user)
    return await ai_run_service.authorize_retry(run, payload.expected_revision)


@router.post("/luot-chay/{ai_run_id}/huy")
async def cancel_ai_run(
    ai_run_id: str,
    payload: AIRunCancelRequest,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _controllable_run(ai_run_id, token, user)
    return await ai_run_service.cancel(run, payload.expected_revision)

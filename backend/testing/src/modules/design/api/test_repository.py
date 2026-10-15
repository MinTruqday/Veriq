from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.contracts.design import (
    ReusableStepCreate,
    ReusableStepPatch,
    TestRepositoryNodeCreate,
    TestRepositoryNodePatch,
)
from src.modules.design.services.test_repository import (
    create_repository_node,
    create_reusable_step,
    list_repository_nodes,
    list_reusable_steps,
    update_repository_node,
    update_reusable_step,
)

router = APIRouter(prefix="/kiem-thu", tags=["Kho kiểm thử"])


@router.get("/du-an/{project_id}/kho-ca-kiem-thu")
async def list_repository(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await list_repository_nodes(project_id, user))


@router.post("/du-an/{project_id}/kho-ca-kiem-thu", status_code=201)
async def create_repository(project_id: str, payload: TestRepositoryNodeCreate, user: CurrentUser = Depends(get_current_user)):
    if payload.project_id != project_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail={"code": "PROJECT_SCOPE_MISMATCH"})
    return envelope(await create_repository_node(payload, user), revision=1)


@router.patch("/kho-ca-kiem-thu/{node_id}")
async def update_repository(node_id: str, payload: TestRepositoryNodePatch, user: CurrentUser = Depends(get_current_user)):
    value = await update_repository_node(node_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-an/{project_id}/buoc-dung-lai")
async def list_steps(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await list_reusable_steps(project_id, user))


@router.post("/du-an/{project_id}/buoc-dung-lai", status_code=201)
async def create_step(project_id: str, payload: ReusableStepCreate, user: CurrentUser = Depends(get_current_user)):
    if payload.project_id != project_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail={"code": "PROJECT_SCOPE_MISMATCH"})
    return envelope(await create_reusable_step(payload, user), revision=1)


@router.patch("/buoc-dung-lai/{step_id}")
async def update_step(step_id: str, payload: ReusableStepPatch, user: CurrentUser = Depends(get_current_user)):
    value = await update_reusable_step(step_id, payload, user)
    return envelope(value, revision=value["revision"])

from fastapi import APIRouter, Depends, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.modules.projects.services.work_items import WorkItemService
from src.schemas.contracts.project import (
    PlanningBoardUpdate,
    PlanningWorkflowUpdate,
    ProjectTaskMigrationInput,
    SprintCreate,
    SprintScopePatch,
    SprintTransition,
    WorkItemCreate,
    WorkItemDependencyCreate,
    WorkItemPatch,
    WorkItemRankUpdate,
    WorkItemTransition,
)

router = APIRouter(prefix="/kiem-thu", tags=["Lập kế hoạch dự án"])


@router.get("/du-an/{project_id}/cong-viec")
async def list_work_items(
    project_id: str,
    item_type: str = Query(default="", max_length=30),
    status: str = Query(default="", max_length=30),
    parent_id: str = Query(default="", max_length=200),
    sprint_id: str = Query(default="", max_length=200),
    release_id: str = Query(default="", max_length=200),
    assignee_id: str = Query(default="", max_length=200),
    backlog_only: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await WorkItemService.list_items(project_id, locals(), user))


@router.post("/du-an/{project_id}/cong-viec", status_code=201)
async def create_work_item(project_id: str, payload: WorkItemCreate, user: CurrentUser = Depends(get_current_user)):
    value = await WorkItemService.create_item(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-an/{project_id}/cong-viec/migrate-project-task/preview")
async def preview_project_task_migration(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await WorkItemService.preview_project_task_migration(project_id, user))


@router.post("/du-an/{project_id}/cong-viec/migrate-project-task")
async def migrate_project_tasks(
    project_id: str,
    payload: ProjectTaskMigrationInput,
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await WorkItemService.migrate_project_tasks(project_id, payload, user))


@router.patch("/du-an/{project_id}/cong-viec/{item_id}")
async def update_work_item(project_id: str, item_id: str, payload: WorkItemPatch, user: CurrentUser = Depends(get_current_user)):
    value = await WorkItemService.update_item(project_id, item_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/du-an/{project_id}/cong-viec/{item_id}/xep-hang")
async def rank_work_item(project_id: str, item_id: str, payload: WorkItemRankUpdate, user: CurrentUser = Depends(get_current_user)):
    value = await WorkItemService.rank_item(project_id, item_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/du-an/{project_id}/cong-viec/{item_id}/chuyen-trang-thai")
async def transition_work_item(project_id: str, item_id: str, payload: WorkItemTransition, user: CurrentUser = Depends(get_current_user)):
    value = await WorkItemService.transition_item(project_id, item_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/du-an/{project_id}/cong-viec/{item_id}/phu-thuoc", status_code=201)
async def create_work_item_dependency(project_id: str, item_id: str, payload: WorkItemDependencyCreate, user: CurrentUser = Depends(get_current_user)):
    return envelope(await WorkItemService.create_dependency(project_id, item_id, payload, user))


@router.get("/du-an/{project_id}/bang-cong-viec")
async def work_board(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await WorkItemService.board(project_id, user))


@router.patch("/du-an/{project_id}/bang-cong-viec")
async def update_work_board(project_id: str, payload: PlanningBoardUpdate, user: CurrentUser = Depends(get_current_user)):
    value = await WorkItemService.update_board(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/du-an/{project_id}/quy-trinh-cong-viec")
async def update_workflow(project_id: str, payload: PlanningWorkflowUpdate, user: CurrentUser = Depends(get_current_user)):
    value = await WorkItemService.update_workflow(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-an/{project_id}/lo-trinh")
async def roadmap(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await WorkItemService.roadmap(project_id, user))


@router.get("/du-an/{project_id}/sprint")
async def list_sprints(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await WorkItemService.list_sprints(project_id, user))


@router.post("/du-an/{project_id}/sprint", status_code=201)
async def create_sprint(project_id: str, payload: SprintCreate, user: CurrentUser = Depends(get_current_user)):
    value = await WorkItemService.create_sprint(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/du-an/{project_id}/sprint/{sprint_id}/pham-vi")
async def patch_sprint_scope(project_id: str, sprint_id: str, payload: SprintScopePatch, user: CurrentUser = Depends(get_current_user)):
    value = await WorkItemService.patch_sprint_scope(project_id, sprint_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/du-an/{project_id}/sprint/{sprint_id}/chuyen-trang-thai")
async def transition_sprint(project_id: str, sprint_id: str, payload: SprintTransition, user: CurrentUser = Depends(get_current_user)):
    value = await WorkItemService.transition_sprint(project_id, sprint_id, payload, user)
    return envelope(value, revision=value["revision"])

from fastapi import APIRouter, Depends, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.contracts.environment import (
    BuildCreate,
    BuildPatch,
    EnvironmentCreate,
    EnvironmentPatch,
    EnvironmentSecretRefs,
    ReleaseCreate,
    ReleasePatch,
    ReleaseTransition,
)
from src.modules.execution.services.execution_context import ExecutionContextService

router = APIRouter(prefix="/kiem-thu", tags=["Ngữ cảnh thực thi kiểm thử"])


@router.get("/du-an/{project_id}/ban-phat-hanh", openapi_extra={"x-function-ids": ["REL-01"]})
async def list_releases(
    project_id: str,
    status: str = Query(default="", max_length=30),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await ExecutionContextService.list_releases(project_id, status, user))


@router.get("/ban-phat-hanh/{release_id}", openapi_extra={"x-function-ids": ["REL-02"]})
async def get_release(release_id: str, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.get_release(release_id, user)
    return envelope(value, revision=value["revision"])


@router.get("/ban-phat-hanh/{release_id}/san-sang-dong", openapi_extra={"x-function-ids": ["REL-08"]})
async def release_close_readiness(release_id: str, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.release_close_readiness(release_id, user)
    return envelope(value.model_dump(), revision=value.revision)


@router.post("/du-an/{project_id}/ban-phat-hanh", status_code=201, openapi_extra={"x-function-ids": ["REL-03"]})
async def create_release(project_id: str, payload: ReleaseCreate, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.create_release(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/ban-phat-hanh/{release_id}", openapi_extra={"x-function-ids": ["REL-04"]})
async def update_release(release_id: str, payload: ReleasePatch, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.update_release(release_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/ban-phat-hanh/{release_id}/kich-hoat", openapi_extra={"x-function-ids": ["REL-05"]})
async def activate_release(release_id: str, payload: ReleaseTransition, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.transition_release(
        release_id, payload, user, "activate"
    )
    return envelope(value, revision=value["revision"])


@router.post("/ban-phat-hanh/{release_id}/dong", openapi_extra={"x-function-ids": ["REL-06"]})
async def close_release(release_id: str, payload: ReleaseTransition, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.transition_release(
        release_id, payload, user, "close"
    )
    return envelope(value, revision=value["revision"])


@router.post("/ban-phat-hanh/{release_id}/luu-tru", openapi_extra={"x-function-ids": ["REL-07"]})
async def archive_release(release_id: str, payload: ReleaseTransition, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.transition_release(
        release_id, payload, user, "archive"
    )
    return envelope(value, revision=value["revision"])


@router.get("/du-an/{project_id}/ban-dung", openapi_extra={"x-function-ids": ["BLD-01"]})
async def list_builds(
    project_id: str,
    release_id: str = Query(default="", max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await ExecutionContextService.list_builds(project_id, release_id, user))


@router.get("/ban-dung/{build_id}", openapi_extra={"x-function-ids": ["BLD-01"]})
async def get_build(build_id: str, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.get_build(build_id, user)
    return envelope(value, revision=value["revision"])


@router.post("/du-an/{project_id}/ban-dung", status_code=201, openapi_extra={"x-function-ids": ["BLD-02"]})
async def create_build(project_id: str, payload: BuildCreate, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.create_build(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/ban-dung/{build_id}", openapi_extra={"x-function-ids": ["BLD-02"]})
async def update_build(build_id: str, payload: BuildPatch, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.update_build(build_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/ban-dung/{build_id}/dat-hien-tai", openapi_extra={"x-function-ids": ["BLD-03"]})
async def set_current_build(build_id: str, payload: ReleaseTransition, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.set_current_build(build_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-an/{project_id}/moi-truong", openapi_extra={"x-function-ids": ["ENV-01"]})
async def list_environments(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await ExecutionContextService.list_environments(project_id, user))


@router.get("/moi-truong/{environment_id}", openapi_extra={"x-function-ids": ["ENV-01"]})
async def get_environment(environment_id: str, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.get_environment(environment_id, user)
    return envelope(value, revision=value["revision"])


@router.post("/du-an/{project_id}/moi-truong", status_code=201, openapi_extra={"x-function-ids": ["ENV-02"]})
async def create_environment(project_id: str, payload: EnvironmentCreate, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.create_environment(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/moi-truong/{environment_id}", openapi_extra={"x-function-ids": ["ENV-03"]})
async def update_environment(environment_id: str, payload: EnvironmentPatch, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.update_environment(environment_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/moi-truong/{environment_id}/bi-mat", openapi_extra={"x-function-ids": ["ENV-04"]})
async def update_environment_secrets(environment_id: str, payload: EnvironmentSecretRefs, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.update_environment_secrets(environment_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.post("/moi-truong/{environment_id}/luu-tru", openapi_extra={"x-function-ids": ["ENV-05"]})
async def archive_environment(environment_id: str, payload: ReleaseTransition, user: CurrentUser = Depends(get_current_user)):
    value = await ExecutionContextService.archive_environment(environment_id, payload, user)
    return envelope(value, revision=value["revision"])

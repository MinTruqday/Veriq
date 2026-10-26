from fastapi import APIRouter, Depends

from src.core.dependency import verify_internal_token
from src.schemas.project import ProjectArtifactIndexRequest, ProjectKnowledgeSearchRequest
from src.services.project_knowledge import (
    index_project_artifact,
    list_project_artifact_chunks,
    remove_project_artifact,
    search_project_knowledge,
)

router = APIRouter(dependencies=[Depends(verify_internal_token)])


@router.post(
    "/du-an/{project_id}/doi-tuong",
    description="Chỉ mục hóa artifact trong phạm vi Project",
)
async def index_artifact(project_id: str, req: ProjectArtifactIndexRequest):
    return await index_project_artifact(project_id, req)


@router.delete("/du-an/{project_id}/doi-tuong/{artifact_version_id}")
async def remove_artifact(project_id: str, artifact_version_id: str):
    return await remove_project_artifact(project_id, artifact_version_id)


@router.get("/du-an/{project_id}/doi-tuong/{artifact_version_id}/cac-doan")
async def list_artifact_chunks(
    project_id: str,
    artifact_version_id: str,
    limit: int = 50,
    cursor: str | None = None,
):
    return await list_project_artifact_chunks(
        project_id, artifact_version_id, limit, cursor
    )


@router.post(
    "/du-an/{project_id}/tim-kiem",
    description="Tìm evidence knowledge theo phạm vi Project",
)
async def search_knowledge(project_id: str, req: ProjectKnowledgeSearchRequest):
    return await search_project_knowledge(project_id, req)

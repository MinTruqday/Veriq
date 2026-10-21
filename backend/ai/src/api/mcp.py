from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.dependency import get_current_user, oauth2_scheme, require_system_admin
from src.repositories.mcp import mcp_repository
from src.schemas.auth import CurrentUser
from src.schemas.mcp import MCPConnection, MCPConnectionCreate, MCPConnectionPatch
from src.tools.mcp_gateway import probe_connection


router = APIRouter(prefix="/mcp", tags=["MCP Gateway"])


@router.post("/ket-noi", status_code=201)
async def create_mcp_connection(
    payload: MCPConnectionCreate,
    user: CurrentUser = Depends(require_system_admin),
):
    connection = MCPConnection(
        project_id=payload.project_id,
        name=payload.name,
        endpoint=str(payload.endpoint),
        credential_environment_variable=payload.credential_environment_variable,
        allowed_read_tools=payload.allowed_read_tools,
        created_by=user.id,
    )
    try:
        return await mcp_repository.create(connection)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail={"code": "MCP_CONNECTION_EXISTS"}) from error


@router.get("/du-an/{project_id}/ket-noi")
async def list_mcp_connections(
    project_id: str,
    token: str = Depends(oauth2_scheme),
    user: CurrentUser = Depends(get_current_user),
):
    # Connection credentials are never returned by this endpoint; access is scoped to project membership.
    from src.services.project_access import project_access

    await project_access(project_id, token)
    values = await mcp_repository.list_project(project_id)
    return [
        item.model_dump(mode="json", exclude={"credential_environment_variable"})
        for item in values
    ]


@router.patch("/ket-noi/{connection_id}")
async def update_mcp_connection(
    connection_id: str,
    payload: MCPConnectionPatch,
    user: CurrentUser = Depends(require_system_admin),
):
    current = await mcp_repository.get(connection_id)
    if not current:
        raise HTTPException(status_code=404, detail={"code": "MCP_CONNECTION_NOT_FOUND"})
    values = payload.model_dump(exclude={"expected_revision"}, exclude_unset=True)
    if "endpoint" in values:
        values["endpoint"] = str(values["endpoint"])
    updated = await mcp_repository.patch(
        connection_id, payload.expected_revision, values
    )
    if not updated:
        latest = await mcp_repository.get(connection_id)
        raise HTTPException(
            status_code=409,
            detail={"code": "REVISION_CONFLICT", "latest": latest.model_dump(mode="json") if latest else None},
        )
    return updated.model_dump(mode="json", exclude={"credential_environment_variable"})


@router.post("/ket-noi/{connection_id}/kiem-tra")
async def test_mcp_connection(
    connection_id: str,
    user: CurrentUser = Depends(require_system_admin),
):
    connection = await mcp_repository.get(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail={"code": "MCP_CONNECTION_NOT_FOUND"})
    result = await probe_connection(connection)
    return {
        "connection_id": connection.connection_id,
        "name": connection.name,
        **result,
    }

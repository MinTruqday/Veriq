from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.contracts.automation import JUnitUnresolvedMappingInput
from src.modules.integrations.services.junit_import import (
    import_junit_result,
    list_junit_imports,
    resolve_junit_unresolved_mapping,
)

router = APIRouter(prefix="/kiem-thu", tags=["Kết quả tự động"])


@router.get("/du-an/{project_id}/ket-qua-tu-dong/junit")
async def list_junit(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await list_junit_imports(project_id, user))


@router.post("/du-an/{project_id}/ket-qua-tu-dong/junit", status_code=201)
async def import_junit(project_id: str, test_run_id: str = Form(...), file: UploadFile = File(...), user: CurrentUser = Depends(get_current_user)):
    content = (await file.read()).decode("utf-8", errors="replace")
    return envelope(await import_junit_result(project_id, test_run_id, content, user))


@router.post("/ket-qua-tu-dong/junit/{import_id}/giai-quyet")
async def resolve_junit(
    import_id: str,
    payload: JUnitUnresolvedMappingInput,
    user: CurrentUser = Depends(get_current_user),
):
    value = await resolve_junit_unresolved_mapping(import_id, payload, user)
    return envelope(value, revision=value["revision"])

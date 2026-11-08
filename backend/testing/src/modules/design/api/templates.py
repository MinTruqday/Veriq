from fastapi import APIRouter, Depends, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.test_case_template import (
    TestCaseTemplateArchive,
    TestCaseTemplateCreate,
    TestCaseTemplatePatch,
)
from src.modules.design.services.test_case_template import TestCaseTemplateService


router = APIRouter(prefix="/kiem-thu", tags=["Mẫu ca kiểm thử"])


@router.get("/du-an/{project_id}/mau-ca-kiem-thu", openapi_extra={"x-function-ids": ["TPLT-01"]})
async def list_templates(
    project_id: str,
    template_type: str | None = Query(default=None, max_length=100),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await TestCaseTemplateService.list(project_id, template_type, user))


@router.get("/mau-ca-kiem-thu/{template_id}", openapi_extra={"x-function-ids": ["TPLT-01"]})
async def get_template(template_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await TestCaseTemplateService.get(template_id, user))


@router.post(
    "/du-an/{project_id}/mau-ca-kiem-thu",
    status_code=201,
    openapi_extra={"x-function-ids": ["TPLT-02"]},
)
async def create_template(
    project_id: str, payload: TestCaseTemplateCreate, user: CurrentUser = Depends(get_current_user)
):
    template = await TestCaseTemplateService.create(project_id, payload, user)
    return envelope(template, revision=1)


@router.patch("/mau-ca-kiem-thu/{template_id}", openapi_extra={"x-function-ids": ["TPLT-02"]})
async def update_template(
    template_id: str, payload: TestCaseTemplatePatch, user: CurrentUser = Depends(get_current_user)
):
    updated = await TestCaseTemplateService.update(template_id, payload, user)
    return envelope(updated, revision=updated["revision"])


@router.post(
    "/mau-ca-kiem-thu/{template_id}/luu-tru", openapi_extra={"x-function-ids": ["TPLT-03"]}
)
async def archive_template(
    template_id: str,
    payload: TestCaseTemplateArchive,
    user: CurrentUser = Depends(get_current_user),
):
    updated = await TestCaseTemplateService.archive(template_id, payload, user)
    return envelope(updated, revision=updated["revision"])

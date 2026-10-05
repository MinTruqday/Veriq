from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope, get_project
from src.modules.requirements.services.requirement_templates import (
    approve_publication,
    consent_publication,
    create_custom_field,
    create_template,
    get_template_version,
    list_custom_fields,
    list_templates,
    list_template_versions,
    preview_template,
    request_publication,
    review_template,
    synthesize_template,
    update_template,
    visible_template,
)
from src.schemas.contracts.requirements import (
    RequirementCustomFieldCreate,
    RequirementTemplateConsent,
    RequirementTemplateCreate,
    RequirementTemplatePublish,
    RequirementTemplateSynthesis,
    RequirementTemplateUpdate,
)


router = APIRouter(prefix="/kiem-thu", tags=["Mẫu yêu cầu"])


@router.get("/du-an/{project_id}/mau-yeu-cau")
async def list_requirement_templates(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await list_templates(project_id, user))


@router.get("/du-an/{project_id}/mau-yeu-cau/{template_id}")
async def get_requirement_template(project_id: str, template_id: str, user: CurrentUser = Depends(get_current_user)):
    await get_project(project_id, user, "requirement.read")
    return envelope(await visible_template(template_id, project_id, user))


@router.get("/du-an/{project_id}/mau-yeu-cau/{template_id}/phien-ban")
async def list_requirement_template_versions(project_id: str, template_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await list_template_versions(project_id, template_id, user))


@router.get("/du-an/{project_id}/mau-yeu-cau/{template_id}/phien-ban/{version}")
async def get_requirement_template_version(project_id: str, template_id: str, version: int, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_template_version(project_id, template_id, version, user))


@router.post("/du-an/{project_id}/mau-yeu-cau", status_code=201)
async def create_requirement_template(project_id: str, payload: RequirementTemplateCreate, user: CurrentUser = Depends(get_current_user)):
    return envelope(await create_template(project_id, payload, user))


@router.put("/du-an/{project_id}/mau-yeu-cau/{template_id}")
async def update_requirement_template(project_id: str, template_id: str, payload: RequirementTemplateUpdate, user: CurrentUser = Depends(get_current_user)):
    return envelope(await update_template(project_id, template_id, payload, user))


@router.post("/du-an/{project_id}/mau-yeu-cau/tong-hop", status_code=201)
async def synthesize_requirement_template(project_id: str, payload: RequirementTemplateSynthesis, user: CurrentUser = Depends(get_current_user)):
    return envelope(await synthesize_template(project_id, payload, user))


@router.post("/du-an/{project_id}/mau-yeu-cau/{template_id}/xem-truoc", status_code=201)
async def preview_requirement_template(project_id: str, template_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await preview_template(project_id, template_id, user))


@router.post("/du-an/{project_id}/mau-yeu-cau/{template_id}/ai/kiem-tra")
async def review_requirement_template(project_id: str, template_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await review_template(project_id, template_id, user))


@router.get("/du-an/{project_id}/truong-yeu-cau")
async def list_requirement_fields(project_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await list_custom_fields(project_id, user))


@router.post("/du-an/{project_id}/truong-yeu-cau", status_code=201)
async def create_requirement_field(project_id: str, payload: RequirementCustomFieldCreate, user: CurrentUser = Depends(get_current_user)):
    return envelope(await create_custom_field(project_id, payload, user))


@router.post("/du-an/{project_id}/mau-yeu-cau/{template_id}/de-nghi-phat-hanh")
async def request_requirement_template_publication(project_id: str, template_id: str, payload: RequirementTemplatePublish, user: CurrentUser = Depends(get_current_user)):
    return envelope(await request_publication(project_id, template_id, payload, user))


@router.post("/du-an/{project_id}/mau-yeu-cau/{template_id}/dong-y")
async def consent_requirement_template_publication(project_id: str, template_id: str, payload: RequirementTemplateConsent, user: CurrentUser = Depends(get_current_user)):
    return envelope(await consent_publication(project_id, template_id, payload, user))


@router.post("/du-an/{project_id}/mau-yeu-cau/{template_id}/duyet-phat-hanh")
async def approve_requirement_template_publication(project_id: str, template_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await approve_publication(project_id, template_id, user))

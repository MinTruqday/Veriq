from collections.abc import Sequence

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.auth import CurrentUser
from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    load_user_identities,
    new_id,
    now,
)
from src.repositories.test_design import test_design_repository
from src.schemas.test_case_template import (
    TemplateType,
    TestCaseTemplateArchive,
    TestCaseTemplateCreate,
    TestCaseTemplatePatch,
)





class TestCaseTemplateService:
    @staticmethod
    async def list(project_id: str, template_type: TemplateType | None, user: CurrentUser):
        await get_project(project_id, user, 'testcase.template.read')
        query = {"project_id": project_id, "status": 'ACTIVE'}
        if template_type:
            query["template_type"] = template_type
        items = await test_design_repository.list_templates(query)
        await TestCaseTemplateService._add_creator_labels(items)
        return items

    @staticmethod
    async def get(template_id: str, user: CurrentUser):
        item = await get_project_entity(
            'test_case_templates',
            template_id,
            user,
            'testcase.template.read',
        )
        await TestCaseTemplateService._add_creator_labels([item])
        return item

    @staticmethod
    async def create(
        project_id: str,
        payload: TestCaseTemplateCreate,
        user: CurrentUser,
    ):
        await get_project(project_id, user, 'testcase.template.manage')
        timestamp = now()
        template = {
            "_id": new_id('TPL'),
            "project_id": project_id,
            **payload.model_dump(),
            "status": 'ACTIVE',
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await test_design_repository.insert_template(template)
        except DuplicateKeyError as error:
            raise HTTPException(
                status_code=409, detail={"code": 'TEMPLATE_NAME_EXISTS'}
            ) from error
        await audit(
            user.id,
            'test_case_template_created',
            'TestCaseTemplate',
            template["_id"],
            project_id,
        )
        return template

    @staticmethod
    async def update(
        template_id: str,
        payload: TestCaseTemplatePatch,
        user: CurrentUser,
    ):
        template = await get_project_entity(
            'test_case_templates',
            template_id,
            user,
            'testcase.template.manage',
        )
        if template.get("status") != 'ACTIVE':
            raise HTTPException(
                status_code=409, detail={"code": 'TEMPLATE_ARCHIVED'}
            )
        changes = payload.model_dump(exclude={"expected_revision"}, exclude_none=True)
        updated = await test_design_repository.update_template(
            template_id,
            template["project_id"],
            payload.expected_revision,
            'ACTIVE',
            {**changes, "updated_at": now()},
        )
        if not updated:
            raise HTTPException(
                status_code=409, detail={"code": 'REVISION_CONFLICT'}
            )
        await audit(
            user.id,
            'test_case_template_updated',
            'TestCaseTemplate',
            template_id,
            template["project_id"],
        )
        return updated

    @staticmethod
    async def archive(
        template_id: str,
        payload: TestCaseTemplateArchive,
        user: CurrentUser,
    ):
        template = await get_project_entity(
            'test_case_templates',
            template_id,
            user,
            'testcase.template.manage',
        )
        if template.get("status") == 'ARCHIVED':
            return template
        updated = await test_design_repository.update_template(
            template_id,
            template["project_id"],
            payload.expected_revision,
            'ACTIVE',
            {
                "status": 'ARCHIVED',
                "archive_reason": payload.reason,
                "updated_at": now(),
            },
        )
        if not updated:
            raise HTTPException(
                status_code=409, detail={"code": 'REVISION_CONFLICT'}
            )
        await audit(
            user.id,
            'test_case_template_archived',
            'TestCaseTemplate',
            template_id,
            template["project_id"],
            {"reason": payload.reason},
        )
        return updated

    @staticmethod
    async def _add_creator_labels(items: Sequence[dict]):
        identities = await load_user_identities(item.get("created_by") for item in items)
        for item in items:
            identity = identities.get(str(item.get("created_by")))
            item["created_by_label"] = identity.get("label") if identity else item.get("created_by")

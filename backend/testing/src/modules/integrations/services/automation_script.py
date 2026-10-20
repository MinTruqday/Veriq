import json
import re

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, get_project_entity, new_id, now, optimistic_patch
from src.repositories.execution_asset import execution_asset_repository
from src.core.ai_automation import ai_contract_metadata, request_ai_automation






def validate_source(source):
    if re.search('(password|secret|token|api[_-]?key)(\\s*[:=]\\s*)[\'\\"](?!\\$\\{|<|Đã ẩn)[^\'\\"]{4,}[\'\\"]', source, re.I):
        raise HTTPException(
            status_code=422,
            detail={"code": 'RAW_SECRET_IN_SCRIPT'},
        )
    return source


def generated_script(result):
    if result.get("status") != 'SUCCESS' or result.get(
        "degraded_mode"
    ):
        raise HTTPException(
            503,
            detail={
                "code": 'AI_PROVIDER_UNAVAILABLE',
                "retryable": True,
            },
        )
    suggestions = result.get("suggestions")
    if (
        not isinstance(suggestions, list)
        or len(suggestions) != 1
        or not isinstance(suggestions[0], dict)
    ):
        raise HTTPException(
            502,
            detail={"code": 'AI_SCRIPT_INVALID'},
        )
    source = suggestions[0].get("source")
    placeholders = suggestions[0].get("secret_placeholders", [])
    if (
        not isinstance(source, str)
        or not source.strip()
        or len(source) > int(100000)
        or source.lstrip().startswith('```')
    ):
        raise HTTPException(
            502,
            detail={"code": 'AI_SCRIPT_INVALID'},
        )
    if not isinstance(placeholders, list) or any(
        not isinstance(item, str)
        or not re.fullmatch('[A-Z][A-Z0-9_]{0,99}', item)
        for item in placeholders
    ):
        raise HTTPException(
            502,
            detail={"code": 'AI_SCRIPT_PLACEHOLDERS_INVALID'},
        )
    return validate_source(source), list(dict.fromkeys(placeholders))


def default_filename(framework, language, version):
    key = re.sub(
        '[^A-Za-z0-9_-]+',
        "-",
        str(version.get("test_case_key") or 'test-case'),
    )
    suffix = {'typescript': 'spec.ts', 'javascript': 'spec.js', 'python': 'py'}[language]
    return f"{key.lower()}.{framework}.{suffix}"


class AutomationScriptService:
    @staticmethod
    async def list(project_id, user):
        await get_project(project_id, user, 'automation.script.export')
        return await execution_asset_repository.list_script_drafts(project_id)

    @staticmethod
    async def get(draft_id, user):
        return await get_project_entity(
            'automation_script_drafts',
            draft_id,
            user,
            'automation.script.export',
        )

    @staticmethod
    async def generate(project_id, payload, user):
        await get_project(project_id, user, 'ai.generate_automation_script')
        existing = await execution_asset_repository.find_script_by_idempotency_key(
            project_id, payload.idempotency_key
        )
        if existing:
            return existing, {}
        version = await execution_asset_repository.find_test_case_version(
            project_id, payload.test_case_version_id
        )
        if not version:
            raise HTTPException(
                status_code=422,
                detail={"code": 'INVALID_TEST_CASE_VERSION'},
            )
        evidence = [
            {
                "artifact_type": 'test_case_version',
                "artifact_id": version.get("test_case_id"),
                "artifact_version_id": version["_id"],
                "authority": 'PROJECT_APPROVED_TEST',
                "text": " ".join(
                    [str(version.get("title") or ""), str(version.get("plain_text_projection") or "")]
                )[: int(4000)],
            }
        ]
        ai_result = await request_ai_automation(
            'automation_script_generation',
            project_id,
            json.dumps(
                {"framework": payload.framework, "language": payload.language},
                ensure_ascii=False,
            ),
            evidence
            + (
                [
                    {
                        "artifact_type": 'user_context',
                        "text": payload.context,
                    }
                ]
                if payload.context
                else []
            ),
        )
        source, placeholders = generated_script(ai_result)
        timestamp = now()
        ai_contract = ai_contract_metadata(ai_result)
        value = {
            "_id": new_id('AUTOSCR'),
            "project_id": project_id,
            "test_case_version_id": version["_id"],
            "test_case_id": version.get("test_case_id"),
            "test_case_key": version.get("test_case_key"),
            "framework": payload.framework,
            "language": payload.language,
            "filename": default_filename(payload.framework, payload.language, version),
            "source": source,
            "secret_placeholders": placeholders,
            "model_suggestions": ai_result.get("suggestions", []),
            **ai_contract,
            "ai_contract": ai_contract,
            "ai_status": ai_contract["status"],
            "generation_status": ai_result.get(
                "status", 'SUCCESS'
            ),
            "status": 'DRAFT',
            "candidate_only": True,
            "repository_write_performed": False,
            "human_confirmation_required": True,
            "idempotency_key": payload.idempotency_key,
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await execution_asset_repository.insert_script_draft(value)
        except DuplicateKeyError:
            existing = await execution_asset_repository.find_script_by_idempotency_key(
                project_id, payload.idempotency_key
            )
            if existing:
                return existing, {}
            raise
        await audit(
            user.id,
            'automation_script_draft_generated',
            'AutomationScriptDraft',
            value["_id"],
            project_id,
            {"framework": payload.framework, "test_case_version_id": version["_id"]},
        )
        return value, {
            "status": ai_result.get("status", 'SUCCESS'),
            "degraded_mode": ai_result.get("degraded_mode"),
        }

    @staticmethod
    async def update(draft_id, payload, user):
        draft = await get_project_entity(
            'automation_script_drafts',
            draft_id,
            user,
            'automation.script.update',
        )
        if draft.get("status") != 'DRAFT':
            raise HTTPException(
                status_code=409,
                detail={"code": 'AUTOMATION_SCRIPT_NOT_DRAFT'},
            )
        changes = payload.model_dump(exclude_unset=True)
        if payload.source is not None:
            changes["source"] = validate_source(payload.source)
        updated = await optimistic_patch(
            'automation_script_drafts',
            draft_id,
            draft["project_id"],
            payload.expected_revision,
            changes,
        )
        await audit(
            user.id,
            'automation_script_draft_updated',
            'AutomationScriptDraft',
            draft_id,
            draft["project_id"],
        )
        return updated

    @staticmethod
    async def approve(draft_id, payload, user):
        draft = await get_project_entity(
            'automation_script_drafts',
            draft_id,
            user,
            'automation.script.approve',
        )
        if draft.get("status") != 'DRAFT':
            raise HTTPException(
                status_code=409,
                detail={"code": 'AUTOMATION_SCRIPT_NOT_DRAFT'},
            )
        validate_source(draft["source"])
        updated = await optimistic_patch(
            'automation_script_drafts',
            draft_id,
            draft["project_id"],
            payload.expected_revision,
            {
                "status": 'APPROVED',
                "review_note": payload.review_note,
                "approved_by": user.id,
                "approved_at": now(),
                "human_confirmation_required": False,
            },
        )
        await audit(
            user.id,
            'automation_script_draft_approved',
            'AutomationScriptDraft',
            draft_id,
            draft["project_id"],
            {"review_note": payload.review_note},
        )
        return updated

    @staticmethod
    async def export(draft_id, user):
        draft = await get_project_entity(
            'automation_script_drafts',
            draft_id,
            user,
            'automation.script.export',
        )
        if draft.get("status") != 'APPROVED':
            raise HTTPException(
                status_code=409,
                detail={"code": 'AUTOMATION_SCRIPT_NOT_APPROVED'},
            )
        source = validate_source(draft["source"])
        await audit(
            user.id,
            'automation_script_exported',
            'AutomationScriptDraft',
            draft_id,
            draft["project_id"],
            {"filename": draft["filename"]},
        )
        return source, draft["filename"]

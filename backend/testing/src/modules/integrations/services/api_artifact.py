import hashlib
import json

from fastapi import HTTPException

from src.core.auth import CurrentUser
from src.core.common import audit, envelope, get_project, get_project_entity, new_id, now
from src.core.rich_text import text_document
from src.schemas.contracts.design import TestCaseDraftCreate
from src.schemas.contracts.requirements import (
    APIArtifactArchive,
    APIArtifactConfirm,
    APIArtifactImpact,
    APIArtifactReview,
    ImportCreate,
)
from src.modules.integrations.services.api_artifact_formats import (
    api_case_blueprints,
    operation_fingerprint,
    operation_identity,
    parse_openapi,
    parse_postman,
    public_api_import,
    sanitize,
    sanitize_postman,
)
from src.repositories.api_artifact import api_artifact_repository
from src.modules.design.services.test_case_transfer import (
    confirm_test_import,
    export_test_cases,
    preview_test_import,
    recover_trace_links,
    store_test_import_preview,
    upload_test_import,
)



__all__ = [
    "confirm_test_import",
    "export_test_cases",
    "preview_test_import",
    "recover_trace_links",
    "upload_test_import",
]


async def list_api_artifacts(
    project_id: str,
    status: str | None,
    user: CurrentUser,
):
    await get_project(project_id, user, 'apiartifact.read')
    query = {"project_id": project_id}
    if status:
        query["status"] = status
    items = await api_artifact_repository.list_imports(
        query, 5000, ("created_at", -1)
    )
    return envelope([public_api_import(item) for item in items])


async def get_api_artifact(artifact_id: str, user: CurrentUser):
    artifact = await get_project_entity('api_imports', artifact_id, user, 'apiartifact.read')
    operations = []
    if artifact.get("status") == 'CONFIRMED':
        operations = await api_artifact_repository.list_operations(
            {"project_id": artifact["project_id"], "import_id": artifact_id},
            5000,
            ("path", 1),
        )
    return envelope(
        {**public_api_import(artifact, include_preview=True), "operations": operations},
        revision=artifact.get("revision", 1),
    )


async def import_api_artifact(
    project_id: str, payload: ImportCreate, user: CurrentUser
):
    await get_project(project_id, user, 'apiartifact.import')
    if payload.format not in set(['openapi', 'postman']):
        raise HTTPException(status_code=422, detail={"code": 'API_ARTIFACT_REQUIRED'})
    try:
        value = json.loads(payload.content) if isinstance(payload.content, str) else payload.content
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=422, detail={"code": 'API_ARTIFACT_JSON_INVALID'}
        ) from error
    if not isinstance(value, dict):
        raise HTTPException(status_code=422, detail={"code": 'API_ARTIFACT_OBJECT_REQUIRED'})
    operations = (
        parse_postman(value)
        if payload.format == 'postman'
        else parse_openapi(value)
    )
    if not operations:
        raise HTTPException(status_code=422, detail={"code": 'API_ARTIFACT_HAS_NO_OPERATIONS'})
    import_id = new_id('AIMP')
    timestamp = now()
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    job = {
        "_id": import_id,
        "project_id": project_id,
        "filename": payload.filename,
        "format": payload.format,
        "content_hash": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "preview": operations,
        "raw_content": sanitize_postman(value)
        if payload.format == 'postman'
        else sanitize(value),
        "selected_indexes": list(range(len(operations))),
        "status": 'PREVIEW_READY',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await api_artifact_repository.insert_import(job)
    await audit(
        user.id,
        'api_artifact_preview_created',
        'APIImport',
        import_id,
        project_id,
        {"operation_count": len(operations), "format": payload.format},
    )
    return envelope(public_api_import(job, include_preview=True), revision=1)


async def review_api_artifact(
    artifact_id: str, payload: APIArtifactReview, user: CurrentUser
):
    artifact = await get_project_entity('api_imports', artifact_id, user, 'apiartifact.review')
    if artifact.get("status") not in set(['PREVIEW_READY', 'REVIEWED']):
        raise HTTPException(status_code=409, detail={"code": 'API_ARTIFACT_NOT_REVIEWABLE'})
    preview = artifact.get("preview") or []
    selected = payload.selected_indexes
    if not selected:
        raise HTTPException(status_code=422, detail={"code": "API_ARTIFACT_SELECTION_REQUIRED", "message": "Cần chọn ít nhất một thao tác API sau khi rà soát"})
    if len(set(selected)) != len(selected) or any(
        index < 0 or index >= len(preview) for index in selected
    ):
        raise HTTPException(status_code=422, detail={"code": 'INVALID_PREVIEW_INDEX'})
    timestamp = now()
    updated = await api_artifact_repository.transition_import(
        {
            "_id": artifact_id,
            "project_id": artifact["project_id"],
            "revision": payload.expected_revision,
            "status": {"$in": ['PREVIEW_READY', 'REVIEWED']},
        },
        {
            "selected_indexes": selected,
            "review_note": payload.review_note,
            "reviewed_by": user.id,
            "reviewed_at": timestamp,
            "updated_at": timestamp,
            "status": 'REVIEWED',
        },
        increment_revision=True,
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'api_artifact_reviewed',
        'APIImport',
        artifact_id,
        artifact["project_id"],
        {"selected_count": len(selected)},
    )
    return envelope(public_api_import(updated, include_preview=True), revision=updated["revision"])


async def confirm_api_artifact(
    artifact_id: str, payload: APIArtifactConfirm, user: CurrentUser
):
    artifact = await get_project_entity('api_imports', artifact_id, user, 'apiartifact.confirm')
    if artifact.get("status") == 'CONFIRMED':
        if artifact.get("idempotency_key") != payload.idempotency_key:
            raise HTTPException(status_code=409, detail={"code": 'IDEMPOTENCY_KEY_CONFLICT'})
        operations = await api_artifact_repository.list_operations(
            {"project_id": artifact["project_id"], "import_id": artifact_id},
            5000,
            ("path", 1),
        )
        return envelope(
            {**public_api_import(artifact), "operations": operations}, revision=artifact["revision"]
        )
    if artifact.get("status") == 'CONFIRMING':
        if artifact.get("idempotency_key") != payload.idempotency_key:
            raise HTTPException(status_code=409, detail={"code": 'IDEMPOTENCY_KEY_CONFLICT'})
    elif artifact.get("status") != 'REVIEWED':
        raise HTTPException(status_code=409, detail={"code": 'API_ARTIFACT_REVIEW_REQUIRED'})
    if artifact.get("revision") != payload.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT', "current_revision": artifact.get("revision")},
        )
    if artifact.get("status") == 'REVIEWED':
        claimed = await api_artifact_repository.transition_import(
            {
                "_id": artifact_id,
                "project_id": artifact["project_id"],
                "revision": payload.expected_revision,
                "status": 'REVIEWED',
            },
            {
                "status": 'CONFIRMING',
                "idempotency_key": payload.idempotency_key,
                "updated_at": now(),
            },
        )
        if not claimed:
            raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
        artifact = claimed
    selected = artifact.get("selected_indexes") or []
    preview = artifact.get("preview") or []
    timestamp = now()
    operations = [
        {
            "_id": f"{'APIOP'}-{hashlib.sha256(f'{artifact_id}:{index}'.encode()).hexdigest()[:32]}",
            "project_id": artifact["project_id"],
            "import_id": artifact_id,
            "source_index": index,
            **preview[index],
            "created_at": timestamp,
        }
        for index in selected
    ]
    for operation in operations:
        await api_artifact_repository.upsert_operation(operation)
    updated = await api_artifact_repository.transition_import(
        {
            "_id": artifact_id,
            "project_id": artifact["project_id"],
            "revision": payload.expected_revision,
            "status": 'CONFIRMING',
            "idempotency_key": payload.idempotency_key,
        },
        {
            "status": 'CONFIRMED',
            "operation_ids": [operation["_id"] for operation in operations],
            "idempotency_key": payload.idempotency_key,
            "confirmed_by": user.id,
            "confirmed_at": timestamp,
            "updated_at": timestamp,
        },
        increment_revision=True,
    )
    if not updated:
        current = await api_artifact_repository.find_import(
            artifact_id, artifact["project_id"]
        )
        if not current or current.get("status") != 'CONFIRMED':
            raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
        updated = current
    persisted = await api_artifact_repository.list_operations(
        {"project_id": artifact["project_id"], "import_id": artifact_id},
        5000,
        ("path", 1),
    )
    await audit(
        user.id,
        'api_artifact_confirmed',
        'APIImport',
        artifact_id,
        artifact["project_id"],
        {"operation_count": len(persisted)},
    )
    return envelope(
        {**public_api_import(updated), "operations": persisted}, revision=updated["revision"]
    )


async def list_api_operations(project_id: str, user: CurrentUser):
    await get_project(project_id, user, 'apiartifact.read')
    artifacts = await api_artifact_repository.list_imports(
        {"project_id": project_id, "status": 'CONFIRMED'}, 5000
    )
    if not artifacts:
        return envelope([])
    return envelope(
        await api_artifact_repository.list_operations(
            {
                "project_id": project_id,
                "import_id": {"$in": [artifact["_id"] for artifact in artifacts]},
            },
            5000,
            ("path", 1),
        )
    )


async def generate_api_tests(operation_id: str, user: CurrentUser):
    operation = await get_project_entity(
        'api_operations', operation_id, user, 'ai.generate_api_testcase'
    )
    await get_project(operation["project_id"], user, "testcase.import")
    await get_project(operation["project_id"], user, "testcase.create")
    artifact = await api_artifact_repository.find_import(
        operation["import_id"], operation["project_id"]
    )
    if not artifact or artifact.get("status") != 'CONFIRMED':
        raise HTTPException(status_code=409, detail={"code": "API_ARTIFACT_NOT_CONFIRMED"})
    cases = api_case_blueprints(operation)
    if not cases:
        raise HTTPException(status_code=422, detail={"code": "API_OPERATION_HAS_NO_TESTABLE_RESPONSES", "message": "Thao tác API chưa có phản hồi đủ rõ trong đặc tả để đề xuất ca kiểm thử"})
    preview = []
    for case in cases:
        draft = TestCaseDraftCreate(
            title=case["title"],
            type='api',
            expected_result_doc=text_document(case["expected"]),
            tags=['api'],
            automation_status='manual',
            origin='import',
            source_evidence=[
                {
                    "artifact_type": 'api_operation',
                    "artifact_version_id": operation_id,
                    "path": operation["path"],
                    "method": operation["method"],
                    "response_code": case["response_code"],
                }
            ],
        )
        preview.append({
            "title": draft.title,
            "type": draft.type,
            "priority": draft.priority,
            "risk": draft.risk,
            "expected": case["expected"],
            "incomplete": True,
            "source_test_case_key": "",
            "source_projection": "",
            "draft": draft.model_dump(),
        })
    job = await store_test_import_preview(
        operation["project_id"],
        f"{operation['method']} {operation['path']}",
        "api_operation",
        preview,
        user,
        {
            "source_api_operation_id": operation_id,
            "source_api_operation_fingerprint": operation_fingerprint(operation),
            "source_api_import_id": operation["import_id"],
        },
    )
    await audit(
        user.id,
        'api_test_preview_created',
        'APIOperation',
        operation_id,
        operation["project_id"],
        {"count": len(preview)},
    )
    return envelope(job)


async def build_api_artifact_diff(project_id, from_artifact_id, to_artifact_id):
    artifacts = await api_artifact_repository.list_imports(
        {
            "_id": {"$in": [from_artifact_id, to_artifact_id]},
            "project_id": project_id,
            "status": 'CONFIRMED',
        },
        2,
    )
    if len(artifacts) != 2:
        raise HTTPException(status_code=422, detail={"code": 'API_ARTIFACT_VERSION_INVALID'})
    operations = await api_artifact_repository.list_operations(
        {"project_id": project_id, "import_id": {"$in": [from_artifact_id, to_artifact_id]}},
        10000,
    )
    by_import = {from_artifact_id: {}, to_artifact_id: {}}
    for operation in operations:
        by_import[operation["import_id"]][operation_identity(operation)] = operation
    before = by_import[from_artifact_id]
    after = by_import[to_artifact_id]
    before_keys = set(before)
    after_keys = set(after)
    return {
        "from_artifact_id": from_artifact_id,
        "to_artifact_id": to_artifact_id,
        "added": [after[identity] for identity in sorted(after_keys - before_keys)],
        "removed": [before[identity] for identity in sorted(before_keys - after_keys)],
        "changed": [
            {"identity": identity, "before": before[identity], "after": after[identity]}
            for identity in sorted(before_keys & after_keys)
            if operation_fingerprint(before[identity]) != operation_fingerprint(after[identity])
        ],
    }


async def diff_api_artifacts(
    project_id: str,
    from_artifact_id: str,
    to_artifact_id: str,
    user: CurrentUser,
):
    await get_project(project_id, user, 'apiartifact.diff.read')
    return envelope(await build_api_artifact_diff(project_id, from_artifact_id, to_artifact_id))


async def analyze_api_artifact_impact(
    project_id: str, payload: APIArtifactImpact, user: CurrentUser
):
    await get_project(project_id, user, 'impact.execute')
    existing = await api_artifact_repository.find_impact(
        project_id,
        'api_artifact_diff',
        payload.from_artifact_id,
        payload.to_artifact_id,
    )
    if existing:
        return envelope(existing, revision=existing.get("revision", 1))
    difference = await build_api_artifact_diff(
        project_id, payload.from_artifact_id, payload.to_artifact_id
    )
    affected_operations = {item["_id"] for item in difference["removed"]} | {
        item["before"]["_id"] for item in difference["changed"]
    }
    current_cases = await api_artifact_repository.list_test_cases(
        project_id, ['ACTIVE', 'NEEDS_UPDATE'], 20000
    )
    versions = await api_artifact_repository.list_test_case_versions(
        project_id,
        [item["current_version_id"] for item in current_cases if item.get("current_version_id")],
        20000,
    )
    affected = []
    for version in versions:
        evidence_ids = {
            evidence.get("artifact_version_id")
            for evidence in version.get("source_evidence", [])
            if evidence.get("artifact_type") == 'api_operation'
        }
        matched = sorted(affected_operations & evidence_ids)
        if not matched:
            continue
        affected.append(
            {
                "test_case_id": version.get("test_case_id"),
                "test_case_version_id": version["_id"],
                "classification": 'NEEDS_UPDATE',
                "confidence": 1,
                "reasons": ['Đặc tả API nguồn đã thay đổi hoặc bị loại bỏ'],
                "evidence": [{"api_operation_ids": matched}],
            }
        )
    new_test_requirements = [
        {
            "classification": 'NEW_TEST_REQUIRED',
            "reason": 'Thao tác API mới chưa có ca kiểm thử được xác nhận',
            "evidence": {"api_operation_id": operation["_id"]},
        }
        for operation in difference["added"]
    ]
    analysis = {
        "_id": new_id('IMP'),
        "project_id": project_id,
        "source_type": 'api_artifact_diff',
        "from_artifact_id": payload.from_artifact_id,
        "to_artifact_id": payload.to_artifact_id,
        "difference": difference,
        "affected_test_cases": affected,
        "new_test_requirements": new_test_requirements,
        "status": 'REVIEW_READY',
        "revision": 1,
        "mode": 'DETERMINISTIC',
        "created_by": user.id,
        "created_at": now(),
    }
    await api_artifact_repository.insert_impact(analysis)
    await audit(
        user.id,
        'api_artifact_impact_created',
        'ImpactAnalysis',
        analysis["_id"],
        project_id,
        {"affected_count": len(affected), "new_test_requirement_count": len(new_test_requirements)},
    )
    return envelope(analysis, revision=1)


async def archive_api_artifact(
    artifact_id: str, payload: APIArtifactArchive, user: CurrentUser
):
    artifact = await get_project_entity('api_imports', artifact_id, user, 'apiartifact.archive')
    if artifact.get("status") == 'ARCHIVED':
        return envelope(public_api_import(artifact), revision=artifact.get("revision", 1))
    timestamp = now()
    updated = await api_artifact_repository.transition_import(
        {
            "_id": artifact_id,
            "project_id": artifact["project_id"],
            "revision": payload.expected_revision,
            "status": {"$ne": 'ARCHIVED'},
        },
        {
            "status": 'ARCHIVED',
            "archive_reason": payload.reason,
            "archived_by": user.id,
            "archived_at": timestamp,
            "updated_at": timestamp,
        },
        increment_revision=True,
    )
    if not updated:
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    await audit(
        user.id,
        'api_artifact_archived',
        'APIImport',
        artifact_id,
        artifact["project_id"],
        {"reason": payload.reason},
    )
    return envelope(public_api_import(updated), revision=updated["revision"])

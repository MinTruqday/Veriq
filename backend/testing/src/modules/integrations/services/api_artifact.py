import hashlib
import json

from fastapi import HTTPException

from src.core.auth import CurrentUser
from src.core.ai_automation import ai_contract_metadata, request_ai_automation
from src.core.common import audit, envelope, get_project, get_project_entity, new_id, now
from src.core.database import database
from src.clients.ai_automation import queue_api_operation_confirmed
from src.core.rich_text import text_document
from src.schemas.contracts.design import TestCaseDraftCreate
from src.schemas.test_analysis import GeneratedCase
from src.schemas.contracts.requirements import (
    APIArtifactArchive,
    APIArtifactConfirm,
    APIArtifactImpact,
    APIArtifactReview,
    ImportCreate,
)
from src.modules.integrations.services.api_artifact_formats import (
    operation_fingerprint,
    operation_identity,
    parse_openapi,
    parse_postman,
    public_api_import,
    sanitize,
    sanitize_postman,
)
from src.repositories.api_artifact import api_artifact_repository
from src.repositories.test_design import test_design_repository
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


def api_operation_source_text(operation):
    schemas = operation.get("schemas")
    if not isinstance(schemas, dict):
        schemas = {}
    contract = {
        key: value for key, value in operation.items() if key != "schemas"
    }
    pending = []

    def collect_references(value):
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith(
                "#/components/schemas/"
            ):
                name = reference.removeprefix("#/components/schemas/").split("/", 1)[0]
                pending.append(name.replace("~1", "/").replace("~0", "~"))
            for child in value.values():
                collect_references(child)
        elif isinstance(value, list):
            for child in value:
                collect_references(child)

    collect_references(contract)
    selected = {}
    while pending:
        name = pending.pop(0)
        if name in selected or name not in schemas:
            continue
        selected[name] = schemas[name]
        collect_references(schemas[name])
    if selected:
        contract["schemas"] = selected
    return json.dumps(contract, sort_keys=True, ensure_ascii=False, indent=2, default=str)


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
    previews = await test_design_repository.list_imports(
        artifact["project_id"], {"source_api_import_id": artifact_id}, 5000
    ) if artifact.get("status") == 'CONFIRMED' else []
    preview_by_operation = {
        item.get("source_api_operation_id"): item
        for item in previews
        if item.get("source_api_operation_id")
    }
    event_ids = [
        f"api-operation:{item['_id']}:r{item.get('revision', 1)}"
        for item in operations
    ]
    event_rows = (
        await database.value.ai_automation_outbox.find(
            {"_id": {"$in": event_ids}}, {"_id": 1, "status": 1}
        ).to_list(len(event_ids))
        if event_ids
        else []
    )
    event_by_id = {item["_id"]: item.get("status") for item in event_rows}
    for operation in operations:
        preview = preview_by_operation.get(operation["_id"])
        if preview:
            operation["test_import_preview_id"] = preview["_id"]
            operation["test_import_preview_status"] = preview.get("status")
        operation["automation_dispatch_status"] = event_by_id.get(
            f"api-operation:{operation['_id']}:r{operation.get('revision', 1)}"
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
        async with await database.client.start_session() as session:
            async with session.start_transaction():
                for operation in operations:
                    await queue_api_operation_confirmed(operation, user, session)
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
            "revision": 1,
            "created_at": timestamp,
        }
        for index in selected
    ]
    async def persist_confirmation(session):
        for operation in operations:
            await api_artifact_repository.upsert_operation(operation, session=session)
        updated_import = await api_artifact_repository.transition_import(
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
            session=session,
        )
        if not updated_import:
            current_import = await api_artifact_repository.find_import(
                artifact_id, artifact["project_id"], session=session
            )
            if not current_import or current_import.get("status") != 'CONFIRMED':
                raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
            updated_import = current_import
        persisted_operations = await api_artifact_repository.list_operations(
            {"project_id": artifact["project_id"], "import_id": artifact_id},
            5000,
            ("path", 1),
            session=session,
        )
        await audit(
            user.id,
            'api_artifact_confirmed',
            'APIImport',
            artifact_id,
            artifact["project_id"],
            {"operation_count": len(persisted_operations)},
            session=session,
        )
        for operation in persisted_operations:
            await queue_api_operation_confirmed(operation, user, session)
        return updated_import, persisted_operations

    async with await database.client.start_session() as session:
        updated, persisted = await session.with_transaction(persist_confirmation)
    if not updated:
        current = await api_artifact_repository.find_import(
            artifact_id, artifact["project_id"]
        )
        if not current or current.get("status") != 'CONFIRMED':
            raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
        updated = current
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
    operations = await api_artifact_repository.list_operations(
        {
            "project_id": project_id,
            "import_id": {"$in": [artifact["_id"] for artifact in artifacts]},
        },
        5000,
        ("path", 1),
    )
    previews = await test_design_repository.list_imports(
        project_id,
        {"source_api_operation_id": {"$in": [item["_id"] for item in operations]}},
        5000,
    )
    preview_by_operation = {
        item["source_api_operation_id"]: item
        for item in previews
        if item.get("source_api_operation_id")
    }
    event_ids = [
        f"api-operation:{item['_id']}:r{item.get('revision', 1)}"
        for item in operations
    ]
    event_rows = (
        await database.value.ai_automation_outbox.find(
            {"_id": {"$in": event_ids}}, {"_id": 1, "status": 1}
        ).to_list(len(event_ids))
        if event_ids
        else []
    )
    event_by_id = {item["_id"]: item.get("status") for item in event_rows}
    for operation in operations:
        preview = preview_by_operation.get(operation["_id"])
        if preview:
            operation["test_import_preview_id"] = preview["_id"]
            operation["test_import_preview_status"] = preview.get("status")
        operation["automation_dispatch_status"] = event_by_id.get(
            f"api-operation:{operation['_id']}:r{operation.get('revision', 1)}"
        )
    return envelope(operations)


async def get_api_operation(operation_id: str, user: CurrentUser):
    operation = await get_project_entity(
        "api_operations", operation_id, user, "apiartifact.read"
    )
    artifact = await api_artifact_repository.find_import(
        operation.get("import_id"), operation.get("project_id")
    )
    if (
        not artifact
        or artifact.get("status") != "CONFIRMED"
        or operation.get("project_id") != artifact.get("project_id")
        or operation.get("import_id") != artifact.get("_id")
    ):
        raise HTTPException(status_code=409, detail={"code": "API_OPERATION_SOURCE_INVALID"})
    return envelope(operation, revision=operation.get("revision", 1))


async def generate_api_tests(operation_id: str, user: CurrentUser):
    if (
        not getattr(user, "_ai_automation_run_id", None)
        or getattr(user, "_ai_automation_trigger", None)
        != "API_OPERATION_CONFIRMED"
    ):
        raise HTTPException(
            status_code=403,
            detail={"code": "API_TEST_GENERATION_REQUIRES_AUTOMATION_EVENT"},
        )
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
    source_fingerprint = operation_fingerprint(operation)
    idempotent_job_id = (
        "TIMP-"
        + hashlib.sha256(
            f"{operation_id}:{source_fingerprint}".encode()
        ).hexdigest()[:32]
    )
    existing_job = await test_design_repository.find_import(
        operation["project_id"], idempotent_job_id
    )
    if existing_job:
        if (
            existing_job.get("source_api_operation_id") != operation_id
            or existing_job.get("source_api_operation_fingerprint")
            != source_fingerprint
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "TEST_IMPORT_IDEMPOTENCY_CONFLICT"},
            )
        return envelope(existing_job)
    source_text = api_operation_source_text(operation)
    evidence_chunks = [
        source_text[index : index + 3500]
        for index in range(0, len(source_text), 3500)
    ]
    if len(evidence_chunks) > 100:
        raise HTTPException(
            status_code=422,
            detail={"code": "API_OPERATION_EVIDENCE_TOO_LARGE"},
        )
    evidence = [
        {
            "artifact_type": "api_operation",
            "artifact_id": operation_id,
            "artifact_version_id": operation_id,
            "source_version": str(operation.get("revision", 1)),
            "authority": "CONFIRMED_API_DEFINITION",
            "text": chunk,
        }
        for chunk in evidence_chunks
    ]
    ai_result = await request_ai_automation(
        "test_generation",
        operation["project_id"],
        "Tạo các ca kiểm thử API có bước thực thi cụ thể, dữ liệu đầu vào và kết quả kiểm chứng được. Chỉ dùng hành vi, tham số, schema, bảo mật và mã phản hồi được mô tả trong thao tác API đã xác nhận. Không suy diễn hành vi lỗi hoặc giới hạn không có trong nguồn. Trả trích dẫn nguyên văn từ nguồn cho từng ca.",
        evidence,
    )
    if ai_result.get("status") != "SUCCESS" or ai_result.get("degraded_mode"):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "API_TEST_GENERATION_UNAVAILABLE",
                "retryable": True,
                "reason_codes": ai_result.get("reason_codes", []),
            },
        )
    try:
        cases = [
            GeneratedCase.model_validate(item)
            for item in ai_result.get("suggestions", [])
        ]
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "API_TEST_GENERATION_CONTRACT_INVALID"},
        ) from error
    if not cases:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "API_TEST_GENERATION_EVIDENCE_INSUFFICIENT",
                "warnings": ai_result.get("warnings", []),
            },
        )
    preview = []
    for case_index, case in enumerate(cases):
        if (
            set(case.evidence_refs) != {operation_id}
            or case.acceptance_criterion_ids
            or case.coverage_obligations
            or case.challenge_techniques
            or not case.evidence_quotes
            or any(
                quote.evidence_ref != operation_id
                or quote.quote not in source_text
                for quote in case.evidence_quotes
            )
        ):
            raise HTTPException(
                status_code=502,
                detail={"code": "API_TEST_GENERATION_GROUNDING_INVALID"},
            )
        draft = TestCaseDraftCreate(
            title=case.title,
            type=case.category,
            objective_doc=text_document(case.objective),
            preconditions_doc=text_document(case.preconditions),
            steps=[
                {
                    "id": hashlib.sha256(
                        f"{operation_id}:{case_index}:{step_index}".encode()
                    ).hexdigest()[:24],
                    "order": step_index + 1,
                    "action_doc": text_document(step.action),
                    "test_data": step.test_data,
                    "expected_doc": text_document(step.expected),
                }
                for step_index, step in enumerate(case.steps)
            ],
            expected_result_doc=text_document(case.expected),
            techniques=case.techniques,
            evidence_refs=case.evidence_refs,
            evidence_quotes=[item.model_dump() for item in case.evidence_quotes],
            tags=["api"],
            automation_status='manual',
            origin='ai_generated',
            source_evidence=[
                {
                    "artifact_type": 'api_operation',
                    "artifact_version_id": operation_id,
                    "text": "\n".join(
                        quote.quote for quote in case.evidence_quotes
                    ),
                    "path": operation.get("path"),
                    "method": operation.get("method"),
                    "operation_id": operation.get("operation_id"),
                }
            ],
        )
        preview.append({
            "title": draft.title,
            "type": draft.type,
            "priority": draft.priority,
            "risk": draft.risk,
            "expected": case.expected,
            "incomplete": False,
            "source_test_case_key": "",
            "source_projection": "",
            "draft": draft.model_dump(),
        })
    job = await store_test_import_preview(
        operation["project_id"],
        f"{operation['method']} {operation['path']}",
        "api_operation_ai",
        preview,
        user,
        {
            "source_api_operation_id": operation_id,
            "source_api_operation_fingerprint": source_fingerprint,
            "source_api_import_id": operation["import_id"],
            "ai_generation": ai_contract_metadata(ai_result),
        },
        idempotent_job_id=idempotent_job_id,
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


async def get_test_import_preview(job_id: str, user: CurrentUser):
    job = await get_project_entity("test_imports", job_id, user, "testcase.import")
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

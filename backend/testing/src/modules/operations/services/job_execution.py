from fastapi import HTTPException

from src.core.auth import CurrentUser
from src.core.common import get_project, now
from src.repositories.analysis import analysis_repository
from src.schemas.contracts.requirements import RequirementCompareInput
from src.schemas.contracts.utility import GenerateInput
from src.modules.quality.services.change_set import create_change_set_record
from src.modules.quality.services.impact_analysis import create_impact_analysis_record
from src.clients.project_knowledge import index_artifact
from src.modules.design.services.test_case_automation import (
    find_duplicate_test_case_records,
    generate_test_case_draft_records,
)


async def process_delegated_job(
    event: str,
    body: dict,
    requester_id: str,
    requester_email: str,
):
    
    if event not in {"impact.analysis.requested", "duplicate.scan.requested", "test.generate.requested", "requirement.semantic_diff.requested", "knowledge.index.requested", "requirement.extract.requested", "document.parse.requested", "document.summary.requested"}:
        raise HTTPException(
            status_code=422, detail={"code": 'UNSUPPORTED_JOB_EVENT'}
        )
    if not requester_id:
        raise HTTPException(status_code=422, detail={"code": 'DELEGATED_IDENTITY_REQUIRED'})
    project_id = str(body.get("project_id") or "")
    if not project_id:
        raise HTTPException(status_code=422, detail={"code": 'DELEGATED_IDENTITY_REQUIRED'})
    user = CurrentUser(
        _id=requester_id,
        email=requester_email or 'worker@internal',
        system_role='USER',
    )
    if event == "impact.analysis.requested":
        await get_project(project_id, user, "impact.execute")
    elif event == "duplicate.scan.requested":
        await get_project(project_id, user, "ai.run_duplicate_check")
    elif event == "test.generate.requested":
        await get_project(project_id, user, "ai.generate_testcase")
    elif event == "requirement.semantic_diff.requested":
        await get_project(project_id, user, "changeset.create")
    elif event == "knowledge.index.requested":
        await get_project(project_id, user, "knowledge.manage")
    else:
        await get_project(project_id, user, "requirement_document.extract")
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    result = await execute_job(event, body, payload, user)
    completed = not (isinstance(result, dict) and result.get("indexed") is False)
    record = {
        "_id": body.get("job_id"),
        "project_id": project_id,
        "artifact_version_id": body.get("artifact_version_id"),
        "event": event,
        "model_version": body.get("model_version"),
        "status": 'COMPLETED' if completed else 'FAILED',
        "error_code": None if completed else 'KNOWLEDGE_INDEX_FAILED',
        "retryable": not completed,
        "state_after_failure": 'INDEX_FAILED' if not completed else None,
        "result": result,
        "completed_at": now(),
    }
    await analysis_repository.upsert_worker_event(record["_id"], record)
    return record


async def execute_job(event: str, body: dict, payload: dict, user: CurrentUser):
    
    if event == 'impact.analysis.requested':
        return await create_impact_analysis_record(
            payload.get("change_set_id") or body.get("artifact_version_id"), None, user
        )
    if event == 'duplicate.scan.requested':
        return await find_duplicate_test_case_records(body["project_id"], user)
    if event == 'test.generate.requested':
        request = GenerateInput(
            **{
                key: value
                for key, value in payload.items()
                if key in {"categories", "count_per_category", "instruction"}
            }
        )
        return await generate_test_case_draft_records(body["artifact_version_id"], request, user)
    if event == 'requirement.semantic_diff.requested':
        request = RequirementCompareInput(
            from_version_id=payload["from_version_id"], to_version_id=payload["to_version_id"]
        )
        return await create_change_set_record(payload["requirement_id"], request, user)
    if event == 'knowledge.index.requested':
        return await reindex_artifact(body["project_id"], body["artifact_version_id"])
    if event == 'requirement.extract.requested':
        return {
            "status": 'READY_FOR_PREVIEW',
            "import_job_id": payload.get("import_job_id"),
        }
    if event == 'document.parse.requested':
        return {
            "status": 'READY_FOR_EXTRACTION',
            "document_id": payload.get("document_id"),
        }
    if event == 'document.summary.requested':
        from src.modules.requirements.services.document_reader import process_document_summary_job

        return await process_document_summary_job(body, payload, user)
    return {"status": 'COMPLETED'}


async def reindex_artifact(project_id: str, version_id: str):
    artifact = await analysis_repository.find_requirement_version(project_id, version_id)
    if artifact:
        collection = 'requirement_versions'
        artifact_type = 'requirement_version'
        artifact_id = artifact['requirement_id']
        authority = 'APPROVED_SOURCE' if artifact.get('status') == 'BASELINED' else 'DRAFT'
        metadata = {
            'acceptance_criterion_ids': artifact.get('acceptance_criterion_ids', []),
            'source_document_ids': artifact.get('source_document_ids', []),
        }
    else:
        artifact = await analysis_repository.find_test_case_version(project_id, version_id)
        collection = 'test_case_versions'
        artifact_type = 'test_case_version'
        artifact_id = artifact['test_case_id'] if artifact else None
        authority = 'APPROVED_SOURCE'
        metadata = {
            'requirement_version_ids': artifact.get('requirement_version_ids', []) if artifact else [],
            'acceptance_criterion_ids': artifact.get('acceptance_criterion_ids', []) if artifact else [],
        }
    if not artifact:
        raise HTTPException(status_code=404, detail={"code": 'ARTIFACT_VERSION_NOT_FOUND'})
    indexed = await index_artifact(
        project_id,
        artifact_type,
        artifact_id,
        artifact["_id"],
        artifact.get("title", ""),
        artifact.get("plain_text_projection", ""),
        artifact.get("status", 'ACTIVE'),
        authority,
        artifact.get("version"),
        **metadata,
    )
    await analysis_repository.set_artifact_index_result(
        collection,
        project_id,
        version_id,
        'INDEXED' if indexed else 'FAILED',
        None if indexed else 'KNOWLEDGE_INDEX_FAILED',
        now() if indexed else None,
    )
    return {"indexed": indexed, "artifact_version_id": version_id}

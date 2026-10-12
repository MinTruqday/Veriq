import csv
import io
import json

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from src.core.auth import CurrentUser
from src.core.common import audit, envelope, get_project, get_project_entity, new_id, now, plain_text
from src.repositories.test_design import test_design_repository
from src.repositories.analysis import analysis_repository
from src.core.rich_text import text_document
from src.repositories.api_artifact import api_artifact_repository
from src.schemas.contracts.design import TestCaseDraftCreate, TestImportConfirm
from src.schemas.contracts.requirements import (
    ImportCreate,
)
from src.modules.integrations.services.api_artifact_formats import create_xlsx, lexical_similarity, model_metadata, operation_fingerprint, terms
from src.modules.requirements.services.requirement_import import extract_xlsx_csv
from src.modules.design.services.test_case_records import comparison_cases, create_test_case_draft_record
from src.modules.design.services.linters import duplicate_score


async def compare_test_import_candidates(project_id, preview, selected_indexes=None):
    existing_cases, threshold = await comparison_cases(project_id)
    selected = set(selected_indexes) if selected_indexes is not None else set(range(len(preview)))
    results = {}
    previous = []
    for index, item in enumerate(preview):
        if index not in selected:
            continue
        candidate = item["draft"]
        matches = []
        for existing in existing_cases + previous:
            if (
                item.get("source_project_id") == project_id
                and item.get("source_test_case_key")
                and item["source_test_case_key"] == existing.get("test_case_key")
            ):
                score = 1
            elif item.get("source_projection") and item["source_projection"] == str(existing.get("plain_text_projection") or "").strip():
                score = 1
            else:
                score, _ = duplicate_score(candidate, existing, threshold)
            if score >= threshold:
                matches.append({
                    "id": existing["_id"],
                    "title": existing.get("title", ""),
                    "score": score,
                    "target_version_id": existing["_id"] if existing.get("test_case_id") and existing.get("status") == "ACTIVE" else None,
                })
        ranked = sorted(matches, key=lambda match: match["score"], reverse=True)
        results[index] = ranked[:3]
        preview_match = next(
            (match for match in ranked if str(match["id"]).startswith("preview:")), None
        )
        if preview_match and preview_match not in results[index]:
            results[index][-1] = preview_match
        previous.append({"_id": f"preview:{index}", **candidate, "test_case_key": item.get("source_test_case_key"), "plain_text_projection": item.get("source_projection")})
    return results


async def store_test_import_preview(project_id, filename, format, preview, user, source=None):
    comparisons = await compare_test_import_candidates(project_id, preview)
    for index, matches in comparisons.items():
        preview[index]["similar_cases"] = matches
    job = {
        "_id": new_id('TIMP'),
        "project_id": project_id,
        "filename": filename,
        "format": format,
        "preview": preview,
        "status": 'PREVIEW_READY',
        "created_by": user.id,
        "created_at": now(),
        **(source or {}),
    }
    await test_design_repository.insert_import(job)
    return job


async def recover_trace_links(project_id: str, user: CurrentUser):
    
    await get_project(project_id, user, "trace.recover")
    requirements = await test_design_repository.list_requirement_versions(
        {"project_id": project_id, "status": 'BASELINED'},
        5000,
    )
    tests = await analysis_repository.list_active_test_case_versions(project_id, 'ACTIVE', 10000)
    existing = await test_design_repository.list_trace_links(
        {"project_id": project_id, "status": {"$in": ['CONFIRMED', 'SUGGESTED']}},
        50000,
    )
    pairs = {(item["source_id"], item["target_id"]) for item in existing}
    
    suggestions = []
    for test in tests:
        ranked = sorted(
            (
                (
                    lexical_similarity(
                        req.get("plain_text_projection", ""), test.get("plain_text_projection", "")
                    ),
                    req,
                )
                for req in requirements
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        for score, requirement in ranked[: 3]:
            if (
                score < 0.18
                or (requirement["_id"], test["_id"]) in pairs
            ):
                continue
            link = {
                "_id": new_id('TL'),
                "project_id": project_id,
                "source_type": 'requirement_version',
                "source_id": requirement["_id"],
                "target_type": 'test_case_version',
                "target_id": test["_id"],
                "link_type": 'verifies',
                "confidence": score,
                "origin": 'trace_recovery',
                "status": 'SUGGESTED',
                "evidence": [
                    {
                        "matched_terms": sorted(
                            terms(requirement.get("plain_text_projection", ""))
                            & terms(test.get("plain_text_projection", ""))
                        )
                    }
                ],
                "created_by": user.id,
                "created_at": now(),
                "updated_at": now(),
            }
            suggestions.append(link)
    await test_design_repository.insert_trace_links(suggestions)
    await audit(
        user.id,
        "trace_recovery_completed",
        "Project",
        project_id,
        project_id,
        {"suggestion_count": len(suggestions)},
    )
    return envelope({"items": suggestions, "model": model_metadata("trace_recovery")})


async def preview_test_import(
    project_id: str, payload: ImportCreate, user: CurrentUser
):
    
    await get_project(project_id, user, "testcase.import")
    if payload.format not in ['csv', 'xlsx']:
        raise HTTPException(status_code=422, detail={"code": 'TEST_IMPORT_FORMAT_UNSUPPORTED'})
    content = str(payload.content)
    rows = list(csv.DictReader(io.StringIO(content)))
    if len(rows) > 2000:
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_ROW_LIMIT_EXCEEDED", "message": "Tệp có quá 2000 dòng dữ liệu, cần chia thành nhiều lần nhập", "limit": 2000, "received": len(rows)})
    preview = []
    invalid_rows = []
    for index, row in enumerate(rows, 2):
        if not any(str(value or "").strip() for value in row.values()):
            continue
        title = str(row.get("title") or "").strip()
        action = str(row.get("action") or row.get("steps") or "").strip()
        expected = str(row.get("expected") or row.get("expected_result") or "").strip()
        projection = str(row.get("plain_text_projection") or "").strip()
        try:
            exported_steps = json.loads(row.get("steps_json") or "[]")
            exported_test_data = json.loads(row.get("test_data_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            invalid_rows.append(index)
            continue
        if not isinstance(exported_steps, list) or not isinstance(exported_test_data, dict):
            invalid_rows.append(index)
            continue
        steps = []
        for step_index, step in enumerate(exported_steps, 1):
            if not isinstance(step, dict):
                steps = []
                break
            step_action = str(step.get("action") or "").strip()
            step_expected = str(step.get("expected") or "").strip()
            step_data = step.get("test_data") or {}
            if not step_action or not step_expected or not isinstance(step_data, dict):
                steps = []
                break
            steps.append({
                "id": str(step.get("id") or f"step-{step_index}"),
                "order": step_index,
                "action_doc": text_document(step_action),
                "test_data": step_data,
                "expected_doc": text_document(step_expected),
            })
        if exported_steps and len(steps) != len(exported_steps):
            invalid_rows.append(index)
            continue
        if not exported_steps and action and expected:
            steps = [{
                "id": "step-1",
                "order": 1,
                "action_doc": text_document(action),
                "test_data": {},
                "expected_doc": text_document(expected),
            }]
        same_project = str(row.get("project_id") or "").strip() == project_id
        if (
            len(title) < 2
            or not exported_steps and bool(action) != bool(expected)
            or not (steps or projection)
        ):
            invalid_rows.append(index)
            continue
        try:
            draft = TestCaseDraftCreate(
                title=title,
                type=row.get("type") or "custom",
                priority=row.get("priority") or "medium",
                risk=row.get("risk") or "medium",
                objective_doc=text_document(str(row.get("objective") or projection).strip()),
                preconditions_doc=text_document(str(row.get("preconditions") or row.get("precondition") or "").strip()),
                steps=steps,
                test_data=exported_test_data,
                expected_result_doc=text_document(str(row.get("expected_result") or expected).strip()),
                postconditions_doc=text_document(str(row.get("postconditions") or "").strip()),
                tags=[item.strip() for item in (row.get("tags") or "").split(",") if item.strip()],
                owner_id=str(row.get("owner_id") or "").strip() or None if same_project else None,
                techniques=[item.strip() for item in (row.get("techniques") or "").split(",") if item.strip()],
                automation_status=row.get("automation_status") or "manual",
                data_set_version_ids=[item.strip() for item in (row.get("data_set_version_ids") or "").split(",") if item.strip()] if same_project else [],
                requirement_version_ids=[item.strip() for item in (row.get("requirement_version_ids") or "").split(",") if item.strip()] if same_project else [],
                acceptance_criterion_ids=[item.strip() for item in (row.get("acceptance_criterion_ids") or "").split(",") if item.strip()] if same_project else [],
                test_condition_ids=[item.strip() for item in (row.get("test_condition_ids") or "").split(",") if item.strip()] if same_project else [],
                scenario_id=str(row.get("scenario_id") or "").strip() or None if same_project else None,
                origin="import",
            )
        except ValidationError:
            invalid_rows.append(index)
            continue
        preview.append({
            "title": title,
            "type": draft.type,
            "priority": draft.priority,
            "risk": draft.risk,
            "expected": expected,
            "incomplete": not bool(steps),
            "source_test_case_key": str(row.get("test_case_key") or "").strip(),
            "source_project_id": str(row.get("project_id") or "").strip(),
            "source_projection": projection,
            "draft": draft.model_dump(),
        })
    if invalid_rows:
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_ROWS_INCOMPLETE", "message": f"Có {len(invalid_rows)} dòng thiếu tên hoặc thiếu dữ liệu kiểm thử, bắt đầu từ dòng {invalid_rows[0]}", "rows": invalid_rows[:20], "count": len(invalid_rows)})
    if not preview:
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_EMPTY", "message": "Tệp không có ca kiểm thử để nhập"})
    return envelope(await store_test_import_preview(
        project_id, payload.filename, payload.format, preview, user
    ))


async def upload_test_import(
    project_id: str,
    format: str,
    file: UploadFile,
    user: CurrentUser,
):
    
    if format not in ['csv', 'xlsx']:
        raise HTTPException(status_code=422, detail={"code": 'TEST_IMPORT_FORMAT_UNSUPPORTED'})
    data = await file.read(20971521)
    if len(data) > 20971520:
        raise HTTPException(status_code=413, detail={"code": 'IMPORT_TOO_LARGE'})
    if format == 'xlsx':
        content = extract_xlsx_csv(data)
    else:
        try:
            content = data.decode('utf-8-sig')
        except UnicodeDecodeError as error:
            raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_ENCODING_INVALID"}) from error
    return await preview_test_import(
        project_id,
        ImportCreate(
            filename=file.filename or f"{'test-cases'}.{format}",
            format=format,
            content=content,
        ),
        user,
    )


async def confirm_test_import(
    job_id: str, payload: TestImportConfirm, user: CurrentUser
):
    
    job = await get_project_entity("test_imports", job_id, user, "testcase.import")
    if job["status"] == 'CONFIRMED':
        return envelope(job)
    if job.get("source_api_operation_id"):
        operation = await api_artifact_repository.find_operation(
            job["source_api_operation_id"], job["project_id"]
        )
        artifact = await api_artifact_repository.find_import(
            job["source_api_import_id"], job["project_id"]
        )
        if (
            not operation
            or not artifact
            or artifact.get("status") != 'CONFIRMED'
            or operation.get("import_id") != job["source_api_import_id"]
            or operation_fingerprint(operation) != job["source_api_operation_fingerprint"]
        ):
            raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_SOURCE_CHANGED", "message": "Nguồn API đã thay đổi hoặc được lưu trữ Hãy xem trước lại trước khi nhập ca"})
    selected = payload.selected_indexes
    if not selected:
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_SELECTION_REQUIRED"})
    if len(selected) != len(set(selected)):
        raise HTTPException(status_code=422, detail={"code": "DUPLICATE_PREVIEW_INDEX"})
    version_resolutions = payload.version_resolutions
    if (
        set(version_resolutions) - set(selected)
        or set(version_resolutions) & set(payload.separate_indexes)
        or len({item.target_version_id for item in version_resolutions.values()}) != len(version_resolutions)
        or any(len(item.reason.strip()) < 2 for item in version_resolutions.values())
    ):
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_RESOLUTION_INVALID"})
    if any(len(payload.separate_reasons.get(index, "").strip()) < 2 for index in payload.separate_indexes):
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_SEPARATE_REASON_REQUIRED", "message": "Cần ghi lý do tạo ca kiểm thử riêng khi có ca gần giống"})
    drafts = []
    for index in selected:
        if index < 0 or index >= len(job["preview"]):
            raise HTTPException(status_code=422, detail={"code": 'INVALID_PREVIEW_INDEX'})
        item = job["preview"][index]
        if item.get("incomplete") and not payload.accept_incomplete:
            raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_INCOMPLETE_ACK_REQUIRED", "message": "Cần xác nhận ca nhập chưa có bước và kết quả kiểm chứng"})
        if not item.get("draft"):
            raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_REUPLOAD_REQUIRED", "message": "Bản xem trước cũ cần được tải lên lại để kiểm tra nguồn dữ liệu"})
        draft_data = dict(item["draft"])
        if index in payload.separate_indexes:
            draft_data["duplicate_reason"] = payload.separate_reasons.get(index, "").strip()
        try:
            drafts.append(TestCaseDraftCreate(**draft_data))
        except ValidationError as error:
            raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_DRAFT_INVALID"}) from error
    comparisons = await compare_test_import_candidates(job["project_id"], job["preview"], selected)
    duplicates = [
        index for index in selected
        if comparisons[index]
        and index not in payload.separate_indexes
        and index not in version_resolutions
    ]
    if duplicates:
        raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_DUPLICATE_REVIEW_REQUIRED", "message": "Cần bỏ chọn ca trùng hoặc ghi lý do tạo ca riêng", "indexes": duplicates, "matches": {index: comparisons[index] for index in duplicates}})
    if set(payload.separate_indexes) - {index for index in selected if comparisons[index] or job["preview"][index].get("similar_cases")}:
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_RESOLUTION_INVALID"})
    targets = {}
    if version_resolutions:
        await get_project(job["project_id"], user, "testcase.version.create")
    for index, resolution in version_resolutions.items():
        if resolution.target_version_id not in {
            match["target_version_id"] for match in comparisons[index]
            if match.get("target_version_id")
        }:
            raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_TARGET_CHANGED", "message": "Ca kiểm thử đích đã thay đổi  Hãy xem trước lại", "index": index})
        version = await test_design_repository.find_case_version(
            resolution.target_version_id, job["project_id"]
        )
        case = await test_design_repository.find_case(
            version["test_case_id"], job["project_id"]
        ) if version else None
        if not case or case.get("status") != "ACTIVE" or case.get("current_version_id") != resolution.target_version_id:
            raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_TARGET_CHANGED", "message": "Phiên bản ca kiểm thử đích đã thay đổi  Hãy xem trước lại", "index": index})
        targets[index] = case
    claimed = await test_design_repository.claim_import(job_id, job["project_id"])
    if not claimed:
        raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_CONFIRM_IN_PROGRESS"})
    created = []
    try:
        for index, draft_data in zip(selected, drafts):
            draft_data = TestCaseDraftCreate.model_validate({
                **draft_data.model_dump(),
                "source_evidence": [
                    *draft_data.source_evidence,
                    {
                        "artifact_type": "test_import",
                        "artifact_id": job_id,
                        "source_api_import_id": job.get("source_api_import_id"),
                        "source_api_operation_id": job.get("source_api_operation_id"),
                    },
                ],
            })
            if index in targets:
                draft_data = draft_data.model_copy(update={"test_case_key": targets[index]["test_case_key"]})
            draft = await create_test_case_draft_record(
                job["project_id"],
                draft_data,
                user,
                parent_version_id=version_resolutions[index].target_version_id if index in targets else None,
                change_reason=version_resolutions[index].reason.strip() if index in targets else None,
            )
            created.append(draft)
        confirmed = await test_design_repository.confirm_import(
            job_id,
            job["project_id"],
            {
                "status": 'CONFIRMED',
                "created_draft_ids": [item["_id"] for item in created],
                "selected_indexes": selected,
                "separate_reasons": {str(index): payload.separate_reasons[index].strip() for index in payload.separate_indexes},
                "version_resolutions": {
                    str(index): resolution.model_dump() for index, resolution in version_resolutions.items()
                },
                "confirmed_at": now(),
            },
        )
        if confirmed.matched_count != 1:
            raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_CONFIRM_IN_PROGRESS"})
    except Exception:
        await test_design_repository.delete_created_drafts(job["project_id"], [item["_id"] for item in created])
        await test_design_repository.reset_import(job_id, job["project_id"])
        if created:
            await audit(
                user.id,
                "test_import_rolled_back",
                "TestImport",
                job_id,
                job["project_id"],
                {"draft_ids": [item["_id"] for item in created]},
            )
        raise
    return envelope({"job_id": job_id, "drafts": created})


async def export_test_cases(
    project_id: str,
    format: str,
    user: CurrentUser,
):
    
    await get_project(project_id, user, "testcase.export")
    versions = await test_design_repository.list_case_versions(
        {"project_id": project_id},
        20000,
        'test_case_key',
        1,
    )
    
    rows = [{
        "project_id": item.get("project_id"),
        "test_case_key": item.get("test_case_key"),
        "version": item.get("version"),
        "title": item.get("title"),
        "type": item.get("type"),
        "priority": item.get("priority"),
        "risk": item.get("risk"),
        "automation_status": item.get("automation_status"),
        "status": item.get("status"),
        "objective": plain_text(item.get("objective_doc", {})),
        "preconditions": plain_text(item.get("preconditions_doc", {})),
        "steps_json": json.dumps([
            {
                "id": step.get("id"),
                "action": plain_text(step.get("action_doc", {})),
                "expected": plain_text(step.get("expected_doc", {})),
                "test_data": step.get("test_data") or {},
            }
            for step in item.get("steps", [])
        ], ensure_ascii=False, separators=(",", ":")),
        "test_data_json": json.dumps(item.get("test_data") or {}, ensure_ascii=False, separators=(",", ":")),
        "expected_result": plain_text(item.get("expected_result_doc", {})),
        "postconditions": plain_text(item.get("postconditions_doc", {})),
        "tags": ",".join(item.get("tags", [])),
        "owner_id": item.get("owner_id"),
        "techniques": ",".join(item.get("techniques", [])),
        "data_set_version_ids": ",".join(item.get("data_set_version_ids", [])),
        "requirement_version_ids": ",".join(item.get("requirement_version_ids", [])),
        "acceptance_criterion_ids": ",".join(item.get("acceptance_criterion_ids", [])),
        "test_condition_ids": ",".join(item.get("test_condition_ids", [])),
        "scenario_id": item.get("scenario_id"),
        "plain_text_projection": item.get("plain_text_projection"),
    } for item in versions]
    fields = [
        "project_id", "test_case_key", "version", "title", "type", "priority", "risk",
        "automation_status", "status", "objective", "preconditions", "steps_json",
        "test_data_json", "expected_result", "postconditions", "tags", "owner_id",
        "techniques", "data_set_version_ids", "requirement_version_ids",
        "acceptance_criterion_ids", "test_condition_ids", "scenario_id",
        "plain_text_projection",
    ]
    if format == 'xlsx':
        content = create_xlsx([fields, *[[row.get(field) for field in fields] for row in rows]])
        return {
            "content": content,
            "media_type": 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            "filename": f"{'test-cases-'}{project_id}.xlsx",
        }
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return {
        "content": stream.getvalue(),
        "media_type": 'text/csv',
        "filename": f"{'test-cases-'}{project_id}.csv",
    }

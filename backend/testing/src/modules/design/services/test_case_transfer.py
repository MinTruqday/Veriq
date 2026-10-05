import csv
import io

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from src.core.auth import CurrentUser
from src.core.common import audit, envelope, get_project, get_project_entity, new_id, now
from src.repositories.test_design import test_design_repository
from src.core.rich_text import text_document
from src.schemas.contracts.design import TestCaseDraftCreate
from src.schemas.contracts.requirements import (
    ImportConfirm,
    ImportCreate,
)
from src.modules.integrations.services.api_artifact_formats import create_xlsx, lexical_similarity, model_metadata, terms
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
            if item.get("source_test_case_key") and item["source_test_case_key"] == existing.get("test_case_key"):
                score = 1
            elif item.get("source_projection") and item["source_projection"] == str(existing.get("plain_text_projection") or "").strip():
                score = 1
            else:
                score, _ = duplicate_score(candidate, existing)
            if score >= threshold:
                matches.append({"id": existing["_id"], "title": existing.get("title", ""), "score": score})
        results[index] = sorted(matches, key=lambda match: match["score"], reverse=True)[:3]
        previous.append({"_id": f"preview:{index}", **candidate, "test_case_key": item.get("source_test_case_key"), "plain_text_projection": item.get("source_projection")})
    return results


async def recover_trace_links(project_id: str, user: CurrentUser):
    
    await get_project(project_id, user, "trace.recover")
    requirements = await test_design_repository.list_requirement_versions(
        {"project_id": project_id, "status": 'BASELINED'},
        5000,
    )
    tests = await test_design_repository.list_case_versions(
        {"project_id": project_id, "status": 'ACTIVE'},
        10000,
    )
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
        if len(title) < 2 or bool(action) != bool(expected) or not (action or projection):
            invalid_rows.append(index)
            continue
        try:
            draft = TestCaseDraftCreate(
                title=title,
                type=row.get("type") or "custom",
                priority=row.get("priority") or "medium",
                risk=row.get("risk") or "medium",
                objective_doc=text_document(projection),
                preconditions_doc=text_document(str(row.get("precondition") or "").strip()),
                steps=[{
                    "id": "step-1",
                    "order": 1,
                    "action_doc": text_document(action),
                    "test_data": {},
                    "expected_doc": text_document(expected),
                }] if action else [],
                expected_result_doc=text_document(expected),
                postconditions_doc=text_document(""),
                tags=[item.strip() for item in (row.get("tags") or "").split(",") if item.strip()],
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
            "incomplete": not bool(action),
            "source_test_case_key": str(row.get("test_case_key") or "").strip(),
            "source_projection": projection,
            "draft": draft.model_dump(),
        })
    if invalid_rows:
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_ROWS_INCOMPLETE", "message": f"Có {len(invalid_rows)} dòng thiếu tên hoặc thiếu dữ liệu kiểm thử, bắt đầu từ dòng {invalid_rows[0]}", "rows": invalid_rows[:20], "count": len(invalid_rows)})
    if not preview:
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_EMPTY", "message": "Tệp không có ca kiểm thử để nhập"})
    comparisons = await compare_test_import_candidates(project_id, preview)
    for index, matches in comparisons.items():
        preview[index]["similar_cases"] = matches
    job = {
        "_id": new_id('TIMP'),
        "project_id": project_id,
        "filename": payload.filename,
        "format": payload.format,
        "preview": preview,
        "status": 'PREVIEW_READY',
        "created_by": user.id,
        "created_at": now(),
    }
    await test_design_repository.insert_import(job)
    return envelope(job)


async def upload_test_import(
    project_id: str,
    format: str,
    file: UploadFile,
    user: CurrentUser,
):
    
    if format not in ['csv', 'xlsx']:
        raise HTTPException(status_code=422, detail={"code": 'TEST_IMPORT_FORMAT_UNSUPPORTED'})
    data = await file.read()
    if len(data) > 20971520:
        raise HTTPException(status_code=413, detail={"code": 'IMPORT_TOO_LARGE'})
    content = (
        extract_xlsx_csv(data)
        if format == 'xlsx'
        else data.decode('utf-8-sig')
    )
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
    job_id: str, payload: ImportConfirm, user: CurrentUser
):
    
    job = await get_project_entity("test_imports", job_id, user, "testcase.import")
    if job["status"] == 'CONFIRMED':
        return envelope(job)
    selected = payload.selected_indexes
    if not selected:
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_SELECTION_REQUIRED"})
    if len(selected) != len(set(selected)):
        raise HTTPException(status_code=422, detail={"code": "DUPLICATE_PREVIEW_INDEX"})
    drafts = []
    for index in selected:
        if index < 0 or index >= len(job["preview"]):
            raise HTTPException(status_code=422, detail={"code": 'INVALID_PREVIEW_INDEX'})
        item = job["preview"][index]
        if item.get("incomplete") and not payload.accept_incomplete:
            raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_INCOMPLETE_ACK_REQUIRED", "message": "Cần xác nhận ca nhập chưa có bước và kết quả kiểm chứng"})
        if not item.get("draft"):
            raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_REUPLOAD_REQUIRED", "message": "Bản xem trước cũ cần được tải lên lại để kiểm tra nguồn dữ liệu"})
        drafts.append(TestCaseDraftCreate(**item["draft"]))
    comparisons = await compare_test_import_candidates(job["project_id"], job["preview"], selected)
    duplicates = [index for index in selected if comparisons[index] and index not in payload.separate_indexes]
    if duplicates:
        raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_DUPLICATE_REVIEW_REQUIRED", "message": "Cần bỏ chọn ca trùng hoặc ghi lý do tạo ca riêng", "indexes": duplicates, "matches": {index: comparisons[index] for index in duplicates}})
    if set(payload.separate_indexes) - {index for index in selected if comparisons[index] or job["preview"][index].get("similar_cases")}:
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_RESOLUTION_INVALID"})
    if any(not payload.separate_reasons.get(index, "").strip() for index in payload.separate_indexes):
        raise HTTPException(status_code=422, detail={"code": "TEST_IMPORT_SEPARATE_REASON_REQUIRED", "message": "Cần ghi lý do tạo ca kiểm thử riêng khi có ca gần giống"})
    claimed = await test_design_repository.claim_import(job_id, job["project_id"])
    if not claimed:
        raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_CONFIRM_IN_PROGRESS"})
    created = []
    try:
        for draft_data in drafts:
            draft = await create_test_case_draft_record(
                job["project_id"],
                draft_data,
                user,
            )
            created.append(draft)
        confirmed = await test_design_repository.confirm_import(
            job_id,
            job["project_id"],
            {
                "status": 'CONFIRMED',
                "created_draft_ids": [item["_id"] for item in created],
                "selected_indexes": selected,
                "separate_reasons": {index: payload.separate_reasons[index].strip() for index in payload.separate_indexes},
                "confirmed_at": now(),
            },
        )
        if confirmed.matched_count != 1:
            raise HTTPException(status_code=409, detail={"code": "TEST_IMPORT_CONFIRM_IN_PROGRESS"})
    except Exception:
        await test_design_repository.delete_created_import_drafts(job["project_id"], [item["_id"] for item in created])
        await test_design_repository.reset_import(job_id, job["project_id"])
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
    
    rows = [[item.get(field) for field in ['test_case_key',
 'version',
 'title',
 'type',
 'priority',
 'risk',
 'automation_status',
 'status',
 'plain_text_projection']] for item in versions]
    if format == 'xlsx':
        content = create_xlsx([['test_case_key',
 'version',
 'title',
 'type',
 'priority',
 'risk',
 'automation_status',
 'status',
 'plain_text_projection'], *rows])
        return {
            "content": content,
            "media_type": 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            "filename": f"{'test-cases-'}{project_id}.xlsx",
        }
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=['test_case_key',
 'version',
 'title',
 'type',
 'priority',
 'risk',
 'automation_status',
 'status',
 'plain_text_projection'])
    writer.writeheader()
    for item in versions:
        writer.writerow({field: item.get(field) for field in ['test_case_key',
 'version',
 'title',
 'type',
 'priority',
 'risk',
 'automation_status',
 'status',
 'plain_text_projection']})
    return {
        "content": stream.getvalue(),
        "media_type": 'text/csv',
        "filename": f"{'test-cases-'}{project_id}.csv",
    }

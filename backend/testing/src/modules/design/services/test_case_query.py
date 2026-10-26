import hashlib
import json

from fastapi import HTTPException

from src.core.common import audit, get_project, get_project_entity, now, page_payload, sort_spec
from src.schemas.contracts.design import TestCaseDraftCreate
from src.repositories.test_design import test_design_repository
from src.modules.design.services.test_case_records import create_test_case_draft_record




async def list_test_case_records(
    project_id,
    user,
    q="",
    key="",
    title="",
    status="",
    priority="",
    test_type="",
    technique="",
    stale_status="",
    automation_status="",
    requirement_id="",
    suite_id="",
    latest_result="",
    tag="",
    owner="",
    page=1,
    page_size=50,
    sort="-updated_at",
):
    await get_project(project_id, user, 'testcase.read')
    requirement_version_ids = set()
    if requirement_id:
        requirement_versions = await test_design_repository.list_requirement_version_ids(
            project_id, requirement_id, None
        )
        requirement_version_ids = {item["_id"] for item in requirement_versions}
        requirement_version_ids.add(requirement_id)
        items = await test_design_repository.list_cases_linked_to_requirement(
            project_id, sorted(requirement_version_ids), status
        )
        version_ids = [item["current_version_id"] for item in items if item.get("current_version_id")]
    else:
        tests = await test_design_repository.list_cases(
            project_id, status, 20000
        )
        version_ids = [item["current_version_id"] for item in tests if item.get("current_version_id")]
        versions = await test_design_repository.list_case_versions_by_ids(
            project_id, version_ids, 20000
        )
        by_id = {item["_id"]: item for item in versions}
        items = [{**item, "current_version": by_id.get(item.get("current_version_id"))} for item in tests]
    traces = await test_design_repository.list_confirmed_case_traces(
        project_id,
        version_ids,
        'CONFIRMED',
        50000,
    )
    trace_counts = {}
    for trace in traces:
        trace_counts[trace["target_id"]] = trace_counts.get(trace["target_id"], 0) + 1
    results = await test_design_repository.list_case_results(
        project_id, version_ids, 50000
    )
    latest_results = {}
    for result in results:
        latest_results.setdefault(result["test_case_version_id"], result.get("status"))
    suite_version_ids = set()
    if suite_id:
        suite = await test_design_repository.find_suite(suite_id, project_id)
        if not suite:
            raise HTTPException(status_code=422, detail={"code": 'INVALID_TEST_SUITE'})
        suite_version_ids = set(suite.get("test_case_version_ids", []))
    for item in items:
        version = item.get("current_version") or {}
        version_id = item.get("current_version_id")
        item["trace_count"] = trace_counts.get(version_id, 0)
        item["latest_result"] = latest_results.get(version_id)
        item["stale_status"] = version.get("stale_status") or (
            'STALE'
            if item.get("status") == 'NEEDS_UPDATE'
            else 'FRESH'
        )
        item["owner_id"] = version.get("owner_id")
        item["tags"] = sorted(set(item.get("tags", [])) | set(version.get("tags", [])))
    terms = [value.strip().lower() for value in (q, key, title) if value.strip()]
    if terms:
        items = [item for item in items if matches_test_case(item, terms)]
    field_filters = {
        "priority": priority,
        "type": test_type,
        "automation_status": automation_status,
        "owner_id": owner,
    }
    for field, value in field_filters.items():
        if value:
            items = [
                item
                for item in items
                if (item.get("current_version") or {}).get(field, item.get(field)) == value
            ]
    if technique:
        items = [item for item in items if technique in (item.get("current_version") or {}).get("techniques", [])]
    if tag:
        items = [item for item in items if tag in item.get("tags", [])]
    if stale_status:
        items = [item for item in items if item.get("stale_status") == stale_status]
    if latest_result:
        items = [item for item in items if item.get("latest_result") == latest_result]
    if requirement_id:
        items = [
            item
            for item in items
            if requirement_version_ids
            & set((item.get("current_version") or {}).get("requirement_version_ids", []))
        ]
    if suite_id:
        items = [item for item in items if item.get("current_version_id") in suite_version_ids]
    sort_field, direction = sort_spec(
        sort,
        {
            "test_case_key",
            "status",
            "updated_at",
            "created_at",
            "title",
            "priority",
            "stale_status",
            "latest_result",
        },
    )
    items.sort(
        key=lambda item: (
            str(
                (item.get("current_version") or {}).get(
                    sort_field, item.get(sort_field, "")
                )
                or ""
            ).casefold(),
            str(item.get("test_case_key") or item.get("_id") or "").casefold(),
        ),
        reverse=direction < 0,
    )
    total = len(items)
    start = (page - 1) * page_size
    payload = page_payload(items[start : start + page_size], page, page_size, total)
    if requirement_id:
        scope = [
            {
                "test_case_id": str(item.get("_id") or ""),
                "current_version_id": str(item.get("current_version_id") or ""),
                "status": item.get("status"),
                "version_revision": (item.get("current_version") or {}).get("revision"),
                "requirement_version_ids": sorted(
                    str(value)
                    for value in (item.get("current_version") or {}).get(
                        "requirement_version_ids", []
                    )
                ),
                "acceptance_criterion_ids": sorted(
                    str(value)
                    for value in (item.get("current_version") or {}).get(
                        "acceptance_criterion_ids", []
                    )
                ),
            }
            for item in items
        ]
        payload["scope_fingerprint"] = hashlib.sha256(
            json.dumps(scope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
    return payload


def matches_test_case(item, terms):
    version = item.get("current_version") or {}
    searchable = f"{item.get('test_case_key', '')} {version.get('title', '')}".lower()
    return all(value in searchable for value in terms)


async def list_test_case_drafts(
    project_id, limit, user, requirement_version_id="", status=""
):
    await get_project(project_id, user, 'testcase.read')
    if requirement_version_id:
        return await test_design_repository.list_related_case_drafts(
            project_id,
            requirement_version_id,
            None,
            [status] if status else None,
        )
    return await test_design_repository.list_case_drafts(project_id, limit)


async def get_test_case_record(test_case_id, user):
    test_case = await get_project_entity('test_cases', test_case_id, user, 'testcase.read')
    version = await test_design_repository.find_case_version(
        test_case.get("current_version_id"), test_case["project_id"]
    )
    return {**test_case, "current_version": version}


async def clone_test_case_record(test_case_id, payload, user):
    test_case = await get_project_entity('test_cases', test_case_id, user, 'testcase.clone')
    if test_case.get("current_version_id") != payload.expected_current_version_id:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT', "current_version_id": test_case.get("current_version_id")},
        )
    version = await test_design_repository.find_case_version(
        payload.expected_current_version_id, test_case["project_id"]
    )
    if not version or version.get("test_case_id") != test_case_id:
        raise HTTPException(status_code=422, detail={"code": 'TEST_CASE_VERSION_NOT_FOUND'})
    result = await create_test_case_draft_record(
        test_case["project_id"],
        TestCaseDraftCreate(
            title=payload.title or f"{version['title']}{' bản sao'}",
            type=version["type"],
            test_level=version.get("test_level"),
            test_kind=version.get("test_kind"),
            expected_impact=version.get("expected_impact") or "unassessed",
            assessment_reason=version.get("assessment_reason", ""),
            priority=version.get("priority") or "unassessed",
            risk=version.get("risk") or "unassessed",
            objective_doc=version.get("objective_doc", {"type": "doc", "content": []}),
            preconditions_doc=version["preconditions_doc"],
            steps=version["steps"],
            test_data=version["test_data"],
            expected_result_doc=version["expected_result_doc"],
            postconditions_doc=version["postconditions_doc"],
            tags=version.get("tags", []),
            required_skills=version.get("required_skills", []),
            custom_values=version.get("custom_values", {}),
            owner_id=version.get("owner_id"),
            techniques=version.get("techniques", []),
            automation_status=version.get(
                "automation_status", 'manual'
            ),
            attachments=version.get("attachments", []),
            data_set_version_ids=version.get("data_set_version_ids", []),
            requirement_version_ids=version.get("requirement_version_ids", []),
            acceptance_criterion_ids=version.get("acceptance_criterion_ids", []),
            coverage_item_ids=version.get("coverage_item_ids", []),
            test_condition_ids=version.get("test_condition_ids", []),
            scenario_id=version.get("scenario_id"),
            repository_node_id=version.get("repository_node_id"),
            bdd=version.get("bdd"),
            coverage_obligations=version.get("coverage_obligations", []),
            obligation_evidence=version.get("obligation_evidence", []),
            challenge_hypotheses=version.get("challenge_hypotheses", []),
            origin='clone',
            source_evidence=version.get("source_evidence", []),
            acceptance_criteria_snapshot_ids=version.get(
                "acceptance_criteria_snapshot_ids"
            ),
            evidence_refs=version.get("evidence_refs", []),
            evidence_quotes=version.get("evidence_quotes", []),
        ),
        user,
    )
    await audit(
        user.id,
        'test_case_cloned',
        'TestCaseDraft',
        result["_id"],
        test_case["project_id"],
        {"source_test_case_id": test_case_id, "source_version_id": version["_id"]},
    )
    return result


async def list_test_case_versions(test_case_id, user):
    await get_project_entity('test_cases', test_case_id, user, 'testcase.version.read')
    return await test_design_repository.list_versions_for_case(
        test_case_id, 500
    )


async def create_test_case_version_draft_record(test_case_id, payload, user):
    test_case = await get_project_entity('test_cases', test_case_id, user, 'testcase.version.create')
    expected_version_id = payload.expected_current_version_id
    if expected_version_id != test_case.get("current_version_id"):
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT', "current_version_id": test_case.get("current_version_id")},
        )
    reason = payload.change_reason.strip()
    version = await test_design_repository.find_case_version(
        expected_version_id, test_case["project_id"]
    )
    if not version or version.get("test_case_id") != test_case_id:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    result = await create_test_case_draft_record(
        test_case["project_id"],
        TestCaseDraftCreate(
            test_case_key=test_case["test_case_key"],
            title=payload.title or version["title"],
            type=version["type"],
            priority=version.get("priority") or "unassessed",
            risk=version.get("risk") or "unassessed",
            test_level=version.get("test_level"),
            test_kind=version.get("test_kind"),
            expected_impact=version.get("expected_impact") or "unassessed",
            assessment_reason=version.get("assessment_reason", ""),
            objective_doc=version.get("objective_doc", {"type": "doc", "content": []}),
            preconditions_doc=version["preconditions_doc"],
            steps=version["steps"],
            test_data=version["test_data"],
            expected_result_doc=version["expected_result_doc"],
            postconditions_doc=version["postconditions_doc"],
            tags=version.get("tags", []),
            required_skills=version.get("required_skills", []),
            custom_values=version.get("custom_values", {}),
            owner_id=version.get("owner_id"),
            techniques=version.get("techniques", []),
            automation_status=version.get(
                "automation_status", 'manual'
            ),
            attachments=version.get("attachments", []),
            data_set_version_ids=version.get("data_set_version_ids", []),
            requirement_version_ids=version.get("requirement_version_ids", []),
            acceptance_criterion_ids=version.get("acceptance_criterion_ids", []),
            test_condition_ids=version.get("test_condition_ids", []),
            coverage_item_ids=version.get("coverage_item_ids", []),
            scenario_id=version.get("scenario_id"),
            repository_node_id=version.get("repository_node_id"),
            bdd=version.get("bdd"),
            origin='manual',
            source_evidence=version.get("source_evidence", []),
            acceptance_criteria_snapshot_ids=version.get(
                "acceptance_criteria_snapshot_ids"
            ),
            coverage_obligations=version.get("coverage_obligations", []),
            obligation_evidence=version.get("obligation_evidence", []),
            evidence_refs=version.get("evidence_refs", []),
            evidence_quotes=version.get("evidence_quotes", []),
            challenge_hypotheses=version.get("challenge_hypotheses", []),
        ),
        user,
        parent_version_id=version["_id"],
        change_reason=reason,
    )
    return result


async def diff_test_case_version_records(test_case_id, from_version, to_version, user):
    test_case = await get_project_entity('test_cases', test_case_id, user, 'testcase.version.read')
    versions = await test_design_repository.list_selected_case_versions(
        test_case["project_id"], test_case_id, [from_version, to_version]
    )
    by_id = {item["_id"]: item for item in versions}
    if from_version not in by_id or to_version not in by_id:
        raise HTTPException(status_code=404, detail={"code": 'ENTITY_NOT_FOUND'})
    before = by_id[from_version]
    after = by_id[to_version]
    fields = [
        "title",
        "type",
        "test_level",
        "test_kind",
        "expected_impact",
        "assessment_reason",
        "priority",
        "risk",
        "objective_doc",
        "preconditions_doc",
        "steps",
        "test_data",
        "expected_result_doc",
        "postconditions_doc",
        "tags",
        "required_skills",
        "custom_values",
        "owner_id",
        "techniques",
        "automation_status",
        "attachments",
        "data_set_version_ids",
        "requirement_version_ids",
        "acceptance_criterion_ids",
        "coverage_item_ids",
        "test_condition_ids",
        "scenario_id",
        "repository_node_id",
        "bdd",
        "source_evidence",
        "evidence_refs",
        "evidence_quotes",
    ]
    return {
        "test_case_id": test_case_id,
        "from_version_id": from_version,
        "to_version_id": to_version,
        "changes": [
            {"field": field, "before": before.get(field), "after": after.get(field)}
            for field in fields
            if before.get(field) != after.get(field)
        ],
    }


async def set_test_case_obsolete(test_case_id, payload, user):
    test_case = await get_project_entity('test_cases', test_case_id, user, 'testcase.archive')
    if test_case.get("status") == 'OBSOLETE':
        return test_case
    if test_case.get("status") not in {
        'ACTIVE',
        'NEEDS_UPDATE',
    }:
        raise HTTPException(status_code=409, detail={"code": 'INVALID_STATE_TRANSITION'})
    if payload.expected_current_version_id != test_case.get("current_version_id"):
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT', "current_version_id": test_case.get("current_version_id")})
    reason = payload.reason.strip()
    timestamp = now()
    updated = await test_design_repository.set_case_lifecycle_status(
        test_case_id,
        test_case["project_id"],
        'OBSOLETE',
        {
            "obsolete_reason": reason,
            "obsolete_by": user.id,
            "obsolete_at": timestamp,
            "updated_at": timestamp,
        },
    )
    await audit(user.id, 'test_case_marked_obsolete', 'TestCase', test_case_id, test_case["project_id"], {"reason": reason})
    return updated


async def restore_test_case_record(test_case_id, payload, user):
    test_case = await get_project_entity('test_cases', test_case_id, user, 'testcase.restore')
    if test_case.get("status") != 'OBSOLETE':
        return test_case
    if payload.expected_current_version_id != test_case.get("current_version_id"):
        raise HTTPException(status_code=409, detail={"code": 'REVISION_CONFLICT'})
    reason = payload.reason.strip()
    timestamp = now()
    updated = await test_design_repository.set_case_lifecycle_status(
        test_case_id,
        test_case["project_id"],
        'ACTIVE',
        {
            "restore_reason": reason,
            "restored_by": user.id,
            "restored_at": timestamp,
            "updated_at": timestamp,
        },
    )
    await audit(user.id, 'test_case_restored', 'TestCase', test_case_id, test_case["project_id"], {"reason": reason})
    return updated

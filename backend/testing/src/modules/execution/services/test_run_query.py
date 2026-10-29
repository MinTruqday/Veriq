import csv
import io
import re

from fastapi import HTTPException

from src.core.common import (
    get_project,
    get_project_entity,
    load_user_identities,
    page_payload,
    sort_spec,
)
from src.repositories.test_run import test_run_repository


def _public_assignment_decisions(run):
    decisions = {}
    for version_id, decision in (run.get("test_case_assignment_decisions") or {}).items():
        safe_decision = dict(decision)
        safe_decision["matched_skill_evidence"] = [
            {
                key: item[key]
                for key in ("name", "level", "source_kind", "confirmed")
                if key in item
            }
            for item in decision.get("matched_skill_evidence") or []
        ]
        decisions[version_id] = safe_decision
    return decisions


async def list_test_run_records(
    project_id,
    user,
    name="",
    release="",
    release_id="",
    build="",
    build_id="",
    environment="",
    environment_id="",
    status="",
    created_by="",
    page=1,
    page_size=50,
    sort="-updated_at",
):
    
    await get_project(project_id, user, "testrun.read")
    query = {"project_id": project_id}
    if name:
        query["name"] = {"$regex": re.escape(name), "$options": "i"}
    if status:
        query["status"] = status
    for field, value in {
        "release": release,
        "release_id": release_id,
        "build": build,
        "build_id": build_id,
        "environment": environment,
        "environment_id": environment_id,
        "created_by": created_by,
    }.items():
        if value:
            query[field] = value
    sort_field, direction = sort_spec(
        sort,
        set(['name', 'release', 'build', 'environment', 'status', 'created_by', 'created_at', 'updated_at']),
    )
    total = await test_run_repository.count_runs(query)
    items = await test_run_repository.list_runs(
        query, sort_field, direction, (page - 1) * page_size, page_size
    )
    return page_payload(items, page, page_size, total)


async def list_test_result_records(project_id, user, status=""):
    
    await get_project(project_id, user, "testrun.read")
    query = {"project_id": project_id}
    statuses = [value.strip() for value in status.split(",") if value.strip()]
    if statuses:
        allowed = set(['NOT_RUN', 'IN_PROGRESS', 'PASS', 'FAIL', 'BLOCKED', 'SKIPPED', 'NOT_APPLICABLE'])
        if not set(statuses) <= allowed:
            raise HTTPException(
                status_code=422, detail={"code": 'INVALID_TEST_RESULT_STATUS'}
            )
        query["status"] = {"$in": statuses}
    return await test_run_repository.list_results(
        query, 5000, "updated_at", -1
    )


async def get_test_run_record(run_id, user):
    
    run = await get_project_entity("test_runs", run_id, user, "testrun.read")
    versions = await test_run_repository.list_versions(
        run["test_case_version_ids"], 10000
    )
    results = await test_run_repository.list_results(
        {"test_run_id": run_id}, 10000
    )
    defects = await test_run_repository.list_defects_for_results(
        run["project_id"], [item["_id"] for item in results], 10000
    )
    decision_assignees = {
        decision.get("assignee_id")
        for decision in (run.get("test_case_assignment_decisions") or {}).values()
        if decision.get("assignee_id")
    }
    assigned_users = set((run.get("test_case_assignments") or {}).values()) | decision_assignees
    try:
        identities = await load_user_identities(assigned_users)
    except HTTPException as error:
        if error.status_code != 503:
            raise
        identities = {}
    return {
        **run,
        "test_case_assignment_decisions": _public_assignment_decisions(run),
        "test_case_versions": versions,
        "results": results,
        "defects": defects,
        "test_case_assignment_identities": {
            user_id: {
                "display_name": identity.get("full_name") or user_id,
            }
            for user_id, identity in identities.items()
        },
    }


async def get_test_result_record(result_id, user):
    result = await test_run_repository.find_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    await get_project(result["project_id"], user, "testrun.read")
    run = await test_run_repository.find_run(
        result.get("test_run_id"), result["project_id"]
    )
    if not run:
        raise HTTPException(status_code=404, detail={"code": "TEST_RUN_NOT_FOUND"})
    versions = await test_run_repository.list_versions(
        [result.get("test_case_version_id")], 1
    )
    defects = await test_run_repository.list_defects_for_results(
        result["project_id"], [result_id], 100
    )
    return {
        **result,
        "test_run": {
            **run,
            "test_case_assignment_decisions": _public_assignment_decisions(run),
        },
        "test_case_version": versions[0] if versions else None,
        "defects": defects,
    }


async def build_test_run_report(run_id, user):
    
    run = await get_project_entity("test_runs", run_id, user, "report.export")
    versions = await test_run_repository.list_versions(
        run["test_case_version_ids"], 10000
    )
    results = await test_run_repository.list_results(
        {"test_run_id": run_id}, 10000
    )
    by_result = {item["test_case_version_id"]: item for item in results}
    identities = await load_user_identities(item.get("executed_by") for item in results)
    
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=['run_id',
 'run_name',
 'environment',
 'build',
 'test_case_key',
 'test_case_version',
 'title',
 'result',
 'executed_by',
 'executed_by_name',
 'executed_by_email',
 'executed_at',
 'note'])
    writer.writeheader()
    for version in versions:
        result = by_result.get(version["_id"], {})
        identity = identities.get(result.get("executed_by"), {})
        writer.writerow(
            {
                "run_id": run_id,
                "run_name": run["name"],
                "environment": run.get("environment"),
                "build": run.get("build"),
                "test_case_key": version.get("test_case_key"),
                "test_case_version": version.get("version"),
                "title": version.get("title"),
                "result": result.get("status", 'NOT_RUN'),
                "executed_by": result.get("executed_by"),
                "executed_by_name": identity.get("full_name"),
                "executed_by_email": identity.get("email"),
                "executed_at": result.get("executed_at")
                or result.get("completed_at")
                or result.get("updated_at"),
                "note": result.get("note"),
            }
        )
    return stream.getvalue()

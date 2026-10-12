import re

from fastapi import HTTPException

from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    new_id,
    now,
    optimistic_patch,
    sort_spec,
)
from src.repositories.test_design import test_design_repository
from src.modules.execution.services.execution_state import validate_test_versions





async def create_test_suite_record(payload, project_id, user):
    if project_id and project_id != payload.project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_SCOPE_MISMATCH'})
    await get_project(payload.project_id, user, "testsuite.create")
    await validate_test_versions(payload.project_id, payload.test_case_version_ids)
    timestamp = now()
    suite = {
        "_id": new_id('TSU'),
        **payload.model_dump(),
        "status": 'ACTIVE',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await test_design_repository.insert_suite(suite)
    await audit(user.id, "test_suite_created", "TestSuite", suite["_id"], payload.project_id)
    return suite


async def list_test_suite_records(
    project_id,
    user,
    q="",
    suite_type="",
    status="",
    sort="-updated_at",
):
    await get_project(project_id, user, "testsuite.read")
    query = {"project_id": project_id}
    if q:
        query["name"] = {"$regex": re.escape(q), "$options": "i"}
    for field, value in {"suite_type": suite_type, "status": status}.items():
        if value:
            query[field] = value
    sort_field, direction = sort_spec(
        sort,
        set(['name', 'suite_type', 'status', 'created_at', 'updated_at']),
    )
    return await test_design_repository.list_suites(query, sort_field, direction)


async def get_test_suite_record(suite_id, user, permission="testsuite.read"):
    return await get_project_entity("test_suites", suite_id, user, permission)


async def update_test_suite_record(suite_id, payload, user):
    suite = await get_test_suite_record(suite_id, user, "testsuite.update")
    if suite.get("status", 'ACTIVE') == 'ARCHIVED':
        raise HTTPException(status_code=409, detail={"code": 'TEST_SUITE_ARCHIVED'})
    if payload.test_case_version_ids is not None:
        await validate_test_versions(suite["project_id"], payload.test_case_version_ids)
    updated = await optimistic_patch(
        "test_suites",
        suite_id,
        suite["project_id"],
        payload.expected_revision,
        payload.model_dump(),
    )
    await audit(user.id, "test_suite_updated", "TestSuite", suite_id, suite["project_id"])
    return updated


async def clone_test_suite_record(suite_id, user):
    suite = await get_test_suite_record(suite_id, user, "testsuite.clone")
    timestamp = now()
    cloned = {
        **suite,
        "_id": new_id('TSU'),
        "name": f"{suite['name']} bản sao",
        "status": 'ACTIVE',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    for field in ("archived_at", "archived_by", "archive_reason"):
        cloned.pop(field, None)
    await test_design_repository.insert_suite(cloned)
    await audit(
        user.id,
        "test_suite_cloned",
        "TestSuite",
        cloned["_id"],
        suite["project_id"],
        {"source_suite_id": suite_id},
    )
    return cloned


async def archive_test_suite_record(suite_id, payload, user):
    suite = await get_test_suite_record(suite_id, user, "testsuite.archive")
    updated = await optimistic_patch(
        "test_suites",
        suite_id,
        suite["project_id"],
        payload.expected_revision,
        {
            "status": 'ARCHIVED',
            "archive_reason": payload.reason,
            "archived_by": user.id,
            "archived_at": now(),
        },
    )
    await audit(user.id, "test_suite_archived", "TestSuite", suite_id, suite["project_id"])
    return updated

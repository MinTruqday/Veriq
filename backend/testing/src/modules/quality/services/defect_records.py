import csv
import io
import re

from fastapi import HTTPException

from src.core.common import (
    audit,
    get_project,
    get_project_entity,
    get_project_role,
    new_id,
    next_key,
    now,
    page_payload,
    sort_spec,
    visible_defect,
)
from src.core.database import database
from src.repositories.defect import defect_repository
from src.modules.execution.services.execution_context import (
    defect_blocks_release,
    recheck_release_gates_for_defect,
    resolve_execution_context,
    serialize_release_gate,
)
from src.clients.project_knowledge import index_artifact
from src.clients.ai_automation import emit_defect_recorded


async def create_defect_record(project_id, payload, user):
    
    if project_id != payload.project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    await get_project(project_id, user, "defect.create")
    linked_result = None
    linked_run = None
    if payload.linked_test_result_id:
        linked_result = await defect_repository.find_test_result(
            payload.linked_test_result_id, project_id
        )
        if not linked_result or linked_result["status"] != 'FAIL':
            raise HTTPException(status_code=422, detail={"code": 'DEFECT_REQUIRES_FAILED_RESULT'})
        linked_run = await defect_repository.find_test_run(
            linked_result.get("test_run_id"), project_id
        )
        if not linked_run:
            raise HTTPException(status_code=409, detail={"code": "DEFECT_TEST_RUN_CONTEXT_UNAVAILABLE"})
    for field in ("release_id", "build_id", "environment_id"):
        supplied = getattr(payload, field)
        run_value = linked_run.get(field) if linked_run else None
        if supplied and run_value and supplied != run_value:
            raise HTTPException(
                status_code=422,
                detail={"code": "DEFECT_EXECUTION_CONTEXT_MISMATCH", "field": field},
            )
    context = await resolve_execution_context(
        project_id,
        user,
        release_id=payload.release_id or (linked_run or {}).get("release_id"),
        build_id=payload.build_id or (linked_run or {}).get("build_id"),
        environment_id=payload.environment_id or (linked_run or {}).get("environment_id"),
        release=payload.release or (linked_run or {}).get("release", ""),
        build=payload.build or (linked_run or {}).get("build", ""),
        environment=payload.environment or (linked_run or {}).get("environment", ""),
    )
    timestamp = now()
    defect = {
        "_id": new_id('DEF'),
        **payload.model_dump(),
        **context,
        "defect_key": payload.defect_key
        or await next_key(project_id, 'defect', 'DEF'),
        "status": 'NEW',
        "revision": 1,
        "created_by": user.id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    async with await database.client.start_session() as session:
        async with session.start_transaction():
            if defect_blocks_release(defect):
                await serialize_release_gate(
                    project_id,
                    [context.get("release_id")],
                    session,
                    require_open_release_ids=[context.get("release_id")],
                )
            await defect_repository.insert_defect(defect, session=session)
            await audit(
                user.id,
                "defect_created",
                "Defect",
                defect["_id"],
                project_id,
                session=session,
            )
            await emit_defect_recorded(defect, user, session=session)
            if defect_blocks_release(defect):
                await recheck_release_gates_for_defect(
                    project_id, [defect.get("release_id")], defect, user, session
                )
    await index_artifact(
        project_id,
        "defect",
        defect["_id"],
        defect["_id"],
        defect["title"],
        " ".join(
            [defect["title"], str(defect.get("environment", "")), str(defect.get("build", ""))]
        ),
        defect["status"],
        'PROJECT_REFERENCE',
        1,
        linked_test_result_id=defect.get("linked_test_result_id"),
        linked_requirement_version_ids=defect.get("linked_requirement_version_ids", []),
    )
    return defect


async def list_defect_records(
    project_id,
    user,
    q="",
    key="",
    title="",
    status="",
    severity="",
    priority="",
    assignee="",
    release="",
    release_id="",
    environment="",
    environment_id="",
    build="",
    build_id="",
    requirement_id="",
    test_case_id="",
    page=1,
    page_size=50,
    sort="-updated_at",
):
    
    await get_project(project_id, user, "defect.read")
    query = {"project_id": project_id}
    search_terms = [value.strip() for value in (q, key, title) if value.strip()]
    if search_terms:
        query["$and"] = [
            {
                "$or": [
                    {"defect_key": {"$regex": re.escape(value), "$options": "i"}},
                    {"title": {"$regex": re.escape(value), "$options": "i"}},
                ]
            }
            for value in search_terms
        ]
    if status:
        query["status"] = status
    for field, value in {
        "severity": severity,
        "priority": priority,
        "assignee": assignee,
        "release": release,
        "release_id": release_id,
        "environment": environment,
        "environment_id": environment_id,
        "build": build,
        "build_id": build_id,
        "linked_test_case_version_id": test_case_id,
    }.items():
        if value:
            query[field] = value
    if requirement_id:
        version_ids = await defect_repository.list_requirement_version_ids(
            project_id, requirement_id, 1000
        )
        version_ids.append(requirement_id)
        query["linked_requirement_version_ids"] = {"$in": version_ids}
    if test_case_id:
        version_ids = await defect_repository.list_test_case_version_ids(
            project_id, test_case_id, 1000
        )
        version_ids.append(test_case_id)
        query["linked_test_case_version_id"] = {"$in": version_ids}
    sort_field, direction = sort_spec(
        sort,
        set(['defect_key',
 'title',
 'status',
 'severity',
 'priority',
 'assignee',
 'release',
 'build',
 'environment',
 'created_at',
 'updated_at']),
    )
    total = await defect_repository.count_defects(query)
    items = await defect_repository.list_defects(
        query, sort_field, direction, (page - 1) * page_size, page_size
    )
    role = await get_project_role(project_id, user.id)
    return page_payload([visible_defect(item, role) for item in items], page, page_size, total)


async def build_defect_export(project_id, user):
    
    await get_project(project_id, user, "report.export")
    defects = await defect_repository.list_project_defects(project_id, 10000)
    
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=['defect_key', 'title', 'severity', 'priority', 'status', 'environment', 'build', 'assignee'])
    writer.writeheader()
    for defect in defects:
        writer.writerow({field: defect.get(field) for field in ['defect_key', 'title', 'severity', 'priority', 'status', 'environment', 'build', 'assignee']})
    return stream.getvalue()


async def get_defect_record(defect_id, project_id, user):
    
    defect = await get_project_entity("defects", defect_id, user, "defect.read")
    if project_id is not None and defect["project_id"] != project_id:
        raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
    role = await get_project_role(defect["project_id"], user.id)
    trace_links = await defect_repository.list_trace_links(
        defect["project_id"],
        defect_id,
        'defect',
        500,
    )
    comments = (
        []
        if role == 'VIEWER'
        else await defect_repository.list_comments(
            defect["project_id"],
            defect_id,
            'defect',
            500,
        )
    )
    attachments = (
        []
        if role == 'VIEWER'
        else await defect_repository.list_attachments(
            defect["project_id"],
            defect_id,
            'defect',
            'ACTIVE',
            500,
        )
    )
    return {
        **visible_defect(defect, role),
        "trace_links": trace_links,
        "comments": comments,
        "attachments": attachments,
    }

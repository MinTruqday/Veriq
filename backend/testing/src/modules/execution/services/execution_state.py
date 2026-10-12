import hashlib
from bson.json_util import dumps as bson_dumps
from fastapi import HTTPException
from src.repositories.execution_policy import execution_policy_repository



FROZEN_RUN_SCOPE_FIELDS = tuple(['test_plan_id',
 'test_suite_ids',
 'test_case_version_ids',
 'environment',
 'environment_id',
 'release',
 'release_id',
 'build',
 'build_id',
 'device_matrix_id',
 'device_profile_keys',
 'device_matrix_snapshot'])
def defect_transitions():
    return {"NEW": {"CONFIRMED", "DUPLICATE", "REJECTED"}, "CONFIRMED": {"DUPLICATE", "IN_PROGRESS", "REJECTED"}, "IN_PROGRESS": {"RESOLVED"}, "RESOLVED": {"READY_FOR_RETEST", "REOPENED"}, "READY_FOR_RETEST": set(), "REOPENED": {"IN_PROGRESS", "RESOLVED"}, "CLOSED": {"REOPENED"}, "REJECTED": {"REOPENED"}, "DUPLICATE": {"REOPENED"}}


def execution_transitions():
    return {"NOT_RUN": {"IN_PROGRESS", "SKIPPED"}, "IN_PROGRESS": {"BLOCKED", "FAIL", "NOT_APPLICABLE", "PASS", "SKIPPED"}, "PASS": set(), "FAIL": set(), "BLOCKED": set(), "SKIPPED": set(), "NOT_APPLICABLE": set()}


def frozen_run_scope(run):
    return {field: run.get(field) for field in FROZEN_RUN_SCOPE_FIELDS}


def frozen_run_scope_hash(scope):
    canonical = bson_dumps(scope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def enforce_not_applicable_policy(project_id, status, step_results=None):
    uses_not_applicable = status == 'NOT_APPLICABLE' or any(
        item.status == 'NOT_APPLICABLE' for item in step_results or []
    )
    if not uses_not_applicable:
        return
    project = await execution_policy_repository.project_settings(project_id)
    if not project or not (project.get("settings") or {}).get(
        'allow_not_applicable_results',
        False,
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": 'NOT_APPLICABLE_POLICY_DISABLED'},
        )


async def select_resume_execution(run, user):
    version_ids = list(run.get("test_case_version_ids", []))
    membership = await execution_policy_repository.active_membership_role(
        run["project_id"], user.id, 'ACTIVE'
    )
    assignments = run.get("test_case_assignments") or {}
    eligible_ids = version_ids
    
    if membership and membership.get("project_role") == 'TESTER':
        explicit_ids = [
            version_id for version_id in version_ids if assignments.get(version_id) == user.id
        ]
        if explicit_ids:
            eligible_ids = explicit_ids
            
        elif run.get("assignee_id") == user.id:
            eligible_ids = [
                version_id for version_id in version_ids if version_id not in assignments
            ]
            
        elif run.get("assignee_id") or assignments:
            raise HTTPException(
                status_code=403,
                detail={"code": 'TEST_RUN_ASSIGNMENT_REQUIRED'},
            )
    results = await execution_policy_repository.list_results(run["_id"], eligible_ids)
    by_version = {item["test_case_version_id"]: item for item in results}
    current_version_id = next(
        (
            version_id
            for version_id in eligible_ids
            if by_version.get(version_id, {}).get("status")
            == 'IN_PROGRESS'
        ),
        None,
    )
    if current_version_id is None:
        current_version_id = next(
            (
                version_id
                for version_id in eligible_ids
                if by_version.get(version_id, {}).get("status")
                == 'NOT_RUN'
            ),
            None,
        )
    current_execution = by_version.get(current_version_id) if current_version_id else None
    current_version = (
        await execution_policy_repository.find_test_case_version(
            current_version_id, run["project_id"]
        )
        if current_version_id
        else None
    )
    return {
        "current_execution": current_execution,
        "current_test_case_version": current_version,
        "position": version_ids.index(current_version_id) + 1 if current_version_id else None,
        "total_count": len(version_ids),
        "remaining_count": sum(
            by_version.get(version_id, {}).get("status")
            in set(['NOT_RUN', 'IN_PROGRESS'])
            for version_id in eligible_ids
        ),
        "assignment_mode": 'RUN_ASSIGNMENT',
    }


async def replay_resume_event(run, event):
    execution = (
        await execution_policy_repository.find_result(event.get("current_execution_id"))
        if event.get("current_execution_id")
        else None
    )
    version = (
        await execution_policy_repository.find_test_case_version(
            event.get("current_test_case_version_id"), run["project_id"]
        )
        if event.get("current_test_case_version_id")
        else None
    )
    return {
        "run": run,
        "resume_event": event,
        "current_execution": execution,
        "current_test_case_version": version,
        "position": event.get("position"),
        "total_count": event.get("total_count", len(run.get("test_case_version_ids", []))),
        "remaining_count": event.get("remaining_count", 0),
        "assignment_mode": event.get(
            "assignment_mode", 'PROJECT_SCOPE'
        ),
        "scope_fingerprint": event.get("scope_fingerprint"),
    }


async def validate_test_versions(project_id, version_ids):
    count = await execution_policy_repository.count_test_case_versions(
        project_id, version_ids
    )
    if count != len(set(version_ids)):
        raise HTTPException(
            status_code=422,
            detail={"code": 'CROSS_PROJECT_OR_MISSING_TEST_VERSION'},
        )

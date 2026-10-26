from fastapi import HTTPException
from pymongo.errors import OperationFailure

from src.core.auth import CurrentUser
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, get_project_entity, new_id, now, optimistic_patch
from src.core.database import database
from src.repositories.execution_context import execution_context_repository
from src.schemas.contracts.execution import ReleaseReadiness, ReleaseReadinessCheck


async def serialize_release_gate(
    project_id,
    release_ids,
    session,
    expected_gate_revisions=None,
    require_open_release_ids=None,
    required_statuses=None,
):
    expected_gate_revisions = expected_gate_revisions or {}
    require_open_release_ids = set(require_open_release_ids or [])
    required_statuses = required_statuses or {}
    for release_id in sorted({str(value) for value in release_ids if value}):
        expected = expected_gate_revisions.get(release_id)
        try:
            updated = await execution_context_repository.advance_release_gate_revision(
                project_id,
                release_id,
                session=session,
                expected_revision=expected,
                required_status=required_statuses.get(release_id),
                require_open=release_id in require_open_release_ids,
            )
        except OperationFailure as error:
            raise_release_gate_conflict(error)
            raise
        if not updated:
            raise HTTPException(
                status_code=409,
                detail={"code": "RELEASE_GATE_REVISION_CONFLICT", "release_id": release_id},
            )


def raise_release_gate_conflict(error):
    if error.code == 112 or error.has_error_label("TransientTransactionError"):
        raise HTTPException(
            status_code=409,
            detail={"code": "RELEASE_GATE_REVISION_CONFLICT"},
        ) from error


def defect_blocks_release(defect, *, status=None, severity=None):
    current_status = str(status if status is not None else defect.get("status") or "")
    current_severity = str(
        severity if severity is not None else defect.get("severity") or ""
    )
    return current_status.upper() in {
        "NEW",
        "CONFIRMED",
        "IN_PROGRESS",
        "READY_FOR_RETEST",
        "REOPENED",
    } and current_severity.lower() in {"blocker", "critical"}





async def recheck_release_gates_for_defect(project_id, release_ids, defect, user, session):
    from src.clients.ai_automation import emit_release_gate_recheck

    for release_id in sorted({str(value) for value in release_ids if value}):
        release = await database.value.releases.find_one(
            {"_id": release_id, "project_id": project_id},
            session=session,
        )
        if release and release.get("status") == "ACTIVE":
            await emit_release_gate_recheck(
                release,
                defect,
                user,
                session=session,
                artifact_type="defect",
            )


async def ensure_release_completion_gate(
    project_id: str, release_id: str, session=None, automation_run_id=None
):
    from src.schemas.test_completion import completion_hash, completion_snapshot
    from src.modules.execution.services.test_completion_readiness import (
        validate_completion_outcome,
        validate_completion_readiness,
    )

    if automation_run_id:
        plans = await execution_context_repository.list_approved_test_plan_scopes(
            project_id, release_id, session=session
        )
        reports = await execution_context_repository.list_automation_completions(
            project_id, release_id, str(automation_run_id), session=session
        )
        plan_ids = {item.get("_id") for item in plans if item.get("_id")}
        report_plan_ids = [item.get("test_plan_id") for item in reports]
        if not plan_ids or len(reports) != len(plan_ids) or set(report_plan_ids) != plan_ids:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "RELEASE_COMPLETION_GATE_FAILED",
                    "reason_code": "AUTOMATED_COMPLETION_SCOPE_INCOMPLETE",
                    "test_plan_ids": sorted(plan_ids - set(report_plan_ids)),
                },
            )
        reports_to_validate = reports
    else:
        plans = await execution_context_repository.list_approved_test_plan_scopes(
            project_id, release_id, session=session
        )
        plan_ids = {str(item.get("_id")) for item in plans if item.get("_id")}
        reports = await execution_context_repository.list_approved_completions(
            project_id, release_id, ["APPROVED", "CLOSED"], session=session
        )
        latest_by_plan = {}
        for item in reports:
            plan_id = item.get("test_plan_id")
            if plan_id and str(plan_id) in plan_ids and str(plan_id) not in latest_by_plan:
                latest_by_plan[str(plan_id)] = item
        if not plan_ids or set(latest_by_plan) != plan_ids:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "RELEASE_COMPLETION_GATE_FAILED",
                    "reason_code": "COMPLETION_PLAN_REPORT_SCOPE_INCOMPLETE",
                    "test_plan_ids": sorted(plan_ids - set(latest_by_plan)),
                },
            )
        reports_to_validate = list(latest_by_plan.values())
        for report in reports_to_validate:
            qa_signed = any(
                item.get("role") == "QA" and item.get("decision") == "APPROVE"
                for item in report.get("sign_offs", [])
            )
            snapshot = report.get("approved_snapshot")
            if (
                not report.get("approved_by")
                or not report.get("approved_at")
                or not qa_signed
                or not isinstance(snapshot, dict)
                or snapshot != completion_snapshot(report)
                or report.get("approved_snapshot_hash") != completion_hash(report)
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "RELEASE_COMPLETION_GATE_FAILED",
                        "reason_code": "APPROVED_COMPLETION_SNAPSHOT_INVALID",
                        "test_plan_id": report.get("test_plan_id"),
                    },
                )

    for report in reports_to_validate:
        automated = bool(automation_run_id)
        scope = report.get("scope_snapshot")
        report_snapshot = report.get("automation_gate_snapshot") if automated else report.get("approved_snapshot")
        report_hash = report.get("automation_gate_hash") if automated else report.get("approved_snapshot_hash")
        if (
            (automated and (report.get("status") != "DRAFT" or report.get("automation_run_id") != str(automation_run_id)))
            or not report.get("test_plan_id")
            or not report.get("monitoring_snapshot_id")
            or not isinstance((scope or {}).get("runs"), list)
            or not isinstance(report_snapshot, dict)
            or report_snapshot != completion_snapshot(report)
            or report_hash != completion_hash(report)
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "RELEASE_COMPLETION_GATE_FAILED",
                    "reason_code": "AUTOMATED_COMPLETION_SNAPSHOT_INVALID" if automated else "APPROVED_COMPLETION_SNAPSHOT_INVALID",
                    "test_plan_id": report.get("test_plan_id"),
                },
            )
        try:
            validate_completion_outcome(report)
            if automated:
                await validate_completion_readiness(report)
        except OperationFailure as error:
            raise_release_gate_conflict(error)
            raise
        except HTTPException as error:
            detail = error.detail if isinstance(error.detail, dict) else {}
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "RELEASE_COMPLETION_GATE_FAILED",
                    "reason_code": detail.get("reason_code", "COMPLETION_REPORT_NOT_RELEASE_READY"),
                    "completion_details": detail,
                    "test_plan_id": report.get("test_plan_id"),
                },
            ) from error
        run_ids = [item.get("run_id") for item in scope["runs"] if item.get("run_id")]
        evidence_since = report.get("created_at") if automated else report.get("approved_at")
        if await execution_context_repository.release_snapshot_sources_changed(
            project_id,
            report["monitoring_snapshot_id"],
            release_id=release_id,
            test_plan_id=report["test_plan_id"],
            run_ids=run_ids,
            session=session,
        ) or await execution_context_repository.release_evidence_changed_since(
            project_id,
            release_id,
            run_ids,
            evidence_since,
            session=session,
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "RELEASE_COMPLETION_GATE_FAILED",
                    "reason_code": "COMPLETION_REPORT_STALE",
                    "test_plan_id": report.get("test_plan_id"),
                },
            )

    report = max(
        reports_to_validate,
        key=lambda item: item.get("approved_at") or item.get("created_at") or now(),
    )
    if not report:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RELEASE_COMPLETION_GATE_FAILED",
                "reason_code": "AUTOMATED_COMPLETION_REPORT_REQUIRED",
            },
        )
    open_blockers = await execution_context_repository.list_open_blocking_defects(
        project_id, release_id, session=session
    )
    if open_blockers:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RELEASE_COMPLETION_GATE_FAILED",
                "reason_code": "OPEN_BLOCKING_DEFECTS",
                "defect_ids": [item["_id"] for item in open_blockers],
            },
        )
    return report


async def ensure_release_assurance_gate(
    project_id: str, release_id: str, session=None, completion_approved_at=None
):
    from src.modules.design.services.test_adequacy import (
        _as_datetime,
        coverage_item_ready_for_assurance,
    )
    from src.modules.execution.services.test_plan import verified_approved_plan_snapshot

    plans = await execution_context_repository.list_approved_test_plan_scopes(
        project_id, release_id, session=session
    )
    if not plans:
        raise HTTPException(
            status_code=409,
            detail={"code": "RELEASE_TEST_PLAN_SCOPE_REQUIRED"},
        )
    snapshots = []
    invalid_plan_ids = []
    for plan in plans:
        try:
            snapshot, _ = verified_approved_plan_snapshot(plan, project_id)
        except HTTPException:
            invalid_plan_ids.append(plan.get("_id"))
            continue
        if snapshot.get("release_id") != release_id:
            invalid_plan_ids.append(plan.get("_id"))
            continue
        snapshots.append(snapshot)
    if invalid_plan_ids:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RELEASE_TEST_PLAN_SNAPSHOT_INVALID",
                "test_plan_ids": sorted(value for value in invalid_plan_ids if value),
            },
        )
    requirement_version_ids = sorted(
        {
            requirement_version_id
            for snapshot in snapshots
            for requirement_version_id in snapshot.get("requirement_version_ids", [])
        }
    )
    if not requirement_version_ids:
        raise HTTPException(
            status_code=409,
            detail={"code": "RELEASE_REQUIREMENT_SCOPE_REQUIRED"},
        )
    assessments = {
        item["requirement_version_id"]: item
        for item in await execution_context_repository.list_adequacy_assessments(
            project_id, requirement_version_ids, session=session
        )
    }
    waiver_owner_ids = [
        (item.get("decision") or {}).get("waiver_owner_id")
        for assessment in assessments.values()
        for item in assessment.get("coverage_items", [])
        if item.get("status") == "WAIVED"
        and (item.get("decision") or {}).get("waiver_owner_id")
    ]
    active_waiver_owners = set(
        await execution_context_repository.list_active_member_ids(
            project_id, waiver_owner_ids, session=session
        )
    )
    timestamp = now()
    completion_timestamp = _as_datetime(completion_approved_at)
    invalid = []
    for requirement_version_id in requirement_version_ids:
        assessment = assessments.get(requirement_version_id)
        if (
            not assessment
            or assessment.get("requirement_version_id") != requirement_version_id
            or assessment.get("status") not in {"ASSURED", "CONDITIONAL"}
        ):
            invalid.append(requirement_version_id)
            continue
        assessment_updated_at = _as_datetime(assessment.get("updated_at"))
        if (
            completion_timestamp
            and (
                not assessment_updated_at
                or assessment_updated_at > completion_timestamp
            )
        ):
            invalid.append(requirement_version_id)
            continue
        coverage_items = assessment.get("coverage_items") or []
        if not coverage_items:
            invalid.append(requirement_version_id)
            continue
        coverage_item_ids = [item.get("coverage_item_id") for item in coverage_items]
        if (
            any(not item_id for item_id in coverage_item_ids)
            or len(coverage_item_ids) != len(set(coverage_item_ids))
        ):
            invalid.append(requirement_version_id)
            continue
        has_active_waiver = False
        unresolved_item = False
        for item in coverage_items:
            item_status = item.get("status")
            item_ready = coverage_item_ready_for_assurance(item, timestamp)
            if not item_ready:
                unresolved_item = True
            if item_status == "WAIVED":
                owner_id = (item.get("decision") or {}).get("waiver_owner_id")
                if item_ready and owner_id in active_waiver_owners:
                    has_active_waiver = True
                else:
                    unresolved_item = True
            elif item_status not in {"VERIFIED_COVERED", "NOT_APPLICABLE"}:
                unresolved_item = True
        status_mismatch = (assessment.get("status") == "CONDITIONAL") != has_active_waiver
        if unresolved_item or status_mismatch:
            invalid.append(requirement_version_id)
    if invalid:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED",
                "requirement_version_ids": invalid,
            },
        )
    return len(requirement_version_ids)


async def resolve_execution_context(
    project_id: str,
    user: CurrentUser,
    *,
    release_id: str | None = None,
    build_id: str | None = None,
    environment_id: str | None = None,
    release: str = "",
    build: str = "",
    environment: str = "",
):
    
    
    
    
    
    release_entity = None
    build_entity = None
    environment_entity = None
    if release_id:
        release_entity = await get_project_entity(
            'releases', release_id, user, 'release.read'
        )
        if release_entity.get("project_id") != project_id:
            raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
        if release_entity.get("status") == 'ARCHIVED':
            raise HTTPException(status_code=422, detail={"code": 'RELEASE_ARCHIVED'})
    if build_id:
        build_entity = await get_project_entity(
            'builds', build_id, user, 'build.read'
        )
        if build_entity.get("project_id") != project_id:
            raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
        linked_release_id = build_entity.get("release_id")
        if release_id and linked_release_id and linked_release_id != release_id:
            raise HTTPException(status_code=422, detail={"code": 'BUILD_RELEASE_MISMATCH'})
        if not release_id and linked_release_id:
            release_id = linked_release_id
            release_entity = await get_project_entity(
                'releases', release_id, user, 'release.read'
            )
            if release_entity.get("status") == 'ARCHIVED':
                raise HTTPException(status_code=422, detail={"code": 'RELEASE_ARCHIVED'})
    if environment_id:
        environment_entity = await get_project_entity(
            'test_environments',
            environment_id,
            user,
            'environment.read',
        )
        if environment_entity.get("project_id") != project_id:
            raise HTTPException(status_code=422, detail={"code": 'PROJECT_MISMATCH'})
        if environment_entity.get("status") == 'ARCHIVED':
            raise HTTPException(status_code=422, detail={"code": 'ENVIRONMENT_ARCHIVED'})
    return {
        "release_id": release_id,
        "build_id": build_id,
        "environment_id": environment_id,
        "release": (release_entity or {}).get("key") or release,
        "build": (build_entity or {}).get("identifier") or build,
        "environment": (environment_entity or {}).get("name") or environment,
    }


def clean_secret_fields(item):
    result = dict(item)
    result.pop("secret_refs", None)
    result["secret_ref_names"] = sorted((item.get("secret_refs") or {}).keys())
    return result


class ExecutionContextService:
    @staticmethod
    async def list_releases(project_id, status, user):
        await get_project(
            project_id, user, 'release.read'
        )
        query = {"project_id": project_id}
        if status:
            query["status"] = status.upper()
        return await execution_context_repository.list_releases(query)

    @staticmethod
    async def get_release(release_id, user):
        
        return await get_project_entity(
            'releases',
            release_id,
            user,
            'release.read',
        )

    @staticmethod
    async def release_close_readiness(release_id, user):
        authorized_release = await get_project_entity(
            'releases',
            release_id,
            user,
            'release.read',
        )
        project_id = authorized_release['project_id']
        checks = []
        completion_report = None

        async with await database.client.start_session() as session:
            async with session.start_transaction():
                release = await database.value.releases.find_one(
                    {'_id': release_id, 'project_id': project_id},
                    session=session,
                )
                if not release:
                    raise HTTPException(status_code=404, detail={'code': 'NOT_FOUND'})

                status_ready = release.get('status') == 'ACTIVE'
                checks.append(
                    ReleaseReadinessCheck(
                        gate='RELEASE_STATE',
                        status='PASS' if status_ready else 'BLOCKED',
                        code='RELEASE_ACTIVE' if status_ready else 'RELEASE_STATE_INVALID',
                        details={
                            'current_status': release.get('status'),
                            'required_status': 'ACTIVE',
                        },
                    )
                )

                gate_revision = release.get('gate_revision', 0)
                valid_gate_revision = (
                    isinstance(gate_revision, int)
                    and not isinstance(gate_revision, bool)
                    and gate_revision >= 0
                )
                checks.append(
                    ReleaseReadinessCheck(
                        gate='GATE_REVISION',
                        status='PASS' if valid_gate_revision else 'BLOCKED',
                        code=(
                            'RELEASE_GATE_REVISION_VALID'
                            if valid_gate_revision
                            else 'RELEASE_GATE_REVISION_INVALID'
                        ),
                        details={'gate_revision': gate_revision if valid_gate_revision else None},
                    )
                )

                try:
                    completion_report = await ensure_release_completion_gate(
                        project_id,
                        release_id,
                        session=session,
                    )
                    completion_details = {
                        'completion_report_id': completion_report.get('_id'),
                        'test_plan_id': completion_report.get('test_plan_id'),
                        'monitoring_snapshot_id': completion_report.get('monitoring_snapshot_id'),
                        'approved_at': completion_report.get('approved_at'),
                    }
                    checks.append(
                        ReleaseReadinessCheck(
                            gate='COMPLETION_REPORT',
                            status='PASS',
                            code='RELEASE_COMPLETION_REPORT_VALID',
                            details=completion_details,
                        )
                    )
                except HTTPException as error:
                    detail = error.detail if isinstance(error.detail, dict) else {}
                    checks.append(
                        ReleaseReadinessCheck(
                            gate='COMPLETION_REPORT',
                            status='BLOCKED',
                            code=detail.get('reason_code') or detail.get('code') or 'RELEASE_COMPLETION_GATE_FAILED',
                            details=detail,
                        )
                    )

                blocking_defects = await execution_context_repository.list_open_blocking_defects(
                    project_id,
                    release_id,
                    session=session,
                )
                checks.append(
                    ReleaseReadinessCheck(
                        gate='BLOCKING_DEFECTS',
                        status='BLOCKED' if blocking_defects else 'PASS',
                        code='OPEN_BLOCKING_DEFECTS' if blocking_defects else 'NO_OPEN_BLOCKING_DEFECTS',
                        details={
                            'defects': [
                                {
                                    'id': item.get('_id'),
                                    'key': item.get('defect_key'),
                                    'status': item.get('status'),
                                    'severity': item.get('severity'),
                                }
                                for item in blocking_defects
                            ]
                        },
                    )
                )

                try:
                    assured_requirement_count = await ensure_release_assurance_gate(
                        project_id,
                        release_id,
                        session=session,
                        completion_approved_at=(
                            completion_report.get('approved_at') or completion_report.get('created_at')
                            if isinstance(completion_report, dict)
                            else None
                        ),
                    )
                    checks.append(
                        ReleaseReadinessCheck(
                            gate='REQUIREMENT_ASSURANCE',
                            status='PASS',
                            code='RELEASE_REQUIREMENT_ASSURANCE_VALID',
                            details={'requirement_count': assured_requirement_count},
                        )
                    )
                except HTTPException as error:
                    detail = error.detail if isinstance(error.detail, dict) else {}
                    checks.append(
                        ReleaseReadinessCheck(
                            gate='REQUIREMENT_ASSURANCE',
                            status='BLOCKED',
                            code=detail.get('reason_code') or detail.get('code') or 'RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED',
                            details=detail,
                        )
                    )

                blockers = [item for item in checks if item.status == 'BLOCKED']
                gate_revision_value = gate_revision if valid_gate_revision else None
                return ReleaseReadiness(
                    release_id=release_id,
                    project_id=project_id,
                    status=release.get('status', ''),
                    revision=release.get('revision', 1),
                    gate_revision=gate_revision_value,
                    evaluated_at=now(),
                    can_close=not blockers,
                    checks=checks,
                    blockers=blockers,
                )

    @staticmethod
    async def create_release(project_id, payload, user):
        
        await get_project(project_id, user, 'release.create')
        timestamp = now()
        release = {
            "_id": new_id('REL'),
            "project_id": project_id,
            **payload.model_dump(),
            "status": 'PLANNED',
            "revision": 1,
            "gate_revision": 0,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            from src.clients.ai_automation import emit_release_changed

            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    await execution_context_repository.insert_release(release, session=session)
                    await audit(
                        user.id,
                        'release_created',
                        'Release',
                        release["_id"],
                        project_id,
                        session=session,
                    )
                    await emit_release_changed(release, user, session=session)
        except DuplicateKeyError:
            raise HTTPException(
                status_code=409,
                detail={"code": 'RELEASE_KEY_EXISTS'},
            )
        return release

    @staticmethod
    async def update_release(release_id, payload, user):
        
        release = await get_project_entity(
            'releases',
            release_id,
            user,
            'release.update',
        )
        if release.get("status") not in set(['PLANNED', 'ACTIVE']):
            raise HTTPException(
                status_code=409,
                detail={"code": 'RELEASE_STATE_INVALID'},
            )
        from src.clients.ai_automation import emit_release_changed

        async with await database.client.start_session() as session:
            async with session.start_transaction():
                updated = await optimistic_patch(
                    'releases',
                    release_id,
                    release["project_id"],
                    payload.expected_revision,
                    payload.model_dump(),
                    session=session,
                )
                await audit(
                    user.id,
                    'release_updated',
                    'Release',
                    release_id,
                    release["project_id"],
                    session=session,
                )
                await emit_release_changed(updated, user, session=session)
        return updated

    @staticmethod
    async def transition_release(release_id, payload, user, transition_action):
        
        transition = {'activate': {'target': 'ACTIVE',
              'sources': ['PLANNED'],
              'permission': 'release.manage',
              'event': 'release_activated'},
 'close': {'target': 'CLOSED',
           'sources': ['ACTIVE'],
           'permission': 'release.close',
           'event': 'release_closed'},
 'archive': {'target': 'ARCHIVED',
             'sources': ['CLOSED', 'PLANNED'],
             'permission': 'release.archive',
             'event': 'release_archived'}}[transition_action]
        target = transition["target"]
        release = await get_project_entity(
            'releases',
            release_id,
            user,
            transition["permission"],
        )
        if release.get("status") not in set(transition["sources"]):
            if release.get("status") == target:
                return release
            raise HTTPException(
                status_code=409,
                detail={
                    "code": 'RELEASE_STATE_INVALID',
                    "current_status": release.get("status"),
                    "target_status": target,
                },
            )
        completion_gate_applied = False
        assurance_scope_size = 0
        from src.clients.ai_automation import emit_release_changed

        try:
            gate_revision = release.get("gate_revision", 0)
            if target == 'CLOSED' and (
                not isinstance(gate_revision, int)
                or isinstance(gate_revision, bool)
                or gate_revision < 0
            ):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "RELEASE_GATE_REVISION_INVALID"},
                )
            async with await database.client.start_session() as session:
                async with session.start_transaction():
                    if target == 'CLOSED':
                        await serialize_release_gate(
                            release["project_id"],
                            [release_id],
                            session,
                            expected_gate_revisions={
                                release_id: gate_revision
                            },
                            required_statuses={release_id: "ACTIVE"},
                        )
                        completion_report = await ensure_release_completion_gate(
                            release["project_id"],
                            release_id,
                            session=session,
                            automation_run_id=getattr(user, "_ai_automation_run_id", None),
                        )
                        completion_gate_applied = bool(completion_report)
                        assurance_scope_size = await ensure_release_assurance_gate(
                            release["project_id"],
                            release_id,
                            session=session,
                            completion_approved_at=(
                                completion_report.get("approved_at") or completion_report.get("created_at")
                                if isinstance(completion_report, dict)
                                else None
                            ),
                        )
                    event = (
                        'release_closed_after_completion'
                        if completion_gate_applied
                        else transition["event"]
                    )
                    updated = await optimistic_patch(
                        'releases',
                        release_id,
                        release["project_id"],
                        payload.expected_revision,
                        {
                            "status": target,
                            f"{target.lower()}_by": user.id,
                            f"{target.lower()}_at": now(),
                            "transition_reason": payload.reason,
                        },
                        session=session,
                    )
                    if target == 'ACTIVE':
                        await execution_context_repository.set_current_release(
                            release["project_id"], release_id, 'ACTIVE', session=session
                        )
                        updated["is_current"] = True
                    await audit(
                        user.id,
                        event,
                        'Release',
                        release_id,
                        release["project_id"],
                        {"reason": payload.reason, "assured_requirement_count": assurance_scope_size},
                        session=session,
                    )
                    await emit_release_changed(updated, user, session=session)
        except HTTPException as error:
            gate_codes = {
                'RELEASE_COMPLETION_GATE_FAILED',
                'RELEASE_GATE_REVISION_CONFLICT',
                'RELEASE_GATE_REVISION_INVALID',
                'REVISION_CONFLICT',
                'RELEASE_TEST_PLAN_SCOPE_REQUIRED',
                'RELEASE_TEST_PLAN_SNAPSHOT_INVALID',
                'RELEASE_REQUIREMENT_SCOPE_REQUIRED',
                'RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED',
            }
            error_detail = error.detail if isinstance(error.detail, dict) else {}
            if target == 'CLOSED' and error_detail.get("code") in gate_codes:
                await audit(
                    user.id,
                    'release_close_blocked',
                    'Release',
                    release_id,
                    release["project_id"],
                    {"reason": payload.reason, "gate_code": error_detail["code"]},
                )
            raise
        return updated

    @staticmethod
    async def list_builds(project_id, release_id, user):
        await get_project(project_id, user, 'build.read')
        query = {"project_id": project_id}
        if release_id:
            query["release_id"] = release_id
        return await execution_context_repository.list_builds(query)

    @staticmethod
    async def get_build(build_id, user):
        
        return await get_project_entity(
            'builds',
            build_id,
            user,
            'build.read',
        )

    @staticmethod
    async def create_build(project_id, payload, user):
        
        await get_project(project_id, user, 'build.create')
        timestamp = now()
        build = {
            "_id": new_id('BLD'),
            "project_id": project_id,
            **payload.model_dump(),
            "status": 'ACTIVE',
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await execution_context_repository.insert_build(build)
        except DuplicateKeyError:
            raise HTTPException(
                status_code=409,
                detail={"code": 'BUILD_IDENTIFIER_EXISTS'},
            )
        await audit(
            user.id,
            'build_created',
            'Build',
            build["_id"],
            project_id,
        )
        return build

    @staticmethod
    async def update_build(build_id, payload, user):
        
        build = await get_project_entity(
            'builds',
            build_id,
            user,
            'build.manage',
        )
        updated = await optimistic_patch(
            'builds',
            build_id,
            build["project_id"],
            payload.expected_revision,
            payload.model_dump(),
        )
        await audit(
            user.id,
            'build_updated',
            'Build',
            build_id,
            build["project_id"],
        )
        return updated

    @staticmethod
    async def set_current_build(build_id, payload, user):
        
        build = await get_project_entity(
            'builds',
            build_id,
            user,
            'build.manage',
        )
        updated = await optimistic_patch(
            'builds',
            build_id,
            build["project_id"],
            payload.expected_revision,
            {"is_current": True},
        )
        await execution_context_repository.set_current_build(build["project_id"], build_id)
        await audit(
            user.id,
            'build_set_current',
            'Build',
            build_id,
            build["project_id"],
        )
        return updated

    @staticmethod
    async def list_environments(project_id, user):
        
        await get_project(project_id, user, 'environment.read')
        items = await execution_context_repository.list_active_environments(
            project_id, 'ARCHIVED'
        )
        return [clean_secret_fields(item) for item in items]

    @staticmethod
    async def get_environment(environment_id, user):
        
        environment = await get_project_entity(
            'test_environments',
            environment_id,
            user,
            'environment.read',
        )
        return clean_secret_fields(environment)

    @staticmethod
    async def create_environment(project_id, payload, user):
        
        await get_project(project_id, user, 'environment.create')
        timestamp = now()
        environment = {
            "_id": new_id('ENV'),
            "project_id": project_id,
            **payload.model_dump(),
            "status": 'ACTIVE',
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await execution_context_repository.insert_environment(environment)
        except DuplicateKeyError:
            raise HTTPException(
                status_code=409,
                detail={"code": 'ENVIRONMENT_NAME_EXISTS'},
            )
        await audit(
            user.id,
            'environment_created',
            'TestEnvironment',
            environment["_id"],
            project_id,
        )
        return clean_secret_fields(environment)

    @staticmethod
    async def update_environment(environment_id, payload, user):
        
        environment = await get_project_entity(
            'test_environments',
            environment_id,
            user,
            'environment.update',
        )
        updated = await optimistic_patch(
            'test_environments',
            environment_id,
            environment["project_id"],
            payload.expected_revision,
            payload.model_dump(),
        )
        await audit(
            user.id,
            'environment_updated',
            'TestEnvironment',
            environment_id,
            environment["project_id"],
        )
        return clean_secret_fields(updated)

    @staticmethod
    async def update_environment_secrets(environment_id, payload, user):
        
        environment = await get_project_entity(
            'test_environments',
            environment_id,
            user,
            'environment.secret_ref.manage',
        )
        updated = await optimistic_patch(
            'test_environments',
            environment_id,
            environment["project_id"],
            payload.expected_revision,
            {"secret_refs": payload.secret_refs},
        )
        await audit(
            user.id,
            'environment_secret_refs_updated',
            'TestEnvironment',
            environment_id,
            environment["project_id"],
            {"names": sorted(payload.secret_refs)},
        )
        return clean_secret_fields(updated)

    @staticmethod
    async def archive_environment(environment_id, payload, user):
        
        environment = await get_project_entity(
            'test_environments',
            environment_id,
            user,
            'environment.archive',
        )
        updated = await optimistic_patch(
            'test_environments',
            environment_id,
            environment["project_id"],
            payload.expected_revision,
            {
                "status": 'ARCHIVED',
                "archive_reason": payload.reason,
                "archived_at": now(),
                "archived_by": user.id,
            },
        )
        await audit(
            user.id,
            'environment_archived',
            'TestEnvironment',
            environment_id,
            environment["project_id"],
            {"reason": payload.reason},
        )
        return clean_secret_fields(updated)

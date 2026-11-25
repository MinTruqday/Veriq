from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError, OperationFailure

from src.core.auth import CurrentUser
from src.core.common import audit, get_project, get_project_entity, new_id, now, optimistic_patch
from src.core.database import database
from src.modules.quality.services.defect_classification import defect_is_blocking
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

def defect_blocks_release(defect, *, status=None):
    current_status = str(status if status is not None else defect.get("status") or "")
    current_defect = {**defect, "status": current_status}
    return current_status.upper() in {
        "NEW",
        "CONFIRMED",
        "IN_PROGRESS",
        "READY_FOR_RETEST",
        "REOPENED",
    } and defect_is_blocking(current_defect)

async def resolve_execution_context(
    project_id: str,
    user: CurrentUser,
    *,
    release_id: str | None = None,
    build_id: str | None = None,
    environment_id: str | None = None,
    release: str = "",
    build: str = "",
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
        "environment": (environment_entity or {}).get("name") or "",
    }

def clean_secret_fields(item):
    result = dict(item)
    result.pop("secret_refs", None)
    result.pop("secret_ref_names", None)
    result.pop("environment_type", None)
    result.pop("capabilities", None)
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

                blockers = [item for item in checks if item.status == 'BLOCKED']
                return ReleaseReadiness(
                    release_id=release_id,
                    project_id=project_id,
                    status=release.get('status', ''),
                    revision=release.get('revision', 1),
                    gate_revision=release.get('gate_revision', 0),
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
                        blocking_defects = await execution_context_repository.list_open_blocking_defects(
                            release["project_id"],
                            release_id,
                            session=session,
                        )
                        if blocking_defects:
                            raise HTTPException(
                                status_code=409,
                                detail={
                                    "code": "OPEN_BLOCKING_DEFECTS",
                                    "defect_ids": [item.get("_id") for item in blocking_defects],
                                },
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
                        transition["event"],
                        'Release',
                        release_id,
                        release["project_id"],
                        {"reason": payload.reason},
                        session=session,
                    )
        except HTTPException as error:
            gate_codes = {
                'RELEASE_GATE_REVISION_CONFLICT',
                'RELEASE_GATE_REVISION_INVALID',
                'OPEN_BLOCKING_DEFECTS',
                'REVISION_CONFLICT',
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

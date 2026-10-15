from datetime import datetime, timezone

from fastapi import HTTPException

from src.core.auth import CurrentUser
from pymongo.errors import DuplicateKeyError

from src.core.common import audit, get_project, get_project_entity, new_id, now, optimistic_patch
from src.repositories.execution_context import execution_context_repository





async def ensure_release_completion_gate(project_id: str, release_id: str):
    if not await execution_context_repository.approved_completion_exists(
        project_id, release_id, ['APPROVED', 'CLOSED']
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": 'RELEASE_COMPLETION_GATE_FAILED'},
        )
    return True


def _active_waiver(item, timestamp):
    if item.get("status") != "WAIVED":
        return False
    value = (item.get("decision") or {}).get("waiver_expires_at")
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value > timestamp


async def ensure_release_assurance_gate(project_id: str, release_id: str):
    plans = await execution_context_repository.list_approved_test_plan_scopes(
        project_id, release_id
    )
    if not plans:
        raise HTTPException(
            status_code=409,
            detail={"code": "RELEASE_TEST_PLAN_SCOPE_REQUIRED"},
        )
    requirement_version_ids = sorted(
        {
            requirement_version_id
            for plan in plans
            for requirement_version_id in (plan.get("approved_snapshot") or plan).get(
                "requirement_version_ids", []
            )
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
            project_id, requirement_version_ids
        )
    }
    timestamp = now()
    invalid = []
    for requirement_version_id in requirement_version_ids:
        assessment = assessments.get(requirement_version_id)
        if not assessment or assessment.get("status") not in {"ASSURED", "CONDITIONAL"}:
            invalid.append(requirement_version_id)
            continue
        if any(
            item.get("status") == "WAIVED" and not _active_waiver(item, timestamp)
            for item in assessment.get("coverage_items", [])
        ):
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
    async def create_release(project_id, payload, user):
        
        await get_project(project_id, user, 'release.create')
        timestamp = now()
        release = {
            "_id": new_id('REL'),
            "project_id": project_id,
            **payload.model_dump(),
            "status": 'PLANNED',
            "revision": 1,
            "created_by": user.id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        try:
            await execution_context_repository.insert_release(release)
        except DuplicateKeyError:
            raise HTTPException(
                status_code=409,
                detail={"code": 'RELEASE_KEY_EXISTS'},
            )
        await audit(
            user.id,
            'release_created',
            'Release',
            release["_id"],
            project_id,
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
        updated = await optimistic_patch(
            'releases',
            release_id,
            release["project_id"],
            payload.expected_revision,
            payload.model_dump(),
        )
        await audit(
            user.id,
            'release_updated',
            'Release',
            release_id,
            release["project_id"],
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
        completion_gate_applied = False
        assurance_scope_size = 0
        if target == 'CLOSED':
            try:
                completion_gate_applied = await ensure_release_completion_gate(release["project_id"], release_id)
                assurance_scope_size = await ensure_release_assurance_gate(
                    release["project_id"], release_id
                )
            except HTTPException:
                await audit(
                    user.id,
                    'release_close_blocked',
                    'Release',
                    release_id,
                    release["project_id"],
                    {"reason": payload.reason},
                )
                raise
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
        )
        if target == 'ACTIVE':
            await execution_context_repository.set_current_release(
                release["project_id"], release_id, 'ACTIVE'
            )
            updated["is_current"] = True
        event = (
            'release_closed_after_completion'
            if completion_gate_applied
            else transition["event"]
        )
        await audit(
            user.id,
            event,
            'Release',
            release_id,
            release["project_id"],
            {"reason": payload.reason, "assured_requirement_count": assurance_scope_size},
        )
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

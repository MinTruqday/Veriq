from dataclasses import dataclass

from fastapi import HTTPException

from src.core.auth import CurrentUser
from src.core.common import audit, get_project_entity, now
from src.repositories.requirement import requirement_repository
from src.modules.design.services.linters import requirement_findings
from src.modules.requirements.services.requirement_indexing import index_requirement_version




@dataclass(frozen=True)
class RequirementBaselineResult:
    version: dict
    indexed: bool

    @property
    def status(self):
        return (
            'SUCCESS'
            if self.indexed
            else 'DEGRADED'
        )

    @property
    def degraded_mode(self):
        return None if self.indexed else 'DEGRADED_VECTOR'


async def submit_requirement_for_review(
    project_id: str,
    requirement_id: str,
    expected_revision: int,
    review_note: str,
    user: CurrentUser,
):
    requirement = await get_project_entity(
        'requirements',
        requirement_id,
        user,
        'requirement.submit_review',
    )
    if requirement["project_id"] != project_id:
        raise HTTPException(
            status_code=422,
            detail={"code": 'PROJECT_MISMATCH'},
        )
    version = await requirement_repository.find_version(
        requirement["current_version_id"], project_id
    )
    if version["status"] == 'IN_REVIEW':
        return version
    if version["status"] != 'DRAFT':
        raise HTTPException(
            status_code=409,
            detail={"code": 'INVALID_STATE_TRANSITION'},
        )
    if version["revision"] != expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'REVISION_CONFLICT',
                "current_revision": version["revision"],
            },
        )
    acceptance_criteria = await requirement_repository.list_acceptance_criteria(
        version["_id"], 200
    )
    findings = requirement_findings(version, acceptance_criteria)
    project = await requirement_repository.find_project_settings(project_id)
    lint_blocking = (project.get("settings") or {}).get(
        'requirement_lint_blocking', True
    )
    if lint_blocking and any(
        item["severity"] == 'error' for item in findings
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": 'REQUIREMENT_LINT_BLOCKED', "findings": findings},
        )
    timestamp = now()
    transitioned = await requirement_repository.transition_version(
        version["_id"],
        project_id,
        expected_revision,
        'DRAFT',
        'IN_REVIEW',
        {
            "review_note": review_note,
            "review_submitted_by": user.id,
            "review_submitted_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not transitioned:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT'},
        )
    await requirement_repository.set_requirement_status(
        requirement_id, project_id, 'IN_REVIEW', timestamp
    )
    version = await requirement_repository.find_version(version["_id"], project_id)
    await audit(
        user.id,
        'requirement_review_submitted',
        'RequirementVersion',
        version["_id"],
        project_id,
        {"review_note": review_note},
    )
    return version


async def return_requirement_for_changes(
    project_id: str,
    requirement_id: str,
    expected_revision: int,
    review_note: str,
    user: CurrentUser,
):
    requirement = await get_project_entity(
        'requirements',
        requirement_id,
        user,
        'requirement.review',
    )
    if requirement["project_id"] != project_id:
        raise HTTPException(
            status_code=422,
            detail={"code": 'PROJECT_MISMATCH'},
        )
    version = await requirement_repository.find_version(
        requirement["current_version_id"], project_id
    )
    if version["status"] != 'IN_REVIEW':
        raise HTTPException(
            status_code=409,
            detail={"code": 'INVALID_STATE_TRANSITION'},
        )
    if version["revision"] != expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'REVISION_CONFLICT',
                "current_revision": version["revision"],
            },
        )
    timestamp = now()
    transitioned = await requirement_repository.transition_version(
        version["_id"],
        project_id,
        expected_revision,
        'IN_REVIEW',
        'DRAFT',
        {
            "review_note": review_note,
            "changes_requested_by": user.id,
            "changes_requested_at": timestamp,
            "updated_at": timestamp,
        },
    )
    if not transitioned:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT'},
        )
    await requirement_repository.set_requirement_status(
        requirement_id, project_id, 'DRAFT', timestamp
    )
    version = await requirement_repository.find_version(version["_id"], project_id)
    await audit(
        user.id,
        'requirement_changes_requested',
        'RequirementVersion',
        version["_id"],
        project_id,
        {"review_note": review_note},
    )
    return version


async def baseline_requirement(
    version_id: str,
    expected_revision: int,
    review_note: str,
    user: CurrentUser,
):
    version = await get_project_entity(
        'requirement_versions',
        version_id,
        user,
        'requirement.approve',
    )
    if version["status"] == 'BASELINED':
        return RequirementBaselineResult(version, True)
    if version["status"] != 'IN_REVIEW':
        raise HTTPException(
            status_code=409,
            detail={"code": 'INVALID_STATE_TRANSITION'},
        )
    if version["revision"] != expected_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'REVISION_CONFLICT',
                "current_revision": version["revision"],
            },
        )
    acceptance_criteria = await requirement_repository.list_acceptance_criteria(
        version["_id"], 200
    )
    findings = requirement_findings(version, acceptance_criteria)
    project = await requirement_repository.find_project_settings(version["project_id"])
    lint_blocking = (project.get("settings") or {}).get(
        'requirement_lint_blocking', True
    )
    if lint_blocking and any(
        item["severity"] == 'error' for item in findings
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": 'REQUIREMENT_LINT_BLOCKED', "findings": findings},
        )
    timestamp = now()
    version = await requirement_repository.baseline_version(
        version_id,
        version["project_id"],
        expected_revision,
        'IN_REVIEW',
        {
            "status": 'BASELINED',
            "review_note": review_note,
            "baselined_at": timestamp,
            "baselined_by": user.id,
            "updated_at": timestamp,
        },
    )
    if not version:
        current = await requirement_repository.find_version(version_id)
        if current and current.get("status") == 'BASELINED':
            return RequirementBaselineResult(current, True)
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT'},
        )
    await requirement_repository.set_current_baseline(
        version["requirement_id"],
        version_id,
        'BASELINED',
        timestamp,
    )
    from src.modules.design.services.test_adequacy import supersede_requirement_assessments
    await supersede_requirement_assessments(
        version["project_id"], version["requirement_id"], version_id, user.id
    )
    await requirement_repository.approve_acceptance_criteria(
        version_id,
        'draft',
        'approved',
        timestamp,
        user.id,
    )
    indexed = await index_requirement_version(version)
    version = await requirement_repository.find_version(version_id)
    await audit(
        user.id,
        'requirement_version_baselined',
        'RequirementVersion',
        version_id,
        version["project_id"],
    )
    return RequirementBaselineResult(version, indexed)


async def make_requirement_obsolete(
    requirement_id: str,
    expected_current_version_id: str,
    reason: str,
    user: CurrentUser,
):
    requirement = await get_project_entity(
        'requirements',
        requirement_id,
        user,
        'requirement.archive',
    )
    if requirement.get("status") == 'OBSOLETE':
        return requirement
    if requirement.get("current_version_id") != expected_current_version_id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'REVISION_CONFLICT',
                "current_version_id": requirement.get("current_version_id"),
            },
        )
    current_version = await requirement_repository.find_version(
        expected_current_version_id, requirement["project_id"], requirement_id
    )
    if (
        not current_version
        or current_version.get("status") not in ['DRAFT', 'IN_REVIEW', 'BASELINED']
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": 'REQUIREMENT_VERSION_CONFLICT'},
        )
    version_status = current_version["status"]
    timestamp = now()
    updated = await requirement_repository.mark_requirement_obsolete(
        requirement_id,
        requirement["project_id"],
        expected_current_version_id,
        requirement["status"],
        'OBSOLETE',
        reason,
        user.id,
        timestamp,
    )
    if not updated:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT'},
        )
    version_updated = await requirement_repository.mark_version_obsolete(
        expected_current_version_id,
        requirement["project_id"],
        requirement_id,
        ['DRAFT', 'IN_REVIEW', 'BASELINED'],
        'OBSOLETE',
        version_status,
        reason,
        user.id,
        timestamp,
    )
    if not version_updated:
        await requirement_repository.rollback_requirement_obsolete(
            requirement_id,
            requirement["project_id"],
            'OBSOLETE',
            timestamp,
            requirement["status"],
            now(),
        )
        raise HTTPException(
            status_code=409,
            detail={"code": 'REQUIREMENT_VERSION_CONFLICT'},
        )
    await audit(
        user.id,
        'requirement_marked_obsolete',
        'Requirement',
        requirement_id,
        requirement["project_id"],
        {"reason": reason, "version_id": expected_current_version_id},
    )
    current_version = await requirement_repository.find_version(
        expected_current_version_id, requirement["project_id"]
    )
    return {**updated, "current_version": current_version}


async def restore_obsolete_requirement(
    requirement_id: str,
    expected_current_version_id: str,
    reason: str,
    user: CurrentUser,
):
    requirement = await get_project_entity(
        'requirements',
        requirement_id,
        user,
        'requirement.restore',
    )
    if requirement.get("status") != 'OBSOLETE':
        raise HTTPException(
            status_code=409,
            detail={"code": 'REQUIREMENT_NOT_OBSOLETE'},
        )
    if requirement.get("current_version_id") != expected_current_version_id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'REVISION_CONFLICT',
                "current_version_id": requirement.get("current_version_id"),
            },
        )
    version = await requirement_repository.find_version(
        expected_current_version_id,
        requirement["project_id"],
        requirement_id,
        'OBSOLETE',
    )
    if not version:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REQUIREMENT_VERSION_CONFLICT'},
        )
    restored_status = requirement.get("status_before_obsolete") or (
        'BASELINED'
        if version.get("baselined_at")
        else 'DRAFT'
    )
    restored_version_status = version.get("status_before_obsolete") or restored_status
    if (
        restored_status not in ['DRAFT', 'IN_REVIEW', 'BASELINED']
        or restored_version_status not in ['DRAFT', 'IN_REVIEW', 'BASELINED']
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": 'REQUIREMENT_RESTORE_STATE_INVALID'},
        )
    timestamp = now()
    version_restored = await requirement_repository.restore_version(
        version["_id"],
        requirement["project_id"],
        requirement_id,
        'OBSOLETE',
        restored_version_status,
        reason,
        user.id,
        timestamp,
    )
    if not version_restored:
        raise HTTPException(
            status_code=409,
            detail={"code": 'REQUIREMENT_VERSION_CONFLICT'},
        )
    updated = await requirement_repository.restore_requirement(
        requirement_id,
        requirement["project_id"],
        expected_current_version_id,
        'OBSOLETE',
        restored_status,
        reason,
        user.id,
        timestamp,
    )
    if not updated:
        await requirement_repository.rollback_version_restore(
            version["_id"],
            requirement["project_id"],
            'OBSOLETE',
            restored_version_status,
            now(),
        )
        raise HTTPException(
            status_code=409,
            detail={"code": 'REVISION_CONFLICT'},
        )
    await audit(
        user.id,
        'requirement_restored',
        'Requirement',
        requirement_id,
        requirement["project_id"],
        {"reason": reason, "version_id": version["_id"]},
    )
    restored_version = await requirement_repository.find_version(
        version["_id"], requirement["project_id"]
    )
    return {**updated, "current_version": restored_version}

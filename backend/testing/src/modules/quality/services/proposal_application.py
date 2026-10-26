import hashlib
from datetime import timedelta

from fastapi import HTTPException
from src.core.human_decisions import require_automation_publication_authority

from src.core.common import audit, get_project_entity, new_id, now
from src.core.configuration import settings
from src.schemas.contracts.design import TestCaseDraftCreate
from src.repositories.proposal_application import proposal_application_repository
from src.modules.quality.services.maintenance_proposal import (
    require_pending_revision,
    update_proposal_acceptance_rate,
)
from src.clients.project_knowledge import index_artifact
from src.modules.design.services.test_case_records import create_test_case_draft_record, project_test_text
from src.modules.design.services.test_evidence import requirement_test_evidence_text


async def approve_maintenance_proposal(
    proposal_id, payload, user, edited=False, expected_project_id=None
):
    
    if expected_project_id is not None:
        proposal = await get_project_entity(
            "maintenance_proposals",
            proposal_id,
            user,
            'proposal.approve',
        )
        if proposal["project_id"] != expected_project_id:
            raise HTTPException(
                status_code=422,
                detail={"code": 'PROJECT_MISMATCH'},
            )
    final_status = (
        'EDITED_ACCEPTED'
        if edited
        else 'ACCEPTED'
    )
    return await apply_maintenance_proposal(proposal_id, payload, user, final_status)


async def apply_maintenance_proposal(proposal_id, payload, user, final_status):
    require_automation_publication_authority(user, "proposal.approve")
    proposal = await get_project_entity(
        "maintenance_proposals", proposal_id, user, 'proposal.approve'
    )
    if proposal.get("status") in ['ACCEPTED', 'EDITED_ACCEPTED'] and proposal.get(
        "applied_artifact_id"
    ):
        result = await proposal_application_repository.find_applied_artifact(
            proposal["applied_artifact_id"], proposal["project_id"]
        )
        return {"proposal": proposal, "result": result}
    previous_status = proposal["status"]
    if previous_status == 'APPLYING':
        if proposal.get("revision") != payload.expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"code": 'REVISION_CONFLICT', "current_revision": proposal["revision"]},
            )
        operation_time = now()
        lease_expires_at = operation_time + timedelta(
            seconds=settings.MAINTENANCE_PROPOSAL_APPLY_LEASE_SECONDS
        )
        stable_version_id = (
            proposal.get("partial_version_id")
            or (
                "TCV-" + hashlib.sha256(proposal_id.encode("utf-8")).hexdigest()
                if proposal.get("proposal_type") == 'UPDATE_TEST_CASE'
                else "TCD-" + hashlib.sha256(proposal_id.encode("utf-8")).hexdigest()
                if proposal.get("proposal_type") == 'CREATE_TEST_CASE'
                else None
            )
        )
        proposal = await proposal_application_repository.take_over_expired_proposal_application(
            proposal_id,
            proposal["project_id"],
            payload.expected_revision,
            operation_time,
            lease_expires_at,
            user.id,
            stable_version_id,
        )
        if not proposal:
            raise HTTPException(
                status_code=409, detail={"code": 'PROPOSAL_APPLY_IN_PROGRESS'}
            )
        previous_status = 'APPLYING'
    else:
        require_pending_revision(proposal, payload, allow_partial=True)
        operation_time = now()
        changes = {
            "status": 'APPLYING',
            "applying_by": user.id,
            "apply_lease_expires_at": operation_time + timedelta(
                seconds=settings.MAINTENANCE_PROPOSAL_APPLY_LEASE_SECONDS
            ),
            "updated_at": operation_time,
        }
        if proposal.get("proposal_type") == 'UPDATE_TEST_CASE':
            changes["partial_version_id"] = proposal.get("partial_version_id") or (
                "TCV-" + hashlib.sha256(proposal_id.encode("utf-8")).hexdigest()
            )
        elif proposal.get("proposal_type") == 'CREATE_TEST_CASE':
            changes["partial_version_id"] = proposal.get("partial_version_id") or (
                "TCD-" + hashlib.sha256(proposal_id.encode("utf-8")).hexdigest()
            )
        proposal = await proposal_application_repository.transition_proposal(
            proposal_id,
            proposal["project_id"],
            payload.expected_revision,
            previous_status,
            changes,
        )
    if not proposal:
        current = await proposal_application_repository.find_proposal(proposal_id)
        if (
            current
            and current.get("status") in ['ACCEPTED', 'EDITED_ACCEPTED']
            and current.get("applied_artifact_id")
        ):
            result = await proposal_application_repository.find_applied_artifact(
                current["applied_artifact_id"], current["project_id"]
            )
            return {"proposal": current, "result": result}
        raise HTTPException(
            status_code=409, detail={"code": 'PROPOSAL_APPLY_IN_PROGRESS'}
        )
    patch = {**proposal.get("patch", {}), **(payload.patch or {})}
    try:
        if previous_status in {'APPLY_PARTIAL', 'APPLYING'} and proposal.get("partial_version_id"):
            partial_version = await proposal_application_repository.find_test_version(
                proposal["partial_version_id"], proposal["project_id"]
            )
            partial_draft = (
                await proposal_application_repository.find_test_draft(
                    proposal["partial_version_id"], proposal["project_id"]
                )
                if not partial_version and proposal["proposal_type"] == 'CREATE_TEST_CASE'
                else None
            )
            if partial_version or partial_draft or previous_status == 'APPLY_PARTIAL':
                result = await recover_partial_proposal(proposal, user)
            elif proposal["proposal_type"] == 'UPDATE_TEST_CASE':
                result = await create_test_version_from_proposal(
                    proposal, {**proposal.get("patch", {}), **(payload.patch or {})}, user
                )
            else:
                result = await create_test_draft_from_proposal(
                    proposal, {**proposal.get("patch", {}), **(payload.patch or {})}, user
                )
        elif proposal["proposal_type"] == 'CREATE_TEST_CASE':
            result = await create_test_draft_from_proposal(proposal, patch, user)
        elif proposal["proposal_type"] == 'UPDATE_TEST_CASE':
            result = await create_test_version_from_proposal(proposal, patch, user)
        elif proposal["proposal_type"] == 'MARK_OBSOLETE':
            result = await mark_test_obsolete(proposal)
        else:
            raise HTTPException(
                status_code=422, detail={"code": 'UNSUPPORTED_PROPOSAL_TYPE'}
            )
    except HTTPException:
        if previous_status == 'APPLYING':
            partial = await proposal_application_repository.find_proposal(proposal_id)
            partial_artifact = (
                await proposal_application_repository.find_applied_artifact(
                    partial.get("partial_version_id"), proposal["project_id"]
                )
                if partial and partial.get("partial_version_id")
                else None
            )
            await proposal_application_repository.update_proposal(
                {
                    "_id": proposal_id,
                    "status": 'APPLYING',
                    "revision": proposal["revision"],
                },
                {
                    "status": 'APPLY_PARTIAL' if partial_artifact else 'PENDING',
                    "apply_lease_expires_at": None,
                    "updated_at": now(),
                },
            )
        else:
            await proposal_application_repository.update_proposal(
                {
                    "_id": proposal_id,
                    "status": 'APPLYING',
                    "revision": proposal["revision"],
                },
                {
                    "status": previous_status,
                    "apply_lease_expires_at": None,
                    "updated_at": now(),
                },
            )
        raise
    except Exception as error:
        partial = await proposal_application_repository.find_proposal(proposal_id)
        partial_artifact = None
        if partial and partial.get("partial_version_id"):
            partial_artifact = await proposal_application_repository.find_applied_artifact(
                partial["partial_version_id"], proposal["project_id"]
            )
        if partial_artifact:
            await proposal_application_repository.update_proposal(
                {
                    "_id": proposal_id,
                    "project_id": proposal["project_id"],
                    "status": 'APPLYING',
                    "revision": proposal["revision"],
                },
                {
                    "status": 'APPLY_PARTIAL',
                    "recovery_error": str(error)[: 500],
                    "updated_at": now(),
                },
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "code": 'PROPOSAL_APPLY_PARTIAL',
                    "retryable": True,
                    "state_after_failure": 'APPLY_PARTIAL',
                    "user_action_required": True,
                },
            ) from error
        await proposal_application_repository.update_proposal(
            {
                "_id": proposal_id,
                "status": 'APPLYING',
                "revision": proposal["revision"],
            },
            {
                "status": 'PENDING',
                "recovery_error": str(error)[: 500],
                "apply_lease_expires_at": None,
                "updated_at": now(),
            },
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": 'PROPOSAL_APPLY_FAILED',
                "retryable": True,
                "state_after_failure": 'UNCHANGED',
                "user_action_required": True,
            },
        ) from error
    finalized = await proposal_application_repository.update_proposal(
        {
            "_id": proposal_id,
            "project_id": proposal["project_id"],
            "status": 'APPLYING',
            "revision": proposal["revision"],
        },
        {
            "status": final_status,
            "applied_artifact_id": result.get("_id"),
            "apply_lease_expires_at": None,
            "review_note": payload.review_note,
            "reviewed_by": user.id,
            "reviewed_at": now(),
            "updated_at": now(),
        },
    )
    if finalized.matched_count != 1:
        await proposal_application_repository.update_proposal(
            {
                "_id": proposal_id,
                "project_id": proposal["project_id"],
                "status": 'APPLYING',
                "revision": proposal["revision"],
            },
            {
                "status": 'APPLY_PARTIAL',
                "partial_version_id": result.get("_id"),
                "updated_at": now(),
            },
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": 'PROPOSAL_APPLY_PARTIAL',
                "retryable": True,
                "state_after_failure": 'APPLY_PARTIAL',
                "user_action_required": True,
            },
        )
    await update_proposal_acceptance_rate(proposal["project_id"])
    await audit(
        user.id,
        'maintenance_proposal_applied',
        'MaintenanceProposal',
        proposal_id,
        proposal["project_id"],
        {"result_id": result.get("_id")},
    )
    return {
        "proposal": await proposal_application_repository.find_proposal(proposal_id),
        "result": result,
    }


async def create_test_version_from_proposal(proposal, patch, user):
    
    test_case = await proposal_application_repository.find_test_case(
        proposal["target_artifact_id"], proposal["project_id"]
    )
    if not test_case or test_case.get("current_version_id") != proposal["base_version_id"]:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'STALE_PROPOSAL',
                "current_version_id": test_case.get("current_version_id") if test_case else None,
            },
        )
    base = await proposal_application_repository.find_test_version(
        proposal["base_version_id"]
    )
    analysis = await proposal_application_repository.find_impact_analysis(
        proposal["impact_analysis_id"]
    )
    change_set = await proposal_application_repository.find_change_set(
        analysis["change_set_id"]
    ) if analysis and analysis.get("change_set_id") else None
    allowed = set(['title',
 'type',
 'priority',
 'risk',
 'objective_doc',
 'preconditions_doc',
 'steps',
 'test_data',
 'expected_result_doc',
 'postconditions_doc',
 'tags',
 'techniques',
 'automation_status',
 'attachments',
 'data_set_version_ids',
 'requirement_version_ids',
 'acceptance_criterion_ids'])
    merged = {**base, **{key: value for key, value in patch.items() if key in allowed}}
    if change_set and change_set.get("to_version_id"):
        current_requirement_version_id = change_set["to_version_id"]
        current_requirement_version = await proposal_application_repository.find_requirement_version(
            current_requirement_version_id, proposal["project_id"]
        )
        if not current_requirement_version:
            raise HTTPException(
                status_code=409,
                detail={"code": "REQUIREMENT_VERSION_NOT_FOUND"},
            )
        requirement_version_ids = list(merged.get("requirement_version_ids", []))
        versions_by_id = {
            version_id: await proposal_application_repository.find_requirement_version(
                version_id, proposal["project_id"]
            )
            for version_id in requirement_version_ids
        }
        replaced_requirement_version_ids = {
            version_id
            for version_id, version in versions_by_id.items()
            if version
            and current_requirement_version
            and version.get("requirement_id") == current_requirement_version.get("requirement_id")
        }
        requirement_version_ids = [
            version_id
            for version_id in requirement_version_ids
            if version_id not in replaced_requirement_version_ids
        ]
        if current_requirement_version_id not in requirement_version_ids:
            requirement_version_ids.append(current_requirement_version_id)
        merged["requirement_version_ids"] = requirement_version_ids

        previous_criteria = await proposal_application_repository.list_acceptance_criteria_by_ids(
            merged.get("acceptance_criterion_ids", []), proposal["project_id"]
        )
        current_criteria = await proposal_application_repository.list_acceptance_criteria_for_version(
            current_requirement_version_id, proposal["project_id"]
        )
        current_criteria_by_key = {
            item.get("key"): item["_id"]
            for item in current_criteria
            if item.get("key")
        }
        criterion_owner_version_ids = {
            item.get("requirement_version_id")
            for item in previous_criteria
            if item.get("requirement_version_id")
        }
        criterion_owner_versions = {
            version_id: await proposal_application_repository.find_requirement_version(
                version_id, proposal["project_id"]
            )
            for version_id in criterion_owner_version_ids
        }
        previous_criterion_ids = {
            item["_id"]
            for item in previous_criteria
            if current_requirement_version
            and criterion_owner_versions.get(item.get("requirement_version_id"))
            and criterion_owner_versions[item["requirement_version_id"]].get("requirement_id")
            == current_requirement_version.get("requirement_id")
        }
        remapped_criterion_ids = [
            current_criteria_by_key[item.get("key")]
            for item in previous_criteria
            if item["_id"] in previous_criterion_ids
            and item.get("key") in current_criteria_by_key
        ]
        retained_criterion_ids = [
            criterion_id
            for criterion_id in merged.get("acceptance_criterion_ids", [])
            if criterion_id not in previous_criterion_ids
        ]
        merged["acceptance_criterion_ids"] = list(
            dict.fromkeys([*retained_criterion_ids, *remapped_criterion_ids])
        )
    merged["plain_text_projection"] = project_test_text(merged)
    from src.modules.design.services.linters import lint_test_case

    findings = lint_test_case(merged)
    blocking_findings = [item for item in findings if item.get("severity") == "error"]
    if blocking_findings:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "MAINTENANCE_TEST_CASE_QUALITY_BLOCKED",
                "findings": blocking_findings,
            },
        )
    version = {
        **{
            key: value
            for key, value in merged.items()
            if key
            not in set(['_id', 'version', 'created_at', 'approved_by', 'parent_version_id', 'change_reason'])
        },
        "_id": proposal.get("partial_version_id") or new_id('TCV'),
        "version": int(base["version"]) + 1,
        "parent_version_id": base["_id"],
        "change_reason": proposal["reason"],
        "approved_by": user.id,
        "created_at": now(),
    }
    existing_version = await proposal_application_repository.find_test_version(
        version["_id"], proposal["project_id"]
    )
    if existing_version:
        if (
            existing_version.get("project_id") != proposal["project_id"]
            or existing_version.get("test_case_id") != proposal["target_artifact_id"]
            or existing_version.get("parent_version_id") != proposal["base_version_id"]
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "PROPOSAL_PARTIAL_VERSION_IDENTITY_MISMATCH"},
            )
        version = existing_version
    else:
        await proposal_application_repository.insert_test_version(version)
    updated = await proposal_application_repository.activate_test_version(
        test_case["_id"],
        proposal["project_id"],
        proposal["base_version_id"],
        version["_id"],
        'ACTIVE',
        now(),
    )
    if not updated:
        raise RuntimeError('TEST_CASE_VERSION_CONFLICT')
    await proposal_application_repository.mark_previous_traces(
        proposal["project_id"],
        base["_id"],
        ['CONFIRMED', 'STALE'],
        'STALE',
        now(),
    )
    await proposal_application_repository.ensure_confirmed_requirement_trace(
        {
            "_id": new_id('TL'),
            "project_id": proposal["project_id"],
            "source_type": 'requirement_version',
            "source_id": change_set["to_version_id"],
            "target_type": 'test_case_version',
            "target_id": version["_id"],
            "link_type": 'verifies',
            "confidence": 1,
            "origin": 'manual',
            "status": 'CONFIRMED',
            "revision": 1,
            "evidence": proposal["evidence"],
            "created_by": user.id,
            "created_at": now(),
            "updated_at": now(),
        }
    )
    await index_artifact(
        version["project_id"],
        'test_case_version',
        version["test_case_id"],
        version["_id"],
        version["title"],
        version["plain_text_projection"],
        version["status"],
        'APPROVED_SOURCE',
        version["version"],
        requirement_version_ids=version.get("requirement_version_ids", []),
        acceptance_criterion_ids=version.get("acceptance_criterion_ids", []),
    )
    return version


async def recover_partial_proposal(proposal, user):
    
    version = await proposal_application_repository.find_test_version(
        proposal["partial_version_id"], proposal["project_id"]
    )
    if not version:
        draft = await proposal_application_repository.find_test_draft(
            proposal["partial_version_id"], proposal["project_id"]
        )
        if draft:
            return draft
        test_case = await proposal_application_repository.find_test_case(
            proposal["partial_version_id"], proposal["project_id"]
        )
        if test_case and proposal.get("proposal_type") == 'MARK_OBSOLETE':
            await proposal_application_repository.set_test_case_status(
                test_case["_id"],
                proposal["project_id"],
                'OBSOLETE',
                now(),
            )
            return await proposal_application_repository.find_test_case(
                test_case["_id"], proposal["project_id"]
            )
    if not version:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 'PARTIAL_ARTIFACT_NOT_FOUND',
                "state_after_failure": 'APPLY_PARTIAL',
            },
        )
    test_case = await proposal_application_repository.find_test_case(
        proposal["target_artifact_id"], proposal["project_id"]
    )
    if not test_case:
        raise HTTPException(
            status_code=409, detail={"code": "PARTIAL_TEST_CASE_NOT_FOUND"}
        )
    current_version_id = test_case.get("current_version_id")
    if current_version_id != version["_id"]:
        if current_version_id != proposal.get("base_version_id"):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "STALE_PROPOSAL",
                    "current_version_id": current_version_id,
                },
            )
        activated = await proposal_application_repository.activate_test_version(
            test_case["_id"],
            proposal["project_id"],
            proposal["base_version_id"],
            version["_id"],
            'ACTIVE',
            now(),
        )
        if not activated:
            raise HTTPException(
                status_code=409, detail={"code": "REVISION_CONFLICT"}
            )
    analysis = await proposal_application_repository.find_impact_analysis(
        proposal["impact_analysis_id"]
    )
    change_set = (
        await proposal_application_repository.find_change_set(analysis["change_set_id"])
        if analysis
        else None
    )
    if change_set:
        trace = await proposal_application_repository.find_trace(
            {
                "project_id": proposal["project_id"],
                "source_id": change_set["to_version_id"],
                "target_id": version["_id"],
                "status": 'CONFIRMED',
            }
        )
        if not trace:
            await proposal_application_repository.ensure_confirmed_requirement_trace(
                {
                    "_id": new_id('TL'),
                    "project_id": proposal["project_id"],
                    "source_type": 'requirement_version',
                    "source_id": change_set["to_version_id"],
                    "target_type": 'test_case_version',
                    "target_id": version["_id"],
                    "link_type": 'verifies',
                    "confidence": 1,
                    "origin": 'manual',
                    "status": 'CONFIRMED',
                    "revision": 1,
                    "evidence": proposal.get("evidence", []),
                    "created_by": user.id,
                    "created_at": now(),
                    "updated_at": now(),
                }
            )
    await index_artifact(
        version["project_id"],
        'test_case_version',
        version["test_case_id"],
        version["_id"],
        version["title"],
        version["plain_text_projection"],
        version["status"],
        'APPROVED_SOURCE',
        version["version"],
        requirement_version_ids=version.get("requirement_version_ids", []),
        acceptance_criterion_ids=version.get("acceptance_criterion_ids", []),
    )
    return version


async def create_test_draft_from_proposal(proposal, patch, user):
    
    required = set(['title', 'steps', 'expected_result_doc'])
    if not required.issubset(patch):
        raise HTTPException(
            status_code=422, detail={"code": 'INCOMPLETE_MAINTENANCE_PATCH'}
        )
    requirement_version_ids = list(dict.fromkeys(patch.get("requirement_version_ids", [])))
    source_evidence = []
    for version_id in requirement_version_ids:
        version = await proposal_application_repository.find_requirement_version(
            version_id, proposal["project_id"]
        )
        if not version:
            raise HTTPException(
                status_code=409,
                detail={"code": "REQUIREMENT_VERSION_NOT_FOUND"},
            )
        source_evidence.append(
            {
                "artifact_type": "requirement_version",
                "artifact_version_id": version_id,
                "text": requirement_test_evidence_text(version),
            }
        )
    payload = TestCaseDraftCreate(
        title=patch["title"],
        type=patch.get("type", 'custom'),
        objective_doc=patch.get("objective_doc", {'type': 'doc', 'content': []}),
        preconditions_doc=patch.get("preconditions_doc", {'type': 'doc', 'content': []}),
        steps=patch["steps"],
        test_data=patch.get("test_data", {}),
        expected_result_doc=patch["expected_result_doc"],
        requirement_version_ids=requirement_version_ids,
        origin='maintenance',
        evidence_refs=requirement_version_ids,
        source_evidence=source_evidence,
    )
    return await create_test_case_draft_record(
        proposal["project_id"],
        payload,
        user,
        draft_id=proposal.get("partial_version_id"),
    )


async def mark_test_obsolete(proposal):
    
    test_case = await proposal_application_repository.find_test_case(
        proposal["target_artifact_id"], proposal["project_id"]
    )
    if not test_case or test_case.get("current_version_id") != proposal["base_version_id"]:
        raise HTTPException(
            status_code=409, detail={"code": 'STALE_PROPOSAL'}
        )
    updated = await proposal_application_repository.mark_test_obsolete(
        test_case["_id"],
        proposal["project_id"],
        proposal["base_version_id"],
        'OBSOLETE',
        now(),
    )
    if not updated:
        raise HTTPException(
            status_code=409, detail={"code": 'STALE_PROPOSAL'}
        )
    return await proposal_application_repository.find_test_case(
        test_case["_id"], proposal["project_id"]
    )

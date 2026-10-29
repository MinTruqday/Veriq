import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.clients import ai_automation
from src.modules.requirements.services import requirement_records
from src.schemas.contracts.requirements import RequirementDraftPatch, RequirementVersionCreate


class RequirementDraftAutomationEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_draft_requirement_does_not_enqueue_maintenance_automation(self):
        user = SimpleNamespace(id="user-1", _ai_automation_run_id=None)
        version = {"_id": "version-1", "project_id": "project-1", "status": "DRAFT", "revision": 1}
        session = object()

        with patch.object(ai_automation, "queue_event", new=AsyncMock()) as queue:
            result = await ai_automation.queue_requirement_changed(version, user, session)

        self.assertIsNone(result)
        queue.assert_not_awaited()

    async def test_baselined_requirement_enqueues_maintenance_automation(self):
        user = SimpleNamespace(id="user-1", _ai_automation_run_id=None)
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "requirement_id": "requirement-1",
            "version": 2,
            "status": "BASELINED",
            "revision": 2,
        }
        session = object()

        with (
            patch(
                "src.repositories.requirement.requirement_repository.find_prior_baseline_candidates",
                new=AsyncMock(
                    return_value=[
                        {
                            "_id": "version-0",
                            "project_id": "project-1",
                            "requirement_id": "requirement-1",
                            "version": 1,
                            "status": "BASELINED",
                        }
                    ]
                ),
            ),
            patch.object(
                ai_automation, "queue_event", new=AsyncMock(return_value="event-1")
            ) as queue,
        ):
            result = await ai_automation.queue_requirement_changed(version, user, session)

        self.assertEqual(result, "event-1")
        queue.assert_awaited_once()
        self.assertEqual(queue.await_args.args[0], "REQUIREMENT_CHANGED")
        self.assertEqual(queue.await_args.kwargs["prior_baseline_version_id"], "version-0")
        self.assertIsNone(queue.await_args.kwargs["change_simulation_blocked_reason"])

    async def test_first_baseline_records_safe_waiting_reason(self):
        user = SimpleNamespace(id="user-1", _ai_automation_run_id=None)
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "requirement_id": "requirement-1",
            "version": 1,
            "status": "BASELINED",
            "revision": 1,
        }

        with (
            patch(
                "src.repositories.requirement.requirement_repository.find_prior_baseline_candidates",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(ai_automation, "queue_event", new=AsyncMock()) as queue,
        ):
            await ai_automation.queue_requirement_changed(version, user, object())

        self.assertIsNone(queue.await_args.kwargs["prior_baseline_version_id"])
        self.assertEqual(
            queue.await_args.kwargs["change_simulation_blocked_reason"],
            "NO_PRIOR_BASELINE",
        )

    async def test_saving_requirement_draft_emits_automation_event_for_saved_revision(self):
        user = SimpleNamespace(id="user-1", _ai_automation_run_id=None)
        requirement = {
            "_id": "requirement-1",
            "project_id": "project-1",
            "current_version_id": "version-1",
            "requirement_key": "REQ-1",
            "owner_id": "user-1",
        }
        version = {"_id": "version-1", "project_id": "project-1", "status": "DRAFT", "revision": 3}
        updated_version = {**version, "revision": 4, "title": "Đăng nhập bằng mã dùng một lần"}
        payload = RequirementDraftPatch(expected_revision=3, title=updated_version["title"])
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))

        with (
            patch.object(requirement_records.database, "client", client),
            patch.object(
                requirement_records, "get_project_entity", new=AsyncMock(return_value=requirement)
            ),
            patch.object(
                requirement_records.requirement_repository,
                "find_version",
                new=AsyncMock(return_value=version),
            ),
            patch.object(
                requirement_records.requirement_repository,
                "update_draft",
                new=AsyncMock(return_value=updated_version),
            ),
            patch.object(requirement_records, "audit", new=AsyncMock()) as audit,
            patch.object(
                requirement_records,
                "queue_requirement_changed",
                new=AsyncMock(return_value="requirement-event"),
            ) as queue,
        ):
            result = await requirement_records.update_requirement_draft_record(
                "project-1", "requirement-1", payload, user
            )

        queue.assert_awaited_once_with(updated_version, user, session)
        audit.assert_awaited_once_with(
            user.id,
            "requirement_draft_updated",
            "Requirement",
            "requirement-1",
            "project-1",
            session=session,
        )
        self.assertEqual(result["current_version"]["revision"], 4)

    async def test_requirement_collaboration_patch_validates_against_persisted_acceptance_criteria(self):
        user = SimpleNamespace(id="user-1", _ai_automation_run_id=None)
        requirement = {
            "_id": "requirement-1",
            "project_id": "project-1",
            "current_version_id": "version-1",
            "requirement_key": "REQ-1",
            "owner_id": "user-1",
        }
        content_doc = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Nội dung yêu cầu"}]}],
        }
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "status": "DRAFT",
            "revision": 3,
            "title": "Requirement có AC",
            "type": "functional",
            "priority": "medium",
            "risk": "medium",
            "content_doc": content_doc,
            "section_states": {"acceptance_criteria": "provided"},
            "custom_values": {},
        }
        acceptance_criteria = [
            {
                "_id": "AC-1",
                "project_id": "project-1",
                "requirement_version_id": "version-1",
                "key": "AC-1",
                "content_doc": content_doc,
                "status": "draft",
            }
        ]
        updated_version = {**version, "revision": 4, "details": {"context": "updated"}}
        payload = RequirementDraftPatch(expected_revision=3, details={"context": "updated"})
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))

        with (
            patch.object(requirement_records.database, "client", client),
            patch.object(requirement_records, "get_project_entity", new=AsyncMock(return_value=requirement)),
            patch.object(requirement_records.requirement_repository, "find_version", new=AsyncMock(return_value=version)),
            patch.object(requirement_records.requirement_repository, "list_acceptance_criteria", new=AsyncMock(return_value=acceptance_criteria)) as list_criteria,
            patch.object(requirement_records, "validate_requirement_custom_values", new=AsyncMock()) as validate_custom,
            patch.object(requirement_records.requirement_repository, "update_draft", new=AsyncMock(return_value=updated_version)),
            patch.object(requirement_records, "audit", new=AsyncMock()),
            patch.object(requirement_records, "queue_requirement_changed", new=AsyncMock()),
        ):
            await requirement_records.update_requirement_draft_record(
                "project-1", "requirement-1", payload, user
            )

        list_criteria.assert_awaited_once_with("version-1", None)
        validated_requirement = validate_custom.await_args.args[1]
        self.assertEqual(len(validated_requirement.acceptance_criteria), 1)
        self.assertEqual(validated_requirement.acceptance_criteria[0].key, "AC-1")

    async def test_requirement_collaboration_patch_returns_structured_validation_error_for_inconsistent_sections(self):
        user = SimpleNamespace(id="user-1", _ai_automation_run_id=None)
        requirement = {
            "_id": "requirement-1",
            "project_id": "project-1",
            "current_version_id": "version-1",
            "requirement_key": "REQ-1",
            "owner_id": "user-1",
        }
        content_doc = {"type": "doc", "content": []}
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "status": "DRAFT",
            "revision": 3,
            "title": "Requirement có AC",
            "type": "functional",
            "priority": "medium",
            "risk": "medium",
            "content_doc": content_doc,
            "section_states": {"acceptance_criteria": "provided"},
            "custom_values": {},
        }
        payload = RequirementDraftPatch(
            expected_revision=3,
            acceptance_criteria=[],
            section_states={"acceptance_criteria": "provided"},
        )

        with (
            patch.object(requirement_records, "get_project_entity", new=AsyncMock(return_value=requirement)),
            patch.object(requirement_records, "get_project", new=AsyncMock()),
            patch.object(requirement_records.requirement_repository, "find_version", new=AsyncMock(return_value=version)),
            patch.object(requirement_records, "validate_requirement_custom_values", new=AsyncMock()) as validate_custom,
        ):
            with self.assertRaises(HTTPException) as error:
                await requirement_records.update_requirement_draft_record(
                    "project-1", "requirement-1", payload, user
                )

        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.detail["code"], "REQUIREMENT_DRAFT_INVALID")
        validate_custom.assert_not_awaited()

    async def test_draft_identity_cas_failure_aborts_event_and_audit(self):
        user = SimpleNamespace(id="user-1", _ai_automation_run_id=None)
        requirement = {
            "_id": "requirement-1",
            "project_id": "project-1",
            "current_version_id": "version-1",
            "requirement_key": "REQ-1",
            "owner_id": "user-1",
        }
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "status": "DRAFT",
            "revision": 3,
        }
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        payload = RequirementDraftPatch(expected_revision=3, tags=["scope-change"])

        with (
            patch.object(requirement_records.database, "client", client),
            patch.object(
                requirement_records,
                "get_project_entity",
                new=AsyncMock(return_value=requirement),
            ),
            patch.object(
                requirement_records.requirement_repository,
                "find_version",
                new=AsyncMock(return_value=version),
            ),
            patch.object(
                requirement_records.requirement_repository,
                "update_draft",
                new=AsyncMock(return_value={**version, "revision": 4}),
            ),
            patch.object(
                requirement_records.requirement_repository,
                "update_requirement_identity",
                new=AsyncMock(return_value=False),
            ) as update_identity,
            patch.object(requirement_records, "audit", new=AsyncMock()) as audit,
            patch.object(
                requirement_records,
                "queue_requirement_changed",
                new=AsyncMock(),
            ) as queue,
        ):
            with self.assertRaises(HTTPException) as error:
                await requirement_records.update_requirement_draft_record(
                    "project-1", "requirement-1", payload, user
                )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(error.exception.detail["code"], "REVISION_CONFLICT")
        update_identity.assert_awaited_once()
        self.assertEqual(
            update_identity.await_args.args[3],
            "version-1",
        )
        queue.assert_not_awaited()
        audit.assert_not_awaited()

    async def test_new_requirement_version_keeps_side_effects_in_one_session(self):
        user = SimpleNamespace(id="user-1", _ai_automation_run_id=None)
        requirement = {
            "_id": "requirement-1",
            "project_id": "project-1",
            "current_version_id": "version-1",
            "requirement_key": "REQ-1",
            "owner_id": "user-1",
        }
        parent = {"_id": "version-1", "project_id": "project-1", "version": 1}
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        payload = RequirementVersionCreate(
            title="Yêu cầu phiên bản mới",
            change_reason="Bổ sung căn cứ nghiệp vụ",
            expected_current_version_id="version-1",
        )

        with (
            patch.object(requirement_records.database, "client", client),
            patch.object(
                requirement_records,
                "get_project_entity",
                new=AsyncMock(return_value=requirement),
            ),
            patch.object(
                requirement_records,
                "validate_requirement_sources",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_records,
                "validate_requirement_api_operations",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_records,
                "validate_requirement_custom_values",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_records.requirement_repository,
                "find_version",
                new=AsyncMock(return_value=parent),
            ),
            patch.object(
                requirement_records.requirement_repository,
                "find_latest_version",
                new=AsyncMock(return_value=parent),
            ),
            patch.object(
                requirement_records.requirement_repository,
                "insert_version",
                new=AsyncMock(),
            ) as insert_version,
            patch.object(
                requirement_records,
                "persist_acceptance_criteria",
                new=AsyncMock(),
            ) as persist_criteria,
            patch.object(
                requirement_records.requirement_repository,
                "activate_version",
                new=AsyncMock(return_value=True),
            ) as activate_version,
            patch.object(
                requirement_records,
                "queue_requirement_changed",
                new=AsyncMock(),
            ) as queue_event,
            patch(
                "src.modules.design.services.test_adequacy.supersede_requirement_assessments",
                new=AsyncMock(),
            ) as supersede_assessments,
            patch(
                "src.modules.requirements.services.requirement_clarifications.supersede_requirement_clarifications",
                new=AsyncMock(),
            ) as supersede_clarifications,
            patch.object(requirement_records, "audit", new=AsyncMock()) as audit,
            patch.object(
                requirement_records,
                "index_requirement_version",
                new=AsyncMock(return_value=True),
            ) as index_version,
        ):
            await requirement_records.create_requirement_version_record(
                "requirement-1", payload, user
            )

        insert_version.assert_awaited_once()
        self.assertIs(insert_version.await_args.kwargs["session"], session)
        persist_criteria.assert_awaited_once()
        self.assertIs(persist_criteria.await_args.args[2], session)
        activate_version.assert_awaited_once()
        self.assertIs(activate_version.await_args.kwargs["session"], session)
        queue_event.assert_awaited_once()
        self.assertIs(queue_event.await_args.args[2], session)
        self.assertIs(supersede_assessments.await_args.args[4], session)
        self.assertIs(supersede_clarifications.await_args.args[3], session)
        self.assertIs(audit.await_args.kwargs["session"], session)
        index_version.assert_awaited_once()


class _AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _AsyncSession(_AsyncContext):
    def start_transaction(self):
        return _AsyncContext()


if __name__ == "__main__":
    unittest.main()

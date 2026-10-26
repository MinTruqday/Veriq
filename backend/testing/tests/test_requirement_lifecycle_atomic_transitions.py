import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.requirements.services import requirement_lifecycle


class RequirementLifecycleAtomicTransitionTests(unittest.IsolatedAsyncioTestCase):
    async def test_submit_review_only_replays_the_exact_transition_revision(self):
        user = SimpleNamespace(id="ba-1")
        requirement = {
            "_id": "requirement-1",
            "project_id": "project-1",
            "current_version_id": "version-1",
        }
        replay = {
            "_id": "version-1",
            "project_id": "project-1",
            "status": "IN_REVIEW",
            "revision": 4,
            "review_submitted_by": user.id,
            "review_note": "Đã sẵn sàng",
        }
        with (
            patch.object(
                requirement_lifecycle,
                "get_project_entity",
                new=AsyncMock(return_value=requirement),
            ),
            patch.object(
                requirement_lifecycle.requirement_repository,
                "find_version",
                new=AsyncMock(return_value=replay),
            ),
        ):
            result = await requirement_lifecycle.submit_requirement_for_review(
                "project-1", "requirement-1", 3, "Đã sẵn sàng", user
            )

        self.assertIs(result, replay)

    async def test_submit_review_rejects_stale_or_different_transition_replay(self):
        user = SimpleNamespace(id="ba-1")
        requirement = {
            "_id": "requirement-1",
            "project_id": "project-1",
            "current_version_id": "version-1",
        }
        current = {
            "_id": "version-1",
            "project_id": "project-1",
            "status": "IN_REVIEW",
            "revision": 5,
            "review_submitted_by": user.id,
            "review_note": "Đã sẵn sàng",
        }
        with (
            patch.object(
                requirement_lifecycle,
                "get_project_entity",
                new=AsyncMock(return_value=requirement),
            ),
            patch.object(
                requirement_lifecycle.requirement_repository,
                "find_version",
                new=AsyncMock(return_value=current),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_lifecycle.submit_requirement_for_review(
                    "project-1", "requirement-1", 3, "Đã sẵn sàng", user
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "REVISION_CONFLICT")

    async def test_return_for_changes_only_replays_the_exact_transition_revision(self):
        user = SimpleNamespace(id="qa-1")
        requirement = {
            "_id": "requirement-1",
            "project_id": "project-1",
            "current_version_id": "version-1",
        }
        replay = {
            "_id": "version-1",
            "project_id": "project-1",
            "status": "DRAFT",
            "revision": 8,
            "changes_requested_by": user.id,
            "review_note": "Bổ sung tiêu chí chấp nhận",
        }
        with (
            patch.object(
                requirement_lifecycle,
                "get_project_entity",
                new=AsyncMock(return_value=requirement),
            ),
            patch.object(
                requirement_lifecycle.requirement_repository,
                "find_version",
                new=AsyncMock(return_value=replay),
            ),
        ):
            result = await requirement_lifecycle.return_requirement_for_changes(
                "project-1", "requirement-1", 7,
                "Bổ sung tiêu chí chấp nhận", user,
            )

        self.assertIs(result, replay)

    async def test_submit_review_updates_version_requirement_and_audit_together(self):
        await self._assert_transition_uses_one_session(
            requirement_lifecycle.submit_requirement_for_review,
            "requirement.submit_review",
            "DRAFT",
            "IN_REVIEW",
            "requirement_review_submitted",
        )

    async def test_return_for_changes_updates_version_requirement_and_audit_together(self):
        await self._assert_transition_uses_one_session(
            requirement_lifecycle.return_requirement_for_changes,
            "requirement.review",
            "IN_REVIEW",
            "DRAFT",
            "requirement_changes_requested",
        )

    async def _assert_transition_uses_one_session(
        self, operation, permission, source_status, target_status, audit_action
    ):
        user = SimpleNamespace(id="user-1")
        requirement = {
            "_id": "requirement-1",
            "project_id": "project-1",
            "current_version_id": "version-1",
        }
        version = {
            "_id": "version-1",
            "project_id": "project-1",
            "status": source_status,
            "revision": 3,
        }
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        with (
            patch.object(requirement_lifecycle.database, "client", client),
            patch.object(
                requirement_lifecycle,
                "get_project_entity",
                new=AsyncMock(return_value=requirement),
            ) as get_entity,
            patch.object(
                requirement_lifecycle.requirement_repository,
                "find_version",
                new=AsyncMock(
                    side_effect=[version, {**version, "status": target_status, "revision": 4}]
                ),
            ),
            patch.object(
                requirement_lifecycle.requirement_repository,
                "list_acceptance_criteria",
                new=AsyncMock(return_value=[]),
            ) as list_acceptance_criteria,
            patch.object(
                requirement_lifecycle.requirement_repository,
                "find_project_settings",
                new=AsyncMock(return_value={"settings": {"requirement_lint_blocking": False}}),
            ),
            patch.object(
                requirement_lifecycle,
                "requirement_findings",
                return_value=[],
            ),
            patch.object(
                requirement_lifecycle.requirement_repository,
                "transition_version",
                new=AsyncMock(return_value=True),
            ) as transition_version,
            patch.object(
                requirement_lifecycle.requirement_repository,
                "set_requirement_status",
                new=AsyncMock(return_value=True),
            ) as set_requirement_status,
            patch.object(requirement_lifecycle, "audit", new=AsyncMock()) as audit,
        ):
            result = await operation(
                "project-1", "requirement-1", 3, "Rà soát nội dung", user
            )

        get_entity.assert_awaited_once_with(
            "requirements", "requirement-1", user, permission
        )
        transition_version.assert_awaited_once()
        if operation == requirement_lifecycle.submit_requirement_for_review:
            list_acceptance_criteria.assert_awaited_once_with("version-1", None)
        else:
            list_acceptance_criteria.assert_not_awaited()
        self.assertEqual(transition_version.await_args.args[3], source_status)
        self.assertEqual(transition_version.await_args.args[4], target_status)
        self.assertIs(transition_version.await_args.kwargs["session"], session)
        set_requirement_status.assert_awaited_once_with(
            "requirement-1", "project-1", target_status,
            set_requirement_status.await_args.args[3], session=session,
        )
        audit.assert_awaited_once()
        self.assertEqual(audit.await_args.args[1], audit_action)
        self.assertIs(audit.await_args.kwargs["session"], session)
        self.assertEqual(result["status"], target_status)

    async def test_baseline_lints_all_acceptance_criteria_before_publication(self):
        user = SimpleNamespace(id="qa-1")
        version = {
            "_id": "version-1",
            "requirement_id": "requirement-1",
            "project_id": "project-1",
            "status": "IN_REVIEW",
            "revision": 3,
        }
        criteria = [{"_id": f"criterion-{index}"} for index in range(1001)]
        updated = {**version, "status": "BASELINED", "revision": 4}
        session = _AsyncSession()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        with (
            patch.object(requirement_lifecycle.database, "client", client),
            patch.object(
                requirement_lifecycle,
                "require_automation_publication_authority",
            ) as publication_authority,
            patch.object(
                requirement_lifecycle,
                "get_project_entity",
                new=AsyncMock(return_value=version),
            ),
            patch.object(
                requirement_lifecycle.requirement_repository,
                "list_acceptance_criteria",
                new=AsyncMock(return_value=criteria),
            ) as list_acceptance_criteria,
            patch.object(
                requirement_lifecycle,
                "requirement_findings",
                return_value=[],
            ) as lint,
            patch.object(
                requirement_lifecycle.requirement_repository,
                "find_project_settings",
                new=AsyncMock(return_value={"settings": {"requirement_lint_blocking": False}}),
            ),
            patch.object(
                requirement_lifecycle.requirement_repository,
                "baseline_version",
                new=AsyncMock(return_value=updated),
            ) as baseline_version,
            patch.object(
                requirement_lifecycle.requirement_repository,
                "set_current_baseline",
                new=AsyncMock(),
            ),
            patch(
                "src.modules.design.services.test_adequacy.supersede_requirement_assessments",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_lifecycle.requirement_repository,
                "approve_acceptance_criteria",
                new=AsyncMock(),
            ),
            patch.object(requirement_lifecycle, "audit", new=AsyncMock()),
            patch(
                "src.clients.ai_automation.queue_requirement_changed",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_lifecycle,
                "index_requirement_version",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                requirement_lifecycle.requirement_repository,
                "find_version",
                new=AsyncMock(return_value=updated),
            ),
        ):
            result = await requirement_lifecycle.baseline_requirement(
                "version-1", 3, "Đã rà soát", user
            )

        publication_authority.assert_called_once_with(user, "requirement.approve")
        list_acceptance_criteria.assert_awaited_once_with("version-1", None)
        lint.assert_called_once_with(version, criteria)
        baseline_version.assert_awaited_once()
        self.assertEqual(result.version["status"], "BASELINED")


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

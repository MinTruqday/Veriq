import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from src.modules.requirements.services import requirement_import_workflow
from src.schemas.contracts.requirements import ImportConfirm


class AsyncContext:
    def __init__(self, value):
        self.value = value
        self.exit_exception = None

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, traceback):
        self.exit_exception = exc
        return False


class FakeSession:
    def __init__(self):
        self.transaction = AsyncContext(self)
        self.exit_exception = None

    def start_transaction(self):
        return self.transaction

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self.exit_exception = exc
        return False


class RequirementImportConfirmationRevisionTests(unittest.IsolatedAsyncioTestCase):
    def test_confirmation_contract_requires_a_preview_revision(self):
        with self.assertRaises(ValidationError):
            ImportConfirm(selected_indexes=[0])

        payload = ImportConfirm(selected_indexes=[0], expected_revision=7)
        self.assertEqual(payload.expected_revision, 7)

    async def test_confirmed_import_retry_reindexes_only_failed_imported_versions(self):
        user = SimpleNamespace(id="user-1")
        job = {
            "_id": "IMPORT-1",
            "project_id": "PROJECT-1",
            "status": "CONFIRMED",
            "created_requirement_version_ids": ["REQV-1", "REQV-2", "REQV-3"],
        }
        versions = [
            {"_id": "REQV-1", "index_status": "READY"},
            {"_id": "REQV-2", "index_status": "FAILED"},
            {"_id": "REQV-3", "index_status": "READY"},
        ]
        payload = ImportConfirm(expected_revision=9)

        with (
            patch.object(
                requirement_import_workflow,
                "get_project_entity",
                new=AsyncMock(return_value=job),
            ),
            patch.object(
                requirement_import_workflow,
                "authorize_requirement_import_job",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_import_workflow, "get_project", new=AsyncMock()
            ),
            patch.object(
                requirement_import_workflow.requirement_repository,
                "list_versions_by_ids",
                new=AsyncMock(return_value=versions),
            ) as list_versions,
            patch.object(
                requirement_import_workflow,
                "index_requirement_version",
                new=AsyncMock(return_value=True),
            ) as index_version,
        ):
            result = await requirement_import_workflow.confirm_requirement_import_job(
                "IMPORT-1", payload, user
            )

        self.assertIs(result["job"], job)
        self.assertIsNone(result["requirements"])
        list_versions.assert_awaited_once_with("PROJECT-1", ["REQV-1", "REQV-2", "REQV-3"], 3)
        index_version.assert_awaited_once_with(versions[1])

    async def test_stale_confirmation_claim_does_not_create_requirements(self):
        user = SimpleNamespace(id="user-1")
        job = {
            "_id": "IMPORT-1",
            "project_id": "PROJECT-1",
            "status": "PREVIEW_READY",
            "revision": 8,
            "preview": [
                {
                    "title": "Đăng nhập",
                    "content_doc": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Người dùng đăng nhập bằng thông tin hợp lệ",
                                    }
                                ],
                            }
                        ],
                    },
                    "source_refs": [{"requirement_document_id": "RDOC-1"}],
                }
            ],
        }
        current_job = {**job, "revision": 9}
        payload = ImportConfirm(selected_indexes=[0], expected_revision=8)

        with (
            patch.object(
                requirement_import_workflow,
                "get_project_entity",
                new=AsyncMock(return_value=job),
            ),
            patch.object(
                requirement_import_workflow,
                "authorize_requirement_import_job",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_import_workflow, "get_project", new=AsyncMock()
            ),
            patch.object(
                requirement_import_workflow,
                "compare_requirement_import_job",
                new=AsyncMock(
                    return_value={
                        "comparisons": [{"candidate_index": 0, "matches": []}]
                    }
                ),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "claim_confirmation",
                new=AsyncMock(return_value=False),
            ) as claim,
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "find",
                new=AsyncMock(return_value=current_job),
            ),
            patch.object(
                requirement_import_workflow,
                "create_requirement_record",
                new=AsyncMock(),
            ) as create_requirement,
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_import_workflow.confirm_requirement_import_job(
                    "IMPORT-1", payload, user
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "IMPORT_CONFIRM_IN_PROGRESS")
        self.assertEqual(claim.await_args.args[-1], 8)
        create_requirement.assert_not_awaited()

    async def test_concurrent_confirmed_replay_recovers_unindexed_versions(self):
        user = SimpleNamespace(id="user-1")
        job = {
            "_id": "IMPORT-1",
            "project_id": "PROJECT-1",
            "status": "PREVIEW_READY",
            "revision": 8,
            "preview": [
                {
                    "title": "Đăng nhập",
                    "content_doc": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Người dùng đăng nhập bằng thông tin hợp lệ",
                                    }
                                ],
                            }
                        ],
                    },
                    "source_refs": [{"requirement_document_id": "RDOC-1"}],
                }
            ],
        }
        confirmed = {
            **job,
            "status": "CONFIRMED",
            "created_requirement_version_ids": ["REQV-1", "REQV-2"],
        }
        versions = [
            {"_id": "REQV-1", "index_status": "READY"},
            {"_id": "REQV-2", "index_status": "FAILED"},
        ]
        with (
            patch.object(
                requirement_import_workflow,
                "get_project_entity",
                new=AsyncMock(return_value=job),
            ),
            patch.object(
                requirement_import_workflow,
                "authorize_requirement_import_job",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_import_workflow, "get_project", new=AsyncMock()
            ),
            patch.object(
                requirement_import_workflow,
                "compare_requirement_import_job",
                new=AsyncMock(
                    return_value={
                        "comparisons": [{"candidate_index": 0, "matches": []}]
                    }
                ),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "claim_confirmation",
                new=AsyncMock(return_value=False),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "find",
                new=AsyncMock(return_value=confirmed),
            ),
            patch.object(
                requirement_import_workflow.requirement_repository,
                "list_versions_by_ids",
                new=AsyncMock(return_value=versions),
            ) as list_versions,
            patch.object(
                requirement_import_workflow,
                "index_requirement_version",
                new=AsyncMock(return_value=True),
            ) as index_version,
        ):
            result = await requirement_import_workflow.confirm_requirement_import_job(
                "IMPORT-1",
                ImportConfirm(selected_indexes=[0], expected_revision=8),
                user,
            )

        self.assertIs(result["job"], confirmed)
        self.assertIsNone(result["requirements"])
        list_versions.assert_awaited_once_with(
            "PROJECT-1", ["REQV-1", "REQV-2"], 2
        )
        index_version.assert_awaited_once_with(versions[1])

    async def run_import_confirmation(self, *, fail_on_second_create=False):
        user = SimpleNamespace(id="user-1")
        candidates = [
            {
                "title": f"Yêu cầu {index}",
                "content_doc": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": f"Nội dung {index}"}],
                        }
                    ],
                },
                "source_refs": [{"requirement_document_id": "RDOC-1"}],
            }
            for index in (1, 2)
        ]
        job = {
            "_id": "IMPORT-1",
            "project_id": "PROJECT-1",
            "status": "PREVIEW_READY",
            "revision": 8,
            "preview": candidates,
        }
        session = FakeSession()
        fake_database = SimpleNamespace(
            client=SimpleNamespace(start_session=AsyncMock(return_value=session))
        )
        first_requirement = {
            "_id": "REQ-1",
            "current_version": {"_id": "REQV-1"},
        }
        create_requirement = AsyncMock(
            side_effect=[
                first_requirement,
                RuntimeError("fault injected after first candidate")
                if fail_on_second_create
                else {"_id": "REQ-2", "current_version": {"_id": "REQV-2"}},
            ]
        )
        confirm = AsyncMock(return_value=True)
        reset = AsyncMock()
        delete_created = AsyncMock()
        index = AsyncMock()
        audit = AsyncMock()
        confirmed_job = {
            "_id": "IMPORT-1",
            "project_id": "PROJECT-1",
            "status": "CONFIRMED",
            "created_requirement_version_ids": ["REQV-1", "REQV-2"],
        }
        indexed_versions = [
            {"_id": "REQV-1", "index_status": "PENDING"},
            {"_id": "REQV-2", "index_status": "PENDING"},
        ]

        with (
            patch.object(
                requirement_import_workflow,
                "get_project_entity",
                new=AsyncMock(return_value=job),
            ),
            patch.object(
                requirement_import_workflow,
                "authorize_requirement_import_job",
                new=AsyncMock(),
            ),
            patch.object(
                requirement_import_workflow, "get_project", new=AsyncMock()
            ),
            patch.object(
                requirement_import_workflow,
                "compare_requirement_import_job",
                new=AsyncMock(
                    return_value={
                        "comparisons": [
                            {"candidate_index": 0, "matches": []},
                            {"candidate_index": 1, "matches": []},
                        ]
                    }
                ),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "claim_confirmation",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "confirm",
                new=confirm,
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "find",
                new=AsyncMock(return_value=confirmed_job),
            ),
            patch.object(
                requirement_import_workflow.requirement_repository,
                "list_versions_by_ids",
                new=AsyncMock(return_value=indexed_versions),
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "reset_confirmation",
                new=reset,
            ),
            patch.object(
                requirement_import_workflow.requirement_import_repository,
                "delete_created_requirements",
                new=delete_created,
            ),
            patch.object(
                requirement_import_workflow,
                "create_requirement_record",
                new=create_requirement,
            ),
            patch.object(
                requirement_import_workflow,
                "index_requirement_version",
                new=index,
            ),
            patch.object(requirement_import_workflow, "audit", new=audit),
            patch.object(requirement_import_workflow, "database", fake_database),
        ):
            result = None
            error = None
            try:
                result = await requirement_import_workflow.confirm_requirement_import_job(
                    "IMPORT-1",
                    ImportConfirm(selected_indexes=[0, 1], expected_revision=8),
                    user,
                )
            except RuntimeError as caught:
                error = caught

        return (
            result,
            error,
            session,
            create_requirement,
            confirm,
            reset,
            delete_created,
            index,
            audit,
        )

    async def test_batch_confirmation_persists_job_and_audit_in_same_transaction(self):
        result, error, session, create, confirm, reset, delete_created, index, audit = await self.run_import_confirmation()

        self.assertIsNone(error)
        self.assertEqual(len(result["requirements"]), 2)
        self.assertIsNone(session.exit_exception)
        self.assertEqual(create.await_count, 2)
        self.assertTrue(all(call.kwargs["session"] is session for call in create.await_args_list))
        self.assertIs(confirm.await_args.kwargs["session"], session)
        self.assertTrue(all(call.kwargs.get("session") is session for call in audit.await_args_list))
        reset.assert_not_awaited()
        delete_created.assert_not_awaited()
        self.assertEqual(index.await_count, 2)

    async def test_failure_after_first_candidate_rolls_back_without_compensation_deletes(self):
        result, error, session, create, confirm, reset, delete_created, index, audit = await self.run_import_confirmation(fail_on_second_create=True)

        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIs(session.exit_exception, error)
        self.assertEqual(create.await_count, 2)
        confirm.assert_not_awaited()
        self.assertEqual(reset.await_args.args[2], "CONFIRMING")
        self.assertEqual(reset.await_args.args[3], "PREVIEW_READY")
        delete_created.assert_not_awaited()
        index.assert_not_awaited()
        failure_audit = [
            call
            for call in audit.await_args_list
            if call.args[1] == "requirement_import_confirmation_failed"
        ]
        self.assertEqual(len(failure_audit), 1)


if __name__ == "__main__":
    unittest.main()

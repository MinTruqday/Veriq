import unittest
from unittest.mock import AsyncMock, patch

from src.modules.requirements.services import requirement_document_worker as worker


class RequirementDocumentWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_processes_durable_uploaded_document_as_its_owner(self):
        document = {
            "_id": "RDOC-queued",
            "project_id": "PRJ-queued",
            "created_by": "BA-1",
            "revision": 7,
            "status": "UPLOADED",
        }
        with (
            patch.object(
                worker.requirement_document_repository,
                "next_parse_candidate",
                new=AsyncMock(return_value=document),
            ),
            patch.object(worker, "get_project", new=AsyncMock()) as authorize,
            patch.object(
                worker,
                "retry_requirement_document_parse_record",
                new=AsyncMock(),
            ) as process,
        ):
            self.assertTrue(await worker.process_next_requirement_document_parse())

        authorize.assert_awaited_once()
        user = authorize.await_args.args[1]
        self.assertEqual(user.id, "BA-1")
        self.assertEqual(authorize.await_args.args[2], "requirement_document.extract")
        process.assert_awaited_once()
        command = process.await_args.args[1]
        self.assertEqual(command.expected_revision, 7)
        self.assertEqual(process.await_args.kwargs["_document"], document)

    async def test_returns_false_when_no_persisted_parse_job_exists(self):
        with patch.object(
            worker.requirement_document_repository,
            "next_parse_candidate",
            new=AsyncMock(return_value=None),
        ):
            self.assertFalse(await worker.process_next_requirement_document_parse())

    async def test_revoked_project_access_fails_closed_and_records_reason(self):
        from fastapi import HTTPException

        document = {
            "_id": "RDOC-revoked",
            "project_id": "PRJ-revoked",
            "created_by": "BA-2",
            "revision": 2,
            "status": "UPLOADED",
        }
        with (
            patch.object(
                worker.requirement_document_repository,
                "next_parse_candidate",
                new=AsyncMock(return_value=document),
            ),
            patch.object(
                worker, "get_project", new=AsyncMock(side_effect=HTTPException(403))
            ),
            patch.object(
                worker.requirement_document_repository,
                "fail_unavailable_owner_parse",
                new=AsyncMock(return_value={"status": "PARSE_FAILED"}),
            ) as fail,
            patch.object(worker, "audit", new=AsyncMock()) as audit,
            patch.object(
                worker,
                "retry_requirement_document_parse_record",
                new=AsyncMock(),
            ) as process,
        ):
            self.assertTrue(await worker.process_next_requirement_document_parse())

        self.assertEqual(fail.await_args.args[1], "DOCUMENT_OWNER_ACCESS_UNAVAILABLE")
        audit.assert_awaited_once()
        process.assert_not_awaited()

    async def test_suspended_project_is_deferred_without_blocking_other_queue_items(self):
        from fastapi import HTTPException

        document = {
            "_id": "RDOC-suspended",
            "project_id": "PRJ-suspended",
            "created_by": "BA-3",
            "revision": 4,
            "status": "UPLOADED",
        }
        with (
            patch.object(
                worker.requirement_document_repository,
                "next_parse_candidate",
                new=AsyncMock(return_value=document),
            ),
            patch.object(
                worker, "get_project", new=AsyncMock(side_effect=HTTPException(423))
            ),
            patch.object(
                worker.requirement_document_repository,
                "defer_parse_attempt",
                new=AsyncMock(return_value=True),
            ) as defer,
            patch.object(
                worker,
                "retry_requirement_document_parse_record",
                new=AsyncMock(),
            ) as process,
        ):
            self.assertTrue(await worker.process_next_requirement_document_parse())

        defer.assert_awaited_once()
        self.assertEqual(defer.await_args.args[0], document)
        process.assert_not_awaited()

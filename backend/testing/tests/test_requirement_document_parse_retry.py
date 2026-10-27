import asyncio
import os
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.requirements.services import requirement_documents
from src.core.common import now
from src.core.configuration import _positive_int_environment


class RequirementDocumentParseRetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id="user-parse-retry", is_system_admin=False)
        self.deduplication_lookup = patch.object(
            requirement_documents.requirement_document_repository,
            "find_by_deduplication_key",
            new=AsyncMock(return_value=None),
        )
        self.deduplication_lookup.start()
        self.addCleanup(self.deduplication_lookup.stop)
        self.source_block_replace = patch.object(
            requirement_documents.requirement_source_block_repository,
            "replace_version",
            new=AsyncMock(return_value=1),
        )
        self.source_block_replace.start()
        self.addCleanup(self.source_block_replace.stop)
        self.document = {
            "_id": "RDOC-parse-retry",
            "project_id": "project-parse-retry",
            "filename": "requirements.txt",
            "format": "txt",
            "raw_source": {"storage": "embedded", "content": "As a user, I can sign in."},
            "status": "UPLOADED",
            "revision": 3,
            "ai_enabled": False,
        }
        self.payload = SimpleNamespace(expected_revision=3)

    async def test_new_upload_is_queued_for_the_durable_parse_worker(self):
        with (
            patch.object(requirement_documents, "supported_requirement_formats", return_value={"txt"}),
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(requirement_documents, "validate_document_recipients", new=AsyncMock(return_value=[])),
            patch.object(requirement_documents, "resolve_source_successor", new=AsyncMock(return_value=None)),
            patch.object(requirement_documents.requirement_document_repository, "find_by_hash", new=AsyncMock(return_value=None)),
            patch.object(requirement_documents, "find_reusable_document_duplicate", new=AsyncMock(return_value=None)),
            patch.object(requirement_documents, "new_id", return_value="RDOC-new-upload"),
            patch.object(requirement_documents, "store_raw_requirement_source", new=AsyncMock(return_value={"sha256": "hash", "object_key": "key"})),
            patch.object(requirement_documents.requirement_document_repository, "insert", new=AsyncMock()),
            patch.object(requirement_documents, "audit", new=AsyncMock()),
            patch.object(requirement_documents, "parse_requirement_source", new=AsyncMock()) as unleased_parser,
            patch.object(requirement_documents, "retry_requirement_document_parse_record", new=AsyncMock()) as parse_pipeline,
        ):
            result = await requirement_documents.upload_requirement_document_record(
                "project-parse-retry",
                "txt",
                "requirements.txt",
                "text/plain",
                b"requirements",
                self.user,
            )

        self.assertEqual(result.data["status"], "UPLOADED")
        self.assertEqual(result.status, "QUEUED")
        unleased_parser.assert_not_awaited()
        parse_pipeline.assert_not_awaited()

    async def test_uploaded_document_recovers_after_interrupted_upload(self):
        claimed = SimpleNamespace(matched_count=1)
        parsed = {**self.document, "status": "READY", "normalized_content": "As a user, I can sign in."}
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(requirement_documents.requirement_document_repository, "claim_status", new=AsyncMock(return_value=claimed)) as claim,
            patch.object(requirement_documents, "read_raw_requirement_source", new=AsyncMock(return_value=b"source")),
            patch.object(requirement_documents, "parse_requirement_source", new=AsyncMock(return_value=("As a user, I can sign in.", {}))),
            patch.object(requirement_documents.requirement_document_repository, "transition_status", new=AsyncMock(return_value=parsed)) as transition,
            patch.object(requirement_documents, "audit", new=AsyncMock()),
        ):
            result = await requirement_documents.retry_requirement_document_parse_record(
                self.document["_id"], self.payload, self.user
            )

        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.data["status"], "READY")
        self.assertEqual(claim.await_args.args[2], "UPLOADED")
        self.assertEqual(transition.await_args.args[2], "PARSING")

    async def test_ready_document_retry_repairs_missing_ai_ingestion_event(self):
        ready = {**self.document, "status": "READY", "ai_enabled": True}
        current = {**ready, "index_status": "INDEXED"}
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=ready)),
            patch.object(requirement_documents, "recover_document_ingestion", new=AsyncMock(return_value=True)) as recover,
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=current)),
        ):
            result = await requirement_documents.retry_requirement_document_parse_record(
                self.document["_id"], self.payload, self.user
            )

        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.data["index_status"], "INDEXED")
        recover.assert_awaited_once_with(ready, self.user)

    async def test_uploaded_document_recovery_continues_ai_index_and_queue(self):
        claimed = SimpleNamespace(matched_count=1)
        parsed = {**self.document, "status": "READY", "ai_enabled": True}
        indexed = {**parsed, "index_status": "INDEXED"}
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(requirement_documents.requirement_document_repository, "claim_status", new=AsyncMock(return_value=claimed)),
            patch.object(requirement_documents, "read_raw_requirement_source", new=AsyncMock(return_value=b"source")),
            patch.object(requirement_documents, "parse_requirement_source", new=AsyncMock(return_value=("requirement", {}))),
            patch.object(requirement_documents.requirement_document_repository, "transition_status", new=AsyncMock(return_value=parsed)),
            patch.object(requirement_documents, "audit", new=AsyncMock()),
            patch.object(requirement_documents, "index_requirement_document", new=AsyncMock(return_value=True)) as index,
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=indexed)),
            patch.object(requirement_documents.ai_automation_access_repository, "allow_source", new=AsyncMock(return_value=True)) as allow_source,
            patch.object(requirement_documents, "queue_document_ingestion", new=AsyncMock()) as queue,
        ):
            result = await requirement_documents.retry_requirement_document_parse_record(
                self.document["_id"], self.payload, self.user
            )

        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.data["index_status"], "INDEXED")
        index.assert_awaited_once_with(parsed)
        allow_source.assert_awaited_once_with("source:RDOC-parse-retry")
        queue.assert_awaited_once_with(indexed, self.user)

    async def test_uploaded_document_recovery_reports_parser_failure_without_success(self):
        claimed = SimpleNamespace(matched_count=1)
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents.requirement_document_repository, "claim_status", new=AsyncMock(return_value=claimed)),
            patch.object(requirement_documents, "read_raw_requirement_source", new=AsyncMock(return_value=b"source")),
            patch.object(requirement_documents, "parse_requirement_source", new=AsyncMock(side_effect=ValueError("bad source"))),
            patch.object(requirement_documents.requirement_document_repository, "transition_status", new=AsyncMock(return_value={**self.document, "status": "PARSE_FAILED"})),
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value={**self.document, "status": "PARSE_FAILED"})),
            patch.object(requirement_documents, "audit", new=AsyncMock()),
        ):
            result = await requirement_documents.retry_requirement_document_parse_record(
                self.document["_id"], self.payload, self.user
            )

        self.assertEqual(result.status, "DEGRADED")
        self.assertEqual(result.degraded_mode, "PARSER_FAILED")
        self.assertEqual(result.data["status"], "PARSE_FAILED")

    async def test_parser_timeout_releases_lease_and_returns_retryable_failure(self):
        claimed = SimpleNamespace(matched_count=1)
        failed = {**self.document, "status": "PARSE_FAILED", "parse_error_type": "TimeoutError"}

        async def never_finishes(_document, _attempt_id):
            await asyncio.Event().wait()

        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents.requirement_document_repository, "claim_status", new=AsyncMock(return_value=claimed)),
            patch.object(requirement_documents, "read_and_parse_requirement_source", new=never_finishes),
            patch.object(requirement_documents, "settings") as settings,
            patch.object(requirement_documents.requirement_document_repository, "transition_status", new=AsyncMock(return_value=failed)) as transition,
            patch.object(requirement_documents, "audit", new=AsyncMock()),
        ):
            settings.DOCUMENT_PARSE_LEASE_SECONDS = 900
            settings.DOCUMENT_PARSE_TIMEOUT_SECONDS = 0.001
            result = await requirement_documents.retry_requirement_document_parse_record(
                self.document["_id"], self.payload, self.user
            )

        self.assertEqual(result.status, "DEGRADED")
        self.assertEqual(
            result.degraded_mode,
            "PARSER_TIMEOUT",
            transition.await_args.args[3].get("parse_error_type"),
        )
        self.assertEqual(result.data["status"], "PARSE_FAILED")
        self.assertEqual(transition.await_args.args[3]["parse_error_type"], "TimeoutError")

    async def test_retry_with_stale_revision_is_rejected(self):
        self.payload.expected_revision = 2
        claimed = SimpleNamespace(matched_count=0)
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents.requirement_document_repository, "claim_status", new=AsyncMock(return_value=claimed)),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.retry_requirement_document_parse_record(
                    self.document["_id"], self.payload, self.user
                )

        self.assertEqual(raised.exception.status_code, 409)

    async def test_active_parse_is_not_reclaimed(self):
        active = {
            **self.document,
            "status": "PARSING",
            "updated_at": now(),
        }
        self.assertFalse(requirement_documents.can_retry_requirement_document_parse(active))

    async def test_stale_parse_is_claimed_with_new_attempt_and_fences_old_worker(self):
        stale = {
            **self.document,
            "status": "PARSING",
            "updated_at": now() - timedelta(seconds=3600),
        }
        claimed = SimpleNamespace(matched_count=1)
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=stale)),
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(requirement_documents.requirement_document_repository, "claim_stale_parse", new=AsyncMock(return_value=claimed)) as claim,
            patch.object(requirement_documents, "read_raw_requirement_source", new=AsyncMock(return_value=b"source")),
            patch.object(requirement_documents, "read_and_parse_requirement_source", new=AsyncMock(return_value=("requirement", {}))),
            patch.object(requirement_documents.requirement_document_repository, "transition_status", new=AsyncMock(return_value=None)) as transition,
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=None)),
            patch.object(requirement_documents.requirement_source_block_repository, "delete_version", new=AsyncMock(return_value=1)),
            patch.object(requirement_documents, "audit", new=AsyncMock()) as audit,
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.retry_requirement_document_parse_record(
                    self.document["_id"], self.payload, self.user
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "PARSE_RETRY_CONFLICT")
        self.assertEqual(claim.await_args.args[0], self.document["_id"])
        self.assertEqual(transition.await_args.kwargs["attempt_id"], claim.await_args.args[-1])
        audit.assert_not_awaited()

    async def test_parse_lease_heartbeat_stops_after_attempt_is_fenced(self):
        with (
            patch.object(requirement_documents.asyncio, "sleep", new=AsyncMock()),
            patch.object(
                requirement_documents.requirement_document_repository,
                "heartbeat_parse_attempt",
                new=AsyncMock(
                    side_effect=[
                        SimpleNamespace(matched_count=1),
                        SimpleNamespace(matched_count=0),
                    ]
                ),
            ) as heartbeat,
        ):
            await requirement_documents.maintain_requirement_parse_lease(
                self.document["_id"], self.document["project_id"], "attempt-1"
            )

        self.assertEqual(heartbeat.await_count, 2)

    def test_parse_lease_configuration_must_be_positive(self):
        with patch.dict(os.environ, {"TEST_PARSE_LEASE": "120"}):
            self.assertEqual(_positive_int_environment("TEST_PARSE_LEASE", "900"), 120)
        with patch.dict(os.environ, {"TEST_PARSE_LEASE": "0"}):
            with self.assertRaises(ValueError):
                _positive_int_environment("TEST_PARSE_LEASE", "900")

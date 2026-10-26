import hashlib
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from src.modules.requirements.services import requirement_documents


class RequirementDocumentUploadPipelineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id="user-upload-test", is_system_admin=False)
        self.project_id = "project-upload-test"
        self.data = b"User Story: A user signs in with a valid account."
        self.document = {
            "_id": "RDOC-upload-test",
            "project_id": self.project_id,
            "filename": "requirements.txt",
            "format": "txt",
            "raw_source": {
                "storage": "object_storage",
                "object_key": "temporary/source.txt",
                "sha256": "content-hash",
                "size": len(self.data),
            },
            "normalized_content": self.data.decode(),
            "source_version": "1",
            "approval_status": "DRAFT",
            "status": "READY",
            "index_status": "INDEXED",
            "ai_enabled": True,
            "visibility": "private",
            "shared_with": [],
            "source_type": "REFERENCE",
            "revision": 2,
            "created_by": self.user.id,
        }

    def common_patches(self):
        patches = [
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(requirement_documents, "validate_document_recipients", new=AsyncMock(return_value=[])),
            patch.object(
                requirement_documents,
                "store_raw_requirement_source",
                new=AsyncMock(return_value=self.document["raw_source"]),
            ),
            patch.object(requirement_documents, "audit", new=AsyncMock()),
            patch.object(requirement_documents.requirement_document_repository, "find_by_hash", new=AsyncMock(return_value=None)),
            patch.object(requirement_documents.requirement_document_repository, "insert", new=AsyncMock()),
            patch.object(requirement_documents.requirement_document_repository, "update", new=AsyncMock()),
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=self.document)),
            patch.object(
                requirement_documents,
                "retry_requirement_document_parse_record",
                new=AsyncMock(return_value=requirement_documents.RequirementDocumentResult(self.document)),
            ),
            patch.object(
                requirement_documents.requirement_document_repository,
                "find_reusable_duplicate",
                new=AsyncMock(return_value=None),
            ),
        ]
        return patches

    async def test_ocr_language_is_rejected_for_non_pdf_before_storage(self):
        from fastapi import HTTPException

        with patch.object(
            requirement_documents,
            "store_raw_requirement_source",
            new=AsyncMock(),
        ) as store:
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.upload_requirement_document_record(
                    self.project_id,
                    "txt",
                    "requirements.txt",
                    "text/plain",
                    self.data,
                    self.user,
                    ocr_language="iso:en",
                )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(
            raised.exception.detail["code"], "OCR_LANGUAGE_REQUIRES_PDF"
        )
        store.assert_not_awaited()

    async def test_upload_persists_source_for_durable_background_parse(self):
        patches = self.common_patches()
        with ExitStack() as stack:
            mocks = [stack.enter_context(item) for item in patches]
            result = await requirement_documents.upload_requirement_document_record(
                self.project_id,
                "txt",
                "requirements.txt",
                "text/plain",
                self.data,
                self.user,
                visibility="private",
                ai_enabled=True,
            )

        self.assertEqual(result.status, "QUEUED")
        self.assertEqual(result.data["_id"], mocks[5].await_args.args[0]["_id"])
        mocks[2].assert_awaited_once()
        self.assertEqual(result.data["status"], "UPLOADED")
        mocks[8].assert_not_awaited()
        mocks[6].assert_not_awaited()

    async def test_upload_does_not_claim_parse_success_before_worker_runs(self):
        patches = self.common_patches()
        with ExitStack() as stack:
            mocks = [stack.enter_context(item) for item in patches]
            result = await requirement_documents.upload_requirement_document_record(
                self.project_id,
                "txt",
                "requirements.txt",
                "text/plain",
                self.data,
                self.user,
                visibility="private",
                ai_enabled=True,
            )

        self.assertEqual(result.data["status"], "UPLOADED")
        self.assertEqual(result.status, "QUEUED")
        mocks[6].assert_not_awaited()
        mocks[8].assert_not_awaited()

    async def test_duplicate_upload_reuses_existing_document_without_storage_write(self):
        duplicate_lookup = AsyncMock(return_value=self.document)
        access_check = AsyncMock(return_value=self.document)
        with (
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(requirement_documents.requirement_document_repository, "find_by_hash", new=duplicate_lookup),
            patch.object(requirement_documents, "require_document_access", new=access_check),
            patch.object(requirement_documents, "recover_document_ingestion", new=AsyncMock(return_value=True)) as recover,
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=self.document)),
            patch.object(requirement_documents, "store_raw_requirement_source", new=AsyncMock()) as store,
        ):
            result = await requirement_documents.upload_requirement_document_record(
                self.project_id,
                "txt",
                "requirements.txt",
                "text/plain",
                self.data,
                self.user,
                visibility="private",
                ai_enabled=True,
            )

        self.assertEqual(result.data["_id"], self.document["_id"])
        access_check.assert_awaited_once_with(self.document, self.user, "requirement_document.read")
        recover.assert_awaited_once_with(self.document, self.user)
        store.assert_not_awaited()

    async def test_duplicate_upload_joins_existing_parse_job(self):
        parsing_document = {**self.document, "status": "PARSING", "revision": 4}
        access_check = AsyncMock(return_value=parsing_document)
        with (
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(
                requirement_documents.requirement_document_repository,
                "find_by_hash",
                new=AsyncMock(return_value=parsing_document),
            ),
            patch.object(requirement_documents, "require_document_access", new=access_check),
            patch.object(requirement_documents, "store_raw_requirement_source", new=AsyncMock()) as store,
        ):
            result = await requirement_documents.upload_requirement_document_record(
                self.project_id,
                "txt",
                "requirements.txt",
                "text/plain",
                self.data,
                self.user,
                visibility="private",
                ai_enabled=True,
            )

        self.assertEqual(result.data["_id"], parsing_document["_id"])
        self.assertEqual(result.data["status"], "PARSING")
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(access_check.await_count, 2)
        access_check.assert_awaited_with(
            parsing_document, self.user, "requirement_document.read"
        )
        store.assert_not_awaited()

    async def test_duplicate_upload_returns_failed_document_for_explicit_retry(self):
        failed_document = {**self.document, "status": "PARSE_FAILED", "revision": 4}
        with (
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(
                requirement_documents.requirement_document_repository,
                "find_by_hash",
                new=AsyncMock(return_value=failed_document),
            ),
            patch.object(
                requirement_documents,
                "require_document_access",
                new=AsyncMock(return_value=failed_document),
            ),
            patch.object(requirement_documents, "store_raw_requirement_source", new=AsyncMock()) as store,
        ):
            result = await requirement_documents.upload_requirement_document_record(
                self.project_id,
                "txt",
                "requirements.txt",
                "text/plain",
                self.data,
                self.user,
                visibility="private",
                ai_enabled=True,
            )

        self.assertEqual(result.data["_id"], failed_document["_id"])
        self.assertEqual(result.data["status"], "PARSE_FAILED")
        store.assert_not_awaited()

    async def test_duplicate_upload_does_not_enqueue_when_ai_or_index_is_not_ready(self):
        document = {**self.document, "ai_enabled": False, "index_status": "NOT_REQUESTED"}
        with (
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(requirement_documents.requirement_document_repository, "find_by_hash", new=AsyncMock(return_value=document)),
            patch.object(requirement_documents, "require_document_access", new=AsyncMock(return_value=document)),
            patch.object(requirement_documents, "recover_document_ingestion", new=AsyncMock(return_value=True)),
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=document)),
            patch.object(requirement_documents, "queue_document_ingestion", new=AsyncMock()) as queue,
        ):
            result = await requirement_documents.upload_requirement_document_record(
                self.project_id,
                "txt",
                "requirements.txt",
                "text/plain",
                self.data,
                self.user,
                visibility="private",
                ai_enabled=False,
            )

        self.assertEqual(result.data["_id"], document["_id"])
        queue.assert_not_awaited()

    async def test_unclaimed_source_cleanup_preserves_object_referenced_by_document(self):
        source = {"object_key": "system/qa/project/yeu-cau/doc/source.txt"}
        persisted = {
            "_id": "doc",
            "raw_source": {"object_key": source["object_key"]},
        }
        with (
            patch.object(
                requirement_documents.requirement_document_repository,
                "find",
                new=AsyncMock(return_value=persisted),
            ),
            patch.object(
                requirement_documents.storage_client,
                "delete_requirement_source",
                new=AsyncMock(),
            ) as delete_source,
        ):
            await requirement_documents.remove_unclaimed_raw_requirement_source(
                "project", "doc", source
            )

        delete_source.assert_not_awaited()

    async def test_unclaimed_source_cleanup_deletes_after_confirming_no_document(self):
        source = {"object_key": "system/qa/project/yeu-cau/doc/source.txt"}
        with (
            patch.object(
                requirement_documents.requirement_document_repository,
                "find",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                requirement_documents.storage_client,
                "delete_requirement_source",
                new=AsyncMock(),
            ) as delete_source,
        ):
            await requirement_documents.remove_unclaimed_raw_requirement_source(
                "project", "doc", source
            )

        delete_source.assert_awaited_once_with(
            "project", "doc", source["object_key"]
        )

    async def test_unclaimed_source_cleanup_keeps_object_when_claim_check_fails(self):
        source = {"object_key": "system/qa/project/yeu-cau/doc/source.txt"}
        with (
            patch.object(
                requirement_documents.requirement_document_repository,
                "find",
                new=AsyncMock(side_effect=RuntimeError("Mongo unavailable")),
            ),
            patch.object(
                requirement_documents.storage_client,
                "delete_requirement_source",
                new=AsyncMock(),
            ) as delete_source,
        ):
            await requirement_documents.remove_unclaimed_raw_requirement_source(
                "project", "doc", source
            )

        delete_source.assert_not_awaited()

    async def test_upload_insert_failure_cleans_only_unclaimed_object(self):
        patches = self.common_patches()
        with ExitStack() as stack:
            mocks = [stack.enter_context(item) for item in patches]
            mocks[5].side_effect = RuntimeError("Mongo insert response lost")
            mocks[7].return_value = None
            delete_source = stack.enter_context(
                patch.object(
                    requirement_documents.storage_client,
                    "delete_requirement_source",
                    new=AsyncMock(),
                )
            )
            with self.assertRaisesRegex(RuntimeError, "Mongo insert response lost"):
                await requirement_documents.upload_requirement_document_record(
                    self.project_id,
                    "txt",
                    "requirements.txt",
                    "text/plain",
                    self.data,
                    self.user,
                    visibility="private",
                    ai_enabled=False,
                )

        delete_source.assert_awaited_once_with(
            self.project_id,
            mocks[2].await_args.args[1],
            self.document["raw_source"]["object_key"],
        )

    async def test_duplicate_upload_with_different_visibility_is_rejected(self):
        from fastapi import HTTPException

        with (
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(
                requirement_documents.requirement_document_repository,
                "find_by_hash",
                new=AsyncMock(return_value=self.document),
            ),
            patch.object(requirement_documents, "store_raw_requirement_source", new=AsyncMock()) as store,
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.upload_requirement_document_record(
                    self.project_id,
                    "txt",
                    "requirements.txt",
                    "text/plain",
                    self.data,
                    self.user,
                    visibility="project",
                    ai_enabled=True,
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "DUPLICATE_SOURCE_SETTINGS_CONFLICT")
        store.assert_not_awaited()

    async def test_project_visible_duplicate_from_another_member_is_reused(self):
        shared_document = {
            **self.document,
            "created_by": "another-project-member",
            "visibility": "project",
            "format": "txt",
            "source_type": "REFERENCE",
            "ai_enabled": True,
        }
        duplicate_lookup = AsyncMock(return_value=shared_document)
        access_check = AsyncMock(return_value=shared_document)
        with (
            patch.object(requirement_documents, "get_project", new=AsyncMock()),
            patch.object(
                requirement_documents,
                "validate_document_recipients",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                requirement_documents.requirement_document_repository,
                "find_by_hash",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                requirement_documents.requirement_document_repository,
                "find_reusable_duplicate",
                new=duplicate_lookup,
            ),
            patch.object(requirement_documents, "require_document_access", new=access_check),
            patch.object(requirement_documents, "recover_document_ingestion", new=AsyncMock(return_value=True)),
            patch.object(requirement_documents.requirement_document_repository, "find", new=AsyncMock(return_value=shared_document)),
            patch.object(
                requirement_documents,
                "store_raw_requirement_source",
                new=AsyncMock(),
            ) as store,
        ):
            result = await requirement_documents.upload_requirement_document_record(
                self.project_id,
                "txt",
                "requirements.txt",
                "text/plain",
                self.data,
                self.user,
                visibility="project",
                ai_enabled=True,
            )

        self.assertEqual(result.data["_id"], shared_document["_id"])
        duplicate_lookup.assert_awaited_once_with(
            self.project_id,
            hashlib.sha256(self.data).hexdigest(),
            "txt",
            "project",
            [],
            True,
            "REFERENCE",
            self.user.id,
            None,
        )
        access_check.assert_awaited_once_with(
            shared_document, self.user, "requirement_document.read"
        )
        store.assert_not_awaited()

    async def test_new_upload_starts_source_lineage_at_version_one(self):
        patches = self.common_patches()
        with ExitStack() as stack:
            mocks = [stack.enter_context(item) for item in patches]
            await requirement_documents.upload_requirement_document_record(
                self.project_id,
                "txt",
                "requirements.txt",
                "text/plain",
                self.data,
                self.user,
                visibility="private",
                ai_enabled=True,
            )

        inserted = mocks[5].await_args.args[0]
        self.assertEqual(inserted["source_series_id"], inserted["_id"])
        self.assertEqual(inserted["source_version_sequence"], 1)
        self.assertEqual(inserted["source_version"], "1")
        self.assertIsNone(inserted["previous_source_version_id"])

    async def test_successor_increments_sequence_and_preserves_parent(self):
        from fastapi import HTTPException

        parent = {
            **self.document,
            "content_hash": "old-hash",
            "format": "txt",
            "visibility": "private",
            "shared_with": [],
            "ai_enabled": False,
            "source_type": "REFERENCE",
            "source_series_id": "source-series",
            "source_version_sequence": 4,
        }
        latest = AsyncMock(return_value=parent)
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=parent)) as parent_lookup,
            patch.object(requirement_documents, "require_document_owner", new=AsyncMock()),
            patch.object(requirement_documents, "ensure_duplicate_settings_match"),
            patch.object(requirement_documents.requirement_document_repository, "latest_in_source_series", new=latest),
        ):
            lineage = await requirement_documents.resolve_source_successor(
                self.project_id,
                parent["_id"],
                self.user,
                content_hash="new-hash",
                format="txt",
                visibility="private",
                shared_with=[],
                ai_enabled=False,
                source_type="REFERENCE",
            )

        self.assertEqual(lineage["source_series_id"], "source-series")
        self.assertEqual(lineage["source_version_sequence"], 5)
        self.assertEqual(lineage["source_version"], "5")
        self.assertEqual(lineage["previous_source_version_id"], parent["_id"])
        latest.assert_awaited_once_with(self.project_id, "source-series")
        parent_lookup.assert_awaited_once_with(
            parent["_id"], self.user, "requirement_document.read"
        )

    async def test_stale_parent_is_rejected_instead_of_branching_lineage(self):
        from fastapi import HTTPException

        parent = {
            **self.document,
            "content_hash": "old-hash",
            "format": "txt",
            "visibility": "private",
            "shared_with": [],
            "ai_enabled": False,
            "source_type": "REFERENCE",
            "source_series_id": "source-series",
            "source_version_sequence": 1,
        }
        latest = {**parent, "_id": "newer-source"}
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=parent)),
            patch.object(requirement_documents, "require_document_owner", new=AsyncMock()),
            patch.object(requirement_documents, "ensure_duplicate_settings_match"),
            patch.object(requirement_documents.requirement_document_repository, "latest_in_source_series", new=AsyncMock(return_value=latest)),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.resolve_source_successor(
                    self.project_id,
                    parent["_id"],
                    self.user,
                    content_hash="new-hash",
                    format="txt",
                    visibility="private",
                    shared_with=[],
                    ai_enabled=False,
                    source_type="REFERENCE",
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "SOURCE_VERSION_PARENT_STALE")
        self.assertEqual(raised.exception.detail["latest_document_id"], "newer-source")

    async def test_identical_source_is_not_added_as_a_new_version(self):
        from fastapi import HTTPException

        parent = {
            **self.document,
            "content_hash": "same-hash",
            "format": "txt",
            "visibility": "private",
            "shared_with": [],
            "ai_enabled": False,
            "source_type": "REFERENCE",
        }
        with (
            patch.object(requirement_documents, "get_requirement_document_record", new=AsyncMock(return_value=parent)),
            patch.object(requirement_documents, "require_document_owner", new=AsyncMock()),
            patch.object(requirement_documents, "ensure_duplicate_settings_match"),
            patch.object(requirement_documents.requirement_document_repository, "latest_in_source_series", new=AsyncMock(return_value=parent)),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.resolve_source_successor(
                    self.project_id,
                    parent["_id"],
                    self.user,
                    content_hash=parent["content_hash"],
                    format="txt",
                    visibility="private",
                    shared_with=[],
                    ai_enabled=False,
                    source_type="REFERENCE",
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "SOURCE_VERSION_CONTENT_UNCHANGED")

    async def test_linked_source_version_cannot_be_renumbered_out_of_lineage(self):
        from fastapi import HTTPException

        document = {
            **self.document,
            "source_series_id": "source-series",
            "source_version_sequence": 3,
            "source_version": "3",
        }
        payload = SimpleNamespace(
            model_dump=Mock(return_value={"expected_revision": 2, "source_version": "7"})
        )
        with patch.object(
            requirement_documents,
            "get_requirement_document_record",
            new=AsyncMock(return_value=document),
        ):
            with self.assertRaises(HTTPException) as raised:
                await requirement_documents.update_requirement_document_record(
                    document["_id"], payload, self.user
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"], "SOURCE_VERSION_IS_LINEAGE_MANAGED"
        )


if __name__ == "__main__":
    unittest.main()

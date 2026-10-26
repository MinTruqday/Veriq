import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from src.clients.knowledge import KnowledgeClient
from src.services.document.internal import (
    INDEX_SOURCE_SNAPSHOT_FIELDS,
    exchange_internal_document,
    indexing_status_from_report,
)
from src.services.document.crud import DocumentCrudService
from src.services.document_ingestion_dispatcher import DocumentIngestionDispatcher
from src.schemas.document import DocumentCreate
from src.repositories.document_ingestion_outbox import document_ingestion_outbox


class DocumentIndexingStatusTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def source_snapshot():
        return {field: None for field in INDEX_SOURCE_SNAPSHOT_FIELDS}

    async def test_document_dispatch_uses_the_ai_internal_webhook_route(self):
        response = MagicMock()
        response.json.return_value = {"status": "accepted"}
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.post = AsyncMock(return_value=response)

        with (
            patch("src.clients.knowledge.httpx.AsyncClient", return_value=client),
            patch("src.clients.knowledge.settings.AI_URL", "http://ai.internal"),
            patch("src.clients.knowledge.settings.SECRET_KEY", "internal-secret"),
        ):
            result = await KnowledgeClient().index_document(
                "document-1", "user-1", event_id="event-1"
            )

        client.post.assert_awaited_once_with(
            "http://ai.internal/su-kien/moc-goi/tai-lieu-dang-tai",
            params={"document_id": "document-1", "user_id": "user-1", "event_id": "event-1"},
            headers={"X-Internal-Token": "internal-secret"},
        )
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(result, {"status": "accepted"})

    def test_clean_index_report_is_complete(self):
        self.assertEqual(
            indexing_status_from_report(
                {"failed_chunks": [], "quarantined_chunks": [], "unprocessed_blocks": []}
            ),
            "indexed",
        )

    def test_any_unprocessed_source_material_marks_index_degraded(self):
        for section in (
            "failed_chunks",
            "quarantined_chunks",
            "unprocessed_blocks",
            "index_cleanup_pending",
        ):
            with self.subTest(section=section):
                self.assertEqual(indexing_status_from_report({section: [{"id": "source-1"}]}), "degraded")

    def test_ocr_accuracy_warning_does_not_mislabel_extracted_text_as_unprocessed(self):
        self.assertEqual(
            indexing_status_from_report(
                {
                    "failed_chunks": [],
                    "quarantined_chunks": [],
                    "unprocessed_blocks": [],
                    "extraction_warnings": [
                        {
                            "type": "ocr_text",
                            "reason_code": "OCR_TEXT_REQUIRES_ACCURACY_VALIDATION",
                        }
                    ],
                }
            ),
            "indexed",
        )

    async def test_partial_index_persists_degraded_state_and_keeps_searchable_chunks(self):
        report = {
            "failed_chunks": [],
            "quarantined_chunks": [],
            "unprocessed_blocks": [
                {"block_id": "#/pages/12/pictures/0", "type": "picture"},
            ],
            "extraction_warnings": [
                {
                    "block_id": "#/pages/3/text",
                    "type": "ocr_text",
                    "page_no": 3,
                    "ocr_page_confidence": 0.72,
                    "reason_code": "OCR_TEXT_REQUIRES_ACCURACY_VALIDATION",
                },
            ],
        }
        update_result = SimpleNamespace(matched_count=1)
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(return_value=update_result),
        ) as update:
            result = await exchange_internal_document(
                {
                    "action": "update_index",
                    "document_id": "document-1",
                    "indexing_attempt_id": "attempt-1",
                    "indexed_chunks": 14,
                    "index_report": report,
                    "source_snapshot": self.source_snapshot(),
                }
            )

        saved = update.await_args.args[1]["$set"]
        self.assertEqual(
            update.await_args.args[0]["indexing_attempt_id"], "attempt-1"
        )
        self.assertEqual(result["data"], {"updated": True, "indexing_status": "degraded"})
        self.assertEqual(saved["indexing_status"], "degraded")
        self.assertTrue(saved["is_indexed"])
        self.assertEqual(saved["index_report"], report)

    async def test_fully_indexed_report_persists_indexed_state(self):
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
        ) as update:
            result = await exchange_internal_document(
                {
                    "action": "update_index",
                    "document_id": "document-1",
                    "indexing_attempt_id": "attempt-1",
                    "indexed_chunks": 14,
                    "index_report": {
                        "failed_chunks": [],
                        "quarantined_chunks": [],
                        "unprocessed_blocks": [],
                    },
                    "source_snapshot": self.source_snapshot(),
                }
            )

        self.assertEqual(result["data"]["indexing_status"], "indexed")
        self.assertEqual(
            update.await_args.args[0]["indexing_attempt_id"], "attempt-1"
        )
        self.assertEqual(update.await_args.args[1]["$set"]["indexing_status"], "indexed")

    async def test_index_publication_is_fenced_when_ai_access_was_revoked(self):
        snapshot = self.source_snapshot()
        snapshot.update({"visibility": "private", "shared_with": ["user-2"]})
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(return_value=SimpleNamespace(matched_count=0)),
        ) as update:
            result = await exchange_internal_document(
                {
                    "action": "update_index",
                    "document_id": "document-1",
                    "indexing_attempt_id": "attempt-1",
                    "indexed_chunks": 14,
                    "index_report": {},
                    "source_snapshot": snapshot,
                }
            )

        query = update.await_args.args[0]
        self.assertFalse(result["data"]["updated"])
        self.assertEqual(query["ai_enabled"], {"$ne": False})
        self.assertEqual(query["index_status"], {"$ne": "REVOKE_PENDING"})
        self.assertEqual(query["indexing_attempt_id"], "attempt-1")
        self.assertEqual(query["visibility"], "private")
        self.assertEqual(query["shared_with"], ["user-2"])

    async def test_index_publication_rejects_missing_source_snapshot(self):
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(),
        ) as update:
            with self.assertRaises(HTTPException) as raised:
                await exchange_internal_document(
                    {
                        "action": "update_index",
                        "document_id": "document-1",
                        "indexing_attempt_id": "attempt-1",
                        "indexing_lease_token": "lease-1",
                        "index_generation": "a" * 64,
                    }
                )

        self.assertEqual(raised.exception.status_code, 422)
        update.assert_not_awaited()

    async def test_stale_event_cannot_start_indexing_after_ai_access_was_revoked(self):
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(return_value=SimpleNamespace(matched_count=0)),
        ) as update:
            result = await exchange_internal_document(
                {
                    "action": "mark_indexing",
                    "document_id": "document-1",
                    "indexing_attempt_id": "stale-attempt",
                }
            )

        query = update.await_args.args[0]
        self.assertFalse(result["data"]["updated"])
        self.assertEqual(query["ai_enabled"], {"$ne": False})
        self.assertEqual(query["index_status"], {"$ne": "REVOKE_PENDING"})

    async def test_revoked_source_cannot_complete_a_stale_indexing_attempt(self):
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(return_value=SimpleNamespace(matched_count=0)),
        ) as update:
            result = await exchange_internal_document(
                {
                    "action": "complete_indexing",
                    "document_id": "document-1",
                    "indexing_attempt_id": "stale-attempt",
                }
            )

        query = update.await_args.args[0]
        self.assertFalse(result["data"]["updated"])
        self.assertEqual(query["ai_enabled"], {"$ne": False})
        self.assertEqual(query["index_status"], {"$ne": "REVOKE_PENDING"})
        self.assertEqual(query["indexing_attempt_id"], "stale-attempt")

    async def test_stale_outbox_dispatch_cannot_claim_a_newer_document_revision(self):
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(return_value=SimpleNamespace(matched_count=0)),
        ) as update:
            result = await exchange_internal_document(
                {
                    "action": "mark_indexing",
                    "document_id": "document-1",
                    "indexing_attempt_id": "attempt-old",
                    "dispatch_event_id": "dispatch-old",
                }
            )

        query = update.await_args.args[0]
        self.assertFalse(result["data"]["updated"])
        self.assertEqual(query["index_dispatch_event_id"], "dispatch-old")

    async def test_mark_indexing_claims_the_document_with_attempt_id(self):
        update_result = SimpleNamespace(matched_count=1)
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(return_value=update_result),
        ) as update:
            result = await exchange_internal_document(
                {
                    "action": "mark_indexing",
                    "document_id": "document-1",
                    "indexing_attempt_id": "attempt-2",
                }
            )

        self.assertEqual(result["data"], {"updated": True})
        self.assertEqual(
            update.await_args.args[1]["$set"]["indexing_attempt_id"], "attempt-2"
        )
        self.assertEqual(update.await_args.args[0]["_id"], "document-1")

    async def test_mark_indexing_rejects_a_missing_attempt_id(self):
        with self.assertRaises(HTTPException) as raised:
            await exchange_internal_document(
                {"action": "mark_indexing", "document_id": "document-1"}
            )
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "Thiếu mã lượt lập chỉ mục")

    async def test_index_progress_is_validated_and_fenced_to_current_attempt(self):
        with patch(
            "src.services.document.internal.DocumentRepository.update_one",
            new=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
        ) as update:
            result = await exchange_internal_document(
                {
                    "action": "update_indexing_progress",
                    "document_id": "document-1",
                    "indexing_attempt_id": "attempt-2",
                    "phase": "parsing",
                    "processed_pages": 6,
                    "total_pages": 12,
                    "unprocessed_pages": 1,
                }
            )

        self.assertEqual(result["data"], {"updated": True})
        query, update_document = update.await_args.args
        self.assertEqual(query["indexing_attempt_id"], "attempt-2")
        self.assertEqual(query["indexing_status"], "indexing")
        self.assertEqual(
            update_document["$set"]["indexing_progress"],
            {
                "indexing_attempt_id": "attempt-2",
                "phase": "parsing",
                "processed_pages": 6,
                "total_pages": 12,
                "unprocessed_pages": 1,
            },
        )

    async def test_index_progress_rejects_out_of_range_page_counts(self):
        with self.assertRaises(HTTPException) as raised:
            await exchange_internal_document(
                {
                    "action": "update_indexing_progress",
                    "document_id": "document-1",
                    "indexing_attempt_id": "attempt-2",
                    "phase": "parsing",
                    "processed_pages": 13,
                    "total_pages": 12,
                    "unprocessed_pages": 0,
                }
            )
        self.assertEqual(raised.exception.status_code, 422)

    async def test_create_document_stays_reconcilable_when_outbox_insert_fails(self):
        user = SimpleNamespace(id="user-1", full_name="Test User")
        document = DocumentCreate(title="Source document", file_url="private/source.pdf")
        with (
            patch(
                "src.services.document.crud.DocumentRepository.find_one",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.services.document.crud.DocumentRepository.insert_one",
                new=AsyncMock(),
            ) as insert,
            patch(
                "src.services.document.crud.document_ingestion_outbox.enqueue",
                new=AsyncMock(side_effect=RuntimeError("AI queue unavailable")),
            ),
        ):
            result = await DocumentCrudService.create_document(document, user)

        self.assertEqual(result["indexing_status"], "queued")
        inserted = insert.await_args.args[0]
        self.assertEqual(inserted["indexing_status"], "queued")
        self.assertFalse(inserted["is_indexed"])

    async def test_retrying_degraded_replacement_retains_previous_version_for_cleanup(self):
        from types import SimpleNamespace

        document = {
            "_id": "document-new",
            "creator_id": "user-1",
            "file_url": "private/source-v2.pdf",
            "previous_version_id": "document-old",
        }
        user = SimpleNamespace(id="user-1")
        with (
            patch(
                "src.services.document.crud.DocumentRepository.find_one",
                new=AsyncMock(side_effect=[document, document]),
            ),
            patch(
                "src.services.document.crud.DocumentRepository.update_one",
                new=AsyncMock(),
            ),
            patch(
                "src.services.document.crud.document_ingestion_outbox.enqueue",
                new=AsyncMock(),
            ) as enqueue,
            patch(
                "src.services.document.crud.serialize_document",
                return_value=document,
            ),
        ):
            await DocumentCrudService.retry_document_indexing("document-new", user)

        enqueue.assert_awaited_once_with(
            document,
            user_id="user-1",
            superseded_document_id="document-old",
            force_new=True,
        )

    async def test_outbox_enqueue_is_idempotent_for_the_same_source_revision(self):
        outbox_collection = SimpleNamespace(update_one=AsyncMock())
        documents_collection = SimpleNamespace(update_one=AsyncMock())
        content_database = MagicMock()
        content_database.__getitem__.side_effect = lambda name: {
            "document_ingestion_outbox": outbox_collection,
            "documents": documents_collection,
        }[name]
        mongo_client = MagicMock()
        mongo_client.__getitem__.return_value = content_database
        source = {
            "_id": "document-1",
            "source_revision": 3,
            "content_hash": "sha256:source",
            "file_url": "private/source-v3.pdf",
        }
        with patch(
            "src.repositories.document_ingestion_outbox.database.mongodb",
            mongo_client,
        ):
            first_event = await document_ingestion_outbox.enqueue(source, "user-1")
            second_event = await document_ingestion_outbox.enqueue(source, "user-1")

        self.assertEqual(first_event, second_event)
        self.assertEqual(outbox_collection.update_one.await_count, 2)
        outbox_filter, outbox_update = outbox_collection.update_one.await_args.args
        self.assertEqual(outbox_filter, {"_id": first_event})
        self.assertEqual(outbox_update["$setOnInsert"]["document_id"], "document-1")
        self.assertEqual(outbox_update["$setOnInsert"]["status"], "pending")
        document_update = documents_collection.update_one.await_args.args[1]["$set"]
        self.assertEqual(document_update["index_dispatch_event_id"], first_event)
        self.assertEqual(document_update["indexing_status"], "queued")

    async def test_reconciliation_uses_a_fresh_event_when_dispatch_pointer_is_missing(self):
        document = {
            "_id": "document-1",
            "creator_id": "user-1",
            "file_url": "private/source.pdf",
            "source_revision": 3,
            "content_hash": "sha256:source",
        }
        outbox = AsyncMock()
        outbox.list_documents_requiring_dispatch.return_value = [document]
        outbox.enqueue.return_value = "new-event"
        documents = SimpleNamespace(update_one=AsyncMock())
        content_database = MagicMock()
        content_database.__getitem__.return_value = documents
        mongo_client = MagicMock()
        mongo_client.__getitem__.return_value = content_database

        with (
            patch(
                "src.services.document_ingestion_dispatcher.document_ingestion_outbox",
                outbox,
            ),
            patch("src.services.document_ingestion_dispatcher.database.mongodb", mongo_client),
        ):
            await DocumentIngestionDispatcher()._reconcile_unqueued_documents()

        outbox.enqueue.assert_awaited_once_with(
            document,
            user_id="user-1",
            superseded_document_id="",
            force_new=True,
        )
        documents.update_one.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

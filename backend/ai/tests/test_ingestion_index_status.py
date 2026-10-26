import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.api.indexing import ingest_document
from src.schemas.ingestion import IngestRequest, IngestResponse
from src.services.ingestion import (
    IngestionPipelineService,
    SOURCE_SNAPSHOT_FIELDS,
    embed_and_index_chunks,
    index_document,
    remove_document,
    publish_index_generation,
    select_summary_chunks,
    validated_indexing_status,
)


class IngestionIndexStatusTests(unittest.TestCase):
    def test_long_document_summary_samples_chunks_across_the_document(self):
        chunks = [
            {
                "id": f"chunk-{index}",
                "text": f"Section {index}: " + ("x" * 990),
                "metadata": {"chunk_id": f"chunk-{index}", "page_numbers": [index + 1]},
            }
            for index in range(30)
        ]

        summary_input, selected = select_summary_chunks(chunks, 5000)

        self.assertLessEqual(len(summary_input), 5000)
        self.assertEqual(selected[0]["id"], "chunk-0")
        self.assertEqual(selected[-1]["id"], "chunk-29")
        self.assertGreater(len(selected), 2)
        self.assertNotEqual(
            [chunk["id"] for chunk in selected],
            [chunk["id"] for chunk in chunks[: len(selected)]],
        )

    def test_short_document_summary_uses_all_source_chunks(self):
        chunks = [
            {"id": "chunk-1", "text": "First source block."},
            {"id": "chunk-2", "text": "Last source block."},
        ]

        summary_input, selected = select_summary_chunks(chunks, 2000)

        self.assertEqual(len(selected), 2)
        self.assertIn("First source block.", summary_input)
        self.assertIn("Last source block.", summary_input)

    def test_summary_sample_rejects_invalid_limit(self):
        with self.assertRaisesRegex(ValueError, "document_summary_input_limit_invalid"):
            select_summary_chunks([], True)

    def test_response_keeps_unprocessed_parser_blocks(self):
        blocks = [{"block_id": "#/pages/3/table/2", "type": "table", "page_no": 3}]
        response = IngestResponse(
            document_id="doc-1",
            status="degraded",
            chunks_count=4,
            unprocessed_blocks=blocks,
            index_cleanup_pending=["qdrant"],
        )
        self.assertEqual(response.unprocessed_blocks, blocks)
        self.assertEqual(response.index_cleanup_pending, ["qdrant"])

    def test_ingest_api_returns_partial_result_and_non_success_message(self):
        blocks = [{"block_id": "#/pages/3/table/2", "type": "table", "page_no": 3}]
        request = IngestRequest(
            document_id="doc-1",
            requester_id="user-1",
        )
        result = {
            "document_id": "doc-1",
            "status": "degraded",
            "chunks_count": 4,
            "unprocessed_blocks": blocks,
        }

        async def invoke():
            with patch("src.api.indexing.index_document_data", new=AsyncMock(return_value=result)):
                return await ingest_document(request, user=None)

        response = asyncio.run(invoke())
        self.assertEqual(response.data.status, "degraded")
        self.assertEqual(response.data.unprocessed_blocks, blocks)
        self.assertIn("còn phần xử lý", response.message)


class DocumentRemovalReliabilityTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def source_document(attempt_id="", lease_token=""):
        return {
            "file_url": "private/source.pdf",
            "title": "source",
            "revision": 1,
            "owner_id": "user-1",
            "creator_id": "user-1",
            "visibility": "private",
            "indexing_attempt_id": attempt_id,
            "indexing_lease_token": lease_token,
            "indexing_lease_until": (
                datetime.now(timezone.utc) + timedelta(minutes=5)
            ).isoformat(),
            "index_status": "indexing",
        }

    async def test_superseded_outbox_dispatch_does_not_claim_or_parse_current_source(self):
        with (
            patch(
                "src.services.ingestion.ContentClient.authorize_document",
                new=AsyncMock(return_value={"file_url": "private/source.pdf"}),
            ),
            patch(
                "src.services.ingestion.ContentClient.mark_indexing",
                new=AsyncMock(return_value={"updated": False, "status": "superseded"}),
            ) as mark_indexing,
            patch(
                "src.services.ingestion.ContentClient.get",
                new=AsyncMock(
                    return_value={"index_dispatch_event_id": "dispatch-new"}
                ),
            ) as get_document,
            patch(
                "src.services.ingestion.ContentClient.mark_index_failed",
                new=AsyncMock(),
            ) as mark_failed,
            patch(
                "src.services.ingestion.ingestion_pipeline.ingest_document",
                new=AsyncMock(),
            ) as ingest,
        ):
            result = await index_document(
                "document-1", "user-1", False, "dispatch-old"
            )

        self.assertEqual(result["status"], "superseded")
        self.assertEqual(mark_indexing.await_args.args[0], "document-1")
        self.assertTrue(mark_indexing.await_args.args[1])
        self.assertEqual(mark_indexing.await_args.args[3], "dispatch-old")
        get_document.assert_not_awaited()
        mark_failed.assert_not_awaited()
        ingest.assert_not_awaited()

    async def test_index_batch_respects_the_smaller_embedding_and_store_limit(self):
        chunks = [
            {"id": f"chunk-{index}", "text": f"source {index}", "metadata": {}}
            for index in range(7)
        ]
        embed_calls = []
        upsert_calls = []

        async def embed_batch(texts):
            embed_calls.append(list(texts))
            return [[0.1] for _ in texts]

        async def upsert(**kwargs):
            upsert_calls.append(kwargs)

        with (
            patch("src.services.ingestion.embedder._batch_size", 2),
            patch("src.services.ingestion.vector_store.upsert_batch_size", 5),
            patch(
                "src.services.ingestion.embedder.embed_batch",
                new=AsyncMock(side_effect=embed_batch),
            ),
            patch("src.services.ingestion.vector_store.upsert", new=AsyncMock(side_effect=upsert)),
            patch("src.services.ingestion.vector_store.wait_upsert", new=AsyncMock()),
            patch("src.services.ingestion.bm25_store.stage_upsert", new=AsyncMock()) as bm25_stage,
            patch("src.services.ingestion.bm25_store.publish_staged", new=AsyncMock()) as bm25_publish,
        ):
            indexed, failed, indexed_ids = await embed_and_index_chunks(
                chunks, AsyncMock()
            )

        self.assertEqual([len(batch) for batch in embed_calls], [2, 2, 2, 1])
        self.assertEqual([len(call["ids"]) for call in upsert_calls], [2, 2, 2, 1])
        self.assertEqual(indexed, 7)
        self.assertEqual(failed, [])
        self.assertEqual(indexed_ids, [f"chunk-{index}" for index in range(7)])
        self.assertEqual(bm25_stage.await_count, 4)
        bm25_publish.assert_awaited_once()

    async def test_all_indexes_are_cleaned_even_when_one_store_fails(self):
        with (
            patch("src.services.ingestion.ContentClient.authorize_document", new=AsyncMock(return_value={})),
            patch("src.services.ingestion.vector_store.delete_by_document", new=AsyncMock(side_effect=RuntimeError("qdrant unavailable"))) as vector_delete,
            patch("src.services.ingestion.bm25_store.delete_by_document", new=AsyncMock()) as bm25_delete,
            patch("src.services.ingestion.ContentClient.mark_unindexed", new=AsyncMock()) as mark_unindexed,
        ):
            with self.assertRaisesRegex(RuntimeError, "document_index_removal_incomplete"):
                await remove_document("doc-1", "user-1", False)

        vector_delete.assert_awaited_once_with("doc-1")
        bm25_delete.assert_awaited_once_with("doc-1")
        mark_unindexed.assert_not_awaited()

    async def test_removal_does_not_report_success_when_content_status_update_missed(self):
        with (
            patch("src.services.ingestion.ContentClient.authorize_document", new=AsyncMock(return_value={})),
            patch("src.services.ingestion.vector_store.delete_by_document", new=AsyncMock()),
            patch("src.services.ingestion.bm25_store.delete_by_document", new=AsyncMock()),
            patch("src.services.ingestion.ContentClient.mark_unindexed", new=AsyncMock(return_value={"updated": False})),
        ):
            with self.assertRaisesRegex(RuntimeError, "document_unindex_status_update_failed"):
                await remove_document("doc-1", "user-1", False)

    def test_partial_index_status_is_propagated_as_degraded(self):
        self.assertEqual(
            validated_indexing_status({"updated": True, "indexing_status": "degraded"}),
            "degraded",
        )

    def test_clean_index_status_is_propagated_as_indexed(self):
        self.assertEqual(
            validated_indexing_status({"updated": True, "indexing_status": "indexed"}),
            "indexed",
        )

    def test_missing_document_update_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "document_index_status_update_failed"):
            validated_indexing_status({"updated": False, "indexing_status": "degraded"})

    def test_unrecognized_status_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "document_index_status_invalid"):
            validated_indexing_status({"updated": True, "indexing_status": "processing"})

    def test_index_generation_cleanup_is_reported_as_degraded(self):
        self.assertEqual(
            validated_indexing_status(
                {"updated": True, "indexing_status": "degraded"}
            ),
            "degraded",
        )

    def test_failed_second_store_write_rolls_back_only_new_generation(self):
        async def invoke():
            document = self.source_document()
            chunk = {
                "id": "chunk-new-generation",
                "text": "A source statement. " * 40,
                "metadata": {"chunk_id": "chunk-new-generation"},
            }
            with (
                patch("src.services.ingestion.ContentClient.authorize_document", new=AsyncMock(return_value=document)),
                patch("src.services.ingestion.document_parser.parse_document_checkpointed", new=AsyncMock(return_value={
                    "markdown": chunk["text"],
                    "structure": [],
                    "unprocessed_blocks": [],
                    "parser": "docling",
                    "parser_version": "1",
                    "source_sha256": "source-hash",
                })),
                patch("src.services.ingestion.chunker.chunk_document", new=AsyncMock(return_value=[chunk])),
                patch("src.services.ingestion.inspect_chunks", new=AsyncMock(return_value=[0])),
                patch("src.services.ingestion.summarize_document", new=AsyncMock(return_value="")),
                patch("src.services.ingestion.embedder._batch_size", 1),
                patch("src.services.ingestion.embedder.embed_batch", new=AsyncMock(return_value=[[0.1]])),
                patch("src.services.ingestion.vector_store.ids_by_document", new=AsyncMock(return_value=["chunk-old-generation"])),
                patch("src.services.ingestion.bm25_store.ids_by_document", new=AsyncMock(return_value=["chunk-old-generation"])),
                patch("src.services.ingestion.vector_store.upsert", new=AsyncMock()) as vector_upsert,
                patch("src.services.ingestion.vector_store.wait_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.stage_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.publish_staged", new=AsyncMock(side_effect=RuntimeError("BM25 unavailable"))),
                patch("src.services.ingestion.vector_store.delete_ids", new=AsyncMock()) as vector_delete,
                patch("src.services.ingestion.bm25_store.delete_ids", new=AsyncMock()) as bm25_delete,
                patch("src.services.ingestion.ContentClient.mark_indexed", new=AsyncMock()) as mark_indexed,
            ):
                with self.assertRaisesRegex(RuntimeError, "BM25 unavailable"):
                    await IngestionPipelineService().ingest_document("doc-1", "user-1")

            self.assertEqual(vector_upsert.await_args.kwargs["ids"], ["chunk-new-generation"])
            vector_delete.assert_awaited_once_with(["chunk-new-generation"])
            bm25_delete.assert_awaited_once_with(["chunk-new-generation"])
            mark_indexed.assert_not_awaited()

        asyncio.run(invoke())

    def test_cancelled_batched_indexing_rolls_back_partial_vector_generation(self):
        async def invoke():
            chunks = [
                {"id": f"chunk-{index}", "text": f"source {index}", "metadata": {}}
                for index in range(2)
            ]
            verify_source = AsyncMock()
            with (
                patch("src.services.ingestion.embedder._batch_size", 1),
                patch("src.services.ingestion.vector_store.upsert_batch_size", 1),
                patch(
                    "src.services.ingestion.embedder.embed_batch",
                    new=AsyncMock(side_effect=[[[0.1]], [[0.2]]]),
                ),
                patch(
                    "src.services.ingestion.vector_store.upsert",
                    new=AsyncMock(side_effect=[None, asyncio.CancelledError()]),
                ),
                patch("src.services.ingestion.vector_store.wait_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.stage_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.publish_staged", new=AsyncMock()),
                patch(
                    "src.services.ingestion.vector_store.delete_ids",
                    new=AsyncMock(),
                ) as vector_delete,
                patch(
                    "src.services.ingestion.bm25_store.delete_ids",
                    new=AsyncMock(),
                ) as bm25_delete,
            ):
                with self.assertRaises(asyncio.CancelledError):
                    await embed_and_index_chunks(chunks, verify_source)

            vector_delete.assert_awaited_once_with(["chunk-0", "chunk-1"])
            bm25_delete.assert_awaited_once_with(["chunk-0", "chunk-1"])
            self.assertEqual(verify_source.await_count, 2)

        asyncio.run(invoke())

    def test_stale_indexing_attempt_rolls_back_only_its_generation(self):
        async def invoke():
            attempt_id = "attempt-old"
            text = "A grounded source statement. " * 30
            chunk = {
                "id": "chunk-old-attempt",
                "text": text,
                "metadata": {"chunk_id": "chunk-old-attempt"},
            }
            with (
                patch(
                    "src.services.ingestion.ContentClient.authorize_document",
                    new=AsyncMock(
                        return_value=self.source_document(attempt_id=attempt_id)
                    ),
                ),
                patch(
                    "src.services.ingestion.document_parser.parse_document_checkpointed",
                    new=AsyncMock(return_value={
                        "markdown": text,
                        "structure": [],
                        "unprocessed_blocks": [],
                        "parser": "docling",
                        "parser_version": "1",
                        "source_sha256": "source-hash",
                    }),
                ),
                patch(
                    "src.services.ingestion.chunker.chunk_document",
                    new=AsyncMock(return_value=[chunk]),
                ),
                patch("src.services.ingestion.inspect_chunks", new=AsyncMock(return_value=[0])),
                patch("src.services.ingestion.summarize_document", new=AsyncMock(return_value="")),
                patch(
                    "src.services.ingestion.embedder._batch_size",
                    1,
                ),
                patch("src.services.ingestion.embedder.embed_batch", new=AsyncMock(return_value=[[0.1]])),
                patch("src.services.ingestion.vector_store.ids_by_document", new=AsyncMock(return_value=[])),
                patch("src.services.ingestion.bm25_store.ids_by_document", new=AsyncMock(return_value=[])),
                patch("src.services.ingestion.vector_store.upsert", new=AsyncMock()),
                patch("src.services.ingestion.vector_store.wait_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.stage_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.publish_staged", new=AsyncMock()),
                patch("src.services.ingestion.vector_store.delete_ids", new=AsyncMock()) as vector_delete,
                patch("src.services.ingestion.bm25_store.delete_ids", new=AsyncMock()) as bm25_delete,
                patch(
                    "src.services.ingestion.ContentClient.mark_indexed",
                    new=AsyncMock(return_value={"updated": False, "indexing_status": "indexed"}),
                ),
                patch(
                    "src.services.ingestion.ContentClient.get",
                    new=AsyncMock(return_value={"active_index_generation": "previous-generation"}),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "document_index_status_update_failed"):
                    await IngestionPipelineService().ingest_document(
                        "doc-1", "user-1", False, attempt_id
                    )

            vector_delete.assert_awaited_once_with(["chunk-old-attempt"])
            bm25_delete.assert_awaited_once_with(["chunk-old-attempt"])

        asyncio.run(invoke())

    def test_access_metadata_change_during_ingestion_prevents_index_publish(self):
        async def invoke():
            text = "A source statement. " * 30
            document = {
                **self.source_document(),
                "revision": 4,
                "owner_id": "user-1",
                "creator_id": "user-1",
                "visibility": "project",
                "shared_with": ["reader-1"],
                "ai_enabled": True,
                "artifact_metadata": {"project_id": "project-1"},
                "indexing_attempt_id": "attempt-1",
                "indexing_lease_token": "g" * 64,
                "indexing_lease_until": (
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ).isoformat(),
                "index_status": "indexing",
            }
            updated_document = {**document, "shared_with": []}
            chunk = {
                "id": "chunk-new-generation",
                "text": text,
                "metadata": {"chunk_id": "chunk-new-generation"},
            }
            with (
                patch(
                    "src.services.ingestion.ContentClient.authorize_document",
                    new=AsyncMock(side_effect=[document, updated_document]),
                ),
                patch(
                    "src.services.ingestion.document_parser.parse_document_checkpointed",
                    new=AsyncMock(return_value={
                        "markdown": text,
                        "structure": [],
                        "unprocessed_blocks": [],
                        "parser": "docling",
                        "parser_version": "1",
                        "source_sha256": "source-hash",
                    }),
                ),
                patch(
                    "src.services.ingestion.chunker.chunk_document",
                    new=AsyncMock(return_value=[chunk]),
                ),
                patch("src.services.ingestion.inspect_chunks", new=AsyncMock(return_value=[0])),
                patch("src.services.ingestion.summarize_document", new=AsyncMock(return_value="")),
                patch("src.services.ingestion.embedder._batch_size", 1),
                patch("src.services.ingestion.embedder.embed_batch", new=AsyncMock(return_value=[[0.1]])),
                patch("src.services.ingestion.vector_store.ids_by_document", new=AsyncMock(return_value=[])),
                patch("src.services.ingestion.bm25_store.ids_by_document", new=AsyncMock(return_value=[])),
                patch("src.services.ingestion.vector_store.upsert", new=AsyncMock()) as vector_upsert,
                patch("src.services.ingestion.vector_store.wait_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.stage_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.publish_staged", new=AsyncMock()),
                patch("src.services.ingestion.vector_store.delete_ids", new=AsyncMock()) as vector_delete,
                patch("src.services.ingestion.bm25_store.delete_ids", new=AsyncMock()) as bm25_delete,
                patch("src.services.ingestion.bm25_store.discard_staged", new=AsyncMock()),
                patch("src.services.ingestion.ContentClient.mark_indexed", new=AsyncMock()) as mark_indexed,
            ):
                with self.assertRaisesRegex(
                    PermissionError, "document_source_changed_during_ingestion"
                ):
                    await IngestionPipelineService().ingest_document(
                        "doc-1", "user-1", False, "attempt-1", "g" * 64
                    )

            vector_upsert.assert_not_awaited()
            mark_indexed.assert_not_awaited()
            vector_delete.assert_awaited_once_with(["chunk-new-generation"])
            bm25_delete.assert_awaited_once_with(["chunk-new-generation"])

        asyncio.run(invoke())

    async def test_publication_readback_preserves_generation_after_lost_response(self):
        with (
            patch(
                "src.services.ingestion.ContentClient.mark_indexed",
                new=AsyncMock(side_effect=TimeoutError("response lost")),
            ),
            patch(
                "src.services.ingestion.ContentClient.get",
                new=AsyncMock(
                    return_value={
                        "active_index_generation": "g" * 64,
                        "indexing_attempt_id": "attempt-1",
                        "indexing_lease_token": "lease-token",
                        "indexing_status": "indexed",
                        "indexed_chunks": 3,
                        "index_report": {},
                    }
                ),
            ),
        ):
            status = await publish_index_generation(
                "doc-1", 3, {}, "source", "parser", "attempt-1", "lease-token",
                "g" * 64, {field: None for field in SOURCE_SNAPSHOT_FIELDS},
            )

        self.assertEqual(status, "indexed")

    async def test_publication_readback_rejects_superseded_attempt_with_same_generation(self):
        with (
            patch(
                "src.services.ingestion.ContentClient.mark_indexed",
                new=AsyncMock(side_effect=TimeoutError("response lost")),
            ),
            patch(
                "src.services.ingestion.ContentClient.get",
                new=AsyncMock(
                    return_value={
                        "active_index_generation": "g" * 64,
                        "indexing_attempt_id": "newer-attempt",
                        "indexing_status": "indexing",
                        "indexed_chunks": 3,
                        "index_report": {},
                    }
                ),
            ),
        ):
            status = await publish_index_generation(
                "doc-1", 3, {}, "source", "parser", "attempt-1", "lease-token",
                "g" * 64, {field: None for field in SOURCE_SNAPSHOT_FIELDS},
            )

        self.assertEqual(status, "")

    def test_old_generation_cleanup_failure_keeps_new_index_and_marks_degraded(self):
        async def invoke():
            document = self.source_document()
            chunk = {
                "id": "chunk-new-generation",
                "text": "A source statement. " * 40,
                "metadata": {"chunk_id": "chunk-new-generation"},
            }
            mark_results = iter(("indexed", "degraded"))

            async def mark_indexed(*_args):
                return {"updated": True, "indexing_status": next(mark_results)}

            with (
                patch("src.services.ingestion.ContentClient.authorize_document", new=AsyncMock(return_value=document)),
                patch("src.services.ingestion.document_parser.parse_document_checkpointed", new=AsyncMock(return_value={
                    "markdown": chunk["text"],
                    "structure": [],
                    "unprocessed_blocks": [],
                    "parser": "docling",
                    "parser_version": "1",
                    "source_sha256": "source-hash",
                })),
                patch("src.services.ingestion.chunker.chunk_document", new=AsyncMock(return_value=[chunk])),
                patch("src.services.ingestion.inspect_chunks", new=AsyncMock(return_value=[0])),
                patch("src.services.ingestion.summarize_document", new=AsyncMock(return_value="")),
                patch("src.services.ingestion.embedder._batch_size", 1),
                patch("src.services.ingestion.embedder.embed_batch", new=AsyncMock(return_value=[[0.1]])),
                patch("src.services.ingestion.vector_store.ids_by_document", new=AsyncMock(return_value=["chunk-old-generation"])),
                patch("src.services.ingestion.bm25_store.ids_by_document", new=AsyncMock(return_value=["chunk-old-generation"])),
                patch("src.services.ingestion.vector_store.upsert", new=AsyncMock()),
                patch("src.services.ingestion.vector_store.wait_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.stage_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.publish_staged", new=AsyncMock()),
                patch("src.services.ingestion.vector_store.delete_ids", new=AsyncMock(side_effect=RuntimeError("Qdrant unavailable"))),
                patch("src.services.ingestion.bm25_store.delete_ids", new=AsyncMock()) as bm25_delete,
                patch("src.services.ingestion.ContentClient.mark_indexed", new=AsyncMock(side_effect=mark_indexed)) as mark,
            ):
                result = await IngestionPipelineService().ingest_document("doc-1", "user-1")

            self.assertEqual(result["status"], "degraded")
            self.assertEqual(
                mark.await_args_list[1].args[2]["index_cleanup_pending"], ["qdrant"]
            )
            bm25_delete.assert_awaited_once_with(["chunk-old-generation"])

        asyncio.run(invoke())

    def test_parser_diagnostics_survive_ingest_report(self):
        async def invoke():
            unprocessed = [{
                "block_id": None,
                "type": "document_structure",
                "reason_code": "STRUCTURE_EXTRACTION_FAILED",
                "locations": [],
            }]
            warnings = [{
                "block_id": None,
                "type": "ocr_text",
                "page_no": 3,
                "ocr_page_confidence": 0.72,
                "reason_code": "OCR_TEXT_REQUIRES_ACCURACY_VALIDATION",
                "locations": [],
            }]
            document = {
                "file_url": "private/source.pdf",
                "title": "source",
                "shared_with": ["reader-1"],
                "created_at": "2026-10-24T08:15:00Z",
                "updated_at": "2026-10-25T09:30:00+07:00",
            }
            parsed_chunk = {
                "id": "chunk-1",
                "text": "Source text that remains searchable.",
                "metadata": {"chunk_id": "chunk-1"},
            }

            with (
                patch("src.services.ingestion.ContentClient.authorize_document", new=AsyncMock(return_value=document)),
                patch("src.services.ingestion.document_parser.parse_document_checkpointed", new=AsyncMock(return_value={
                    "markdown": parsed_chunk["text"],
                    "structure": [],
                    "unprocessed_blocks": unprocessed,
                    "extraction_warnings": warnings,
                    "parser": "docling",
                    "parser_version": "2.142.1",
                    "ocr_enabled": True,
                    "source_sha256": "verified-source-hash",
                })),
                patch(
                    "src.services.ingestion.chunker.chunk_document",
                    new=AsyncMock(return_value=[parsed_chunk]),
                ) as chunker_mock,
                patch("src.services.ingestion.inspect_chunks", new=AsyncMock(return_value=[0])),
                patch(
                    "src.services.ingestion.embed_and_index_chunks",
                    new=AsyncMock(return_value=(1, [], ["chunk-1"])),
                ),
                patch("src.services.ingestion.vector_store.ids_by_document", new=AsyncMock(return_value=[])),
                patch("src.services.ingestion.bm25_store.ids_by_document", new=AsyncMock(return_value=[])),
                patch("src.services.ingestion.vector_store.upsert", new=AsyncMock()),
                patch("src.services.ingestion.vector_store.wait_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.stage_upsert", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.publish_staged", new=AsyncMock()),
                patch("src.services.ingestion.vector_store.delete_ids", new=AsyncMock()),
                patch("src.services.ingestion.bm25_store.delete_ids", new=AsyncMock()),
                patch("src.services.ingestion.ContentClient.mark_indexed", new=AsyncMock(return_value={
                    "updated": True,
                    "indexing_status": "degraded",
                })) as mark_indexed,
            ):
                result = await IngestionPipelineService().ingest_document(
                    "document-1", "requester-1", False
                )

            self.assertEqual(result["status"], "degraded")
            self.assertEqual(result["unprocessed_blocks"], unprocessed)
            self.assertEqual(result["extraction_warnings"], warnings)
            self.assertEqual(mark_indexed.await_args.args[2]["unprocessed_blocks"], unprocessed)
            self.assertEqual(mark_indexed.await_args.args[2]["extraction_warnings"], warnings)
            indexed_metadata = chunker_mock.await_args.args[1]
            self.assertEqual(indexed_metadata["source_hash"], "verified-source-hash")
            self.assertEqual(indexed_metadata["parser_name"], "docling")
            self.assertEqual(indexed_metadata["parser_version"], "2.142.1")
            self.assertTrue(indexed_metadata["ocr_enabled"])
            self.assertEqual(indexed_metadata["extraction_status"], "DEGRADED")
            self.assertEqual(indexed_metadata["unprocessed_block_count"], 1)
            self.assertEqual(indexed_metadata["shared_with"], ["reader-1"])
            self.assertEqual(
                indexed_metadata["source_created_at"], "2026-10-24T08:15:00+00:00"
            )
            self.assertEqual(
                indexed_metadata["source_updated_at"], "2026-10-25T02:30:00+00:00"
            )
            self.assertNotIn("file_url", indexed_metadata)
            self.assertEqual(len(indexed_metadata["index_generation"]), 64)
            self.assertTrue(indexed_metadata["indexed_at"])

        asyncio.run(invoke())


if __name__ == "__main__":
    unittest.main()

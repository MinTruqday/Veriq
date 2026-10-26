import unittest

from src.services.retrieval import RetrievalService


class RetrievalMetadataSafetyTests(unittest.TestCase):
    def test_fused_results_never_expose_object_storage_file_url(self):
        source = {
            "id": "chunk-1",
            "text": "Requirement source text",
            "metadata": {
                "document_id": "doc-1",
                "artifact_version_id": "doc-v1",
                "file_url": "https://object-store.invalid/private/signed-token",
            },
            "score": 0.9,
        }

        result = RetrievalService()._rrf_fuse([source], [])[0]

        self.assertEqual(result["metadata"]["document_id"], "doc-1")
        self.assertEqual(result["metadata"]["artifact_version_id"], "doc-v1")
        self.assertNotIn("file_url", result["metadata"])
        self.assertIn("file_url", source["metadata"])

    def test_citations_preserve_each_point_version_and_source_spans_without_acl_fields(self):
        results = [
            {
                "id": "point-v1-a",
                "metadata": {
                    "document_id": "doc-1",
                    "artifact_type": "requirement_version",
                    "artifact_id": "req-1",
                    "artifact_version_id": "req-v1",
                    "source_version": "1",
                    "chunk_id": "chunk-a",
                    "chunk_index": 0,
                    "page_numbers": [3],
                    "source_spans": [{"block_id": "block-a", "page_no": 3}],
                    "owner_id": "user-1",
                    "shared_with": ["user-2"],
                },
            },
            {
                "id": "point-v2-a",
                "metadata": {
                    "document_id": "doc-1",
                    "artifact_type": "requirement_version",
                    "artifact_id": "req-1",
                    "artifact_version_id": "req-v2",
                    "source_version": "2",
                    "chunk_id": "chunk-a",
                    "chunk_index": 0,
                    "page_numbers": [4],
                    "source_spans": [{"block_id": "block-b", "page_no": 4}],
                    "owner_id": "user-1",
                    "shared_with": ["user-2"],
                },
            },
        ]

        citations = RetrievalService().get_citations(results)

        self.assertEqual(len(citations), 2)
        self.assertEqual(citations[0]["artifact_version_id"], "req-v1")
        self.assertEqual(citations[0]["page_numbers"], [3])
        self.assertEqual(citations[0]["source_spans"][0]["block_id"], "block-a")
        self.assertEqual(citations[1]["artifact_version_id"], "req-v2")
        self.assertNotIn("owner_id", citations[0])
        self.assertNotIn("shared_with", citations[0])

    def test_citations_do_not_merge_project_artifacts_without_document_ids(self):
        citations = RetrievalService().get_citations(
            [
                {
                    "id": "point-requirement",
                    "metadata": {
                        "artifact_id": "req-1",
                        "artifact_version_id": "req-v1",
                        "chunk_id": "shared-chunk",
                    },
                },
                {
                    "id": "point-test-case",
                    "metadata": {
                        "artifact_id": "tc-1",
                        "artifact_version_id": "tc-v1",
                        "chunk_id": "shared-chunk",
                    },
                },
            ]
        )

        self.assertEqual([item["artifact_id"] for item in citations], ["req-1", "tc-1"])

    def test_sparse_legacy_payload_is_sanitized_when_first_seen(self):
        result = RetrievalService()._rrf_fuse(
            [],
            [
                {
                    "id": "legacy-chunk",
                    "text": "Legacy indexed content",
                    "metadata": {
                        "document_id": "legacy-doc",
                        "file_url": "s3://private-bucket/internal-key",
                    },
                    "bm25_score": 1.0,
                }
            ],
        )[0]

        self.assertEqual(result["metadata"]["document_id"], "legacy-doc")
        self.assertNotIn("file_url", result["metadata"])


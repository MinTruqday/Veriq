import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.knowledge.hybrid import hybrid_evidence


class HybridEvidenceProvenanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_database_tool_and_source_location_metadata_reach_agent_evidence(self):
        source_span = {
            "block_id": "#/pages/7/blocks/2",
            "source_start": 12,
            "source_end": 47,
            "offset_basis": "normalized_block",
            "locations": [{"page_no": 7, "bbox": {"x0": 1, "y0": 2, "x1": 3, "y1": 4}}],
        }
        database_result = {
            "items": [{
                "artifact_type": "requirement_document",
                "artifact_id": "document-1",
                "artifact_version_id": "document-version-1",
                "authority": "PROJECT_REFERENCE",
                "score": 0.8,
                "text": "Mật khẩu phải có ít nhất 12 ký tự.",
                "chunk_id": "chunk-7",
                "chunk_index": 4,
                "chunk_type": "docling_structure_semantic",
                "page_numbers": [7],
                "source_spans": [source_span],
                "source_hash": "source-hash",
                "retrieved_passages": [
                    {
                        "text": "Mật khẩu phải có ít nhất 12 ký tự.",
                        "score": 0.8,
                        "chunk_id": "chunk-7",
                        "chunk_index": 4,
                        "chunk_type": "docling_structure_semantic",
                        "page_numbers": [7],
                        "source_spans": [source_span],
                        "source_hash": "source-hash",
                    },
                    {
                        "text": "Sau 5 lần đăng nhập sai, tài khoản bị khóa.",
                        "score": 0.7,
                        "chunk_id": "chunk-12",
                        "chunk_index": 9,
                        "chunk_type": "docling_structure_semantic",
                        "page_numbers": [12],
                        "source_spans": [{"block_id": "#/pages/12/blocks/1"}],
                        "source_hash": "source-hash",
                    },
                ],
            }]
        }
        with (
            patch(
                "src.tools.knowledge_tools.retrieve_project_evidence",
                new=SimpleNamespace(
                    ainvoke=AsyncMock(return_value=json.dumps(database_result))
                ),
            ),
            patch("src.services.embedding.embedder.embed_query", new=AsyncMock(return_value=[0.1])),
            patch(
                "src.store.vector.vector_store.query",
                new=AsyncMock(
                    return_value=[
                        {
                            "id": "wrong-type-point",
                            "score": 0.99,
                            "text": "Do not attach this evidence to the document.",
                            "metadata": {
                                "artifact_type": "defect",
                                "artifact_id": "document-1",
                                "artifact_version_id": "document-version-1",
                            },
                        }
                    ]
                ),
            ),
            patch(
                "src.knowledge.graph.repository.graph_repository.search",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.knowledge.hybrid.project_artifact_generation_repository.filter_active",
                new=AsyncMock(side_effect=lambda matches: matches),
            ),
            patch(
                "src.memory.long_term.long_term_memory.list",
                new=AsyncMock(return_value=[]),
            ),
        ):
            evidence = await hybrid_evidence(
                "project-1", "password rule", "member-1", token="internal-token"
            )

        self.assertEqual(len(evidence.items), 2)
        item = next(item for item in evidence.items if item.chunk_id == "chunk-7")
        other_item = next(item for item in evidence.items if item.chunk_id == "chunk-12")
        self.assertEqual(item.chunk_index, 4)
        self.assertEqual(item.page_numbers, [7])
        self.assertEqual(item.source_spans, [source_span])
        self.assertEqual(item.source_hash, "source-hash")
        self.assertEqual(other_item.page_numbers, [12])
        self.assertEqual(other_item.text, "Sau 5 lần đăng nhập sai, tài khoản bị khóa.")
        self.assertNotIn("KNOWLEDGE_UNAVAILABLE", evidence.degraded_flags)

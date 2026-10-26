from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.modules.quality.services import analytics as analytics_module
from src.modules.quality.services.analytics import AnalyticsService
from src.schemas.contracts.utility import SearchInput


@pytest.mark.asyncio
async def test_hybrid_knowledge_result_keeps_best_chunk_and_source_location(monkeypatch):
    user = SimpleNamespace(id="member-a", is_system_admin=False)
    database_record = {
        "_id": "document-version-1",
        "project_id": "project-a",
        "created_by": "member-a",
        "filename": "requirements.pdf",
        "normalized_content": "Short database projection that is not the matched passage.",
        "status": "ACTIVE",
        "authority": "PROJECT_REFERENCE",
    }
    best_chunk = {
        "artifact_type": "requirement_document",
        "artifact_id": "document-1",
        "artifact_version_id": "document-version-1",
        "title": "Requirements",
        "authority": "SEMANTIC_INDEX",
        "score": 0.9,
        "text": "Mật khẩu phải có ít nhất 12 ký tự.",
        "chunk_id": "chunk-best",
        "chunk_index": 4,
        "chunk_type": "docling_structure_semantic",
        "page_numbers": [7],
        "source_spans": [{
            "block_id": "#/pages/7/blocks/2",
            "source_start": 12,
            "source_end": 47,
            "offset_basis": "normalized_block",
            "locations": [{"page_no": 7, "bbox": {"x0": 1, "y0": 2, "x1": 3, "y1": 4}}],
        }],
    }
    lower_chunk = {
        **best_chunk,
        "score": 0.4,
        "text": "A less relevant retrieved chunk.",
        "chunk_id": "chunk-lower",
        "chunk_index": 1,
        "page_numbers": [2],
        "source_spans": [{"block_id": "#/pages/2/blocks/1"}],
    }

    async def list_records(collection, query, _limit, _sort=None, projection=None):
        if collection != "requirement_documents":
            return []
        if projection == {"_id": 1}:
            return [{"_id": "document-version-1"}]
        return [database_record]

    monkeypatch.setattr(analytics_module, "get_project", AsyncMock(return_value={"settings": {}}))
    monkeypatch.setattr(
        analytics_module.analytics_repository,
        "list_records",
        list_records,
    )
    monkeypatch.setattr(
        analytics_module,
        "search_project_with_status",
        AsyncMock(return_value={
            "items": [lower_chunk, best_chunk],
            "degraded_mode": "NORMAL",
            "error_code": None,
        }),
    )

    results, _metadata = await AnalyticsService.search_knowledge(
        "project-a",
        SearchInput(query="Mật khẩu", artifact_types=["requirement_document"], limit=10),
        user,
    )

    assert len(results["items"]) == 1
    item = results["items"][0]
    assert item["text"] == best_chunk["text"]
    assert item["authority"] == "PROJECT_REFERENCE"
    assert item["retrieval_source"] == "hybrid_fusion"
    assert item["chunk_id"] == "chunk-best"
    assert item["chunk_index"] == 4
    assert item["page_numbers"] == [7]
    assert item["source_spans"] == best_chunk["source_spans"]
    assert [passage["chunk_id"] for passage in item["retrieved_passages"]] == [
        "chunk-best",
        "chunk-lower",
    ]


@pytest.mark.asyncio
async def test_dense_only_document_uses_current_database_authority(monkeypatch):
    user = SimpleNamespace(id="member-a", is_system_admin=False)
    current_record = {
        "_id": "document-version-1",
        "project_id": "project-a",
        "created_by": "member-a",
        "filename": "requirements.pdf",
        "normalized_content": "Text not matching the lexical query.",
        "status": "ACTIVE",
        "authority": "PROJECT_REFERENCE",
    }
    dense_item = {
        "artifact_type": "requirement_document",
        "artifact_id": "stale-document-id",
        "artifact_version_id": "document-version-1",
        "title": "Stale title from vector metadata",
        "authority": "STALE_VECTOR_AUTHORITY",
        "status": "ARCHIVED",
        "score": 0.9,
        "text": "A relevant passage found by dense retrieval.",
        "chunk_id": "chunk-1",
        "source_spans": [{"block_id": "#/pages/1/blocks/1"}],
    }

    async def list_records(collection, query, _limit, _sort=None, projection=None):
        if collection != "requirement_documents":
            return []
        if "_id" in query and "$in" in query["_id"]:
            if query.get("status") == {"$ne": "ARCHIVED"}:
                return [current_record]
            return []
        return []

    monkeypatch.setattr(analytics_module, "get_project", AsyncMock(return_value={"settings": {}}))
    monkeypatch.setattr(analytics_module.analytics_repository, "list_records", list_records)
    monkeypatch.setattr(
        analytics_module,
        "search_project_with_status",
        AsyncMock(return_value={"items": [dense_item], "degraded_mode": "NORMAL", "error_code": None}),
    )

    results, _metadata = await AnalyticsService.search_knowledge(
        "project-a",
        SearchInput(
            query="unmatched lexical phrase",
            artifact_types=["requirement_document"],
            limit=10,
        ),
        user,
    )

    assert len(results["items"]) == 1
    item = results["items"][0]
    assert item["artifact_id"] == "document-version-1"
    assert item["title"] == "requirements.pdf"
    assert item["authority"] == "PROJECT_REFERENCE"
    assert item["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_archived_dense_document_is_not_returned(monkeypatch):
    user = SimpleNamespace(id="member-a", is_system_admin=False)
    archived_record = {
        "_id": "document-version-archived",
        "project_id": "project-a",
        "created_by": "member-a",
        "filename": "old-requirements.pdf",
        "status": "ARCHIVED",
    }
    dense_item = {
        "artifact_type": "requirement_document",
        "artifact_id": "document-archived",
        "artifact_version_id": "document-version-archived",
        "authority": "PROJECT_REFERENCE",
        "status": "ACTIVE",
        "score": 0.9,
        "text": "Archived requirement passage.",
    }

    async def list_records(collection, query, _limit, _sort=None, projection=None):
        if collection == "requirement_documents" and "_id" in query:
            assert query.get("status") == {"$ne": "ARCHIVED"}
            return []
        return []

    monkeypatch.setattr(analytics_module, "get_project", AsyncMock(return_value={"settings": {}}))
    monkeypatch.setattr(analytics_module.analytics_repository, "list_records", list_records)
    monkeypatch.setattr(
        analytics_module,
        "search_project_with_status",
        AsyncMock(return_value={"items": [dense_item], "degraded_mode": "NORMAL", "error_code": None}),
    )

    results, _metadata = await AnalyticsService.search_knowledge(
        "project-a",
        SearchInput(
            query="Archived requirement",
            artifact_types=["requirement_document"],
            limit=10,
        ),
        user,
    )

    assert results["items"] == []

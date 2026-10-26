from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.schemas.project import ProjectKnowledgeSearchRequest
from src.services import project_knowledge
from src.services.project_knowledge import search_project_knowledge
from src.services.retrieval import RetrievalService


@pytest.mark.asyncio
async def test_cache_hit_rechecks_live_document_access(monkeypatch):
    request = ProjectKnowledgeSearchRequest(
        query="login rule", requester_id="member-a", is_admin=False
    )
    key = (
        "project-a",
        request.query,
        (),
        request.limit,
        request.requester_id,
        request.is_admin,
    )
    project_knowledge.SEARCH_CACHE.clear()
    project_knowledge.SEARCH_CACHE[key] = (
        10.0,
        {
            "items": [{"document_id": "source-1", "text": "private source"}],
            "degraded_mode": "NORMAL",
            "error_code": None,
        },
    )
    access_check = AsyncMock(return_value=[])
    monkeypatch.setattr(
        project_knowledge.retriever,
        "_filter_currently_accessible_sources",
        access_check,
    )
    monkeypatch.setattr(
        project_knowledge.project_artifact_generation_repository,
        "filter_active",
        AsyncMock(side_effect=lambda documents: documents),
    )

    with patch("src.services.project_knowledge.time.monotonic", return_value=10.5):
        result = await search_project_knowledge("project-a", request)

    access_check.assert_awaited_once_with(
        project_knowledge.SEARCH_CACHE[key][1]["items"], "member-a", False
    )
    assert result["items"] == []
    project_knowledge.SEARCH_CACHE.clear()


@pytest.mark.asyncio
async def test_cache_hit_fails_closed_when_live_access_check_is_unavailable(monkeypatch):
    request = ProjectKnowledgeSearchRequest(
        query="login rule", requester_id="member-a", is_admin=False
    )
    key = (
        "project-a",
        request.query,
        (),
        request.limit,
        request.requester_id,
        request.is_admin,
    )
    project_knowledge.SEARCH_CACHE.clear()
    project_knowledge.SEARCH_CACHE[key] = (10.0, {"items": [{"text": "private source"}]})
    check = AsyncMock(side_effect=RuntimeError("content service unavailable"))
    monkeypatch.setattr(project_knowledge.retriever, "_filter_currently_accessible_sources", check)
    monkeypatch.setattr(
        project_knowledge.project_artifact_generation_repository,
        "filter_active",
        AsyncMock(side_effect=lambda documents: documents),
    )

    with patch("src.services.project_knowledge.time.monotonic", return_value=10.5):
        with pytest.raises(HTTPException) as raised:
            await search_project_knowledge("project-a", request)

    assert raised.value.status_code == 503
    assert raised.value.detail == {"code": "DOCUMENT_ACCESS_VERIFICATION_UNAVAILABLE"}
    project_knowledge.SEARCH_CACHE.clear()


@pytest.mark.asyncio
async def test_source_document_id_is_checked_when_document_id_is_absent(monkeypatch):
    authorize = AsyncMock(return_value={})
    monkeypatch.setattr(
        "src.clients.content.ContentClient.active_index_generations_many", authorize
    )

    result = await RetrievalService._filter_currently_accessible_sources(
        [
            {
                "text": "derived requirement text",
                "metadata": {"source_document_id": "source-1"},
            }
        ],
        "member-a",
        False,
    )

    authorize.assert_awaited_once_with(["source-1"], "member-a", False)
    assert result == []

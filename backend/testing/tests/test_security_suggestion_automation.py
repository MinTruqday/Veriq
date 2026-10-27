import hashlib
from types import SimpleNamespace

import pytest

from src.modules.design.services import design_suggestion


@pytest.mark.asyncio
async def test_security_suggestion_event_replay_returns_matching_record(monkeypatch):
    version = {
        "_id": "version-1",
        "requirement_id": "requirement-1",
        "status": "BASELINED",
        "revision": 2,
    }
    source_event_id = "requirement-version:version-1:2:BASELINED"
    idempotency_key = "security-requirement:" + hashlib.sha256(
        f"{source_event_id}:version-1".encode("utf-8")
    ).hexdigest()
    existing = {
        "_id": "suggestion-1",
        "source_event_id": source_event_id,
        "source_event_revision": 2,
        "requirement_version_ids": ["version-1"],
    }
    payload = SimpleNamespace(
        requirement_version_ids=["version-1"],
        source_event_id=source_event_id,
        source_event_revision=2,
        idempotency_key=idempotency_key,
        categories=[],
        context="",
    )
    user = SimpleNamespace(id="user-1")

    async def get_project(*args, **kwargs):
        return {"_id": "project-1"}

    async def requirement_evidence(*args, **kwargs):
        return [version], []

    async def find_current_requirement(*args, **kwargs):
        return {"current_version_id": "version-1"}

    async def find_security_suggestion(*args, **kwargs):
        return existing

    monkeypatch.setattr(
        design_suggestion,
        "require_ai_automation_event",
        lambda principal, allowed: {
            "source_event_id": source_event_id,
            "trigger": "REQUIREMENT_CHANGED",
            "run_id": "run-1",
        },
    )
    monkeypatch.setattr(design_suggestion, "get_project", get_project)
    monkeypatch.setattr(design_suggestion, "requirement_evidence", requirement_evidence)
    monkeypatch.setattr(
        design_suggestion.test_design_repository,
        "find_current_requirement",
        find_current_requirement,
    )
    monkeypatch.setattr(
        design_suggestion.test_design_repository,
        "find_security_suggestion",
        find_security_suggestion,
    )

    result, metadata = await design_suggestion.DesignSuggestionService.generate_security(
        "project-1", payload, user
    )

    assert result is existing
    assert metadata == {}

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.modules.requirements.services import requirement_analysis
from src.schemas.contracts.requirements import RequirementDuplicateCheckInput


@pytest.mark.asyncio
async def test_project_wide_duplicate_scan_rejects_requirement_truncation(monkeypatch):
    monkeypatch.setattr(
        requirement_analysis,
        "get_project",
        _resolved(None),
    )
    monkeypatch.setattr(
        requirement_analysis.settings,
        "REQUIREMENT_DUPLICATE_SCAN_MAX_ITEMS",
        1,
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_requirements",
        _resolved([{"_id": "REQ-1"}, {"_id": "REQ-2"}]),
    )

    with pytest.raises(HTTPException) as raised:
        await requirement_analysis.find_requirement_duplicates(
            "PRJ-1", RequirementDuplicateCheckInput(), SimpleNamespace(id="qa-1")
        )

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "REQUIREMENT_DUPLICATE_SCAN_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_duplicate_scan_rejects_missing_current_versions(monkeypatch):
    monkeypatch.setattr(
        requirement_analysis,
        "get_project",
        _resolved(None),
    )
    monkeypatch.setattr(
        requirement_analysis.settings,
        "REQUIREMENT_DUPLICATE_SCAN_MAX_ITEMS",
        10,
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_requirements",
        _resolved([{"_id": "REQ-1", "current_version_id": "REQV-1"}]),
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_versions",
        _resolved([]),
    )

    with pytest.raises(HTTPException) as raised:
        await requirement_analysis.find_requirement_duplicates(
            "PRJ-1", RequirementDuplicateCheckInput(), SimpleNamespace(id="qa-1")
        )

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "REQUIREMENT_DUPLICATE_SCAN_VERSION_SNAPSHOT_INCOMPLETE"


@pytest.mark.asyncio
async def test_duplicate_scan_rejects_wrong_version_ids_even_when_count_matches(monkeypatch):
    monkeypatch.setattr(
        requirement_analysis,
        "get_project",
        _resolved(None),
    )
    monkeypatch.setattr(
        requirement_analysis.settings,
        "REQUIREMENT_DUPLICATE_SCAN_MAX_ITEMS",
        10,
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_requirements",
        _resolved([{"_id": "REQ-1", "current_version_id": "REQV-1"}]),
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_versions",
        _resolved([{"_id": "REQV-OTHER"}]),
    )

    with pytest.raises(HTTPException) as raised:
        await requirement_analysis.find_requirement_duplicates(
            "PRJ-1", RequirementDuplicateCheckInput(), SimpleNamespace(id="qa-1")
        )

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "REQUIREMENT_DUPLICATE_SCAN_VERSION_SNAPSHOT_INCOMPLETE"


@pytest.mark.asyncio
async def test_duplicate_scan_rejects_version_owned_by_another_requirement(monkeypatch):
    monkeypatch.setattr(
        requirement_analysis,
        "get_project",
        _resolved(None),
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_requirements",
        _resolved([{"_id": "REQ-1", "current_version_id": "REQV-1"}]),
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_versions",
        _resolved(
            [
                {
                    "_id": "REQV-1",
                    "project_id": "PRJ-1",
                    "requirement_id": "REQ-OTHER",
                }
            ]
        ),
    )

    with pytest.raises(HTTPException) as raised:
        await requirement_analysis.find_requirement_duplicates(
            "PRJ-1", RequirementDuplicateCheckInput(), SimpleNamespace(id="qa-1")
        )

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "REQUIREMENT_DUPLICATE_SCAN_VERSION_SNAPSHOT_INCOMPLETE"


@pytest.mark.asyncio
async def test_duplicate_scan_rejects_truncated_acceptance_criteria(monkeypatch):
    monkeypatch.setattr(
        requirement_analysis,
        "get_project",
        _resolved(None),
    )
    monkeypatch.setattr(
        requirement_analysis.settings,
        "REQUIREMENT_DUPLICATE_SCAN_MAX_ITEMS",
        10,
    )
    monkeypatch.setattr(
        requirement_analysis.settings,
        "REQUIREMENT_DUPLICATE_SCAN_MAX_CRITERIA",
        1,
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_requirements",
        _resolved([{"_id": "REQ-1", "current_version_id": "REQV-1"}]),
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_versions",
        _resolved(
            [
                {
                    "_id": "REQV-1",
                    "project_id": "PRJ-1",
                    "requirement_id": "REQ-1",
                    "title": "Đăng nhập",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_acceptance_criteria",
        _resolved(
            [
                {"_id": "AC-1", "requirement_version_id": "REQV-1"},
                {"_id": "AC-2", "requirement_version_id": "REQV-1"},
            ]
        ),
    )

    with pytest.raises(HTTPException) as raised:
        await requirement_analysis.find_requirement_duplicates(
            "PRJ-1", RequirementDuplicateCheckInput(), SimpleNamespace(id="qa-1")
        )

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "REQUIREMENT_DUPLICATE_SCAN_CRITERIA_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_duplicate_scan_records_the_scoring_signals_it_actually_uses(monkeypatch):
    monkeypatch.setattr(
        requirement_analysis,
        "get_project",
        _resolved(None),
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_requirements",
        _resolved(
            [
                {"_id": "REQ-1", "current_version_id": "REQV-1"},
                {"_id": "REQ-2", "current_version_id": "REQV-2"},
            ]
        ),
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_versions",
        _resolved(
            [
                {
                    "_id": "REQV-1",
                    "project_id": "PRJ-1",
                    "requirement_id": "REQ-1",
                    "title": "Đăng nhập",
                },
                {
                    "_id": "REQV-2",
                    "project_id": "PRJ-1",
                    "requirement_id": "REQ-2",
                    "title": "Đăng nhập",
                },
            ]
        ),
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "list_acceptance_criteria",
        _resolved([]),
    )
    monkeypatch.setattr(
        requirement_analysis.requirement_analysis_repository,
        "insert_duplicate_scan",
        _resolved(None),
    )
    monkeypatch.setattr(requirement_analysis, "audit", _resolved(None))

    result = await requirement_analysis.find_requirement_duplicates(
        "PRJ-1", RequirementDuplicateCheckInput(), SimpleNamespace(id="qa-1")
    )

    assert result["algorithm"] == {
        "name": "requirement_duplicate",
        "version": "1",
        "score_signals": [
            "content_similarity",
            "business_rule_similarity",
            "acceptance_criteria_similarity",
        ],
        "aggregation": "arithmetic_mean_of_available_signals",
        "explanation_only_signals": ["actor_similarity"],
    }


def _resolved(value):
    async def result(*args, **kwargs):
        return value

    return result

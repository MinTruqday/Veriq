import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch

from src.core.ai_automation import (
    require_ai_automation_event,
    require_document_ingestion_event,
)
from src.modules.quality.api.analytics import ask_project
from src.modules.requirements.api.requirement_templates import review_requirement_template
from src.core.auth import CurrentUser
from src.schemas.contracts.utility import ProjectQuestionInput


class Principal:
    pass


def test_manual_user_cannot_start_ai_generation():
    with pytest.raises(HTTPException) as error:
        require_ai_automation_event(Principal(), {"REQUIREMENT_CHANGED"})

    assert error.value.status_code == 403
    assert error.value.detail["code"] == "AI_AUTOMATION_EVENT_REQUIRED"


def test_verified_automation_event_can_start_allowed_generation():
    principal = Principal()
    principal._ai_automation_run_id = "run-1"
    principal._ai_automation_trigger = "REQUIREMENT_CHANGED"
    principal._ai_automation_source_event_id = "requirement-version:version-1:2:BASELINED"

    result = require_ai_automation_event(principal, {"REQUIREMENT_CHANGED"})

    assert result == {
        "run_id": "run-1",
        "trigger": "REQUIREMENT_CHANGED",
        "source_event_id": "requirement-version:version-1:2:BASELINED",
    }


def test_unrelated_automation_trigger_cannot_start_generation():
    principal = Principal()
    principal._ai_automation_run_id = "run-1"
    principal._ai_automation_trigger = "TEST_CASE_APPROVED"
    principal._ai_automation_source_event_id = "test-case:case-1:3:APPROVED"

    with pytest.raises(HTTPException) as error:
        require_ai_automation_event(principal, {"REQUIREMENT_CHANGED"})

    assert error.value.status_code == 403
    assert error.value.detail["code"] == "AI_AUTOMATION_EVENT_REQUIRED"


def test_document_synthesis_requires_the_triggering_document_in_the_source_set():
    principal = Principal()
    principal._ai_automation_run_id = "run-2"
    principal._ai_automation_trigger = "DOCUMENT_INGESTED"
    principal._ai_automation_source_event_id = "requirement-document:DOC-7:4"

    assert require_document_ingestion_event(principal, ["DOC-7", "DOC-8"]) == (
        "DOC-7",
        4,
    )

    with pytest.raises(HTTPException) as error:
        require_document_ingestion_event(principal, ["DOC-8"])

    assert error.value.status_code == 403
    assert error.value.detail["code"] == "VERIFIED_DOCUMENT_EVENT_REQUIRED"


@pytest.mark.asyncio
async def test_project_question_remains_an_explicit_ai_action():
    user = CurrentUser(_id="user-1", email="user@example.test")
    payload = ProjectQuestionInput(question="Tóm tắt rủi ro của dự án")
    result = {"answer": "Căn cứ theo hồ sơ dự án", "evidence": []}

    with patch(
        "src.modules.quality.api.analytics.AnalyticsService.ask_project",
        new=AsyncMock(return_value=(result, {"status": "SUCCESS"})),
    ) as ask:
        response = await ask_project("project-1", payload, user)

    assert response["data"] == result
    ask.assert_awaited_once()


@pytest.mark.asyncio
async def test_template_quality_review_remains_an_explicit_ai_action():
    user = CurrentUser(_id="user-1", email="user@example.test")
    result = {"status": "REVIEW_REQUIRED", "findings": []}

    with patch(
        "src.modules.requirements.api.requirement_templates.review_template",
        new=AsyncMock(return_value=result),
    ) as review:
        response = await review_requirement_template("project-1", "template-1", user)

    assert response["data"] == result
    review.assert_awaited_once_with("project-1", "template-1", user)

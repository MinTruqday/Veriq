from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from starlette.requests import Request

from src.core.ai_automation import request_ai_automation
from src.modules.projects.api.projects import _accept_language
from src.schemas.contracts.project import ProjectCreate


@pytest.mark.asyncio
async def test_ai_request_uses_project_locale_as_trusted_output_language():
    project_collection = Mock()
    project_collection.find_one = AsyncMock(return_value={"locale": "en-US"})
    database_value = Mock(projects=project_collection)
    database_client = MagicMock()
    database_client.__getitem__.return_value = database_value

    with (
        patch("src.core.ai_automation.database.client", database_client),
        patch(
            "src.core.ai_automation.ai_automation_client.request",
            new=AsyncMock(return_value={"capability": "capability-a", "status": "SUCCESS"}),
        ) as request,
    ):
        await request_ai_automation("capability-a", "project-a", "", [])

    assert request.await_args.args[0]["output_language"] == "en-US"


def test_new_project_has_no_fixed_output_locale_and_uses_request_language():
    payload = ProjectCreate(
        key="LANG",
        name="Language test",
        initial_qa_user_id="qa-user",
    )
    request = Request(
        {
            "type": "http",
            "headers": [(b"accept-language", b"en-US,en;q=0.9,vi;q=0.8")],
        }
    )

    assert payload.locale is None
    assert _accept_language(request) == "en-US"

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.modules.execution.services import test_run_query


def test_test_run_read_resolves_assignment_names_without_exposing_account_details(monkeypatch):
    run = {
        "_id": "run-1",
        "project_id": "project-1",
        "test_case_version_ids": ["case-version-1", "case-version-2"],
        "test_case_assignments": {"case-version-1": "tester-1"},
        "test_case_assignment_decisions": {
            "case-version-1": {"assignee_id": "tester-1"},
            "case-version-2": {"assignee_id": "tester-2"},
        },
    }
    monkeypatch.setattr(
        test_run_query,
        "get_project_entity",
        AsyncMock(return_value=run),
    )
    monkeypatch.setattr(
        test_run_query.test_run_repository,
        "list_versions",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        test_run_query.test_run_repository,
        "list_results",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        test_run_query.test_run_repository,
        "list_defects_for_results",
        AsyncMock(return_value=[]),
    )
    identities = AsyncMock(
        return_value={
            "tester-1": {"full_name": "Nguyễn An", "email": "an@example.test"},
            "tester-2": {"full_name": "Trần Bình", "email": "binh@example.test"},
        }
    )
    monkeypatch.setattr(test_run_query, "load_user_identities", identities)

    result = asyncio.run(
        test_run_query.get_test_run_record("run-1", SimpleNamespace(id="reader"))
    )

    assert result["test_case_assignment_identities"] == {
        "tester-1": {"display_name": "Nguyễn An"},
        "tester-2": {"display_name": "Trần Bình"},
    }
    assert identities.await_args.args[0] == {"tester-1", "tester-2"}
    assert "email" not in repr(result["test_case_assignment_identities"])

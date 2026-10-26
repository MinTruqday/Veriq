import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.modules.execution.services import test_run as service
from src.schemas.contracts.execution import TestRunRerunInput


class MemoryTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, error_type, error, traceback):
        return False


class MemorySession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, error_type, error, traceback):
        return False

    def start_transaction(self):
        return MemoryTransaction()


class MemoryClient:
    async def start_session(self):
        return MemorySession()


def test_rerun_only_accepts_a_completed_or_aborted_source(monkeypatch):
    source = {"_id": "run-a", "project_id": "project-a", "status": "IN_PROGRESS"}
    monkeypatch.setattr(service, "get_project_entity", AsyncMock(return_value=source))

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            service.rerun_test_run_record(
                "project-a",
                "run-a",
                TestRunRerunInput(idempotency_key="rerun-key-0001"),
                SimpleNamespace(id="qa-a"),
            )
        )

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "TEST_RUN_RERUN_REQUIRES_TERMINAL_SOURCE"


def test_rerun_creates_fresh_results_and_preserves_source_scope(monkeypatch):
    source = {
        "_id": "run-a",
        "project_id": "project-a",
        "name": "Regression run",
        "status": "COMPLETED",
        "revision": 4,
        "test_plan_id": None,
        "test_suite_ids": ["suite-a"],
        "test_case_version_ids": ["version-a", "version-b"],
        "assignment_strategy": "MANUAL",
        "test_case_assignments": {"version-a": "tester-a"},
        "environment": "staging",
        "environment_id": "environment-a",
        "release": "release-1",
        "release_id": "release-a",
        "build": "build-1",
        "build_id": "build-a",
    }
    inserted_runs = []
    inserted_results = []
    repository = service.test_run_repository
    monkeypatch.setattr(service, "get_project_entity", AsyncMock(return_value=source))
    monkeypatch.setattr(service, "validate_test_versions", AsyncMock())
    monkeypatch.setattr(repository, "find_rerun_by_key", AsyncMock(side_effect=[None, None]))
    monkeypatch.setattr(repository, "find_run_by_idempotency_key", AsyncMock(return_value=None))
    monkeypatch.setattr(repository, "find_run", AsyncMock(return_value=source))
    monkeypatch.setattr(repository, "insert_run", AsyncMock(side_effect=lambda item, session=None: inserted_runs.append(item)))
    monkeypatch.setattr(repository, "insert_results", AsyncMock(side_effect=lambda items, session=None: inserted_results.extend(items)))
    monkeypatch.setattr(service, "audit", AsyncMock())
    monkeypatch.setattr(service, "index_artifact", AsyncMock())
    monkeypatch.setattr(service, "database", SimpleNamespace(client=MemoryClient()))

    result = asyncio.run(
        service.rerun_test_run_record(
            "project-a",
            "run-a",
            TestRunRerunInput(idempotency_key="rerun-key-0001"),
            SimpleNamespace(id="qa-a"),
        )
    )

    assert result["rerun_of_run_id"] == "run-a"
    assert result["test_case_version_ids"] == source["test_case_version_ids"]
    assert result["environment_id"] == source["environment_id"]
    assert result["release_id"] == source["release_id"]
    assert result["build_id"] == source["build_id"]
    assert result["test_case_assignments"] == source["test_case_assignments"]
    assert result["status"] == "DRAFT"
    assert len(inserted_runs) == 1
    assert [item["status"] for item in inserted_results] == ["NOT_RUN", "NOT_RUN"]
    assert all(item["test_run_id"] == result["_id"] for item in inserted_results)
    assert all(item["step_results"] == [] and item["executor_id"] is None for item in inserted_results)
    assert source["status"] == "COMPLETED"

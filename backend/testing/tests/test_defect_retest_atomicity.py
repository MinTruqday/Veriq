import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.modules.quality.services import defect_lifecycle as service


class _AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Session(_AsyncContext):
    def start_transaction(self):
        return _AsyncContext()


def _setup_retest(monkeypatch, *, apply_result=None, mark_error=None):
    session = _Session()
    defect = {
        "_id": "defect-a",
        "project_id": "project-a",
        "status": "READY_FOR_RETEST",
        "revision": 4,
        "linked_test_case_version_id": "case-version-a",
    }
    result = {
        "_id": "result-a",
        "test_run_id": "run-a",
        "test_case_version_id": "case-version-a",
        "status": "PASS",
    }
    updated = {**defect, "status": "CLOSED", "revision": 5}
    monkeypatch.setattr(
        service,
        "database",
        SimpleNamespace(client=SimpleNamespace(start_session=AsyncMock(return_value=session))),
    )
    monkeypatch.setattr(service, "get_project_entity", AsyncMock(return_value=defect))
    monkeypatch.setattr(
        service.defect_repository,
        "find_retest",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        service.defect_repository,
        "find_test_result",
        AsyncMock(return_value=result),
    )
    monkeypatch.setattr(
        service.defect_repository,
        "insert_retest",
        AsyncMock(),
    )
    monkeypatch.setattr(
        service.defect_repository,
        "apply_retest",
        AsyncMock(return_value=apply_result if apply_result is not None else updated),
    )
    monkeypatch.setattr(
        service.defect_repository,
        "mark_retest_applied",
        AsyncMock(side_effect=mark_error),
    )
    monkeypatch.setattr(service, "audit", AsyncMock())
    monkeypatch.setattr(service, "new_id", lambda prefix: f"{prefix}-a")
    monkeypatch.setattr(service, "now", lambda: "2026-10-26T00:00:00Z")
    payload = SimpleNamespace(
        idempotency_key="retry-a",
        test_result_id="result-a",
        expected_revision=4,
        note="Rerun passed",
    )
    user = SimpleNamespace(id="tester-a")
    return session, defect, updated, payload, user


def test_retest_persists_event_defect_transition_and_audit_in_one_transaction(monkeypatch):
    async def run():
        session, _, updated, payload, user = _setup_retest(monkeypatch)
        result = await service.retest_defect_record("project-a", "defect-a", payload, user)

        assert result["defect"] == updated
        assert result["retest"]["application_status"] == "APPLIED"
        service.defect_repository.insert_retest.assert_awaited_once()
        service.defect_repository.apply_retest.assert_awaited_once()
        service.defect_repository.mark_retest_applied.assert_awaited_once_with(
            "DRT-a", "APPLIED", session=session
        )
        assert service.defect_repository.insert_retest.await_args.kwargs["session"] is session
        assert service.defect_repository.apply_retest.await_args.kwargs["session"] is session
        assert service.audit.await_args.kwargs["session"] is session

    asyncio.run(run())


def test_retest_revision_conflict_aborts_without_persisting_a_pending_event(monkeypatch):
    async def run():
        _setup_retest(monkeypatch, apply_result=None)
        service.defect_repository.apply_retest.return_value = None
        with pytest.raises(HTTPException) as raised:
            await service.retest_defect_record(
                "project-a",
                "defect-a",
                SimpleNamespace(
                    idempotency_key="retry-b",
                    test_result_id="result-a",
                    expected_revision=3,
                    note="Rerun passed",
                ),
                SimpleNamespace(id="tester-a"),
            )

        assert raised.value.status_code == 409
        assert raised.value.detail["code"] == "REVISION_CONFLICT"
        service.defect_repository.mark_retest_applied.assert_not_awaited()
        service.audit.assert_not_awaited()

    asyncio.run(run())


def test_retest_audit_failure_aborts_transaction_after_state_write_attempt(monkeypatch):
    async def run():
        session, _, _, payload, user = _setup_retest(monkeypatch)
        service.audit.side_effect = RuntimeError("audit unavailable")
        with pytest.raises(RuntimeError, match="audit unavailable"):
            await service.retest_defect_record("project-a", "defect-a", payload, user)

        assert service.defect_repository.insert_retest.await_args.kwargs["session"] is session
        assert service.defect_repository.apply_retest.await_args.kwargs["session"] is session
        assert service.defect_repository.mark_retest_applied.await_args.kwargs["session"] is session
        assert service.audit.await_args.kwargs["session"] is session

    asyncio.run(run())


def test_retest_uses_original_result_version_when_defect_version_link_is_missing(monkeypatch):
    async def run():
        _setup_retest(monkeypatch)
        defect = {
            "_id": "defect-a",
            "project_id": "project-a",
            "status": "READY_FOR_RETEST",
            "revision": 4,
            "linked_test_result_id": "result-original",
        }
        monkeypatch.setattr(service, "get_project_entity", AsyncMock(return_value=defect))
        service.defect_repository.find_test_result.side_effect = [
            {
                "_id": "result-new",
                "test_run_id": "run-new",
                "test_case_version_id": "case-version-a",
                "status": "PASS",
            },
            {
                "_id": "result-original",
                "test_run_id": "run-old",
                "test_case_version_id": "case-version-a",
                "status": "FAIL",
            },
        ]
        payload = SimpleNamespace(
            idempotency_key="retry-new-result",
            test_result_id="result-new",
            expected_revision=4,
            note="Retest",
        )
        await service.retest_defect_record(
            "project-a", "defect-a", payload, SimpleNamespace(id="tester-a")
        )
        assert service.defect_repository.find_test_result.await_count == 2

    asyncio.run(run())


def test_retest_rejects_reusing_the_original_failure_result(monkeypatch):
    async def run():
        _setup_retest(monkeypatch)
        original = {
            "_id": "result-original",
            "test_run_id": "run-old",
            "test_case_version_id": "case-version-a",
            "status": "FAIL",
        }
        defect = {
            "_id": "defect-a",
            "project_id": "project-a",
            "status": "READY_FOR_RETEST",
            "revision": 4,
            "linked_test_result_id": "result-original",
        }
        monkeypatch.setattr(service, "get_project_entity", AsyncMock(return_value=defect))
        service.defect_repository.find_test_result.side_effect = [original, original]
        with pytest.raises(HTTPException) as raised:
            await service.retest_defect_record(
                "project-a",
                "defect-a",
                SimpleNamespace(
                    idempotency_key="reuse-original-result",
                    test_result_id="result-original",
                    expected_revision=4,
                    note="Retest",
                ),
                SimpleNamespace(id="tester-a"),
            )
        assert raised.value.status_code == 422
        assert raised.value.detail["code"] == "RETEST_RESULT_MUST_BE_NEW"
        service.defect_repository.insert_retest.assert_not_awaited()

    asyncio.run(run())


def test_retest_fails_closed_when_original_result_cannot_be_loaded(monkeypatch):
    async def run():
        _setup_retest(monkeypatch)
        defect = {
            "_id": "defect-a",
            "project_id": "project-a",
            "status": "READY_FOR_RETEST",
            "revision": 4,
            "linked_test_result_id": "result-original",
        }
        monkeypatch.setattr(service, "get_project_entity", AsyncMock(return_value=defect))
        service.defect_repository.find_test_result.side_effect = [
            {
                "_id": "result-new",
                "test_run_id": "run-new",
                "test_case_version_id": "case-version-a",
                "status": "PASS",
            },
            None,
        ]
        with pytest.raises(HTTPException) as raised:
            await service.retest_defect_record(
                "project-a",
                "defect-a",
                SimpleNamespace(
                    idempotency_key="missing-original-result",
                    test_result_id="result-new",
                    expected_revision=4,
                    note="Retest",
                ),
                SimpleNamespace(id="tester-a"),
            )
        assert raised.value.status_code == 409
        assert raised.value.detail["code"] == "DEFECT_RETEST_SOURCE_RESULT_UNAVAILABLE"
        service.defect_repository.insert_retest.assert_not_awaited()

    asyncio.run(run())

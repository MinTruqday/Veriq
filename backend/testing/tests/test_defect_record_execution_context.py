import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.modules.quality.services import defect_records as service
from src.repositories import defect as defect_repository_module
from src.schemas.contracts.defects import DefectCreate


class _AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Session(_AsyncContext):
    def start_transaction(self):
        return _AsyncContext()


def _payload(**overrides):
    values = {
        "project_id": "project-a",
        "title": "Failed execution defect",
        "linked_test_result_id": "result-a",
    }
    values.update(overrides)
    return DefectCreate(**values)


def _configure_linked_failure(monkeypatch, *, run=None):
    monkeypatch.setattr(service, "get_project", AsyncMock())
    monkeypatch.setattr(
        service.defect_repository,
        "find_test_result",
        AsyncMock(
            return_value={
                "_id": "result-a",
                "project_id": "project-a",
                "test_run_id": "run-a",
                "test_case_version_id": "case-version-a",
                "status": "FAIL",
            }
        ),
    )
    monkeypatch.setattr(
        service.defect_repository,
        "find_test_run",
        AsyncMock(
            return_value=run
            or {
                "_id": "run-a",
                "project_id": "project-a",
                "release_id": None,
                "build_id": None,
                "environment_id": None,
                "test_case_version_ids": ["case-version-a"],
            }
        ),
    )
    monkeypatch.setattr(
        service.defect_repository,
        "find_test_case_version",
        AsyncMock(return_value={"_id": "case-version-a", "project_id": "project-a"}),
    )


def test_defect_rejects_test_case_version_different_from_failed_result(monkeypatch):
    async def run():
        _configure_linked_failure(monkeypatch)
        with pytest.raises(HTTPException) as raised:
            await service.create_defect_record(
                "project-a",
                _payload(linked_test_case_version_id="case-version-b"),
                type("User", (), {"id": "qa-a"})(),
            )

        assert raised.value.status_code == 422
        assert raised.value.detail["code"] == "DEFECT_TEST_CASE_CONTEXT_MISMATCH"
        service.defect_repository.find_test_run.assert_not_awaited()

    asyncio.run(run())


def test_defect_rejects_test_case_version_from_another_project(monkeypatch):
    async def run():
        monkeypatch.setattr(service, "get_project", AsyncMock())
        monkeypatch.setattr(
            service.defect_repository,
            "find_test_case_version",
            AsyncMock(return_value=None),
        )
        with pytest.raises(HTTPException) as raised:
            await service.create_defect_record(
                "project-a",
                _payload(linked_test_result_id=None, linked_test_case_version_id="case-version-b"),
                type("User", (), {"id": "qa-a"})(),
            )

        assert raised.value.status_code == 422
        assert raised.value.detail["code"] == "INVALID_TEST_CASE_VERSION"

    asyncio.run(run())


def test_defect_rejects_failed_result_case_outside_run_scope(monkeypatch):
    async def run():
        _configure_linked_failure(
            monkeypatch,
            run={
                "_id": "run-a",
                "project_id": "project-a",
                "release_id": None,
                "build_id": None,
                "environment_id": None,
                "test_case_version_ids": [],
            },
        )
        with pytest.raises(HTTPException) as raised:
            await service.create_defect_record(
                "project-a",
                _payload(),
                type("User", (), {"id": "qa-a"})(),
            )

        assert raised.value.status_code == 409
        assert raised.value.detail["code"] == "DEFECT_TEST_CASE_OUTSIDE_RUN_SCOPE"
        service.defect_repository.find_test_case_version.assert_not_awaited()

    asyncio.run(run())


def test_defect_rejects_requirement_version_from_another_project(monkeypatch):
    async def run():
        monkeypatch.setattr(service, "get_project", AsyncMock())
        monkeypatch.setattr(
            service.defect_repository,
            "count_requirement_versions",
            AsyncMock(return_value=0),
        )
        with pytest.raises(HTTPException) as raised:
            await service.create_defect_record(
                "project-a",
                _payload(linked_test_result_id=None, linked_requirement_version_ids=["req-version-b"]),
                type("User", (), {"id": "qa-a"})(),
            )

        assert raised.value.status_code == 422
        assert raised.value.detail["code"] == "INVALID_REQUIREMENT_VERSION"

    asyncio.run(run())


def test_defect_rejects_release_context_not_present_on_linked_run(monkeypatch):
    async def run():
        _configure_linked_failure(monkeypatch)
        with pytest.raises(HTTPException) as raised:
            await service.create_defect_record(
                "project-a",
                _payload(release_id="release-a"),
                type("User", (), {"id": "qa-a"})(),
            )

        assert raised.value.status_code == 422
        assert raised.value.detail == {
            "code": "DEFECT_EXECUTION_CONTEXT_MISMATCH",
            "field": "release_id",
        }

    asyncio.run(run())


def test_defect_rechecks_failed_result_inside_transaction(monkeypatch):
    async def run():
        _configure_linked_failure(monkeypatch)
        result = {
            "_id": "result-a",
            "project_id": "project-a",
            "test_run_id": "run-a",
            "test_case_version_id": "case-version-a",
            "status": "FAIL",
            "revision": 3,
        }
        corrected = {**result, "status": "PASS", "revision": 4}
        service.defect_repository.find_test_result.side_effect = [result, corrected]
        session = _Session()
        monkeypatch.setattr(
            service,
            "database",
            SimpleNamespace(
                client=SimpleNamespace(start_session=AsyncMock(return_value=session))
            ),
        )
        monkeypatch.setattr(service, "resolve_execution_context", AsyncMock(return_value={}))
        monkeypatch.setattr(service, "next_key", AsyncMock(return_value="DEF-1"))

        with pytest.raises(HTTPException) as raised:
            await service.create_defect_record(
                "project-a",
                _payload(),
                type("User", (), {"id": "qa-a"})(),
            )

        assert raised.value.status_code == 409
        assert raised.value.detail["code"] == "DEFECT_TEST_RESULT_CONTEXT_CHANGED"
        assert service.defect_repository.find_test_result.await_count == 2

    asyncio.run(run())


def test_defect_aborts_when_failed_result_changes_before_transactional_link(monkeypatch):
    async def run():
        _configure_linked_failure(monkeypatch)
        result = {
            "_id": "result-a",
            "project_id": "project-a",
            "test_run_id": "run-a",
            "test_case_version_id": "case-version-a",
            "status": "FAIL",
            "revision": 3,
        }
        service.defect_repository.find_test_result.side_effect = [result, result]
        session = _Session()
        monkeypatch.setattr(
            service,
            "database",
            SimpleNamespace(
                client=SimpleNamespace(start_session=AsyncMock(return_value=session))
            ),
        )
        monkeypatch.setattr(service, "resolve_execution_context", AsyncMock(return_value={}))
        monkeypatch.setattr(service, "next_key", AsyncMock(return_value="DEF-1"))
        monkeypatch.setattr(
            service.defect_repository,
            "link_failed_result_to_defect",
            AsyncMock(return_value=None),
        )

        with pytest.raises(HTTPException) as raised:
            await service.create_defect_record(
                "project-a",
                _payload(),
                type("User", (), {"id": "qa-a"})(),
            )

        assert raised.value.status_code == 409
        assert raised.value.detail["code"] == "DEFECT_TEST_RESULT_CONTEXT_CHANGED"
        assert service.defect_repository.link_failed_result_to_defect.await_args.args[-1] is session

    asyncio.run(run())


def test_defect_rejects_run_context_changed_inside_transaction(monkeypatch):
    async def run():
        original_run = {
            "_id": "run-a",
            "project_id": "project-a",
            "release_id": "release-a",
            "build_id": "build-a",
            "environment_id": "environment-a",
            "test_case_version_ids": ["case-version-a"],
        }
        changed_run = {**original_run, "environment_id": "environment-b"}
        _configure_linked_failure(monkeypatch, run=original_run)
        service.defect_repository.find_test_run.side_effect = [original_run, changed_run]
        result = {
            "_id": "result-a",
            "project_id": "project-a",
            "test_run_id": "run-a",
            "test_case_version_id": "case-version-a",
            "status": "FAIL",
            "revision": 3,
        }
        service.defect_repository.find_test_result.side_effect = [result, result]
        session = _Session()
        monkeypatch.setattr(
            service,
            "database",
            SimpleNamespace(
                client=SimpleNamespace(start_session=AsyncMock(return_value=session))
            ),
        )
        monkeypatch.setattr(service, "resolve_execution_context", AsyncMock(return_value={}))
        monkeypatch.setattr(service, "next_key", AsyncMock(return_value="DEF-1"))
        monkeypatch.setattr(
            service.defect_repository,
            "link_failed_result_to_defect",
            AsyncMock(),
        )

        with pytest.raises(HTTPException) as raised:
            await service.create_defect_record(
                "project-a",
                _payload(),
                type("User", (), {"id": "qa-a"})(),
            )

        assert raised.value.status_code == 409
        assert raised.value.detail["code"] == "DEFECT_TEST_RESULT_CONTEXT_CHANGED"
        service.defect_repository.link_failed_result_to_defect.assert_not_awaited()

    asyncio.run(run())


def test_linking_defect_advances_failed_result_revision(monkeypatch):
    async def run():
        find_one_and_update = AsyncMock(return_value={"_id": "result-a"})
        monkeypatch.setattr(
            defect_repository_module,
            "database",
            SimpleNamespace(
                value=SimpleNamespace(
                    test_results=SimpleNamespace(
                        find_one_and_update=find_one_and_update
                    )
                )
            ),
        )
        session = object()
        await defect_repository_module.defect_repository.link_failed_result_to_defect(
            "result-a",
            "project-a",
            3,
            "run-a",
            "case-version-a",
            "defect-a",
            "2026-10-27T00:00:00+00:00",
            session,
        )

        query, changes = find_one_and_update.await_args.args[:2]
        assert query["revision"] == 3
        assert changes["$inc"] == {"revision": 1}
        assert changes["$set"]["updated_at"] == "2026-10-27T00:00:00+00:00"
        assert changes["$addToSet"] == {"linked_defect_ids": "defect-a"}
        assert find_one_and_update.await_args.kwargs["session"] is session

    asyncio.run(run())


def test_defect_create_reuses_matching_idempotency_key(monkeypatch):
    async def run():
        payload = _payload(idempotency_key="defect-create-operation")
        request_hash = service._defect_request_fingerprint(payload)
        existing = {
            "_id": "defect-existing",
            "title": "Failed execution defect",
            "status": "NEW",
            "idempotency_request_hash": request_hash,
        }
        monkeypatch.setattr(service, "get_project", AsyncMock())
        monkeypatch.setattr(
            service.defect_repository,
            "find_defect_by_idempotency",
            AsyncMock(return_value=existing),
        )
        create = AsyncMock()
        enqueue = AsyncMock()
        monkeypatch.setattr(service, "_create_defect_record", create)
        monkeypatch.setattr(service.defect_search_index_repository, "enqueue", enqueue)

        result = await service.create_defect_record(
            "project-a",
            payload,
            type("User", (), {"id": "qa-a"})(),
        )

        assert result["_id"] == existing["_id"]
        assert "idempotency_key" not in result
        assert "idempotency_request_hash" not in result
        create.assert_not_awaited()
        enqueue.assert_awaited_once_with(existing)

    asyncio.run(run())


def test_defect_create_rejects_idempotency_key_with_different_payload(monkeypatch):
    async def run():
        payload = _payload(idempotency_key="defect-create-operation")
        monkeypatch.setattr(service, "get_project", AsyncMock())
        monkeypatch.setattr(
            service.defect_repository,
            "find_defect_by_idempotency",
            AsyncMock(
                return_value={
                    "_id": "defect-existing",
                    "idempotency_request_hash": "different-payload",
                }
            ),
        )
        create = AsyncMock()
        monkeypatch.setattr(service, "_create_defect_record", create)

        with pytest.raises(HTTPException) as raised:
            await service.create_defect_record(
                "project-a",
                payload,
                type("User", (), {"id": "qa-a"})(),
            )

        assert raised.value.status_code == 409
        assert raised.value.detail["code"] == "IDEMPOTENCY_KEY_REUSED"
        create.assert_not_awaited()

    asyncio.run(run())


def test_defect_create_recovers_from_concurrent_idempotency_insert(monkeypatch):
    async def run():
        payload = _payload(idempotency_key="defect-create-operation")
        request_hash = service._defect_request_fingerprint(payload)
        existing = {
            "_id": "defect-existing",
            "title": "Failed execution defect",
            "status": "NEW",
            "idempotency_request_hash": request_hash,
        }
        monkeypatch.setattr(service, "get_project", AsyncMock())
        find_by_key = AsyncMock(side_effect=[None, existing])
        monkeypatch.setattr(
            service.defect_repository,
            "find_defect_by_idempotency",
            find_by_key,
        )
        create = AsyncMock(side_effect=DuplicateKeyError("duplicate idempotency key"))
        enqueue = AsyncMock()
        monkeypatch.setattr(service, "_create_defect_record", create)
        monkeypatch.setattr(service.defect_search_index_repository, "enqueue", enqueue)
        user = SimpleNamespace(id="qa-a")

        result = await service.create_defect_record(
            "project-a",
            payload,
            user,
        )

        assert result["_id"] == existing["_id"]
        assert find_by_key.await_count == 2
        create.assert_awaited_once_with(
            "project-a",
            payload,
            user,
        )
        enqueue.assert_awaited_once_with(existing)

    asyncio.run(run())

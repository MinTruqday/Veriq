import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.modules.execution.services import test_plan as test_plan_service
from src.modules.execution.services import test_run as service
from src.modules.execution.services.test_plan import (
    _legacy_plan_snapshot_hash,
    plan_snapshot,
    plan_snapshot_hash,
    verified_approved_plan_snapshot,
)
from src.modules.execution.services.execution_state import frozen_run_scope
from src.schemas.contracts.execution import (
    TestRunAssignmentInput as RunAssignmentInput,
    TestRunCreate as RunCreate,
)


class MemoryTransaction:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        self.session.transaction_open = True
        return self

    async def __aexit__(self, error_type, error, traceback):
        if error_type:
            self.session.pending.clear()
            self.session.rolled_back = True
            self.session.transaction_open = False
            return False
        self.session.committed.extend(self.session.pending)
        self.session.pending.clear()
        self.session.transaction_open = False


class MemorySession:
    def __init__(self):
        self.pending = []
        self.committed = []
        self.rolled_back = False
        self.transaction_open = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, error_type, error, traceback):
        return False

    def start_transaction(self):
        return MemoryTransaction(self)


class MemoryClient:
    def __init__(self, session):
        self.session = session

    async def start_session(self):
        return self.session


def _async_value(value):
    async def resolve(*args, **kwargs):
        return value

    return resolve


def test_idempotency_key_requires_same_run_context_and_scope():
    payload = RunCreate(
        project_id="project-a",
        name="Run A",
        test_plan_id="plan-a",
        test_suite_ids=["suite-a", "suite-a"],
        test_case_version_ids=["version-a"],
        assignment_strategy="CONFIRMED_SKILLS",
    )
    existing = {
        "name": "Run A",
        "test_plan_id": "plan-a",
        "test_suite_ids": ["suite-a"],
        "test_case_version_ids": ["version-a"],
        "assignment_strategy": "CONFIRMED_SKILLS",
        "release_id": "release-a",
        "build_id": None,
        "environment_id": "env-a",
    }
    context = {
        "release_id": "release-a",
        "build_id": None,
        "environment_id": "env-a",
    }

    assert service._idempotent_run_matches(existing, payload, ["version-a"], context)
    assert service._idempotent_run_matches(
        {**existing, "test_suite_ids": ["suite-a", "suite-a"]},
        payload,
        ["version-a"],
        context,
    )
    assert not service._idempotent_run_matches(existing, payload, ["version-b"], context)
    assert not service._idempotent_run_matches(
        {**existing, "environment_id": "env-b"}, payload, ["version-a"], context
    )


def test_approved_test_plan_snapshot_must_match_its_stored_hash():
    plan = {
        "_id": "plan-a",
        "project_id": "project-a",
        "status": "APPROVED",
        "name": "Kế hoạch đã duyệt",
        "test_case_version_ids": ["version-a"],
        "requirement_version_ids": ["requirement-v1"],
    }
    snapshot = plan_snapshot(plan)
    digest = plan_snapshot_hash(snapshot)
    approved = {
        **plan,
        "approved_snapshot": snapshot,
        "approved_snapshot_hash": digest,
        "baseline_hash": digest,
    }

    actual, actual_digest = verified_approved_plan_snapshot(approved, "project-a")

    assert actual == snapshot
    assert actual_digest == digest

    tampered = {**approved, "approved_snapshot": {**snapshot, "test_case_version_ids": ["version-b"]}}
    with pytest.raises(HTTPException) as raised:
        verified_approved_plan_snapshot(tampered, "project-a")
    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "TEST_PLAN_APPROVED_SNAPSHOT_INVALID"


def test_approved_test_plan_pins_test_set_revision_and_membership():
    plan = {
        "_id": "plan-a",
        "project_id": "project-a",
        "status": "APPROVED",
        "name": "Kế hoạch đã duyệt",
        "test_suite_ids": ["suite-a"],
        "test_suite_snapshots": [
            {
                "test_suite_id": "suite-a",
                "revision": 4,
                "test_case_version_ids": ["version-a", "version-b"],
            }
        ],
    }
    snapshot = plan_snapshot(plan)
    digest = plan_snapshot_hash(snapshot)
    approved = {
        **plan,
        "approved_snapshot": snapshot,
        "approved_snapshot_hash": digest,
        "baseline_hash": digest,
    }

    verified, _ = verified_approved_plan_snapshot(approved, "project-a")

    assert verified["test_suite_snapshots"] == plan["test_suite_snapshots"]
    assert service._plan_suite_versions(["suite-a"], verified) == ["version-a", "version-b"]
    tampered = {
        **approved,
        "approved_snapshot": {
            **snapshot,
            "test_suite_snapshots": [
                {
                    **snapshot["test_suite_snapshots"][0],
                    "test_case_version_ids": ["version-c"],
                }
            ],
        },
    }
    with pytest.raises(HTTPException) as raised:
        verified_approved_plan_snapshot(tampered, "project-a")
    assert raised.value.detail["code"] == "TEST_PLAN_APPROVED_SNAPSHOT_INVALID"


def test_test_run_plan_suite_snapshot_rejects_unknown_or_malformed_scope():
    snapshot = {
        "test_suite_snapshots": [
            {
                "test_suite_id": "suite-a",
                "revision": 2,
                "test_case_version_ids": ["version-a"],
            }
        ]
    }
    assert service._plan_suite_versions(["suite-a"], snapshot) == ["version-a"]
    with pytest.raises(HTTPException) as raised:
        service._plan_suite_versions(["suite-b"], snapshot)
    assert raised.value.detail["code"] == "TEST_RUN_SUITE_OUTSIDE_PLAN_SCOPE"
    with pytest.raises(HTTPException) as raised:
        service._plan_suite_versions(
            ["suite-a"], {"test_suite_snapshots": [{"test_suite_id": "suite-a"}]}
        )
    assert raised.value.detail["code"] == "TEST_PLAN_SUITE_SNAPSHOT_INVALID"


def test_legacy_plan_snapshot_is_accepted_only_when_baseline_matches_live_scope():
    legacy = {
        "_id": "plan-a",
        "project_id": "project-a",
        "status": "APPROVED",
        "test_case_version_ids": ["version-a"],
    }
    legacy["baseline_hash"] = _legacy_plan_snapshot_hash(legacy)

    snapshot, digest = verified_approved_plan_snapshot(legacy, "project-a")

    assert snapshot["test_case_version_ids"] == ["version-a"]
    assert digest == legacy["baseline_hash"]

    legacy["test_case_version_ids"] = ["version-b"]
    with pytest.raises(HTTPException) as raised:
        verified_approved_plan_snapshot(legacy, "project-a")
    assert raised.value.detail["code"] == "TEST_PLAN_APPROVED_SNAPSHOT_INVALID"


def test_run_creation_rechecks_plan_snapshot_inside_creation_transaction(monkeypatch):
    session, calls = _configure_create(monkeypatch, fail_after_partial_results=False)
    payload = RunCreate(
        project_id="project-a",
        name="Run theo scope đã duyệt",
        test_plan_id="plan-a",
    )
    plan = {
        "_id": "plan-a",
        "project_id": "project-a",
        "status": "APPROVED",
        "name": "Kế hoạch đã duyệt",
        "test_case_version_ids": ["version-a"],
    }
    snapshot = plan_snapshot(plan)
    digest = plan_snapshot_hash(snapshot)
    approved_plan = {
        **plan,
        "approved_snapshot": snapshot,
        "approved_snapshot_hash": digest,
        "baseline_hash": digest,
    }
    tampered_plan = {
        **approved_plan,
        "approved_snapshot": {**snapshot, "test_case_version_ids": ["version-b"]},
    }
    monkeypatch.setattr(
        service.test_run_repository,
        "find_plan",
        AsyncMock(side_effect=[approved_plan, tampered_plan]),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.create_test_run_record(payload, "project-a", SimpleNamespace(id="qa-a")))

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "TEST_PLAN_APPROVED_SNAPSHOT_INVALID"
    assert session.rolled_back is True
    assert session.committed == []
    assert calls == []


def _configure_create(monkeypatch, *, fail_after_partial_results):
    session = MemorySession()
    calls = []
    monkeypatch.setattr(service.database, "client", MemoryClient(session))
    monkeypatch.setattr(service, "get_project", _async_value(None))
    monkeypatch.setattr(
        service,
        "resolve_execution_context",
        _async_value(
            {
                "environment": "staging",
                "environment_id": None,
                "release": "",
                "release_id": None,
                "build": "",
                "build_id": None,
            }
        ),
    )
    monkeypatch.setattr(service, "validate_test_versions", _async_value(None))

    async def insert_run(value, *, session):
        calls.append(("run", session))
        session.pending.append(("run", value["_id"]))

    async def insert_results(values, *, session):
        calls.append(("results", session))
        session.pending.append(("result", values[0]["_id"]))
        if fail_after_partial_results:
            raise RuntimeError("synthetic failure after first execution result")

    async def audit(*args, session=None, **kwargs):
        calls.append(("audit", session))
        session.pending.append(("audit", args[2]))

    async def index(*args, **kwargs):
        calls.append(("index", None))

    monkeypatch.setattr(service.test_run_repository, "insert_run", insert_run)
    monkeypatch.setattr(service.test_run_repository, "insert_results", insert_results)
    monkeypatch.setattr(service, "audit", audit)
    monkeypatch.setattr(service, "index_artifact", index)
    return session, calls


def test_run_and_initial_results_roll_back_together_when_result_insert_fails(monkeypatch):
    session, calls = _configure_create(monkeypatch, fail_after_partial_results=True)
    payload = RunCreate(
        project_id="project-a",
        name="Run nguyên tử",
        test_case_version_ids=["version-a", "version-b"],
    )
    user = SimpleNamespace(id="qa-a")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        asyncio.run(service.create_test_run_record(payload, "project-a", user))

    assert session.rolled_back is True
    assert session.committed == []
    assert [name for name, _ in calls] == ["run", "results"]
    assert all(call_session is session for _, call_session in calls)
    assert not any(name == "index" for name, _ in calls)


def test_run_results_and_audit_commit_in_one_transaction_before_indexing(monkeypatch):
    session, calls = _configure_create(monkeypatch, fail_after_partial_results=False)
    payload = RunCreate(
        project_id="project-a",
        name="Run nguyên tử",
        test_case_version_ids=["version-a"],
    )
    user = SimpleNamespace(id="qa-a")

    run = asyncio.run(service.create_test_run_record(payload, "project-a", user))

    assert run["_id"].startswith("TRUN-")
    assert session.rolled_back is False
    assert [kind for kind, _ in session.committed] == ["run", "result", "audit"]
    assert [name for name, _ in calls] == ["run", "results", "audit", "index"]
    assert all(call_session is session for _, call_session in calls[:3])


def test_run_creation_pins_approved_plan_hash_and_requirement_versions(monkeypatch):
    session, calls = _configure_create(monkeypatch, fail_after_partial_results=False)
    payload = RunCreate(
        project_id="project-a",
        name="Run theo snapshot",
        test_plan_id="plan-a",
    )
    source_plan = {
        "_id": "plan-a",
        "project_id": "project-a",
        "status": "APPROVED",
        "test_case_version_ids": ["version-a"],
        "requirement_version_ids": ["requirement-v3", "requirement-v4"],
    }
    snapshot = plan_snapshot(source_plan)
    snapshot_hash = plan_snapshot_hash(snapshot)
    approved_plan = {
        **source_plan,
        "approved_snapshot": snapshot,
        "approved_snapshot_hash": snapshot_hash,
        "baseline_hash": snapshot_hash,
    }
    monkeypatch.setattr(
        service.test_run_repository,
        "find_plan",
        AsyncMock(return_value=approved_plan),
    )
    persisted = []

    async def insert_run(value, *, session):
        persisted.append(value.copy())
        session.pending.append(("run", value["_id"]))

    monkeypatch.setattr(service.test_run_repository, "insert_run", insert_run)

    run = asyncio.run(
        service.create_test_run_record(payload, "project-a", SimpleNamespace(id="qa-a"))
    )

    assert run["test_plan_snapshot_hash"] == snapshot_hash
    assert run["requirement_version_ids"] == ["requirement-v3", "requirement-v4"]
    assert persisted[0]["test_plan_snapshot_hash"] == snapshot_hash
    assert persisted[0]["requirement_version_ids"] == ["requirement-v3", "requirement-v4"]
    assert session.rolled_back is False
    assert [kind for kind, _ in session.committed] == ["run", "result", "audit"]


def test_confirmed_skill_assignment_uses_the_run_creation_transaction(monkeypatch):
    session, calls = _configure_create(monkeypatch, fail_after_partial_results=False)
    assignment_calls = []
    payload = RunCreate(
        project_id="project-a",
        name="Run có phân công theo kỹ năng",
        test_case_version_ids=["version-a"],
        assignment_strategy="CONFIRMED_SKILLS",
    )
    monkeypatch.setattr(
        service.test_run_repository,
        "list_versions",
        _async_value([{"_id": "version-a", "required_skills": ["API"]}]),
    )

    async def assign(project_id, versions, *, session):
        assert session.transaction_open is True
        assignment_calls.append((project_id, versions, session))
        return (
            {"version-a": "tester-a"},
            [],
            {"version-a": {"assignee_id": "tester-a", "skill_profile_revision": 4}},
        )

    async def fence(project_id, revisions, timestamp, *, session):
        assert session.transaction_open is True
        assignment_calls.append(("fence", project_id, revisions, session))
        return []

    monkeypatch.setattr(service, "automatically_assign_test_cases", assign)
    monkeypatch.setattr(service.skill_profile_repository, "fence_assignment_revisions", fence)

    run = asyncio.run(
        service.create_test_run_record(payload, "project-a", SimpleNamespace(id="qa-a"))
    )

    assert len(assignment_calls) == 2
    assert assignment_calls[0][0] == "project-a"
    assert assignment_calls[0][2] is session
    assert assignment_calls[1] == (
        "fence",
        "project-a",
        {"tester-a": 4},
        session,
    )
    assert run["test_case_assignments"] == {"version-a": "tester-a"}
    assert run["test_case_assignment_decisions"]["version-a"]["skill_profile_revision"] == 4
    assert [kind for kind, _ in session.committed] == ["run", "result", "audit"]


def _configure_assignment(monkeypatch, *, current_profile_revision):
    session = MemorySession()
    calls = []
    monkeypatch.setattr(service.database, "client", MemoryClient(session))
    monkeypatch.setattr(
        service,
        "get_project_entity",
        _async_value(
            {
                "_id": "run-a",
                "project_id": "project-a",
                "revision": 2,
                "assignee_id": None,
                "test_case_version_ids": ["version-a"],
                "test_case_assignments": {},
            }
        ),
    )
    monkeypatch.setattr(
        service.test_run_repository,
        "find_active_tester",
        _async_value({"user_id": "tester-a"}),
    )
    monkeypatch.setattr(service.test_run_repository, "count_active_testers", _async_value(1))

    async def fence_profiles(project_id, expected_revisions, timestamp, *, session):
        calls.append(("fence", project_id, expected_revisions, session))
        return [
            user_id
            for user_id, expected_revision in expected_revisions.items()
            if expected_revision != current_profile_revision
        ]

    async def patch(collection, entity_id, project_id, expected_revision, changes, *, session):
        assert session.transaction_open is True
        calls.append(("patch", session))
        session.pending.append(("run", changes))
        return {"_id": entity_id, "revision": expected_revision + 1, **changes}

    async def audit(*args, session=None, **kwargs):
        assert session.transaction_open is True
        calls.append(("audit", session))
        session.pending.append(("audit", args[2]))

    monkeypatch.setattr(
        service.skill_profile_repository,
        "fence_assignment_revisions",
        fence_profiles,
    )
    monkeypatch.setattr(service, "optimistic_patch", patch)
    monkeypatch.setattr(service, "audit", audit)
    return session, calls


def _assignment_payload(profile_revision=5):
    return RunAssignmentInput(
        expected_revision=2,
        assignee_id="tester-a",
        test_case_assignments={"version-a": "tester-a"},
        expected_skill_profile_revisions={"tester-a": profile_revision},
    )


def test_assignment_rejects_changed_skill_profile_and_rolls_back(monkeypatch):
    session, calls = _configure_assignment(monkeypatch, current_profile_revision=6)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            service.assign_test_run_record(
                "project-a", "run-a", _assignment_payload(5), SimpleNamespace(id="qa-a")
            )
        )

    assert error.value.status_code == 409
    assert error.value.detail == {
        "code": "SKILL_PROFILE_CHANGED_RECOMMEND_AGAIN",
        "user_ids": ["tester-a"],
    }
    assert session.rolled_back is True
    assert session.committed == []
    assert not any(name == "patch" for name, *_ in calls)


def test_assignment_and_audit_commit_when_skill_profile_revision_matches(monkeypatch):
    session, calls = _configure_assignment(monkeypatch, current_profile_revision=5)

    updated = asyncio.run(
        service.assign_test_run_record(
            "project-a", "run-a", _assignment_payload(), SimpleNamespace(id="qa-a")
        )
    )

    assert updated["revision"] == 3
    assert [kind for kind, _ in session.committed] == ["run", "audit"]
    assert [call[0] for call in calls] == ["fence", "patch", "audit"]


def test_run_patch_validates_the_new_test_plan_snapshot(monkeypatch):
    run = {
        "_id": "TRUN-existing",
        "project_id": "project-a",
        "status": "DRAFT",
        "test_plan_id": None,
        "test_case_version_ids": ["version-a"],
        "release_id": None,
        "build_id": None,
        "environment_id": None,
    }
    patched = []

    monkeypatch.setattr(service, "get_project_entity", _async_value(run))
    monkeypatch.setattr(
        service,
        "verified_approved_plan_snapshot",
        lambda plan, _project_id: (plan["approved_snapshot"], "plan-hash"),
    )
    monkeypatch.setattr(
        service.test_run_repository,
        "find_plan",
        _async_value(
            {
                "_id": "plan-new",
                "status": "APPROVED",
                "approved_snapshot": {
                    "test_case_version_ids": ["version-b"],
                    "release_id": None,
                    "build_id": None,
                    "environment_id": None,
                },
            }
        ),
    )

    async def patch(*args, **kwargs):
        patched.append((args, kwargs))
        return {**run, **kwargs["changes"]}

    monkeypatch.setattr(service, "optimistic_patch", patch)
    monkeypatch.setattr(service, "audit", _async_value(None))
    payload = SimpleNamespace(
        expected_revision=1,
        model_dump=lambda **kwargs: {"test_plan_id": "plan-new"},
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.update_test_run_record("project-a", "TRUN-existing", payload, SimpleNamespace(id="qa-a")))

    assert raised.value.status_code == 422
    assert raised.value.detail.get("code") == "TEST_RUN_OUTSIDE_PLAN_SCOPE"
    assert patched == []


def test_run_patch_accepts_new_plan_when_existing_scope_is_inside_snapshot(monkeypatch):
    run = {
        "_id": "TRUN-existing",
        "project_id": "project-a",
        "status": "DRAFT",
        "test_plan_id": None,
        "test_case_version_ids": ["version-a"],
        "release_id": None,
        "build_id": None,
        "environment_id": None,
    }
    patched = []
    monkeypatch.setattr(service, "get_project_entity", _async_value(run))
    monkeypatch.setattr(
        service,
        "verified_approved_plan_snapshot",
        lambda plan, _project_id: (plan["approved_snapshot"], "plan-hash"),
    )
    monkeypatch.setattr(
        service.test_run_repository,
        "find_plan",
        _async_value(
            {
                "_id": "plan-new",
                "status": "APPROVED",
                "approved_snapshot": {
                    "test_case_version_ids": ["version-a", "version-b"],
                    "requirement_version_ids": ["requirement-v3"],
                    "release_id": None,
                    "build_id": None,
                    "environment_id": None,
                },
            }
        ),
    )

    async def patch(*args, **kwargs):
        changes = args[4]
        patched.append(changes)
        return {**run, **changes}

    monkeypatch.setattr(service, "optimistic_patch", patch)
    monkeypatch.setattr(service, "audit", _async_value(None))
    payload = SimpleNamespace(
        expected_revision=1,
        model_dump=lambda **kwargs: {"test_plan_id": "plan-new"},
    )

    result = asyncio.run(
        service.update_test_run_record("project-a", "TRUN-existing", payload, SimpleNamespace(id="qa-a"))
    )

    assert result["test_plan_id"] == "plan-new"
    assert patched == [
        {
            "test_plan_id": "plan-new",
            "test_plan_snapshot_hash": "plan-hash",
            "requirement_version_ids": ["requirement-v3"],
        }
    ]


@pytest.mark.parametrize("replacement_plan_id", [None, "plan-other"])
def test_run_patch_cannot_detach_or_replace_an_existing_plan_binding(monkeypatch, replacement_plan_id):
    run = {
        "_id": "TRUN-existing",
        "project_id": "project-a",
        "status": "DRAFT",
        "test_plan_id": "plan-original",
        "test_case_version_ids": ["version-a"],
        "revision": 2,
    }
    monkeypatch.setattr(service, "get_project_entity", _async_value(run))
    payload = SimpleNamespace(
        expected_revision=2,
        model_dump=lambda **kwargs: {"test_plan_id": replacement_plan_id},
    )
    patched = []
    monkeypatch.setattr(service, "optimistic_patch", lambda *args, **kwargs: patched.append(args))

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            service.update_test_run_record(
                "project-a", "TRUN-existing", payload, SimpleNamespace(id="qa-a")
            )
        )

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "TEST_RUN_PLAN_BINDING_FROZEN"
    assert patched == []


def test_frozen_run_scope_captures_the_exact_plan_and_requirement_versions():
    run = {
        "test_plan_id": "plan-a",
        "test_plan_snapshot_hash": "approved-plan-hash",
        "requirement_version_ids": ["requirement-v3", "requirement-v4"],
        "test_case_version_ids": ["case-v2"],
    }

    scope = frozen_run_scope(run)

    assert scope["test_plan_snapshot_hash"] == "approved-plan-hash"
    assert scope["requirement_version_ids"] == ["requirement-v3", "requirement-v4"]


@pytest.mark.parametrize(
    ("changed_field", "changed_value"),
    [("name", "Tên khác"), ("test_suite_ids", ["suite-other"])],
)
def test_run_idempotency_rejects_key_reuse_for_changed_payload(monkeypatch, changed_field, changed_value):
    existing = {
        "_id": "TRUN-existing",
        "name": "Run hiện tại",
        "test_plan_id": None,
        "test_suite_ids": ["suite-a"],
        "test_case_version_ids": ["version-a"],
        "assignment_strategy": "MANUAL",
        "release_id": None,
        "build_id": None,
        "environment_id": None,
    }
    payload_values = {
        "project_id": "project-a",
        "idempotency_key": "same-key-123",
        "name": existing["name"],
        "test_plan_id": None,
        "test_suite_ids": list(existing["test_suite_ids"]),
        "test_case_version_ids": list(existing["test_case_version_ids"]),
        "assignment_strategy": "MANUAL",
        "release_id": None,
        "build_id": None,
        "environment_id": None,
    }
    payload_values[changed_field] = changed_value
    payload = RunCreate(**payload_values)
    monkeypatch.setattr(service, "get_project", _async_value(None))
    monkeypatch.setattr(
        service,
        "resolve_execution_context",
        _async_value(
            {
                "environment": "staging",
                "environment_id": None,
                "release": "",
                "release_id": None,
                "build": "",
                "build_id": None,
            }
        ),
    )
    monkeypatch.setattr(service, "validate_test_versions", _async_value(None))
    monkeypatch.setattr(
        service.test_run_repository,
        "list_suites",
        _async_value(
            [
                {"_id": suite_id, "test_case_version_ids": ["version-a"]}
                for suite_id in payload.test_suite_ids
            ]
        ),
    )
    monkeypatch.setattr(
        service.test_run_repository,
        "find_run_by_idempotency_key",
        _async_value(existing),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.create_test_run_record(payload, "project-a", SimpleNamespace(id="qa-a")))

    assert raised.value.status_code == 409
    assert raised.value.detail.get("code") == "IDEMPOTENCY_KEY_REUSED"


def test_test_run_cannot_select_a_test_set_outside_the_approved_plan_snapshot():
    snapshot = {"test_suite_ids": ["suite-approved"]}

    with pytest.raises(HTTPException) as raised:
        service._validate_plan_suite_scope(["suite-other"], snapshot)

    assert raised.value.status_code == 422
    assert raised.value.detail == {"code": "TEST_RUN_SUITE_OUTSIDE_PLAN_SCOPE"}


def test_test_run_can_select_a_subset_of_test_sets_in_the_approved_plan_snapshot():
    service._validate_plan_suite_scope(
        ["suite-approved"], {"test_suite_ids": ["suite-approved", "suite-also-approved"]}
    )


def test_test_plan_scope_snapshots_selected_test_set_revision_and_membership(monkeypatch):
    monkeypatch.setattr(
        test_plan_service.test_plan_repository,
        "count_requirement_versions",
        AsyncMock(return_value=0),
    )
    monkeypatch.setattr(
        test_plan_service.test_plan_repository,
        "list_suites",
        AsyncMock(return_value=[
            {
                "_id": "suite-a",
                "revision": 7,
                "test_case_version_ids": ["version-a", "version-a", "version-b"],
            }
        ]),
    )
    monkeypatch.setattr(
        test_plan_service.test_plan_repository,
        "count_test_case_versions",
        AsyncMock(return_value=2),
    )

    scope = asyncio.run(
        test_plan_service.validate_plan_scope("project-a", [], ["suite-a"], [])
    )

    assert scope["test_suite_snapshots"] == [
        {
            "test_suite_id": "suite-a",
            "revision": 7,
            "test_case_version_ids": ["version-a", "version-b"],
        }
    ]
    assert scope["test_case_version_ids"] == ["version-a", "version-b"]

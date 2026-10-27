import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.modules.execution.services import execution_context as service
from src.modules.design.services.test_adequacy import coverage_item_ready_for_assurance
from src.repositories import execution_context as repository
from src.schemas.test_completion import completion_hash, completion_snapshot
from src.schemas.test_monitoring import source_fingerprint
from src.modules.execution.services.test_plan import plan_snapshot, plan_snapshot_hash

_LIVE_RELEASE_SNAPSHOT_SOURCES_CHANGED = (
    repository.execution_context_repository.release_snapshot_sources_changed
)


def _async_value(value):
    async def resolve(*args, **kwargs):
        return value

    return resolve


@pytest.fixture(autouse=True)
def _default_snapshot_source_check(monkeypatch):
    monkeypatch.setattr(
        service.execution_context_repository,
        "release_snapshot_sources_changed",
        _async_value(False),
    )


def _configure_gate(monkeypatch, assessment):
    plan = {
        "_id": "plan-a",
        "project_id": "project-a",
        "release_id": "release-a",
        "status": "APPROVED",
        "requirement_version_ids": ["requirement-version-a"],
    }
    snapshot = plan_snapshot(plan)
    plan_hash = plan_snapshot_hash(snapshot)
    plan.update(
        {
            "approved_snapshot": snapshot,
            "approved_snapshot_hash": plan_hash,
            "baseline_hash": plan_hash,
        }
    )
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_approved_test_plan_scopes",
        _async_value([plan]),
    )
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_adequacy_assessments",
        _async_value([assessment]),
    )
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_active_member_ids",
        _async_value(["owner-1"]),
    )
    monkeypatch.setattr(
        service,
        "now",
        lambda: datetime(2026, 10, 24, tzinfo=timezone.utc),
    )


def _configure_approved_completion(monkeypatch, report, plan_ids=("plan-a",)):
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_approved_test_plan_scopes",
        _async_value([{"_id": plan_id} for plan_id in plan_ids]),
    )
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_approved_completions",
        _async_value([report]),
    )


def _verified_item():
    return {
        "coverage_item_id": "obligation-a",
        "requirement_version_id": "requirement-version-a",
        "source_type": "acceptance_criterion",
        "source_id": "criterion-a",
        "source_ref": "AC-1",
        "source_quote": "A valid source quote",
        "status": "VERIFIED_COVERED",
        "test_case_versions": [
            {
                "assurance_evidence_complete": True,
                "requirement_version_ids": ["requirement-version-a"],
                "acceptance_criterion_ids": ["criterion-a"],
                "evidence_refs": ["criterion-a"],
                "evidence_quotes": [
                    {"evidence_ref": "criterion-a", "quote": "A valid source quote"}
                ],
                "techniques": ["BOUNDARY_VALUE"],
            }
        ],
    }


class _Cursor:
    def __init__(self, values):
        self.values = values

    async def to_list(self, limit):
        return self.values[:limit]


class _Collection:
    def __init__(self, values):
        self.values = values

    async def find_one(self, query, *args, **kwargs):
        return next((item for item in self.values if _matches(item, query)), None)

    def find(self, query, *args, **kwargs):
        return _Cursor([item for item in self.values if _matches(item, query)])


def _matches(item, query):
    for field, expected in query.items():
        actual = item.get(field)
        if isinstance(expected, dict) and "$in" in expected:
            if actual not in expected["$in"]:
                return False
        elif actual != expected:
            return False
    return True


def _snapshot_database():
    source_state = {
        "plan": {"id": "plan-a", "revision": 3, "hash": "plan-hash"},
        "runs": [
            {
                "id": "run-a",
                "revision": 4,
                "scope_hash": "scope-hash",
                "status": "COMPLETED",
            }
        ],
        "results": [{"id": "result-a", "revision": 2, "status": "PASS"}],
        "defects": [],
        "conditions": [],
        "nfr_plans": [],
        "environment_incidents": [],
        "requirements": ["requirement-version-a"],
        "acceptance_criteria": ["criterion-a"],
        "api_operations": ["operation-a"],
    }
    snapshot = {
        "_id": "snapshot-a",
        "project_id": "project-a",
        "release_id": "release-a",
        "test_plan_id": "plan-a",
        "source_state": source_state,
        "source_fingerprint": source_fingerprint(source_state),
    }
    collections = {
        "test_monitoring_snapshots": [snapshot],
        "test_plans": [
            {
                "_id": "plan-a",
                "project_id": "project-a",
                "release_id": "release-a",
                "revision": 3,
                "approved_snapshot_hash": "plan-hash",
                "approved_snapshot": {"requirement_version_ids": ["requirement-version-a"]},
            }
        ],
        "test_runs": [
            {
                "_id": "run-a",
                "project_id": "project-a",
                "revision": 4,
                "frozen_scope_hash": "scope-hash",
                "status": "COMPLETED",
            }
        ],
        "test_results": [
            {"_id": "result-a", "project_id": "project-a", "revision": 2, "status": "PASS"}
        ],
        "defects": [],
        "test_conditions": [],
        "non_functional_test_plans": [],
        "environment_incidents": [],
        "requirement_versions": [
            {"_id": "requirement-version-a", "project_id": "project-a", "requirement_id": "requirement-a"}
        ],
        "requirements": [
            {
                "_id": "requirement-a",
                "project_id": "project-a",
                "status": "BASELINED",
                "current_version_id": "requirement-version-a",
            }
        ],
        "acceptance_criteria": [
            {"_id": "criterion-a", "project_id": "project-a", "requirement_version_id": "requirement-version-a"}
        ],
        "api_operations": [{"_id": "operation-a", "project_id": "project-a"}],
    }
    return SimpleNamespace(
        **{name: _Collection(values) for name, values in collections.items()}
    )
def test_release_assurance_gate_rejects_tampered_or_wrong_release_plan_snapshot(monkeypatch):
    plan = {
        "_id": "plan-a",
        "project_id": "project-a",
        "release_id": "release-a",
        "status": "APPROVED",
        "requirement_version_ids": ["requirement-version-a"],
    }
    snapshot = plan_snapshot(plan)
    digest = plan_snapshot_hash(snapshot)
    plan.update(
        {
            "approved_snapshot": {**snapshot, "release_id": "release-b"},
            "approved_snapshot_hash": digest,
            "baseline_hash": digest,
        }
    )
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_approved_test_plan_scopes",
        _async_value([plan]),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_assurance_gate("project-a", "release-a"))

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "RELEASE_TEST_PLAN_SNAPSHOT_INVALID"
    assert raised.value.detail["test_plan_ids"] == ["plan-a"]


def test_release_assurance_gate_rejects_unresolved_item_inside_assured_snapshot(monkeypatch):
    _configure_gate(
        monkeypatch,
        {
            "requirement_version_id": "requirement-version-a",
            "status": "ASSURED",
            "coverage_items": [
                {"coverage_item_id": "obligation-a", "status": "UNASSESSED"}
            ],
        },
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_assurance_gate("project-a", "release-a"))

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED"


def test_release_completion_gate_requires_intact_qa_approved_snapshot(monkeypatch):
    report = {
        "_id": "completion-a",
        "project_id": "project-a",
        "release_id": "release-a",
        "status": "APPROVED",
        "approved_by": "qa-a",
        "approved_at": datetime(2026, 10, 24, tzinfo=timezone.utc),
        "sign_offs": [{"role": "QA", "decision": "APPROVE"}],
        "defect_summary": {"open_blocker": 0},
        "test_plan_id": "plan-a",
        "monitoring_snapshot_id": "snapshot-a",
        "scope_snapshot": {"runs": []},
        "exit_criteria_evaluations": [{"criterion_id": "exit-a", "status": "PASS"}],
        "recommendation": "READY_FOR_RELEASE",
    }
    report["approved_snapshot"] = completion_snapshot(report)
    report["approved_snapshot_hash"] = completion_hash(report)
    _configure_approved_completion(monkeypatch, report)
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_open_blocking_defects",
        _async_value([]),
    )
    monkeypatch.setattr(
        service.execution_context_repository,
        "release_evidence_changed_since",
        _async_value(False),
    )

    assert asyncio.run(service.ensure_release_completion_gate("project-a", "release-a"))


def test_release_completion_gate_requires_a_report_for_every_approved_plan(monkeypatch):
    report = {
        "_id": "completion-a",
        "project_id": "project-a",
        "release_id": "release-a",
        "status": "APPROVED",
        "test_plan_id": "plan-a",
    }
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_approved_test_plan_scopes",
        _async_value([{"_id": "plan-a"}, {"_id": "plan-b"}]),
    )
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_approved_completions",
        _async_value([report]),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_completion_gate("project-a", "release-a"))

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "RELEASE_COMPLETION_GATE_FAILED"
    assert raised.value.detail["reason_code"] == "COMPLETION_PLAN_REPORT_SCOPE_INCOMPLETE"
    assert raised.value.detail["test_plan_ids"] == ["plan-b"]


def test_release_completion_gate_rejects_report_mutated_after_approval(monkeypatch):
    report = {
        "_id": "completion-a",
        "project_id": "project-a",
        "release_id": "release-a",
        "status": "APPROVED",
        "approved_by": "qa-a",
        "approved_at": datetime(2026, 10, 24, tzinfo=timezone.utc),
        "sign_offs": [{"role": "QA", "decision": "APPROVE"}],
        "defect_summary": {"open_blocker": 0},
        "test_plan_id": "plan-a",
        "monitoring_snapshot_id": "snapshot-a",
        "scope_snapshot": {"runs": []},
    }
    report["approved_snapshot"] = completion_snapshot(report)
    report["approved_snapshot_hash"] = completion_hash(report)
    report["defect_summary"] = {"open_blocker": 1}
    _configure_approved_completion(monkeypatch, report)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_completion_gate("project-a", "release-a"))

    assert raised.value.detail["reason_code"] == "APPROVED_COMPLETION_SNAPSHOT_INVALID"


def test_release_completion_gate_rejects_blocker_added_after_report_approval(monkeypatch):
    report = {
        "_id": "completion-a",
        "project_id": "project-a",
        "release_id": "release-a",
        "status": "APPROVED",
        "approved_by": "qa-a",
        "approved_at": datetime(2026, 10, 24, tzinfo=timezone.utc),
        "sign_offs": [{"role": "QA", "decision": "APPROVE"}],
        "defect_summary": {"open_blocker": 0},
        "test_plan_id": "plan-a",
        "monitoring_snapshot_id": "snapshot-a",
        "scope_snapshot": {"runs": [{"run_id": "run-a"}]},
        "exit_criteria_evaluations": [{"criterion_id": "exit-a", "status": "PASS"}],
        "recommendation": "READY_FOR_RELEASE",
    }
    report["approved_snapshot"] = completion_snapshot(report)
    report["approved_snapshot_hash"] = completion_hash(report)
    _configure_approved_completion(monkeypatch, report)
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_open_blocking_defects",
        _async_value([{"_id": "defect-new", "severity": "BLOCKER"}]),
    )
    monkeypatch.setattr(
        service.execution_context_repository,
        "release_evidence_changed_since",
        _async_value(False),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_completion_gate("project-a", "release-a"))

    assert raised.value.detail["reason_code"] == "OPEN_BLOCKING_DEFECTS"


def test_release_completion_gate_rejects_report_stale_after_execution_change(monkeypatch):
    report = {
        "_id": "completion-a",
        "project_id": "project-a",
        "release_id": "release-a",
        "status": "APPROVED",
        "approved_by": "qa-a",
        "approved_at": datetime(2026, 10, 24, tzinfo=timezone.utc),
        "sign_offs": [{"role": "QA", "decision": "APPROVE"}],
        "defect_summary": {"open_blocker": 0},
        "test_plan_id": "plan-a",
        "monitoring_snapshot_id": "snapshot-a",
        "scope_snapshot": {"runs": [{"run_id": "run-a"}]},
        "exit_criteria_evaluations": [{"criterion_id": "exit-a", "status": "PASS"}],
        "recommendation": "READY_FOR_RELEASE",
    }
    report["approved_snapshot"] = completion_snapshot(report)
    report["approved_snapshot_hash"] = completion_hash(report)
    _configure_approved_completion(monkeypatch, report)
    monkeypatch.setattr(
        service.execution_context_repository,
        "release_evidence_changed_since",
        _async_value(True),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_completion_gate("project-a", "release-a"))

    assert raised.value.detail["reason_code"] == "COMPLETION_REPORT_STALE"


def test_release_completion_gate_rejects_revision_change_even_when_timestamp_check_is_clean(monkeypatch):
    report = {
        "_id": "completion-a",
        "project_id": "project-a",
        "release_id": "release-a",
        "status": "APPROVED",
        "approved_by": "qa-a",
        "approved_at": datetime(2026, 10, 24, tzinfo=timezone.utc),
        "sign_offs": [{"role": "QA", "decision": "APPROVE"}],
        "defect_summary": {"open_blocker": 0},
        "test_plan_id": "plan-a",
        "monitoring_snapshot_id": "snapshot-a",
        "scope_snapshot": {"runs": [{"run_id": "run-a"}]},
        "exit_criteria_evaluations": [{"criterion_id": "exit-a", "status": "PASS"}],
        "recommendation": "READY_FOR_RELEASE",
    }
    report["approved_snapshot"] = completion_snapshot(report)
    report["approved_snapshot_hash"] = completion_hash(report)
    _configure_approved_completion(monkeypatch, report)
    monkeypatch.setattr(
        service.execution_context_repository,
        "release_snapshot_sources_changed",
        _async_value(True),
    )
    monkeypatch.setattr(
        service.execution_context_repository,
        "release_evidence_changed_since",
        _async_value(False),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_completion_gate("project-a", "release-a"))

    assert raised.value.detail["reason_code"] == "COMPLETION_REPORT_STALE"


def test_release_snapshot_sources_match_exact_saved_revisions(monkeypatch):
    fake_database = _snapshot_database()
    monkeypatch.setattr(repository, "database", SimpleNamespace(value=fake_database))

    assert not asyncio.run(
        repository.execution_context_repository.release_snapshot_sources_changed(
            "project-a", "snapshot-a", "release-a", "plan-a", ["run-a"]
        )
    )


def test_release_snapshot_sources_detect_same_timestamp_revision_change(monkeypatch):
    fake_database = _snapshot_database()
    fake_database.test_results.values[0]["revision"] = 3
    monkeypatch.setattr(repository, "database", SimpleNamespace(value=fake_database))
    monkeypatch.setattr(
        repository.execution_context_repository,
        "release_snapshot_sources_changed",
        _LIVE_RELEASE_SNAPSHOT_SOURCES_CHANGED,
    )

    assert asyncio.run(
        repository.execution_context_repository.release_snapshot_sources_changed(
            "project-a", "snapshot-a", "release-a", "plan-a", ["run-a"]
        )
    )


def test_release_snapshot_sources_reject_tampered_fingerprint(monkeypatch):
    fake_database = _snapshot_database()
    fake_database.test_monitoring_snapshots.values[0]["source_fingerprint"] = "tampered"
    monkeypatch.setattr(repository, "database", SimpleNamespace(value=fake_database))
    monkeypatch.setattr(
        repository.execution_context_repository,
        "release_snapshot_sources_changed",
        _LIVE_RELEASE_SNAPSHOT_SOURCES_CHANGED,
    )

    assert asyncio.run(
        repository.execution_context_repository.release_snapshot_sources_changed(
            "project-a", "snapshot-a", "release-a", "plan-a", ["run-a"]
        )
    )


def test_release_assurance_gate_rejects_conditional_status_without_live_waiver(monkeypatch):
    _configure_gate(
        monkeypatch,
        {
            "requirement_version_id": "requirement-version-a",
            "status": "CONDITIONAL",
            "coverage_items": [
                {"coverage_item_id": "obligation-a", "status": "VERIFIED_COVERED"}
            ],
        },
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_assurance_gate("project-a", "release-a"))

    assert raised.value.detail["code"] == "RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED"


def test_release_assurance_gate_accepts_only_live_waivers_for_conditional_scope(monkeypatch):
    _configure_gate(
        monkeypatch,
        {
            "requirement_version_id": "requirement-version-a",
            "status": "CONDITIONAL",
            "coverage_items": [
                _verified_item(),
                {
                    "coverage_item_id": "obligation-b",
                    "requirement_version_id": "requirement-version-a",
                    "source_type": "business_rule",
                    "source_id": "rule-2",
                    "source_ref": "business_rule:2",
                    "source_quote": "A waived source quote",
                    "status": "WAIVED",
                    "owner_id": "owner-1",
                    "decision": {
                        "waiver_expires_at": "2026-10-25T00:00:00Z",
                        "waiver_review_at": "2026-10-24T00:00:00Z",
                        "waiver_owner_id": "owner-1",
                        "reason": "Accepted for this release",
                        "decided_by": "qa-1",
                        "decided_at": "2026-10-23T00:00:00Z",
                    },
                },
            ],
        },
    )

    assert asyncio.run(service.ensure_release_assurance_gate("project-a", "release-a")) == 1


def test_release_assurance_gate_fails_closed_for_malformed_waiver_expiry(monkeypatch):
    _configure_gate(
        monkeypatch,
        {
            "requirement_version_id": "requirement-version-a",
            "status": "CONDITIONAL",
            "coverage_items": [
                {
                    "coverage_item_id": "obligation-a",
                    "requirement_version_id": "requirement-version-a",
                    "status": "WAIVED",
                    "decision": {"waiver_expires_at": "not-a-date"},
                }
            ],
        },
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_assurance_gate("project-a", "release-a"))

    assert raised.value.detail["code"] == "RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED"


def test_release_assurance_gate_rejects_waiver_with_inactive_owner(monkeypatch):
    _configure_gate(
        monkeypatch,
        {
            "requirement_version_id": "requirement-version-a",
            "status": "CONDITIONAL",
            "coverage_items": [
                {
                    "coverage_item_id": "obligation-a",
                    "requirement_version_id": "requirement-version-a",
                    "source_type": "business_rule",
                    "source_id": "0",
                    "source_ref": "business_rule:1",
                    "source_quote": "A waived source quote",
                    "status": "WAIVED",
                    "owner_id": "owner-1",
                    "decision": {
                        "waiver_expires_at": "2026-10-25T00:00:00Z",
                        "waiver_review_at": "2026-10-24T00:00:00Z",
                        "waiver_owner_id": "owner-1",
                        "reason": "Accepted for this release",
                        "decided_by": "qa-1",
                        "decided_at": "2026-10-23T00:00:00Z",
                    },
                }
            ],
        },
    )
    monkeypatch.setattr(
        service.execution_context_repository,
        "list_active_member_ids",
        _async_value([]),
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_assurance_gate("project-a", "release-a"))

    assert raised.value.detail["code"] == "RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED"


def test_coverage_item_requires_case_quote_from_its_source():
    item = {
        **_verified_item(),
        "test_case_versions": [
            {
                "assurance_evidence_complete": True,
                "requirement_version_ids": ["requirement-version-a"],
                "acceptance_criterion_ids": ["criterion-a"],
                "evidence_refs": ["criterion-a"],
                "evidence_quotes": [
                    {"evidence_ref": "criterion-a", "quote": "Unrelated requirement text"}
                ],
                "techniques": ["BOUNDARY_VALUE"],
            }
        ],
    }

    assert not coverage_item_ready_for_assurance(
        item, datetime(2026, 10, 24, tzinfo=timezone.utc)
    )


def test_coverage_item_accepts_case_quoting_its_source_and_mapping():
    assert coverage_item_ready_for_assurance(
        _verified_item(), datetime(2026, 10, 24, tzinfo=timezone.utc)
    )


def test_release_assurance_gate_rejects_assured_snapshot_with_no_obligations(monkeypatch):
    _configure_gate(
        monkeypatch,
        {
            "requirement_version_id": "requirement-version-a",
            "status": "ASSURED",
            "coverage_items": [],
        },
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_assurance_gate("project-a", "release-a"))

    assert raised.value.detail["code"] == "RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED"


def test_release_assurance_gate_rejects_duplicate_obligation_ids(monkeypatch):
    _configure_gate(
        monkeypatch,
        {
            "requirement_version_id": "requirement-version-a",
            "status": "ASSURED",
            "coverage_items": [_verified_item(), _verified_item()],
        },
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.ensure_release_assurance_gate("project-a", "release-a"))

    assert raised.value.detail["code"] == "RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED"


def test_release_assurance_gate_rejects_assessment_updated_after_approved_report(monkeypatch):
    _configure_gate(
        monkeypatch,
        {
            "requirement_version_id": "requirement-version-a",
            "status": "ASSURED",
            "updated_at": datetime(2026, 10, 25, tzinfo=timezone.utc),
            "coverage_items": [_verified_item()],
        },
    )

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            service.ensure_release_assurance_gate(
                "project-a",
                "release-a",
                completion_approved_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
            )
        )

    assert raised.value.detail["code"] == "RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED"


class _AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Session(_AsyncContext):
    def start_transaction(self):
        return _AsyncContext()


def test_release_gates_and_close_audit_share_transaction_session():
    async def run():
        session = _Session()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        user = SimpleNamespace(id="qa-1")
        release = {"_id": "release-a", "project_id": "project-a", "status": "ACTIVE"}
        updated = {**release, "status": "CLOSED"}
        with (
            patch.object(service, "database", SimpleNamespace(client=client)),
            patch.object(service, "get_project_entity", new=AsyncMock(return_value=release)),
            patch.object(service, "ensure_release_completion_gate", new=AsyncMock(return_value=True)) as completion,
            patch.object(service, "ensure_release_assurance_gate", new=AsyncMock(return_value=2)) as assurance,
            patch.object(service, "serialize_release_gate", new=AsyncMock()) as serialize_gate,
            patch.object(service, "optimistic_patch", new=AsyncMock(return_value=updated)) as patch_release,
            patch.object(service, "audit", new=AsyncMock()) as audit,
            patch("src.clients.ai_automation.emit_release_changed", new=AsyncMock()) as emit,
        ):
            result = await service.ExecutionContextService.transition_release(
                "release-a",
                SimpleNamespace(expected_revision=3, reason="Đủ điều kiện phát hành"),
                user,
                "close",
            )

        assert result["status"] == "CLOSED"
        assert serialize_gate.await_args.args[2] is session
        assert completion.await_args.kwargs["session"] is session
        assert assurance.await_args.kwargs["session"] is session
        assert patch_release.await_args.kwargs["session"] is session
        assert audit.await_args.kwargs["session"] is session
        assert audit.await_args.args[1] == "release_closed_after_completion"
        assert emit.await_args.kwargs["session"] is session

    asyncio.run(run())


def test_invalid_test_plan_snapshot_blocks_close_and_is_audited_after_rollback():
    async def reject_snapshot(*args, **kwargs):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RELEASE_TEST_PLAN_SNAPSHOT_INVALID",
                "test_plan_ids": ["plan-a"],
            },
        )

    async def run():
        session = _Session()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        user = SimpleNamespace(id="qa-1")
        release = {"_id": "release-a", "project_id": "project-a", "status": "ACTIVE"}
        with (
            patch.object(service, "database", SimpleNamespace(client=client)),
            patch.object(service, "get_project_entity", new=AsyncMock(return_value=release)),
            patch.object(service, "ensure_release_completion_gate", new=AsyncMock(return_value={"approved_at": service.now()})),
            patch.object(service, "ensure_release_assurance_gate", new=reject_snapshot),
            patch.object(service, "serialize_release_gate", new=AsyncMock()),
            patch.object(service, "optimistic_patch", new=AsyncMock()) as patch_release,
            patch.object(service, "audit", new=AsyncMock()) as audit,
            patch("src.clients.ai_automation.emit_release_changed", new=AsyncMock()) as emit,
        ):
            with pytest.raises(HTTPException) as raised:
                await service.ExecutionContextService.transition_release(
                    "release-a",
                    SimpleNamespace(expected_revision=3, reason="Kiểm tra gate"),
                    user,
                    "close",
                )

        assert raised.value.detail["code"] == "RELEASE_TEST_PLAN_SNAPSHOT_INVALID"
        patch_release.assert_not_awaited()
        emit.assert_not_awaited()
        audit.assert_awaited_once_with(
            user.id,
            "release_close_blocked",
            "Release",
            "release-a",
            "project-a",
            {"reason": "Kiểm tra gate", "gate_code": "RELEASE_TEST_PLAN_SNAPSHOT_INVALID"},
        )

    asyncio.run(run())


def test_concurrent_release_gate_change_blocks_close_and_records_conflict():
    async def reject_gate_revision(*args, **kwargs):
        raise HTTPException(
            status_code=409,
            detail={"code": "RELEASE_GATE_REVISION_CONFLICT", "release_id": "release-a"},
        )

    async def run():
        session = _Session()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        user = SimpleNamespace(id="qa-1")
        release = {
            "_id": "release-a",
            "project_id": "project-a",
            "status": "ACTIVE",
            "gate_revision": 7,
        }
        with (
            patch.object(service, "database", SimpleNamespace(client=client)),
            patch.object(service, "get_project_entity", new=AsyncMock(return_value=release)),
            patch.object(service, "serialize_release_gate", new=reject_gate_revision),
            patch.object(service, "ensure_release_completion_gate", new=AsyncMock()) as completion,
            patch.object(service, "optimistic_patch", new=AsyncMock()) as patch_release,
            patch.object(service, "audit", new=AsyncMock()) as audit,
            patch("src.clients.ai_automation.emit_release_changed", new=AsyncMock()) as emit,
        ):
            with pytest.raises(HTTPException) as raised:
                await service.ExecutionContextService.transition_release(
                    "release-a",
                    SimpleNamespace(expected_revision=3, reason="Gate changed concurrently"),
                    user,
                    "close",
                )

        assert raised.value.detail["code"] == "RELEASE_GATE_REVISION_CONFLICT"
        completion.assert_not_awaited()
        patch_release.assert_not_awaited()
        emit.assert_not_awaited()
        audit.assert_awaited_once_with(
            user.id,
            "release_close_blocked",
            "Release",
            "release-a",
            "project-a",
            {"reason": "Gate changed concurrently", "gate_code": "RELEASE_GATE_REVISION_CONFLICT"},
        )

    asyncio.run(run())


def test_stale_release_revision_does_not_close_and_is_audited_as_conflict():
    async def reject_release_revision(*args, **kwargs):
        raise HTTPException(
            status_code=409,
            detail={"code": "REVISION_CONFLICT", "current_revision": 8},
        )

    async def run():
        session = _Session()
        client = SimpleNamespace(start_session=AsyncMock(return_value=session))
        user = SimpleNamespace(id="qa-1")
        release = {
            "_id": "release-a",
            "project_id": "project-a",
            "status": "ACTIVE",
            "gate_revision": 2,
        }
        with (
            patch.object(service, "database", SimpleNamespace(client=client)),
            patch.object(service, "get_project_entity", new=AsyncMock(return_value=release)),
            patch.object(service, "serialize_release_gate", new=AsyncMock()),
            patch.object(service, "ensure_release_completion_gate", new=AsyncMock(return_value={"approved_at": service.now()})),
            patch.object(service, "ensure_release_assurance_gate", new=AsyncMock(return_value=1)),
            patch.object(service, "optimistic_patch", new=reject_release_revision),
            patch.object(service, "audit", new=AsyncMock()) as audit,
            patch("src.clients.ai_automation.emit_release_changed", new=AsyncMock()) as emit,
        ):
            with pytest.raises(HTTPException) as raised:
                await service.ExecutionContextService.transition_release(
                    "release-a",
                    SimpleNamespace(expected_revision=2, reason="Concurrent release edit"),
                    user,
                    "close",
                )

        assert raised.value.detail["code"] == "REVISION_CONFLICT"
        emit.assert_not_awaited()
        audit.assert_awaited_once_with(
            user.id,
            "release_close_blocked",
            "Release",
            "release-a",
            "project-a",
            {"reason": "Concurrent release edit", "gate_code": "REVISION_CONFLICT"},
        )

    asyncio.run(run())

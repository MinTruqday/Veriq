import pytest
from fastapi import HTTPException

from src.modules.execution.services.test_run_execution import (
    _idempotency_fingerprint,
    _stored_result_matches_request,
    _verify_idempotency_replay,
)
from src.schemas.contracts.execution import (
    TestExecutionPatch as ExecutionPatch,
    TestResultCorrectionInput as ResultCorrectionInput,
    TestResultInput as ResultInput,
)


def test_result_retry_must_match_original_payload():
    original = ResultInput(
        status="PASS",
        note="Đăng nhập thành công",
        idempotency_key="retry-key-0001",
    )
    changed = ResultInput(
        status="FAIL",
        note="Đăng nhập thất bại",
        idempotency_key="retry-key-0001",
    )
    stored = {
        **original.model_dump(),
        "idempotency_request_hash": _idempotency_fingerprint(original),
    }

    assert _stored_result_matches_request(stored, original)
    assert not _stored_result_matches_request(stored, changed)


def test_execution_update_retry_rejects_same_key_with_changed_result():
    original = ExecutionPatch(status="PASS", idempotency_key="update-key-001")
    changed = ExecutionPatch(status="FAIL", idempotency_key="update-key-001")
    receipt = {"request_hash": _idempotency_fingerprint(original)}

    _verify_idempotency_replay(receipt, original, entity="TEST_EXECUTION_UPDATE")
    with pytest.raises(HTTPException) as raised:
        _verify_idempotency_replay(receipt, changed, entity="TEST_EXECUTION_UPDATE")

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_correction_retry_fingerprint_includes_reason():
    original = ResultCorrectionInput(
        status="PASS", reason="Đã xác minh log", idempotency_key="correct-key-01"
    )
    changed = ResultCorrectionInput(
        status="PASS", reason="Lý do đã thay đổi", idempotency_key="correct-key-01"
    )
    receipt = {"request_hash": _idempotency_fingerprint(original)}

    with pytest.raises(HTTPException) as raised:
        _verify_idempotency_replay(receipt, changed, entity="TEST_RESULT_CORRECTION")

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "IDEMPOTENCY_KEY_REUSED"

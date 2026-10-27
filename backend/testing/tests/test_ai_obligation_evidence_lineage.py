import pytest
from pydantic import ValidationError

from src.schemas.contracts.design import TestCaseDraftCreate
from src.schemas.test_analysis import GeneratedCase


def generated_case_payload():
    return {
        "title": "Kiểm tra chính sách khóa tài khoản",
        "category": "validation",
        "objective": "Xác minh ngưỡng khóa được nêu trong yêu cầu",
        "steps": [{"action": "Thực hiện thao tác theo yêu cầu", "expected": "Tài khoản bị khóa"}],
        "expected": "Tài khoản bị khóa sau 5 lần nhập sai.",
        "coverage_obligations": ["LOCKOUT"],
        "obligation_evidence": [
            {
                "obligation_key": "LOCKOUT",
                "evidence_quotes": [
                    {"evidence_ref": "REQ-V1", "quote": "Tài khoản bị khóa sau 5 lần nhập sai."}
                ],
            }
        ],
        "evidence_refs": ["REQ-V1"],
        "evidence_quotes": [
            {"evidence_ref": "REQ-V1", "quote": "Tài khoản bị khóa sau 5 lần nhập sai."}
        ],
    }


def test_generated_case_keeps_evidence_for_each_blueprint_obligation():
    generated = GeneratedCase.model_validate(generated_case_payload())

    assert generated.obligation_evidence[0].obligation_key == "LOCKOUT"
    assert generated.model_dump()["obligation_evidence"][0]["evidence_quotes"][0][
        "evidence_ref"
    ] == "REQ-V1"


def test_generated_case_rejects_coverage_without_obligation_evidence():
    payload = generated_case_payload()
    payload["obligation_evidence"] = []

    with pytest.raises(ValidationError):
        GeneratedCase.model_validate(payload)


def test_generated_case_accepts_only_required_skills_present_in_source_quote():
    payload = generated_case_payload()
    payload["required_skills"] = ["API testing"]
    payload["evidence_quotes"].append(
        {"evidence_ref": "REQ-V1", "quote": "API testing is required for this operation."}
    )

    generated = GeneratedCase.model_validate(payload)

    assert generated.required_skills == ["API testing"]


def test_generated_case_rejects_required_skill_not_present_in_source_quote():
    payload = generated_case_payload()
    payload["required_skills"] = ["Security testing"]

    with pytest.raises(ValidationError):
        GeneratedCase.model_validate(payload)


def test_ai_draft_keeps_obligation_evidence_with_frozen_source_quote():
    payload = {
        "title": "Kiểm tra chính sách khóa tài khoản",
        "origin": "ai_generated",
        "coverage_obligations": ["LOCKOUT"],
        "obligation_evidence": generated_case_payload()["obligation_evidence"],
        "evidence_refs": ["REQ-V1"],
        "evidence_quotes": generated_case_payload()["evidence_quotes"],
        "source_evidence": [
            {
                "artifact_type": "requirement_version",
                "artifact_version_id": "REQ-V1",
                "text": "Tài khoản bị khóa sau 5 lần nhập sai.",
            }
        ],
    }

    draft = TestCaseDraftCreate.model_validate(payload)

    assert draft.model_dump()["obligation_evidence"] == payload["obligation_evidence"]


def test_ai_draft_rejects_obligation_quote_not_in_source_citations():
    payload = {
        "title": "Kiểm tra chính sách khóa tài khoản",
        "origin": "ai_generated",
        "coverage_obligations": ["LOCKOUT"],
        "obligation_evidence": [
            {
                "obligation_key": "LOCKOUT",
                "evidence_quotes": [
                    {"evidence_ref": "REQ-V1", "quote": "Mọi tài khoản đều được đăng nhập."}
                ],
            }
        ],
        "evidence_refs": ["REQ-V1"],
        "evidence_quotes": [
            {"evidence_ref": "REQ-V1", "quote": "Tài khoản bị khóa sau 5 lần nhập sai."}
        ],
        "source_evidence": [
            {
                "artifact_type": "requirement_version",
                "artifact_version_id": "REQ-V1",
                "text": "Tài khoản bị khóa sau 5 lần nhập sai.",
            }
        ],
    }

    with pytest.raises(ValidationError):
        TestCaseDraftCreate.model_validate(payload)

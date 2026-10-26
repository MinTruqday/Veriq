import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.modules.design.services import test_adequacy


class TransactionSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def with_transaction(self, callback):
        return await callback(self)


class TestAdequacyAuditTransactions(unittest.IsolatedAsyncioTestCase):
    def test_business_rule_case_maps_only_when_its_evidence_quotes_the_rule(self):
        item = {
            "coverage_item_id": "coverage-rule-1",
            "requirement_version_id": "requirement-version-1",
            "source_type": "business_rule",
            "source_id": "0",
            "source_quote": "Tài khoản bị khóa sau 5 lần nhập sai.",
        }
        case = {
            "requirement_version_ids": ["requirement-version-1"],
            "coverage_item_ids": [],
            "techniques": ["BOUNDARY_VALUE"],
            "evidence_refs": ["requirement-version-1"],
            "evidence_quotes": [
                {
                    "evidence_ref": "requirement-version-1",
                    "quote": "Tài khoản bị khóa sau 5 lần nhập sai.",
                }
            ],
            "test_data": [{"failed_attempts": 5}],
            "expected_result_doc": {"text": "Tài khoản bị khóa."},
        }

        self.assertTrue(test_adequacy._case_mapping(item, case))
        case["evidence_quotes"] = [
            {"evidence_ref": "requirement-version-1", "quote": "Đăng nhập thành công."}
        ]
        self.assertFalse(test_adequacy._case_mapping(item, case))

    async def test_assessment_write_and_audit_share_transaction_session(self):
        session = TransactionSession()
        updated = {"_id": "assessment-1", "revision": 2}
        with (
            patch.object(
                test_adequacy.database,
                "client",
                new=SimpleNamespace(start_session=AsyncMock(return_value=session)),
            ),
            patch.object(
                test_adequacy.test_adequacy_repository,
                "replace",
                new=AsyncMock(return_value=updated),
            ) as replace,
            patch.object(
                test_adequacy, "audit", new=AsyncMock(return_value={})
            ) as audit,
        ):
            result = await test_adequacy._replace_assessment_with_audit(
                "assessment-1",
                "project-1",
                1,
                {"status": "ASSURED"},
                SimpleNamespace(id="qa-1"),
                "test_adequacy_assessment_approved",
            )

        self.assertEqual(result, updated)
        self.assertIs(replace.await_args.kwargs["session"], session)
        self.assertIs(audit.await_args.kwargs["session"], session)

    async def test_audit_failure_aborts_transaction_callback(self):
        session = TransactionSession()
        with (
            patch.object(
                test_adequacy.database,
                "client",
                new=SimpleNamespace(start_session=AsyncMock(return_value=session)),
            ),
            patch.object(
                test_adequacy.test_adequacy_repository,
                "replace",
                new=AsyncMock(return_value={"_id": "assessment-1"}),
            ) as replace,
            patch.object(
                test_adequacy,
                "audit",
                new=AsyncMock(side_effect=RuntimeError("audit storage unavailable")),
            ) as audit,
        ):
            with self.assertRaisesRegex(RuntimeError, "audit storage unavailable"):
                await test_adequacy._replace_assessment_with_audit(
                    "assessment-1",
                    "project-1",
                    1,
                    {"status": "ASSURED"},
                    SimpleNamespace(id="qa-1"),
                    "test_adequacy_assessment_approved",
                )

        replace.assert_awaited_once()
        audit.assert_awaited_once()

    async def test_approval_checks_open_clarifications_in_same_transaction(self):
        session = TransactionSession()
        timestamp = datetime.now(timezone.utc)
        assessment = {
            "_id": "assessment-1",
            "project_id": "project-1",
            "requirement_version_id": "requirement-version-1",
            "revision": 3,
            "status": "IN_REVIEW",
            "coverage_items": [
                {
                    "coverage_item_id": "coverage-1",
                    "requirement_version_id": "requirement-version-1",
                    "source_type": "business_rule",
                    "source_id": "0",
                    "source_ref": "business_rule:1",
                    "source_quote": "Chỉ tài khoản hợp lệ được đăng nhập.",
                    "status": "NOT_APPLICABLE",
                    "decision": {
                        "reason": "Không áp dụng cho sản phẩm này.",
                        "decided_by": "qa-1",
                        "decided_at": timestamp,
                    },
                }
            ],
        }
        open_clarification = {"_id": "clarification-open"}

        with (
            patch.object(test_adequacy.database, "client", SimpleNamespace(
                start_session=AsyncMock(return_value=session)
            )),
            patch.object(
                test_adequacy,
                "get_project_entity",
                new=AsyncMock(return_value=assessment),
            ),
            patch.object(test_adequacy, "_require_qa", new=AsyncMock()),
            patch.object(
                test_adequacy.requirement_repository,
                "bump_clarification_gate_revision",
                new=AsyncMock(return_value=True),
            ) as bump_gate,
            patch.object(
                test_adequacy.requirement_clarification_repository,
                "list_open_for_version",
                new=AsyncMock(return_value=[open_clarification]),
            ) as list_open,
            patch.object(
                test_adequacy.test_adequacy_repository,
                "replace",
                new=AsyncMock(),
            ) as replace,
            patch.object(test_adequacy, "audit", new=AsyncMock()) as audit,
        ):
            with self.assertRaises(HTTPException) as raised:
                await test_adequacy.approve_adequacy_assessment(
                    "assessment-1",
                    SimpleNamespace(expected_revision=3, note="Đã rà soát"),
                    SimpleNamespace(id="qa-1"),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"], "ADEQUACY_OPEN_CLARIFICATIONS"
        )
        self.assertEqual(
            raised.exception.detail["clarification_ids"], ["clarification-open"]
        )
        self.assertIs(bump_gate.await_args.kwargs["session"], session)
        self.assertIs(list_open.await_args.kwargs["session"], session)
        replace.assert_not_awaited()
        audit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

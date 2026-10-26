import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.modules.design.services import test_case_query


class TestCaseVersionEvidenceCopyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id="qa")
        self.test_case = {
            "_id": "case-1",
            "project_id": "project-1",
            "test_case_key": "TC-1",
            "current_version_id": "version-1",
        }
        self.version = {
            "_id": "version-1",
            "test_case_id": "case-1",
            "title": "Kiểm tra khóa tài khoản",
            "type": "validation",
            "preconditions_doc": {"type": "doc", "content": []},
            "steps": [],
            "test_data": {},
            "expected_result_doc": {"type": "doc", "content": []},
            "postconditions_doc": {"type": "doc", "content": []},
            "coverage_obligations": ["LOCKOUT"],
            "obligation_evidence": [
                {
                    "obligation_key": "LOCKOUT",
                    "evidence_quotes": [
                        {"evidence_ref": "REQ-V1", "quote": "Khóa sau 5 lần nhập sai."}
                    ],
                }
            ],
            "source_evidence": [
                {
                    "artifact_type": "requirement_version",
                    "artifact_version_id": "REQ-V1",
                    "text": "Khóa sau 5 lần nhập sai.",
                }
            ],
            "evidence_refs": ["REQ-V1"],
            "evidence_quotes": [
                {"evidence_ref": "REQ-V1", "quote": "Khóa sau 5 lần nhập sai."}
            ],
            "acceptance_criteria_snapshot_ids": ["AC-1"],
        }

    async def _captured_payload(self, call):
        create = AsyncMock(return_value={"_id": "draft-1"})
        with (
            patch.object(test_case_query, "get_project_entity", new=AsyncMock(return_value=self.test_case)),
            patch.object(test_case_query.test_design_repository, "find_case_version", new=AsyncMock(return_value=self.version)),
            patch.object(test_case_query, "create_test_case_draft_record", new=create),
            patch.object(test_case_query, "audit", new=AsyncMock()),
        ):
            await call()
        return create.await_args.args[1]

    async def test_clone_preserves_obligation_and_acceptance_evidence(self):
        payload = await self._captured_payload(
            lambda: test_case_query.clone_test_case_record(
                "case-1",
                SimpleNamespace(expected_current_version_id="version-1", title=None),
                self.user,
            )
        )

        self.assertEqual(payload.obligation_evidence[0].obligation_key, "LOCKOUT")
        self.assertEqual(payload.acceptance_criteria_snapshot_ids, ["AC-1"])

    async def test_new_version_preserves_obligation_evidence(self):
        payload = await self._captured_payload(
            lambda: test_case_query.create_test_case_version_draft_record(
                "case-1",
                SimpleNamespace(
                    expected_current_version_id="version-1",
                    change_reason="Làm rõ kiểm thử",
                    title=None,
                ),
                self.user,
            )
        )

        self.assertEqual(payload.obligation_evidence[0].obligation_key, "LOCKOUT")
        self.assertEqual(payload.acceptance_criteria_snapshot_ids, ["AC-1"])

import unittest

from pydantic import ValidationError

from src.agents.runner.nodes import verify
from src.schemas.agent import AgentRunStatus, VeriqRunState
from src.schemas.inference_change_simulation import (
    ChangeSimulationClassificationOutput,
    ChangeSimulationEvidenceQuoteOutput,
    ChangeSimulationPatchOutput,
    ChangeSimulationReportOutput,
)
from src.services.change_simulation import (
    change_simulation_batches,
    simulation_source_payload,
    validate_change_simulation_report,
)


class ChangeSimulationReportTests(unittest.TestCase):
    def setUp(self):
        self.observations = [
            {
                "tool_name": "get_requirement_version",
                "status": "COMPLETED",
                "result": {
                    "_id": "REQV-1",
                    "content": "Người dùng đăng nhập bằng mật khẩu.",
                },
            },
            {
                "tool_name": "get_test_case_version_by_id",
                "status": "COMPLETED",
                "source_version_id": "TCV-1",
                "result": {
                    "_id": "TCV-1",
                    "title": "Đăng nhập mật khẩu",
                    "expected": "Đăng nhập thành công",
                },
            },
        ]
        self.evidence = [
            {
                "artifact_type": "requirement_version",
                "artifact_version_id": "REQV-1",
                "text": "Người dùng đăng nhập bằng mật khẩu.",
            }
        ]

    def test_change_simulation_classification_is_partitioned_without_losing_scope(self):
        batches = change_simulation_batches(
            [f"TCV-{index}" for index in range(1, 16)], 6
        )

        self.assertEqual([len(batch) for batch in batches], [6, 6, 3])
        self.assertEqual(
            [item for batch in batches for item in batch],
            [f"TCV-{index}" for index in range(1, 16)],
        )

    def test_change_simulation_batching_deduplicates_ids_in_stable_order(self):
        self.assertEqual(
            change_simulation_batches(["TCV-1", None, " ", "TCV-1", "TCV-2"], 1),
            [["TCV-1"], ["TCV-2"]],
        )

    def test_change_simulation_batch_size_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "change_simulation_batch_size_invalid"):
            change_simulation_batches(["TCV-1"], 0)

    def report(self, *, quote="Người dùng đăng nhập bằng mật khẩu.", classifications=None):
        if classifications is None:
            classifications = [
                ChangeSimulationClassificationOutput(
                    test_case_version_id="TCV-1",
                    classification="POTENTIALLY_AFFECTED",
                    reason="Nguồn đề xuất cần được đối chiếu với điều kiện đăng nhập.",
                    evidence=[
                        ChangeSimulationEvidenceQuoteOutput(
                            source_type="BASELINE_REQUIREMENT",
                            artifact_version_id="REQV-1",
                            quote=quote,
                        ),
                        ChangeSimulationEvidenceQuoteOutput(
                            source_type="PROPOSED_REQUIREMENT",
                            artifact_version_id="REQV-1",
                            quote="passkey",
                        ),
                        ChangeSimulationEvidenceQuoteOutput(
                            source_type="TEST_CASE_VERSION",
                            artifact_version_id="TCV-1",
                            quote="Đăng nhập thành công",
                        ),
                    ],
                )
            ]
        return ChangeSimulationReportOutput(
            baseline_requirement_version_id="REQV-1",
            classifications=classifications,
        )

    def validate(self, report, ids=None):
        return validate_change_simulation_report(
            report,
            "REQV-1",
            "Người dùng đăng nhập bằng mật khẩu hoặc passkey.",
            ids or ["TCV-1"],
            self.observations,
            self.evidence,
        )

    def test_accepts_full_scope_with_verbatim_quotes_from_exact_sources(self):
        result = self.validate(self.report())
        self.assertEqual(result["classifications"][0]["test_case_version_id"], "TCV-1")

    def test_classifies_each_linked_version_against_its_own_content(self):
        self.observations.append({
            "tool_name": "get_test_case_version_by_id",
            "status": "COMPLETED",
            "source_version_id": "TCV-2",
            "result": {
                "_id": "TCV-2",
                "title": "Password reset",
                "expected": "Reset email sent",
            },
        })
        self.observations[1]["source_version_id"] = "TCV-1"
        payload = simulation_source_payload(
            self.observations,
            self.evidence,
            "REQV-1",
            "Người dùng đăng nhập bằng mật khẩu hoặc passkey.",
        )
        self.assertEqual(
            {item["test_case_version_id"] for item in payload["linked_test_case_versions"]},
            {"TCV-1", "TCV-2"},
        )
        first, second = self.report().classifications[0], self.report().classifications[0].model_copy(deep=True)
        second.test_case_version_id = "TCV-2"
        second.evidence[2].artifact_version_id = "TCV-2"
        second.evidence[2].quote = "Reset email sent"
        report = self.report(classifications=[first, second])
        result = validate_change_simulation_report(
            report,
            "REQV-1",
            "Người dùng đăng nhập bằng mật khẩu hoặc passkey.",
            ["TCV-1", "TCV-2"],
            self.observations,
            self.evidence,
        )
        self.assertEqual(len(result["classifications"]), 2)

    def test_does_not_use_a_version_read_returned_for_a_different_id(self):
        self.observations[1]["result"]["_id"] = "TCV-OTHER"
        with self.assertRaisesRegex(
            ValueError, "change_simulation_quote_source_out_of_scope"
        ):
            self.validate(self.report())

        payload = simulation_source_payload(
            self.observations,
            self.evidence,
            "REQV-1",
            "Người dùng đăng nhập bằng mật khẩu hoặc passkey.",
        )
        self.assertEqual(payload["linked_test_case_versions"], [])

    def test_rejects_quote_not_present_in_source(self):
        with self.assertRaisesRegex(ValueError, "quote_not_found_in_source"):
            self.validate(self.report(quote="Người dùng luôn đăng nhập được."))

    def test_rejects_quote_found_only_inside_another_word(self):
        self.observations[0]["result"]["content"] = "invalid"
        self.evidence[0]["text"] = "invalid"
        with self.assertRaisesRegex(ValueError, "quote_not_found_in_source"):
            self.validate(self.report(quote="valid"))

    def test_rejects_missing_classification(self):
        with self.assertRaisesRegex(ValueError, "classification_scope_incomplete"):
            self.validate(self.report(classifications=[]))

    def test_rejects_duplicate_classification(self):
        row = self.report().classifications[0]
        with self.assertRaisesRegex(ValueError, "duplicate_test_case_classification"):
            self.validate(self.report(classifications=[row, row]))

    def test_rejects_quote_from_another_test_case_version(self):
        item = self.report().classifications[0].model_copy(deep=True)
        item.evidence[1].artifact_version_id = "TCV-OTHER"
        with self.assertRaisesRegex(ValueError, "quote_source_out_of_scope"):
            self.validate(self.report(classifications=[item]))

    def test_patch_is_required_only_for_needs_update(self):
        with self.assertRaisesRegex(ValidationError, "patch_required_for_update"):
            ChangeSimulationClassificationOutput(
                test_case_version_id="TCV-1",
                classification="NEEDS_UPDATE",
                reason="Ca cần cập nhật theo thay đổi.",
                evidence=[
                    ChangeSimulationEvidenceQuoteOutput(
                        source_type="BASELINE_REQUIREMENT",
                        artifact_version_id="REQV-1",
                        quote="Người dùng đăng nhập bằng mật khẩu.",
                    )
                ],
            )

    def test_patch_contract_accepts_supported_case_fields_and_typed_steps(self):
        patch = ChangeSimulationPatchOutput.model_validate(
            {
                "title": "Đăng nhập bằng mật khẩu hoặc passkey",
                "steps": [
                    {
                        "action": "Nhập thông tin đăng nhập hợp lệ",
                        "expected": "Hệ thống cho phép đăng nhập",
                        "test_data": {"credential": "valid"},
                    }
                ],
            }
        )

        self.assertEqual(patch.steps[0].action, "Nhập thông tin đăng nhập hợp lệ")

    def test_needs_update_requires_patch_citations_from_proposed_requirement_and_case(self):
        row = self.report().classifications[0].model_dump()
        row["classification"] = "NEEDS_UPDATE"
        row["proposed_patch"] = {"title": "Đăng nhập bằng mật khẩu hoặc passkey"}
        row["proposed_patch_evidence"] = [row["evidence"][1], row["evidence"][2]]

        parsed = ChangeSimulationClassificationOutput.model_validate(row)

        self.assertEqual(len(parsed.proposed_patch_evidence), 2)

    def test_needs_update_rejects_patch_citation_not_in_classification_evidence(self):
        row = self.report().classifications[0].model_dump()
        row["classification"] = "NEEDS_UPDATE"
        row["proposed_patch"] = {"title": "Đăng nhập bằng mật khẩu hoặc passkey"}
        row["proposed_patch_evidence"] = [
            row["evidence"][1],
            {
                "source_type": "TEST_CASE_VERSION",
                "artifact_version_id": "TCV-1",
                "quote": "Không có trong bằng chứng của phân loại",
            },
        ]

        with self.assertRaisesRegex(
            ValidationError, "patch_evidence_not_in_classification_evidence"
        ):
            ChangeSimulationClassificationOutput.model_validate(row)

    def test_patch_contract_rejects_empty_payload_shapes(self):
        for value in ({"steps": []}, {"test_data": {}}):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValidationError, "change_simulation_patch_content_required"
            ):
                ChangeSimulationPatchOutput.model_validate(value)

        with self.assertRaises(ValidationError):
            ChangeSimulationPatchOutput.model_validate({"title": "   "})

    def test_patch_contract_rejects_fields_not_supported_by_test_case_maintenance(self):
        with self.assertRaises(ValidationError):
            ChangeSimulationPatchOutput.model_validate(
                {"release_decision": "APPROVE", "title": "Đăng nhập"}
            )

    def test_patch_contract_rejects_empty_or_incomplete_steps(self):
        with self.assertRaisesRegex(ValidationError, "patch_content_required"):
            ChangeSimulationPatchOutput.model_validate({})

        with self.assertRaises(ValidationError):
            ChangeSimulationPatchOutput.model_validate(
                {"steps": [{"action": "Chọn đăng nhập"}]}
            )


class ChangeSimulationRunVerificationTests(unittest.IsolatedAsyncioTestCase):
    def state(self, with_report):
        report = {"verified": True} if with_report else None
        run = VeriqRunState(
            project_id="PROJECT-1",
            user_id="QA-1",
            role="QA",
            objective="Mô phỏng thay đổi Requirement",
            evidence_refs=["REQV-1"],
            proposal={"evidence_refs": ["REQV-1"], "change_simulation_report": report},
            status=AgentRunStatus.VERIFYING,
            completed_tasks=[{"project_id": "PROJECT-1"}],
        )
        return {
            "run": run.model_dump(mode="python"),
            "constraints": {"change_simulation": True},
            "results": [
                {
                    "task_id": "TASK-1",
                    "status": "COMPLETED",
                    "summary": "Đã đọc nguồn được phép.",
                    "evidence_refs": ["REQV-1"],
                    "reason_codes": [],
                    "warnings": [],
                }
            ],
        }

    async def test_missing_report_fails_closed(self):
        updated = await verify(self.state(with_report=False))
        run = VeriqRunState(**updated["run"])
        self.assertEqual(run.status, AgentRunStatus.FAILED)
        self.assertEqual(run.error_code, "CHANGE_SIMULATION_REPORT_INCOMPLETE")

    async def test_verified_report_allows_simulation_completion(self):
        updated = await verify(self.state(with_report=True))
        run = VeriqRunState(**updated["run"])
        self.assertEqual(run.status, AgentRunStatus.COMPLETED)
        self.assertTrue(run.proposal["verification"]["change_simulation_report_valid"])


if __name__ == "__main__":
    unittest.main()

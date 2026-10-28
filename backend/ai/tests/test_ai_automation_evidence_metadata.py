import unittest
from unittest.mock import AsyncMock, patch

from src.schemas.inference_requests import (
    TestingAutomationRequest,
    TestingEvidence,
    TestingEvidence as EvidenceSchema,
)
from src.services.ai_automation import (
    evidence_payload,
    evidence_text,
    generate_ai_automation,
    generated_cases_have_grounded_citations,
    performance_targets_have_evidence,
)


class AIAutomationEvidenceMetadataTests(unittest.TestCase):
    def test_generated_case_citations_and_required_skills_need_exact_source_support(self):
        evidence = [
            {
                "artifact_id": "req-1",
                "artifact_version_id": "req-1",
                "text": "API testing is required for this operation.",
            }
        ]
        case = {
            "evidence_refs": ["req-1"],
            "evidence_quotes": [
                {
                    "evidence_ref": "req-1",
                    "quote": "API testing is required for this operation.",
                }
            ],
            "required_skills": ["API testing"],
        }

        self.assertTrue(generated_cases_have_grounded_citations([case], evidence))
        self.assertFalse(
            generated_cases_have_grounded_citations(
                [
                    {
                        **case,
                        "evidence_quotes": [
                            {
                                **case["evidence_quotes"][0],
                                "quote": "API testing is recommended.",
                            }
                        ],
                    }
                ],
                evidence,
            )
        )
        self.assertFalse(
            generated_cases_have_grounded_citations(
                [{**case, "required_skills": ["Security testing"]}], evidence
            )
        )

    def test_generated_case_rejects_subword_source_quote_and_skill(self):
        self.assertFalse(
            generated_cases_have_grounded_citations(
                [{
                    "evidence_refs": ["req-1"],
                    "evidence_quotes": [{"evidence_ref": "req-1", "quote": "valid"}],
                    "required_skills": [],
                }],
                [{"artifact_id": "req-1", "text": "invalid"}],
            )
        )
        self.assertFalse(
            generated_cases_have_grounded_citations(
                [{
                    "evidence_refs": ["req-1"],
                    "evidence_quotes": [{"evidence_ref": "req-1", "quote": "JavaScript"}],
                    "required_skills": ["Java"],
                }],
                [{"artifact_id": "req-1", "text": "JavaScript is required."}],
            )
        )

    def test_performance_numeric_targets_need_exact_quote_from_their_source(self):
        evidence = [
            {
                "artifact_id": "REQV-1",
                "artifact_version_id": "REQV-1",
                "text": "Hệ thống chịu tải 120 người dùng trong 15 phút, đạt 35 yêu cầu mỗi giây.",
            }
        ]
        suggestion = {
            "virtual_users": 120,
            "duration_minutes": 15,
            "requests_per_second": 35.0,
            "evidence_quotes": [
                {
                    "evidence_ref": "REQV-1",
                    "quote": "120 người dùng trong 15 phút, đạt 35 yêu cầu mỗi giây",
                }
            ],
        }

        self.assertTrue(performance_targets_have_evidence([suggestion], evidence))
        self.assertFalse(
            performance_targets_have_evidence(
                [{**suggestion, "virtual_users": 121}], evidence
            )
        )


    def test_performance_quote_inside_another_word_is_not_source_evidence(self):
        self.assertFalse(
            performance_targets_have_evidence(
                [{
                    "virtual_users": 1,
                    "evidence_quotes": [{"evidence_ref": "REQV-1", "quote": "valid"}],
                }],
                [{"artifact_id": "REQV-1", "text": "invalid"}],
            )
        )
        self.assertFalse(
            performance_targets_have_evidence(
                [
                    {
                        "virtual_users": 1,
                        "evidence_quotes": [
                            {"evidence_ref": "REQV-1", "quote": "Yêu cầu hiệu năng"}
                        ],
                    }
                ],
                [{"artifact_id": "REQV-1", "text": "invalid Yêu cầu hiệu năng"}],
            )
        )

    def test_prompt_payload_preserves_server_verified_version_lineage(self):
        evidence = EvidenceSchema(
            artifact_type="requirement_document",
            artifact_id="document-v2-record",
            artifact_version_id="document-v2-record",
            source_version="2",
            authority="PROJECT_REFERENCE",
            relationship_paths=[["document-v1-record", "document-v2-record"]],
            text="Mật khẩu phải có ít nhất 12 ký tự.",
        )

        payload = evidence_payload([evidence])
        prompt_evidence = evidence_text(payload)

        self.assertEqual(payload[0]["artifact_version_id"], "document-v2-record")
        self.assertEqual(payload[0]["source_version"], "2")
        self.assertEqual(
            payload[0]["relationship_paths"],
            [["document-v1-record", "document-v2-record"]],
        )
        self.assertIn('"source_version": "2"', prompt_evidence)
        self.assertIn(
            '"relationship_paths": [["document-v1-record", "document-v2-record"]]',
            prompt_evidence,
        )
        self.assertIn("Mật khẩu phải có ít nhất 12 ký tự.", prompt_evidence)

    def test_prompt_payload_preserves_verified_fact_identity_kind_and_quote(self):
        evidence = EvidenceSchema(
            artifact_type="requirement_document",
            artifact_id="document-v2-record",
            artifact_version_id="document-v2-record",
            authority="PROJECT_REFERENCE",
            verified_facts=[
                {
                    "source_fact_id": "FACT-123",
                    "fact_kind": "business_rule",
                    "quote": "Mật khẩu phải có ít nhất 12 ký tự.",
                    "source_start": 0,
                    "source_end": 36,
                    "source_offset_basis": "CANONICAL_TEXT",
                }
            ],
            text="Mật khẩu phải có ít nhất 12 ký tự.",
        )

        payload = evidence_payload([evidence])
        prompt_evidence = evidence_text(payload)

        self.assertEqual(payload[0]["verified_facts"][0]["source_fact_id"], "FACT-123")
        self.assertIn('"fact_kind": "business_rule"', prompt_evidence)
        self.assertIn('"quote": "Mật khẩu phải có ít nhất 12 ký tự."', prompt_evidence)


class AIAutomationLogPrivacyTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_error_message_is_not_written_to_application_log(self):
        private_source_text = "private requirement text that must not appear in logs"
        request = TestingAutomationRequest(
            capability="test_generation",
            project_id="project-1",
            instruction="Generate grounded test cases.",
            evidence=[
                TestingEvidence(
                    artifact_type="requirement",
                    artifact_id="req-1",
                    artifact_version_id="req-v1",
                    text="The user can sign in with valid credentials.",
                )
            ],
        )

        with (
            patch(
                "src.services.ai_automation.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.ai_automation.structured",
                new=AsyncMock(side_effect=RuntimeError(private_source_text)),
            ),
            patch(
                "src.services.ai_automation.model_metadata",
                return_value={"provider": "test", "model": "test-model"},
            ),
            patch("src.services.ai_automation.logger.warning") as warning,
        ):
            result = await generate_ai_automation(request)

        self.assertEqual(result.status.value, "DEGRADED")
        self.assertNotIn(private_source_text, str(warning.call_args))
        self.assertIn("AI_PROVIDER_UNAVAILABLE", str(warning.call_args))


if __name__ == "__main__":
    unittest.main()

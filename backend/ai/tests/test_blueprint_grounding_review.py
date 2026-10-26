import unittest
from unittest.mock import AsyncMock, patch

from src.schemas.inference_requirements import (
    TestabilityBlueprintCompilationOutput,
    TestabilityBlueprintGroundingReview,
    TestabilityBlueprintClaimReviewItem,
)
from src.schemas.inference_requests import TestingAutomationRequest, TestingEvidence
from src.services.ai_automation import generate_ai_automation


class BlueprintGroundingReviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        quote = "Mật khẩu phải có ít nhất 12 ký tự."
        self.request = TestingAutomationRequest(
            capability="testability_blueprint_compilation",
            project_id="project-1",
            instruction="Compile the verified facts into a testability blueprint.",
            evidence=[
                TestingEvidence(
                    artifact_type="requirement_document",
                    artifact_id="doc-1",
                    artifact_version_id="doc-1-v1",
                    verified_facts=[
                        {
                            "source_fact_id": "fact-1",
                            "fact_kind": "business_rule",
                            "quote": quote,
                            "source_start": 0,
                            "source_end": len(quote),
                            "source_offset_basis": "CANONICAL_TEXT",
                        }
                    ],
                    text=quote,
                )
            ],
        )
        self.blueprint = TestabilityBlueprintCompilationOutput(
            evidence_refs=["doc-1-v1"],
            confidence=0.9,
            obligations=[
                {
                    "key": "PASSWORD_MIN_LENGTH",
                    "obligation": "Xác minh mật khẩu có tối thiểu 12 ký tự.",
                    "source_ref": "doc-1-v1",
                    "source_quote": quote,
                }
            ],
        )

    async def _run(self, review):
        with (
            patch(
                "src.services.ai_automation.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.ai_automation.structured",
                new=AsyncMock(side_effect=[self.blueprint, review]),
            ) as structured_call,
            patch(
                "src.services.ai_automation.model_metadata",
                return_value={"provider": "test", "model": "test-model"},
            ),
        ):
            result = await generate_ai_automation(self.request)
        return result, structured_call

    async def test_blueprint_claims_are_independently_checked_against_verified_facts(self):
        review = TestabilityBlueprintGroundingReview(
            obligations=[TestabilityBlueprintClaimReviewItem(index=0)],
            clarifications=[],
        )
        result, structured_call = await self._run(review)

        self.assertEqual(result.status.value, "SUCCESS")
        self.assertEqual(structured_call.await_count, 2)
        self.assertIn("<untrusted_verified_source_evidence_json>", structured_call.await_args_list[1].args[0])
        self.assertIn("fact-1", structured_call.await_args_list[1].args[0])
        self.assertEqual(result.obligations[0]["key"], "PASSWORD_MIN_LENGTH")

    async def test_semantically_unsupported_obligation_is_degraded_not_published(self):
        self.blueprint.obligations[0].obligation = "Kiểm tra tài khoản bị khóa sau 5 lần đăng nhập sai."
        review = TestabilityBlueprintGroundingReview(
            obligations=[
                TestabilityBlueprintClaimReviewItem(
                    index=0,
                    unsupported_claims=["tài khoản bị khóa sau 5 lần đăng nhập sai"],
                )
            ],
            clarifications=[],
        )
        result, _ = await self._run(review)

        self.assertEqual(result.status.value, "DEGRADED")
        self.assertEqual(result.obligations, [])
        self.assertIn("AI_UNGROUNDED_OUTPUT", result.reason_codes)
        self.assertEqual(result.findings[0]["claim_type"], "OBLIGATION")
        self.assertEqual(
            result.findings[0]["unsupported_claims"],
            ["tài khoản bị khóa sau 5 lần đăng nhập sai"],
        )

    async def test_incomplete_reviewer_output_fails_closed(self):
        review = TestabilityBlueprintGroundingReview(obligations=[], clarifications=[])
        result, _ = await self._run(review)

        self.assertEqual(result.status.value, "DEGRADED")
        self.assertEqual(result.obligations, [])
        self.assertIn("AI_GROUNDING_REVIEW_INVALID", result.reason_codes)


if __name__ == "__main__":
    unittest.main()

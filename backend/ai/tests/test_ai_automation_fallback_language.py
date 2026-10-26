import unittest
from unittest.mock import AsyncMock, patch

from src.schemas.inference_requests import TestingAutomationRequest as AutomationRequestSchema
from src.schemas.inference_requests import TestingEvidence as EvidenceSchema
from src.services.ai_automation import generate_ai_automation


class AIAutomationFallbackLanguageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.request = AutomationRequestSchema(
            capability="project_question",
            project_id="project-1",
            instruction="Tóm tắt yêu cầu đăng nhập",
            evidence=[
                EvidenceSchema(
                    artifact_type="requirement",
                    artifact_id="requirement-1",
                    artifact_version_id="requirement-version-1",
                    text="Người dùng đăng nhập bằng mật khẩu hợp lệ.",
                )
            ],
        )

    async def test_provider_failure_returns_a_vietnamese_user_facing_fallback(self):
        with (
            patch(
                "src.services.ai_automation.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.ai_automation.structured",
                new=AsyncMock(side_effect=RuntimeError("provider unavailable")),
            ),
            patch(
                "src.services.ai_automation.model_metadata",
                return_value={"provider": "test", "model": "test-model"},
            ),
        ):
            result = await generate_ai_automation(self.request)

        self.assertEqual(result.status.value, "DEGRADED")
        self.assertEqual(
            result.answer,
            "Chưa thể tạo kết quả có căn cứ vì dịch vụ AI hiện không khả dụng",
        )

    async def test_invalid_output_returns_a_vietnamese_user_facing_fallback(self):
        with (
            patch(
                "src.services.ai_automation.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.ai_automation.structured",
                new=AsyncMock(side_effect=ValueError("invalid output")),
            ),
            patch(
                "src.services.ai_automation.model_metadata",
                return_value={"provider": "test", "model": "test-model"},
            ),
        ):
            result = await generate_ai_automation(self.request)

        self.assertEqual(result.status.value, "DEGRADED")
        self.assertEqual(
            result.answer,
            "Đầu ra của mô hình không đáp ứng hợp đồng dữ liệu yêu cầu",
        )


if __name__ == "__main__":
    unittest.main()

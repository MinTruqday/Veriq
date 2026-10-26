import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from langchain_core.messages import SystemMessage

from src.services.evaluation import _llm_judge


class EvaluationPromptOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_judge_instruction_is_owned_by_the_evaluation_prompt_module(self):
        scores = {
            "accuracy": 8,
            "completeness": 7,
            "relevance": 9,
            "explanation": "Đánh giá có căn cứ.",
        }
        structured_model = SimpleNamespace(
            ainvoke=AsyncMock(return_value=SimpleNamespace(model_dump=lambda: scores))
        )
        model = SimpleNamespace(with_structured_output=Mock(return_value=structured_model))

        with patch("src.utils.huggingface.create_chat_model", return_value=model):
            result = await _llm_judge("So sánh", "Kết quả chuẩn", "Kết quả thực tế")

        self.assertEqual(result, scores)
        model.with_structured_output.assert_called_once()
        messages = structured_model.ainvoke.await_args.args[0]
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertIn("Kết quả chuẩn", messages[0].content)
        self.assertIn("Kết quả thực tế", messages[0].content)

    async def test_judge_provider_failure_returns_vietnamese_explanation(self):
        with patch(
            "src.utils.huggingface.create_chat_model",
            side_effect=RuntimeError("provider unavailable"),
        ):
            result = await _llm_judge("So sánh", "Kết quả chuẩn", "Kết quả thực tế")

        self.assertEqual(
            result["explanation"],
            "Không thể hoàn tất đánh giá do lỗi nội bộ của hệ thống.",
        )


if __name__ == "__main__":
    unittest.main()

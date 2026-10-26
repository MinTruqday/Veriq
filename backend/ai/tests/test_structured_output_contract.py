import unittest
from unittest.mock import AsyncMock, patch

from pydantic import BaseModel

from src.services.inference import structured


class _Output(BaseModel):
    value: str


class StructuredOutputContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_receives_schema_and_validated_output_is_typed(self):
        with (
            patch("src.services.inference.chat", new=AsyncMock(return_value='{"value":"grounded"}')) as chat,
            patch("src.services.inference.schema_instruction", return_value="schema instructions"),
        ):
            result = await structured("prompt", _Output)

        self.assertEqual(result, _Output(value="grounded"))
        self.assertEqual(chat.await_count, 1)
        self.assertEqual(
            chat.await_args.kwargs["response_schema"],
            _Output.model_json_schema(),
        )
        self.assertIn("schema instructions", chat.await_args.args[0][0]["content"])

    async def test_invalid_output_is_corrected_and_revalidated_before_return(self):
        prompt_attempts = []
        with (
            patch(
                "src.services.inference.chat",
                new=AsyncMock(side_effect=['{"wrong":"field"}', '{"value":"fixed"}']),
            ) as chat,
            patch("src.services.inference.schema_instruction", return_value="schema instructions"),
            patch("src.services.inference.correction_instruction", return_value="Return the missing value field."),
        ):
            result = await structured(
                "prompt",
                _Output,
                prompt_attempt_observer=lambda messages, attempt: prompt_attempts.append(
                    (messages, attempt)
                ),
            )

        self.assertEqual(result.value, "fixed")
        self.assertEqual(chat.await_count, 2)
        correction_messages = chat.await_args_list[1].args[0]
        self.assertEqual(correction_messages[-1]["content"], "Return the missing value field.")
        self.assertEqual(chat.await_args_list[1].kwargs["response_schema"], _Output.model_json_schema())
        self.assertEqual([attempt for _, attempt in prompt_attempts], [1, 2])
        self.assertNotEqual(prompt_attempts[0][0], prompt_attempts[1][0])

    async def test_provider_schema_can_be_disabled_without_skipping_local_validation(self):
        with (
            patch("src.services.inference.chat", new=AsyncMock(return_value='{"value":"locally checked"}')) as chat,
            patch("src.services.inference.schema_instruction", return_value="schema instructions"),
        ):
            result = await structured("prompt", _Output, provider_schema=False)

        self.assertEqual(result.value, "locally checked")
        self.assertIsNone(chat.await_args.kwargs["response_schema"])

    async def test_provider_failure_is_not_misreported_as_schema_retry(self):
        with (
            patch("src.services.inference.chat", new=AsyncMock(side_effect=RuntimeError("provider unavailable"))) as chat,
            patch("src.services.inference.schema_instruction", return_value="schema instructions"),
            patch("src.services.inference.correction_instruction") as correction,
        ):
            with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
                await structured("prompt", _Output)

        chat.assert_awaited_once()
        correction.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from src.schemas.inference_skill_profile import (
    SkillProfileExtractionOutput,
    SkillProfileExtractionRequest,
)
from src.services.skill_profile_extraction import extract_skill_profile_candidates


class SkillProfileExtractionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.request = SkillProfileExtractionRequest(
            project_id="project-a",
            source_blocks=[
                {
                    "block_id": "#/pages/2/blocks/1",
                    "page_no": 2,
                    "text": "Kinh nghiệm: kiểm thử API bằng Postman trong dự án thanh toán.",
                }
            ],
        )

    def test_request_rejects_duplicate_source_block_ids(self):
        with self.assertRaises(ValidationError):
            SkillProfileExtractionRequest(
                project_id="project-a",
                source_blocks=[
                    {"block_id": "page-1:block-1", "page_no": 1, "text": "First source quote."},
                    {"block_id": "page-1:block-1", "page_no": 2, "text": "Different source quote."},
                ],
            )

    async def test_returns_only_candidates_grounded_in_exact_private_cv_block(self):
        generated = SkillProfileExtractionOutput.model_validate({
            "skills": [
                {
                    "name": "Postman",
                    "evidence_quote": "kiểm thử API bằng Postman",
                    "source_block_id": "#/pages/2/blocks/1",
                    "page_no": 2,
                }
            ],
            "experiences": [
                {
                    "title": "Dự án thanh toán",
                    "domain": "Thanh toán",
                    "technologies": ["Postman"],
                    "responsibilities": "Kiểm thử API",
                    "evidence_quote": "Kinh nghiệm: kiểm thử API bằng Postman trong dự án thanh toán.",
                    "source_block_id": "#/pages/2/blocks/1",
                    "page_no": 2,
                }
            ],
            "warnings": [],
        })
        with (
            patch(
                "src.services.skill_profile_extraction.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.skill_profile_extraction.structured",
                new=AsyncMock(return_value=generated),
            ) as structured,
        ):
            output = await extract_skill_profile_candidates(self.request)

        self.assertEqual(output.skills[0].name, "Postman")
        self.assertEqual(output.experiences[0].page_no, 2)
        self.assertIn("Kinh nghiệm:", output.experiences[0].evidence_quote)
        self.assertEqual(structured.await_args.args[1], type(output))

    async def test_rejects_quote_not_found_in_source(self):
        generated = SkillProfileExtractionOutput.model_validate({
            "skills": [{
                "name": "Selenium", "evidence_quote": "Thành thạo Selenium",
                "source_block_id": "#/pages/2/blocks/1", "page_no": 2,
            }],
            "experiences": [], "warnings": [],
        })
        with (
            patch(
                "src.services.skill_profile_extraction.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.skill_profile_extraction.structured",
                new=AsyncMock(return_value=generated),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await extract_skill_profile_candidates(self.request)
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail["code"], "CV_EVIDENCE_NOT_FOUND")

    async def test_rejects_quote_found_only_inside_another_word(self):
        request = SkillProfileExtractionRequest(
            project_id="project-a",
            source_blocks=[{"block_id": "cv-token", "page_no": 1, "text": "invalid"}],
        )
        generated = SkillProfileExtractionOutput.model_validate({
            "skills": [{
                "name": "valid",
                "evidence_quote": "valid",
                "source_block_id": "cv-token",
                "page_no": 1,
            }],
            "experiences": [],
            "warnings": [],
        })
        with (
            patch(
                "src.services.skill_profile_extraction.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.skill_profile_extraction.structured",
                new=AsyncMock(return_value=generated),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await extract_skill_profile_candidates(request)

        self.assertEqual(raised.exception.detail["code"], "CV_EVIDENCE_NOT_FOUND")

    async def test_rejects_experience_claim_supported_elsewhere_but_not_by_cited_quote(self):
        request = SkillProfileExtractionRequest(
            project_id="project-a",
            source_blocks=[{
                "block_id": "cv-block",
                "page_no": 2,
                "text": "API tester used Postman. Kotlin appears in a separate training list.",
            }],
        )
        generated = SkillProfileExtractionOutput.model_validate({
            "skills": [],
            "experiences": [{
                "title": "API tester",
                "technologies": ["Kotlin"],
                "evidence_quote": "API tester used Postman",
                "source_block_id": "cv-block",
                "page_no": 2,
            }],
            "warnings": [],
        })
        with (
            patch(
                "src.services.skill_profile_extraction.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.skill_profile_extraction.structured",
                new=AsyncMock(return_value=generated),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await extract_skill_profile_candidates(request)
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail["code"], "CV_CLAIM_NOT_GROUNDED")

    async def test_preserves_only_an_explicit_time_period_grounded_in_the_quote(self):
        request = SkillProfileExtractionRequest(
            project_id="project-a",
            source_blocks=[{
                "block_id": "cv-period",
                "page_no": 3,
                "text": "QA Engineer, 2020–2022, used Postman for API testing.",
            }],
        )
        generated = SkillProfileExtractionOutput.model_validate({
            "skills": [],
            "experiences": [{
                "title": "QA Engineer",
                "period": "2020–2022",
                "technologies": ["Postman"],
                "evidence_quote": "QA Engineer, 2020–2022, used Postman for API testing.",
                "source_block_id": "cv-period",
                "page_no": 3,
            }],
            "warnings": [],
        })
        with (
            patch(
                "src.services.skill_profile_extraction.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.skill_profile_extraction.structured",
                new=AsyncMock(return_value=generated),
            ),
        ):
            output = await extract_skill_profile_candidates(request)

        self.assertEqual(output.experiences[0].period, "2020–2022")

    async def test_rejects_inferred_time_period_absent_from_cited_quote(self):
        request = SkillProfileExtractionRequest(
            project_id="project-a",
            source_blocks=[{
                "block_id": "cv-no-period",
                "page_no": 3,
                "text": "QA Engineer used Postman for API testing.",
            }],
        )
        generated = SkillProfileExtractionOutput.model_validate({
            "skills": [],
            "experiences": [{
                "title": "QA Engineer",
                "period": "2020–2022",
                "technologies": ["Postman"],
                "evidence_quote": "QA Engineer used Postman for API testing.",
                "source_block_id": "cv-no-period",
                "page_no": 3,
            }],
            "warnings": [],
        })
        with (
            patch(
                "src.services.skill_profile_extraction.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.skill_profile_extraction.structured",
                new=AsyncMock(return_value=generated),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await extract_skill_profile_candidates(request)

        self.assertEqual(raised.exception.detail["code"], "CV_CLAIM_NOT_GROUNDED")

    async def test_rejects_skill_name_that_only_matches_inside_a_longer_name(self):
        request = SkillProfileExtractionRequest(
            project_id="project-a",
            source_blocks=[{
                "block_id": "cv-block",
                "page_no": 2,
                "text": "JavaScript automation experience",
            }],
        )
        generated = SkillProfileExtractionOutput.model_validate({
            "skills": [{
                "name": "Java",
                "evidence_quote": "JavaScript automation experience",
                "source_block_id": "cv-block",
                "page_no": 2,
            }],
            "experiences": [],
            "warnings": [],
        })
        with (
            patch(
                "src.services.skill_profile_extraction.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.skill_profile_extraction.structured",
                new=AsyncMock(return_value=generated),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await extract_skill_profile_candidates(request)
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail["code"], "CV_CLAIM_NOT_GROUNDED")

    async def test_rejects_page_reference_not_matching_parser(self):
        generated = SkillProfileExtractionOutput.model_validate({
            "skills": [{
                "name": "Postman", "evidence_quote": "Postman",
                "source_block_id": "#/pages/2/blocks/1", "page_no": 3,
            }],
            "experiences": [], "warnings": [],
        })
        with (
            patch(
                "src.services.skill_profile_extraction.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch(
                "src.services.skill_profile_extraction.structured",
                new=AsyncMock(return_value=generated),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await extract_skill_profile_candidates(self.request)
        self.assertEqual(raised.exception.detail["code"], "CV_PAGE_REFERENCE_MISMATCH")

    async def test_unsafe_source_is_rejected_before_model_call(self):
        model = AsyncMock()
        with (
            patch(
                "src.services.skill_profile_extraction.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": False}),
            ),
            patch("src.services.skill_profile_extraction.structured", new=model),
        ):
            with self.assertRaises(HTTPException) as raised:
                await extract_skill_profile_candidates(self.request)
        self.assertEqual(raised.exception.detail["code"], "CV_CONTENT_UNSAFE")
        model.assert_not_awaited()

    async def test_extracted_text_limit_is_enforced_before_model_call(self):
        request = SkillProfileExtractionRequest(
            project_id="project-a",
            source_blocks=[{"block_id": f"b{i}", "text": "x" * 3000} for i in range(34)],
        )
        model = AsyncMock()
        with (
            patch(
                "src.services.skill_profile_extraction.guardrails_engine.async_inspect_input",
                new=AsyncMock(return_value={"is_safe": True}),
            ),
            patch("src.services.skill_profile_extraction.structured", new=model),
        ):
            with self.assertRaises(HTTPException) as raised:
                await extract_skill_profile_candidates(request)
        self.assertEqual(raised.exception.status_code, 413)
        model.assert_not_awaited()

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from src.schemas.inference_staffing import (
    StaffingCandidateInput,
    StaffingCandidateRecommendation,
    StaffingEvidenceFact,
    StaffingRecommendationOutput,
    StaffingRecommendationRequest,
    StaffingSkillMatch,
)
from src.services.staffing_recommendation import recommend_staffing


def request():
    return StaffingRecommendationRequest(
        project_id="project-1",
        output_language="vi",
        required_skills=["Kỹ năng dự án"],
        candidates=[
            StaffingCandidateInput(
                candidate_id="candidate-1",
                confirmed_skills=["Kỹ năng dự án"],
                evidence_facts=[
                    StaffingEvidenceFact(
                        fact_id="skill-1",
                        description="Confirmed profile skill",
                    ),
                    StaffingEvidenceFact(
                        fact_id="availability",
                        description="Available for assignment",
                    ),
                ],
                availability="AVAILABLE",
                active_project_count=0,
                active_case_count=0,
                active_run_count=0,
            )
        ],
    )


def result(*, fact_id="skill-1", required_skill="Kỹ năng dự án", unmatched=None):
    return StaffingRecommendationOutput(
        recommendations=[
            StaffingCandidateRecommendation(
                candidate_id="candidate-1",
                reason="Evidence supports this candidate.",
                supporting_facts=["skill-1", "availability"],
                skill_matches=[
                    StaffingSkillMatch(
                        required_skill=required_skill,
                        evidence_fact_id=fact_id,
                        match_type="EXACT",
                        rationale="The recorded skill name matches the requirement.",
                    )
                ],
                unmatched_required_skills=unmatched or [],
            )
        ],
        warnings=[],
    )


class StaffingRecommendationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_accepts_exact_match_with_a_candidate_skill_fact(self):
        with patch(
            "src.services.staffing_recommendation.structured",
            new=AsyncMock(return_value=result()),
        ):
            response = await recommend_staffing(request())

        self.assertEqual(response.recommendations[0].skill_matches[0].evidence_fact_id, "skill-1")

    async def test_rejects_skill_reference_outside_candidate_evidence(self):
        with patch(
            "src.services.staffing_recommendation.structured",
            new=AsyncMock(return_value=result(fact_id="availability")),
        ):
            with self.assertRaises(HTTPException) as raised:
                await recommend_staffing(request())

        self.assertEqual(raised.exception.detail["code"], "STAFFING_SKILL_EVIDENCE_INVALID")

    async def test_rejects_exact_match_that_does_not_match_recorded_skill(self):
        with patch(
            "src.services.staffing_recommendation.structured",
            new=AsyncMock(return_value=result(required_skill="Khác")),
        ):
            with self.assertRaises(HTTPException) as raised:
                await recommend_staffing(request())

        self.assertEqual(raised.exception.detail["code"], "STAFFING_SKILL_COVERAGE_INVALID")

    async def test_rejects_reusing_one_skill_fact_for_multiple_requirements(self):
        value = request()
        value.required_skills = ["Kỹ năng dự án", "Một kỹ năng khác"]
        output = result()
        item = output.recommendations[0]
        item.skill_matches.append(item.skill_matches[0].model_copy(update={"required_skill": "Một kỹ năng khác"}))
        with patch(
            "src.services.staffing_recommendation.structured",
            new=AsyncMock(return_value=output),
        ):
            with self.assertRaises(HTTPException) as raised:
                await recommend_staffing(value)

        self.assertEqual(raised.exception.detail["code"], "STAFFING_SKILL_EVIDENCE_REUSED")


if __name__ == "__main__":
    unittest.main()

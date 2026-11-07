import unittest

from pydantic import ValidationError

from src.schemas.inference import RequirementQualityRecommendationOutput
from src.schemas.inference_requirements import RequirementQualityModelOutput
from src.services.ai_automation import grounded_requirement_recommendations


class RequirementQualityRecommendationTests(unittest.TestCase):
    def test_contract_returns_recommendations_without_findings_or_severity(self):
        output = RequirementQualityModelOutput.model_validate({
            "recommendations": [{
                "category": "OMISSION",
                "message": "Nên làm rõ thời điểm thông báo được gửi.",
                "suggestion": "Bổ sung điều kiện xác định thời điểm gửi thông báo.",
                "evidence_refs": ["REQ-V1"],
                "evidence_quotes": [{
                    "evidence_ref": "REQ-V1",
                    "quote": "Hệ thống gửi thông báo cho người dùng.",
                }],
                "reason_codes": ["MISSING_NOTIFICATION_TIMING"],
            }],
        })

        self.assertEqual(len(output.recommendations), 1)
        self.assertIsInstance(output.recommendations[0], RequirementQualityRecommendationOutput)
        self.assertFalse(hasattr(output.recommendations[0], "severity"))
        with self.assertRaises(ValidationError):
            RequirementQualityModelOutput.model_validate({"findings": []})

    def test_only_recommendations_with_exact_source_quotes_are_retained(self):
        accepted, rejected = grounded_requirement_recommendations(
            [
                {
                    "evidence_refs": ["REQ-V1"],
                    "evidence_quotes": [{
                        "evidence_ref": "REQ-V1",
                        "quote": "Hệ thống gửi thông báo cho người dùng.",
                    }],
                },
                {
                    "evidence_refs": ["REQ-V1"],
                    "evidence_quotes": [{
                        "evidence_ref": "REQ-V1",
                        "quote": "Người dùng luôn nhận được thông báo tức thì.",
                    }],
                },
            ],
            [{
                "artifact_version_id": "REQ-V1",
                "text": "Hệ thống gửi thông báo cho người dùng.",
            }],
        )

        self.assertEqual(len(accepted), 1)
        self.assertTrue(rejected)


if __name__ == "__main__":
    unittest.main()

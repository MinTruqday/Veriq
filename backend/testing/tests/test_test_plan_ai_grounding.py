import unittest

from fastapi import HTTPException

from src.modules.execution.services.test_plan import validate_test_plan_ai_field_grounding


class TestPlanAiGroundingTests(unittest.TestCase):
    def test_keeps_fields_with_exact_source_quotes(self):
        proposal = {
            "objective": "Kiểm tra thanh toán",
            "field_evidence": [
                {
                    "field": "objective",
                    "evidence_quotes": [
                        {"evidence_ref": "REQ-1", "quote": "Kiểm tra thanh toán"}
                    ],
                }
            ],
        }

        unsupported = validate_test_plan_ai_field_grounding(
            proposal, {"REQ-1": "Mục tiêu: Kiểm tra thanh toán"}
        )

        self.assertEqual(unsupported, [])
        self.assertEqual(proposal["objective"], "Kiểm tra thanh toán")
        self.assertEqual(proposal["field_evidence"][0]["field"], "objective")

    def test_omits_unverifiable_field_without_rejecting_grounded_fields(self):
        proposal = {
            "objective": "Kiểm tra thanh toán",
            "environment": "Mọi trình duyệt và thiết bị",
            "field_evidence": [
                {
                    "field": "objective",
                    "evidence_quotes": [
                        {"evidence_ref": "REQ-1", "quote": "Kiểm tra thanh toán"}
                    ],
                },
                {
                    "field": "environment",
                    "evidence_quotes": [
                        {"evidence_ref": "REQ-1", "quote": "Chrome trên desktop"}
                    ],
                },
            ],
        }

        unsupported = validate_test_plan_ai_field_grounding(
            proposal, {"REQ-1": "Mục tiêu: Kiểm tra thanh toán"}
        )

        self.assertEqual(unsupported, ["environment"])
        self.assertEqual(proposal["objective"], "Kiểm tra thanh toán")
        self.assertEqual(proposal["environment"], "")
        self.assertEqual([item["field"] for item in proposal["field_evidence"]], ["objective"])

    def test_duplicate_field_evidence_is_rejected(self):
        proposal = {
            "objective": "Kiểm tra thanh toán",
            "field_evidence": [
                {"field": "objective", "evidence_quotes": [{"evidence_ref": "REQ-1", "quote": "Kiểm tra"}]},
                {"field": "objective", "evidence_quotes": [{"evidence_ref": "REQ-1", "quote": "thanh toán"}]},
            ],
        }

        with self.assertRaises(HTTPException):
            validate_test_plan_ai_field_grounding(proposal, {"REQ-1": "Kiểm tra thanh toán"})


if __name__ == "__main__":
    unittest.main()

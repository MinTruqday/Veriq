import unittest

from src.schemas.inference_requests import TestingEvidence as EvidenceSchema
from src.services.ai_automation import (
    evidence_payload,
    evidence_text,
    performance_targets_have_evidence,
)


class AIAutomationEvidenceMetadataTests(unittest.TestCase):
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
        self.assertFalse(
            performance_targets_have_evidence(
                [
                    {
                        **suggestion,
                        "evidence_quotes": [
                            {"evidence_ref": "REQV-1", "quote": "Yêu cầu hiệu năng"}
                        ],
                    }
                ],
                evidence,
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


if __name__ == "__main__":
    unittest.main()

import hashlib
import unittest

from src.schemas.automation import DerivationReceipt, SourceFact
from src.services.automation_provenance import (
    canonicalize_source_facts,
    carry_source_fact_lineage,
    has_provenance_gap,
    missing_blueprint_artifact_coverage_count,
    source_fact_identity,
    verified_blueprint_artifact_lineage,
    verified_blueprint_claim_lineage,
    verified_blueprint_from_observations,
    verified_blueprint_snapshot,
    verified_source_span,
)


class VerifiedSourceSpanTests(unittest.TestCase):
    def setUp(self):
        self.evidence = [
            {
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "text": "Người dùng đăng nhập bằng mật khẩu hợp lệ.",
            }
        ]

    def test_accepts_exact_quote_with_verified_revision_and_position(self):
        quote = "đăng nhập bằng mật khẩu hợp lệ"
        start = self.evidence[0]["text"].index(quote)
        result = verified_source_span(
            {
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": quote,
                "source_start": start,
                "source_end": start + len(quote),
            },
            self.evidence,
        )
        self.assertEqual(result["source_start"], start)
        self.assertEqual(result["source_end"], start + len(quote))

    def test_accepts_verified_blueprint_fact_excerpt_with_canonical_span(self):
        quote = "Người dùng đăng nhập bằng mật khẩu hợp lệ."
        result = verified_source_span(
            {
                "artifact_type": "requirement_document",
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": quote,
                "source_start": 0,
                "source_end": len(quote),
                "source_offset_basis": "CANONICAL_TEXT",
            },
            [
                {
                    "artifact_type": "requirement_document",
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v2",
                    "text": quote,
                    "source_start": 0,
                    "source_end": len(quote),
                    "source_verification": "VERIFIED_BLUEPRINT_SOURCE_FACT",
                    "source_offset_basis": "CANONICAL_TEXT",
                }
            ],
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["source_start"], 0)
        self.assertEqual(result["source_end"], len(quote))
        self.assertEqual(result["source_offset_basis"], "CANONICAL_TEXT")

    def test_rejects_blueprint_fact_excerpt_when_quote_or_span_differs(self):
        quote = "Người dùng đăng nhập bằng mật khẩu hợp lệ."
        result = verified_source_span(
            {
                "artifact_type": "requirement_document",
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": quote,
                "source_start": 0,
                "source_end": len(quote),
            },
            [
                {
                    "artifact_type": "requirement_document",
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v2",
                    "text": "Người dùng đăng nhập bằng mật khẩu khác.",
                    "source_start": 0,
                    "source_end": len(quote),
                    "source_verification": "VERIFIED_BLUEPRINT_SOURCE_FACT",
                }
            ],
        )
        self.assertIsNone(result)

    def test_rejects_fact_claimed_chunk_basis_without_source_location_metadata(self):
        quote = "đăng nhập bằng mật khẩu hợp lệ"
        start = self.evidence[0]["text"].index(quote)
        verified = verified_source_span(
            {
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": quote,
                "source_start": start,
                "source_end": start + len(quote),
                "source_offset_basis": "RETRIEVED_CHUNK",
            },
            self.evidence,
        )

        self.assertEqual(verified["source_offset_basis"], "UNKNOWN")
        self.assertIsNone(verified["source_chunk_id"])

    def test_retrieved_chunk_basis_requires_server_source_location_metadata(self):
        quote = "đăng nhập bằng mật khẩu hợp lệ"
        start = self.evidence[0]["text"].index(quote)
        source = {
            **self.evidence[0],
            "chunk_id": "chunk-8",
            "chunk_index": 3,
            "page_numbers": [2],
        }
        verified = verified_source_span(
            {
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": quote,
                "source_start": start,
                "source_end": start + len(quote),
                "source_offset_basis": "UNKNOWN",
            },
            [source],
        )

        self.assertEqual(verified["source_offset_basis"], "RETRIEVED_CHUNK")
        self.assertEqual(verified["source_chunk_id"], "chunk-8")
        self.assertEqual(verified["source_chunk_index"], 3)
        self.assertEqual(verified["source_page_numbers"], [2])

    def test_canonical_text_basis_requires_explicit_server_source_evidence(self):
        quote = "đăng nhập bằng mật khẩu hợp lệ"
        start = self.evidence[0]["text"].index(quote)
        source = {**self.evidence[0], "source_offset_basis": "CANONICAL_TEXT"}
        verified = verified_source_span(
            {
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": quote,
                "source_start": start,
                "source_end": start + len(quote),
                "source_offset_basis": "RETRIEVED_CHUNK",
            },
            [source],
        )

        self.assertEqual(verified["source_offset_basis"], "CANONICAL_TEXT")

    def test_source_lineage_comes_from_authoritative_evidence_not_model_fact(self):
        quote = "đăng nhập bằng mật khẩu hợp lệ"
        start = self.evidence[0]["text"].index(quote)
        evidence = [{
            **self.evidence[0],
            "relationship_path": ["source-root", "source-v2", "doc-1"],
            "chunk_id": "chunk-7",
            "chunk_index": 6,
            "chunk_type": "docling_structure_semantic",
            "page_numbers": [7],
            "source_spans": [{"block_id": "block-7", "offset_basis": "normalized_block"}],
            "source_hash": "source-hash",
        }]
        verified = verified_source_span(
            {
                "artifact_type": "requirement_document",
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": quote,
                "source_start": start,
                "source_end": start + len(quote),
                "relationship_path": ["invented-root", "other-project"],
            },
            evidence,
        )

        self.assertEqual(
            verified["relationship_path"], ["source-root", "source-v2", "doc-1"]
        )
        self.assertEqual(verified["source_offset_basis"], "RETRIEVED_CHUNK")
        saved_fact = SourceFact(
            source_fact_id="FACT-lineage",
            automation_run_id="run-1",
            project_id="project-1",
            artifact_type=verified["artifact_type"],
            artifact_id=verified["artifact_id"],
            artifact_version_id=verified["artifact_version_id"],
            source=verified.get("source", "document"),
            authority=verified.get("authority", "project"),
            quote=verified["quote"],
            source_start=verified["source_start"],
            source_end=verified["source_end"],
            relationship_path=verified["relationship_path"],
            source_chunk_id=verified["source_chunk_id"],
            source_chunk_index=verified["source_chunk_index"],
            source_chunk_type=verified["source_chunk_type"],
            source_page_numbers=verified["source_page_numbers"],
            source_spans=verified["source_spans"],
            source_hash=verified["source_hash"],
            source_offset_basis=verified["source_offset_basis"],
        )
        saved_round_trip = SourceFact.model_validate(saved_fact.model_dump())
        self.assertEqual(saved_round_trip.relationship_path, ["source-root", "source-v2", "doc-1"])
        self.assertEqual(saved_round_trip.source_chunk_id, "chunk-7")
        self.assertEqual(saved_round_trip.source_chunk_index, 6)
        self.assertEqual(saved_round_trip.source_page_numbers, [7])
        self.assertEqual(saved_round_trip.source_spans[0]["block_id"], "block-7")
        self.assertEqual(saved_round_trip.source_hash, "source-hash")
        self.assertEqual(saved_round_trip.source_offset_basis, "RETRIEVED_CHUNK")

    def test_rejects_missing_revision_or_unknown_source(self):
        fact = {"artifact_id": "doc-1", "quote": "Người dùng"}
        self.assertIsNone(verified_source_span(fact, self.evidence))
        self.assertIsNone(
            verified_source_span(
                {
                    **fact,
                    "artifact_version_id": "doc-1-v3",
                },
                self.evidence,
            )
        )

    def test_rejects_same_artifact_id_and_version_from_another_type(self):
        evidence = [{
            **self.evidence[0],
            "artifact_type": "defect",
        }]
        quote = "Người dùng"
        start = evidence[0]["text"].index(quote)

        verified = verified_source_span(
            {
                "artifact_type": "requirement_document",
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": quote,
                "source_start": start,
                "source_end": start + len(quote),
            },
            evidence,
        )

        self.assertIsNone(verified)

    def test_rejects_false_or_partial_positions(self):
        for start, end in ((0, 15), (-1, 10)):
            with self.subTest(start=start, end=end):
                self.assertIsNone(
                    verified_source_span(
                        {
                            "artifact_id": "doc-1",
                            "artifact_version_id": "doc-1-v2",
                            "quote": "mật khẩu hợp lệ",
                            "source_start": start,
                            "source_end": end,
                        },
                        self.evidence,
                    )
                )

    def test_accepts_only_explicitly_verified_compact_source_citation_spans(self):
        quote = "Khi nhập đúng thông tin, người dùng vào được hệ thống."
        fact = {
            "artifact_id": "doc-1",
            "artifact_version_id": "doc-1-v2",
            "quote": quote,
            "source_start": 120,
            "source_end": 120 + len(quote),
        }
        evidence = [{
            "artifact_id": "doc-1",
            "artifact_version_id": "doc-1-v2",
            "text": quote,
            "source_start": fact["source_start"],
            "source_end": fact["source_end"],
            "source_verification": "VERIFIED_REQUIREMENT_SOURCE_CITATION",
        }]
        verified = verified_source_span(fact, evidence)
        self.assertEqual(verified["source_start"], fact["source_start"])
        self.assertEqual(verified["source_end"], fact["source_end"])
        self.assertEqual(verified["source_offset_basis"], "SOURCE_CITATION")
        self.assertEqual(verified["relationship_path"], [])
        self.assertIsNone(
            verified_source_span(fact, [{**evidence[0], "source_verification": ""}])
        )
        self.assertIsNone(
            verified_source_span(fact, [{**evidence[0], "source_end": fact["source_end"] + 1}])
        )

    def test_infers_position_only_when_exact_quote_is_unique(self):
        unique = verified_source_span(
            {
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": "Người dùng",
            },
            self.evidence,
        )
        self.assertEqual(unique["source_start"], 0)
        ambiguous = verified_source_span(
            {
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": "đăng nhập",
            },
            [
                *self.evidence,
                {**self.evidence[0], "text": "Có thể đăng nhập lại."},
            ],
        )
        self.assertIsNone(ambiguous)

    def test_malformed_vector_location_metadata_is_dropped_not_promoted(self):
        quote = "Người dùng"
        start = self.evidence[0]["text"].index(quote)
        evidence = [{
            **self.evidence[0],
            "chunk_id": "chunk-1",
            "chunk_index": "invalid",
            "chunk_type": 7,
            "page_numbers": [7, "8", True, -1],
            "source_spans": [None, {"block_id": "block-1"}, "invalid"],
            "source_hash": 42,
        }]

        verified = verified_source_span(
            {
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": quote,
                "source_start": start,
                "source_end": start + len(quote),
            },
            evidence,
        )

        self.assertIsNone(verified["source_chunk_index"])
        self.assertIsNone(verified["source_chunk_type"])
        self.assertEqual(verified["source_page_numbers"], [7])
        self.assertEqual(verified["source_spans"], [{"block_id": "block-1"}])
        self.assertIsNone(verified["source_hash"])

    def test_derivation_receipt_carries_source_facts_through_verified_tool_reads(self):
        lineage = {"doc-1-v2": ["fact-1"]}
        observed = carry_source_fact_lineage(
            ["doc-1-v2"], ["task-1:get_requirement"], lineage
        )
        compiled = carry_source_fact_lineage(
            ["task-1:get_requirement"], ["requirement-v3"], lineage
        )
        self.assertEqual(observed, ["fact-1"])
        self.assertEqual(compiled, ["fact-1"])
        self.assertEqual(lineage["requirement-v3"], ["fact-1"])

    def test_unrelated_tool_result_does_not_gain_source_lineage(self):
        lineage = {"doc-1-v2": ["fact-1"]}
        result = carry_source_fact_lineage(["unknown-tool-ref"], ["output-1"], lineage)
        self.assertEqual(result, [])
        self.assertEqual(lineage["output-1"], [])

    def test_same_version_quote_with_parent_or_version_artifact_id_is_one_fact(self):
        parent_fact = {
            "artifact_type": "requirement_version",
            "artifact_id": "REQ-1",
            "artifact_version_id": "REQV-1",
            "source_start": 0,
            "source_end": 16,
            "quote": "Sign in succeeds",
        }
        version_alias = {**parent_fact, "artifact_id": "REQV-1"}
        self.assertEqual(source_fact_identity(parent_fact), source_fact_identity(version_alias))
        self.assertNotEqual(
            source_fact_identity(parent_fact),
            source_fact_identity({**parent_fact, "source_end": 18}),
        )

    def test_resumed_version_aliases_are_canonicalized_from_verified_event_evidence(self):
        parent_fact = {
            "artifact_type": "requirement_version",
            "artifact_id": "REQ-1",
            "artifact_version_id": "REQV-1",
            "source_start": 0,
            "source_end": 16,
            "quote": "Sign in succeeds",
        }
        version_alias = {**parent_fact, "artifact_id": "REQV-1"}
        facts = canonicalize_source_facts(
            [version_alias, parent_fact],
            [
                {"artifact_type": "requirement_version", "artifact_id": "REQ-1", "artifact_version_id": "REQV-1"},
                {"artifact_type": "requirement_version", "artifact_id": "REQV-1", "artifact_version_id": "REQV-1"},
            ],
        )
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["artifact_id"], "REQ-1")

    def test_unverified_source_facts_or_unlinked_mutations_are_a_provenance_gap(self):
        self.assertTrue(has_provenance_gap(1, 0))
        self.assertTrue(has_provenance_gap(0, 1))
        self.assertTrue(has_provenance_gap(0, 0, 1))
        self.assertFalse(has_provenance_gap(0, 0))

    def test_blueprint_receipt_requires_every_obligation_and_clarification_to_resolve_to_facts(self):
        source_fact = type(
            "Fact",
            (),
            {
                "automation_run_id": "run-1",
                "project_id": "project-1",
                "artifact_type": "requirement_document",
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": "Người dùng đăng nhập bằng mật khẩu hợp lệ.",
                "quote_sha256": hashlib.sha256(
                    "Người dùng đăng nhập bằng mật khẩu hợp lệ.".encode("utf-8")
                ).hexdigest(),
            },
        )()
        blueprint = {
            "capability": "testability_blueprint_compilation",
            "obligations": [
                {
                    "key": "login-valid",
                    "obligation": "Đăng nhập bằng mật khẩu hợp lệ",
                    "source_ref": "doc-1-v2",
                    "source_quote": "Người dùng đăng nhập bằng mật khẩu hợp lệ.",
                }
            ],
            "clarifications": [
                {
                    "code": "login-error",
                    "category": "MISSING_ERROR_BEHAVIOR",
                    "question": "Hệ thống xử lý thông tin đăng nhập không hợp lệ như thế nào?",
                    "reason": "Nguồn chỉ mô tả thông tin hợp lệ nên chưa xác định được hành vi với thông tin sai.",
                    "priority": "HIGH",
                    "evidence_refs": ["doc-1-v2"],
                    "source_quote": "Người dùng đăng nhập bằng mật khẩu hợp lệ.",
                    "unlocks_obligation_keys": ["login-valid"],
                }
            ],
            "evidence_refs": ["doc-1-v2"],
            "confidence": 0.9,
            "warnings": [],
        }
        snapshot = verified_blueprint_snapshot(
            blueprint,
            [source_fact],
            project_id="project-1",
            automation_run_id="run-1",
        )
        self.assertIsNotNone(snapshot)
        receipt = DerivationReceipt(
            automation_run_id="run-1",
            project_id="project-1",
            agent_run_id="agent-1",
            outcome="COMPLETED",
            testability_blueprint=snapshot,
        )
        self.assertEqual(receipt.testability_blueprint.obligations[0].key, "login-valid")
        invalid = {
            **blueprint,
            "obligations": [
                {**blueprint["obligations"][0], "source_quote": "Đăng nhập với mọi loại mật khẩu"}
            ],
        }
        self.assertIsNone(
            verified_blueprint_snapshot(
                invalid,
                [source_fact],
                project_id="project-1",
                automation_run_id="run-1",
            )
        )

    def test_blueprint_claim_lineage_links_each_claim_to_its_exact_source_fact(self):
        quote = "The account owner can reset the password."
        facts = [
            SourceFact(
                source_fact_id="FACT-supported",
                automation_run_id="run-1",
                project_id="project-1",
                artifact_type="requirement_document",
                artifact_id="doc-1",
                artifact_version_id="doc-1-v1",
                source="document",
                authority="project",
                quote=quote,
                quote_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            ),
            SourceFact(
                source_fact_id="FACT-unrelated",
                automation_run_id="run-1",
                project_id="project-1",
                artifact_type="requirement_document",
                artifact_id="doc-2",
                artifact_version_id="doc-2-v1",
                source="document",
                authority="project",
                quote="An unrelated requirement.",
                quote_sha256=hashlib.sha256(
                    "An unrelated requirement.".encode("utf-8")
                ).hexdigest(),
            ),
        ]
        blueprint = {
            "obligations": [
                {
                    "key": "password-reset",
                    "source_ref": "doc-1-v1",
                    "source_quote": quote,
                }
            ],
            "clarifications": [
                {
                    "code": "reset-expiry",
                    "evidence_refs": ["doc-1-v1"],
                    "source_quote": quote,
                }
            ],
        }

        lineage = verified_blueprint_claim_lineage(blueprint, facts)

        self.assertEqual(
            [
                (item["claim_type"], item["claim_key"], item["source_fact_ids"])
                for item in lineage
            ],
            [
                ("OBLIGATION", "password-reset", ["FACT-supported"]),
                ("CLARIFICATION", "reset-expiry", ["FACT-supported"]),
            ],
        )
        self.assertEqual(len(lineage[0]["source_quote_sha256"]), 64)

    def test_blueprint_claim_lineage_fails_closed_for_unmapped_claim(self):
        blueprint = {
            "obligations": [
                {
                    "key": "missing-source",
                    "source_ref": "doc-missing-v1",
                    "source_quote": "No verified source fact supports this.",
                }
            ],
            "clarifications": [],
        }

        self.assertIsNone(verified_blueprint_claim_lineage(blueprint, []))

    def test_blueprint_receipt_excludes_facts_from_another_project_or_run(self):
        fact = SourceFact(
            source_fact_id="FACT-other-scope",
            automation_run_id="run-other",
            project_id="project-other",
            artifact_type="requirement_document",
            artifact_id="doc-1",
            artifact_version_id="doc-1-v1",
            source="document",
            authority="project",
            quote="The account owner can reset the password.",
            quote_sha256=hashlib.sha256(
                "The account owner can reset the password.".encode("utf-8")
            ).hexdigest(),
        )
        blueprint = {
            "capability": "testability_blueprint_compilation",
            "evidence_refs": ["doc-1-v1"],
            "confidence": 0.9,
            "warnings": [],
            "obligations": [
                {
                    "key": "password-reset",
                    "source_ref": "doc-1-v1",
                    "source_quote": fact.quote,
                }
            ],
            "clarifications": [],
        }

        self.assertIsNone(
            verified_blueprint_snapshot(
                blueprint,
                [fact],
                project_id="project-1",
                automation_run_id="run-1",
            )
        )
        self.assertIsNone(
            verified_blueprint_claim_lineage(
                blueprint,
                [fact],
                project_id="project-1",
                automation_run_id="run-1",
            )
        )

    def test_blueprint_rejects_ambiguous_reference_across_artifact_types(self):
        quote = "The account owner can reset the password."
        facts = [
            SourceFact(
                source_fact_id="FACT-document",
                automation_run_id="run-1",
                project_id="project-1",
                artifact_type="requirement_document",
                artifact_id="doc-1",
                artifact_version_id="shared-version-id",
                source="document",
                authority="project",
                quote=quote,
                quote_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            ),
            SourceFact(
                source_fact_id="FACT-test-case",
                automation_run_id="run-1",
                project_id="project-1",
                artifact_type="test_case_version",
                artifact_id="case-1",
                artifact_version_id="shared-version-id",
                source="database",
                authority="project",
                quote=quote,
                quote_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            ),
        ]
        blueprint = {
            "evidence_refs": ["shared-version-id"],
            "obligations": [
                {
                    "key": "password-reset",
                    "source_ref": "shared-version-id",
                    "source_quote": quote,
                }
            ],
            "clarifications": [],
        }

        self.assertIsNone(verified_blueprint_snapshot(blueprint, facts))
        self.assertIsNone(verified_blueprint_claim_lineage(blueprint, facts))

    def test_blueprint_receipt_rejects_fact_with_missing_or_tampered_quote_hash(self):
        quote = "The account owner can reset the password."
        fact = SourceFact(
            source_fact_id="FACT-hash-check",
            automation_run_id="run-1",
            project_id="project-1",
            artifact_type="requirement_document",
            artifact_id="doc-1",
            artifact_version_id="doc-1-v1",
            source="document",
            authority="project",
            quote=quote,
            quote_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        )
        blueprint = {
            "capability": "testability_blueprint_compilation",
            "evidence_refs": ["doc-1-v1"],
            "confidence": 0.9,
            "warnings": [],
            "obligations": [
                {
                    "key": "password-reset",
                    "source_ref": "doc-1-v1",
                    "source_quote": quote,
                }
            ],
            "clarifications": [],
        }

        self.assertIsNotNone(verified_blueprint_snapshot(blueprint, [fact]))
        self.assertIsNone(
            verified_blueprint_snapshot(
                blueprint, [fact.model_copy(update={"quote_sha256": "0" * 64})]
            )
        )
        self.assertIsNone(
            verified_blueprint_snapshot(
                blueprint, [fact.model_copy(update={"quote_sha256": None})]
            )
        )

    def test_blueprint_artifact_lineage_requires_same_project_readback(self):
        blueprint = {"obligations": [{"key": "login-valid"}]}
        claims = [
            {
                "claim_type": "OBLIGATION",
                "claim_key": "login-valid",
                "source_fact_ids": ["FACT-login"],
            }
        ]
        observations = [
            {
                "tool_name": "process_ingested_requirement_document",
                "status": "COMPLETED",
                "verification": {"status": "COMPLETED"},
                "result": {
                    "blueprint_artifact_coverage": [
                        {
                            "obligation_key": "login-valid",
                            "requirement_version_ids": ["REQV-1"],
                            "test_case_ids": ["TC-1"],
                            "test_case_version_ids": ["TCV-1"],
                        }
                    ],
                    "verification": {
                        "project_id": "project-1",
                        "checks": [
                            {"artifact_type": "requirement_version", "artifact_id": "REQV-1"},
                            {"artifact_type": "test_case", "artifact_id": "TC-1"},
                            {"artifact_type": "test_case_version", "artifact_id": "TCV-1"},
                        ],
                    },
                },
            }
        ]

        lineage, rejected_count = verified_blueprint_artifact_lineage(
            blueprint, claims, observations, "project-1"
        )

        self.assertEqual(rejected_count, 0)
        self.assertEqual(
            {(item["artifact_type"], item["artifact_id"]) for item in lineage},
            {
                ("requirement_version", "REQV-1"),
                ("test_case", "TC-1"),
                ("test_case_version", "TCV-1"),
            },
        )
        self.assertTrue(all(item["source_fact_ids"] == ["FACT-login"] for item in lineage))

    def test_blueprint_artifact_lineage_rejects_foreign_project_readback(self):
        blueprint = {"obligations": [{"key": "login-valid"}]}
        claims = [
            {
                "claim_type": "OBLIGATION",
                "claim_key": "login-valid",
                "source_fact_ids": ["FACT-login"],
            }
        ]
        observations = [
            {
                "tool_name": "process_ingested_requirement_document",
                "status": "COMPLETED",
                "verification": {"status": "COMPLETED"},
                "result": {
                    "blueprint_artifact_coverage": [
                        {"obligation_key": "login-valid", "requirement_version_ids": ["REQV-other"]}
                    ],
                    "verification": {
                        "project_id": "another-project",
                        "checks": [
                            {"artifact_type": "requirement_version", "artifact_id": "REQV-other"}
                        ],
                    },
                },
            }
        ]

        lineage, rejected_count = verified_blueprint_artifact_lineage(
            blueprint, claims, observations, "project-1"
        )

        self.assertEqual(lineage, [])
        self.assertEqual(rejected_count, 1)

    def test_blueprint_artifact_lineage_rejects_unverified_observation(self):
        blueprint = {"obligations": [{"key": "login-valid"}]}
        claims = [
            {
                "claim_type": "OBLIGATION",
                "claim_key": "login-valid",
                "source_fact_ids": ["FACT-login"],
            }
        ]
        observations = [
            {
                "tool_name": "process_ingested_requirement_document",
                "status": "FAILED",
                "verification": {"status": "FAILED"},
                "result": {
                    "blueprint_artifact_coverage": [
                        {
                            "obligation_key": "login-valid",
                            "requirement_version_ids": ["REQV-1"],
                            "test_case_version_ids": ["TCV-1"],
                        }
                    ],
                    "verification": {
                        "project_id": "project-1",
                        "checks": [
                            {"artifact_type": "requirement_version", "artifact_id": "REQV-1"},
                            {"artifact_type": "test_case_version", "artifact_id": "TCV-1"},
                        ],
                    },
                },
            }
        ]

        lineage, rejected_count = verified_blueprint_artifact_lineage(
            blueprint, claims, observations, "project-1"
        )

        self.assertEqual(lineage, [])
        self.assertEqual(rejected_count, 1)

    def test_completed_blueprint_obligation_requires_requirement_and_frozen_case_links(self):
        blueprint = {
            "obligations": [{"key": "covered"}, {"key": "missing-case"}, {"key": "missing-both"}]
        }
        lineage = [
            {
                "obligation_key": "covered",
                "artifact_type": "requirement_version",
                "artifact_id": "REQV-1",
            },
            {
                "obligation_key": "covered",
                "artifact_type": "test_case_version",
                "artifact_id": "TCV-1",
            },
            {
                "obligation_key": "missing-case",
                "artifact_type": "requirement_version",
                "artifact_id": "REQV-2",
            },
        ]

        missing = missing_blueprint_artifact_coverage_count(blueprint, lineage)

        self.assertEqual(missing, 2)
        self.assertTrue(has_provenance_gap(0, 0, 0, missing))

    def test_successful_requirement_compilation_without_blueprint_is_a_provenance_gap(self):
        observations = [{
            "tool_name": "process_ingested_requirement_document",
            "status": "COMPLETED",
            "verification": {"status": "COMPLETED"},
            "result": {"status": "COMPLETED"},
        }]

        blueprint, rejected_count = verified_blueprint_from_observations(
            observations, []
        )

        self.assertIsNone(blueprint)
        self.assertEqual(rejected_count, 1)
        self.assertTrue(has_provenance_gap(0, 0, rejected_count))

    def test_grounded_blueprint_is_preserved_when_import_is_partially_incomplete(self):
        quote = "Người dùng đăng nhập bằng mật khẩu hợp lệ."
        source_fact = type(
            "Fact",
            (),
            {
                "artifact_type": "requirement_document",
                "artifact_id": "doc-1",
                "artifact_version_id": "doc-1-v2",
                "quote": quote,
                "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            },
        )()
        candidate = {
            "capability": "testability_blueprint_compilation",
            "obligations": [
                {
                    "key": "login-valid",
                    "obligation": "Đăng nhập bằng thông tin hợp lệ",
                    "source_ref": "doc-1",
                    "source_quote": quote,
                }
            ],
            "clarifications": [],
            "evidence_refs": ["doc-1"],
            "confidence": 0.9,
            "warnings": [],
        }
        observations = [{
            "tool_name": "process_ingested_requirement_document",
            "status": "FAILED",
            "reason_code": "AUTOMATION_PARTIAL_FAILURE",
            "verification": {"status": "INCOMPLETE"},
            "result": {"testability_blueprint": candidate},
        }]

        blueprint, rejected_count = verified_blueprint_from_observations(
            observations, [source_fact]
        )

        self.assertIsNotNone(blueprint)
        self.assertEqual(blueprint["obligations"][0]["source_quote"], quote)
        self.assertEqual(rejected_count, 0)

    def test_nonterminal_or_noncompiler_observations_do_not_require_blueprint(self):
        observations = [
            {
                "tool_name": "process_changed_requirement_version",
                "status": "FAILED",
                "verification": {"status": "FAILED"},
                "result": {},
            },
            {
                "tool_name": "get_requirement_version",
                "status": "COMPLETED",
                "verification": {"status": "COMPLETED"},
                "result": {},
            },
        ]

        blueprint, rejected_count = verified_blueprint_from_observations(
            observations, []
        )

        self.assertIsNone(blueprint)
        self.assertEqual(rejected_count, 0)


if __name__ == "__main__":
    unittest.main()

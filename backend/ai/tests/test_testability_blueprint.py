import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.prompts.requirement_templates import (
    REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS,
    requirement_document_synthesis_instruction,
)
from src.prompts.test_generation import requirement_test_generation_instruction
from src.prompts.testability_benchmark import CLARIFICATION_BASELINE
from src.prompts.testability_blueprint import TESTABILITY_BLUEPRINT_COMPILATION
from src.schemas.automation import AutomationFact
from src.schemas.inference_requirements import RequirementTemplateSuggestionOutput
from src.schemas.inference_requirements import (
    TestabilityBlueprintCompilationOutput as BlueprintCompilationOutputSchema,
)
from src.services.testability_blueprint import (
    _bounded_blueprint_warnings,
    compile_testability_blueprint,
    facts_bound_to_authorized_evidence,
    map_blueprint_obligations_to_requirements,
    obligations_supported_by_requirement_version,
    verified_fact_evidence,
)
from src.tools.requirement_document_workflow import verified_document_facts


class TestabilityBlueprintTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fact = AutomationFact(
            artifact_type="RequirementDocument",
            artifact_id="doc-1",
            artifact_version_id="doc-1-v1",
            source="document",
            authority="project",
            quote="Mật khẩu phải có ít nhất 12 ký tự",
            source_start=0,
            source_end=len("Mật khẩu phải có ít nhất 12 ký tự"),
        )
        self.evidence = {
            "doc-1-v1": {
                "artifact_id": "doc-1",
                "text": "Mật khẩu phải có ít nhất 12 ký tự",
            }
        }

    def test_aggregated_blueprint_warnings_respect_output_contract(self):
        warnings = [f"batch-{index}" for index in range(60)]

        result = _bounded_blueprint_warnings(warnings)

        self.assertEqual(len(result), 50)
        self.assertEqual(result[-1], "11 cảnh báo bổ sung đã được gộp")

    def test_prompt_uses_english_instructions_and_user_selected_output_language(self):
        self.assertIn("Compile a testability blueprint", TESTABILITY_BLUEPRINT_COMPILATION)
        self.assertIn("language explicitly requested by the user", TESTABILITY_BLUEPRINT_COMPILATION)
        self.assertIn("Do not turn a broad goal or label", TESTABILITY_BLUEPRINT_COMPILATION)
        self.assertIn("Do not ask for optional presentation details", TESTABILITY_BLUEPRINT_COMPILATION)
        self.assertIn("never join quotes, paraphrase them, or insert ellipses", TESTABILITY_BLUEPRINT_COMPILATION)
        self.assertIn(
            "preserve each independently testable claim as its own obligation",
            TESTABILITY_BLUEPRINT_COMPILATION,
        )
        self.assertIn("unlocks_obligation_keys", TESTABILITY_BLUEPRINT_COMPILATION)
        self.assertNotIn("Biên dịch", TESTABILITY_BLUEPRINT_COMPILATION)
        self.assertIn("language explicitly requested by the user", REQUIREMENT_TEMPLATE_SYNTHESIS_INSTRUCTIONS)
        self.assertIn("language explicitly requested by the user", CLARIFICATION_BASELINE)
        test_generation = requirement_test_generation_instruction()
        self.assertIn("language explicitly requested by the user", test_generation)
        self.assertIn("State the documented, observable outcome directly", test_generation)
        self.assertIn("instead of inventing a value", test_generation)
        compiled_generation = requirement_test_generation_instruction(
            [{"key": "LOGIN_ACCESS", "obligation": "Đăng nhập thành công", "source_quote": "Đăng nhập đúng."}]
        )
        self.assertIn(
            "One Test Case may cover multiple keys only when its same steps",
            compiled_generation,
        )
        self.assertIn("Retain every key separately", compiled_generation)
        self.assertIn("Avoid duplicates", compiled_generation)

    def test_template_prompt_maps_grounded_obligations_to_acceptance_criteria(self):
        quote = "Mật khẩu phải có ít nhất 12 ký tự."
        instruction = requirement_document_synthesis_instruction(
            {
                "obligations": [
                    {
                        "key": "password-minimum-length",
                        "obligation": "Kiểm tra độ dài mật khẩu tối thiểu",
                        "source_ref": "doc-1-v1",
                        "source_quote": quote,
                    }
                ],
                "clarifications": [],
            },
        )

        self.assertIn("copy its exact source quote into acceptance_criteria", instruction)
        self.assertIn(quote, instruction)
        self.assertIn(
            "Keep unrelated grounded Requirements when another needs clarification",
            instruction,
        )

    def test_template_prompt_owns_source_specific_actor_and_quote_rules(self):
        properties = RequirementTemplateSuggestionOutput.model_json_schema()["properties"]
        self.assertIn("actors", properties)
        self.assertIn("acceptance_criteria", properties)
        instruction = requirement_document_synthesis_instruction(
            {"obligations": [], "clarifications": []}
        )
        self.assertIn("actors field is not limited to User Stories", instruction)
        self.assertIn("copy its exact source quote into acceptance_criteria", instruction)

    def test_unknown_clarification_links_reject_the_entire_blueprint(self):
        with self.assertRaisesRegex(ValueError, "blueprint_clarification_unknown_obligation_link"):
            BlueprintCompilationOutputSchema.model_validate(
                {
                    "capability": "testability_blueprint_compilation",
                    "obligations": [],
                    "clarifications": [
                        {
                            "code": "CONFLICT_1",
                            "category": "CONTRADICTION",
                            "question": "Quy tắc nào được áp dụng?",
                            "reason": "Hai nguồn quy định kết quả khác nhau nên chưa thể xác định kết quả cần kiểm thử.",
                            "priority": "HIGH",
                            "evidence_refs": ["doc-1-v1"],
                            "source_quote": "Tài khoản bị khóa sau 5 lần nhập sai.",
                            "unlocks_obligation_keys": ["OBLIGATION_NOT_RETURNED"],
                        }
                    ],
                    "evidence_refs": ["doc-1-v1"],
                    "confidence": 0.9,
                    "warnings": [],
                }
            )

    def test_evidence_includes_only_allowed_exact_source_facts(self):
        unauthorized = self.fact.model_copy(update={"artifact_id": "doc-2"})
        result = verified_fact_evidence(
            [self.fact, unauthorized], self.evidence, {"doc-1"}
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, self.fact.quote)

    def test_fact_evidence_resolves_matching_source_from_multiple_chunks(self):
        evidence = {
            "doc-1-v1": [
                {
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v1",
                    "text": "Đoạn khác trong tài liệu.",
                },
                {
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v1",
                    "text": self.fact.quote,
                },
            ]
        }

        result = verified_fact_evidence([self.fact], evidence, {"doc-1"})

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, self.fact.quote)

    def test_canonical_fact_uses_full_source_when_retrieved_chunk_appears_first(self):
        quote = self.fact.quote
        canonical_text = f"{'x' * 120}\n{quote}\nPhần tiếp theo."
        start = canonical_text.index(quote)
        fact = self.fact.model_copy(
            update={
                "source_start": start,
                "source_end": start + len(quote),
                "source_offset_basis": "CANONICAL_TEXT",
            }
        )
        evidence = {
            "doc-1-v1": [
                {
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v1",
                    "text": quote,
                },
                {
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v1",
                    "source_offset_basis": "RETRIEVED_CHUNK",
                    "relationship_path": ["doc-1"],
                    "text": canonical_text,
                },
                {
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v1",
                    "source_offset_basis": "CANONICAL_TEXT",
                    "relationship_path": ["doc-root", "doc-1"],
                    "text": canonical_text,
                },
            ]
        }

        result = verified_fact_evidence([fact], evidence, {"doc-root", "doc-1"})

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].verified_facts[0].source_start, start)
        self.assertEqual(result[0].verified_facts[0].source_end, start + len(quote))
        self.assertEqual(result[0].relationship_paths, [["doc-root", "doc-1"]])

    def test_canonical_fact_rejects_a_chunk_local_offset_without_canonical_source(self):
        quote = self.fact.quote
        canonical_text = f"{'x' * 120}\n{quote}\nPhần tiếp theo."
        start = canonical_text.index(quote)
        fact = self.fact.model_copy(
            update={
                "source_start": start,
                "source_end": start + len(quote),
                "source_offset_basis": "CANONICAL_TEXT",
            }
        )
        evidence = {
            "doc-1-v1": [
                {
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v1",
                    "source_offset_basis": "RETRIEVED_CHUNK",
                    "text": canonical_text,
                }
            ]
        }

        self.assertEqual(verified_fact_evidence([fact], evidence, {"doc-1"}), [])

    def test_fact_evidence_rejects_version_id_mismatch(self):
        mismatched_evidence = {
            "doc-1-v1": {
                **self.evidence["doc-1-v1"],
                "artifact_version_id": "doc-1-v2",
            }
        }
        self.assertEqual(
            verified_fact_evidence(
                [self.fact], mismatched_evidence, {"doc-1"}
            ),
            [],
        )
        self.assertEqual(
            facts_bound_to_authorized_evidence(
                [self.fact],
                mismatched_evidence,
                {"doc-1"},
                {"doc-1": ["doc-1"]},
            ),
            [],
        )

    def test_fact_metadata_must_match_authoritative_source_metadata(self):
        mismatched_type = {
            "doc-1-v1": {
                **self.evidence["doc-1-v1"],
                "artifact_type": "test_case",
            }
        }
        self.assertEqual(
            verified_fact_evidence([self.fact], mismatched_type, {"doc-1"}),
            [],
        )

        authoritative_source = {
            "doc-1-v1": {
                **self.evidence["doc-1-v1"],
                "artifact_type": "requirement_document",
                "authority": "PROJECT_REFERENCE",
            }
        }
        authoritative_fact = self.fact.model_copy(
            update={
                "artifact_type": "requirement_document",
                "authority": "PROJECT_REFERENCE",
            }
        )
        evidence = verified_fact_evidence(
            [authoritative_fact], authoritative_source, {"doc-1"}
        )
        self.assertEqual(evidence[0].artifact_type, "requirement_document")
        self.assertEqual(evidence[0].authority, "PROJECT_REFERENCE")

    def test_evidence_keeps_only_well_formed_verified_fact_lineage(self):
        verified = self.fact.model_copy(
            update={"relationship_path": ["doc-root", "doc-mid", "doc-1"]}
        )
        malformed = self.fact.model_copy(
            update={"relationship_path": ["", "forged-node"]}
        )
        evidence = {
            "doc-1-v1": {
                "artifact_id": "doc-1",
                "text": self.fact.quote,
                "relationship_path": ["doc-root", "doc-mid", "doc-1"],
            }
        }
        result = verified_fact_evidence(
            [verified, malformed],
            evidence,
            {"doc-root", "doc-mid", "doc-1"},
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0].relationship_paths,
            [["doc-root", "doc-mid", "doc-1"]],
        )

    def test_evidence_discards_graph_paths_that_are_not_authorized_document_ancestry(self):
        unrelated_scope = self.fact.model_copy(
            update={"relationship_path": ["doc-1", "unrelated-test-case"]}
        )
        wrong_terminal = self.fact.model_copy(
            update={"relationship_path": ["doc-root", "doc-other"]}
        )
        cyclic = self.fact.model_copy(
            update={"relationship_path": ["doc-root", "doc-mid", "doc-root", "doc-1"]}
        )

        result = verified_fact_evidence(
            [unrelated_scope, wrong_terminal, cyclic],
            self.evidence,
            {"doc-root", "doc-mid", "doc-1", "doc-other"},
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].relationship_paths, [])

    def test_fact_lineage_is_rebound_from_authorized_source_not_tool_input(self):
        forged = self.fact.model_copy(
            update={"relationship_path": ["attacker-root", "doc-1"]}
        )
        evidence = {
            "doc-1-v1": {
                "artifact_id": "doc-1",
                "text": self.fact.quote,
                "relationship_path": ["doc-root", "series-doc", "doc-1"],
            }
        }

        verified = facts_bound_to_authorized_evidence(
            [forged],
            evidence,
            {"doc-root", "series-doc", "doc-1"},
            {"doc-1": ["doc-root", "series-doc", "doc-1"]},
        )

        self.assertEqual(len(verified), 1)
        self.assertEqual(
            verified[0].relationship_path,
            ["doc-root", "series-doc", "doc-1"],
        )

    def test_fact_offsets_are_rebound_to_verified_authoritative_positions(self):
        quote = self.fact.quote
        source_text = f"{quote} phần còn lại"
        evidence = {
            "doc-1-v1": {
                "artifact_id": "doc-1",
                "text": source_text,
            }
        }
        malformed_cases = [
            (self.fact, source_text, -1, len(quote) - 1),
            (self.fact, source_text, 0, len(source_text) + 1),
            (self.fact.model_copy(update={"quote": "x"}), "x", False, True),
        ]
        for fact, text, start, end in malformed_cases:
            with self.subTest(start=start, end=end):
                malformed = fact.model_copy(
                    update={"source_start": start, "source_end": end}
                )
                verified = facts_bound_to_authorized_evidence(
                    [malformed],
                    {"doc-1-v1": {"artifact_id": "doc-1", "text": text}},
                    {"doc-1"},
                    {"doc-1": ["doc-1"]},
                    {"doc-1": {"normalized_content": text}},
                )
                self.assertEqual(len(verified), 1)
                self.assertEqual(verified[0].source_start, 0)
                self.assertEqual(verified[0].source_end, len(fact.quote))
                self.assertEqual(verified[0].source_offset_basis, "CANONICAL_TEXT")

    def test_negative_source_citation_offsets_are_rejected(self):
        quote = self.fact.quote
        malformed = self.fact.model_copy(
            update={
                "source_start": -1,
                "source_end": len(quote) - 1,
                "source_offset_basis": "SOURCE_CITATION",
            }
        )
        evidence = {
            "doc-1-v1": {
                "artifact_id": "doc-1",
                "text": quote,
                "source_verification": "VERIFIED_REQUIREMENT_SOURCE_CITATION",
                "source_start": -1,
                "source_end": len(quote) - 1,
            }
        }

        self.assertEqual(verified_fact_evidence([malformed], evidence, {"doc-1"}), [])

    def test_fact_lineage_uses_api_verified_version_chain_not_graph_neighborhood(self):
        evidence = {
            "doc-1-v1": {
                "artifact_id": "doc-1",
                "text": self.fact.quote,
                "relationship_path": ["doc-1", "related-requirement", "doc-2"],
            }
        }

        verified = facts_bound_to_authorized_evidence(
            [self.fact],
            evidence,
            {"doc-root", "doc-1"},
            {"doc-1": ["doc-root", "doc-1"]},
        )

        self.assertEqual(len(verified), 1)
        self.assertEqual(verified[0].relationship_path, ["doc-root", "doc-1"])

    def test_fact_from_later_chunk_is_rebased_to_the_authoritative_document(self):
        quote = self.fact.quote
        evidence = {
            "doc-1-v1": [
                {
                    "artifact_type": "RequirementDocument",
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v1",
                    "text": "Đoạn khác ở đầu tài liệu.",
                },
                {
                    "artifact_type": "RequirementDocument",
                    "artifact_id": "doc-1",
                    "artifact_version_id": "doc-1-v1",
                    "text": f"Quy tắc: {quote}",
                },
            ]
        }
        authoritative_text = f"Mục mở đầu.\nQuy tắc: {quote}\nMục kết thúc."

        verified = facts_bound_to_authorized_evidence(
            [self.fact],
            evidence,
            {"doc-1"},
            {"doc-1": ["doc-1"]},
            {"doc-1": {"normalized_content": authoritative_text}},
        )

        self.assertEqual(len(verified), 1)
        self.assertEqual(verified[0].source_offset_basis, "CANONICAL_TEXT")
        self.assertEqual(
            authoritative_text[verified[0].source_start:verified[0].source_end],
            quote,
        )

    def test_fact_with_repeated_quote_is_not_given_a_guessed_document_position(self):
        quote = self.fact.quote
        evidence = {
            "doc-1-v1": [{**self.evidence["doc-1-v1"], "text": quote}]
        }
        authoritative_text = f"{quote}\nGhi chú.\n{quote}"

        verified = facts_bound_to_authorized_evidence(
            [self.fact],
            evidence,
            {"doc-1"},
            {"doc-1": ["doc-1"]},
            {"doc-1": {"normalized_content": authoritative_text}},
        )

        self.assertEqual(verified, [])

    def test_repeated_quote_uses_an_already_verified_canonical_span(self):
        quote = self.fact.quote
        authoritative_text = f"{quote}\nGhi chú.\n{quote}"
        second_position = authoritative_text.rfind(quote)
        canonical_fact = self.fact.model_copy(
            update={
                "source_start": second_position,
                "source_end": second_position + len(quote),
                "source_offset_basis": "CANONICAL_TEXT",
            }
        )

        verified = facts_bound_to_authorized_evidence(
            [canonical_fact],
            {"doc-1-v1": [{**self.evidence["doc-1-v1"], "text": quote}]},
            {"doc-1"},
            {"doc-1": ["doc-1"]},
            {"doc-1": {"normalized_content": authoritative_text}},
        )

        self.assertEqual(len(verified), 1)
        self.assertEqual(verified[0].source_start, second_position)
        self.assertEqual(verified[0].source_end, second_position + len(quote))
        self.assertEqual(verified[0].source_offset_basis, "CANONICAL_TEXT")

    def test_fact_is_rejected_when_current_document_content_cannot_be_read_back(self):
        verified = facts_bound_to_authorized_evidence(
            [self.fact],
            self.evidence,
            {"doc-1"},
            {"doc-1": ["doc-1"]},
            {"doc-1": {"_id": "doc-1", "status": "READY"}},
        )

        self.assertEqual(verified, [])

    async def test_blueprint_compiler_receives_verified_lineage_with_source_quote(self):
        fact = self.fact.model_copy(update={"relationship_path": ["forged", "doc-1"]})
        evidence = {
            "doc-1-v1": {
                "artifact_id": "doc-1",
                "text": self.fact.quote,
                "relationship_path": ["doc-root", "series-doc", "doc-1"],
            }
        }
        model_result = {
            "status": "SUCCESS",
            "degraded_mode": None,
            "evidence_refs": ["doc-1-v1"],
            "obligations": [{
                "key": "source-obligation",
                "obligation": "Kiểm thử hành vi được nêu trong nguồn.",
                "source_ref": "doc-1-v1",
                "source_quote": self.fact.quote,
            }],
            "clarifications": [],
        }
        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_: model_result)),
        ) as generate:
            result = await compile_testability_blueprint(
                "project-1",
                [fact],
                evidence,
                {"doc-root", "series-doc", "doc-1"},
            )

        self.assertEqual(result["status"], "SUCCESS")
        request = generate.await_args.args[0]
        self.assertEqual(request.evidence[0].text, fact.quote)
        self.assertEqual(len(request.evidence[0].verified_facts), 1)
        self.assertEqual(request.evidence[0].verified_facts[0].quote, fact.quote)
        self.assertEqual(request.evidence[0].verified_facts[0].fact_kind, fact.fact_kind)
        self.assertEqual(
            request.evidence[0].relationship_paths,
            [["doc-root", "series-doc", "doc-1"]],
        )

    async def test_blueprint_compiles_independent_same_version_sources_without_overwrite(self):
        documents = {
            "doc-registered": {
                "_id": "doc-registered",
                "source_version": "1",
                "normalized_content": "Chỉ tài khoản đã đăng ký mới được đăng nhập.",
            },
            "doc-password": {
                "_id": "doc-password",
                "source_version": "1",
                "normalized_content": "Mật khẩu phải có ít nhất 12 ký tự.",
            },
        }
        facts, evidence = verified_document_facts(
            ["doc-registered", "doc-password"], documents
        )
        model_output = {
            "status": "SUCCESS",
            "degraded_mode": None,
            "evidence_refs": ["doc-registered", "doc-password"],
            "obligations": [
                {
                    "key": "registered-account-only",
                    "obligation": "Tài khoản chưa đăng ký không được đăng nhập",
                    "source_ref": "doc-registered",
                    "source_quote": "Chỉ tài khoản đã đăng ký mới được đăng nhập.",
                },
                {
                    "key": "password-minimum-length",
                    "obligation": "Mật khẩu có độ dài tối thiểu 12 ký tự",
                    "source_ref": "doc-password",
                    "source_quote": "Mật khẩu phải có ít nhất 12 ký tự.",
                },
            ],
            "clarifications": [],
        }
        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(
                return_value=SimpleNamespace(model_dump=lambda **_: model_output)
            ),
        ) as generate:
            result = await compile_testability_blueprint(
                "project-1",
                facts,
                evidence,
                {"doc-registered", "doc-password"},
            )

        self.assertEqual(result["status"], "SUCCESS")
        request = generate.await_args.args[0]
        self.assertEqual(
            {item.artifact_version_id: item.text for item in request.evidence},
            {
                "doc-registered": "Chỉ tài khoản đã đăng ký mới được đăng nhập.",
                "doc-password": "Mật khẩu phải có ít nhất 12 ký tự.",
            },
        )
        self.assertEqual(
            {item["source_ref"] for item in result["obligations"]},
            {"doc-registered", "doc-password"},
        )

    def test_fact_requires_revision_and_exact_source_span(self):
        missing_revision = self.fact.model_copy(update={"artifact_version_id": None})
        wrong_span = self.fact.model_copy(update={"source_start": 1, "source_end": len(self.fact.quote) + 1})
        wrong_quote = self.fact.model_copy(update={"quote": "Mật khẩu phải có ít nhất 20 ký tự"})
        result = verified_fact_evidence(
            [missing_revision, wrong_span, wrong_quote], self.evidence, {"doc-1"}
        )
        self.assertEqual(result, [])

    async def test_missing_verified_evidence_does_not_call_model(self):
        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(),
        ) as generate:
            result = await compile_testability_blueprint("project-1", [], {}, {"doc-1"})
        self.assertEqual(result["status"], "DEGRADED")
        self.assertIn("NO_VERIFIED_BLUEPRINT_EVIDENCE", result["reason_codes"])
        generate.assert_not_awaited()

    async def test_model_obligation_with_fabricated_quote_is_rejected(self):
        model_result = {
            "status": "SUCCESS",
            "degraded_mode": None,
            "evidence_refs": ["doc-1-v1"],
            "obligations": [
                {
                    "key": "password-minimum-length",
                    "obligation": "Kiểm tra độ dài tối thiểu của mật khẩu",
                    "source_ref": "doc-1-v1",
                    "source_quote": "Mật khẩu phải có ít nhất 20 ký tự",
                }
            ],
            "clarifications": [],
        }
        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_: model_result)),
        ):
            result = await compile_testability_blueprint(
                "project-1", [self.fact], self.evidence, {"doc-1"}
            )
        self.assertEqual(result["status"], "DEGRADED")
        self.assertIn("BLUEPRINT_OBLIGATION_GROUNDING_INVALID", result["reason_codes"])
        self.assertEqual(result["obligations"], [])

    async def test_model_obligation_quote_inside_another_word_is_rejected(self):
        fact = self.fact.model_copy(
            update={
                "quote": "invalid",
                "source_start": 0,
                "source_end": len("invalid"),
            }
        )
        evidence = {"doc-1-v1": {"artifact_id": "doc-1", "text": "invalid"}}
        model_result = {
            "status": "SUCCESS",
            "degraded_mode": None,
            "evidence_refs": ["doc-1-v1"],
            "obligations": [{
                "key": "valid-token",
                "obligation": "Kiểm tra từ hợp lệ.",
                "source_ref": "doc-1-v1",
                "source_quote": "valid",
            }],
            "clarifications": [],
        }
        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_: model_result)),
        ):
            result = await compile_testability_blueprint(
                "project-1", [fact], evidence, {"doc-1"}
            )

        self.assertEqual(result["status"], "DEGRADED")
        self.assertIn("BLUEPRINT_OBLIGATION_GROUNDING_INVALID", result["reason_codes"])

    async def test_obligation_source_must_be_listed_in_blueprint_evidence_refs(self):
        second_fact = self.fact.model_copy(
            update={
                "artifact_id": "doc-2",
                "artifact_version_id": "doc-2-v1",
                "quote": "Mã xác minh có hiệu lực trong 10 phút.",
                "source_start": 0,
                "source_end": len("Mã xác minh có hiệu lực trong 10 phút."),
            }
        )
        evidence = {
            **self.evidence,
            "doc-2-v1": {
                "artifact_id": "doc-2",
                "artifact_version_id": "doc-2-v1",
                "text": second_fact.quote,
            },
        }
        model_result = {
            "status": "SUCCESS",
            "degraded_mode": None,
            "evidence_refs": ["doc-2-v1"],
            "obligations": [{
                "key": "password-minimum-length",
                "obligation": "Kiểm tra độ dài mật khẩu",
                "source_ref": "doc-1-v1",
                "source_quote": self.fact.quote,
            }],
            "clarifications": [],
        }

        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_: model_result)),
        ):
            result = await compile_testability_blueprint(
                "project-1",
                [self.fact, second_fact],
                evidence,
                {"doc-1", "doc-2"},
            )

        self.assertEqual(result["status"], "DEGRADED")
        self.assertIn("BLUEPRINT_EVIDENCE_REFERENCE_INCOMPLETE", result["reason_codes"])
        self.assertEqual(result["obligations"], [])

    async def test_clarification_sources_must_be_listed_in_blueprint_evidence_refs(self):
        second_fact = self.fact.model_copy(
            update={
                "artifact_id": "doc-2",
                "artifact_version_id": "doc-2-v1",
                "quote": "Mã xác minh có hiệu lực trong 10 phút.",
                "source_start": 0,
                "source_end": len("Mã xác minh có hiệu lực trong 10 phút."),
            }
        )
        evidence = {
            **self.evidence,
            "doc-2-v1": {
                "artifact_id": "doc-2",
                "artifact_version_id": "doc-2-v1",
                "text": second_fact.quote,
            },
        }
        model_result = {
            "status": "SUCCESS",
            "degraded_mode": None,
            "evidence_refs": ["doc-2-v1"],
            "obligations": [],
            "clarifications": [{
                "code": "MISSING_LOGIN_LIMIT",
                "category": "OMISSION",
                "question": "Mã xác minh được phép nhập sai bao nhiêu lần?",
                "reason": "Nguồn chưa nêu giới hạn số lần nhập sai.",
                "priority": "MEDIUM",
                "evidence_refs": ["doc-1-v1"],
                "source_quote": self.fact.quote,
                "unlocks_obligation_keys": [],
            }],
        }

        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_: model_result)),
        ):
            result = await compile_testability_blueprint(
                "project-1",
                [self.fact, second_fact],
                evidence,
                {"doc-1", "doc-2"},
            )

        self.assertEqual(result["status"], "DEGRADED")
        self.assertIn("BLUEPRINT_EVIDENCE_REFERENCE_INCOMPLETE", result["reason_codes"])
        self.assertEqual(result["clarifications"], [])

    async def test_blueprint_obligation_must_be_grounded_in_an_extracted_fact(self):
        surrounding_text = (
            f"{self.fact.quote}. Tài liệu cũng nhắc tới hỗ trợ khách hàng."
        )
        evidence = {
            "doc-1-v1": {
                "artifact_id": "doc-1",
                "text": surrounding_text,
            }
        }
        model_result = {
            "status": "SUCCESS",
            "degraded_mode": None,
            "evidence_refs": ["doc-1-v1"],
            "obligations": [
                {
                    "key": "unsupported-customer-support",
                    "obligation": "Kiểm tra hỗ trợ khách hàng",
                    "source_ref": "doc-1-v1",
                    "source_quote": "Tài liệu cũng nhắc tới hỗ trợ khách hàng.",
                }
            ],
            "clarifications": [],
        }
        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_: model_result)),
        ):
            result = await compile_testability_blueprint(
                "project-1", [self.fact], evidence, {"doc-1"}
            )

        self.assertEqual(result["status"], "DEGRADED")
        self.assertIn("BLUEPRINT_OBLIGATION_GROUNDING_INVALID", result["reason_codes"])
        self.assertEqual(result["obligations"], [])

    async def test_blueprint_clarification_must_be_grounded_in_an_extracted_fact(self):
        surrounding_text = (
            f"{self.fact.quote}. Tài liệu cũng nhắc tới hỗ trợ khách hàng."
        )
        evidence = {
            "doc-1-v1": {
                "artifact_id": "doc-1",
                "text": surrounding_text,
            }
        }
        model_result = {
            "status": "SUCCESS",
            "degraded_mode": None,
            "evidence_refs": ["doc-1-v1"],
            "obligations": [],
            "clarifications": [
                {
                    "code": "CUSTOMER_SUPPORT_RULE",
                    "category": "OMISSION",
                    "question": (
                        "Hỗ trợ khách hàng cần được xử lý theo quy tắc nào?"
                    ),
                    "reason": (
                        "Cụm từ này không mô tả hành vi hay điều kiện có thể kiểm thử."
                    ),
                    "priority": "MEDIUM",
                    "evidence_refs": ["doc-1-v1"],
                    "source_quote": "Tài liệu cũng nhắc tới hỗ trợ khách hàng.",
                    "unlocks_obligation_keys": [],
                }
            ],
        }
        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_: model_result)),
        ):
            result = await compile_testability_blueprint(
                "project-1", [self.fact], evidence, {"doc-1"}
            )

        self.assertEqual(result["status"], "DEGRADED")
        self.assertIn("BLUEPRINT_CLARIFICATION_GROUNDING_INVALID", result["reason_codes"])
        self.assertEqual(result["clarifications"], [])

    async def test_conflicting_source_quote_cannot_be_synthetic_join(self):
        second_fact = self.fact.model_copy(
            update={
                "artifact_id": "doc-2",
                "artifact_version_id": "doc-2-v1",
                "quote": "Mật khẩu có thể ngắn hơn 12 ký tự",
                "source_start": 0,
                "source_end": len("Mật khẩu có thể ngắn hơn 12 ký tự"),
            }
        )
        evidence = {
            **self.evidence,
            "doc-2-v1": {
                "artifact_id": "doc-2",
                "text": "Mật khẩu có thể ngắn hơn 12 ký tự",
            },
        }
        synthetic_quote = f"{self.fact.quote} ... {second_fact.quote}"
        model_result = {
            "status": "SUCCESS",
            "degraded_mode": None,
            "evidence_refs": ["doc-1-v1", "doc-2-v1"],
            "obligations": [],
            "clarifications": [
                {
                    "key": "password-conflict",
                    "code": "PASSWORD_LENGTH_CONFLICT",
                    "category": "CONFLICT",
                    "question": "Quy tắc độ dài mật khẩu nào có hiệu lực?",
                    "reason": "Hai nguồn đưa ra quy tắc khác nhau.",
                    "evidence_refs": ["doc-1-v1", "doc-2-v1"],
                    "source_quote": synthetic_quote,
                    "unlocks_obligation_keys": [],
                }
            ],
        }
        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_: model_result)),
        ):
            result = await compile_testability_blueprint(
                "project-1", [self.fact, second_fact], evidence, {"doc-1", "doc-2"}
            )
        self.assertEqual(result["status"], "DEGRADED")
        self.assertIn("BLUEPRINT_CLARIFICATION_GROUNDING_INVALID", result["reason_codes"])
        self.assertEqual(result["clarifications"], [])

    async def test_clarification_requires_a_reason_for_new_compiler_output(self):
        model_result = {
            "status": "SUCCESS",
            "degraded_mode": None,
            "evidence_refs": ["doc-1-v1"],
            "obligations": [],
            "clarifications": [{
                "code": "MISSING_RULE",
                "category": "OMISSION",
                "question": "Quy tắc này áp dụng trong trường hợp nào?",
                "evidence_refs": ["doc-1-v1"],
                "source_quote": self.fact.quote,
                "unlocks_obligation_keys": [],
            }],
        }
        with patch(
            "src.services.testability_blueprint.generate_ai_automation",
            new=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_: model_result)),
        ):
            result = await compile_testability_blueprint(
                "project-1", [self.fact], self.evidence, {"doc-1"}
            )
        self.assertEqual(result["status"], "DEGRADED")
        self.assertIn("BLUEPRINT_CLARIFICATION_REASON_MISSING", result["reason_codes"])
        self.assertEqual(result["clarifications"], [])

    async def test_large_blueprint_evidence_is_compiled_in_configured_batches(self):
        source_parts = []
        facts = []
        cursor = 0
        for index in range(3):
            quote = f"Điều khoản {index:03d}: " + ("x" * 2500)
            if source_parts:
                cursor += 1
            facts.append(
                AutomationFact(
                    artifact_type="requirement_document",
                    artifact_id="large-doc",
                    artifact_version_id="large-doc-v1",
                    source="document",
                    authority="project",
                    quote=quote,
                    source_start=cursor,
                    source_end=cursor + len(quote),
                    source_offset_basis="CANONICAL_TEXT",
                )
            )
            source_parts.append(quote)
            cursor += len(quote)
        source_text = "\n".join(source_parts)
        evidence_by_ref = {
            "large-doc-v1": {
                "artifact_id": "large-doc",
                "artifact_version_id": "large-doc-v1",
                "source_offset_basis": "CANONICAL_TEXT",
                "text": source_text,
            }
        }
        self.assertEqual(
            len(verified_fact_evidence(facts, evidence_by_ref, {"large-doc"})), 3
        )
        batch_sizes = []

        async def compile_batch(request):
            batch_sizes.append(len(request.evidence))
            evidence = request.evidence[0]
            quote = evidence.verified_facts[0].quote
            output = {
                "status": "SUCCESS",
                "degraded_mode": None,
                "evidence_refs": [evidence.artifact_version_id],
                "obligations": [{
                    "key": "SAME_MODEL_KEY",
                    "obligation": f"Kiểm tra điều khoản {quote[:20]}",
                    "source_ref": evidence.artifact_version_id,
                    "source_quote": quote,
                }],
                "clarifications": [],
                "confidence": 0.82,
                "warnings": [],
            }
            return SimpleNamespace(model_dump=lambda **_: output)

        with (
            patch("src.services.testability_blueprint.settings.AI_AGENT_MAX_EVIDENCE_ITEMS", 2),
            patch(
                "src.services.testability_blueprint.generate_ai_automation",
                new=AsyncMock(side_effect=compile_batch),
            ),
        ):
            result = await compile_testability_blueprint(
                "project-1", facts, evidence_by_ref, {"large-doc"}
            )

        self.assertEqual(batch_sizes, [2, 1], result)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(len(result["obligations"]), 2)
        self.assertEqual(
            [item["key"] for item in result["obligations"]],
            ["B001-SAME_MODEL_KEY", "B002-SAME_MODEL_KEY"],
        )

        failure_calls = 0

        async def fail_second_batch(request):
            nonlocal failure_calls
            failure_calls += 1
            if failure_calls == 1:
                return await compile_batch(request)
            raise RuntimeError("provider unavailable")

        with (
            patch("src.services.testability_blueprint.settings.AI_AGENT_MAX_EVIDENCE_ITEMS", 2),
            patch(
                "src.services.testability_blueprint.generate_ai_automation",
                new=AsyncMock(side_effect=fail_second_batch),
            ),
        ):
            failed_result = await compile_testability_blueprint(
                "project-1", facts, evidence_by_ref, {"large-doc"}
            )

        self.assertEqual(failed_result["status"], "DEGRADED")
        self.assertEqual(
            failed_result["reason_codes"], ["BLUEPRINT_BATCH_COMPILATION_FAILED"]
        )
        self.assertEqual(failed_result["obligations"], [])

    async def test_empty_blueprint_batch_is_reported_when_other_batches_succeed(self):
        second_fact = self.fact.model_copy(
            update={
                "artifact_id": "doc-2",
                "artifact_version_id": "doc-2-v1",
                "quote": "Trang đăng nhập có logo của hệ thống.",
                "source_start": 0,
                "source_end": len("Trang đăng nhập có logo của hệ thống."),
            }
        )
        evidence = {
            **self.evidence,
            "doc-2-v1": {
                "artifact_id": "doc-2",
                "artifact_version_id": "doc-2-v1",
                "text": second_fact.quote,
            },
        }

        async def compile_batch(request):
            item = request.evidence[0]
            if item.artifact_version_id == "doc-1-v1":
                output = {
                    "status": "SUCCESS",
                    "degraded_mode": None,
                    "evidence_refs": [item.artifact_version_id],
                    "obligations": [],
                    "clarifications": [],
                    "confidence": 0.8,
                    "warnings": [],
                }
            else:
                output = {
                    "status": "SUCCESS",
                    "degraded_mode": None,
                    "evidence_refs": [item.artifact_version_id],
                    "obligations": [{
                        "key": "logo-display",
                        "obligation": "Kiểm tra logo trang đăng nhập",
                        "source_ref": item.artifact_version_id,
                        "source_quote": second_fact.quote,
                    }],
                    "clarifications": [],
                    "confidence": 0.8,
                    "warnings": [],
                }
            return SimpleNamespace(model_dump=lambda **_: output)

        with (
            patch("src.services.testability_blueprint.settings.AI_AGENT_MAX_EVIDENCE_ITEMS", 1),
            patch(
                "src.services.testability_blueprint.generate_ai_automation",
                new=AsyncMock(side_effect=compile_batch),
            ),
        ):
            result = await compile_testability_blueprint(
                "project-1",
                [self.fact, second_fact],
                evidence,
                {"doc-1", "doc-2"},
            )

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(len(result["obligations"]), 1)
        self.assertIn("BATCH_1:NO_TESTABILITY_OUTCOMES", result["warnings"])

    def test_legacy_blueprint_receipt_without_reason_remains_readable(self):
        output = BlueprintCompilationOutputSchema.model_validate({
            "capability": "testability_blueprint_compilation",
            "obligations": [],
            "clarifications": [{
                "code": "LEGACY",
                "category": "OMISSION",
                "question": "Cần làm rõ quy tắc?",
                "priority": "MEDIUM",
                "evidence_refs": ["doc-1-v1"],
                "source_quote": self.fact.quote,
            }],
            "evidence_refs": ["doc-1-v1"],
            "confidence": 0.5,
        })
        self.assertEqual(output.clarifications[0].reason, "")

    def test_obligations_must_belong_to_requirement_version_sources(self):
        obligation = {
            "key": "password-minimum-length",
            "source_ref": "doc-1-v1",
            "source_quote": self.fact.quote,
        }
        version = {
            "source_refs": [{
                "requirement_document_id": "doc-1",
                "source_version": "1",
                "content_hash": "hash-1",
                "source_start": 0,
                "source_end": len(self.fact.quote),
                "source_quote": self.fact.quote,
            }],
            "plain_text_projection": "Đăng nhập bằng mật khẩu",
            "acceptance_criteria": [],
        }
        documents = {
            "doc-1": {
                "_id": "doc-1",
                "source_version": "1",
                "content_hash": "hash-1",
            }
        }
        supported, unsupported = obligations_supported_by_requirement_version(
            version, [obligation], self.evidence, documents
        )
        self.assertEqual(supported, [obligation])
        self.assertEqual(unsupported, [])

        documents["doc-1"]["content_hash"] = "stale-hash"
        supported, unsupported = obligations_supported_by_requirement_version(
            version, [obligation], self.evidence, documents
        )
        self.assertEqual(supported, [])
        self.assertEqual(unsupported, [obligation])

    def test_open_clarification_does_not_hide_source_mapped_blueprint_obligation(self):
        quote = "Nếu thông tin đăng nhập không hợp lệ, hệ thống từ chối truy cập."
        obligation = {
            "key": "LOGIN_REJECT_INVALID_CREDENTIALS",
            "source_ref": "REQV-1",
            "source_quote": quote,
        }
        version = {
            "_id": "REQV-1",
            "plain_text_projection": quote,
            "open_clarifications": [{"_id": "RCL-1", "status": "OPEN"}],
        }

        mapped, by_version = map_blueprint_obligations_to_requirements(
            [{"version": version}],
            [obligation],
            {"REQV-1": {"artifact_id": "REQV-1"}},
        )

        self.assertEqual(mapped, {obligation["key"]})
        self.assertEqual(by_version["REQV-1"], ([obligation], []))

    def test_ambiguous_evidence_alias_does_not_crash_or_map_obligation(self):
        quote = "Tài khoản chỉ đăng nhập bằng mật khẩu hợp lệ."
        obligation = {
            "key": "VALID_PASSWORD_REQUIRED",
            "source_ref": "SHARED-V1",
            "source_quote": quote,
        }
        version = {
            "_id": "REQV-1",
            "source_refs": [{"requirement_document_id": "DOC-1"}],
            "plain_text_projection": quote,
        }
        evidence = {
            "SHARED-V1": [
                {"artifact_id": "DOC-1", "artifact_version_id": "SHARED-V1"},
                {"artifact_id": "DOC-2", "artifact_version_id": "SHARED-V1"},
            ]
        }

        mapped, by_version = map_blueprint_obligations_to_requirements(
            [{"version": version}], [obligation], evidence
        )

        self.assertEqual(mapped, set())
        self.assertEqual(by_version["REQV-1"], ([], []))

    def test_obligation_uses_persisted_source_span_when_quote_is_not_duplicated(self):
        source_text = "Đăng nhập thành công.\nMật khẩu sai thì từ chối đăng nhập."
        cited_text = "Mật khẩu sai thì từ chối đăng nhập."
        start = source_text.index(cited_text)
        obligation = {
            "key": "reject-wrong-password",
            "source_ref": "doc-1-v1",
            "source_quote": cited_text,
        }
        version = {
            "source_refs": [
                {
                    "requirement_document_id": "doc-1",
                    "source_version": "1",
                    "content_hash": "hash-1",
                    "source_start": start,
                    "source_end": start + len(cited_text),
                    "source_quote": None,
                    "source_text_hash": hashlib.sha256(cited_text.encode("utf-8")).hexdigest(),
                },
                {
                    "requirement_document_id": "doc-1",
                    "source_version": "1",
                    "content_hash": "hash-1",
                    "source_start": 0,
                    "source_end": len("Đăng nhập thành công."),
                    "source_quote": None,
                    "source_text_hash": hashlib.sha256(
                        "Đăng nhập thành công.".encode("utf-8")
                    ).hexdigest(),
                },
            ],
            "plain_text_projection": "Đăng nhập thành công",
            "acceptance_criteria": [],
        }
        evidence = {
            "doc-1-v1": {"artifact_id": "doc-1", "text": cited_text}
        }
        documents = {
            "doc-1": {
                "_id": "doc-1",
                "source_version": "1",
                "content_hash": "hash-1",
                "normalized_content": source_text,
            }
        }

        supported, unsupported = obligations_supported_by_requirement_version(
            version, [obligation], evidence, documents
        )

        self.assertEqual(supported, [obligation])
        self.assertEqual(unsupported, [])

    def test_obligation_rejects_mismatch_between_quote_and_persisted_span(self):
        source_text = "Đăng nhập thành công.\nMật khẩu sai thì từ chối đăng nhập."
        cited_text = "Mật khẩu sai thì từ chối đăng nhập."
        start = source_text.index(cited_text)
        obligation = {
            "key": "reject-wrong-password",
            "source_ref": "doc-1-v1",
            "source_quote": "Mật khẩu đúng thì đăng nhập thành công.",
        }
        version = {
            "source_refs": [{
                "requirement_document_id": "doc-1",
                "source_version": "1",
                "content_hash": "hash-1",
                "source_start": start,
                "source_end": start + len(cited_text),
                "source_quote": None,
            }],
            "plain_text_projection": "Đăng nhập thành công",
            "acceptance_criteria": [],
        }
        evidence = {
            "doc-1-v1": {"artifact_id": "doc-1", "text": source_text}
        }
        documents = {
            "doc-1": {
                "_id": "doc-1",
                "source_version": "1",
                "content_hash": "hash-1",
            }
        }

        supported, unsupported = obligations_supported_by_requirement_version(
            version, [obligation], evidence, documents
        )

        self.assertEqual(supported, [])
        self.assertEqual(unsupported, [])

    def test_one_requirement_citation_does_not_claim_another_quote_from_same_document(self):
        source_text = "Đăng nhập thành công.\nMật khẩu sai thì từ chối đăng nhập."
        obligation = {
            "key": "reject-wrong-password",
            "source_ref": "doc-1-v1",
            "source_quote": "Mật khẩu sai thì từ chối đăng nhập.",
        }
        version = {
            "source_refs": [{
                "requirement_document_id": "doc-1",
                "source_version": "1",
                "content_hash": "hash-1",
                "source_start": 0,
                "source_end": len("Đăng nhập thành công."),
                "source_quote": "Đăng nhập thành công.",
            }],
            "plain_text_projection": "Đăng nhập thành công",
            "acceptance_criteria": [],
        }
        evidence = {"doc-1-v1": {"artifact_id": "doc-1", "text": source_text}}
        documents = {
            "doc-1": {
                "_id": "doc-1",
                "source_version": "1",
                "content_hash": "hash-1",
            }
        }

        supported, unsupported = obligations_supported_by_requirement_version(
            version, [obligation], evidence, documents
        )

        self.assertEqual(supported, [])
        self.assertEqual(unsupported, [])

    def test_obligation_quote_must_exist_in_the_linked_document_revision(self):
        obligation = {
            "key": "password-minimum-length",
            "source_ref": "doc-1-v1",
            "source_quote": "Mật khẩu phải có ít nhất 20 ký tự",
        }
        version = {
            "source_refs": [{
                "requirement_document_id": "doc-1",
                "source_version": "1",
                "content_hash": "hash-1",
                "source_start": 0,
                "source_end": len("Mật khẩu phải có ít nhất 20 ký tự"),
                "source_quote": "Mật khẩu phải có ít nhất 20 ký tự",
            }],
            "plain_text_projection": "Mật khẩu cần đủ độ dài",
            "acceptance_criteria": [],
        }
        documents = {"doc-1": {"_id": "doc-1", "source_version": "1", "content_hash": "hash-1"}}
        supported, unsupported = obligations_supported_by_requirement_version(
            version, [obligation], self.evidence, documents
        )
        self.assertEqual(supported, [])
        self.assertEqual(unsupported, [obligation])

    def test_document_synthesis_prompt_stays_within_api_contract_without_duplicating_source_facts(self):
        facts = [
            self.fact.model_copy(update={
                "artifact_id": f"doc-{index}",
                "artifact_version_id": f"doc-{index}-v1",
                "quote": f"Yêu cầu nguồn số {index}: {self.fact.quote}",
            })
            for index in range(1, 9)
        ]
        blueprint = {
            "obligations": [
                {
                    "key": f"obligation-{index}",
                    "obligation": f"Kiểm chứng yêu cầu nguồn số {index}",
                    "source_ref": f"doc-{index}-v1",
                    "source_quote": facts[index - 1].quote,
                }
                for index in range(1, 4)
            ],
            "clarifications": [],
        }
        instruction = requirement_document_synthesis_instruction(blueprint)
        self.assertLessEqual(len(instruction), 3000)
        self.assertIn("obligation-1", instruction)
        self.assertIn("doc-1-v1", instruction)
        self.assertIn("Use only cited evidence", instruction)
        self.assertNotIn("Yêu cầu nguồn số 8", instruction)


if __name__ == "__main__":
    unittest.main()

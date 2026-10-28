import unicodedata
import unittest
from unittest.mock import AsyncMock, patch

from src.prompts.testability_benchmark import (
    clarification_baseline_instruction,
    direct_generation_baseline_instruction,
)
from src.schemas.evaluation import TestabilityBenchmarkCandidate as BenchmarkCandidateSchema
from src.schemas.evaluation import TestabilityBenchmarkCase as BenchmarkCaseSchema
from src.schemas.evaluation import TestabilityBenchmarkDatasetCreate as BenchmarkDatasetCreateSchema
from src.schemas.evaluation import TestabilityBenchmarkGoldCase as BenchmarkGoldCaseSchema
from src.schemas.evaluation import TestabilityBenchmarkReport as BenchmarkReportSchema
from src.schemas.evaluation import TestabilityBenchmarkRequest as BenchmarkRequestSchema
from src.services.testability_benchmark import TestabilityBenchmarkService


class TestBenchmarkPromptContracts(unittest.TestCase):
    def test_pipeline_instructions_keep_the_research_baselines_distinct(self):
        task = "Đánh giá khả năng kiểm thử đăng nhập."

        clarification = clarification_baseline_instruction(task)
        direct_generation = direct_generation_baseline_instruction(task)

        self.assertIn(task, clarification)
        self.assertIn(task, direct_generation)
        self.assertIn("without first decomposing it into obligations", clarification)
        self.assertIn("Generate evidence-grounded test cases directly", direct_generation)
        self.assertNotEqual(clarification, direct_generation)


class TestBenchmarkPairedUncertainty(unittest.TestCase):
    def test_case_bootstrap_interval_is_repeatable_and_scoped_to_paired_cases(self):
        values = [0.1, 0.2, 0.6, 0.7]
        first = TestabilityBenchmarkService.paired_case_bootstrap_effect(
            values, "dataset-a:compiler_vs_direct:source_quote_precision"
        )
        second = TestabilityBenchmarkService.paired_case_bootstrap_effect(
            values, "dataset-a:compiler_vs_direct:source_quote_precision"
        )

        self.assertEqual(first, second)
        self.assertEqual(first["case_count"], 4)
        self.assertEqual(first["mean_left_minus_right"], 0.4)
        self.assertLessEqual(first["interval_low"], first["mean_left_minus_right"])
        self.assertGreaterEqual(first["interval_high"], first["mean_left_minus_right"])
        self.assertIn("không đo biến động giữa các lần gọi mô hình", first["scope"])

    def test_case_bootstrap_does_not_claim_interval_for_one_case(self):
        result = TestabilityBenchmarkService.paired_case_bootstrap_effect(
            [0.25], "dataset-a:single-case"
        )

        self.assertEqual(result["case_count"], 1)
        self.assertEqual(result["mean_left_minus_right"], 0.25)
        self.assertIsNone(result["interval_low"])
        self.assertIsNone(result["interval_high"])


class TestBenchmarkCandidateLineage(unittest.TestCase):
    def test_source_quote_grounding_does_not_accept_the_wrong_source_version(self):
        quote = "SRS: Mã xác minh có hiệu lực trong 5 phút."
        case = BenchmarkCaseSchema(
            case_id="source-quote-wrong-version",
            sources=[
                {"source_id": "srs", "artifact_version_id": "srs-v1", "text": quote},
                {"source_id": "api", "artifact_version_id": "api-v1", "text": quote},
            ],
            expected_source_quotes=[quote],
            expected_source_quote_sources={quote: ["srs-v1"]},
            expected_clarification_categories=["CONTRADICTION"],
        )
        candidate = BenchmarkCandidateSchema(
            source_quotes=[quote],
            source_quote_citations=[{"quote": quote, "source_ref": "api-v1"}],
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, candidate)

        self.assertEqual(scores["source_quote_validity"], 1.0)
        self.assertEqual(scores["source_quote"]["source_reference"]["precision"], 0.0)
        self.assertEqual(scores["source_quote"]["source_reference"]["recall"], 0.0)

    def test_all_pipeline_adapters_preserve_source_quote_version_citations(self):
        quote = "Mật khẩu tối thiểu 12 ký tự."
        compiler = TestabilityBenchmarkService._candidate_from_blueprint({
            "obligations": [{
                "key": "password-minimum",
                "source_ref": "source-v1",
                "source_quote": quote,
            }],
            "clarifications": [{
                "code": "missing-boundary",
                "category": "MISSING_BOUNDARY",
                "evidence_refs": ["source-v1"],
                "source_quote": quote,
            }],
        })
        clarification = TestabilityBenchmarkService._candidate_from_clarification({
            "clarifications": [{
                "code": "missing-boundary",
                "category": "MISSING_BOUNDARY",
                "evidence_refs": ["source-v1"],
                "source_quote": quote,
            }],
        })
        direct = TestabilityBenchmarkService._candidate_from_direct_generation({
            "suggestions": [{
                "coverage_obligations": ["password-minimum"],
                "evidence_quotes": [{"evidence_ref": "source-v1", "quote": quote}],
            }],
        })

        for candidate in (compiler, clarification, direct):
            self.assertIn(
                (quote, "source-v1"),
                {(citation.quote, citation.source_ref) for citation in candidate.source_quote_citations},
            )

    def test_obligation_citation_without_duplicate_key_fields_is_scored(self):
        quote = "Tài khoản bị khóa sau năm lần đăng nhập sai."
        candidate = BenchmarkCandidateSchema(
            obligation_citations={
                "account_lockout": [{"quote": quote, "source_ref": "policy-v3"}]
            }
        )
        case = BenchmarkCaseSchema(
            case_id="citation-only-obligation",
            sources=[{
                "source_id": "policy",
                "artifact_version_id": "policy-v3",
                "text": quote,
            }],
            expected_obligation_sources={"account_lockout": quote},
            expected_obligation_source_refs={"account_lockout": "policy-v3"},
            compiler=candidate,
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, candidate)

        self.assertEqual(scores["obligation"]["precision"], 1.0)
        self.assertEqual(scores["obligation"]["recall"], 1.0)

    def test_blueprint_candidate_preserves_obligation_source_version(self):
        candidate = TestabilityBenchmarkService._candidate_from_blueprint(
            {
                "obligations": [
                    {
                        "key": "account_lockout",
                        "source_ref": "policy-v3",
                        "source_quote": "Tài khoản bị khóa sau năm lần đăng nhập sai.",
                    }
                ],
                "clarifications": [],
            }
        )

        self.assertEqual(
            [citation.model_dump() for citation in candidate.obligation_citations["account_lockout"]],
            [{
                "quote": "Tài khoản bị khóa sau năm lần đăng nhập sai.",
                "source_ref": "policy-v3",
            }],
        )

    def test_direct_generation_candidate_preserves_evidence_source_version(self):
        candidate = TestabilityBenchmarkService._candidate_from_direct_generation(
            {
                "suggestions": [
                    {
                        "coverage_obligations": ["account_lockout"],
                        "evidence_quotes": [
                            {
                                "evidence_ref": "policy-v3",
                                "quote": "Tài khoản bị khóa sau năm lần đăng nhập sai.",
                            }
                        ],
                    }
                ]
            }
        )

        self.assertEqual(
            [citation.model_dump() for citation in candidate.obligation_citations["account_lockout"]],
            [{
                "quote": "Tài khoản bị khóa sau năm lần đăng nhập sai.",
                "source_ref": "policy-v3",
            }],
        )

    def test_direct_generation_merges_evidence_for_an_obligation_across_test_cases(self):
        required_quote = "Tài khoản bị khóa sau năm lần đăng nhập sai."
        additional_quote = "Lịch sử đăng nhập được ghi nhận."
        candidate = TestabilityBenchmarkService._candidate_from_direct_generation(
            {
                "suggestions": [
                    {
                        "coverage_obligations": ["account_lockout"],
                        "evidence_quotes": [{
                            "evidence_ref": "policy-v3",
                            "quote": required_quote,
                        }],
                        "obligation_evidence": [{
                            "obligation_key": "account_lockout",
                            "evidence_quotes": [{
                                "evidence_ref": "policy-v3",
                                "quote": required_quote,
                            }],
                        }],
                    },
                    {
                        "coverage_obligations": ["account_lockout"],
                        "evidence_quotes": [{
                            "evidence_ref": "audit-v1",
                            "quote": additional_quote,
                        }],
                        "obligation_evidence": [{
                            "obligation_key": "account_lockout",
                            "evidence_quotes": [{
                                "evidence_ref": "audit-v1",
                                "quote": additional_quote,
                            }],
                        }],
                    },
                ]
            }
        )

        self.assertEqual(
            candidate.obligation_evidence["account_lockout"],
            [required_quote, additional_quote],
        )
        self.assertEqual(
            [citation.model_dump() for citation in candidate.obligation_citations["account_lockout"]],
            [
                {"quote": required_quote, "source_ref": "policy-v3"},
                {"quote": additional_quote, "source_ref": "audit-v1"},
            ],
        )
        case = BenchmarkCaseSchema(
            case_id="reused-obligation-across-test-cases",
            source_text=f"{required_quote} {additional_quote}",
            expected_obligation_sources={"account_lockout": required_quote},
            compiler=candidate,
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, candidate)

        self.assertEqual(scores["obligation"]["precision"], 1.0)
        self.assertEqual(scores["obligation"]["recall"], 1.0)

    def test_blank_candidate_labels_do_not_count_as_questions_or_obligations(self):
        quote = "Người dùng phải xác thực trước khi xem dữ liệu."
        case = BenchmarkCaseSchema(
            case_id="blank-candidate-labels",
            source_text=quote,
            expected_source_quotes=[quote],
            expected_clarification_categories=["missing_actor"],
            expected_obligation_sources={"authentication_required": quote},
            compiler=BenchmarkCandidateSchema(
                clarification_codes=["", "   "],
                clarification_categories=["  "],
                obligation_keys=["", "   "],
                obligation_evidence={"": [quote]},
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, case.compiler)

        self.assertEqual(scores["clarification_count"], 0)
        self.assertEqual(scores["obligation"]["precision"], 0.0)
        self.assertEqual(scores["obligation"]["recall"], 0.0)
        self.assertEqual(scores["obligation"]["unexpected"], [])


class TestSyntheticBenchmarkDataset(unittest.TestCase):
    def test_synthetic_dataset_has_fixed_balanced_scenario_families(self):
        cases = TestabilityBenchmarkService.synthetic_cases()

        self.assertEqual(len(cases), 30)
        self.assertEqual(
            {
                family: sum(case.scenario_family == family for case in cases)
                for family in (
                    "COMPLETE",
                    "MISSING_OR_AMBIGUOUS",
                    "DUPLICATE_OR_CONFLICT",
                )
            },
            {
                "COMPLETE": 10,
                "MISSING_OR_AMBIGUOUS": 10,
                "DUPLICATE_OR_CONFLICT": 10,
            },
        )
        self.assertEqual(len({case.case_id for case in cases}), 30)

    def test_synthetic_oracle_is_grounded_and_exposes_duplicate_and_conflict_rules(self):
        cases = TestabilityBenchmarkService.synthetic_cases()
        complete = [case for case in cases if case.case_id.startswith("SYN-COMPLETE-")]
        missing = [case for case in cases if case.case_id.startswith("SYN-MISSING-")]
        duplicates = [case for case in cases if case.case_id.startswith("SYN-DUPLICATE-")]
        conflicts = [case for case in cases if case.case_id.startswith("SYN-CONFLICT-")]

        self.assertTrue(all(case.expected_obligation_sources for case in complete))
        self.assertTrue(all(case.expected_clarification_categories for case in missing))
        self.assertTrue(all(len(case.sources) == 2 for case in duplicates + conflicts))
        self.assertTrue(all(not case.expected_clarification_categories for case in duplicates))
        self.assertTrue(all(
            case.expected_clarification_categories == ["CONTRADICTION"]
            for case in conflicts
        ))
        for case in cases:
            source_texts = [source.text for source in case.sources]
            self.assertTrue(all(
                any(quote in source for source in source_texts)
                for quote in case.expected_source_quotes
            ))

    def test_synthetic_design_discloses_scope_and_non_superiority_limit(self):
        design = TestabilityBenchmarkService.synthetic_benchmark_design()

        self.assertEqual(design["case_count"], 30)
        self.assertEqual(design["requested_repetitions"], 3)
        self.assertEqual(len(design["pipelines"]), 3)
        self.assertTrue(any("not establish" in item for item in design["limitations"]))

    def test_scoring_version_changes_when_source_version_citation_metrics_are_added(self):
        scoring_method = TestabilityBenchmarkService._scoring_method()

        self.assertEqual(scoring_method["version"], "testability-benchmark-v3")
        self.assertIn("source_quote_source_precision_recall", scoring_method)

class TestabilityBenchmarkExecutionStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_maximum_matching_uses_stable_tie_breaking(self):
        matching = TestabilityBenchmarkService._maximum_obligation_matching(
            [[0, 1], [0, 1]], 2
        )

        self.assertEqual(matching, {0: 0, 1: 1})

    async def test_maximum_matching_handles_a_1000_edge_augmenting_path(self):
        size = 1000
        adjacency = [[index, index + 1] for index in range(size - 1)]
        adjacency.append([0])

        matching = TestabilityBenchmarkService._maximum_obligation_matching(
            adjacency, size
        )

        self.assertEqual(len(matching), size)
        self.assertEqual(len(set(matching.values())), size)

    async def test_priority_ndcg_is_not_scored_without_an_explicit_gold_order(self):
        quote = "Mật khẩu phải đáp ứng chính sách bảo mật."
        case = BenchmarkCaseSchema(
            case_id="clarification-order-without-gold-priority",
            source_text=quote,
            expected_source_quotes=[quote],
            expected_clarification_categories=["security_policy", "user_eligibility"],
            compiler=BenchmarkCandidateSchema(
                clarification_categories=["user_eligibility", "security_policy"]
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, case.compiler)

        self.assertIsNone(scores["clarification_priority"]["ndcg"])
        self.assertIsNone(scores["clarification_priority"]["first_relevant_rank"])

    async def test_priority_ndcg_uses_only_the_explicit_gold_order(self):
        quote = "Mật khẩu phải đáp ứng chính sách bảo mật."
        case = BenchmarkCaseSchema(
            case_id="clarification-order-with-gold-priority",
            source_text=quote,
            expected_source_quotes=[quote],
            expected_clarification_categories=["security_policy", "user_eligibility"],
            expected_clarification_priorities=["security_policy", "user_eligibility"],
            compiler=BenchmarkCandidateSchema(
                clarification_categories=["user_eligibility", "security_policy"]
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, case.compiler)

        self.assertLess(scores["clarification_priority"]["ndcg"], 1.0)
        self.assertEqual(scores["clarification_priority"]["first_relevant_rank"], 1)

    async def test_clarification_count_counts_questions_not_unique_categories(self):
        quote = "Mật khẩu phải đáp ứng chính sách bảo mật."
        case = BenchmarkCaseSchema(
            case_id="repeated-clarification-category",
            source_text=quote,
            expected_source_quotes=[quote],
            expected_clarification_categories=["security_policy"],
            expected_obligation_keys=["password_rule"],
            expected_clarification_unlocks={"security_policy": ["password_rule"]},
            clarification_without_obligation_planning=BenchmarkCandidateSchema(
                source_quotes=[quote],
                clarification_codes=["security_policy", "security_policy"],
                clarification_categories=["security_policy", "security_policy"],
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(
            case,
            case.clarification_without_obligation_planning,
            score_obligations=False,
        )

        self.assertEqual(scores["clarification"]["precision"], 1.0)
        self.assertEqual(scores["clarification_count"], 2)
        self.assertEqual(scores["gold_obligations_unlocked_per_clarification"], 0.5)

    def test_scoring_request_rejects_duplicate_case_ids(self):
        cases = [
            BenchmarkCaseSchema(
                case_id="duplicate",
                source_text="Có quy tắc kiểm thử.",
                expected_source_quotes=["Có quy tắc kiểm thử."],
                expected_obligation_keys=["rule"],
            )
            for _ in range(2)
        ]

        with self.assertRaisesRegex(ValueError, "benchmark_case_ids_must_be_unique"):
            BenchmarkRequestSchema(cases=cases)

    def test_dataset_creation_rejects_duplicate_case_ids(self):
        cases = [
            BenchmarkGoldCaseSchema(
                case_id="duplicate",
                source_text="Có quy tắc kiểm thử.",
                expected_source_quotes=["Có quy tắc kiểm thử."],
                expected_obligation_keys=["rule"],
            )
            for _ in range(2)
        ]

        with self.assertRaisesRegex(ValueError, "benchmark_case_ids_must_be_unique"):
            BenchmarkDatasetCreateSchema(
                dataset_id="dataset-1",
                title="Dataset",
                cases=cases,
            )

    def test_scoring_legacy_dataset_rejects_duplicate_case_ids_before_pipeline(self):
        cases = [
            BenchmarkGoldCaseSchema(
                case_id="duplicate",
                source_text="Có quy tắc kiểm thử.",
                expected_source_quotes=["Có quy tắc kiểm thử."],
                expected_obligation_keys=["rule"],
            )
            for _ in range(2)
        ]

        with self.assertRaisesRegex(ValueError, "benchmark_case_ids_must_be_unique"):
            TestabilityBenchmarkService.validate_cases_for_scoring(cases)

    def test_gold_case_without_any_answer_key_is_rejected(self):
        case = BenchmarkGoldCaseSchema(
            case_id="unscored-case",
            source_text="Mật khẩu tối thiểu 12 ký tự.",
        )
        with self.assertRaisesRegex(ValueError, "benchmark_case_requires_answer_key"):
            case.validate_for_scoring()

    def test_gold_answer_key_rejects_duplicate_priority_labels(self):
        with self.assertRaisesRegex(
            ValueError, "benchmark_expected_clarification_priorities_must_be_unique"
        ):
            BenchmarkGoldCaseSchema(
                case_id="duplicate-priority-label",
                source_text="Mật khẩu phải đáp ứng chính sách bảo mật.",
                expected_source_quotes=["Mật khẩu phải đáp ứng chính sách bảo mật."],
                expected_clarification_categories=["security_policy"],
                expected_clarification_priorities=[
                    "security_policy",
                    "security_policy",
                ],
            )

    def test_gold_answer_key_rejects_duplicate_source_quotes(self):
        quote = "Mật khẩu phải đáp ứng chính sách bảo mật."
        with self.assertRaisesRegex(
            ValueError, "benchmark_expected_source_quotes_must_be_unique"
        ):
            BenchmarkGoldCaseSchema(
                case_id="duplicate-source-quote",
                source_text=quote,
                expected_source_quotes=[quote, quote],
                expected_clarification_categories=["security_policy"],
            )

    def test_gold_source_quote_references_must_cover_all_expected_quotes(self):
        first_quote = "SRS: Mã xác minh có hiệu lực trong 5 phút."
        second_quote = "API: Mã xác minh có hiệu lực trong 10 phút."
        with self.assertRaisesRegex(
            ValueError,
            "benchmark_quote_source_answer_key_must_cover_all_expected_quotes",
        ):
            BenchmarkGoldCaseSchema(
                case_id="partial-quote-source-map",
                sources=[
                    {"source_id": "srs", "artifact_version_id": "srs-v1", "text": first_quote},
                    {"source_id": "api", "artifact_version_id": "api-v1", "text": second_quote},
                ],
                expected_source_quotes=[first_quote, second_quote],
                expected_source_quote_sources={first_quote: ["srs-v1"]},
                expected_clarification_categories=["CONTRADICTION"],
            )

    def test_gold_answer_key_rejects_priority_labels_scoring_would_normalize_as_duplicates(self):
        quote = "Mật khẩu phải đáp ứng chính sách bảo mật."
        with self.assertRaisesRegex(
            ValueError, "benchmark_expected_clarification_priorities_must_be_unique"
        ):
            BenchmarkGoldCaseSchema(
                case_id="normalized-duplicate-priority-label",
                source_text=quote,
                expected_source_quotes=[quote],
                expected_clarification_categories=["security_policy"],
                expected_clarification_priorities=[
                    "security_policy",
                    " security_policy ",
                ],
            )

    def test_gold_answer_key_rejects_source_quotes_scoring_would_normalize_as_duplicates(self):
        quote = "Mật khẩu phải đáp ứng chính sách bảo mật."
        with self.assertRaisesRegex(
            ValueError, "benchmark_expected_source_quotes_must_be_unique"
        ):
            BenchmarkGoldCaseSchema(
                case_id="normalized-duplicate-source-quote",
                source_text=quote,
                expected_source_quotes=[quote, quote.rstrip(".")],
                expected_clarification_categories=["security_policy"],
            )

    def test_quote_only_gold_case_is_rejected_without_a_scored_behavior(self):
        case = BenchmarkGoldCaseSchema(
            case_id="quote-only-case",
            source_text="Mật khẩu tối thiểu 12 ký tự.",
            expected_source_quotes=["Mật khẩu tối thiểu 12 ký tự."],
        )
        with self.assertRaisesRegex(ValueError, "benchmark_case_requires_answer_key"):
            case.validate_for_scoring()

    def test_obligation_source_can_supply_the_gold_source_quote(self):
        case = BenchmarkGoldCaseSchema(
            case_id="password-minimum",
            source_text="Mật khẩu tối thiểu 12 ký tự.",
            expected_obligation_sources={
                "password_minimum": "Mật khẩu tối thiểu 12 ký tự."
            },
        )

        self.assertEqual(
            case.expected_source_quotes,
            ["Mật khẩu tối thiểu 12 ký tự."],
        )

    def test_gold_quote_cannot_be_assembled_across_independent_sources(self):
        with self.assertRaisesRegex(
            ValueError, "benchmark_expected_quote_must_appear_in_source"
        ):
            BenchmarkGoldCaseSchema(
                case_id="separate-source-boundary",
                sources=[
                    {
                        "source_id": "first",
                        "artifact_version_id": "first-v1",
                        "text": "Mật khẩu phải",
                    },
                    {
                        "source_id": "second",
                        "artifact_version_id": "second-v1",
                        "text": "ít nhất 12 ký tự.",
                    },
                ],
                expected_source_quotes=["Mật khẩu phải ít nhất 12 ký tự."],
            )

    def test_gold_quote_inside_another_word_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError, "benchmark_expected_quote_must_appear_in_source"
        ):
            BenchmarkGoldCaseSchema(
                case_id="subword-source-quote",
                source_text="invalid",
                expected_source_quotes=["valid"],
                expected_clarification_categories=["missing_rule"],
            )

    def test_gold_answer_key_cannot_use_source_text_ignored_by_explicit_sources(self):
        with self.assertRaisesRegex(
            ValueError, "benchmark_expected_quote_must_appear_in_source"
        ):
            BenchmarkGoldCaseSchema(
                case_id="unused-source-text",
                source_text="Mật khẩu phải có ít nhất 12 ký tự.",
                sources=[
                    {
                        "source_id": "actual-source",
                        "artifact_version_id": "actual-source-v1",
                        "text": "Yêu cầu chưa nêu quy tắc mật khẩu.",
                    }
                ],
                expected_source_quotes=["Mật khẩu phải có ít nhất 12 ký tự."],
                expected_obligation_keys=["password_minimum"],
            )

    def test_gold_case_rejects_ambiguous_source_identifiers(self):
        with self.assertRaisesRegex(ValueError, "benchmark_source_ids_must_be_unique"):
            BenchmarkGoldCaseSchema(
                case_id="duplicate-source-id",
                sources=[
                    {
                        "source_id": "same-source",
                        "artifact_version_id": "source-v1",
                        "text": "Quy tắc một.",
                    },
                    {
                        "source_id": "same-source",
                        "artifact_version_id": "source-v2",
                        "text": "Quy tắc hai.",
                    },
                ],
                expected_source_quotes=["Quy tắc một."],
                expected_obligation_keys=["rule-one"],
            )

        with self.assertRaisesRegex(
            ValueError, "benchmark_source_version_ids_must_be_unique"
        ):
            BenchmarkGoldCaseSchema(
                case_id="duplicate-source-version",
                sources=[
                    {
                        "source_id": "first-source",
                        "artifact_version_id": "same-version",
                        "text": "Quy tắc một.",
                    },
                    {
                        "source_id": "second-source",
                        "artifact_version_id": "same-version",
                        "text": "Quy tắc hai.",
                    },
                ],
                expected_source_quotes=["Quy tắc một."],
                expected_obligation_keys=["rule-one"],
            )

    def test_gold_answer_key_rejects_empty_quotes(self):
        with self.assertRaisesRegex(
            ValueError, "benchmark_expected_quote_must_appear_in_source"
        ):
            BenchmarkGoldCaseSchema(
                case_id="empty-answer-key-quote",
                source_text="Có yêu cầu nguồn.",
                expected_source_quotes=["   "],
                expected_obligation_keys=["requirement"],
            )

        with self.assertRaisesRegex(
            ValueError, "benchmark_obligation_quote_must_appear_in_source"
        ):
            BenchmarkGoldCaseSchema(
                case_id="empty-obligation-quote",
                source_text="Có yêu cầu nguồn.",
                expected_source_quotes=["Có yêu cầu nguồn."],
                expected_obligation_sources={"requirement": ""},
            )

    def test_repeated_run_summary_reports_mean_variance_and_partial_pipeline_runs(self):
        def make_report(run_id, compiler_recall, direct_recall, direct_failed=0, status="COMPLETE"):
            is_second_run = run_id == "run-2"
            cases = []
            for case_index, case_id in enumerate(("case-a", "case-b")):
                direct_accepted = not (direct_failed and case_id == "case-b")
                compiler_count = (
                    2 if case_index == 0 else 1
                ) if not is_second_run else 1
                baseline_count = 2
                cases.append(
                    {
                        "case_id": case_id,
                        "compiler": {
                            "source_quote": {"recall": compiler_recall},
                            "clarification_count": compiler_count,
                        },
                        "clarification_without_obligation_planning": {
                            "source_quote": {"recall": 1.0},
                            "clarification_count": baseline_count,
                        },
                        "direct_generation": {
                            "source_quote": {
                                "recall": direct_recall if direct_accepted else None
                            }
                        },
                        "pipeline_outcomes": {
                            "compiler": "ACCEPTED",
                            "clarification_without_obligation_planning": "ACCEPTED",
                            "direct_generation": "ACCEPTED" if direct_accepted else "FAILED",
                        },
                    }
                )
            return BenchmarkReportSchema(
                total_cases=2,
                clarification_without_obligation_planning={"source_quote_recall": 1.0},
                compiler={"source_quote_recall": compiler_recall},
                direct_generation={"source_quote_recall": direct_recall},
                cases=cases,
                run_id=run_id,
                dataset_id="dataset-1",
                execution_status=status,
                clarification_savings_vs_baseline=None,
                clarification_savings_paired_cases=2,
                pipeline_case_counts={
                    "compiler": {"accepted": 2, "rejected": 0, "failed": 0},
                    "clarification_without_obligation_planning": {
                        "accepted": 2,
                        "rejected": 0,
                        "failed": 0,
                    },
                    "direct_generation": {
                        "accepted": 2 if direct_failed == 0 else 1,
                        "rejected": 0,
                        "failed": direct_failed,
                    },
                },
                paired_pipeline_comparisons={
                    "compiler_vs_clarification_without_obligation_planning": {
                        "left_pipeline": "compiler",
                        "right_pipeline": "clarification_without_obligation_planning",
                        "paired_case_count": 2,
                        "case_ids": ["case-a", "case-b"],
                    }
                },
            )

        summary = TestabilityBenchmarkService.summarize_repeated_reports(
            "dataset-1",
            2,
            [
                make_report("run-1", 0.4, 0.9),
                make_report("run-2", 0.6, 0.0, direct_failed=1, status="PARTIAL"),
            ],
        )

        self.assertEqual(summary.execution_status, "PARTIAL")
        self.assertEqual(summary.completed_repetitions, 1)
        self.assertEqual(summary.partial_repetitions, 1)
        compiler = summary.pipeline_statistics["compiler"]
        self.assertEqual(compiler.runs_with_scores, 2)
        self.assertEqual(compiler.stable_case_ids, ["case-a", "case-b"])
        self.assertEqual(compiler.metrics["source_quote_recall"].mean, 0.5)
        self.assertEqual(compiler.metrics["source_quote_recall"].population_stddev, 0.1)
        direct = summary.pipeline_statistics["direct_generation"]
        self.assertEqual(direct.runs_with_scores, 2)
        self.assertEqual(direct.stable_case_ids, ["case-a"])
        self.assertEqual(direct.runs_with_failures, 1)
        self.assertEqual(direct.metrics["source_quote_recall"].mean, 0.45)
        self.assertEqual(direct.metrics["source_quote_recall"].population_stddev, 0.45)
        self.assertEqual(summary.clarification_savings_vs_baseline.observed_runs, 2)
        self.assertEqual(summary.clarification_savings_vs_baseline.paired_case_ids, ["case-a", "case-b"])
        self.assertEqual(summary.clarification_savings_vs_baseline.mean, 0.75)
        self.assertEqual(summary.clarification_savings_vs_baseline.population_stddev, 0.25)
        effect = summary.paired_pipeline_statistics[
            "compiler_vs_clarification_without_obligation_planning"
        ]["paired_effects"]["source_quote_recall"]
        self.assertEqual(effect["case_count"], 2)
        self.assertEqual(effect["mean_left_minus_right"], -0.5)
        self.assertLessEqual(effect["interval_low"], -0.5)
        self.assertGreaterEqual(effect["interval_high"], -0.5)

    def test_repeated_metrics_use_same_cases_for_each_run_and_denominator(self):
        reports = []
        for run_id, metric_values in (
            (
                "run-1",
                {
                    "case-a": {"source_quote_validity": 0.2},
                    "case-b": {"source_quote_validity": 1.0},
                    "case-c": {"clarification_count": 1},
                },
            ),
            (
                "run-2",
                {
                    "case-a": {"source_quote_validity": 0.8},
                    "case-b": {"clarification_count": 2},
                    "case-c": {"source_quote_validity": 0.6},
                },
            ),
        ):
            reports.append(
                BenchmarkReportSchema(
                    total_cases=3,
                    clarification_without_obligation_planning={},
                    compiler={},
                    direct_generation={},
                    cases=[
                        {
                            "case_id": case_id,
                            "compiler": metrics,
                            "pipeline_outcomes": {"compiler": "ACCEPTED"},
                        }
                        for case_id, metrics in metric_values.items()
                    ],
                    run_id=run_id,
                    dataset_id="dataset-1",
                )
            )

        summary = TestabilityBenchmarkService.summarize_repeated_reports(
            "dataset-1", 2, reports
        )

        compiler = summary.pipeline_statistics["compiler"]
        self.assertEqual(compiler.runs_with_scores, 2)
        self.assertEqual(compiler.metrics["source_quote_validity"].observed_runs, 2)
        self.assertEqual(compiler.metrics["source_quote_validity"].mean, 0.5)
        self.assertEqual(compiler.metrics["source_quote_validity"].paired_case_count, 1)
        self.assertEqual(compiler.metrics["source_quote_validity"].paired_case_ids, ["case-a"])
        self.assertEqual(compiler.metrics["average_clarification_count"].observed_runs, 0)
        self.assertIsNone(compiler.metrics["average_clarification_count"].mean)
        self.assertEqual(compiler.metrics["average_clarification_count"].paired_case_count, 0)

    async def test_repeated_run_count_is_bounded(self):
        with self.assertRaisesRegex(ValueError, "BENCHMARK_REPETITIONS_OUT_OF_RANGE"):
            await TestabilityBenchmarkService().run_repeated_dataset("dataset-1", [], 6)

    async def test_repeated_runner_saves_each_real_report_and_indexes_the_repetition(self):
        service = TestabilityBenchmarkService()
        reports = [
            BenchmarkReportSchema(
                total_cases=1,
                clarification_without_obligation_planning={"source_quote_recall": 1.0},
                compiler={"source_quote_recall": 0.5},
                direct_generation={"source_quote_recall": 0.75},
                cases=[
                    {
                        "case_id": "case-1",
                        "compiler": {"source_quote": {"recall": 0.5}},
                        "clarification_without_obligation_planning": {
                            "source_quote": {"recall": 1.0}
                        },
                        "direct_generation": {"source_quote": {"recall": 0.75}},
                        "pipeline_outcomes": {
                            "compiler": "ACCEPTED",
                            "clarification_without_obligation_planning": "ACCEPTED",
                            "direct_generation": "ACCEPTED",
                        },
                    }
                ],
                run_id=f"run-{index}",
                dataset_id="dataset-1",
                pipeline_case_counts={
                    name: {"accepted": 1, "rejected": 0, "failed": 0}
                    for name in (
                        "compiler",
                        "clarification_without_obligation_planning",
                        "direct_generation",
                    )
                },
            )
            for index in (1, 2)
        ]
        save_report = AsyncMock()
        run_dataset = AsyncMock(side_effect=reports)
        with patch.object(service, "run_dataset", new=run_dataset):
            summary = await service.run_repeated_dataset(
                "dataset-1", [], repetitions=2, on_report=save_report
            )

        self.assertEqual(summary.run_ids, ["run-1", "run-2"])
        self.assertEqual(summary.completed_repetitions, 2)
        self.assertEqual(summary.execution_status, "COMPLETE")
        self.assertEqual(save_report.await_count, 2)
        self.assertEqual(
            [call.kwargs["pipeline_order"] for call in run_dataset.await_args_list],
            [
                (
                    "compiler",
                    "clarification_without_obligation_planning",
                    "direct_generation",
                ),
                (
                    "clarification_without_obligation_planning",
                    "direct_generation",
                    "compiler",
                ),
            ],
        )
        self.assertEqual(reports[0].pipeline_metadata["repetition_index"], 1)
        self.assertEqual(reports[1].pipeline_metadata["repetition_index"], 2)
        self.assertEqual(
            summary.pipeline_statistics["compiler"].metrics["source_quote_recall"].population_stddev,
            0.0,
        )

    async def test_repeated_runner_continues_after_one_crashed_repetition(self):
        service = TestabilityBenchmarkService()
        valid_report = BenchmarkReportSchema(
            total_cases=1,
            clarification_without_obligation_planning={"source_quote_recall": 1.0},
            compiler={"source_quote_recall": 0.5},
            direct_generation={"source_quote_recall": 0.75},
            cases=[],
            run_id="run-2",
            dataset_id="dataset-1",
            pipeline_case_counts={
                name: {"accepted": 1, "rejected": 0, "failed": 0}
                for name in (
                    "compiler",
                    "clarification_without_obligation_planning",
                    "direct_generation",
                )
            },
        )
        with patch.object(
            service,
            "run_dataset",
            new=AsyncMock(side_effect=[RuntimeError("provider secret must not escape"), valid_report]),
        ):
            summary = await service.run_repeated_dataset("dataset-1", [], repetitions=2)

        self.assertEqual(summary.execution_status, "PARTIAL")
        self.assertEqual(summary.failed_repetitions, 1)
        self.assertEqual(summary.partial_repetitions, 0)
        self.assertEqual(summary.run_ids, ["run-2"])
        self.assertEqual(summary.repetition_failures, [{
            "repetition_index": 1,
            "error_code": "RUNTIMEERROR",
        }])

    def test_benchmark_facts_require_a_version_and_exact_source_span(self):
        source_text = "Thanh toán phải hoàn tất trước khi xác nhận đơn hàng. invalid"
        source = {
            "artifact_id": "doc-1",
            "artifact_version_id": "doc-1-v1",
            "text": source_text,
        }
        valid_fact = {
            "artifact_id": "doc-1",
            "artifact_version_id": "doc-1-v1",
            "quote": source_text,
            "source_start": 0,
            "source_end": len(source_text),
        }
        invalid_fact = {**valid_fact, "source_start": 1}
        missing_revision = {**valid_fact, "artifact_version_id": None}
        subword_start = source_text.index("valid")
        subword_fact = {
            **valid_fact,
            "quote": "valid",
            "source_start": subword_start,
            "source_end": subword_start + len("valid"),
        }

        result = TestabilityBenchmarkService._verified_fact_evidence(
            [invalid_fact, missing_revision, subword_fact, valid_fact], [source]
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["artifact_version_id"], "doc-1-v1")
        self.assertEqual(result[0]["text"], source_text)

    def test_benchmark_facts_reject_negative_source_offsets(self):
        source_text = "abcdefghij"
        source = {
            "artifact_id": "doc-1",
            "artifact_version_id": "doc-1-v1",
            "text": source_text,
        }
        negative_span_fact = {
            "artifact_id": "doc-1",
            "artifact_version_id": "doc-1-v1",
            "quote": "fghi",
            "source_start": -5,
            "source_end": -1,
        }

        result = TestabilityBenchmarkService._verified_fact_evidence(
            [negative_span_fact], [source]
        )

        self.assertEqual(result, [])

    async def test_answer_key_matching_ignores_terminal_punctuation_only(self):
        quote = "Người dùng đã đăng ký có thể đăng nhập bằng email và mật khẩu."
        case = BenchmarkCaseSchema(
            case_id="login-rule",
            source_text=quote,
            expected_source_quotes=[quote],
            expected_obligation_sources={"login": quote},
            compiler=BenchmarkCandidateSchema(
                source_quotes=[quote.removesuffix(".")],
                obligation_keys=["model-generated-key"],
                obligation_evidence={"model-generated-key": [quote.removesuffix(".")]},
            ),
        )
        report = await TestabilityBenchmarkService().evaluate(
            BenchmarkRequestSchema(cases=[case])
        )
        compiler = report.cases[0]["compiler"]
        self.assertEqual(compiler["source_quote"]["precision"], 1.0)
        self.assertEqual(compiler["source_quote"]["recall"], 1.0)
        self.assertEqual(compiler["obligation"]["precision"], 1.0)
        self.assertEqual(compiler["obligation"]["recall"], 1.0)

    async def test_candidate_quote_spanning_independent_sources_is_not_grounded(self):
        case = BenchmarkCaseSchema(
            case_id="separate-source-boundary",
            sources=[
                {
                    "source_id": "first",
                    "artifact_version_id": "first-v1",
                    "text": "Mật khẩu phải",
                },
                {
                    "source_id": "second",
                    "artifact_version_id": "second-v1",
                    "text": "ít nhất 12 ký tự.",
                },
            ],
            expected_source_quotes=["Mật khẩu phải"],
            compiler=BenchmarkCandidateSchema(
                source_quotes=["Mật khẩu phải ít nhất 12 ký tự."]
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(
            case, case.compiler, score_obligations=False
        )

        self.assertEqual(scores["source_quote_validity"], 0.0)

    async def test_candidate_quote_inside_another_word_is_not_grounded(self):
        case = BenchmarkCaseSchema(
            case_id="quote-word-boundary",
            source_text="The system rejects invalid credentials.",
            expected_source_quotes=["The system rejects invalid credentials"],
            compiler=BenchmarkCandidateSchema(source_quotes=["valid"]),
        )

        scores = TestabilityBenchmarkService._candidate_scores(
            case, case.compiler, score_obligations=False
        )

        self.assertEqual(scores["source_quote_validity"], 0.0)

    def test_source_quote_metrics_do_not_match_inside_another_word(self):
        scores = TestabilityBenchmarkService._source_quote_scores(
            ["valid"], ["invalid"]
        )

        self.assertEqual(scores["precision"], 0.0)
        self.assertEqual(scores["recall"], 0.0)

    async def test_candidate_cannot_ground_against_source_text_ignored_by_runtime(self):
        visible_quote = "Yêu cầu chưa nêu quy tắc mật khẩu."
        hidden_quote = "Mật khẩu phải có ít nhất 12 ký tự."
        case = BenchmarkCaseSchema(
            case_id="runtime-source-boundary",
            source_text=hidden_quote,
            sources=[
                {
                    "source_id": "actual-source",
                    "artifact_version_id": "actual-source-v1",
                    "text": visible_quote,
                }
            ],
            expected_source_quotes=[visible_quote],
            expected_obligation_sources={"password_rule": visible_quote},
            compiler=BenchmarkCandidateSchema(
                source_quotes=[hidden_quote],
                obligation_keys=["password_rule"],
                obligation_evidence={"password_rule": [hidden_quote]},
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, case.compiler)

        self.assertEqual(scores["source_quote_validity"], 0.0)
        self.assertEqual(scores["obligation"]["precision"], 0.0)
        self.assertEqual(scores["obligation"]["recall"], 0.0)

    async def test_obligation_score_requires_the_answer_key_source_version(self):
        quote = "Tài khoản bị khóa sau năm lần đăng nhập sai."
        sources = [
            {
                "source_id": "policy-v1",
                "artifact_version_id": "policy-v1",
                "text": quote,
            },
            {
                "source_id": "api-v1",
                "artifact_version_id": "api-v1",
                "text": quote,
            },
        ]
        case = BenchmarkCaseSchema(
            case_id="wrong-source-lineage",
            sources=sources,
            expected_source_quotes=[quote],
            expected_obligation_sources={"account_lockout": quote},
            expected_obligation_source_refs={"account_lockout": "policy-v1"},
            compiler=BenchmarkCandidateSchema(
                source_quotes=[quote],
                obligation_keys=["account_lockout"],
                obligation_evidence={"account_lockout": [quote]},
                obligation_citations={
                    "account_lockout": [{"quote": quote, "source_ref": "api-v1"}]
                },
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, case.compiler)

        self.assertEqual(scores["source_quote_validity"], 1.0)
        self.assertEqual(scores["obligation"]["precision"], 0.0)
        self.assertEqual(scores["obligation"]["recall"], 0.0)

    def test_obligation_citation_quote_must_exist_in_the_cited_source(self):
        quote = "Tài khoản bị khóa sau năm lần đăng nhập sai."
        case = BenchmarkCaseSchema(
            case_id="citation-quote-in-wrong-source",
            sources=[
                {
                    "source_id": "policy",
                    "artifact_version_id": "policy-v1",
                    "text": "Chính sách chưa xác định giới hạn đăng nhập sai.",
                },
                {
                    "source_id": "api",
                    "artifact_version_id": "api-v1",
                    "text": quote,
                },
            ],
            expected_source_quotes=[quote],
            expected_obligation_sources={"account_lockout": quote},
            expected_obligation_source_refs={"account_lockout": "api-v1"},
            compiler=BenchmarkCandidateSchema(
                obligation_citations={
                    "account_lockout": [{"quote": quote, "source_ref": "policy-v1"}]
                }
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, case.compiler)

        self.assertEqual(scores["obligation"]["precision"], 0.0)
        self.assertEqual(scores["obligation"]["recall"], 0.0)

    def test_gold_source_reference_must_name_a_document_version(self):
        with self.assertRaisesRegex(
            ValueError, "benchmark_expected_source_reference_not_found"
        ):
            BenchmarkGoldCaseSchema(
                case_id="unknown-source-reference",
                sources=[
                    {
                        "source_id": "policy",
                        "artifact_version_id": "policy-v1",
                        "text": "Tài khoản bị khóa sau năm lần đăng nhập sai.",
                    }
                ],
                expected_source_quotes=[
                    "Tài khoản bị khóa sau năm lần đăng nhập sai."
                ],
                expected_obligation_sources={
                    "account_lockout": "Tài khoản bị khóa sau năm lần đăng nhập sai."
                },
                expected_obligation_source_refs={"account_lockout": "missing-v1"},
            )

    def test_gold_obligation_quote_must_belong_to_its_answer_key_source_version(self):
        with self.assertRaisesRegex(
            ValueError, "benchmark_obligation_quote_not_in_cited_source"
        ):
            BenchmarkGoldCaseSchema(
                case_id="obligation-quote-wrong-version",
                sources=[
                    {
                        "source_id": "policy",
                        "artifact_version_id": "policy-v1",
                        "text": "Chính sách chưa xác định số lần đăng nhập sai.",
                    },
                    {
                        "source_id": "api",
                        "artifact_version_id": "api-v1",
                        "text": "Tài khoản bị khóa sau năm lần đăng nhập sai.",
                    },
                ],
                expected_source_quotes=[
                    "Tài khoản bị khóa sau năm lần đăng nhập sai."
                ],
                expected_obligation_sources={
                    "account_lockout": "Tài khoản bị khóa sau năm lần đăng nhập sai."
                },
                expected_obligation_source_refs={"account_lockout": "policy-v1"},
            )

    def test_gold_quote_source_mapping_normalizes_unicode_consistently(self):
        composed = "Cà phê phải được xác nhận."
        decomposed = unicodedata.normalize("NFD", composed)
        case = BenchmarkGoldCaseSchema(
            case_id="unicode-source-map",
            sources=[{
                "source_id": "srs",
                "artifact_version_id": "srs-v1",
                "text": composed,
            }],
            expected_source_quotes=[composed],
            expected_source_quote_sources={decomposed: ["srs-v1"]},
            expected_clarification_categories=["MISSING_RULE"],
        )

        self.assertEqual(case.expected_source_quote_sources, {decomposed: ["srs-v1"]})

    async def test_obligation_score_requires_its_own_evidence_to_be_grounded(self):
        quote = "Mật khẩu phải có ít nhất 12 ký tự."
        case = BenchmarkCaseSchema(
            case_id="ungrounded-obligation-evidence",
            source_text=quote,
            expected_source_quotes=[quote],
            expected_obligation_sources={"password_minimum": quote},
            compiler=BenchmarkCandidateSchema(
                source_quotes=["Bằng chứng không liên quan."],
                obligation_keys=["password_minimum"],
                obligation_evidence={"password_minimum": [quote + " Quy tắc bảo mật." ]},
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(
            case, case.compiler
        )

        self.assertEqual(scores["source_quote_validity"], 0.0)
        self.assertEqual(scores["obligation"]["precision"], 0.0)
        self.assertEqual(scores["obligation"]["recall"], 0.0)

    async def test_overlapping_obligation_evidence_uses_maximum_matching(self):
        short_quote = "Mật khẩu hợp lệ"
        long_quote = "Mật khẩu hợp lệ khi đủ độ dài"
        flexible_key, constrained_key = list({"prediction-a", "prediction-b"})
        case = BenchmarkCaseSchema(
            case_id="overlapping-obligation-evidence",
            source_text=f"{long_quote}.",
            expected_source_quotes=[short_quote, long_quote],
            expected_obligation_sources={
                "short_requirement": short_quote,
                "long_requirement": long_quote,
            },
            compiler=BenchmarkCandidateSchema(
                obligation_keys=[flexible_key, constrained_key],
                obligation_evidence={
                    flexible_key: [long_quote],
                    constrained_key: [short_quote],
                },
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, case.compiler)

        self.assertEqual(scores["obligation"]["precision"], 1.0)
        self.assertEqual(scores["obligation"]["recall"], 1.0)
        self.assertEqual(scores["obligation"]["unexpected"], [])
        self.assertEqual(scores["obligation"]["missing"], [])

    async def test_unsubstantiated_predicted_obligation_remains_in_precision_denominator(self):
        first_quote = "Mật khẩu phải có ít nhất 12 ký tự."
        second_quote = "Tài khoản bị khóa sau năm lần đăng nhập sai."
        case = BenchmarkCaseSchema(
            case_id="two-security-obligations",
            source_text=f"{first_quote} {second_quote}",
            expected_source_quotes=[first_quote, second_quote],
            expected_obligation_sources={
                "password_minimum": first_quote,
                "failed_login_lock": second_quote,
            },
            compiler=BenchmarkCandidateSchema(
                source_quotes=[first_quote],
                obligation_keys=["password_minimum", "failed_login_lock"],
                obligation_evidence={"password_minimum": [first_quote]},
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, case.compiler)

        self.assertEqual(scores["obligation"]["precision"], 0.5)
        self.assertEqual(scores["obligation"]["recall"], 0.5)
        self.assertEqual(scores["obligation"]["unexpected"], ["failed_login_lock"])
        self.assertEqual(scores["obligation"]["missing"], ["failed_login_lock"])

    async def test_correct_predictions_stay_in_obligation_precision_denominator(self):
        first_quote = "Mật khẩu phải có ít nhất 12 ký tự."
        second_quote = "Tài khoản bị khóa sau năm lần đăng nhập sai."
        case = BenchmarkCaseSchema(
            case_id="two-correct-one-invented-obligation",
            source_text=f"{first_quote} {second_quote}",
            expected_source_quotes=[first_quote, second_quote],
            expected_obligation_sources={
                "password_minimum": first_quote,
                "failed_login_lock": second_quote,
            },
            compiler=BenchmarkCandidateSchema(
                source_quotes=[first_quote, second_quote],
                obligation_keys=["password_minimum", "failed_login_lock", "invented"],
                obligation_evidence={
                    "password_minimum": [first_quote],
                    "failed_login_lock": [second_quote],
                },
            ),
        )

        scores = TestabilityBenchmarkService._candidate_scores(case, case.compiler)

        self.assertEqual(scores["obligation"]["precision"], 0.6667)
        self.assertEqual(scores["obligation"]["recall"], 1.0)
        self.assertEqual(scores["obligation"]["unexpected"], ["invented"])

    async def test_source_quote_scoring_accepts_a_grounded_passage_covering_gold_quotes(self):
        source_text = (
            "Người dùng đã đăng ký có thể đăng nhập bằng email và mật khẩu. "
            "Khi xác thực thành công, hệ thống chuyển người dùng đến trang chính. "
            "Thông tin không hợp lệ sẽ bị từ chối."
        )
        first = "Người dùng đã đăng ký có thể đăng nhập bằng email và mật khẩu"
        second = "Khi xác thực thành công, hệ thống chuyển người dùng đến trang chính"
        third = "Thông tin không hợp lệ sẽ bị từ chối"
        case = BenchmarkCaseSchema(
            case_id="login-passage-citation",
            source_text=source_text,
            expected_source_quotes=[first, second, third],
            expected_obligation_sources={
                "registered_user_can_login": first,
                "successful_login_opens_home": second,
                "invalid_credentials_are_rejected": third,
            },
            compiler=BenchmarkCandidateSchema(
                source_quotes=[f"{first}. {second}.", "một trích dẫn không liên quan"],
            ),
        )

        report = await TestabilityBenchmarkService().evaluate(
            BenchmarkRequestSchema(cases=[case])
        )

        scores = report.cases[0]["compiler"]["source_quote"]
        self.assertEqual(scores["precision"], 0.5)
        self.assertEqual(scores["recall"], 0.6667)
        self.assertEqual(scores["matched"], sorted([first, second]))
        self.assertEqual(scores["missing"], [third])
        self.assertEqual(scores["unexpected"], ["một trích dẫn không liên quan"])

    async def test_grounding_rejection_is_scored_in_a_complete_run(self):
        case = BenchmarkGoldCaseSchema(
            case_id="login-rule",
            source_text="Mật khẩu phải có ít nhất 12 ký tự.",
            expected_source_quotes=["Mật khẩu phải có ít nhất 12 ký tự."],
            expected_obligation_sources={
                "password_minimum": "Mật khẩu phải có ít nhất 12 ký tự."
            },
        )
        source_fact = {
            "artifact_type": "benchmark_source",
            "artifact_id": "dataset-1:login-rule",
            "artifact_version_id": "dataset-1:login-rule:source-v1",
            "source": "document",
            "authority": "benchmark_answer_key_dataset",
            "quote": "Mật khẩu phải có ít nhất 12 ký tự.",
            "source_start": 0,
            "source_end": len("Mật khẩu phải có ít nhất 12 ký tự."),
        }

        async def pipeline(_capability, *_args):
            return {
                "status": "SUCCESS",
                "clarifications": [],
                "suggestions": [],
                "model": {},
            }

        service = TestabilityBenchmarkService()
        with (
            patch(
                "src.services.testability_benchmark.extract_source_facts",
                new=AsyncMock(return_value={"source_facts": [source_fact]}),
            ),
            patch(
                "src.services.testability_benchmark.compile_testability_blueprint",
                new=AsyncMock(return_value={
                    "status": "DEGRADED",
                    "reason_codes": ["AI_OUTPUT_INVALID"],
                    "model": {},
                }),
            ) as compile_blueprint,
            patch.object(service, "_run_pipeline", new=AsyncMock(side_effect=pipeline)),
            patch("src.services.testability_benchmark.model_metadata", return_value={}),
        ):
            report = await service.run_dataset("dataset-1", [case])

        self.assertEqual(report.execution_status, "COMPLETE")
        self.assertEqual(report.pipeline_failures, [])
        self.assertEqual(len(report.pipeline_rejections), 1)
        self.assertEqual(report.pipeline_rejections[0]["pipeline"], "compiler")
        compile_blueprint.assert_awaited_once()
        args = compile_blueprint.await_args.args
        self.assertEqual(args[0], "benchmark:dataset-1")
        self.assertEqual(args[1][0].artifact_version_id, source_fact["artifact_version_id"])
        self.assertIn(source_fact["artifact_version_id"], args[2])
        self.assertEqual(args[3], {source_fact["artifact_id"]})

    async def test_provider_unavailable_makes_live_benchmark_partial(self):
        case = BenchmarkGoldCaseSchema(
            case_id="login-rule",
            source_text="Mật khẩu phải có ít nhất 12 ký tự.",
            expected_source_quotes=["Mật khẩu phải có ít nhất 12 ký tự."],
            expected_obligation_sources={
                "password_minimum": "Mật khẩu phải có ít nhất 12 ký tự."
            },
        )
        source_fact = {
            "artifact_type": "benchmark_source",
            "artifact_id": "dataset-1:login-rule",
            "artifact_version_id": "dataset-1:login-rule:source-v1",
            "source": "document",
            "authority": "benchmark_answer_key_dataset",
            "quote": "Mật khẩu phải có ít nhất 12 ký tự.",
            "source_start": 0,
            "source_end": len("Mật khẩu phải có ít nhất 12 ký tự."),
        }
        service = TestabilityBenchmarkService()
        with (
            patch(
                "src.services.testability_benchmark.extract_source_facts",
                new=AsyncMock(return_value={"source_facts": [source_fact]}),
            ),
            patch(
                "src.services.testability_benchmark.compile_testability_blueprint",
                new=AsyncMock(return_value={
                    "status": "DEGRADED",
                    "reason_codes": ["BLUEPRINT_MODEL_CALL_FAILED"],
                    "model": {},
                }),
            ),
            patch.object(
                service,
                "_run_pipeline",
                new=AsyncMock(return_value={
                    "status": "SUCCESS",
                    "clarifications": [],
                    "suggestions": [],
                    "model": {},
                }),
            ),
            patch("src.services.testability_benchmark.model_metadata", return_value={}),
        ):
            report = await service.run_dataset("dataset-1", [case])

        self.assertEqual(report.execution_status, "PARTIAL")
        self.assertEqual(len(report.pipeline_failures), 1)
        self.assertEqual(report.pipeline_failures[0]["pipeline"], "compiler")
        self.assertEqual(report.pipeline_rejections, [])
        self.assertEqual(report.clarification_savings_paired_cases, 0)
        self.assertIsNone(report.clarification_savings_vs_baseline)

    async def test_all_successful_pipelines_remain_complete(self):
        case = BenchmarkGoldCaseSchema(
            case_id="login-rule",
            source_text="Mật khẩu phải có ít nhất 12 ký tự.",
            expected_source_quotes=["Mật khẩu phải có ít nhất 12 ký tự."],
            expected_obligation_sources={
                "password_minimum": "Mật khẩu phải có ít nhất 12 ký tự."
            },
        )
        source_fact = {
            "artifact_type": "benchmark_source",
            "artifact_id": "dataset-1:login-rule",
            "artifact_version_id": "dataset-1:login-rule:source-v1",
            "source": "document",
            "authority": "benchmark_answer_key_dataset",
            "quote": "Mật khẩu phải có ít nhất 12 ký tự.",
            "source_start": 0,
            "source_end": len("Mật khẩu phải có ít nhất 12 ký tự."),
        }
        service = TestabilityBenchmarkService()
        with (
            patch(
                "src.services.testability_benchmark.extract_source_facts",
                new=AsyncMock(return_value={"source_facts": [source_fact]}),
            ),
            patch(
                "src.services.testability_benchmark.compile_testability_blueprint",
                new=AsyncMock(return_value={
                    "status": "SUCCESS",
                    "obligations": [],
                    "clarifications": [],
                    "model": {},
                }),
            ),
            patch.object(
                service,
                "_run_pipeline",
                new=AsyncMock(
                    return_value={
                        "status": "SUCCESS",
                        "obligations": [],
                        "clarifications": [],
                        "suggestions": [],
                        "model": {},
                    }
                ),
            ),
            patch("src.services.testability_benchmark.model_metadata", return_value={}),
        ):
            report = await service.run_dataset("dataset-1", [case])

        self.assertEqual(report.execution_status, "COMPLETE")
        self.assertEqual(report.pipeline_failures, [])
        self.assertEqual(report.pipeline_rejections, [])
        comparison = report.paired_pipeline_comparisons[
            "compiler_vs_direct_generation"
        ]
        self.assertEqual(comparison["paired_case_count"], 1)
        self.assertEqual(comparison["case_ids"], ["login-rule"])
        self.assertIsNotNone(comparison["left_metrics"])
        self.assertIsNotNone(comparison["right_metrics"])

    async def test_run_dataset_preserves_model_metadata_for_each_case(self):
        quote = "Mật khẩu phải có ít nhất 12 ký tự."
        cases = [
            BenchmarkGoldCaseSchema(
                case_id=case_id,
                source_text=quote,
                expected_source_quotes=[quote],
                expected_obligation_sources={"password_minimum": quote},
            )
            for case_id in ("login-rule-a", "login-rule-b")
        ]
        compiler_models = iter(("compiler-a", "compiler-b"))

        async def extract_facts(request):
            source = request["evidence"][0]
            return {
                "source_facts": [{
                    "artifact_type": source["artifact_type"],
                    "artifact_id": source["artifact_id"],
                    "artifact_version_id": source["artifact_version_id"],
                    "source": source["source"],
                    "authority": source["authority"],
                    "quote": quote,
                    "source_start": 0,
                    "source_end": len(quote),
                }]
            }

        async def compile_blueprint(*_args):
            return {
                "status": "SUCCESS",
                "obligations": [],
                "clarifications": [],
                "model": {"model": next(compiler_models)},
            }

        async def run_pipeline(capability, _dataset_id, case, *_args):
            return {
                "status": "SUCCESS",
                "clarifications": [],
                "suggestions": [],
                "model": {"model": f"{capability}-{case.case_id}"},
            }

        service = TestabilityBenchmarkService()
        with (
            patch(
                "src.services.testability_benchmark.extract_source_facts",
                new=AsyncMock(side_effect=extract_facts),
            ),
            patch(
                "src.services.testability_benchmark.compile_testability_blueprint",
                new=AsyncMock(side_effect=compile_blueprint),
            ),
            patch.object(service, "_run_pipeline", new=AsyncMock(side_effect=run_pipeline)),
            patch("src.services.testability_benchmark.model_metadata", return_value={}),
        ):
            report = await service.run_dataset("dataset-1", cases)

        metadata = report.pipeline_metadata["model_metadata_by_capability"]
        self.assertEqual(metadata["compiler"], {
            "login-rule-a": {"model": "compiler-a"},
            "login-rule-b": {"model": "compiler-b"},
        })
        for capability in ("clarification_baseline", "test_generation"):
            self.assertEqual(
                set(metadata[capability]),
                {"login-rule-a", "login-rule-b"},
            )
            self.assertEqual(
                metadata[capability]["login-rule-a"]["model"],
                f"{capability}-login-rule-a",
            )
            self.assertEqual(
                metadata[capability]["login-rule-b"]["model"],
                f"{capability}-login-rule-b",
            )

    async def test_rejected_pipeline_is_not_reported_as_zero_quality_score(self):
        quote = "Mật khẩu phải có ít nhất 12 ký tự."
        case = BenchmarkGoldCaseSchema(
            case_id="login-rule",
            source_text=quote,
            expected_source_quotes=[quote],
            expected_obligation_sources={"password_minimum": quote},
        )
        source_fact = {
            "artifact_type": "benchmark_source",
            "artifact_id": "dataset-1:login-rule",
            "artifact_version_id": "dataset-1:login-rule:source-v1",
            "source": "document",
            "authority": "benchmark_answer_key_dataset",
            "quote": quote,
            "source_start": 0,
            "source_end": len(quote),
        }
        service = TestabilityBenchmarkService()

        async def pipeline(capability, *_args):
            if capability == "test_generation":
                return {
                    "status": "DEGRADED",
                    "reason_codes": ["AI_UNGROUNDED_OUTPUT"],
                    "suggestions": [],
                    "model": {},
                }
            return {"status": "SUCCESS", "clarifications": [], "model": {}}

        with (
            patch(
                "src.services.testability_benchmark.extract_source_facts",
                new=AsyncMock(return_value={"source_facts": [source_fact]}),
            ),
            patch(
                "src.services.testability_benchmark.compile_testability_blueprint",
                new=AsyncMock(return_value={
                    "status": "SUCCESS",
                    "obligations": [{
                        "key": "password_minimum",
                        "source_quote": quote,
                    }],
                    "clarifications": [],
                    "model": {},
                }),
            ),
            patch.object(service, "_run_pipeline", new=AsyncMock(side_effect=pipeline)),
            patch("src.services.testability_benchmark.model_metadata", return_value={}),
        ):
            report = await service.run_dataset("dataset-1", [case])

        self.assertEqual(report.execution_status, "COMPLETE")
        self.assertEqual(
            report.pipeline_case_counts["direct_generation"],
            {"attempted": 1, "accepted": 0, "rejected": 1, "failed": 0},
        )
        self.assertEqual(report.clarification_savings_paired_cases, 1)
        self.assertEqual(report.clarification_savings_vs_baseline, 0.0)
        self.assertIsNone(report.direct_generation["obligation_precision"])
        self.assertEqual(
            report.cases[0]["pipeline_outcomes"]["direct_generation"], "REJECTED"
        )
        self.assertIsNone(report.cases[0]["direct_generation"]["source_quote_validity"])
        self.assertIsNone(report.cases[0]["direct_generation"]["obligation"]["precision"])
        self.assertIsNone(report.cases[0]["direct_generation"]["clarification_count"])


if __name__ == "__main__":
    unittest.main()

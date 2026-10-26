import math
import statistics
import time
import unicodedata
from datetime import datetime, timezone
from uuid import uuid4

from loguru import logger

from src.agents.runner.automation_graph import extract_source_facts
from src.prompts.testability_benchmark import (
    clarification_baseline_instruction,
    direct_generation_baseline_instruction,
)
from src.schemas.automation import AutomationFact
from src.schemas.evaluation import (
    TestabilityBenchmarkCandidate,
    TestabilityBenchmarkCase,
    TestabilityBenchmarkGoldCase,
    TestabilityBenchmarkMetricRepeatStats,
    TestabilityBenchmarkRepeatedReport,
    TestabilityBenchmarkReport,
    TestabilityBenchmarkRequest,
    validate_unique_benchmark_case_ids,
)
from src.schemas.inference_requests import TestingAutomationRequest, TestingEvidence
from src.services.ai_automation import generate_ai_automation
from src.services.inference import model_metadata
from src.services.testability_blueprint import compile_testability_blueprint


class TestabilityBenchmarkService:
    """Score compiler outputs against caller-supplied experimental answer keys."""

    SYNTHETIC_DATASET_ID = "veriq-synthetic-testability-v2"
    SYNTHETIC_DATASET_IDS = (
        SYNTHETIC_DATASET_ID,
        "veriq-synthetic-testability-v1",
    )
    SYNTHETIC_PIPELINE_NAMES = (
        "compiler",
        "direct_generation",
        "clarification_without_obligation_planning",
    )

    @classmethod
    def synthetic_cases(cls):
        complete_sources = (
            "AC-01: Khi email và mật khẩu hợp lệ, hệ thống tạo phiên đăng nhập.",
            "AC-02: Khi mật khẩu không hợp lệ, hệ thống từ chối đăng nhập.",
            "AC-03: Khi tài khoản bị khóa, hệ thống không tạo phiên đăng nhập.",
            "AC-04: Khi liên kết đặt lại mật khẩu đã hết hạn, hệ thống từ chối yêu cầu.",
            "AC-05: Khi giỏ hàng rỗng, hệ thống không cho tạo đơn hàng.",
            "AC-06: Khi thanh toán được chấp thuận, đơn hàng chuyển sang trạng thái Đã thanh toán.",
            "AC-07: Khi thanh toán bị từ chối, đơn hàng giữ trạng thái Chưa thanh toán.",
            "AC-08: Hệ thống từ chối cập nhật giỏ hàng nếu số lượng sản phẩm bằng 0.",
            "AC-09: Người dùng không có quyền quản trị không được xem trang quản trị.",
            "AC-10: Gửi lại cùng mã yêu cầu thanh toán không tạo thêm giao dịch thứ hai.",
        )
        missing_sources = (
            (
                "Hệ thống xử lý yêu cầu theo cách phù hợp.",
                ["AMBIGUITY"],
                ["AMBIGUITY"],
            ),
            (
                "Người dùng có thể cập nhật địa chỉ giao hàng.",
                ["MISSING_ACCEPTANCE_CRITERIA"],
                ["MISSING_ACCEPTANCE_CRITERIA"],
            ),
            (
                "Số lần thử đăng nhập không được vượt quá giới hạn; sau khi vượt giới hạn, tài khoản bị xử lý.",
                ["MISSING_BOUNDARY", "MISSING_STATE_RULE"],
                ["MISSING_BOUNDARY", "MISSING_STATE_RULE"],
            ),
            (
                "Khi mã thanh toán không hợp lệ, hệ thống xử lý giao dịch và cập nhật đơn hàng.",
                ["MISSING_ERROR_BEHAVIOR", "MISSING_STATE_RULE"],
                ["MISSING_ERROR_BEHAVIOR", "MISSING_STATE_RULE"],
            ),
            (
                "Nhân viên có thể xem báo cáo khi được cấp quyền.",
                ["MISSING_PERMISSION_RULE", "MISSING_ACCEPTANCE_CRITERIA"],
                ["MISSING_PERMISSION_RULE", "MISSING_ACCEPTANCE_CRITERIA"],
            ),
            (
                "Đơn hàng được cập nhật sau khi thanh toán; nếu thanh toán thất bại thì hệ thống xử lý phù hợp.",
                ["MISSING_STATE_RULE", "MISSING_ERROR_BEHAVIOR"],
                ["MISSING_STATE_RULE", "MISSING_ERROR_BEHAVIOR"],
            ),
            (
                "Mã khách hàng phải hợp lệ trước khi lưu hồ sơ; hệ thống phản hồi khi mã không hợp lệ.",
                ["MISSING_DATA_RULE", "MISSING_ERROR_BEHAVIOR"],
                ["MISSING_DATA_RULE", "MISSING_ERROR_BEHAVIOR"],
            ),
            (
                "Kết quả tìm kiếm phải được trả về nhanh.",
                ["MISSING_NON_FUNCTIONAL_CRITERIA"],
                ["MISSING_NON_FUNCTIONAL_CRITERIA"],
            ),
            (
                "Trải nghiệm sử dụng cần thân thiện.",
                ["UNTESTABLE"],
                ["UNTESTABLE"],
            ),
            (
                "Người dùng có thể yêu cầu khôi phục mật khẩu.",
                ["OMISSION", "MISSING_ACCEPTANCE_CRITERIA"],
                ["OMISSION", "MISSING_ACCEPTANCE_CRITERIA"],
            ),
        )
        duplicate_sources = (
            "AC-11: Hệ thống gửi email xác nhận sau khi tạo tài khoản thành công.",
            "AC-12: Khi người dùng đăng xuất, hệ thống kết thúc phiên hiện tại.",
            "AC-13: Hệ thống từ chối lưu biểu mẫu khi trường bắt buộc còn trống.",
            "AC-14: Người dùng chỉ xem được hồ sơ thuộc tài khoản của mình.",
            "AC-15: Khi mã xác minh còn hiệu lực, hệ thống chấp nhận mã đó.",
        )
        conflict_sources = (
            (
                "SRS: Mã xác minh có hiệu lực trong 5 phút.",
                "API Definition: Mã xác minh có hiệu lực trong 10 phút.",
            ),
            (
                "SRS: Hệ thống khóa tài khoản sau 3 lần đăng nhập sai.",
                "Quy tắc vận hành: Hệ thống khóa tài khoản sau 5 lần đăng nhập sai.",
            ),
            (
                "SRS: Số lượng đặt hàng tối đa là 20 sản phẩm.",
                "API Definition: Số lượng đặt hàng tối đa là 25 sản phẩm.",
            ),
            (
                "SRS: Phiên đăng nhập hết hạn sau 30 phút không hoạt động.",
                "Quy tắc vận hành: Phiên đăng nhập hết hạn sau 60 phút không hoạt động.",
            ),
            (
                "SRS: Mã giảm giá được áp dụng một lần cho mỗi đơn hàng.",
                "API Definition: Mã giảm giá được áp dụng tối đa hai lần cho mỗi đơn hàng.",
            ),
        )
        cases = []
        instruction = "Phân tích nội dung nguồn, giữ nguyên bằng chứng và không suy đoán dữ liệu còn thiếu."

        for index, quote in enumerate(complete_sources, start=1):
            case_id = f"SYN-COMPLETE-{index:02d}"
            source_ref = f"{case_id}-SOURCE-V1"
            obligation_key = f"{case_id}-OBLIGATION-01"
            cases.append(TestabilityBenchmarkGoldCase(
                case_id=case_id,
                scenario_family="COMPLETE",
                task_instruction=instruction,
                sources=[{
                    "source_id": f"{case_id}-SOURCE",
                    "artifact_type": "requirement",
                    "artifact_version_id": source_ref,
                    "authority": "synthetic_rule_oracle",
                    "text": quote,
                }],
                expected_source_quotes=[quote],
                expected_obligation_keys=[obligation_key],
                expected_obligation_sources={obligation_key: quote},
                expected_obligation_source_refs={obligation_key: source_ref},
            ))

        for index, (quote, categories, priorities) in enumerate(missing_sources, start=1):
            case_id = f"SYN-MISSING-{index:02d}"
            cases.append(TestabilityBenchmarkGoldCase(
                case_id=case_id,
                scenario_family="MISSING_OR_AMBIGUOUS",
                task_instruction=instruction,
                sources=[{
                    "source_id": f"{case_id}-SOURCE",
                    "artifact_type": "requirement",
                    "artifact_version_id": f"{case_id}-SOURCE-V1",
                    "authority": "synthetic_rule_oracle",
                    "text": quote,
                }],
                expected_source_quotes=[quote],
                expected_clarification_categories=categories,
                expected_clarification_priorities=priorities,
            ))

        for index, quote in enumerate(duplicate_sources, start=1):
            case_id = f"SYN-DUPLICATE-{index:02d}"
            obligation_key = f"{case_id}-OBLIGATION-01"
            cases.append(TestabilityBenchmarkGoldCase(
                case_id=case_id,
                scenario_family="DUPLICATE_OR_CONFLICT",
                task_instruction=instruction,
                sources=[
                    {
                        "source_id": f"{case_id}-SRS",
                        "artifact_type": "requirement",
                        "artifact_version_id": f"{case_id}-SRS-V1",
                        "authority": "synthetic_rule_oracle",
                        "text": quote,
                    },
                    {
                        "source_id": f"{case_id}-API",
                        "artifact_type": "api_definition",
                        "artifact_version_id": f"{case_id}-API-V1",
                        "authority": "synthetic_rule_oracle",
                        "text": quote,
                    },
                ],
                expected_source_quotes=[quote],
                expected_obligation_keys=[obligation_key],
                expected_obligation_sources={obligation_key: quote},
            ))

        for index, (first_quote, second_quote) in enumerate(conflict_sources, start=1):
            case_id = f"SYN-CONFLICT-{index:02d}"
            cases.append(TestabilityBenchmarkGoldCase(
                case_id=case_id,
                scenario_family="DUPLICATE_OR_CONFLICT",
                task_instruction=instruction,
                sources=[
                    {
                        "source_id": f"{case_id}-SRS",
                        "artifact_type": "requirement",
                        "artifact_version_id": f"{case_id}-SRS-V1",
                        "authority": "synthetic_rule_oracle",
                        "text": first_quote,
                    },
                    {
                        "source_id": f"{case_id}-API",
                        "artifact_type": "api_definition",
                        "artifact_version_id": f"{case_id}-API-V1",
                        "authority": "synthetic_rule_oracle",
                        "text": second_quote,
                    },
                ],
                expected_source_quotes=[first_quote, second_quote],
                expected_clarification_categories=["CONTRADICTION"],
                expected_clarification_priorities=["CONTRADICTION"],
            ))

        cls.validate_cases_for_scoring(cases)
        return cases

    @classmethod
    def synthetic_benchmark_design(cls):
        return {
            "dataset_kind": "SYNTHETIC_DETERMINISTIC",
            "dataset_id": cls.SYNTHETIC_DATASET_ID,
            "case_count": 30,
            "scenario_families": {
                "COMPLETE": 10,
                "MISSING_OR_AMBIGUOUS": 10,
                "DUPLICATE_OR_CONFLICT": 10,
            },
            "oracle_method": (
                "Answer keys are generated by fixed scenario construction rules: explicit behavior yields one obligation; "
                "constructed omissions yield the listed clarification categories and explicit synthetic priority order; "
                "repeated source text yields one obligation; opposing source statements yield CONTRADICTION. "
                "Priority order is authored for these synthetic examples, not independently reviewed real-world ground truth."
            ),
            "pipelines": list(cls.SYNTHETIC_PIPELINE_NAMES),
            "requested_repetitions": 3,
            "metrics": [
                "source quote validity and precision/recall",
                "obligation precision/recall with source-version grounding",
                "clarification-category precision/recall and priority NDCG",
                "pipeline acceptance, rejection, failure, and latency",
            ],
            "limitations": [
                "Synthetic cases verify execution and compare behavior on these constructed scenarios only.",
                "Synthetic multi-issue cases exercise ranking metrics, but their priority labels are authored examples rather than independent expert adjudication.",
                "Three repetitions are descriptive and do not establish statistical significance.",
                "No result from this dataset establishes production correctness, generalization, or superiority.",
            ],
        }

    @staticmethod
    def validate_cases_for_scoring(cases):
        validate_unique_benchmark_case_ids(cases)
        for case in cases:
            case.validate_for_scoring()

    @staticmethod
    def _scoring_method():
        return {
            "version": "testability-benchmark-v2",
            "aggregation": (
                "Macro average: average each applicable case score equally; metrics with no "
                "defined gold value are null and omitted from that metric's denominator. "
                "The metric_case_counts field reports each pipeline metric's actual denominator."
            ),
            "source_quote_validity": (
                "Unique normalized candidate quotes that occur contiguously in one supplied source "
                "/ all unique normalized candidate quotes."
            ),
            "source_quote_precision_recall": (
                "Set precision and recall over normalized candidate quotes and human-authored gold quotes."
            ),
            "clarification_precision_recall": (
                "Set precision and recall over predicted versus gold clarification categories; "
                "legacy exact codes are used when categories are absent from the answer key."
            ),
            "obligation_precision_recall": (
                "Set precision and recall over obligation keys. When the answer key includes source quotes, "
                "a match also requires grounded quote evidence and any specified source-version reference."
            ),
            "clarification_count": (
                "Number of predicted clarification questions (codes when present, otherwise categories); "
                "this is a workload measure, not a quality score by itself."
            ),
            "clarification_priority_ndcg": (
                "Normalized DCG against the explicit answer-key priority order, with gain 2^relevance - 1 "
                "and log2(rank + 1) discount; null when no gold order is supplied."
            ),
            "gold_obligations_unlocked_per_clarification": (
                "Gold obligations linked to predicted gold clarification categories / predicted question count; "
                "does not assert that a user actually answered those questions."
            ),
            "clarification_savings_vs_baseline": (
                "Mean baseline question count minus compiler question count over only cases where both "
                "pipelines returned SUCCESS; the report records that paired-case denominator."
            ),
            "paired_pipeline_comparisons": (
                "Each pair is rescored on the intersection of cases accepted by both pipelines; "
                "compare only these entries when acceptance differs."
            ),
            "repeated_run_stable_cases": (
                "Repeated-run means and population standard deviations are recomputed on the exact "
                "case IDs accepted in every repetition for that pipeline or pipeline pair, then "
                "restricted per metric to cases with a defined score in every repetition. If there "
                "is no common applicable case, the repeated metric is null rather than mixing cohorts."
            ),
            "limitations": [
                "Answer-key quality still depends on human authorship and independent review.",
                "Macro averages and repeated-run population standard deviation are descriptive; they do not establish statistical significance.",
                "A benchmark result does not prove production correctness, generalization, or superiority outside this dataset.",
                "Pipeline failures and output rejections are reported separately from quality scores.",
                "Synthetic rule-generated cases are engineering checks and are not a substitute for independently reviewed real-world scenarios.",
            ],
        }

    @staticmethod
    def _unscored_candidate_metrics():
        return {
            "source_quote_validity": None,
            "source_quote": {
                "precision": None,
                "recall": None,
                "matched": [],
                "unexpected": [],
                "missing": [],
            },
            "clarification": {
                "precision": None,
                "recall": None,
                "matched": [],
                "unexpected": [],
                "missing": [],
            },
            "obligation": {
                "precision": None,
                "recall": None,
                "matched": [],
                "unexpected": [],
                "missing": [],
            },
            "clarification_count": None,
            "clarification_priority": {"ndcg": None, "first_relevant_rank": None},
            "gold_obligations_unlocked_per_clarification": None,
        }

    @staticmethod
    def _normalize_source_quote(value: str) -> str:
        normalized = unicodedata.normalize("NFC", str(value or ""))
        normalized = " ".join(normalized.split())
        return normalized.rstrip(".!?。！？").rstrip()

    @classmethod
    def _quote_is_grounded_in_one_source(cls, quote: str, source_texts: list[str]) -> bool:
        normalized_quote = cls._normalize_source_quote(quote)
        return bool(normalized_quote) and any(
            normalized_quote in cls._normalize_source_quote(source_text)
            for source_text in source_texts
        )

    @staticmethod
    def _set_scores(expected: list[str], actual: list[str]) -> dict:
        expected_values = {value.strip() for value in expected if value.strip()}
        actual_values = {value.strip() for value in actual if value.strip()}
        matched = expected_values & actual_values
        return {
            "precision": (
                round(len(matched) / len(actual_values), 4)
                if actual_values else (0.0 if expected_values else None)
            ),
            "recall": (
                round(len(matched) / len(expected_values), 4)
                if expected_values else None
            ),
            "matched": sorted(matched),
            "unexpected": sorted(actual_values - expected_values),
            "missing": sorted(expected_values - actual_values),
        }

    @classmethod
    def _source_quote_scores(cls, expected: list[str], actual: list[str]) -> dict:
        expected_values = list(dict.fromkeys(
            normalized
            for normalized in (
                cls._normalize_source_quote(value) for value in expected
            )
            if normalized
        ))
        actual_values = list(dict.fromkeys(
            normalized
            for normalized in (
                cls._normalize_source_quote(value) for value in actual
            )
            if normalized
        ))
        expected_set = {value for value in expected_values if value}
        actual_set = {value for value in actual_values if value}
        covered = {
            expected_quote
            for expected_quote in expected_set
            if any(expected_quote in actual_quote for actual_quote in actual_set)
        }
        supporting = {
            actual_quote
            for actual_quote in actual_set
            if any(expected_quote in actual_quote for expected_quote in expected_set)
        }
        return {
            "precision": (
                round(len(supporting) / len(actual_values), 4)
                if actual_values else (0.0 if expected_values else None)
            ),
            "recall": (
                round(len(covered) / len(expected_values), 4)
                if expected_values else None
            ),
            "matched": sorted(covered),
            "unexpected": sorted(actual_set - supporting),
            "missing": sorted(set(expected_values) - covered),
        }

    @staticmethod
    def _maximum_obligation_matching(
        adjacency: list[list[int]], prediction_count: int
    ) -> dict[int, int]:
        expected_count = len(adjacency)
        unmatched = -1
        pair_expected = [unmatched] * expected_count
        pair_prediction = [unmatched] * prediction_count
        distance = [unmatched] * expected_count

        while True:
            queue = []
            for expected_index in range(expected_count):
                if pair_expected[expected_index] == unmatched:
                    distance[expected_index] = 0
                    queue.append(expected_index)
                else:
                    distance[expected_index] = unmatched

            shortest_augmenting_path = None
            queue_index = 0
            while queue_index < len(queue):
                expected_index = queue[queue_index]
                queue_index += 1
                next_distance = distance[expected_index] + 1
                if (
                    shortest_augmenting_path is not None
                    and next_distance > shortest_augmenting_path
                ):
                    continue
                for prediction_index in adjacency[expected_index]:
                    matched_expected = pair_prediction[prediction_index]
                    if matched_expected == unmatched:
                        if shortest_augmenting_path is None:
                            shortest_augmenting_path = next_distance
                    elif distance[matched_expected] == unmatched:
                        distance[matched_expected] = next_distance
                        queue.append(matched_expected)

            if shortest_augmenting_path is None:
                break

            augmented = False
            edge_offsets = [0] * expected_count
            for root_index in range(expected_count):
                if pair_expected[root_index] != unmatched or distance[root_index] != 0:
                    continue
                expected_stack = [root_index]
                path_predictions = []
                while expected_stack:
                    expected_index = expected_stack[-1]
                    descended = False
                    while edge_offsets[expected_index] < len(adjacency[expected_index]):
                        prediction_index = adjacency[expected_index][
                            edge_offsets[expected_index]
                        ]
                        edge_offsets[expected_index] += 1
                        next_distance = distance[expected_index] + 1
                        if next_distance > shortest_augmenting_path:
                            continue
                        matched_expected = pair_prediction[prediction_index]
                        if matched_expected == unmatched:
                            if next_distance != shortest_augmenting_path:
                                continue
                            for path_index, path_expected in enumerate(
                                expected_stack[:-1]
                            ):
                                path_prediction = path_predictions[path_index]
                                pair_expected[path_expected] = path_prediction
                                pair_prediction[path_prediction] = path_expected
                            pair_expected[expected_stack[-1]] = prediction_index
                            pair_prediction[prediction_index] = expected_stack[-1]
                            augmented = True
                            break
                        if distance[matched_expected] == next_distance:
                            path_predictions.append(prediction_index)
                            expected_stack.append(matched_expected)
                            descended = True
                            break
                    if augmented:
                        break
                    if descended:
                        continue
                    distance[expected_index] = unmatched
                    expected_stack.pop()
                    if path_predictions and len(path_predictions) >= len(expected_stack):
                        path_predictions.pop()

            if not augmented:
                break

        return {
            prediction_index: expected_index
            for prediction_index, expected_index in enumerate(pair_prediction)
            if expected_index != unmatched
        }

    @staticmethod
    def _case_source_texts(case) -> list[str]:
        if case.sources:
            return [source.text for source in case.sources if source.text.strip()]
        return [case.source_text] if case.source_text.strip() else []

    @classmethod
    def _candidate_scores(
        cls, case, candidate, *, score_obligations=True, score_clarifications=True
    ) -> dict:
        def non_empty_values(values):
            return [value.strip() for value in values if isinstance(value, str) and value.strip()]

        source_texts = cls._case_source_texts(case)
        quote_scores = cls._source_quote_scores(
            case.expected_source_quotes,
            candidate.source_quotes,
        )
        grounded_quotes = [
            quote for quote in candidate.source_quotes
            if cls._quote_is_grounded_in_one_source(quote, source_texts)
        ]
        unique_candidate_quotes = {
            cls._normalize_source_quote(quote)
            for quote in candidate.source_quotes
            if cls._normalize_source_quote(quote)
        }
        unique_grounded_quotes = {
            cls._normalize_source_quote(quote) for quote in grounded_quotes
        }
        expected_clarifications = (
            case.expected_clarification_categories or case.expected_clarification_codes
        )
        actual_clarifications = non_empty_values(candidate.clarification_categories)
        if not actual_clarifications:
            actual_clarifications = non_empty_values(candidate.clarification_codes)
        clarification_scores = (
            cls._set_scores(expected_clarifications, actual_clarifications)
            if score_clarifications else {"precision": None, "recall": None, "matched": [], "unexpected": [], "missing": []}
        )
        if not score_obligations:
            obligation_scores = {
                "precision": None, "recall": None, "matched": [], "unexpected": [], "missing": []
            }
        elif case.expected_obligation_sources:
            predicted_obligations = candidate.obligation_evidence
            predicted_keys = sorted(
                set(non_empty_values(candidate.obligation_keys))
                | set(non_empty_values(list(predicted_obligations)))
                | set(non_empty_values(list(candidate.obligation_citations)))
            )
            remaining_predictions = set(predicted_keys)
            predicted_count = len(remaining_predictions)
            expected_keys = sorted(case.expected_obligation_sources)
            grounded_unversioned = {}
            grounded_versioned = {}
            for predicted_key in predicted_keys:
                grounded_unversioned[predicted_key] = [
                    cls._normalize_source_quote(quote)
                    for quote in predicted_obligations.get(predicted_key, [])
                    if cls._quote_is_grounded_in_one_source(quote, source_texts)
                ]
                grounded_versioned[predicted_key] = [
                    (cls._normalize_source_quote(citation.quote), citation.source_ref)
                    for citation in candidate.obligation_citations.get(predicted_key, [])
                    if cls._quote_is_grounded_in_one_source(citation.quote, source_texts)
                ]
            adjacency = []
            for expected_key in expected_keys:
                expected_quote = cls._normalize_source_quote(
                    case.expected_obligation_sources[expected_key]
                )
                expected_source_ref = case.expected_obligation_source_refs.get(expected_key)
                compatible_predictions = []
                for prediction_index, predicted_key in enumerate(predicted_keys):
                    if expected_source_ref:
                        is_compatible = any(
                            quote == expected_quote and source_ref == expected_source_ref
                            for quote, source_ref in grounded_versioned[predicted_key]
                        )
                    else:
                        is_compatible = any(
                            quote == expected_quote
                            for quote in grounded_unversioned[predicted_key]
                        )
                    if is_compatible:
                        compatible_predictions.append(prediction_index)
                adjacency.append(compatible_predictions)
            prediction_to_expected = cls._maximum_obligation_matching(
                adjacency, len(predicted_keys)
            )
            matched_prediction_to_expected = {
                predicted_keys[prediction_index]: expected_keys[expected_index]
                for prediction_index, expected_index in prediction_to_expected.items()
            }
            matched_obligations = list(matched_prediction_to_expected.values())
            remaining_predictions.difference_update(matched_prediction_to_expected)
            expected_count = len(case.expected_obligation_sources)
            obligation_scores = {
                "precision": (
                    round(len(matched_obligations) / predicted_count, 4)
                    if predicted_count else (0.0 if expected_count else None)
                ),
                "recall": round(len(matched_obligations) / expected_count, 4) if expected_count else None,
                "matched": sorted(matched_obligations),
                "unexpected": sorted(remaining_predictions),
                "missing": sorted(set(case.expected_obligation_sources) - set(matched_obligations)),
            }
        else:
            obligation_scores = cls._set_scores(case.expected_obligation_keys, candidate.obligation_keys)
        priority_scores = (
            cls._clarification_priority_scores(
                case.expected_clarification_priorities,
                actual_clarifications,
            )
            if score_clarifications else {"ndcg": None, "first_relevant_rank": None}
        )
        clarified = {
            obligation
            for code in set(actual_clarifications)
            if code in expected_clarifications
            for obligation in case.expected_clarification_unlocks.get(code, [])
        }
        clarification_count = (
            len(non_empty_values(candidate.clarification_codes) or actual_clarifications)
            if score_clarifications else None
        )
        return {
            "source_quote_validity": (
                round(len(unique_grounded_quotes) / len(unique_candidate_quotes), 4)
                if unique_candidate_quotes else None
            ),
            "source_quote": quote_scores,
            "clarification": clarification_scores,
            "obligation": obligation_scores,
            "clarification_count": clarification_count,
            "clarification_priority": priority_scores,
            "gold_obligations_unlocked_per_clarification": (
                round(len(clarified) / clarification_count, 4)
                if clarification_count else None
            ),
        }

    @staticmethod
    def _clarification_priority_scores(expected: list[str], actual: list[str]) -> dict:
        """Score whether higher-priority gold clarifications are asked earlier."""
        expected_order = list(dict.fromkeys(value.strip() for value in expected if value.strip()))
        actual_order = list(dict.fromkeys(value.strip() for value in actual if value.strip()))
        if not expected_order:
            return {"ndcg": None, "first_relevant_rank": None}
        relevance = {
            value: len(expected_order) - index
            for index, value in enumerate(expected_order)
        }
        discounted_gain = sum(
            (2 ** relevance.get(value, 0) - 1) / math.log2(index + 2)
            for index, value in enumerate(actual_order)
        )
        ideal_gain = sum(
            (2 ** (len(expected_order) - index) - 1) / math.log2(index + 2)
            for index in range(len(expected_order))
        )
        first_relevant_rank = next(
            (index + 1 for index, value in enumerate(actual_order) if value in relevance),
            None,
        )
        return {
            "ndcg": round(discounted_gain / ideal_gain, 4) if ideal_gain else 1.0,
            "first_relevant_rank": first_relevant_rank,
        }

    async def evaluate(self, request: TestabilityBenchmarkRequest) -> TestabilityBenchmarkReport:
        """Compare the obligation-aware compiler with two explicit baselines."""
        cases = []
        clarification_scores = []
        compiler_scores = []
        direct_scores = []
        for case in request.cases:
            clarification = self._candidate_scores(
                case,
                case.clarification_without_obligation_planning,
                score_obligations=False,
            )
            compiler = self._candidate_scores(case, case.compiler)
            direct = self._candidate_scores(
                case, case.direct_generation, score_clarifications=False
            )
            clarification_scores.append(clarification)
            compiler_scores.append(compiler)
            direct_scores.append(direct)
            cases.append(
                {
                    "case_id": case.case_id,
                    "scenario_family": case.scenario_family,
                    "clarification_without_obligation_planning": clarification,
                    "compiler": compiler,
                    "direct_generation": direct,
                }
            )

        def average_metric(values, key):
            applicable = [value[key] for value in values if value[key] is not None]
            return round(sum(applicable) / len(applicable), 4) if applicable else None

        def aggregate(values):
            return {
                "source_quote_validity": average_metric(values, "source_quote_validity"),
                "source_quote_precision": average_metric(
                    [{"metric": value["source_quote"]["precision"]} for value in values],
                    "metric",
                ),
                "source_quote_recall": average_metric(
                    [{"metric": value["source_quote"]["recall"]} for value in values],
                    "metric",
                ),
                "clarification_precision": average_metric(
                    [{"metric": value["clarification"]["precision"]} for value in values],
                    "metric",
                ),
                "clarification_recall": average_metric(
                    [{"metric": value["clarification"]["recall"]} for value in values],
                    "metric",
                ),
                "obligation_precision": average_metric(
                    [{"metric": value["obligation"]["precision"]} for value in values],
                    "metric",
                ),
                "obligation_recall": average_metric(
                    [{"metric": value["obligation"]["recall"]} for value in values],
                    "metric",
                ),
                "average_clarification_count": average_metric(
                    [{"metric": value["clarification_count"]} for value in values],
                    "metric",
                ),
                "clarification_priority_ndcg": average_metric(
                    [{"metric": value["clarification_priority"]["ndcg"]} for value in values],
                    "metric",
                ),
                "gold_obligations_unlocked_per_clarification": average_metric(
                    [{"metric": value["gold_obligations_unlocked_per_clarification"]} for value in values],
                    "metric",
                ),
            }

        metric_paths = {
            "source_quote_validity": ("source_quote_validity",),
            "source_quote_precision": ("source_quote", "precision"),
            "source_quote_recall": ("source_quote", "recall"),
            "clarification_precision": ("clarification", "precision"),
            "clarification_recall": ("clarification", "recall"),
            "obligation_precision": ("obligation", "precision"),
            "obligation_recall": ("obligation", "recall"),
            "average_clarification_count": ("clarification_count",),
            "clarification_priority_ndcg": ("clarification_priority", "ndcg"),
            "gold_obligations_unlocked_per_clarification": (
                "gold_obligations_unlocked_per_clarification",
            ),
        }

        def metric_case_counts(values):
            counts = {}
            for metric_name, path in metric_paths.items():
                applicable = []
                for value in values:
                    score = value
                    for key in path:
                        score = score.get(key) if isinstance(score, dict) else None
                    if score is not None:
                        applicable.append(score)
                counts[metric_name] = len(applicable)
            return counts

        report = TestabilityBenchmarkReport(
            total_cases=len(cases),
            clarification_without_obligation_planning=aggregate(clarification_scores),
            compiler=aggregate(compiler_scores),
            direct_generation=aggregate(direct_scores),
            cases=cases,
            scenario_family_counts={
                family: sum(case.scenario_family == family for case in request.cases)
                for family in (
                    "COMPLETE",
                    "MISSING_OR_AMBIGUOUS",
                    "DUPLICATE_OR_CONFLICT",
                )
                if any(case.scenario_family == family for case in request.cases)
            },
            clarification_savings_vs_baseline=(
                round(
                    sum(
                        baseline["clarification_count"] - compiler["clarification_count"]
                        for baseline, compiler in zip(clarification_scores, compiler_scores)
                    ) / len(cases),
                    4,
                )
                if cases else None
            ),
            clarification_savings_paired_cases=len(cases),
            scoring_method=self._scoring_method(),
        )
        report.metric_case_counts = {
            "clarification_without_obligation_planning": metric_case_counts(clarification_scores),
            "compiler": metric_case_counts(compiler_scores),
            "direct_generation": metric_case_counts(direct_scores),
        }
        report.benchmark_design = {
            "answer_key_basis": "caller_supplied_case_answer_key",
            "interpretation": "Descriptive only; not a correctness or superiority guarantee.",
        }
        logger.info("Testability compiler benchmark completed cases={}", report.total_cases)
        return report

    @staticmethod
    def _source_evidence(case, dataset_id):
        if case.sources:
            return [
                {
                    "artifact_type": source.artifact_type,
                    "artifact_id": f"{dataset_id}:{case.case_id}:{source.source_id}",
                    "artifact_version_id": source.artifact_version_id,
                    "source": "document",
                    "authority": source.authority,
                    "text": source.text,
                }
                for source in case.sources
            ]
        return [{
            "artifact_type": "benchmark_source",
            "artifact_id": f"{dataset_id}:{case.case_id}",
            "artifact_version_id": f"{dataset_id}:{case.case_id}:source-v1",
            "source": "document",
            "authority": "benchmark_answer_key_dataset",
            "text": case.source_text,
        }]

    @staticmethod
    def _candidate_from_blueprint(output):
        obligations = output.get("obligations", [])
        clarifications = output.get("clarifications", [])
        obligation_evidence = {
            str(item.get("key", "")): [str(item.get("source_quote", ""))]
            for item in obligations
            if item.get("key") and item.get("source_quote")
        }
        return TestabilityBenchmarkCandidate(
            source_quotes=list(dict.fromkeys(
                [item.get("source_quote", "") for item in obligations]
                + [item.get("source_quote", "") for item in clarifications]
            )),
            clarification_codes=[item.get("code", "") for item in clarifications],
            clarification_categories=[item.get("category", "") for item in clarifications],
            obligation_keys=[item.get("key", "") for item in obligations],
            obligation_evidence=obligation_evidence,
            obligation_citations={
                str(item.get("key", "")): [{
                    "quote": str(item.get("source_quote", "")),
                    "source_ref": str(item.get("source_ref", "")),
                }]
                for item in obligations
                if item.get("key") and item.get("source_ref") and item.get("source_quote")
            },
        )

    @staticmethod
    def _candidate_from_clarification(output):
        return TestabilityBenchmarkCandidate(
            source_quotes=[
                item.get("source_quote", "") for item in output.get("clarifications", [])
            ],
            clarification_codes=[
                item.get("code", "") for item in output.get("clarifications", [])
            ],
            clarification_categories=[
                item.get("category", "") for item in output.get("clarifications", [])
            ],
        )

    @staticmethod
    def _candidate_from_direct_generation(output):
        cases = output.get("suggestions", [])
        quotes = []
        obligations = []
        obligation_evidence = {}
        obligation_citations = {}
        for case in cases:
            case_obligations = list(
                dict.fromkeys(
                    str(item)
                    for item in case.get("coverage_obligations", [])
                    if item
                )
            )
            obligations.extend(case_obligations)
            case_quotes = list(dict.fromkeys(
                item.get("quote", "") for item in case.get("evidence_quotes", [])
            ))
            quotes.extend(case_quotes)
            case_citations = [
                {
                    "quote": str(item.get("quote", "")),
                    "source_ref": str(item.get("evidence_ref", "")),
                }
                for item in case.get("evidence_quotes", [])
                if item.get("quote") and item.get("evidence_ref")
            ]
            for mapping in case.get("obligation_evidence", []):
                obligation = str(mapping.get("obligation_key") or "")
                linked_quotes = [
                    str(item.get("quote", ""))
                    for item in mapping.get("evidence_quotes", [])
                    if item.get("quote") and item.get("evidence_ref")
                ]
                linked_citations = [
                    {
                        "quote": str(item.get("quote", "")),
                        "source_ref": str(item.get("evidence_ref", "")),
                    }
                    for item in mapping.get("evidence_quotes", [])
                    if item.get("quote") and item.get("evidence_ref")
                ]
                if obligation in case_obligations and linked_quotes:
                    obligation_evidence.setdefault(obligation, [])
                    obligation_citations.setdefault(obligation, [])
                    obligation_evidence[obligation].extend(linked_quotes)
                    obligation_citations[obligation].extend(linked_citations)
            if len(case_obligations) == 1 and not case.get("obligation_evidence"):
                obligation = case_obligations[0]
                if case_citations:
                    obligation_evidence.setdefault(obligation, []).extend(
                        citation["quote"] for citation in case_citations
                    )
                    obligation_citations.setdefault(obligation, []).extend(case_citations)
        obligation_evidence = {
            obligation: list(dict.fromkeys(quotes))
            for obligation, quotes in obligation_evidence.items()
        }
        obligation_citations = {
            obligation: list({
                (citation["quote"], citation["source_ref"]): citation
                for citation in citations
            }.values())
            for obligation, citations in obligation_citations.items()
        }
        return TestabilityBenchmarkCandidate(
            source_quotes=list(dict.fromkeys(quotes)),
            obligation_keys=list(dict.fromkeys(obligations)),
            obligation_evidence=obligation_evidence,
            obligation_citations=obligation_citations,
        )

    async def _run_pipeline(self, capability, dataset_id, case, evidence, instruction):
        request = TestingAutomationRequest(
            capability=capability,
            project_id=f"benchmark:{dataset_id}",
            instruction=instruction,
            evidence=[TestingEvidence.model_validate(item) for item in evidence],
        )
        result = await generate_ai_automation(request)
        return result.model_dump(mode="json")

    @staticmethod
    def _verified_fact_evidence(facts, source_evidence):
        grouped = {}
        sources_by_ref = {
            str(item.get("artifact_version_id") or item.get("artifact_id")): item
            for item in source_evidence
            if item.get("artifact_id")
        }
        for fact in facts:
            reference = str(fact.get("artifact_version_id") or "")
            quote = str(fact.get("quote") or "").strip()
            source = sources_by_ref.get(reference)
            start = fact.get("source_start")
            end = fact.get("source_end")
            source_text = str((source or {}).get("text") or "")
            if (
                not reference
                or not source
                or str(source.get("artifact_id") or "") != str(fact.get("artifact_id") or "")
                or not quote
                or type(start) is not int
                or type(end) is not int
                or start < 0
                or end > len(source_text)
                or end <= start
                or end - start != len(quote)
                or source_text[start:end] != quote
            ):
                continue
            entry = grouped.setdefault(reference, {
                "artifact_type": fact.get("artifact_type") or "benchmark_source",
                "artifact_id": fact.get("artifact_id"),
                "artifact_version_id": fact.get("artifact_version_id"),
                "authority": fact.get("authority") or "benchmark_answer_key_dataset",
                "text": [],
            })
            if quote not in entry["text"]:
                entry["text"].append(quote)
        return [
            {**value, "text": "\n".join(value["text"])}
            for value in grouped.values()
        ]

    async def _run_benchmark_pipeline(self, pipeline, dataset_id, gold_case, source_evidence):
        if pipeline == "compiler":
            extraction = await extract_source_facts({"evidence": source_evidence})
            verified = self._verified_fact_evidence(
                extraction.get("source_facts", []), source_evidence
            )
            if not verified:
                raise RuntimeError("NO_VERIFIED_SOURCE_FACTS")
            evidence_by_ref = {
                str(item.get("artifact_version_id") or item.get("artifact_id")): item
                for item in source_evidence
            }
            source_facts = [
                AutomationFact.model_validate(item)
                for item in extraction.get("source_facts", [])
            ]
            output = await compile_testability_blueprint(
                f"benchmark:{dataset_id}",
                source_facts,
                evidence_by_ref,
                {str(item["artifact_id"]) for item in source_evidence},
            )
            return self._candidate_from_blueprint(output), output, "compiler"
        if pipeline == "clarification_without_obligation_planning":
            output = await self._run_pipeline(
                "clarification_baseline",
                dataset_id,
                gold_case,
                source_evidence,
                clarification_baseline_instruction(gold_case.task_instruction),
            )
            return (
                self._candidate_from_clarification(output),
                output,
                "clarification_baseline",
            )
        if pipeline == "direct_generation":
            output = await self._run_pipeline(
                "test_generation",
                dataset_id,
                gold_case,
                source_evidence,
                direct_generation_baseline_instruction(gold_case.task_instruction),
            )
            return self._candidate_from_direct_generation(output), output, "test_generation"
        raise ValueError("BENCHMARK_PIPELINE_UNKNOWN")

    async def run_dataset(self, dataset_id: str, cases: list[TestabilityBenchmarkGoldCase], pipeline_order=None):
        """Run the actual extraction/compiler, clarification, and direct-test pipelines."""
        self.validate_cases_for_scoring(cases)
        available_pipelines = (
            "compiler",
            "clarification_without_obligation_planning",
            "direct_generation",
        )
        pipeline_order = tuple(pipeline_order or available_pipelines)
        if len(pipeline_order) != len(available_pipelines) or set(pipeline_order) != set(available_pipelines):
            raise ValueError("BENCHMARK_PIPELINE_ORDER_INVALID")
        started = time.perf_counter()
        run_id = f"TBR-{uuid4().hex}"
        scored_cases = []
        failures = []
        rejections = []
        raw_outputs = {}
        pipeline_outcomes = {}
        model_metadata_by_capability = {}

        def failure_code(error):
            value = str(error)
            if isinstance(error, RuntimeError) and value and all(
                character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_;-" for character in value
            ):
                return value[:160]
            return type(error).__name__

        def record_non_success(case_id, pipeline, output):
            reason_codes = output.get("reason_codes", [])
            provider_failure = any(
                "PROVIDER_UNAVAILABLE" in str(code)
                or "MODEL_CALL_FAILED" in str(code)
                for code in reason_codes
            ) or output.get("degraded_mode") == "DEGRADED_AI"
            record = {
                "case_id": case_id,
                "pipeline": pipeline,
                "reason_codes": reason_codes,
            }
            if provider_failure:
                failures.append({**record, "error_code": reason_codes[0] if reason_codes else "MODEL_CALL_FAILED"})
            else:
                rejections.append(record)

        def outcome_for(output):
            if output.get("status") == "SUCCESS":
                return "ACCEPTED"
            reason_codes = output.get("reason_codes", [])
            if output.get("degraded_mode") == "DEGRADED_AI" or any(
                "PROVIDER_UNAVAILABLE" in str(code)
                or "MODEL_CALL_FAILED" in str(code)
                for code in reason_codes
            ):
                return "FAILED"
            return "REJECTED"

        for gold_case in cases:
            source_evidence = self._source_evidence(gold_case, dataset_id)
            compiler_candidate = TestabilityBenchmarkCandidate()
            clarification_candidate = TestabilityBenchmarkCandidate()
            direct_candidate = TestabilityBenchmarkCandidate()
            raw_outputs[gold_case.case_id] = {}
            pipeline_outcomes[gold_case.case_id] = {}

            candidates = {
                "compiler": compiler_candidate,
                "clarification_without_obligation_planning": clarification_candidate,
                "direct_generation": direct_candidate,
            }
            for pipeline in pipeline_order:
                try:
                    candidate, output, capability = await self._run_benchmark_pipeline(
                        pipeline, dataset_id, gold_case, source_evidence
                    )
                    candidates[pipeline] = candidate
                    raw_outputs[gold_case.case_id][pipeline] = output
                    pipeline_outcomes[gold_case.case_id][pipeline] = outcome_for(output)
                    model_metadata_by_capability.setdefault(capability, {})[
                        gold_case.case_id
                    ] = output.get("model", {})
                    if output.get("status") != "SUCCESS":
                        record_non_success(gold_case.case_id, pipeline, output)
                except Exception as error:
                    pipeline_outcomes[gold_case.case_id][pipeline] = "FAILED"
                    failures.append({
                        "case_id": gold_case.case_id,
                        "pipeline": pipeline,
                        "error_code": failure_code(error),
                    })
            compiler_candidate = candidates["compiler"]
            clarification_candidate = candidates["clarification_without_obligation_planning"]
            direct_candidate = candidates["direct_generation"]

            scored_cases.append(TestabilityBenchmarkCase(
                **gold_case.model_dump(),
                compiler=compiler_candidate,
                clarification_without_obligation_planning=clarification_candidate,
                direct_generation=direct_candidate,
            ))

        report = await self.evaluate(TestabilityBenchmarkRequest(cases=scored_cases))
        pipeline_fields = {
            "compiler": "compiler",
            "clarification_without_obligation_planning": "clarification_without_obligation_planning",
            "direct_generation": "direct_generation",
        }
        report.pipeline_case_counts = {}
        for pipeline, report_field in pipeline_fields.items():
            outcomes = [items.get(pipeline) for items in pipeline_outcomes.values()]
            accepted_ids = {
                case_id for case_id, items in pipeline_outcomes.items()
                if items.get(pipeline) == "ACCEPTED"
            }
            report.pipeline_case_counts[pipeline] = {
                "attempted": len(outcomes),
                "accepted": outcomes.count("ACCEPTED"),
                "rejected": outcomes.count("REJECTED"),
                "failed": outcomes.count("FAILED"),
            }
            if accepted_ids:
                accepted_cases = [case for case in scored_cases if case.case_id in accepted_ids]
                accepted_report = await self.evaluate(
                    TestabilityBenchmarkRequest(cases=accepted_cases)
                )
                setattr(report, report_field, getattr(accepted_report, report_field))
                report.metric_case_counts[pipeline] = accepted_report.metric_case_counts[
                    report_field
                ]
            else:
                setattr(report, report_field, {
                    "source_quote_validity": None,
                    "source_quote_precision": None,
                    "source_quote_recall": None,
                    "clarification_precision": None,
                    "clarification_recall": None,
                    "obligation_precision": None,
                    "obligation_recall": None,
                    "average_clarification_count": None,
                    "clarification_priority_ndcg": None,
                    "gold_obligations_unlocked_per_clarification": None,
                })
                report.metric_case_counts[pipeline] = {
                    metric_name: 0
                    for metric_name in (
                        "source_quote_validity",
                        "source_quote_precision",
                        "source_quote_recall",
                        "clarification_precision",
                        "clarification_recall",
                        "obligation_precision",
                        "obligation_recall",
                        "average_clarification_count",
                        "clarification_priority_ndcg",
                        "gold_obligations_unlocked_per_clarification",
                    )
                }

        accepted_by_pipeline = {
            pipeline: {
                case_id
                for case_id, outcomes in pipeline_outcomes.items()
                if outcomes.get(pipeline) == "ACCEPTED"
            }
            for pipeline in pipeline_fields
        }
        comparison_pairs = (
            ("compiler", "direct_generation"),
            ("compiler", "clarification_without_obligation_planning"),
            ("direct_generation", "clarification_without_obligation_planning"),
        )
        report.paired_pipeline_comparisons = {}
        for left, right in comparison_pairs:
            common_case_ids = accepted_by_pipeline[left] & accepted_by_pipeline[right]
            comparison_key = f"{left}_vs_{right}"
            if not common_case_ids:
                report.paired_pipeline_comparisons[comparison_key] = {
                    "left_pipeline": left,
                    "right_pipeline": right,
                    "paired_case_count": 0,
                    "case_ids": [],
                    "left_metrics": None,
                    "right_metrics": None,
                    "left_metric_case_counts": {},
                    "right_metric_case_counts": {},
                }
                continue

            paired_cases = [
                case for case in scored_cases if case.case_id in common_case_ids
            ]
            paired_report = await self.evaluate(
                TestabilityBenchmarkRequest(cases=paired_cases)
            )
            report.paired_pipeline_comparisons[comparison_key] = {
                "left_pipeline": left,
                "right_pipeline": right,
                "paired_case_count": len(paired_cases),
                "case_ids": sorted(common_case_ids),
                "left_metrics": getattr(paired_report, pipeline_fields[left]),
                "right_metrics": getattr(paired_report, pipeline_fields[right]),
                "left_metric_case_counts": paired_report.metric_case_counts[left],
                "right_metric_case_counts": paired_report.metric_case_counts[right],
            }

        paired_cases = [
            case for case in scored_cases
            if pipeline_outcomes.get(case.case_id, {}).get("compiler") == "ACCEPTED"
            and pipeline_outcomes.get(case.case_id, {}).get(
                "clarification_without_obligation_planning"
            ) == "ACCEPTED"
        ]
        report.clarification_savings_paired_cases = len(paired_cases)
        if paired_cases:
            paired_report = await self.evaluate(
                TestabilityBenchmarkRequest(cases=paired_cases)
            )
            report.clarification_savings_vs_baseline = (
                paired_report.clarification_savings_vs_baseline
            )
        else:
            report.clarification_savings_vs_baseline = None
        report_pipeline_fields = {
            "compiler": "compiler",
            "clarification_without_obligation_planning": "clarification_without_obligation_planning",
            "direct_generation": "direct_generation",
        }
        for case in report.cases:
            outcomes = pipeline_outcomes.get(case["case_id"], {})
            case["pipeline_outcomes"] = outcomes
            for report_field, pipeline in report_pipeline_fields.items():
                if outcomes.get(pipeline) != "ACCEPTED":
                    case[report_field] = self._unscored_candidate_metrics()
        report.run_id = run_id
        report.dataset_id = dataset_id
        report.scenario_family_counts = {
            family: sum(case.scenario_family == family for case in cases)
            for family in (
                "COMPLETE",
                "MISSING_OR_AMBIGUOUS",
                "DUPLICATE_OR_CONFLICT",
            )
            if any(case.scenario_family == family for case in cases)
        }
        report.benchmark_design = (
            self.synthetic_benchmark_design()
            if dataset_id == self.SYNTHETIC_DATASET_ID
            else {
                "answer_key_basis": "caller_supplied_case_answer_key",
                "interpretation": "Descriptive only; not a correctness or superiority guarantee.",
            }
        )
        report.pipeline_metadata = {
            "provider": model_metadata().get("provider"),
            "model": model_metadata().get("model"),
            "pipelines": [
                "verified_source_fact_extraction_plus_testability_blueprint_compilation",
                "clarification_baseline_without_obligation_planning",
                "direct_test_generation_with_grounding_review",
            ],
            "execution_order": list(pipeline_order),
            "candidate_outputs": raw_outputs,
            "model_metadata_by_capability": model_metadata_by_capability,
        }
        report.pipeline_failures = failures
        report.pipeline_rejections = rejections
        report.duration_ms = round((time.perf_counter() - started) * 1000)
        report.execution_status = "PARTIAL" if failures else "COMPLETE"
        report.created_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Live testability benchmark completed run_id={} dataset_id={} cases={} pipeline_failures={}",
            run_id, dataset_id, report.total_cases, len(failures),
        )
        return report

    async def run_synthetic_benchmark(self, repetitions=3, on_report=None):
        if repetitions != 3:
            raise ValueError("SYNTHETIC_BENCHMARK_REQUIRES_THREE_REPETITIONS")
        cases = self.synthetic_cases()
        design = self.synthetic_benchmark_design()

        async def annotate_and_save(report):
            report.benchmark_design = design
            report.scenario_family_counts = {
                family: sum(case.scenario_family == family for case in cases)
                for family in (
                    "COMPLETE",
                    "MISSING_OR_AMBIGUOUS",
                    "DUPLICATE_OR_CONFLICT",
                )
            }
            report.pipeline_metadata = {
                **report.pipeline_metadata,
                "benchmark_design": design,
            }
            if on_report is not None:
                await on_report(report)

        report = await self.run_repeated_dataset(
            self.SYNTHETIC_DATASET_ID,
            cases,
            repetitions=repetitions,
            on_report=annotate_and_save,
        )
        report.benchmark_design = design
        return report

    async def run_repeated_dataset(
        self,
        dataset_id: str,
        cases: list[TestabilityBenchmarkGoldCase],
        repetitions: int = 3,
        on_report=None,
    ) -> TestabilityBenchmarkRepeatedReport:
        if repetitions < 1 or repetitions > 5:
            raise ValueError("BENCHMARK_REPETITIONS_OUT_OF_RANGE")
        self.validate_cases_for_scoring(cases)

        reports = []
        repetition_failures = []
        pipeline_names = (
            "compiler",
            "clarification_without_obligation_planning",
            "direct_generation",
        )
        for repetition in range(1, repetitions + 1):
            try:
                rotation = (repetition - 1) % len(pipeline_names)
                pipeline_order = pipeline_names[rotation:] + pipeline_names[:rotation]
                report = await self.run_dataset(
                    dataset_id, cases, pipeline_order=pipeline_order
                )
            except Exception as error:
                repetition_failures.append({
                    "repetition_index": repetition,
                    "error_code": type(error).__name__.upper(),
                })
                continue
            report.pipeline_metadata = {
                **report.pipeline_metadata,
                "repetition_index": repetition,
                "requested_repetitions": repetitions,
            }
            reports.append(report)
            if on_report is not None:
                await on_report(report)

        return self.summarize_repeated_reports(
            dataset_id, repetitions, reports, repetition_failures
        )

    @staticmethod
    def summarize_repeated_reports(
        dataset_id, repetitions, reports, repetition_failures=None
    ):
        repetition_failures = repetition_failures or []
        metric_names = (
            "source_quote_validity",
            "source_quote_precision",
            "source_quote_recall",
            "clarification_precision",
            "clarification_recall",
            "obligation_precision",
            "obligation_recall",
            "average_clarification_count",
            "clarification_priority_ndcg",
            "gold_obligations_unlocked_per_clarification",
        )

        metric_paths = {
            "source_quote_validity": ("source_quote_validity",),
            "source_quote_precision": ("source_quote", "precision"),
            "source_quote_recall": ("source_quote", "recall"),
            "clarification_precision": ("clarification", "precision"),
            "clarification_recall": ("clarification", "recall"),
            "obligation_precision": ("obligation", "precision"),
            "obligation_recall": ("obligation", "recall"),
            "average_clarification_count": ("clarification_count",),
            "clarification_priority_ndcg": ("clarification_priority", "ndcg"),
            "gold_obligations_unlocked_per_clarification": (
                "gold_obligations_unlocked_per_clarification",
            ),
        }

        def case_metric(case, pipeline_name, metric_name):
            value = (case.get(pipeline_name) or {})
            for key in metric_paths[metric_name]:
                if not isinstance(value, dict):
                    return None
                value = value.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            return float(value)

        def metric_statistics(values, case_ids=None):
            return TestabilityBenchmarkMetricRepeatStats(
                observed_runs=len(values),
                mean=round(statistics.fmean(values), 4) if values else None,
                population_stddev=(
                    round(statistics.pstdev(values), 4) if len(values) >= 2 else None
                ),
                minimum=round(min(values), 4) if values else None,
                maximum=round(max(values), 4) if values else None,
                paired_case_count=len(case_ids) if case_ids is not None else None,
                paired_case_ids=sorted(case_ids) if case_ids is not None else [],
            )

        def accepted_case_maps(pipeline_name):
            return [
                {
                    str(case.get("case_id")): case
                    for case in report.cases
                    if case.get("case_id")
                    and case.get("pipeline_outcomes", {}).get(pipeline_name) == "ACCEPTED"
                }
                for report in reports
            ]

        def common_ids(case_maps):
            if not case_maps:
                return set()
            return set.intersection(*(set(case_map) for case_map in case_maps))

        def run_metric_values(case_map, case_ids, pipeline_name, metric_name):
            values = [
                value
                for case_id in case_ids
                if (value := case_metric(case_map[case_id], pipeline_name, metric_name)) is not None
            ]
            return statistics.fmean(values) if values else None

        pipeline_statistics = {}
        for pipeline_name in (
            "compiler",
            "clarification_without_obligation_planning",
            "direct_generation",
        ):
            case_maps = accepted_case_maps(pipeline_name)
            stable_case_ids = common_ids(case_maps)
            metrics = {}
            for metric_name in metric_names:
                metric_case_ids = {
                    case_id
                    for case_id in stable_case_ids
                    if all(
                        case_metric(case_map[case_id], pipeline_name, metric_name)
                        is not None
                        for case_map in case_maps
                    )
                }
                values = [
                    value
                    for case_map in case_maps
                    if (value := run_metric_values(
                        case_map,
                        {
                            case_id
                            for case_id in stable_case_ids
                            if case_metric(case_map[case_id], pipeline_name, metric_name)
                            is not None
                        },
                        pipeline_name,
                        metric_name,
                    )) is not None
                ]
                metrics[metric_name] = metric_statistics(values, metric_case_ids)
            pipeline_statistics[pipeline_name] = {
                "runs_with_scores": sum(
                    any(
                        case_metric(case, pipeline_name, metric_name) is not None
                        for case in case_map.values()
                        for metric_name in metric_names
                    )
                    for case_map in case_maps
                ),
                "stable_case_count": len(stable_case_ids),
                "stable_case_ids": sorted(stable_case_ids),
                "runs_with_failures": sum(
                    (report.pipeline_case_counts.get(pipeline_name) or {}).get("failed", 0) > 0
                    for report in reports
                ),
                "rejected_cases": sum(
                    (report.pipeline_case_counts.get(pipeline_name) or {}).get("rejected", 0)
                    for report in reports
                ),
                "failed_cases": sum(
                    (report.pipeline_case_counts.get(pipeline_name) or {}).get("failed", 0)
                    for report in reports
                ),
                "metrics": metrics,
            }

        savings_maps = []
        for report in reports:
            comparison = report.paired_pipeline_comparisons.get(
                "compiler_vs_clarification_without_obligation_planning", {}
            )
            accepted = set(comparison.get("case_ids") or [])
            savings_maps.append(
                {
                    str(case.get("case_id")): case
                    for case in report.cases
                    if case.get("case_id")
                    and str(case.get("case_id")) in accepted
                }
            )
        stable_savings_case_ids = {
            case_id
            for case_id in common_ids(savings_maps)
            if all(
                case_metric(case_map[case_id], "compiler", "average_clarification_count")
                is not None
                and case_metric(
                    case_map[case_id],
                    "clarification_without_obligation_planning",
                    "average_clarification_count",
                ) is not None
                for case_map in savings_maps
            )
        }
        repeated_savings = []
        for case_map in savings_maps:
            case_differences = []
            for case_id in stable_savings_case_ids:
                case = case_map[case_id]
                compiler_count = case_metric(case, "compiler", "average_clarification_count")
                baseline_count = case_metric(
                    case,
                    "clarification_without_obligation_planning",
                    "average_clarification_count",
                )
                if compiler_count is not None and baseline_count is not None:
                    case_differences.append(baseline_count - compiler_count)
            if case_differences:
                repeated_savings.append(statistics.fmean(case_differences))
        clarification_savings_statistics = metric_statistics(
            repeated_savings, stable_savings_case_ids
        )

        paired_pipeline_statistics = {}
        comparison_keys = sorted({
            key
            for report in reports
            for key in report.paired_pipeline_comparisons
        })
        for comparison_key in comparison_keys:
            report_observations = [
                (
                    report,
                    report.paired_pipeline_comparisons.get(
                        comparison_key,
                        {
                            "left_pipeline": comparison_key.split("_vs_", 1)[0],
                            "right_pipeline": comparison_key.split("_vs_", 1)[-1],
                            "paired_case_count": 0,
                            "case_ids": [],
                        },
                    ),
                )
                for report in reports
            ]
            observations = [observation for _, observation in report_observations]
            comparison_case_maps = [
                {
                    str(case.get("case_id")): case
                    for case in report.cases
                    if case.get("case_id")
                    and str(case.get("case_id")) in set(observation.get("case_ids") or [])
                }
                for report, observation in report_observations
            ]
            stable_comparison_case_ids = common_ids(comparison_case_maps)
            entry = {
                "left_pipeline": observations[0]["left_pipeline"],
                "right_pipeline": observations[0]["right_pipeline"],
                "observed_runs": len(reports) if stable_comparison_case_ids else 0,
                "requested_runs": len(observations),
                "stable_case_count": len(stable_comparison_case_ids),
                "stable_case_ids": sorted(stable_comparison_case_ids),
                "mean_paired_case_count": round(
                    statistics.fmean(
                        item["paired_case_count"]
                        for item in observations
                        if item.get("paired_case_count", 0) > 0
                    ),
                    4,
                ) if any(item.get("paired_case_count", 0) > 0 for item in observations) else None,
            }
            for side, pipeline_name in (
                ("left_metrics", entry["left_pipeline"]),
                ("right_metrics", entry["right_pipeline"]),
            ):
                entry[side] = {}
                for metric_name in metric_names:
                    metric_case_ids = {
                        case_id
                        for case_id in stable_comparison_case_ids
                        if all(
                            case_metric(case_map[case_id], pipeline_name, metric_name)
                            is not None
                            for case_map in comparison_case_maps
                        )
                    }
                    values = [
                        value
                        for case_map in comparison_case_maps
                        if (value := run_metric_values(
                            case_map,
                            metric_case_ids,
                            pipeline_name,
                            metric_name,
                        )) is not None
                    ]
                    entry[side][metric_name] = metric_statistics(
                        values, metric_case_ids
                    ).model_dump(mode="json")
            paired_pipeline_statistics[comparison_key] = entry

        completed = sum(report.execution_status == "COMPLETE" for report in reports)
        return TestabilityBenchmarkRepeatedReport(
            dataset_id=dataset_id,
            requested_repetitions=repetitions,
            completed_repetitions=completed,
            partial_repetitions=len(reports) - completed,
            failed_repetitions=len(repetition_failures),
            run_ids=[report.run_id for report in reports if report.run_id],
            repetition_failures=repetition_failures,
            pipeline_statistics=pipeline_statistics,
            paired_pipeline_statistics=paired_pipeline_statistics,
            clarification_savings_vs_baseline=clarification_savings_statistics,
            execution_status=(
                "COMPLETE"
                if completed == repetitions and not repetition_failures
                else "PARTIAL"
            ),
        )


testability_benchmark = TestabilityBenchmarkService()

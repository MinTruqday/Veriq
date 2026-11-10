import json

from src.schemas.evaluation import TestabilityBenchmarkGoldCase
from src.schemas.inference_requests import TestingAutomationRequest, TestingEvidence
from src.services.ai_automation import generate_ai_automation
from src.services.automation_provenance import source_quote_spans


class TestabilityBenchmarkSemanticScoring:
    """Compare Blueprint obligation meaning with human-authored semantic labels."""

    async def evaluate_blueprint_semantics(
        self, dataset_id, gold_case, before_blueprint, after_blueprint, source_evidence
    ):
        if not gold_case.expected_obligation_meanings:
            return {
                "status": "NOT_AVAILABLE",
                "reason": "HUMAN_AUTHORED_OBLIGATION_MEANINGS_REQUIRED",
                "evaluator": "MODEL_JUDGE",
            }

        expected = gold_case.expected_obligation_meanings
        source_text_by_ref = {
            str(item.get("artifact_version_id") or item.get("artifact_id")): str(
                item.get("text") or ""
            )
            for item in source_evidence
        }
        candidates = {
            "BEFORE_SELF_REVIEW": self._blueprint_predictions(
                before_blueprint, source_text_by_ref
            ),
            "AFTER_SELF_REVIEW": self._blueprint_predictions(
                after_blueprint, source_text_by_ref
            ),
        }
        total_predictions = sum(len(items) for items in candidates.values())
        if not total_predictions:
            return {
                "status": "SCORED",
                "evaluator": "MODEL_JUDGE",
                "expected_obligation_count": len(expected),
                "before_self_review": self._metrics(expected, []),
                "after_self_review": self._metrics(expected, []),
                "matches": [],
                "warnings": ["NO_BLUEPRINT_OBLIGATIONS_TO_COMPARE"],
            }

        instruction = json.dumps(
            {
                "task_instruction": gold_case.task_instruction,
                "expected_obligations": [
                    {"key": key, "meaning": meaning}
                    for key, meaning in expected.items()
                ],
                "candidate_obligations": candidates,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        request = TestingAutomationRequest(
            capability="testability_benchmark_semantic_evaluation",
            project_id=f"benchmark:{dataset_id}",
            instruction=instruction,
            evidence=[TestingEvidence.model_validate(item) for item in source_evidence],
        )
        result = await generate_ai_automation(request)
        if result.status != "SUCCESS" or result.degraded_mode:
            return {
                "status": "NOT_AVAILABLE",
                "reason": "SEMANTIC_EVALUATOR_UNAVAILABLE",
                "reason_codes": result.reason_codes,
                "evaluator": "MODEL_JUDGE",
            }

        raw_matches = result.semantic_matches
        expected_indices = {
            (candidate_name, index)
            for candidate_name, predictions in candidates.items()
            for index in range(len(predictions))
        }
        returned_indices = [
            (item.get("candidate"), item.get("prediction_index"))
            for item in raw_matches
        ]
        if (
            len(returned_indices) != len(set(returned_indices))
            or set(returned_indices) != expected_indices
        ):
            return {
                "status": "NOT_AVAILABLE",
                "reason": "SEMANTIC_EVALUATOR_OUTPUT_INCOMPLETE",
                "evaluator": "MODEL_JUDGE",
            }

        validated = {name: [] for name in candidates}
        for item in raw_matches:
            candidate_name = item["candidate"]
            key = item.get("expected_obligation_key")
            judgment = item.get("judgment")
            if judgment == "MATCH":
                if key not in expected or any(
                    existing.get("expected_obligation_key") == key
                    and existing.get("judgment") == "MATCH"
                    for existing in validated[candidate_name]
                ):
                    return {
                        "status": "NOT_AVAILABLE",
                        "reason": "SEMANTIC_EVALUATOR_MATCH_INVALID",
                        "evaluator": "MODEL_JUDGE",
                    }
            elif key is not None:
                return {
                    "status": "NOT_AVAILABLE",
                    "reason": "SEMANTIC_EVALUATOR_NON_MATCH_HAS_KEY",
                    "evaluator": "MODEL_JUDGE",
                }
            validated[candidate_name].append(item)

        return {
            "status": "SCORED",
            "evaluator": "MODEL_JUDGE",
            "evaluator_model": result.model,
            "expected_obligation_count": len(expected),
            "before_self_review": self._metrics(
                expected, validated["BEFORE_SELF_REVIEW"]
            ),
            "after_self_review": self._metrics(
                expected, validated["AFTER_SELF_REVIEW"]
            ),
            "matches": raw_matches,
            "warnings": list(result.warnings),
            "interpretation": (
                "Đánh giá ngữ nghĩa do mô hình giám khảo ước lượng trên mô tả nghĩa vụ do người biên soạn nhập; "
                "không phải xác minh độc lập và cần được diễn giải cùng nguồn dẫn, nhãn tham chiếu và giới hạn của giám khảo."
            ),
        }

    @staticmethod
    def _blueprint_predictions(blueprint, source_text_by_ref):
        output = []
        for item in (blueprint or {}).get("obligations", []):
            text = str(item.get("obligation") or "").strip()
            quote = str(item.get("source_quote") or "").strip()
            source_ref = str(item.get("source_ref") or "").strip()
            if text and quote and source_ref:
                output.append(
                    {
                        "text": text,
                        "source_ref": source_ref,
                        "source_quote": quote,
                        "source_quote_valid": bool(
                            source_ref in source_text_by_ref
                            and source_quote_spans(source_text_by_ref[source_ref], quote)
                        ),
                    }
                )
        return output

    @staticmethod
    def _metrics(expected, reviews):
        matched = [
            item
            for item in reviews
            if item.get("judgment") == "MATCH" and item.get("expected_obligation_key")
        ]
        matched_keys = {item["expected_obligation_key"] for item in matched}
        prediction_count = len(reviews)
        expected_count = len(expected)
        precision = len(matched) / prediction_count if prediction_count else 0.0
        recall = len(matched_keys) / expected_count if expected_count else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if recall is not None and precision + recall
            else 0.0 if recall is not None else None
        )
        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4) if recall is not None else None,
            "f1": round(f1, 4) if f1 is not None else None,
            "matched_obligation_keys": sorted(matched_keys),
            "missing_obligation_keys": sorted(set(expected) - matched_keys),
            "uncertain_prediction_count": sum(
                item.get("judgment") == "UNCERTAIN" for item in reviews
            ),
            "prediction_count": prediction_count,
        }

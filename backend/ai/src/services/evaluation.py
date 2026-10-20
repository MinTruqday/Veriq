import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from loguru import logger

from src.schemas.evaluation import TestabilityBenchmarkRequest, TestabilityBenchmarkReport


@dataclass
class EvaluationReport:
    query: str
    expected: str
    actual: str
    retrieval_precision: float = 0.0
    generation_faithfulness: float = 0.0
    answer_relevance: float = 0.0
    bleu: float = 0.0
    rouge_l: float = 0.0
    judge_scores: Optional[dict] = None
    overall_score: float = 0.0


def _compute_bleu(reference: str, hypothesis: str, max_n: int = 4) -> float:
    ref_tokens = reference.lower().split()
    hyp_tokens = hypothesis.lower().split()
    if not ref_tokens or not hyp_tokens:
        return 0.0
    brevity_penalty = min(1.0, math.exp(1 - len(ref_tokens) / max(len(hyp_tokens), 1)))
    precisions = []
    for n in range(1, max_n + 1):
        ref_ngrams = Counter(tuple(ref_tokens[i : i + n]) for i in range(len(ref_tokens) - n + 1))
        hyp_ngrams = Counter(tuple(hyp_tokens[i : i + n]) for i in range(len(hyp_tokens) - n + 1))
        clipped = sum(min(hyp_ngrams[ng], ref_ngrams[ng]) for ng in hyp_ngrams)
        total = max(sum(hyp_ngrams.values()), 1)
        precisions.append(clipped / total)
    if any(p == 0 for p in precisions):
        return 0.0
    log_avg = sum(math.log(p) for p in precisions) / len(precisions)
    return brevity_penalty * math.exp(log_avg)


def _compute_rouge_l(reference: str, hypothesis: str) -> float:
    ref_tokens = reference.lower().split()
    hyp_tokens = hypothesis.lower().split()
    if not ref_tokens or not hyp_tokens:
        return 0.0
    m, n = len(ref_tokens), len(hyp_tokens)
    lcs_table = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref_tokens[i - 1] == hyp_tokens[j - 1]:
                lcs_table[i][j] = lcs_table[i - 1][j - 1] + 1
            else:
                lcs_table[i][j] = max(lcs_table[i - 1][j], lcs_table[i][j - 1])
    lcs_len = lcs_table[m][n]
    precision = lcs_len / n if n > 0 else 0.0
    recall = lcs_len / m if m > 0 else 0.0
    if precision + recall == 0.0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


async def _llm_judge(instruction: str, expected: str, actual: str) -> dict:
    from langchain_core.messages import HumanMessage, SystemMessage

    from src.prompts.evaluation import eval_judge
    from src.schemas.evaluation import JudgeScores
    from src.utils.huggingface import create_chat_model

    prompt = eval_judge(instruction, expected, actual)
    try:
        evaluator = create_chat_model().with_structured_output(JudgeScores)
        scores = await evaluator.ainvoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content="Produce the required evaluation result"),
            ],
            max_tokens=256,
            temperature=0.1,
        )
        return scores.model_dump()
    except Exception:
        logger.exception("Language model output evaluation error")
        return {
            "accuracy": 0,
            "completeness": 0,
            "relevance": 0,
            "explanation": "The evaluation process failed to complete successfully due to an internal system exception",
        }


class EvaluationHarness:
    def __init__(self):
        self._reports: list[EvaluationReport] = []
        self._dataset: list[dict] = []

    def load_dataset(self, dataset_path: str):
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                self._dataset = json.load(f)
            logger.info("Test dataset loaded")
        except Exception:
            logger.exception("Test dataset loading error")
            self._dataset = []

    async def evaluate_knowledge_response(
        self,
        query: str,
        expected_answer: str,
        actual_answer: str,
        contexts: list[str],
        use_judge: bool = False,
    ) -> EvaluationReport:
        retrieval_precision = 0.0
        if contexts and expected_answer:
            expected_tokens = set(expected_answer.casefold().split())
            if expected_tokens:
                matched = sum(
                    1 for ctx in contexts if expected_tokens & set(ctx.casefold().split())
                )
                retrieval_precision = min(matched / len(contexts), 1.0)

        bleu = round(_compute_bleu(expected_answer, actual_answer), 4)
        rouge = round(_compute_rouge_l(expected_answer, actual_answer), 4)

        gen_faithfulness = min((bleu + rouge) / 2 + retrieval_precision * 0.2, 1.0)
        answer_relevance = min(rouge * 0.6 + bleu * 0.4 + 0.1, 1.0)

        judge_scores = None
        if use_judge:
            judge_scores = await _llm_judge(query, expected_answer, actual_answer)

        if judge_scores:
            judge_avg = (
                judge_scores["accuracy"] + judge_scores["completeness"] + judge_scores["relevance"]
            ) / 30
            overall = (retrieval_precision + gen_faithfulness + answer_relevance + judge_avg) / 4
        else:
            overall = (retrieval_precision + gen_faithfulness + answer_relevance) / 3

        report = EvaluationReport(
            query=query,
            expected=expected_answer,
            actual=actual_answer,
            retrieval_precision=round(retrieval_precision, 4),
            generation_faithfulness=round(gen_faithfulness, 4),
            answer_relevance=round(answer_relevance, 4),
            bleu=bleu,
            rouge_l=rouge,
            judge_scores=judge_scores,
            overall_score=round(overall, 4),
        )
        self._reports.append(report)
        logger.info("Information retrieval evaluation complete")
        return report

    async def run_benchmark(self, model_name: str, use_judge: bool = False) -> dict:
        from src.utils.model_provider import model_client

        if not self._dataset:
            return {"error_code": "evaluation_dataset_not_loaded"}

        try:
            client = model_client
        except Exception:
            logger.exception("Evaluation client initialization failed")
            return {"error_code": "evaluation_client_initialization_failed"}

        results = []
        for sample in self._dataset:
            instruction = sample.get("instruction", "")
            inp = sample.get("input", "")
            expected = sample.get("output", "")
            from src.prompts.evaluation import evaluation_harness_prompt

            prompt = evaluation_harness_prompt(instruction, inp).strip()
            try:
                resp = await client.chat_completion(
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": "Produce the requested benchmark response"},
                    ],
                    max_tokens=512,
                    temperature=0.1,
                )
                actual = resp.choices[0].message.content.strip()
            except Exception:
                results.append(
                    {
                        "instruction": instruction,
                        "expected": expected,
                        "actual": "The system encountered an unexpected error during the model evaluation execution",
                        "bleu": 0.0,
                        "rouge_l": 0.0,
                        "judge_scores": None,
                    }
                )
                continue

            bleu = round(_compute_bleu(expected, actual), 4)
            rouge = round(_compute_rouge_l(expected, actual), 4)
            judge_scores = None
            if use_judge:
                judge_scores = await _llm_judge(instruction, expected, actual)

            results.append(
                {
                    "instruction": instruction,
                    "input": inp,
                    "expected": expected,
                    "actual": actual,
                    "bleu": bleu,
                    "rouge_l": rouge,
                    "judge_scores": judge_scores,
                }
            )

        valid = [r for r in results if isinstance(r["bleu"], float)]
        avg_bleu = round(sum(r["bleu"] for r in valid) / max(len(valid), 1), 4)
        avg_rouge = round(sum(r["rouge_l"] for r in valid) / max(len(valid), 1), 4)

        judge_results = [r["judge_scores"] for r in valid if r.get("judge_scores")]
        avg_judge = None
        if judge_results:
            avg_judge = {
                "accuracy": round(
                    sum(j["accuracy"] for j in judge_results) / len(judge_results), 2
                ),
                "completeness": round(
                    sum(j["completeness"] for j in judge_results) / len(judge_results), 2
                ),
                "relevance": round(
                    sum(j["relevance"] for j in judge_results) / len(judge_results), 2
                ),
            }

        summary = {
            "model": model_name,
            "total_samples": len(results),
            "average_bleu": avg_bleu,
            "average_rouge_l": avg_rouge,
            "average_judge_scores": avg_judge,
            "results": results,
        }
        logger.info("AI model evaluation complete")
        return summary

    async def evaluate_testability_compiler(
        self, request: TestabilityBenchmarkRequest
    ) -> TestabilityBenchmarkReport:
        from src.services.testability_benchmark import testability_benchmark

        return await testability_benchmark.evaluate(request)

    def get_dashboard_metrics(self) -> dict:
        if not self._reports:
            return {
                "status": "The system currently has no recorded evaluation to generate the dashboard metrics",
                "total_evaluations": 0,
            }
        count = len(self._reports)
        return {
            "total_evaluations": count,
            "average_metrics": {
                "retrieval_precision": round(
                    sum(r.retrieval_precision for r in self._reports) / count, 4
                ),
                "generation_faithfulness": round(
                    sum(r.generation_faithfulness for r in self._reports) / count, 4
                ),
                "answer_relevance": round(
                    sum(r.answer_relevance for r in self._reports) / count, 4
                ),
                "bleu": round(sum(r.bleu for r in self._reports) / count, 4),
                "rouge_l": round(sum(r.rouge_l for r in self._reports) / count, 4),
                "overall_score": round(sum(r.overall_score for r in self._reports) / count, 4),
            },
            "status": "The evaluation metrics dashboard is ready and available for viewing",
        }


evaluation = EvaluationHarness()

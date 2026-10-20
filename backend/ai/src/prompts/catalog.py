"""Compatibility exports for prompts grouped by security, retrieval, and evaluation."""

from src.prompts.evaluation import eval_judge, evaluation_harness_prompt
from src.prompts.retrieval import cross_document_query, document_global_summary
from src.prompts.security import prompt_injection_detector, security_scan

__all__ = [
    "cross_document_query",
    "document_global_summary",
    "eval_judge",
    "evaluation_harness_prompt",
    "prompt_injection_detector",
    "security_scan",
]

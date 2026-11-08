"""Compatibility exports for prompts grouped by security and retrieval."""

from src.prompts.retrieval import cross_document_query, document_global_summary
from src.prompts.security import prompt_injection_detector, security_scan

__all__ = [
    "cross_document_query",
    "document_global_summary",
    "prompt_injection_detector",
    "security_scan",
]

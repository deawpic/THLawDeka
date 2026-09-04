"""
THLawDeka AI Agent Harness v3.0 - Core Engine & Evaluation Testbed
"""

from harness.cache import LegalMcpCache, LegalPayloadDistiller
from harness.verifier import (
    audit_response_for_hallucinations,
    extract_all_deka_numbers,
    extract_all_statute_citations,
    detect_unverified_deka_citations,
    sanitize_hallucinated_deka_numbers,
    detect_absolute_guarantees,
)
from harness.evaluator import LegalBenchmarkEvaluator

__all__ = [
    "LegalMcpCache",
    "LegalPayloadDistiller",
    "audit_response_for_hallucinations",
    "extract_all_deka_numbers",
    "extract_all_statute_citations",
    "detect_unverified_deka_citations",
    "sanitize_hallucinated_deka_numbers",
    "detect_absolute_guarantees",
    "LegalBenchmarkEvaluator",
]

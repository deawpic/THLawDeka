"""
THLawDeka AI Agent Harness v3.0 - Core Engine & Evaluation Testbed
"""

from harness.cache import LegalMcpCache, LegalPayloadDistiller

check_first_run = LegalMcpCache.check_first_run
ensure_cache_file = LegalMcpCache.ensure_cache_file

from harness.verifier import (
    audit_response_for_hallucinations,
    extract_all_deka_numbers,
    extract_all_statute_citations,
    detect_unverified_deka_citations,
    sanitize_hallucinated_deka_numbers,
    detect_absolute_guarantees,
    validate_mermaid_syntax,
    validate_markdown_tables,
    detect_prohibited_ascii,
)
from harness.evaluator import LegalBenchmarkEvaluator

__all__ = [
    "LegalMcpCache",
    "LegalPayloadDistiller",
    "check_first_run",
    "ensure_cache_file",
    "audit_response_for_hallucinations",
    "extract_all_deka_numbers",
    "extract_all_statute_citations",
    "detect_unverified_deka_citations",
    "sanitize_hallucinated_deka_numbers",
    "detect_absolute_guarantees",
    "validate_mermaid_syntax",
    "validate_markdown_tables",
    "detect_prohibited_ascii",
    "LegalBenchmarkEvaluator",
]

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
)
from harness.evaluator import LegalBenchmarkEvaluator

from harness.document import (
    find_system_chromium_binary,
    convert_html_to_thai_pdf,
    convert_markdown_to_thai_pdf,
    safe_run_python_script,
    validate_docx_alignment,
    build_odt_thai_style_properties,
    check_system_environment,
    get_thai_saraban_css,
    markdown_to_thai_html,
)

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
    "LegalBenchmarkEvaluator",
    "find_system_chromium_binary",
    "convert_html_to_thai_pdf",
    "convert_markdown_to_thai_pdf",
    "safe_run_python_script",
    "validate_docx_alignment",
    "build_odt_thai_style_properties",
    "check_system_environment",
    "get_thai_saraban_css",
    "markdown_to_thai_html",
]

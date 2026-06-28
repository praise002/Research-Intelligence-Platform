"""
Output guardrails — fast rule-based checks on the generated report
BEFORE it is delivered to the user. No LLM needed here — just string
checks. These run after the evaluator scores the report.

Two different outcomes:
  - FAIL  → report is blocked, synthesiser retries (up to max loops)
  - WARN  → report is delivered but with a visible warning to the user

Four checks:
  check_minimum_length    → FAIL if under 500 words
  check_source_citations  → FAIL if zero citations found
  check_required_sections → FAIL if SWOT, trends, or summary missing
  check_source_count      → WARN if fewer than 5 sources used
"""

import re

from src.custom_logging import get_logger

log = get_logger(__name__)


MIN_WORD_COUNT = 500
MIN_SOURCE_COUNT = 5

# Required section headers — checked case-insensitively
REQUIRED_SECTIONS = [
    "executive summary",
    "swot",
    "trends",
    "sources",
]

# Citation pattern — matches [1], [2], [12] etc. inline in the report

_CITATION_REGEX = re.compile(r"\[\d+\]")


# Individual guard functions — each returns (passed: bool, message: str)

def check_minimum_length(report: str) -> tuple[bool, str]:
    """
    Counts words in the report. Under 500 words means the synthesiser
    produced an incomplete output — trigger a retry.
    """
    word_count = len(report.split())
    if word_count < MIN_WORD_COUNT:
        msg = f"Report too short: {word_count} words (minimum {MIN_WORD_COUNT})"
        log.warning("guardrail.output.too_short", word_count=word_count)
        return False, msg
    return True, ""


def check_source_citations(report: str) -> tuple[bool, str]:
    """
    Checks for at least one inline citation ([1], [2], etc.).
    Zero citations means the report is making ungrounded claims —
    every competitive intelligence claim must trace back to a source.
    """
    citations = _CITATION_REGEX.findall(report)
    if not citations:
        msg = "Report contains no source citations"
        log.warning("guardrail.output.no_citations")
        return False, msg
    return True, ""


def check_required_sections(report: str) -> tuple[bool, str]:
    """
    Verifies all required sections exist in the report.
    Checks case-insensitively so "## SWOT Analysis" and "## Swot" both pass.
    """
    report_lower = report.lower()
    missing = [
        section for section in REQUIRED_SECTIONS
        if section not in report_lower
    ]
    if missing:
        msg = f"Report missing required sections: {', '.join(missing)}"
        log.warning("guardrail.output.missing_sections", missing=missing)
        return False, msg
    return True, ""


def check_source_count(source_count: int) -> tuple[bool, str]:
    """
    Unlike the other three, this is a WARNING not a FAIL.
    The report still gets delivered — but with a visible notice
    so the user knows to treat it with less confidence.
    Under 5 sources means the research had limited data to work with.
    """
    if source_count < MIN_SOURCE_COUNT:
        msg = (
            f"This report was generated from {source_count} sources "
            f"(recommended minimum: {MIN_SOURCE_COUNT}). "
            "Findings may be incomplete — treat with caution."
        )
        log.info("guardrail.output.low_source_count", source_count=source_count)
        return False, msg
    return True, ""


# Orchestrator

def run_all_output_guards(
    report: str,
    source_count: int,
) -> tuple[bool, list[str]]:
    """
    Runs all four output guards and returns:
      passed   → True if all FAIL-type checks passed (length, citations, sections)
                 False if any FAIL-type check failed → synthesiser should retry
      warnings → list of warning strings to append to the delivered report
                 (low source count warning lives here, not in passed)

    USAGE (in report_formatter node):
        passed, warnings = run_all_output_guards(
            report=state["synthesis_output"],
            source_count=len(state["validated_sources"]),
        )
        if not passed and state["loop_count"] < 3:
            # trigger retry
        elif not passed:
            # max loops reached — deliver with warnings anyway
    """
    warnings: list[str] = []
    failures: list[str] = []

    # FAIL-type checks — block delivery if any fail
    for check_fn in [check_minimum_length, check_source_citations, check_required_sections]:
        passed, message = check_fn(report)
        if not passed:
            failures.append(message)

    # WARN-type check — never blocks delivery
    count_ok, count_message = check_source_count(source_count)
    if not count_ok:
        warnings.append(count_message)

    if failures:
        log.warning(
            "guardrail.output.failed",
            failures=failures,
            warning_count=len(warnings),
        )
        return False, warnings

    log.info(
        "guardrail.output.passed",
        source_count=source_count,
        warning_count=len(warnings),
    )
    return True, warnings
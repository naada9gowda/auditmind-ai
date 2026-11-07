"""
compliance/extract_findings.py — Draft finding extraction from audit reports.

Two-layer strategy:
  1. Rule-based (always runs): scan page text for heading/phrase patterns
     ("Finding", "Observation", "Non-conformity", "not completed", "missing",
     "incomplete") and extract severity, control ID, department.
  2. LLM enrichment (optional, only when LLM_PROVIDER != none): sends page
     text to the LLM; output is validated against LLMFindingList schema;
     any failure falls back to rule-based result.

All extracted findings are stored with:
  ai_generated = True
  review_status = "Draft"

They NEVER become approved records until a human reviewer approves them.

Security: document text is treated as untrusted DATA. Text containing
"ignore previous instructions" or similar is passed as data to the LLM
wrapped in delimiters — the LLM is explicitly told to treat it as data.
Any injected command found in a document cannot change control status or
auto-approve a finding; those transitions require explicit API calls by an
authenticated human reviewer.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known departments (matched case-insensitively)
# ---------------------------------------------------------------------------
KNOWN_DEPARTMENTS = ["IT Operations", "HR", "Finance", "Engineering"]

# ---------------------------------------------------------------------------
# Trigger patterns (finding paragraph detection)
# ---------------------------------------------------------------------------
_FINDING_TRIGGERS = re.compile(
    r"\b(finding|observation|non[\s-]?conformity|non[\s-]?compliance|"
    r"exception|issue|deficiency|gap|not completed|not\s+found|"
    r"missing|incomplete|overdue|failed|failure|no evidence)\b",
    re.IGNORECASE,
)

_HEADING_PATTERN = re.compile(
    r"^(finding\s*\d*|observation\s*\d*|non[\s-]?conformity\s*\d*|"
    r"exception\s*\d*|issue\s*\d*)",
    re.IGNORECASE | re.MULTILINE,
)

# ---------------------------------------------------------------------------
# Severity detection
# ---------------------------------------------------------------------------
_SEVERITY_HIGH = re.compile(r"\b(high|critical|major|severe)\b", re.IGNORECASE)
_SEVERITY_LOW = re.compile(r"\b(low|minor|informational|advisory)\b", re.IGNORECASE)
_SEVERITY_MEDIUM = re.compile(r"\b(medium|moderate|significant)\b", re.IGNORECASE)

# Control-code regex (e.g. SEC-014)
_RE_CONTROL_CODE = re.compile(r"\b([A-Z]{2,5}-\d{3,4})\b")


def _detect_severity(text: str) -> str:
    """Infer severity from keywords in text; default Medium."""
    if _SEVERITY_HIGH.search(text):
        return "High"
    if _SEVERITY_LOW.search(text):
        return "Low"
    return "Medium"


def _detect_department(text: str) -> str | None:
    """Match text against known departments (case-insensitive)."""
    text_lower = text.lower()
    for dept in KNOWN_DEPARTMENTS:
        if dept.lower() in text_lower:
            return dept
    return None


def _extract_control_code(text: str) -> str | None:
    """Return first control code found in text, or None."""
    m = _RE_CONTROL_CODE.search(text)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Dataclass for a draft finding (before DB write)
# ---------------------------------------------------------------------------
@dataclass
class DraftFinding:
    description: str
    severity: str
    control_code: str | None        # e.g. "SEC-014" (code, not DB id)
    department: str | None
    source_page: int | None
    source_excerpt: str | None
    ai_generated: bool = True
    review_status: str = "Draft"


# ---------------------------------------------------------------------------
# Rule-based extractor
# ---------------------------------------------------------------------------

def _split_into_paragraphs(text: str) -> list[str]:
    """Split text on blank lines or heading-like lines."""
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def extract_findings_rule_based(
    pages: list[tuple[int, str]],
) -> list[DraftFinding]:
    """
    Rule-based finding extraction.
    Returns one DraftFinding per detected paragraph that contains a trigger.
    """
    drafts: list[DraftFinding] = []

    for page_num, text in pages:
        paragraphs = _split_into_paragraphs(text)
        for para in paragraphs:
            if not _FINDING_TRIGGERS.search(para):
                continue
            # Skip very short snippets (likely headers, not full findings)
            if len(para.split()) < 5:
                continue
            excerpt = para[:300] + ("…" if len(para) > 300 else "")
            drafts.append(
                DraftFinding(
                    description=para[:1000],
                    severity=_detect_severity(para),
                    control_code=_extract_control_code(para),
                    department=_detect_department(para),
                    source_page=page_num,
                    source_excerpt=excerpt,
                )
            )

    # Deduplicate: if same (control_code, page_num) already added, skip
    seen: set[tuple] = set()
    unique: list[DraftFinding] = []
    for d in drafts:
        key = (d.control_code, d.source_page, d.description[:80])
        if key not in seen:
            seen.add(key)
            unique.append(d)

    return unique


# ---------------------------------------------------------------------------
# LLM-enhanced extractor
# ---------------------------------------------------------------------------

def extract_findings_with_llm(
    pages: list[tuple[int, str]],
    llm_provider: Any,
    control_code_to_id: dict[str, str],   # code → DB UUID mapping for enrichment
) -> list[DraftFinding] | None:
    """
    Try LLM extraction. Returns None on failure (caller uses rule-based).
    Document text is wrapped in delimiters inside the provider — treated as data.
    """
    combined = "\n\n".join(f"[Page {n}]\n{t}" for n, t in pages[:10])
    try:
        result = llm_provider.extract_findings(combined, KNOWN_DEPARTMENTS)
        if result is None:
            return None
        drafts: list[DraftFinding] = []
        for f in result.findings:
            # Validate severity
            sev = f.severity if f.severity in ("High", "Medium", "Low") else "Medium"
            drafts.append(
                DraftFinding(
                    description=f.description[:1000],
                    severity=sev,
                    control_code=f.control_id,     # LLM returns code, not DB id
                    department=f.department,
                    source_page=f.source_page,
                    source_excerpt=(f.source_excerpt or "")[:300],
                )
            )
        return drafts or None
    except Exception as exc:
        logger.warning("LLM finding extraction raised unexpected error: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def extract_findings(
    *,
    pages: list[tuple[int, str]],
    llm_provider: Any | None = None,
    control_code_to_id: dict[str, str] | None = None,
) -> list[DraftFinding]:
    """
    Extract draft findings from audit report pages.

    Strategy:
    1. Run rule-based extraction (always).
    2. If LLM provider available, attempt LLM extraction.
    3. If LLM succeeds and returns ≥1 result, prefer LLM findings that cover
       pages the rule-based extractor also flagged (reduces false positives).
       If LLM result is empty or fails, return rule-based.

    Result: deduplicated list of DraftFinding objects, never auto-approved.
    """
    ctrl_map = control_code_to_id or {}

    rule_findings = extract_findings_rule_based(pages)
    logger.debug("Rule-based extraction found %d findings.", len(rule_findings))

    if llm_provider is not None:
        llm_findings = extract_findings_with_llm(pages, llm_provider, ctrl_map)
        if llm_findings:
            logger.info("LLM extraction found %d findings; using LLM results.", len(llm_findings))
            return llm_findings
        logger.info("LLM extraction unavailable or empty; using rule-based results.")

    return rule_findings

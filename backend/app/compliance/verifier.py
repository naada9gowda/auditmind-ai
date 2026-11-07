"""
compliance/verifier.py — Deterministic evidence assessment engine.

Checks each piece of evidence (a document mapped to a control) against:
  1. Date freshness: document date vs. control cadence window → Expired
  2. Required-field checks: per-control evidence_expectation → Incomplete
  3. Confidence threshold: low-confidence mapping → Requires Human Review
  4. Missing evidence: no document for a control → Missing
  5. Otherwise → Candidate Match

Returns a VerificationResult with assessment, reasons, and source info.

Design rules:
- All logic is deterministic (no model calls here).
- Never auto-sets control status to Compliant.
- Returns the source document, page number and excerpt with every result.
- Document text is treated as untrusted DATA — never interpreted as instructions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.compliance.mapping import CADENCE_DAYS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Assessment labels (mirror model constants)
# ---------------------------------------------------------------------------
ASSESSMENT_CANDIDATE_MATCH = "Candidate Match"
ASSESSMENT_MISSING = "Missing"
ASSESSMENT_EXPIRED = "Expired"
ASSESSMENT_INCOMPLETE = "Incomplete"
ASSESSMENT_HUMAN_REVIEW = "Requires Human Review"

# Confidence threshold below which we escalate to human review
_LOW_CONFIDENCE_THRESHOLD = 0.25


# ---------------------------------------------------------------------------
# Per-control required-field rules
# Format: control_code → list of (label, regex_patterns)
# A field is considered PRESENT if ANY of its patterns matches the page text.
# ---------------------------------------------------------------------------
_REQUIRED_FIELDS: dict[str, list[tuple[str, list[str]]]] = {
    "SEC-014": [
        (
            "reviewer name",
            [r"\b(reviewed\s+by|reviewer|conducted\s+by|prepared\s+by)\s*[:\-]?\s*\w"],
        ),
        (
            "review date",
            [
                # Must have an explicit label — bare ISO date alone does not satisfy this field
                r"\b(review\s+date|date\s+of\s+review|reviewed\s+on|completed\s+on)\b",
            ],
        ),
        (
            "approval or sign-off",
            [
                r"\b(approved\s+by|sign[\s-]?off|authoris(ed|ed)\s+by|"
                r"approval|manager\s+approval|signoff|signed\s+off)\b"
            ],
        ),
    ],
    "SEC-005": [
        ("backup test date", [r"\b(test\s+date|tested\s+on|backup\s+test)\b"]),
        ("result or outcome", [r"\b(result|outcome|pass|fail|success|failure)\b"]),
    ],
}


@dataclass
class VerificationResult:
    """Result of verifying one document-to-control mapping."""
    control_id: str
    control_code: str
    document_id: str | None
    assessment: str                      # Candidate Match | Expired | Incomplete | Requires Human Review | Missing
    reasons: list[str] = field(default_factory=list)
    page_number: int | None = None
    excerpt: str | None = None
    evidence_date: date | None = None


def verify_evidence(
    *,
    control: Any,                        # Control ORM object
    document: Any | None,               # Document ORM object (or None → Missing)
    page_number: int | None = None,
    excerpt: str | None = None,
    page_text: str | None = None,       # text of the evidence page, for field checks
    confidence: float = 1.0,
    as_of_date: date | None = None,     # defaults to today
) -> VerificationResult:
    """
    Run all deterministic checks for one (control, document) pair.

    Priority (first match wins):
      1. No document → Missing
      2. Low confidence mapping → Requires Human Review
      3. Document date expired → Expired
      4. Required fields missing → Incomplete
      5. → Candidate Match
    """
    as_of = as_of_date or date.today()
    code = control.control_code

    # --- 1. Missing ---
    if document is None:
        return VerificationResult(
            control_id=control.id,
            control_code=code,
            document_id=None,
            assessment=ASSESSMENT_MISSING,
            reasons=["No evidence document is mapped to this control."],
        )

    doc_date: date | None = getattr(document, "extracted_date", None)

    # --- 2. Low confidence ---
    if confidence < _LOW_CONFIDENCE_THRESHOLD:
        return VerificationResult(
            control_id=control.id,
            control_code=code,
            document_id=document.id,
            assessment=ASSESSMENT_HUMAN_REVIEW,
            reasons=[
                f"Mapping confidence ({confidence:.0%}) is below threshold "
                f"({_LOW_CONFIDENCE_THRESHOLD:.0%}). Human review required."
            ],
            page_number=page_number,
            excerpt=excerpt,
            evidence_date=doc_date,
        )

    # --- 3. Expiry check ---
    cadence_str = (control.cadence or "").lower().strip()
    cadence_days = CADENCE_DAYS.get(cadence_str)
    if cadence_days and doc_date:
        cutoff = as_of - timedelta(days=cadence_days)
        if doc_date < cutoff:
            return VerificationResult(
                control_id=control.id,
                control_code=code,
                document_id=document.id,
                assessment=ASSESSMENT_EXPIRED,
                reasons=[
                    f"Evidence date {doc_date} is older than the {cadence_str} "
                    f"cadence window ({cadence_days} days). "
                    f"Cutoff was {cutoff} (as of {as_of})."
                ],
                page_number=page_number,
                excerpt=excerpt,
                evidence_date=doc_date,
            )

    # --- 4. Required-field checks ---
    if page_text and code in _REQUIRED_FIELDS:
        text_lower = page_text.lower()
        missing_fields: list[str] = []
        for field_label, patterns in _REQUIRED_FIELDS[code]:
            found = any(
                re.search(pat, text_lower, re.IGNORECASE)
                for pat in patterns
            )
            if not found:
                missing_fields.append(field_label)
        if missing_fields:
            return VerificationResult(
                control_id=control.id,
                control_code=code,
                document_id=document.id,
                assessment=ASSESSMENT_INCOMPLETE,
                reasons=[
                    f"Required evidence field(s) not found: {', '.join(missing_fields)}. "
                    f"Evidence expectation: {control.evidence_expectation or 'not specified'}."
                ],
                page_number=page_number,
                excerpt=excerpt,
                evidence_date=doc_date,
            )

    # --- 5. Candidate Match ---
    return VerificationResult(
        control_id=control.id,
        control_code=code,
        document_id=document.id,
        assessment=ASSESSMENT_CANDIDATE_MATCH,
        reasons=[
            f"Document appears to satisfy control requirements "
            f"(confidence {confidence:.0%})."
        ],
        page_number=page_number,
        excerpt=excerpt,
        evidence_date=doc_date,
    )


def assess_missing_controls(
    *,
    all_controls: list[Any],
    mapped_control_ids: set[str],
) -> list[VerificationResult]:
    """
    For every control NOT covered by any document, return a Missing result.
    Called after mapping to flag gaps.
    """
    results: list[VerificationResult] = []
    for ctrl in all_controls:
        if ctrl.id not in mapped_control_ids:
            results.append(
                VerificationResult(
                    control_id=ctrl.id,
                    control_code=ctrl.control_code,
                    document_id=None,
                    assessment=ASSESSMENT_MISSING,
                    reasons=["No evidence document is mapped to this control."],
                )
            )
    return results

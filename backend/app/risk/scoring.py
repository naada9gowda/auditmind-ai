"""
risk/scoring.py — Deterministic prioritisation scoring for audit findings.

Generates early-warning risk indicators for compliance prioritisation.
NOTE: These are risk indicators/early-warning signals, NOT predictions.
Disclaimer is always attached to all results.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.related_finding import RelatedFinding
from app.models.remediation import RemediationAction
from app.risk.config import (
    DISCLAIMER,
    EVIDENCE_INCOMPLETE,
    EVIDENCE_MISSING_EXPIRED,
    HIGH_THRESHOLD,
    MEDIUM_THRESHOLD,
    OVERDUE_PARTIAL,
    OVERDUE_SEVERE,
    RECURRENCE_MAX,
    SEVERITY_SCORES,
)


def score_finding(finding: Finding, db: Session, organisation_id: str) -> dict[str, Any]:
    """
    Score a single finding based on severity, recurrence, overdue remediations,
    and evidence weakness. All queries are strictly scoped to organisation_id.
    """
    # 1. Severity component
    sev_pts = float(SEVERITY_SCORES.get(finding.severity, 0))
    sev_reason = f"Finding is {finding.severity} severity ({int(sev_pts)} pts)."

    # 2. Recurrence component
    # Count confirmed RelatedFinding rows for this finding
    confirmed_rf_count = (
        db.query(RelatedFinding)
        .filter(
            RelatedFinding.organisation_id == organisation_id,
            RelatedFinding.finding_id == finding.id,
            RelatedFinding.reviewed_by.isnot(None),
        )
        .count()
    )

    recurrence_count = 0
    if getattr(finding, "is_recurrence", False):
        recurrence_count = max(1, confirmed_rf_count)
    elif confirmed_rf_count > 0:
        recurrence_count = confirmed_rf_count

    recurrence_pts = float(min(recurrence_count, RECURRENCE_MAX))
    recurrence_reason = f"Has appeared in {recurrence_count} prior audit cycle(s)."

    # 3. Overdue remediation component
    today = date.today()
    actions = (
        db.query(RemediationAction)
        .filter(
            RemediationAction.organisation_id == organisation_id,
            RemediationAction.finding_id == finding.id,
        )
        .all()
    )
    overdue_days_list = [
        (today - a.due_date).days
        for a in actions
        if a.due_date and a.due_date < today and a.status != "Completed"
    ]

    max_days = 0
    if overdue_days_list:
        max_days = max(overdue_days_list)
        if max_days > 30:
            overdue_pts = float(OVERDUE_SEVERE)
            overdue_reason = f"Remediation action is {max_days} days overdue (>30 days)."
        else:
            overdue_pts = float(OVERDUE_PARTIAL)
            overdue_reason = f"Remediation action is {max_days} days overdue."
    else:
        overdue_pts = 0.0
        overdue_reason = "No overdue remediation actions."

    # 4. Evidence weakness component
    evidence_pts = 0.0
    if finding.control_id:
        evidence_items = (
            db.query(Evidence)
            .filter(
                Evidence.organisation_id == organisation_id,
                Evidence.control_id == finding.control_id,
            )
            .all()
        )
        has_missing_or_expired = any(e.assessment in ("Missing", "Expired") for e in evidence_items)
        has_incomplete = any(e.assessment == "Incomplete" for e in evidence_items)
        if has_missing_or_expired:
            evidence_pts = float(EVIDENCE_MISSING_EXPIRED)
            evidence_reason = "Control has missing or expired evidence."
        elif has_incomplete:
            evidence_pts = float(EVIDENCE_INCOMPLETE)
            evidence_reason = "Control has incomplete evidence."
        else:
            evidence_pts = 0.0
            evidence_reason = "Evidence records reviewed; no critical weakness identified."
    else:
        evidence_pts = 0.0
        evidence_reason = "No linked control to assess evidence."

    # Total score capped at 10.0
    total_score = min(10.0, float(sev_pts + recurrence_pts + overdue_pts + evidence_pts))

    # Priority level
    if total_score >= HIGH_THRESHOLD:
        level = "High"
    elif total_score >= MEDIUM_THRESHOLD:
        level = "Medium"
    else:
        level = "Low"

    # Dynamic plain-English explanation
    reasons: list[str] = []
    if finding.severity:
        reasons.append(f"the finding is {finding.severity.lower()} severity")
    if recurrence_count > 0:
        reasons.append(f"has appeared in {recurrence_count} prior audit cycle(s)")
    if overdue_days_list:
        reasons.append(f"the corrective action is {max_days} days overdue")
    if evidence_pts > 0:
        reasons.append("has weak or missing evidence")

    if reasons:
        if len(reasons) == 1:
            reasons_str = reasons[0]
        elif len(reasons) == 2:
            reasons_str = f"{reasons[0]} and {reasons[1]}"
        else:
            reasons_str = f"{', '.join(reasons[:-1])}, and {reasons[-1]}"
        explanation = f"{level} priority because {reasons_str}."
    else:
        explanation = f"{level} priority risk indicator based on current evaluation."

    components = [
        {"name": "severity", "points": sev_pts, "reason": sev_reason},
        {"name": "recurrence", "points": recurrence_pts, "reason": recurrence_reason},
        {"name": "overdue_remediation", "points": overdue_pts, "reason": overdue_reason},
        {"name": "evidence_weakness", "points": evidence_pts, "reason": evidence_reason},
    ]

    return {
        "finding_id": finding.id,
        "score": total_score,
        "level": level,
        "components": components,
        "explanation": explanation,
        "disclaimer": DISCLAIMER,
    }


def score_all_open_findings(db: Session, organisation_id: str) -> list[dict[str, Any]]:
    """
    Score all Open findings in the organisation, sorted descending by risk score.
    """
    open_findings = (
        db.query(Finding)
        .filter(
            Finding.organisation_id == organisation_id,
            Finding.status == "Open",
        )
        .all()
    )
    scored = [score_finding(f, db, organisation_id) for f in open_findings]
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored

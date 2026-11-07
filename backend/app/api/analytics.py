"""
api/analytics.py — Analytics and early-warning risk indicator endpoints.

Provides organisation-scoped aggregated compliance metrics and prioritisation
scores. All endpoints require authentication and strictly scope queries to the
authenticated user's organisation.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import _get_current_user
from app.database import get_db
from app.models.audit_cycle import AuditCycle
from app.models.control import Control
from app.models.finding import Finding
from app.models.related_finding import RelatedFinding
from app.models.remediation import RemediationAction
from app.models.user import User
from app.risk.config import DISCLAIMER
from app.risk.scoring import score_all_open_findings

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/risks", summary="Get early-warning risk indicators for all open findings")
def get_risks(
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> dict[str, Any]:
    """
    Score all Open findings in the user's organisation and return enriched
    prioritisation signals with control and source metadata.
    """
    scored_findings = score_all_open_findings(db, user.organisation_id)

    # Fetch all open findings in this organisation for fast enrichment
    open_findings = (
        db.query(Finding)
        .filter(
            Finding.organisation_id == user.organisation_id,
            Finding.status == "Open",
        )
        .all()
    )
    findings_map = {f.id: f for f in open_findings}

    # Fetch control codes for linked controls
    control_ids = {f.control_id for f in open_findings if f.control_id}
    controls = (
        db.query(Control)
        .filter(
            Control.organisation_id == user.organisation_id,
            Control.id.in_(control_ids),
        )
        .all()
        if control_ids
        else []
    )
    control_code_map = {c.id: c.control_code for c in controls}

    # Fetch related finding IDs for each finding
    all_rf = (
        db.query(RelatedFinding.finding_id, RelatedFinding.related_finding_id)
        .filter(RelatedFinding.organisation_id == user.organisation_id)
        .all()
    )
    related_map: dict[str, list[str]] = {}
    for fid, rfid in all_rf:
        related_map.setdefault(fid, []).append(rfid)

    enriched_risks: list[dict[str, Any]] = []
    for s in scored_findings:
        f = findings_map.get(s["finding_id"])
        c_code = control_code_map.get(f.control_id) if f and f.control_id else None
        item = {
            **s,
            "control_id": f.control_id if f else None,
            "control_code": c_code,
            "department": f.department if f else None,
            "severity": f.severity if f else "Medium",
            "description": f.description if f else "",
            "source_document_id": f.source_document_id if f else None,
            "source_page": f.source_page if f else None,
            "related_finding_ids": related_map.get(s["finding_id"], []),
        }
        enriched_risks.append(item)

    return {
        "disclaimer": DISCLAIMER,
        "risks": enriched_risks,
    }


@router.get("/summary", summary="Get aggregated compliance and risk summary")
def get_summary(
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> dict[str, Any]:
    """
    Return high-level compliance indicators, status breakdowns, overdue remediation
    counts, recurrence metrics, and risk distributions.
    """
    org_id = user.organisation_id

    # 1. Control status counts
    control_status_counts = {
        "Compliant": 0,
        "Needs Review": 0,
        "Gap Identified": 0,
        "Not Assessed": 0,
    }
    ctrl_rows = (
        db.query(Control.status, func.count(Control.id))
        .filter(Control.organisation_id == org_id)
        .group_by(Control.status)
        .all()
    )
    for st, cnt in ctrl_rows:
        if st in control_status_counts:
            control_status_counts[st] = cnt
        else:
            control_status_counts[st] = cnt

    # 2. Open findings by severity
    open_findings_by_severity = {"High": 0, "Medium": 0, "Low": 0}
    f_rows = (
        db.query(Finding.severity, func.count(Finding.id))
        .filter(
            Finding.organisation_id == org_id,
            Finding.status == "Open",
        )
        .group_by(Finding.severity)
        .all()
    )
    for sev, cnt in f_rows:
        if sev in open_findings_by_severity:
            open_findings_by_severity[sev] = cnt

    # 3. Overdue actions count
    today = date.today()
    overdue_actions_count = (
        db.query(func.count(RemediationAction.id))
        .filter(
            RemediationAction.organisation_id == org_id,
            RemediationAction.due_date < today,
            RemediationAction.status != "Completed",
        )
        .scalar()
        or 0
    )

    # 4. Recurring findings count
    recurring_findings_count = (
        db.query(func.count(Finding.id))
        .filter(
            Finding.organisation_id == org_id,
            Finding.is_recurrence == True,
        )
        .scalar()
        or 0
    )

    # 5. Findings per department per audit cycle
    dept_cycle_rows = (
        db.query(
            Finding.department,
            Finding.audit_cycle_id,
            AuditCycle.name,
            func.count(Finding.id),
        )
        .outerjoin(
            AuditCycle,
            (AuditCycle.id == Finding.audit_cycle_id)
            & (AuditCycle.organisation_id == org_id),
        )
        .filter(Finding.organisation_id == org_id)
        .group_by(Finding.department, Finding.audit_cycle_id, AuditCycle.name)
        .all()
    )
    findings_per_dept_per_cycle = [
        {
            "department": dept or "Unassigned",
            "audit_cycle_id": cycle_id,
            "cycle_name": cycle_name or ("Unassigned" if cycle_id is None else "Unknown Cycle"),
            "count": count,
        }
        for dept, cycle_id, cycle_name, count in dept_cycle_rows
    ]

    # 6. Risk by control
    scored_open = score_all_open_findings(db, org_id)
    score_by_finding = {s["finding_id"]: s["score"] for s in scored_open}

    open_findings = (
        db.query(Finding)
        .filter(
            Finding.organisation_id == org_id,
            Finding.status == "Open",
        )
        .all()
    )

    control_scores: dict[str, list[float]] = {}
    for f in open_findings:
        if f.control_id and f.id in score_by_finding:
            control_scores.setdefault(f.control_id, []).append(score_by_finding[f.id])

    org_controls = (
        db.query(Control)
        .filter(Control.organisation_id == org_id)
        .all()
    )

    risk_by_control = []
    for c in org_controls:
        scores = control_scores.get(c.id, [])
        finding_count = len(scores)
        avg_score = round(sum(scores) / finding_count, 2) if finding_count > 0 else 0.0
        risk_by_control.append({
            "control_id": c.id,
            "control_code": c.control_code,
            "title": c.title,
            "avg_score": avg_score,
            "finding_count": finding_count,
        })
    risk_by_control.sort(key=lambda x: (x["avg_score"], x["finding_count"]), reverse=True)

    return {
        "control_status_counts": control_status_counts,
        "open_findings_by_severity": open_findings_by_severity,
        "overdue_actions_count": overdue_actions_count,
        "recurring_findings_count": recurring_findings_count,
        "findings_per_dept_per_cycle": findings_per_dept_per_cycle,
        "risk_by_control": risk_by_control,
        "disclaimer": DISCLAIMER,
    }

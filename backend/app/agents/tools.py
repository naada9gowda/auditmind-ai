"""
agents/tools.py — Deterministic tool functions for AuditMind AI assistant.

All tools are strictly organisation-scoped, validate their inputs, and enforce
the non-negotiable compliance rules:
  - All AI-generated findings and remediations are DRAFT only.
  - Queries filter strictly by organisation_id.
  - History is retrieved solely from authentic DB records.
  - Document text is treated as untrusted data.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.history.sql_history import SqlHistoryService
from app.models.control import Control
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.remediation import RemediationAction
from app.models.status_history import StatusHistory
from app.risk.scoring import score_all_open_findings

logger = logging.getLogger(__name__)


def search_controls(query: str, db: Session, organisation_id: str) -> list[dict[str, Any]]:
    """
    Search controls in the organisation by code or title keyword.
    Returns: [{id, control_code, title, status, cadence}]
    """
    if not query or not query.strip():
        # Return all or top controls in org
        controls = (
            db.query(Control)
            .filter(Control.organisation_id == organisation_id)
            .limit(20)
            .all()
        )
    else:
        term = f"%{query.strip()}%"
        controls = (
            db.query(Control)
            .filter(
                Control.organisation_id == organisation_id,
                or_(
                    Control.control_code.ilike(term),
                    Control.title.ilike(term),
                ),
            )
            .all()
        )

    return [
        {
            "id": c.id,
            "control_code": c.control_code,
            "title": c.title,
            "status": c.status,
            "cadence": c.cadence,
        }
        for c in controls
    ]


def get_finding_history(control_id: str, db: Session, organisation_id: str) -> dict[str, Any]:
    """
    Calls SqlHistoryService.get_timeline() and returns serialized ControlTimeline.
    If no relevant records exist, returns message: 'No relevant history found'.
    """
    svc = SqlHistoryService()
    timeline = svc.get_timeline(
        organisation_id=organisation_id,
        control_id=control_id,
        db=db,
    )

    serialized_entries = [
        {
            "event_type": e.event_type,
            "event_date": e.event_date.isoformat() if e.event_date else None,
            "entity_id": e.entity_id,
            "entity_type": e.entity_type,
            "summary": e.summary,
            "detail": e.detail,
        }
        for e in timeline.entries
    ]

    msg = timeline.message
    if not serialized_entries and not msg:
        msg = "No relevant history found."

    return {
        "control_id": timeline.control_id,
        "control_code": timeline.control_code,
        "message": msg,
        "entries": serialized_entries,
    }


def assess_evidence(control_id: str, db: Session, organisation_id: str) -> list[dict[str, Any]]:
    """
    Query Evidence records for a specific control in the organisation.
    Returns: [{id, assessment, document_id, page_number, excerpt, review_status}]
    """
    evidence_rows = (
        db.query(Evidence)
        .filter(
            Evidence.organisation_id == organisation_id,
            Evidence.control_id == control_id,
        )
        .all()
    )

    return [
        {
            "id": e.id,
            "assessment": e.assessment,
            "document_id": e.document_id,
            "page_number": e.page_number,
            "excerpt": e.excerpt,
            "review_status": e.review_status,
        }
        for e in evidence_rows
    ]


def get_risk_indicators(db: Session, organisation_id: str) -> list[dict[str, Any]]:
    """
    Return top 5 early-warning risk indicators from score_all_open_findings.
    """
    scored = score_all_open_findings(db, organisation_id)
    return scored[:5]


def draft_finding(
    control_id: str,
    description: str,
    severity: str,
    department: str,
    db: Session,
    organisation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Creates a Finding with review_status='Draft' and ai_generated=True.
    NOTE: This is DRAFT only. Never auto-approves or auto-closes.
    """
    valid_severity = severity if severity in ("High", "Medium", "Low") else "Medium"

    finding = Finding(
        organisation_id=organisation_id,
        control_id=control_id,
        description=description.strip(),
        severity=valid_severity,
        department=department.strip() if department else None,
        status="Open",
        review_status="Draft",
        ai_generated=True,
    )
    db.add(finding)
    db.flush()

    sh = StatusHistory(
        organisation_id=organisation_id,
        entity_type="finding",
        entity_id=finding.id,
        old_status=None,
        new_status="Open",
        changed_by=actor_id,
        note="Draft finding created by AI assistant.",
    )
    db.add(sh)
    db.commit()
    db.refresh(finding)

    return {
        "id": finding.id,
        "control_id": finding.control_id,
        "description": finding.description,
        "severity": finding.severity,
        "department": finding.department,
        "status": finding.status,
        "review_status": finding.review_status,
        "ai_generated": finding.ai_generated,
    }


def draft_remediation(
    finding_id: str,
    action: str,
    owner: str,
    due_date: str,
    db: Session,
    organisation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Creates a RemediationAction with status='Planned'.
    NOTE: DRAFT only.
    """
    finding = (
        db.query(Finding)
        .filter(
            Finding.id == finding_id,
            Finding.organisation_id == organisation_id,
        )
        .first()
    )
    if not finding:
        raise ValueError(f"Finding '{finding_id}' not found in organisation.")

    parsed_date: date | None = None
    if due_date:
        try:
            parsed_date = date.fromisoformat(due_date.strip())
        except (ValueError, TypeError):
            parsed_date = None

    rem = RemediationAction(
        organisation_id=organisation_id,
        finding_id=finding_id,
        action=action.strip(),
        owner=owner.strip() if owner else None,
        due_date=parsed_date,
        status="Planned",
    )
    db.add(rem)
    db.flush()

    sh = StatusHistory(
        organisation_id=organisation_id,
        entity_type="remediation",
        entity_id=rem.id,
        old_status=None,
        new_status="Planned",
        changed_by=actor_id,
        note="Draft remediation action created by AI assistant.",
    )
    db.add(sh)
    db.commit()
    db.refresh(rem)

    return {
        "id": rem.id,
        "finding_id": rem.finding_id,
        "action": rem.action,
        "owner": rem.owner,
        "due_date": rem.due_date.isoformat() if rem.due_date else None,
        "status": rem.status,
    }

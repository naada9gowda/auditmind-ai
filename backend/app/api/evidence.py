"""
api/evidence.py — Evidence mapping and review endpoints.

POST /api/evidence/map               — manually map a document to a control
POST /api/evidence/{id}/review       — accept/reject an evidence assessment
GET  /api/evidence                   — list evidence for the org
GET  /api/evidence/{id}              — single evidence record
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import _get_current_user, require_role
from app.database import get_db
from app.models.activity_log import ActivityLog
from app.models.control import Control
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.status_history import StatusHistory
from app.models.user import User
from app.schemas.evidence import EvidenceMapRequest, EvidenceOut, EvidenceReviewRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evidence", tags=["evidence"])

VALID_ASSESSMENTS = {
    "Candidate Match", "Missing", "Expired", "Incomplete", "Requires Human Review"
}
VALID_REVIEW_DECISIONS = {"Approved", "Rejected"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_evidence_or_404(ev_id: str, org_id: str, db: Session) -> Evidence:
    ev = db.query(Evidence).filter(
        Evidence.id == ev_id,
        Evidence.organisation_id == org_id,
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence record not found.")
    return ev


def _get_control_or_404(ctrl_id: str, org_id: str, db: Session) -> Control:
    ctrl = db.query(Control).filter(
        Control.id == ctrl_id,
        Control.organisation_id == org_id,
    ).first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Control not found.")
    return ctrl


def _get_document_or_404(doc_id: str, org_id: str, db: Session) -> Document:
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.organisation_id == org_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[EvidenceOut], summary="List evidence for the organisation")
def list_evidence(
    control_id: Optional[str] = Query(None),
    assessment: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> list:
    q = db.query(Evidence).filter(Evidence.organisation_id == user.organisation_id)
    if control_id:
        q = q.filter(Evidence.control_id == control_id)
    if assessment:
        q = q.filter(Evidence.assessment == assessment)
    if review_status:
        q = q.filter(Evidence.review_status == review_status)
    return q.all()


@router.get("/{ev_id}", response_model=EvidenceOut, summary="Get a single evidence record")
def get_evidence(
    ev_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> Evidence:
    return _get_evidence_or_404(ev_id, user.organisation_id, db)


@router.post(
    "/map",
    response_model=EvidenceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Manually map or re-map a document to a control",
)
def map_evidence(
    payload: EvidenceMapRequest,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer", "auditor"),
) -> Evidence:
    """
    Create (or replace) an evidence record linking a document to a control.
    Assessment defaults to Requires Human Review until a reviewer acts.
    """
    ctrl = _get_control_or_404(payload.control_id, user.organisation_id, db)
    doc = _get_document_or_404(payload.document_id, user.organisation_id, db)

    # Remove any existing Draft evidence for this (control, document) pair
    existing = db.query(Evidence).filter(
        Evidence.organisation_id == user.organisation_id,
        Evidence.control_id == ctrl.id,
        Evidence.document_id == doc.id,
        Evidence.review_status == "Draft",
    ).first()
    if existing:
        db.delete(existing)
        db.flush()

    ev = Evidence(
        organisation_id=user.organisation_id,
        document_id=doc.id,
        control_id=ctrl.id,
        evidence_date=doc.extracted_date,
        review_status="Draft",
        assessment="Requires Human Review",
        excerpt=payload.excerpt,
        page_number=payload.page_number,
    )
    db.add(ev)

    # Activity log
    db.add(ActivityLog(
        organisation_id=user.organisation_id,
        actor=user.id,
        action="evidence_mapped",
        entity_type="evidence",
        entity_id=ev.id,
        detail=f"Document {doc.id} manually mapped to control {ctrl.control_code}.",
        created_at=datetime.now(timezone.utc),
    ))

    db.commit()
    db.refresh(ev)
    logger.info("Evidence mapped: document=%s control=%s by user=%s", doc.id, ctrl.control_code, user.id)
    return ev


@router.post(
    "/{ev_id}/review",
    response_model=EvidenceOut,
    summary="Reviewer accepts or rejects an evidence assessment",
)
def review_evidence(
    ev_id: str,
    payload: EvidenceReviewRequest,
    db: Session = Depends(get_db),
    user: User = require_role("compliance_officer", "auditor"),
) -> Evidence:
    """
    A human reviewer approves or rejects the evidence assessment.
    Optionally overrides the assessment label.
    Writes status_history and activity_log.

    Rules:
    - Only compliance_officer or auditor may review.
    - Approving evidence does NOT automatically set control status to Compliant.
      Control status changes must be initiated explicitly by an authorised user.
    """
    ev = _get_evidence_or_404(ev_id, user.organisation_id, db)

    decision = payload.decision
    if decision not in VALID_REVIEW_DECISIONS:
        raise HTTPException(
            status_code=422,
            detail=f"decision must be one of {sorted(VALID_REVIEW_DECISIONS)}.",
        )

    # Optional assessment override
    new_assessment = payload.assessment
    if new_assessment and new_assessment not in VALID_ASSESSMENTS:
        raise HTTPException(
            status_code=422,
            detail=f"assessment must be one of {sorted(VALID_ASSESSMENTS)}.",
        )

    old_review_status = ev.review_status
    old_assessment = ev.assessment

    ev.review_status = decision           # "Approved" or "Rejected"
    ev.reviewed_by = user.id
    if new_assessment:
        ev.assessment = new_assessment

    now = datetime.now(timezone.utc)

    # Append-only status history
    db.add(StatusHistory(
        organisation_id=user.organisation_id,
        entity_type="evidence",
        entity_id=ev.id,
        old_status=old_review_status,
        new_status=decision,
        changed_by=user.id,
        changed_at=now,
        note=payload.note,
    ))

    # Activity log
    detail = f"Evidence review_status changed from '{old_review_status}' to '{decision}'."
    if new_assessment and new_assessment != old_assessment:
        detail += f" Assessment updated from '{old_assessment}' to '{new_assessment}'."
    if payload.note:
        detail += f" Note: {payload.note}"

    db.add(ActivityLog(
        organisation_id=user.organisation_id,
        actor=user.id,
        action="evidence_reviewed",
        entity_type="evidence",
        entity_id=ev.id,
        detail=detail,
        created_at=now,
    ))

    db.commit()
    db.refresh(ev)
    logger.info(
        "Evidence reviewed: ev_id=%s decision=%s by user=%s",
        ev.id, decision, user.id,
    )
    return ev

"""
api/findings.py — CRUD + filter endpoints for findings.

Filters on GET /api/findings:
  - control_id
  - department
  - status
  - audit_cycle_id
  - severity
  - review_status
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import _get_current_user, require_role
from app.database import get_db
from app.history.sql_history import get_history_service
from app.models.finding import Finding
from app.models.related_finding import RelatedFinding
from app.models.remediation import RemediationAction
from app.models.status_history import StatusHistory
from app.models.user import User
from app.schemas.finding import FindingCreate, FindingOut, FindingUpdate
from app.schemas.status_history import StatusHistoryOut
from app.services.status import transition_status

router = APIRouter(prefix="/findings", tags=["findings"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_finding_or_404(finding_id: str, org_id: str, db: Session) -> Finding:
    finding = db.query(Finding).filter(
        Finding.id == finding_id,
        Finding.organisation_id == org_id,
    ).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return finding


# ---------------------------------------------------------------------------
# List / get
# ---------------------------------------------------------------------------

@router.get("", response_model=List[FindingOut], summary="List findings with optional filters")
def list_findings(
    control_id: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    audit_cycle_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> list:
    q = db.query(Finding).filter(Finding.organisation_id == user.organisation_id)
    if control_id:
        q = q.filter(Finding.control_id == control_id)
    if department:
        q = q.filter(Finding.department == department)
    if status_filter:
        q = q.filter(Finding.status == status_filter)
    if audit_cycle_id:
        q = q.filter(Finding.audit_cycle_id == audit_cycle_id)
    if severity:
        q = q.filter(Finding.severity == severity)
    if review_status:
        q = q.filter(Finding.review_status == review_status)
    return q.order_by(Finding.id).all()


@router.get("/{finding_id}", response_model=FindingOut, summary="Get a single finding")
def get_finding(
    finding_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> Finding:
    return _get_finding_or_404(finding_id, user.organisation_id, db)


# ---------------------------------------------------------------------------
# Create / update
# ---------------------------------------------------------------------------

@router.post("", response_model=FindingOut, status_code=status.HTTP_201_CREATED, summary="Create a finding")
def create_finding(
    payload: FindingCreate,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer", "auditor"),
) -> Finding:
    finding = Finding(
        organisation_id=user.organisation_id,
        **payload.model_dump(),
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


@router.patch("/{finding_id}", response_model=FindingOut, summary="Update finding metadata")
def update_finding(
    finding_id: str,
    payload: FindingUpdate,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer", "auditor"),
) -> Finding:
    finding = _get_finding_or_404(finding_id, user.organisation_id, db)
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(finding, field, val)
    db.commit()
    db.refresh(finding)
    return finding


# ---------------------------------------------------------------------------
# Status transition
# ---------------------------------------------------------------------------

@router.post("/{finding_id}/status", response_model=FindingOut, summary="Transition finding status")
def change_finding_status(
    finding_id: str,
    new_status: str = Query(..., description="Target status value"),
    note: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> Finding:
    finding = _get_finding_or_404(finding_id, user.organisation_id, db)

    # Guard: closing requires at least one Completed remediation action
    if new_status == "Closed":
        has_completed = (
            db.query(RemediationAction)
            .filter(
                RemediationAction.finding_id == finding_id,
                RemediationAction.status == "Completed",
            )
            .first()
        )
        if not has_completed:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cannot close a finding without at least one Completed "
                    "remediation action. Mark a remediation as Completed first."
                ),
            )

    transition_status(
        db=db,
        entity_type="finding",
        entity=finding,
        new_status=new_status,
        actor=user,
        note=note,
    )
    db.commit()
    db.refresh(finding)
    return finding


# ---------------------------------------------------------------------------
# Approve — sets review_status=Approved, writes status_history, finds related
# ---------------------------------------------------------------------------

@router.post(
    "/{finding_id}/approve",
    summary="Approve a Draft finding (compliance_officer / admin only)",
)
def approve_finding(
    finding_id: str,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer"),
) -> Dict[str, Any]:
    """
    Approve a Draft finding.

    Side-effects:
      1. Sets review_status = Approved.
      2. Writes a status_history row for the review_status change.
      3. Runs find_related_findings() and stores matches in related_findings
         (reviewed_by = null — awaiting reviewer confirmation).

    Returns the updated FindingOut plus a list of related_findings created.
    """
    finding = _get_finding_or_404(finding_id, user.organisation_id, db)

    if finding.review_status != "Draft":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Finding review_status is '{finding.review_status}', not 'Draft'. "
                "Only Draft findings can be approved."
            ),
        )

    old_rs = finding.review_status
    finding.review_status = "Approved"

    # Write status_history row for review_status change
    from app.models.status_history import StatusHistory
    from datetime import datetime, timezone
    sh = StatusHistory(
        organisation_id=user.organisation_id,
        entity_type="finding_review",
        entity_id=finding.id,
        old_status=old_rs,
        new_status="Approved",
        changed_by=user.id,
        changed_at=datetime.now(timezone.utc),
        note="Finding approved.",
    )
    db.add(sh)

    db.flush()  # get finding.id stable before history query

    # Run history search for related findings
    svc = get_history_service()
    related_results = svc.find_related_findings(
        organisation_id=user.organisation_id,
        control_id=finding.control_id,
        department=finding.department,
        description=finding.description,
        exclude_finding_id=finding.id,
        exclude_cycle_id=finding.audit_cycle_id,
        db=db,
    )

    # Persist suggestions that don't already exist
    created_related: list[dict] = []
    for r in related_results:
        existing = (
            db.query(RelatedFinding)
            .filter(
                RelatedFinding.finding_id == finding.id,
                RelatedFinding.related_finding_id == r.related_finding_id,
            )
            .first()
        )
        if not existing:
            rf = RelatedFinding(
                organisation_id=user.organisation_id,
                finding_id=finding.id,
                related_finding_id=r.related_finding_id,
                match_reason=r.match_reason,
                match_score=r.match_score,
                reviewed_by=None,
            )
            db.add(rf)
            created_related.append({
                "related_finding_id": r.related_finding_id,
                "match_score": r.match_score,
                "match_reason": r.match_reason,
            })

    db.commit()
    db.refresh(finding)

    finding_out = FindingOut.model_validate(finding)
    return {
        "finding": finding_out.model_dump(),
        "related_findings_created": len(created_related),
        "related_findings": created_related,
        "message": (
            f"Finding approved. {len(created_related)} related finding suggestion(s) stored."
            if created_related
            else "Finding approved. No relevant history found."
        ),
    }


# ---------------------------------------------------------------------------
# Related-finding review — confirm or reject a suggestion
# ---------------------------------------------------------------------------

class _RelatedReviewBody(FindingOut.__class__):
    """We only need a tiny body — define it inline to avoid schema clutter."""
    pass


from pydantic import BaseModel


class RelatedReviewBody(BaseModel):
    decision: str  # "confirmed" | "rejected"


@router.post(
    "/{finding_id}/related/{related_id}/review",
    summary="Confirm or reject a related-finding suggestion (compliance_officer / auditor)",
)
def review_related_finding(
    finding_id: str,
    related_id: str,
    body: RelatedReviewBody,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer", "auditor"),
) -> Dict[str, Any]:
    """
    Confirm or reject a related-finding suggestion.

    - decision = "confirmed": marks the suggestion as reviewed AND sets
      is_recurrence = True on the finding.
    - decision = "rejected": marks the suggestion as reviewed (reviewed_by is
      set) but leaves is_recurrence unchanged.

    In both cases, reviewed_by = current user's ID.
    """
    if body.decision not in ("confirmed", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="decision must be 'confirmed' or 'rejected'.",
        )

    finding = _get_finding_or_404(finding_id, user.organisation_id, db)

    rf = (
        db.query(RelatedFinding)
        .filter(
            RelatedFinding.id == related_id,
            RelatedFinding.finding_id == finding_id,
            RelatedFinding.organisation_id == user.organisation_id,
        )
        .first()
    )
    if not rf:
        raise HTTPException(
            status_code=404,
            detail="Related finding suggestion not found for this finding.",
        )

    rf.reviewed_by = user.id

    if body.decision == "confirmed":
        finding.is_recurrence = True

    db.commit()
    db.refresh(finding)
    db.refresh(rf)

    return {
        "decision": body.decision,
        "related_finding_id": rf.related_finding_id,
        "finding_id": finding.id,
        "is_recurrence": finding.is_recurrence,
        "reviewed_by": rf.reviewed_by,
    }


# ---------------------------------------------------------------------------
# History — status history + related findings for a finding
# ---------------------------------------------------------------------------

@router.get(
    "/{finding_id}/history",
    summary="Get status history (and related finding suggestions) for a finding",
)
def get_finding_history(
    finding_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> Dict[str, Any]:
    """
    Returns:
      - status_history: list of status_history rows
      - related_findings: list of related_finding suggestions (with review status)
    """
    finding = _get_finding_or_404(finding_id, user.organisation_id, db)

    history_rows = (
        db.query(StatusHistory)
        .filter(
            StatusHistory.entity_id == finding_id,
            StatusHistory.organisation_id == user.organisation_id,
        )
        .order_by(StatusHistory.changed_at.asc())
        .all()
    )

    related_rows = (
        db.query(RelatedFinding)
        .filter(
            RelatedFinding.finding_id == finding_id,
            RelatedFinding.organisation_id == user.organisation_id,
        )
        .all()
    )

    history_out = [StatusHistoryOut.model_validate(h) for h in history_rows]
    related_out = [
        {
            "id": r.id,
            "related_finding_id": r.related_finding_id,
            "match_score": r.match_score,
            "match_reason": r.match_reason,
            "reviewed_by": r.reviewed_by,
        }
        for r in related_rows
    ]

    return {
        "finding_id": finding.id,
        "is_recurrence": finding.is_recurrence,
        "status_history": [h.model_dump() for h in history_out],
        "related_findings": related_out,
    }

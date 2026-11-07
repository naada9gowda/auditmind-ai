"""
api/controls.py — CRUD endpoints for the control register.

All queries are filtered by the current user's organisation_id.
Status changes go through the status-transition service.

GET /api/controls returns each control's stored status plus a
computed_status signal derived from approved findings and evidence:
  - "Compliant" is NEVER auto-set by the system; it only reflects the
    stored status set explicitly by an authorised human reviewer.
  - If there are open/approved findings for a control → "Gap Identified"
  - If there is at least one Approved evidence with Candidate Match → "Needs Review"
    (meaning evidence is present but explicit Compliant decision still needed)
  - Otherwise stored status is returned as-is.
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import _get_current_user, require_role
from app.database import get_db
from app.models.control import Control
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.user import User
from app.schemas.control import ControlCreate, ControlOut, ControlUpdate, ControlWithComputedStatus
from app.schemas.status_history import StatusHistoryOut
from app.services.status import transition_status
from app.models.status_history import StatusHistory

router = APIRouter(prefix="/controls", tags=["controls"])


def _compute_status(control: Control, db: Session) -> str:
    """
    Compute a derived status signal for display purposes only.

    Rules (in priority order):
      1. Any Approved finding that is Open or In Remediation → "Gap Identified"
      2. Stored status is "Compliant" (set by human) → "Compliant"
      3. Any Approved evidence with Candidate Match → "Needs Review"
         (evidence exists but human hasn't yet set Compliant)
      4. Fall back to stored status.

    Design rule: this function NEVER modifies the control.status column.
    Compliant can only come from an explicit human action via PATCH /status.
    """
    # Check for open approved findings
    open_finding = db.query(Finding).filter(
        Finding.control_id == control.id,
        Finding.review_status == "Approved",
        Finding.status.in_(["Open", "In Remediation"]),
    ).first()
    if open_finding:
        return "Gap Identified"

    # Respect human-set Compliant
    if control.status == "Compliant":
        return "Compliant"

    # Check for approved candidate evidence
    candidate_ev = db.query(Evidence).filter(
        Evidence.control_id == control.id,
        Evidence.review_status == "Approved",
        Evidence.assessment == "Candidate Match",
    ).first()
    if candidate_ev:
        return "Needs Review"   # evidence present, but human hasn't closed compliance loop

    return control.status


@router.get("", response_model=List[ControlWithComputedStatus], summary="List controls for the current organisation")
def list_controls(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> list:
    q = db.query(Control).filter(Control.organisation_id == user.organisation_id)
    if status_filter:
        q = q.filter(Control.status == status_filter)
    controls = q.order_by(Control.control_code).all()
    # Annotate with computed status (read-only display field)
    result = []
    for ctrl in controls:
        data = ControlWithComputedStatus.model_validate(ctrl)
        data.computed_status = _compute_status(ctrl, db)
        result.append(data)
    return result


@router.post("", response_model=ControlOut, status_code=status.HTTP_201_CREATED, summary="Create a new control")
def create_control(
    payload: ControlCreate,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer"),
) -> Control:
    control = Control(
        organisation_id=user.organisation_id,
        **payload.model_dump(),
    )
    db.add(control)
    db.commit()
    db.refresh(control)
    return control


@router.get("/{control_id}", response_model=ControlOut, summary="Get a single control")
def get_control(
    control_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> Control:
    control = db.query(Control).filter(
        Control.id == control_id,
        Control.organisation_id == user.organisation_id,
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="Control not found.")
    return control


@router.patch("/{control_id}", response_model=ControlOut, summary="Update control metadata (not status)")
def update_control(
    control_id: str,
    payload: ControlUpdate,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer"),
) -> Control:
    control = db.query(Control).filter(
        Control.id == control_id,
        Control.organisation_id == user.organisation_id,
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="Control not found.")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(control, field, val)
    db.commit()
    db.refresh(control)
    return control


@router.post("/{control_id}/status", response_model=ControlOut, summary="Transition control status")
def change_control_status(
    control_id: str,
    new_status: str = Query(..., description="Target status value"),
    note: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer"),
) -> Control:
    control = db.query(Control).filter(
        Control.id == control_id,
        Control.organisation_id == user.organisation_id,
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="Control not found.")
    transition_status(
        db=db,
        entity_type="control",
        entity=control,
        new_status=new_status,
        actor=user,
        note=note,
    )
    db.commit()
    db.refresh(control)
    return control


@router.get("/{control_id}/history", response_model=List[StatusHistoryOut], summary="Get status history for a control")
def get_control_history(
    control_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> list:
    # Verify the control belongs to this org
    control = db.query(Control).filter(
        Control.id == control_id,
        Control.organisation_id == user.organisation_id,
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="Control not found.")
    return (
        db.query(StatusHistory)
        .filter(
            StatusHistory.entity_type == "control",
            StatusHistory.entity_id == control_id,
            StatusHistory.organisation_id == user.organisation_id,
        )
        .order_by(StatusHistory.changed_at.asc())
        .all()
    )

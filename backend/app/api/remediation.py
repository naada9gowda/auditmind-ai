"""
api/remediation.py — CRUD endpoints for remediation actions.

Role-based permission rules on status transitions:
  - auditor: may NOT change remediation status (read-only on remediations)
  - control_owner: may move to "In Progress" or "Ready for Review"
  - compliance_officer / admin: may also move to "Completed"

is_overdue is computed on every response (not stored in DB).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import _get_current_user, require_role
from app.database import get_db
from app.models.finding import Finding
from app.models.remediation import RemediationAction
from app.models.user import User
from app.schemas.remediation import RemediationCreate, RemediationOut, RemediationUpdate
from app.services.status import transition_status

router = APIRouter(prefix="/remediations", tags=["remediations"])

# Statuses that only compliance_officer / admin may set
_PRIVILEGED_STATUSES = frozenset({"Completed"})
# Statuses that auditors may NOT change to (they cannot change status at all)
_AUDITOR_DENIED_ROLES = frozenset({"auditor"})


def _assert_finding_in_org(finding_id: str, org_id: str, db: Session) -> Finding:
    """Guard: ensure the finding exists and belongs to the user's org."""
    finding = db.query(Finding).filter(
        Finding.id == finding_id,
        Finding.organisation_id == org_id,
    ).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found or not in your organisation.")
    return finding


# ---------------------------------------------------------------------------
# List / get
# ---------------------------------------------------------------------------

@router.get("", response_model=List[RemediationOut], summary="List remediation actions")
def list_remediations(
    finding_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> list:
    q = db.query(RemediationAction).filter(
        RemediationAction.organisation_id == user.organisation_id
    )
    if finding_id:
        q = q.filter(RemediationAction.finding_id == finding_id)
    if status_filter:
        q = q.filter(RemediationAction.status == status_filter)
    actions = q.order_by(RemediationAction.due_date).all()
    return [RemediationOut.from_orm_with_overdue(a) for a in actions]


@router.get("/{action_id}", response_model=RemediationOut, summary="Get a single remediation action")
def get_remediation(
    action_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> RemediationOut:
    action = db.query(RemediationAction).filter(
        RemediationAction.id == action_id,
        RemediationAction.organisation_id == user.organisation_id,
    ).first()
    if not action:
        raise HTTPException(status_code=404, detail="Remediation action not found.")
    return RemediationOut.from_orm_with_overdue(action)


# ---------------------------------------------------------------------------
# Create / update
# ---------------------------------------------------------------------------

@router.post("", response_model=RemediationOut, status_code=status.HTTP_201_CREATED, summary="Create a remediation action")
def create_remediation(
    payload: RemediationCreate,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer", "control_owner"),
) -> RemediationOut:
    # Ensure the finding is in the same org
    _assert_finding_in_org(payload.finding_id, user.organisation_id, db)
    action = RemediationAction(
        organisation_id=user.organisation_id,
        **payload.model_dump(),
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return RemediationOut.from_orm_with_overdue(action)


@router.patch("/{action_id}", response_model=RemediationOut, summary="Update remediation action metadata")
def update_remediation(
    action_id: str,
    payload: RemediationUpdate,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer", "control_owner"),
) -> RemediationOut:
    action = db.query(RemediationAction).filter(
        RemediationAction.id == action_id,
        RemediationAction.organisation_id == user.organisation_id,
    ).first()
    if not action:
        raise HTTPException(status_code=404, detail="Remediation action not found.")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(action, field, val)
    db.commit()
    db.refresh(action)
    return RemediationOut.from_orm_with_overdue(action)


# ---------------------------------------------------------------------------
# Status transition — with role-based permission enforcement
# ---------------------------------------------------------------------------

@router.post("/{action_id}/status", response_model=RemediationOut, summary="Transition remediation status")
def change_remediation_status(
    action_id: str,
    new_status: str = Query(..., description="Target status value"),
    note: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> RemediationOut:
    """
    Transition a remediation action's status.

    Permission rules:
      - auditor: cannot change status (403)
      - control_owner: may set "In Progress" or "Ready for Review" only
      - compliance_officer / admin: may set any status including "Completed"
    """
    action = db.query(RemediationAction).filter(
        RemediationAction.id == action_id,
        RemediationAction.organisation_id == user.organisation_id,
    ).first()
    if not action:
        raise HTTPException(status_code=404, detail="Remediation action not found.")

    # Auditors cannot change remediation status
    if user.role == "auditor":
        raise HTTPException(
            status_code=403,
            detail="Auditors cannot change remediation status.",
        )

    # Only compliance_officer / admin can mark Completed
    if new_status == "Completed" and user.role not in ("compliance_officer", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Only compliance_officer or admin may mark a remediation as Completed.",
        )

    transition_status(
        db=db,
        entity_type="remediation",
        entity=action,
        new_status=new_status,
        actor=user,
        note=note,
    )
    db.commit()
    db.refresh(action)
    return RemediationOut.from_orm_with_overdue(action)

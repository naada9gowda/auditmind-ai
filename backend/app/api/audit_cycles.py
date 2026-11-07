"""
api/audit_cycles.py — CRUD endpoints for audit cycles.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import _get_current_user, require_role
from app.database import get_db
from app.models.audit_cycle import AuditCycle
from app.models.user import User
from app.schemas.audit_cycle import AuditCycleCreate, AuditCycleOut

router = APIRouter(prefix="/audit-cycles", tags=["audit-cycles"])


@router.get("", response_model=List[AuditCycleOut], summary="List audit cycles")
def list_audit_cycles(
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> list:
    return (
        db.query(AuditCycle)
        .filter(AuditCycle.organisation_id == user.organisation_id)
        .order_by(AuditCycle.start_date.desc())
        .all()
    )


@router.post("", response_model=AuditCycleOut, status_code=status.HTTP_201_CREATED, summary="Create an audit cycle")
def create_audit_cycle(
    payload: AuditCycleCreate,
    db: Session = Depends(get_db),
    user: User = require_role("admin", "compliance_officer", "auditor"),
) -> AuditCycle:
    cycle = AuditCycle(
        organisation_id=user.organisation_id,
        **payload.model_dump(),
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle


@router.get("/{cycle_id}", response_model=AuditCycleOut, summary="Get a single audit cycle")
def get_audit_cycle(
    cycle_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> AuditCycle:
    cycle = db.query(AuditCycle).filter(
        AuditCycle.id == cycle_id,
        AuditCycle.organisation_id == user.organisation_id,
    ).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Audit cycle not found.")
    return cycle

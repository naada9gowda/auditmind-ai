"""
services/status.py — Status-transition service.

Design rules enforced here:
- Every status change is validated against an allowed-transition table.
- A StatusHistory row is INSERTED (never updated) for every change.
- An ActivityLog row is INSERTED for every change.
- Findings can only be set to 'Closed' by a compliance_officer or admin,
  and only when the current status is 'Ready for Review'.
- All writes happen in a single transaction (the caller's session).

Usage:
    from app.services.status import transition_status
    transition_status(
        db=db,
        entity_type="finding",
        entity=finding_obj,
        new_status="In Remediation",
        actor=current_user,
        note="Assigned to IT team",
    )
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.status_history import StatusHistory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed transitions per entity type
# Format: { current_status -> set(allowed_next_statuses) }
# ---------------------------------------------------------------------------

FINDING_TRANSITIONS: dict[str, set[str]] = {
    "Open": {"In Remediation", "Ready for Review"},
    "In Remediation": {"Ready for Review", "Open"},
    "Ready for Review": {"Closed", "Open", "In Remediation"},
    "Closed": {"Open"},          # re-open is allowed by any authorised user
}

CONTROL_TRANSITIONS: dict[str, set[str]] = {
    "Not Assessed": {"Needs Review", "Gap Identified", "Compliant"},
    "Needs Review": {"Compliant", "Gap Identified", "Not Assessed"},
    "Gap Identified": {"Needs Review", "In Remediation", "Not Assessed"},
    "Compliant": {"Needs Review", "Not Assessed"},
    # "In Remediation" is an intermediate tag for controls in some workflows
    "In Remediation": {"Gap Identified", "Needs Review", "Compliant"},
}

REMEDIATION_TRANSITIONS: dict[str, set[str]] = {
    "Planned": {"In Progress"},
    "In Progress": {"Ready for Review", "Planned"},
    "Ready for Review": {"Completed", "In Progress"},
    "Completed": {"In Progress"},   # allow re-opening completed actions
}

_TRANSITION_TABLES: dict[str, dict[str, set[str]]] = {
    "finding": FINDING_TRANSITIONS,
    "control": CONTROL_TRANSITIONS,
    "remediation": REMEDIATION_TRANSITIONS,
}

# Roles that may close a finding
_FINDING_CLOSE_ROLES = {"compliance_officer", "admin"}


def transition_status(
    *,
    db: Session,
    entity_type: str,          # "finding" | "control" | "remediation"
    entity: Any,               # ORM object with .status and .organisation_id
    new_status: str,
    actor: Any,                # User ORM object (has .id, .role)
    note: str | None = None,
) -> None:
    """
    Validate and apply a status transition in-place.

    Writes a StatusHistory row and an ActivityLog row inside the caller's
    transaction. The caller is responsible for db.commit().

    Raises:
        HTTPException 400 — invalid transition.
        HTTPException 403 — insufficient role for this transition.
    """
    transitions = _TRANSITION_TABLES.get(entity_type)
    if transitions is None:
        raise ValueError(f"Unknown entity_type for status transition: '{entity_type}'")

    old_status: str = entity.status
    allowed: set[str] = transitions.get(old_status, set())

    if new_status not in allowed:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot transition {entity_type} from '{old_status}' to '{new_status}'. "
                f"Allowed next statuses: {sorted(allowed) or 'none'}."
            ),
        )

    # Special rule: only compliance_officer or admin can close a finding
    if entity_type == "finding" and new_status == "Closed":
        if actor.role not in _FINDING_CLOSE_ROLES:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Only compliance_officer or admin may close a finding. "
                    f"Your role is '{actor.role}'."
                ),
            )

    # Apply the status change to the ORM object
    entity.status = new_status

    now = datetime.now(timezone.utc)

    # Append-only history record
    history = StatusHistory(
        organisation_id=entity.organisation_id,
        entity_type=entity_type,
        entity_id=entity.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=actor.id,
        changed_at=now,
        note=note,
    )
    db.add(history)

    # Immutable activity log
    log = ActivityLog(
        organisation_id=entity.organisation_id,
        actor=actor.id,
        action="status_change",
        entity_type=entity_type,
        entity_id=entity.id,
        detail=f"{entity_type} status changed from '{old_status}' to '{new_status}'."
               + (f" Note: {note}" if note else ""),
        created_at=now,
    )
    db.add(log)

    logger.info(
        "status_change entity_type=%s entity_id=%s %s->%s actor=%s",
        entity_type, entity.id, old_status, new_status, actor.id,
    )

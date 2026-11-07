"""
api/history.py — Audit history and timeline endpoints.

Endpoints:
  GET /api/history/timeline?control_id=<uuid_or_code>
      Returns the full chronological audit timeline for a control.

  GET /api/findings/{finding_id}/history
      Now extended: returns status history rows PLUS any related findings
      stored for this finding.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import _get_current_user
from app.database import get_db
from app.history.sql_history import get_history_service
from app.models.control import Control
from app.models.user import User

router = APIRouter(tags=["history"])


# ---------------------------------------------------------------------------
# GET /api/history/timeline
# ---------------------------------------------------------------------------

@router.get(
    "/history/timeline",
    summary="Get the full chronological audit timeline for a control",
)
def get_history_timeline(
    control_id: Optional[str] = Query(None, description="Control UUID"),
    control_code: Optional[str] = Query(None, description="Control code, e.g. SEC-014"),
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> Dict[str, Any]:
    """
    Returns all audit cycles, findings, remediation actions, and status changes
    for the specified control, ordered chronologically.

    Accepts either `control_id` (UUID) or `control_code` (e.g. SEC-014).
    Returns {"control_id": ..., "control_code": ..., "entries": [...], "message": "..."}.
    """
    if not control_id and not control_code:
        raise HTTPException(
            status_code=400,
            detail="Provide either control_id or control_code as a query parameter.",
        )

    # Resolve control_code → control_id
    resolved_control_id = control_id
    if not resolved_control_id and control_code:
        ctrl = (
            db.query(Control)
            .filter(
                Control.organisation_id == user.organisation_id,
                Control.control_code == control_code,
            )
            .first()
        )
        if not ctrl:
            raise HTTPException(
                status_code=404,
                detail=f"Control with code '{control_code}' not found.",
            )
        resolved_control_id = ctrl.id

    svc = get_history_service()
    timeline = svc.get_timeline(
        organisation_id=user.organisation_id,
        control_id=resolved_control_id,
        db=db,
    )

    # Serialise TimelineEntry dataclasses to plain dicts
    entries_out: List[Dict[str, Any]] = []
    for entry in timeline.entries:
        entries_out.append({
            "event_type": entry.event_type,
            "event_date": entry.event_date.isoformat() if entry.event_date else None,
            "entity_id": entry.entity_id,
            "entity_type": entry.entity_type,
            "summary": entry.summary,
            "detail": entry.detail,
        })

    return {
        "control_id": timeline.control_id,
        "control_code": timeline.control_code,
        "entries": entries_out,
        "message": timeline.message,
    }

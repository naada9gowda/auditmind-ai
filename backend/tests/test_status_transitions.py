"""
tests/test_status_transitions.py

Verifies:
  - Valid transitions succeed.
  - Invalid transitions raise HTTPException 400.
  - Only compliance_officer / admin can close a finding.
  - Every transition writes a StatusHistory row.
  - Transitions write an ActivityLog row.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.control import Control
from app.models.finding import Finding
from app.models.remediation import RemediationAction
from app.models.status_history import StatusHistory
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.services.status import transition_status


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user(db, org_id, role):
    u = User(
        organisation_id=org_id,
        name=f"User {role}",
        email=f"{role}@test.example",
        role=role,
    )
    db.add(u)
    db.flush()
    return u


def _control(db, org_id, status="Not Assessed"):
    c = Control(
        organisation_id=org_id,
        control_code="SEC-TST",
        title="Test Control",
        status=status,
    )
    db.add(c)
    db.flush()
    return c


def _finding(db, org_id, status="Open"):
    f = Finding(
        organisation_id=org_id,
        severity="High",
        description="Test finding",
        status=status,
    )
    db.add(f)
    db.flush()
    return f


def _remediation(db, org_id, finding_id, status="Planned"):
    r = RemediationAction(
        organisation_id=org_id,
        finding_id=finding_id,
        action="Fix it",
        status=status,
    )
    db.add(r)
    db.flush()
    return r


# ── Control transitions ────────────────────────────────────────────────────────

class TestControlTransitions:
    def test_valid_not_assessed_to_needs_review(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "compliance_officer")
        control = _control(db, org_a.id, "Not Assessed")

        transition_status(db=db, entity_type="control", entity=control, new_status="Needs Review", actor=actor)
        db.commit()

        assert control.status == "Needs Review"

    def test_invalid_not_assessed_to_compliant_directly(self, db: Session, two_orgs):
        # Actually this IS allowed per our table, but let's test a truly invalid one:
        # Not Assessed -> Closed (doesn't exist for controls)
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "admin")
        control = _control(db, org_a.id, "Not Assessed")

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db=db, entity_type="control", entity=control, new_status="Closed", actor=actor)
        assert exc_info.value.status_code == 400

    def test_history_row_written(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "compliance_officer")
        control = _control(db, org_a.id, "Not Assessed")

        transition_status(db=db, entity_type="control", entity=control, new_status="Needs Review", actor=actor)
        db.commit()

        rows = db.query(StatusHistory).filter_by(entity_id=control.id).all()
        assert len(rows) == 1
        assert rows[0].old_status == "Not Assessed"
        assert rows[0].new_status == "Needs Review"

    def test_activity_log_written(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "admin")
        control = _control(db, org_a.id, "Not Assessed")

        transition_status(db=db, entity_type="control", entity=control, new_status="Gap Identified", actor=actor)
        db.commit()

        logs = db.query(ActivityLog).filter_by(entity_id=control.id, action="status_change").all()
        assert len(logs) == 1


# ── Finding transitions ────────────────────────────────────────────────────────

class TestFindingTransitions:
    def test_open_to_in_remediation(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "auditor")
        finding = _finding(db, org_a.id, "Open")

        transition_status(db=db, entity_type="finding", entity=finding, new_status="In Remediation", actor=actor)
        db.commit()
        assert finding.status == "In Remediation"

    def test_cannot_close_from_open(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "compliance_officer")
        finding = _finding(db, org_a.id, "Open")

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db=db, entity_type="finding", entity=finding, new_status="Closed", actor=actor)
        assert exc_info.value.status_code == 400

    def test_close_requires_ready_for_review(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "compliance_officer")
        finding = _finding(db, org_a.id, "In Remediation")

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db=db, entity_type="finding", entity=finding, new_status="Closed", actor=actor)
        assert exc_info.value.status_code == 400

    def test_close_by_compliance_officer_from_ready(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "compliance_officer")
        finding = _finding(db, org_a.id, "Ready for Review")

        transition_status(db=db, entity_type="finding", entity=finding, new_status="Closed", actor=actor)
        db.commit()
        assert finding.status == "Closed"

    def test_close_by_admin_from_ready(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "admin")
        finding = _finding(db, org_a.id, "Ready for Review")

        transition_status(db=db, entity_type="finding", entity=finding, new_status="Closed", actor=actor)
        db.commit()
        assert finding.status == "Closed"

    def test_close_by_auditor_forbidden(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "auditor")
        finding = _finding(db, org_a.id, "Ready for Review")

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db=db, entity_type="finding", entity=finding, new_status="Closed", actor=actor)
        assert exc_info.value.status_code == 403

    def test_close_by_control_owner_forbidden(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "control_owner")
        finding = _finding(db, org_a.id, "Ready for Review")

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db=db, entity_type="finding", entity=finding, new_status="Closed", actor=actor)
        assert exc_info.value.status_code == 403

    def test_multiple_transitions_write_multiple_history_rows(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "compliance_officer")
        finding = _finding(db, org_a.id, "Open")

        transition_status(db=db, entity_type="finding", entity=finding, new_status="In Remediation", actor=actor)
        transition_status(db=db, entity_type="finding", entity=finding, new_status="Ready for Review", actor=actor)
        transition_status(db=db, entity_type="finding", entity=finding, new_status="Closed", actor=actor)
        db.commit()

        rows = db.query(StatusHistory).filter_by(entity_id=finding.id).all()
        assert len(rows) == 3  # one per transition — append-only


# ── Remediation transitions ────────────────────────────────────────────────────

class TestRemediationTransitions:
    def test_planned_to_in_progress(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "control_owner")
        finding = _finding(db, org_a.id)
        rem = _remediation(db, org_a.id, finding.id, "Planned")

        transition_status(db=db, entity_type="remediation", entity=rem, new_status="In Progress", actor=actor)
        db.commit()
        assert rem.status == "In Progress"

    def test_cannot_skip_to_completed(self, db: Session, two_orgs):
        org_a, user_a, _, _ = two_orgs
        actor = _user(db, org_a.id, "admin")
        finding = _finding(db, org_a.id)
        rem = _remediation(db, org_a.id, finding.id, "Planned")

        with pytest.raises(HTTPException) as exc_info:
            transition_status(db=db, entity_type="remediation", entity=rem, new_status="Completed", actor=actor)
        assert exc_info.value.status_code == 400

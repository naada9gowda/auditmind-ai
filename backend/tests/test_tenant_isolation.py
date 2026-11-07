"""
tests/test_tenant_isolation.py

Verifies that a user from Org B cannot read records belonging to Org A.
Tests all entity types that carry organisation_id.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.control import Control
from app.models.audit_cycle import AuditCycle
from app.models.finding import Finding
from app.models.remediation import RemediationAction


def _make_control(org_id: str, code: str) -> Control:
    return Control(
        organisation_id=org_id,
        control_code=code,
        title=f"Control {code}",
        status="Not Assessed",
    )


def _make_cycle(org_id: str, name: str) -> AuditCycle:
    return AuditCycle(organisation_id=org_id, name=name)


def _make_finding(org_id: str, cycle_id: str, control_id: str) -> Finding:
    return Finding(
        organisation_id=org_id,
        audit_cycle_id=cycle_id,
        control_id=control_id,
        severity="High",
        description="Test finding",
    )


class TestControlIsolation:
    def test_org_b_cannot_read_org_a_control(self, db: Session, two_orgs):
        org_a, user_a, org_b, user_b = two_orgs

        control_a = _make_control(org_a.id, "SEC-001")
        db.add(control_a)
        db.commit()

        # Query as user_b (org B)
        result = (
            db.query(Control)
            .filter(Control.organisation_id == user_b.organisation_id)
            .all()
        )
        assert len(result) == 0, "Org B should not see Org A's controls"

    def test_org_a_sees_only_own_controls(self, db: Session, two_orgs):
        org_a, user_a, org_b, user_b = two_orgs

        db.add(_make_control(org_a.id, "SEC-001"))
        db.add(_make_control(org_a.id, "SEC-002"))
        db.add(_make_control(org_b.id, "SEC-003"))  # belongs to B
        db.commit()

        result = (
            db.query(Control)
            .filter(Control.organisation_id == user_a.organisation_id)
            .all()
        )
        codes = {c.control_code for c in result}
        assert codes == {"SEC-001", "SEC-002"}, "Org A should see only its own controls"
        assert "SEC-003" not in codes


class TestFindingIsolation:
    def test_org_b_cannot_read_org_a_findings(self, db: Session, two_orgs):
        org_a, user_a, org_b, user_b = two_orgs

        cycle_a = _make_cycle(org_a.id, "Cycle A")
        control_a = _make_control(org_a.id, "SEC-001")
        db.add_all([cycle_a, control_a])
        db.flush()

        finding = _make_finding(org_a.id, cycle_a.id, control_a.id)
        db.add(finding)
        db.commit()

        result = (
            db.query(Finding)
            .filter(Finding.organisation_id == user_b.organisation_id)
            .all()
        )
        assert len(result) == 0


class TestRemediationIsolation:
    def test_org_b_cannot_read_org_a_remediations(self, db: Session, two_orgs):
        org_a, user_a, org_b, user_b = two_orgs

        cycle_a = _make_cycle(org_a.id, "Cycle A")
        control_a = _make_control(org_a.id, "SEC-001")
        db.add_all([cycle_a, control_a])
        db.flush()

        finding_a = _make_finding(org_a.id, cycle_a.id, control_a.id)
        db.add(finding_a)
        db.flush()

        remediation = RemediationAction(
            organisation_id=org_a.id,
            finding_id=finding_a.id,
            action="Fix the gap",
        )
        db.add(remediation)
        db.commit()

        result = (
            db.query(RemediationAction)
            .filter(RemediationAction.organisation_id == user_b.organisation_id)
            .all()
        )
        assert len(result) == 0


class TestAuditCycleIsolation:
    def test_org_b_cannot_read_org_a_cycles(self, db: Session, two_orgs):
        org_a, user_a, org_b, user_b = two_orgs

        db.add(_make_cycle(org_a.id, "Cycle A Q1"))
        db.commit()

        result = (
            db.query(AuditCycle)
            .filter(AuditCycle.organisation_id == user_b.organisation_id)
            .all()
        )
        assert len(result) == 0

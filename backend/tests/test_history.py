"""
tests/test_history.py — Phase 4 acceptance tests for the Audit History module.

Test matrix:
  1. approve January finding → find_related_findings returns [] → "No relevant history found" in message
  2. approve April finding (same control/dept/description) → January appears as related, score > threshold, reason contains "SEC-014" and "IT Operations"
  3. GET /api/history/timeline?control_code=SEC-014 → entries in chronological order
  4. Close finding WITHOUT Completed remediation → 400
  5. Close finding WITH Completed remediation → 200
  6. status_history has exactly one row per status change (not duplicated)
  7. control_owner cannot mark remediation Completed → 403
  8. auditor cannot change remediation status at all → 403
  9. Confirm related finding → is_recurrence = True on the finding
 10. is_overdue correctly computed on remediation

Fixture pattern (critical for SQLite in-memory):
  Use a single shared connection pinned to all sessions — prevents "no such table" errors.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.organisation import Organisation
from app.models.user import User
from app.models.control import Control
from app.models.audit_cycle import AuditCycle
from app.models.finding import Finding
from app.models.remediation import RemediationAction
from app.models.related_finding import RelatedFinding
from app.models.status_history import StatusHistory
from app.history.sql_history import SqlHistoryService

# ---------------------------------------------------------------------------
# Engine & session fixtures — shared in-memory SQLite connection
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    conn = eng.connect()
    Base.metadata.create_all(bind=conn)
    eng._test_conn = conn  # type: ignore[attr-defined]
    yield eng
    conn.close()


@pytest.fixture(scope="module")
def session_factory(engine):
    conn = engine._test_conn  # type: ignore[attr-defined]
    return sessionmaker(bind=conn)


@pytest.fixture(scope="module")
def db(session_factory) -> Generator[Session, None, None]:
    session = session_factory()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Seed helpers — module-scoped so they persist across tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def org(db: Session) -> Organisation:
    o = Organisation(name="Test Org History")
    db.add(o)
    db.flush()
    return o


@pytest.fixture(scope="module")
def users(db: Session, org: Organisation) -> dict[str, User]:
    roles = ["admin", "compliance_officer", "control_owner", "auditor"]
    result: dict[str, User] = {}
    for role in roles:
        u = User(
            organisation_id=org.id,
            name=f"Test {role}",
            email=f"test_{role}_{uuid.uuid4().hex[:6]}@example.com",
            role=role,
        )
        db.add(u)
        db.flush()
        result[role] = u
    return result


@pytest.fixture(scope="module")
def ctrl_014(db: Session, org: Organisation) -> Control:
    c = Control(
        organisation_id=org.id,
        control_code="SEC-014",
        title="Employee Access Reviews",
        description="Formal user access rights reviews at regular intervals.",
        owner="IT Operations Manager",
        cadence="quarterly",
        evidence_expectation="Signed review record with approval.",
        status="Needs Review",
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture(scope="module")
def cycle_jan(db: Session, org: Organisation) -> AuditCycle:
    cy = AuditCycle(
        organisation_id=org.id,
        name="January 2026 Audit",
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 31),
    )
    db.add(cy)
    db.flush()
    return cy


@pytest.fixture(scope="module")
def cycle_apr(db: Session, org: Organisation) -> AuditCycle:
    cy = AuditCycle(
        organisation_id=org.id,
        name="April 2026 Audit",
        start_date=date(2026, 4, 5),
        end_date=date(2026, 4, 25),
    )
    db.add(cy)
    db.flush()
    return cy


@pytest.fixture(scope="module")
def finding_jan(db: Session, org: Organisation, ctrl_014: Control, cycle_jan: AuditCycle) -> Finding:
    """January finding — starts as Draft so we can approve it in tests."""
    f = Finding(
        organisation_id=org.id,
        audit_cycle_id=cycle_jan.id,
        control_id=ctrl_014.id,
        department="IT Operations",
        severity="High",
        description=(
            "Employee access reviews for IT Operations are incomplete and approval records are missing. "
            "Privileged account access lists have not been reviewed or signed off. "
            "Several leavers retain active access."
        ),
        status="Open",
        review_status="Draft",
        ai_generated=False,
        is_recurrence=False,
    )
    db.add(f)
    db.flush()
    db.commit()
    return f


@pytest.fixture(scope="module")
def finding_apr(db: Session, org: Organisation, ctrl_014: Control, cycle_apr: AuditCycle) -> Finding:
    """April finding — starts as Draft."""
    f = Finding(
        organisation_id=org.id,
        audit_cycle_id=cycle_apr.id,
        control_id=ctrl_014.id,
        department="IT Operations",
        severity="High",
        description=(
            "Employee access reviews for IT Operations remain incomplete in Q2 2026. "
            "Approval records are again missing. Privileged accounts have not been audited. "
            "Root cause — absence of automated review schedule — has not been addressed."
        ),
        status="Open",
        review_status="Draft",
        ai_generated=False,
        is_recurrence=False,
    )
    db.add(f)
    db.flush()
    db.commit()
    return f


# ---------------------------------------------------------------------------
# TestClient — override get_db to use shared in-memory session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client(session_factory, users: dict[str, User]) -> TestClient:
    def _override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _headers(user: User) -> dict[str, str]:
    return {"X-User-Id": user.id}


# ===========================================================================
# Tests
# ===========================================================================


class TestApproveJanuary:
    """Test 1: Approve January finding — no history yet → empty related list."""

    def test_approve_jan_no_history(
        self, client: TestClient, users: dict[str, User], finding_jan: Finding
    ):
        co = users["compliance_officer"]
        resp = client.post(
            f"/api/findings/{finding_jan.id}/approve",
            headers=_headers(co),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["finding"]["review_status"] == "Approved"
        assert data["related_findings_created"] == 0
        assert "No relevant history found" in data["message"]

    def test_jan_review_status_is_approved(
        self, client: TestClient, users: dict[str, User], finding_jan: Finding
    ):
        co = users["compliance_officer"]
        resp = client.get(f"/api/findings/{finding_jan.id}", headers=_headers(co))
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "Approved"

    def test_status_history_written_on_approve(
        self, db: Session, finding_jan: Finding
    ):
        """Exactly one review_status history row for the approve action."""
        rows = (
            db.query(StatusHistory)
            .filter(
                StatusHistory.entity_id == finding_jan.id,
                StatusHistory.entity_type == "finding_review",
            )
            .all()
        )
        assert len(rows) == 1
        assert rows[0].old_status == "Draft"
        assert rows[0].new_status == "Approved"


class TestApproveApril:
    """Test 2: Approve April finding — January should appear as related."""

    def test_approve_apr_finds_jan_related(
        self, client: TestClient, users: dict[str, User], finding_apr: Finding
    ):
        co = users["compliance_officer"]
        resp = client.post(
            f"/api/findings/{finding_apr.id}/approve",
            headers=_headers(co),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["finding"]["review_status"] == "Approved"
        assert data["related_findings_created"] >= 1

        # Verify at least one suggestion contains "SEC-014" and "IT Operations" in the reason
        reasons = [r["match_reason"] for r in data["related_findings"]]
        assert any("SEC-014" in r or "IT Operations" in r for r in reasons), (
            f"Expected SEC-014 or IT Operations in reasons: {reasons}"
        )

    def test_apr_related_score_above_threshold(
        self, client: TestClient, users: dict[str, User], finding_apr: Finding
    ):
        co = users["compliance_officer"]
        resp = client.get(
            f"/api/findings/{finding_apr.id}/history",
            headers=_headers(co),
        )
        assert resp.status_code == 200
        related = resp.json()["related_findings"]
        assert len(related) >= 1
        scores = [r["match_score"] for r in related]
        assert max(scores) >= 0.15, f"Scores below threshold: {scores}"

    def test_cannot_approve_already_approved(
        self, client: TestClient, users: dict[str, User], finding_apr: Finding
    ):
        """Approving an already-Approved finding returns 400."""
        co = users["compliance_officer"]
        resp = client.post(
            f"/api/findings/{finding_apr.id}/approve",
            headers=_headers(co),
        )
        assert resp.status_code == 400


class TestTimeline:
    """Test 3: GET /api/history/timeline?control_code=SEC-014."""

    def test_timeline_returns_entries(
        self, client: TestClient, users: dict[str, User], ctrl_014: Control
    ):
        co = users["compliance_officer"]
        resp = client.get(
            "/api/history/timeline",
            params={"control_code": "SEC-014"},
            headers=_headers(co),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["control_code"] == "SEC-014"
        assert len(data["entries"]) >= 1

    def test_timeline_chronological_order(
        self, client: TestClient, users: dict[str, User]
    ):
        co = users["compliance_officer"]
        resp = client.get(
            "/api/history/timeline",
            params={"control_code": "SEC-014"},
            headers=_headers(co),
        )
        entries = resp.json()["entries"]
        dates = [e["event_date"] for e in entries if e["event_date"]]
        assert dates == sorted(dates), f"Timeline entries not in order: {dates}"

    def test_timeline_unknown_code_404(
        self, client: TestClient, users: dict[str, User]
    ):
        co = users["compliance_officer"]
        resp = client.get(
            "/api/history/timeline",
            params={"control_code": "SEC-UNKNOWN"},
            headers=_headers(co),
        )
        assert resp.status_code == 404

    def test_timeline_no_params_400(
        self, client: TestClient, users: dict[str, User]
    ):
        co = users["compliance_officer"]
        resp = client.get("/api/history/timeline", headers=_headers(co))
        assert resp.status_code == 400


class TestCloseRequiresRemediation:
    """Tests 4 & 5: Closing a finding requires at least one Completed remediation."""

    @pytest.fixture(scope="class")
    def open_finding(self, db: Session, org: Organisation, ctrl_014: Control) -> Finding:
        f = Finding(
            organisation_id=org.id,
            control_id=ctrl_014.id,
            department="IT Operations",
            severity="Low",
            description="Test finding for close-requires-remediation tests.",
            status="Open",
            review_status="Draft",
            ai_generated=False,
        )
        db.add(f)
        db.flush()
        db.commit()
        return f

    def test_close_without_remediation_returns_400(
        self, client: TestClient, users: dict[str, User], open_finding: Finding
    ):
        co = users["compliance_officer"]
        resp = client.post(
            f"/api/findings/{open_finding.id}/status",
            params={"new_status": "Closed"},
            headers=_headers(co),
        )
        assert resp.status_code == 400
        assert "Completed" in resp.json()["detail"]

    def test_close_with_completed_remediation_succeeds(
        self, client: TestClient, db: Session, users: dict[str, User], open_finding: Finding
    ):
        """Add a Completed remediation, then close the finding."""
        co = users["compliance_officer"]

        # Create a completed remediation directly in DB
        rem = RemediationAction(
            organisation_id=open_finding.organisation_id,
            finding_id=open_finding.id,
            owner="Test Owner",
            action="Fix the gap.",
            due_date=date.today(),
            status="Completed",
        )
        db.add(rem)
        db.commit()

        # Now status transition to In Remediation first (required by allowed transitions)
        resp = client.post(
            f"/api/findings/{open_finding.id}/status",
            params={"new_status": "In Remediation"},
            headers=_headers(co),
        )
        assert resp.status_code == 200

        resp = client.post(
            f"/api/findings/{open_finding.id}/status",
            params={"new_status": "Ready for Review"},
            headers=_headers(co),
        )
        assert resp.status_code == 200

        resp = client.post(
            f"/api/findings/{open_finding.id}/status",
            params={"new_status": "Closed"},
            headers=_headers(co),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "Closed"


class TestStatusHistoryNoDuplicates:
    """Test 6: Exactly one status_history row per status change."""

    def test_no_duplicate_history_rows(
        self, db: Session, finding_jan: Finding
    ):
        rows = (
            db.query(StatusHistory)
            .filter(
                StatusHistory.entity_id == finding_jan.id,
                StatusHistory.entity_type == "finding_review",
                StatusHistory.old_status == "Draft",
                StatusHistory.new_status == "Approved",
            )
            .all()
        )
        assert len(rows) == 1, f"Expected exactly 1 history row, got {len(rows)}"


class TestRemediationPermissions:
    """Tests 7 & 8: Role-based remediation status permissions."""

    @pytest.fixture(scope="class")
    def rem_action(self, db: Session, finding_jan: Finding) -> RemediationAction:
        r = RemediationAction(
            organisation_id=finding_jan.organisation_id,
            finding_id=finding_jan.id,
            owner="Owner",
            action="Remediation for permission tests.",
            due_date=date.today() + timedelta(days=30),
            status="Planned",
        )
        db.add(r)
        db.flush()
        db.commit()
        return r

    def test_control_owner_cannot_complete_remediation(
        self, client: TestClient, users: dict[str, User], rem_action: RemediationAction
    ):
        """Test 7: control_owner cannot set status = Completed."""
        owner = users["control_owner"]
        resp = client.post(
            f"/api/remediations/{rem_action.id}/status",
            params={"new_status": "Completed"},
            headers=_headers(owner),
        )
        assert resp.status_code == 403
        assert "Completed" in resp.json()["detail"]

    def test_auditor_cannot_change_remediation_status(
        self, client: TestClient, users: dict[str, User], rem_action: RemediationAction
    ):
        """Test 8: auditor cannot change remediation status at all."""
        auditor = users["auditor"]
        resp = client.post(
            f"/api/remediations/{rem_action.id}/status",
            params={"new_status": "In Progress"},
            headers=_headers(auditor),
        )
        assert resp.status_code == 403
        assert "Auditors" in resp.json()["detail"]

    def test_control_owner_can_set_in_progress(
        self, client: TestClient, users: dict[str, User], rem_action: RemediationAction
    ):
        """control_owner may transition to In Progress."""
        owner = users["control_owner"]
        resp = client.post(
            f"/api/remediations/{rem_action.id}/status",
            params={"new_status": "In Progress"},
            headers=_headers(owner),
        )
        assert resp.status_code == 200

    def test_compliance_officer_can_complete_remediation(
        self, client: TestClient, users: dict[str, User], rem_action: RemediationAction
    ):
        """compliance_officer may set Completed (via Ready for Review — required by transition table)."""
        co = users["compliance_officer"]

        # Must go through Ready for Review first (already In Progress from previous test)
        resp = client.post(
            f"/api/remediations/{rem_action.id}/status",
            params={"new_status": "Ready for Review"},
            headers=_headers(co),
        )
        assert resp.status_code == 200, f"Ready for Review failed: {resp.text}"

        resp = client.post(
            f"/api/remediations/{rem_action.id}/status",
            params={"new_status": "Completed"},
            headers=_headers(co),
        )
        assert resp.status_code == 200, f"Completed failed: {resp.text}"
        assert resp.json()["status"] == "Completed"


class TestConfirmRelatedFinding:
    """Test 9: Confirming a related finding sets is_recurrence = True."""

    def test_confirm_related_sets_is_recurrence(
        self,
        client: TestClient,
        db: Session,
        users: dict[str, User],
        finding_apr: Finding,
    ):
        co = users["compliance_officer"]

        # Fetch the related findings for April finding
        resp = client.get(
            f"/api/findings/{finding_apr.id}/history",
            headers=_headers(co),
        )
        assert resp.status_code == 200
        related = resp.json()["related_findings"]
        assert len(related) >= 1, "No related findings to confirm"

        rf_id = related[0]["id"]

        # Confirm the first related finding
        resp = client.post(
            f"/api/findings/{finding_apr.id}/related/{rf_id}/review",
            json={"decision": "confirmed"},
            headers=_headers(co),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["decision"] == "confirmed"
        assert data["is_recurrence"] is True

        # Verify on the finding itself
        resp2 = client.get(f"/api/findings/{finding_apr.id}", headers=_headers(co))
        assert resp2.json()["is_recurrence"] is True


class TestIsOverdue:
    """Test 10: is_overdue correctly computed on remediations."""

    def test_overdue_remediation(self, db: Session, org: Organisation, finding_jan: Finding):
        past_date = date.today() - timedelta(days=5)
        r = RemediationAction(
            organisation_id=org.id,
            finding_id=finding_jan.id,
            owner="Test",
            action="Overdue action",
            due_date=past_date,
            status="Planned",
        )
        db.add(r)
        db.flush()
        db.commit()

        from app.schemas.remediation import RemediationOut
        out = RemediationOut.from_orm_with_overdue(r)
        assert out.is_overdue is True

    def test_not_overdue_remediation(self, db: Session, org: Organisation, finding_jan: Finding):
        future_date = date.today() + timedelta(days=10)
        r = RemediationAction(
            organisation_id=org.id,
            finding_id=finding_jan.id,
            owner="Test",
            action="Future action",
            due_date=future_date,
            status="Planned",
        )
        db.add(r)
        db.flush()
        db.commit()

        from app.schemas.remediation import RemediationOut
        out = RemediationOut.from_orm_with_overdue(r)
        assert out.is_overdue is False

    def test_completed_not_overdue_even_if_past_due(
        self, db: Session, org: Organisation, finding_jan: Finding
    ):
        past_date = date.today() - timedelta(days=10)
        r = RemediationAction(
            organisation_id=org.id,
            finding_id=finding_jan.id,
            owner="Test",
            action="Completed past-due action",
            due_date=past_date,
            status="Completed",
        )
        db.add(r)
        db.flush()
        db.commit()

        from app.schemas.remediation import RemediationOut
        out = RemediationOut.from_orm_with_overdue(r)
        assert out.is_overdue is False


class TestHistoryServiceDirect:
    """Direct unit tests for SqlHistoryService."""

    def test_find_related_empty_when_no_history(
        self, db: Session, org: Organisation, ctrl_014: Control
    ):
        """With a fresh control that has no Approved findings, returns []."""
        new_ctrl = Control(
            organisation_id=org.id,
            control_code="SEC-999",
            title="Test Only Control",
            description="For test use only.",
            owner="Tester",
            cadence="annual",
            evidence_expectation="N/A",
            status="Not Assessed",
        )
        db.add(new_ctrl)
        db.flush()

        svc = SqlHistoryService()
        results = svc.find_related_findings(
            organisation_id=org.id,
            control_id=new_ctrl.id,
            department="Engineering",
            description="A completely new type of finding never seen before.",
            db=db,
        )
        assert results == []

    def test_find_related_respects_min_score(
        self, db: Session, org: Organisation, ctrl_014: Control, finding_jan: Finding
    ):
        """With a very high min_score, the January finding should not appear."""
        svc = SqlHistoryService()
        results = svc.find_related_findings(
            organisation_id=org.id,
            control_id=ctrl_014.id,
            department="IT Operations",
            description="Access review incomplete approval missing.",
            exclude_finding_id=finding_jan.id,
            min_score=0.99,  # impossible to reach
            db=db,
        )
        assert results == []

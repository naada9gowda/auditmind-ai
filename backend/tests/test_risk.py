"""
tests/test_risk.py — Acceptance tests for AuditMind AI Risk Scoring and Analytics.

Test Matrix:
1. score_finding returns score >= 3 for a High severity finding
2. High severity + recurrence + overdue = High level (score >= 7)
3. Low severity + no recurrence + no overdue = Low level
4. score changes after adding a confirmed related finding
5. Disclaimer string present in every scored result
6. GET /api/analytics/risks returns 200 with disclaimer field
7. GET /api/analytics/summary returns all required keys
8. Tenant isolation: org_b cannot see org_a risk data
"""

from __future__ import annotations

import os
import uuid
from datetime import date, timedelta
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_PROVIDER"] = "none"

from app.database import Base, get_db
from app.main import app
from app.models.audit_cycle import AuditCycle
from app.models.control import Control
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.organisation import Organisation
from app.models.related_finding import RelatedFinding
from app.models.remediation import RemediationAction
from app.models.user import User
from app.risk.config import DISCLAIMER
from app.risk.scoring import score_all_open_findings, score_finding


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    conn = eng.connect()
    Base.metadata.create_all(bind=conn)
    eng._test_conn = conn
    yield eng
    conn.close()


@pytest.fixture(scope="module")
def session_factory(engine):
    conn = engine._test_conn
    return sessionmaker(bind=conn)


@pytest.fixture(scope="module")
def db(session_factory) -> Generator[Session, None, None]:
    session = session_factory()
    yield session
    session.close()


@pytest.fixture(scope="module")
def client(session_factory) -> Generator[TestClient, None, None]:
    def _override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def org_a(db: Session) -> Organisation:
    o = Organisation(name="Risk Org A")
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@pytest.fixture(scope="module")
def org_b(db: Session) -> Organisation:
    o = Organisation(name="Risk Org B")
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@pytest.fixture(scope="module")
def user_a(db: Session, org_a: Organisation) -> User:
    u = User(organisation_id=org_a.id, name="User A", email=f"usera_{uuid.uuid4().hex[:6]}@example.com", role="compliance_officer")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture(scope="module")
def user_b(db: Session, org_b: Organisation) -> User:
    u = User(organisation_id=org_b.id, name="User B", email=f"userb_{uuid.uuid4().hex[:6]}@example.com", role="compliance_officer")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture(scope="module")
def control_a(db: Session, org_a: Organisation) -> Control:
    c = Control(
        organisation_id=org_a.id,
        control_code="SEC-014",
        title="Access Reviews",
        status="Needs Review",
        cadence="quarterly",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture(scope="module")
def cycle_a(db: Session, org_a: Organisation) -> AuditCycle:
    cy = AuditCycle(
        organisation_id=org_a.id,
        name="Q1 2026 Audit",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
    )
    db.add(cy)
    db.commit()
    db.refresh(cy)
    return cy


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_1_score_finding_high_severity(db: Session, org_a: Organisation, control_a: Control):
    """1. score_finding returns score >= 3 for a High severity finding."""
    finding = Finding(
        organisation_id=org_a.id,
        control_id=control_a.id,
        description="High severity access review failure.",
        severity="High",
        status="Open",
        review_status="Approved",
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)

    result = score_finding(finding, db, org_a.id)
    assert result["score"] >= 3.0
    sev_comp = next((c for c in result["components"] if c["name"] == "severity"), None)
    assert sev_comp is not None
    assert sev_comp["points"] == 3.0


def test_2_high_recurrence_overdue_yields_high_level(
    db: Session, org_a: Organisation, control_a: Control
):
    """2. High severity + recurrence + overdue = High level (score >= 7)."""
    finding = Finding(
        organisation_id=org_a.id,
        control_id=control_a.id,
        description="Repeated privileged access review gaps.",
        severity="High",
        status="Open",
        review_status="Approved",
        is_recurrence=True,
    )
    db.add(finding)
    db.flush()

    # Add 2 confirmed related findings (2 pts)
    f_old1 = Finding(organisation_id=org_a.id, description="Old finding 1", severity="Medium")
    f_old2 = Finding(organisation_id=org_a.id, description="Old finding 2", severity="Medium")
    db.add_all([f_old1, f_old2])
    db.flush()

    rf1 = RelatedFinding(
        organisation_id=org_a.id,
        finding_id=finding.id,
        related_finding_id=f_old1.id,
        reviewed_by="test_reviewer",
    )
    rf2 = RelatedFinding(
        organisation_id=org_a.id,
        finding_id=finding.id,
        related_finding_id=f_old2.id,
        reviewed_by="test_reviewer",
    )
    db.add_all([rf1, rf2])

    # Add severe overdue remediation (>30 days overdue -> 2 pts)
    rem = RemediationAction(
        organisation_id=org_a.id,
        finding_id=finding.id,
        action="Revoke stale access accounts",
        due_date=date.today() - timedelta(days=45),
        status="In Progress",
    )
    db.add(rem)
    db.commit()
    db.refresh(finding)

    result = score_finding(finding, db, org_a.id)
    # Severity (3) + Recurrence (2) + Overdue (2) = 7 pts >= 7 -> High
    assert result["score"] >= 7.0
    assert result["level"] == "High"


def test_3_low_severity_no_recurrence_no_overdue(db: Session, org_a: Organisation, control_a: Control):
    """3. Low severity + no recurrence + no overdue = Low level."""
    finding = Finding(
        organisation_id=org_a.id,
        control_id=control_a.id,
        description="Minor documentation formatting issue.",
        severity="Low",
        status="Open",
        review_status="Approved",
        is_recurrence=False,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)

    result = score_finding(finding, db, org_a.id)
    assert result["score"] < 4.0
    assert result["level"] == "Low"


def test_4_score_changes_after_adding_confirmed_related_finding(
    db: Session, org_a: Organisation, control_a: Control
):
    """4. score changes after adding a confirmed related finding."""
    finding = Finding(
        organisation_id=org_a.id,
        control_id=control_a.id,
        description="Access review procedure not completed on time.",
        severity="Medium",
        status="Open",
        review_status="Approved",
        is_recurrence=False,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)

    score_before = score_finding(finding, db, org_a.id)["score"]

    # Add earlier finding and confirmed relation
    f_prior = Finding(organisation_id=org_a.id, description="Prior access failure", severity="Medium")
    db.add(f_prior)
    db.flush()

    rf = RelatedFinding(
        organisation_id=org_a.id,
        finding_id=finding.id,
        related_finding_id=f_prior.id,
        reviewed_by="reviewer_123",
    )
    db.add(rf)
    finding.is_recurrence = True
    db.commit()
    db.refresh(finding)

    score_after = score_finding(finding, db, org_a.id)["score"]
    assert score_after > score_before


def test_5_disclaimer_present_in_every_scored_result(
    db: Session, org_a: Organisation, control_a: Control
):
    """5. Disclaimer string present in every scored result."""
    finding = Finding(
        organisation_id=org_a.id,
        control_id=control_a.id,
        description="Evaluating disclaimer inclusion.",
        severity="Medium",
        status="Open",
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)

    single = score_finding(finding, db, org_a.id)
    assert single["disclaimer"] == DISCLAIMER

    all_scored = score_all_open_findings(db, org_a.id)
    assert len(all_scored) > 0
    for s in all_scored:
        assert s["disclaimer"] == DISCLAIMER


def test_6_api_analytics_risks_returns_200_with_disclaimer(client: TestClient, user_a: User):
    """6. GET /api/analytics/risks returns 200 with disclaimer field."""
    res = client.get("/api/analytics/risks", headers={"X-User-Id": user_a.id})
    assert res.status_code == 200
    data = res.json()
    assert "disclaimer" in data
    assert data["disclaimer"] == DISCLAIMER
    assert "risks" in data
    assert isinstance(data["risks"], list)
    if data["risks"]:
        first = data["risks"][0]
        assert "finding_id" in first
        assert "score" in first
        assert "level" in first
        assert "components" in first
        assert "related_finding_ids" in first


def test_7_api_analytics_summary_returns_all_required_keys(client: TestClient, user_a: User):
    """7. GET /api/analytics/summary returns all required keys."""
    res = client.get("/api/analytics/summary", headers={"X-User-Id": user_a.id})
    assert res.status_code == 200
    data = res.json()

    required_keys = [
        "control_status_counts",
        "open_findings_by_severity",
        "overdue_actions_count",
        "recurring_findings_count",
        "findings_per_dept_per_cycle",
        "risk_by_control",
        "disclaimer",
    ]
    for key in required_keys:
        assert key in data, f"Missing required key '{key}' in summary"

    assert data["disclaimer"] == DISCLAIMER
    assert isinstance(data["control_status_counts"], dict)
    assert isinstance(data["open_findings_by_severity"], dict)
    assert isinstance(data["overdue_actions_count"], int)
    assert isinstance(data["recurring_findings_count"], int)
    assert isinstance(data["findings_per_dept_per_cycle"], list)
    assert isinstance(data["risk_by_control"], list)


def test_8_tenant_isolation_org_b_cannot_see_org_a_data(
    client: TestClient, db: Session, org_a: Organisation, org_b: Organisation, user_a: User, user_b: User
):
    """8. Tenant isolation: org_b cannot see org_a risk data."""
    # Org A has findings created in prior tests
    res_a = client.get("/api/analytics/risks", headers={"X-User-Id": user_a.id})
    assert res_a.status_code == 200
    risks_a = res_a.json()["risks"]
    assert len(risks_a) > 0
    org_a_finding_ids = {r["finding_id"] for r in risks_a}

    # Org B queries risks — must be empty or contain only Org B findings
    res_b = client.get("/api/analytics/risks", headers={"X-User-Id": user_b.id})
    assert res_b.status_code == 200
    risks_b = res_b.json()["risks"]
    org_b_finding_ids = {r["finding_id"] for r in risks_b}

    # Ensure complete disjointness
    assert org_a_finding_ids.isdisjoint(org_b_finding_ids)

    # Summary checks
    summary_b = client.get("/api/analytics/summary", headers={"X-User-Id": user_b.id}).json()
    assert summary_b["overdue_actions_count"] == 0
    assert summary_b["recurring_findings_count"] == 0

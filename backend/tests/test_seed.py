"""
tests/test_seed.py

Verifies that:
  - The seed script creates exactly 1 organisation, 4 users, 20 controls.
  - Re-running seed is idempotent (no duplicates).
  - SEC-014 has the required fields.
"""

from __future__ import annotations

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("LLM_PROVIDER", "none")

from app.database import Base            # noqa: E402
from app.models.organisation import Organisation  # noqa: E402
from app.models.user import User                 # noqa: E402
from app.models.control import Control           # noqa: E402
from app.seed import seed                        # noqa: E402


def _make_in_memory_setup():
    """Return (engine, session_factory) for a fresh in-memory SQLite DB."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, factory


@pytest.fixture()
def seed_session() -> Session:
    """
    Runs seed() against a fresh in-memory DB and yields an open session.
    seed() is passed the engine and session_factory directly — no monkeypatching.
    """
    engine, factory = _make_in_memory_setup()
    seed(session_factory=factory, bind_engine=engine)   # first run

    session = factory()
    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def seed_session_double(seed_session: Session) -> Session:
    """Runs seed a second time (idempotency check) and returns the same session."""
    # Retrieve the engine from the existing session's bind
    engine = seed_session.bind
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    seed(session_factory=factory, bind_engine=engine)   # second run — no-op
    return seed_session


class TestSeedCreatesExpectedRecords:
    def test_one_organisation(self, seed_session: Session):
        orgs = seed_session.query(Organisation).all()
        assert len(orgs) == 1
        assert orgs[0].name == "ABC Technologies"

    def test_four_users(self, seed_session: Session):
        users = seed_session.query(User).all()
        assert len(users) == 4
        roles = {u.role for u in users}
        assert roles == {"admin", "compliance_officer", "control_owner", "auditor"}

    def test_twenty_controls(self, seed_session: Session):
        controls = seed_session.query(Control).all()
        assert len(controls) == 20

    def test_all_control_codes_unique(self, seed_session: Session):
        codes = [c.control_code for c in seed_session.query(Control).all()]
        assert len(codes) == len(set(codes))

    def test_sec014_fields(self, seed_session: Session):
        sec014 = seed_session.query(Control).filter_by(control_code="SEC-014").first()
        assert sec014 is not None, "SEC-014 must exist in the seed data"
        assert "access" in sec014.title.lower(), "SEC-014 title must mention 'access'"
        assert sec014.owner == "IT Operations Manager"
        assert sec014.cadence == "quarterly"
        assert sec014.evidence_expectation is not None
        assert len(sec014.evidence_expectation) > 10

    def test_all_users_belong_to_org(self, seed_session: Session):
        org = seed_session.query(Organisation).first()
        users = seed_session.query(User).all()
        for u in users:
            assert u.organisation_id == org.id

    def test_all_controls_belong_to_org(self, seed_session: Session):
        org = seed_session.query(Organisation).first()
        controls = seed_session.query(Control).all()
        for c in controls:
            assert c.organisation_id == org.id


class TestSeedIsIdempotent:
    def test_still_one_org_after_double_seed(self, seed_session_double: Session):
        orgs = seed_session_double.query(Organisation).all()
        assert len(orgs) == 1

    def test_still_four_users_after_double_seed(self, seed_session_double: Session):
        users = seed_session_double.query(User).all()
        assert len(users) == 4

    def test_still_twenty_controls_after_double_seed(self, seed_session_double: Session):
        controls = seed_session_double.query(Control).all()
        assert len(controls) == 20

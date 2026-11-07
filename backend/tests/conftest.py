"""
tests/conftest.py — Shared pytest fixtures.

Uses an in-memory SQLite database so tests are fast and isolated.
Each test gets a fresh database.
"""

from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Point at an in-memory SQLite before importing anything that touches the DB
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LLM_PROVIDER"] = "none"

from app.database import Base, get_db  # noqa: E402
from app.main import app               # noqa: E402
from app.models.organisation import Organisation  # noqa: E402
from app.models.user import User                 # noqa: E402
from app.models.control import Control           # noqa: E402


def _make_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )


@pytest.fixture()
def db() -> Session:
    """Yields a fresh in-memory database session for each test."""
    engine = _make_engine()
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def two_orgs(db: Session):
    """
    Creates two organisations with one user each.
    Returns (org_a, user_a, org_b, user_b).
    """
    org_a = Organisation(name="Org Alpha")
    org_b = Organisation(name="Org Beta")
    db.add_all([org_a, org_b])
    db.flush()

    user_a = User(organisation_id=org_a.id, name="Alice", email="alice@alpha.example", role="admin")
    user_b = User(organisation_id=org_b.id, name="Bob", email="bob@beta.example", role="admin")
    db.add_all([user_a, user_b])
    db.commit()

    return org_a, user_a, org_b, user_b


@pytest.fixture()
def client(db: Session):
    """
    Returns a TestClient wired to the in-memory database.
    The DB override replaces the real get_db dependency.
    """
    engine = _make_engine()
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c, TestingSession
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

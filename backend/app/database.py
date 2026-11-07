"""
database.py — SQLAlchemy engine, session factory, and declarative base.

DATABASE_URL is read from the environment (falls back to a local SQLite file).
Call `init_db()` once at startup to create all tables.
"""

from __future__ import annotations

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./auditmind.db")

# SQLite requires check_same_thread=False for multi-threaded use in FastAPI
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,          # set True for SQL debug output
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def init_db() -> None:
    """Create all tables (no-op if they already exist)."""
    from app.models import all_models  # noqa: F401 — ensures models are registered
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
main.py — FastAPI application entry point for AuditMind AI.

Start with:
    uvicorn app.main:app --reload --port 8000

API docs: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db

# Configure root logger
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create all DB tables on startup (no-op if they already exist)."""
    logger.info("AuditMind AI starting — initialising database…")
    init_db()
    logger.info("Database ready.")
    yield
    logger.info("AuditMind AI shutting down.")


app = FastAPI(
    title="AuditMind AI",
    description=(
        "AI-assisted compliance and continuous audit management. "
        "All AI suggestions are DRAFT until a human reviewer approves them."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
from app.api import analytics, assistant, audit_cycles, controls, documents, evidence, findings, history, remediation, users  # noqa: E402

app.include_router(users.router, prefix="/api")
app.include_router(controls.router, prefix="/api")
app.include_router(audit_cycles.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(remediation.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")



# ── Health & User Alias ────────────────────────────────────────────────────────
@app.get("/api/health", tags=["meta"], summary="Health check")
def health() -> dict:
    """Returns 200 OK when the service is running."""
    return {"status": "ok", "service": "AuditMind AI"}


from app.auth import _get_current_user
from app.models.user import User
from app.schemas.user import UserOut

@app.get("/api/me", response_model=UserOut, tags=["users"], summary="Get current authenticated user")
def me(user: User = Depends(_get_current_user)) -> UserOut:
    return user  # type: ignore[return-value]


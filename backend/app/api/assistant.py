"""
api/assistant.py — AI Compliance Assistant Chat endpoint.

Supports conversational audit intelligence with deterministic fallback
when LLM_PROVIDER=none or upon LLM provider failure.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.assistant import (
    ChatRequest,
    ChatResponse,
    check_rate_limit,
    deterministic_answer,
    run_llm_assistant,
)
from app.auth import _get_current_user
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=ChatResponse, summary="Chat with AI compliance assistant")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
) -> ChatResponse:
    """
    Assistant chat endpoint.
    Applies in-memory rate limiting (20 requests per minute per user).
    Falls back deterministically if LLM is unavailable or LLM_PROVIDER=none.
    """
    # 1. Rate limit check
    check_rate_limit(user.id)

    # 2. Check provider
    provider = os.getenv("LLM_PROVIDER", "none").lower()
    if provider == "none":
        return deterministic_answer(request, db, user, model_unavailable=False)

    try:
        return run_llm_assistant(request, db, user)
    except Exception as exc:
        logger.warning("LLM assistant invocation failed: %s; falling back to deterministic answer.", exc)
        return deterministic_answer(request, db, user, model_unavailable=True)

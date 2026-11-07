"""
config.py — Application settings read from environment variables.

All secrets and paths come from env; this module must never hardcode them.
"""

from __future__ import annotations

import os
from pathlib import Path


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


# ── File storage ───────────────────────────────────────────────────────────────
UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "./uploads"))
MAX_UPLOAD_MB: int = _int_env("MAX_UPLOAD_MB", 20)

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "none").lower()

# ── Allowed upload types ───────────────────────────────────────────────────────
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".txt"})
ALLOWED_DOC_TYPES: frozenset[str] = frozenset({"policy", "audit_report", "evidence"})

# PDF magic bytes
PDF_MAGIC: bytes = b"%PDF"

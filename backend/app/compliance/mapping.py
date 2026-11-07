"""
compliance/mapping.py — Control mapping service.

Given a processed document, finds candidate controls using three layers:
  (a) Explicit control ID match in text   → highest confidence (0.95)
  (b) Keyword/phrase overlap scoring      → TF-IDF-style weighted scoring
  (c) Optional LLM classification         → only when LLM_PROVIDER != none

Returns a list of ControlMatch dataclasses: control_id (DB uuid), confidence,
matched_terms, page_number, and excerpt.

Security: document text is treated as untrusted DATA — it is never interpreted
as instructions. When passed to the LLM it is wrapped in delimiters.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Control-code regex  (e.g. SEC-014, ISO-001, ACL-003)
# ---------------------------------------------------------------------------
_RE_CONTROL_CODE = re.compile(r"\b([A-Z]{2,5}-\d{3,4})\b")

# ---------------------------------------------------------------------------
# Cadence → window (days) used by verifier (kept here as shared truth)
# ---------------------------------------------------------------------------
CADENCE_DAYS: dict[str, int] = {
    "daily": 1,
    "weekly": 7,
    "monthly": 31,
    "quarterly": 100,
    "biannual": 185,
    "semi-annual": 185,
    "annual": 366,
    "yearly": 366,
}


@dataclass
class ControlMatch:
    """A candidate control matched to a document."""
    control_id: str            # DB UUID of the control
    control_code: str          # e.g. SEC-014
    confidence: float          # 0.0 – 1.0
    matched_terms: list[str] = field(default_factory=list)
    page_number: int | None = None
    excerpt: str | None = None
    match_method: str = "keyword"   # explicit | keyword | llm


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Lower-case word tokenise; strip punctuation."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _make_control_keywords(control: Any) -> list[str]:
    """
    Build a de-duplicated keyword list from a control's title + description.
    Stop-words are excluded to reduce noise.
    """
    _STOP = {
        "a", "an", "the", "of", "in", "and", "or", "to", "is", "are", "be",
        "for", "with", "that", "this", "as", "by", "on", "at", "from", "it",
        "its", "has", "have", "been", "not", "shall", "must", "should", "will",
        "may", "can", "all", "any", "each", "their", "which", "that",
    }
    raw = f"{control.title or ''} {control.description or ''}"
    tokens = _tokenize(raw)
    seen: set[str] = set()
    kws: list[str] = []
    for t in tokens:
        if t not in _STOP and len(t) > 2 and t not in seen:
            kws.append(t)
            seen.add(t)
    return kws


def _score_page(page_tokens: list[str], keywords: list[str]) -> tuple[float, list[str]]:
    """
    TF-IDF-style score for one page against a keyword list.

    Strategy:
      - For each keyword that appears in page_tokens, award score =
        1 + log(1 + count_in_page) so repeated mentions boost the score.
      - Normalise by number of keywords so longer keyword lists don't
        automatically win.
      - Cap at 1.0.
    """
    page_set = set(page_tokens)
    total = max(len(keywords), 1)
    matched: list[str] = []
    raw_score = 0.0
    for kw in keywords:
        count = page_tokens.count(kw)
        if count > 0:
            matched.append(kw)
            raw_score += 1.0 + math.log(1.0 + count)
    # Normalise: each keyword contributes max 1.0 so raw_score / total → 0..1 ish
    normalised = min(raw_score / (total * 2), 1.0)   # *2 dampens to keep below 1
    return normalised, matched


def _best_excerpt(page_text: str, terms: list[str], max_len: int = 300) -> str | None:
    """Find the sentence/snippet in page_text that contains the most terms."""
    if not terms:
        return None
    sentences = re.split(r"(?<=[.!?])\s+|\n", page_text)
    best: tuple[int, str] = (0, "")
    for s in sentences:
        s_low = s.lower()
        hits = sum(1 for t in terms if t in s_low)
        if hits > best[0]:
            best = (hits, s)
    text = best[1].strip()
    return (text[:max_len] + "…") if len(text) > max_len else text or None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def map_document_to_controls(
    *,
    pages: list[tuple[int, str]],      # (page_number, text) from extractor
    controls: list[Any],               # list of Control ORM objects
    llm_provider: Any | None = None,   # LLMProvider instance or None
    min_keyword_confidence: float = 0.05,
) -> list[ControlMatch]:
    """
    Map a document's pages to candidate controls.

    Steps:
    1. Build an index: control_code → Control ORM object.
    2. For each page, scan for explicit control-code mentions → confidence 0.95.
    3. Score each (page, control) pair by keyword overlap → score in 0..1.
    4. Optionally call LLM for additional mappings; merge/update.
    5. Return one ControlMatch per (control, best_page), deduplicated.

    Returns list sorted by confidence descending.
    """
    if not pages or not controls:
        return []

    # Build lookup maps
    code_to_ctrl: dict[str, Any] = {c.control_code: c for c in controls}
    ctrl_keywords: dict[str, list[str]] = {
        c.control_code: _make_control_keywords(c) for c in controls
    }

    # Accumulator: control_code → best ControlMatch so far
    best_matches: dict[str, ControlMatch] = {}

    full_text_for_llm: list[str] = []

    for page_num, page_text in pages:
        full_text_for_llm.append(f"[Page {page_num}]\n{page_text}")
        page_tokens = _tokenize(page_text)

        # --- (a) Explicit control-code mentions ---
        explicit_codes = {m.group(1) for m in _RE_CONTROL_CODE.finditer(page_text)}
        for code in explicit_codes:
            ctrl = code_to_ctrl.get(code)
            if ctrl is None:
                continue
            excerpt = _best_excerpt(page_text, [code.lower()], 300) or page_text[:300]
            existing = best_matches.get(code)
            if existing is None or existing.confidence < 0.95:
                best_matches[code] = ControlMatch(
                    control_id=ctrl.id,
                    control_code=code,
                    confidence=0.95,
                    matched_terms=[code],
                    page_number=page_num,
                    excerpt=excerpt,
                    match_method="explicit",
                )

        # --- (b) Keyword scoring ---
        for ctrl in controls:
            code = ctrl.control_code
            keywords = ctrl_keywords.get(code, [])
            if not keywords:
                continue
            score, matched = _score_page(page_tokens, keywords)
            if score < min_keyword_confidence:
                continue
            existing = best_matches.get(code)
            if existing is None or (existing.match_method == "keyword" and existing.confidence < score):
                excerpt = _best_excerpt(page_text, matched, 300)
                best_matches[code] = ControlMatch(
                    control_id=ctrl.id,
                    control_code=code,
                    confidence=round(score, 4),
                    matched_terms=matched[:10],
                    page_number=page_num,
                    excerpt=excerpt,
                    match_method="keyword",
                )

    # --- (c) LLM enrichment (optional) ---
    if llm_provider is not None:
        try:
            combined_text = "\n\n".join(full_text_for_llm[:10])  # cap to avoid huge prompts
            ctrl_summaries = [
                {"code": c.control_code, "title": c.title, "description": (c.description or "")[:200]}
                for c in controls
            ]
            llm_result = llm_provider.classify_control_mappings(combined_text, ctrl_summaries)
            if llm_result:
                for m in llm_result.mappings:
                    ctrl = code_to_ctrl.get(m.control_code)
                    if ctrl is None:
                        continue
                    existing = best_matches.get(m.control_code)
                    # Only upgrade if LLM is more confident than current keyword match
                    if existing is None or (
                        existing.match_method not in ("explicit",) and existing.confidence < m.confidence
                    ):
                        best_matches[m.control_code] = ControlMatch(
                            control_id=ctrl.id,
                            control_code=m.control_code,
                            confidence=round(m.confidence, 4),
                            matched_terms=m.matched_terms,
                            page_number=m.page_number,
                            excerpt=m.excerpt,
                            match_method="llm",
                        )
        except Exception as exc:
            logger.warning("LLM control mapping step failed; using rule-based results only: %s", exc)

    # Sort by confidence descending
    return sorted(best_matches.values(), key=lambda m: m.confidence, reverse=True)

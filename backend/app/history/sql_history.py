"""
history/sql_history.py — SQLAlchemy implementation of HistoryService.

Scoring algorithm for find_related_findings:
  score = Σ(component weights), capped at 1.0

  Component             Weight  Condition
  ─────────────────     ──────  ──────────────────────────────────────
  control_id match       0.45   same control DB UUID
  department match       0.20   same department string
  keyword overlap        0–0.25 Jaccard similarity of description tokens
  time proximity         0–0.10 findings within 180 days of each other

Threshold default: 0.15 (configurable via min_score arg)

match_reason is composed in plain English from whichever components fired.
Example: "Same control SEC-014, same department IT Operations,
          3 shared keywords: access, review, incomplete"

Design rules:
- All queries filter by organisation_id.
- Findings from the same audit_cycle are excluded (exclude_cycle_id).
- The finding itself is excluded (exclude_finding_id).
- If nothing meets the threshold, returns [] — never fabricates.
- Only Approved findings are returned as history (Draft findings are not
  established records).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.history.interface import HistoryService
from app.history.schemas import (
    ControlTimeline,
    RelatedFindingResult,
    RemediationSummary,
    TimelineEntry,
)
from app.models.audit_cycle import AuditCycle
from app.models.control import Control
from app.models.finding import Finding
from app.models.remediation import RemediationAction
from app.models.status_history import StatusHistory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stop-words for keyword extraction
# ---------------------------------------------------------------------------
_STOP = frozenset({
    "a", "an", "the", "of", "in", "and", "or", "to", "is", "are", "be",
    "for", "with", "that", "this", "as", "by", "on", "at", "from", "it",
    "its", "has", "have", "been", "not", "shall", "must", "should", "will",
    "may", "can", "all", "any", "each", "their", "which", "was", "were",
    "no", "did", "does", "had", "but", "if", "into", "out", "so", "then",
    "than", "also", "been", "both", "during", "while", "after", "before",
})

_MAX_PROXIMITY_DAYS = 365   # older than this gets zero proximity credit


def _tokens(text: str | None) -> set[str]:
    """Lower-case word tokens, stop-words removed, length ≥ 3."""
    if not text:
        return set()
    return {
        w for w in re.findall(r"[a-z0-9]+", text.lower())
        if len(w) >= 3 and w not in _STOP
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _days_apart(f1: Finding, f2: Finding) -> int | None:
    """Return absolute days between two findings' creation proxies, or None."""
    # Use audit_cycle start dates if available, else None
    return None  # will be computed with cycle dates in the main loop


def _build_reason(
    *,
    control_match: bool,
    control_code: str | None,
    dept_match: bool,
    department: str | None,
    shared_tokens: set[str],
    days: int | None,
) -> str:
    """Compose a plain-English match reason."""
    parts: list[str] = []
    if control_match and control_code:
        parts.append(f"Same control {control_code}")
    if dept_match and department:
        parts.append(f"same department {department}")
    if shared_tokens:
        kw_list = ", ".join(sorted(shared_tokens)[:6])
        n = len(shared_tokens)
        parts.append(f"{n} shared keyword{'s' if n != 1 else ''}: {kw_list}")
    if days is not None and days <= _MAX_PROXIMITY_DAYS:
        parts.append(f"findings {days} days apart")
    if not parts:
        return "Keyword and content overlap detected."
    result = parts[0]
    if len(parts) > 1:
        result = result + ", " + ", ".join(parts[1:])
    return result + "."


class SqlHistoryService(HistoryService):
    """
    SQLAlchemy-backed implementation of HistoryService.

    Pass a live Session on each call (stateless — no session stored on self).
    """

    # Score component weights
    _W_CONTROL = 0.45
    _W_DEPT = 0.20
    _W_KEYWORD_MAX = 0.25
    _W_TIME_MAX = 0.10

    def find_related_findings(
        self,
        *,
        organisation_id: str,
        control_id: str | None = None,
        control_code: str | None = None,
        department: str | None = None,
        description: str | None = None,
        exclude_finding_id: str | None = None,
        exclude_cycle_id: str | None = None,
        min_score: float = 0.15,
        limit: int = 10,
        db: Session,                             # injected per-call
    ) -> list[RelatedFindingResult]:
        """
        Search Approved findings for the org and score them against the
        provided signals. Returns list sorted by match_score descending.
        Empty list → callers emit "No relevant history found".
        """
        # Fetch candidate pool: Approved findings, same org, exclude self and same cycle
        q = (
            db.query(Finding)
            .filter(
                Finding.organisation_id == organisation_id,
                Finding.review_status == "Approved",
            )
        )
        if exclude_finding_id:
            q = q.filter(Finding.id != exclude_finding_id)
        if exclude_cycle_id:
            q = q.filter(
                (Finding.audit_cycle_id != exclude_cycle_id)
                | (Finding.audit_cycle_id.is_(None))
            )
        candidates: list[Finding] = q.all()

        if not candidates:
            return []

        # Resolve control_code for display if we have a control_id
        code_display = control_code
        if not code_display and control_id:
            ctrl = db.get(Control, control_id)
            code_display = ctrl.control_code if ctrl else None

        # Pre-compute query tokens
        query_tokens = _tokens(description)

        # Collect cycle start dates for proximity scoring
        cycle_cache: dict[str, datetime | None] = {}

        def _cycle_date(cycle_id: str | None) -> datetime | None:
            if cycle_id is None:
                return None
            if cycle_id not in cycle_cache:
                cy = db.get(AuditCycle, cycle_id)
                if cy and cy.start_date:
                    from datetime import datetime as dt
                    cycle_cache[cycle_id] = dt.combine(cy.start_date, dt.min.time())
                else:
                    cycle_cache[cycle_id] = None
            return cycle_cache[cycle_id]

        results: list[RelatedFindingResult] = []

        for cand in candidates:
            score = 0.0
            ctrl_match = False
            dept_match = False
            shared: set[str] = set()

            # (a) Control match
            if control_id and cand.control_id == control_id:
                score += self._W_CONTROL
                ctrl_match = True

            # (b) Department match
            if department and cand.department == department:
                score += self._W_DEPT
                dept_match = True

            # (c) Keyword overlap
            cand_tokens = _tokens(cand.description)
            if query_tokens and cand_tokens:
                j = _jaccard(query_tokens, cand_tokens)
                shared = query_tokens & cand_tokens
                score += j * self._W_KEYWORD_MAX

            # (d) Time proximity (use cycle start dates as proxy)
            days_apart: int | None = None
            if exclude_cycle_id and cand.audit_cycle_id:
                q_date = _cycle_date(exclude_cycle_id)
                c_date = _cycle_date(cand.audit_cycle_id)
                if q_date and c_date:
                    days_apart = abs((q_date - c_date).days)
                    if days_apart <= _MAX_PROXIMITY_DAYS:
                        prox = 1.0 - (days_apart / _MAX_PROXIMITY_DAYS)
                        score += prox * self._W_TIME_MAX

            score = min(round(score, 4), 1.0)
            if score < min_score:
                continue

            # Build plain-English reason
            reason = _build_reason(
                control_match=ctrl_match,
                control_code=code_display,
                dept_match=dept_match,
                department=cand.department,
                shared_tokens=shared,
                days=days_apart,
            )

            # Resolve control code for the candidate
            cand_code: str | None = None
            if cand.control_id:
                c = db.get(Control, cand.control_id)
                cand_code = c.control_code if c else None

            # Gather remediation actions for this candidate
            rem_actions = (
                db.query(RemediationAction)
                .filter(RemediationAction.finding_id == cand.id)
                .all()
            )
            rem_summaries = [
                RemediationSummary(
                    id=r.id,
                    action=r.action,
                    owner=r.owner,
                    due_date=r.due_date,
                    status=r.status,
                    evidence_note=r.evidence_note,
                )
                for r in rem_actions
            ]

            results.append(
                RelatedFindingResult(
                    related_finding_id=cand.id,
                    match_score=score,
                    match_reason=reason,
                    control_code=cand_code,
                    control_id=cand.control_id,
                    department=cand.department,
                    severity=cand.severity,
                    description=cand.description,
                    status=cand.status,
                    review_status=cand.review_status,
                    audit_cycle_id=cand.audit_cycle_id,
                    source_document_id=cand.source_document_id,
                    source_page=cand.source_page,
                    source_excerpt=cand.source_excerpt,
                    remediation_actions=rem_summaries,
                )
            )

        results.sort(key=lambda r: r.match_score, reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------

    def get_timeline(
        self,
        *,
        organisation_id: str,
        control_id: str,
        db: Session,                             # injected per-call
    ) -> ControlTimeline:
        """
        Return a chronological timeline for a control.
        Events: audit cycles that contain findings for this control,
        those findings, their remediation actions, and status changes.
        """
        ctrl = db.get(Control, control_id)
        if ctrl is None or ctrl.organisation_id != organisation_id:
            return ControlTimeline(
                control_id=control_id,
                control_code="unknown",
                entries=[],
                message="Control not found.",
            )

        entries: list[TimelineEntry] = []

        # Findings for this control
        findings = (
            db.query(Finding)
            .filter(
                Finding.control_id == control_id,
                Finding.organisation_id == organisation_id,
            )
            .all()
        )

        cycle_ids = {f.audit_cycle_id for f in findings if f.audit_cycle_id}
        cycle_map: dict[str, AuditCycle] = {}
        for cid in cycle_ids:
            cy = db.get(AuditCycle, cid)
            if cy:
                cycle_map[cid] = cy

        # Add audit cycle entries
        for cy in cycle_map.values():
            dt = datetime.combine(cy.start_date, datetime.min.time()) if cy.start_date else None
            entries.append(TimelineEntry(
                event_type="audit_cycle",
                event_date=dt,
                entity_id=cy.id,
                entity_type="audit_cycle",
                summary=f"Audit cycle: {cy.name}",
                detail={
                    "name": cy.name,
                    "start_date": cy.start_date.isoformat() if cy.start_date else None,
                    "end_date": cy.end_date.isoformat() if cy.end_date else None,
                },
            ))

        # Add finding entries and their children
        for f in findings:
            cycle_start = None
            if f.audit_cycle_id and f.audit_cycle_id in cycle_map:
                cy = cycle_map[f.audit_cycle_id]
                if cy.start_date:
                    cycle_start = datetime.combine(cy.start_date, datetime.min.time())

            entries.append(TimelineEntry(
                event_type="finding",
                event_date=cycle_start,
                entity_id=f.id,
                entity_type="finding",
                summary=f"Finding [{f.severity}]: {f.description[:100]}",
                detail={
                    "severity": f.severity,
                    "status": f.status,
                    "review_status": f.review_status,
                    "department": f.department,
                    "ai_generated": f.ai_generated,
                    "is_recurrence": getattr(f, "is_recurrence", False),
                    "source_page": f.source_page,
                },
            ))

            # Remediation actions
            for r in db.query(RemediationAction).filter(RemediationAction.finding_id == f.id).all():
                due = datetime.combine(r.due_date, datetime.min.time()) if r.due_date else None
                entries.append(TimelineEntry(
                    event_type="remediation",
                    event_date=due,
                    entity_id=r.id,
                    entity_type="remediation",
                    summary=f"Remediation [{r.status}]: {r.action[:100]}",
                    detail={
                        "owner": r.owner,
                        "status": r.status,
                        "due_date": r.due_date.isoformat() if r.due_date else None,
                        "evidence_note": r.evidence_note,
                    },
                ))

            # Status changes for this finding
            for sh in (
                db.query(StatusHistory)
                .filter(
                    StatusHistory.entity_type == "finding",
                    StatusHistory.entity_id == f.id,
                    StatusHistory.organisation_id == organisation_id,
                )
                .order_by(StatusHistory.changed_at)
                .all()
            ):
                entries.append(TimelineEntry(
                    event_type="status_change",
                    event_date=sh.changed_at,
                    entity_id=sh.id,
                    entity_type="status_history",
                    summary=f"Status: {sh.old_status} → {sh.new_status}",
                    detail={
                        "old_status": sh.old_status,
                        "new_status": sh.new_status,
                        "changed_by": sh.changed_by,
                        "note": sh.note,
                    },
                ))

        # Sort by event_date ascending; events without dates go last
        entries.sort(key=lambda e: (e.event_date is None, e.event_date or datetime.min))

        if not entries:
            return ControlTimeline(
                control_id=ctrl.id,
                control_code=ctrl.control_code,
                entries=[],
                message="No relevant history found.",
            )

        return ControlTimeline(
            control_id=ctrl.id,
            control_code=ctrl.control_code,
            entries=entries,
            message="",
        )


def get_history_service() -> SqlHistoryService:
    """Factory function — returns the configured history service implementation."""
    return SqlHistoryService()

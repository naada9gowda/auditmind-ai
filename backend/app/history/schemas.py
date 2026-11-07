"""
history/schemas.py — Dataclasses / Pydantic models for history service results.

These are plain Python dataclasses used as return types from HistoryService.
They are converted to dict / JSON by the API layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class RemediationSummary:
    """Compact remediation action included in a related-finding result."""
    id: str
    action: str
    owner: str | None
    due_date: date | None
    status: str
    evidence_note: str | None


@dataclass
class RelatedFindingResult:
    """
    A previous finding that is similar to the current one.
    Returned by HistoryService.find_related_findings().
    """
    related_finding_id: str          # DB UUID of the earlier finding
    match_score: float               # 0.0 – 1.0
    match_reason: str                # human-readable plain English explanation

    # Earlier finding details
    control_code: str | None
    control_id: str | None
    department: str | None
    severity: str
    description: str
    status: str
    review_status: str
    audit_cycle_id: str | None

    # Source citation
    source_document_id: str | None
    source_page: int | None
    source_excerpt: str | None

    # Remediation outcome
    remediation_actions: list[RemediationSummary] = field(default_factory=list)


@dataclass
class TimelineEntry:
    """One event in a control's audit timeline."""
    event_type: str              # "audit_cycle" | "finding" | "remediation" | "status_change"
    event_date: datetime | date | None
    entity_id: str
    entity_type: str
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class ControlTimeline:
    """Full chronological history for a control."""
    control_id: str
    control_code: str
    entries: list[TimelineEntry] = field(default_factory=list)
    message: str = ""            # "No relevant history found" if entries is empty

"""
history/interface.py — Abstract HistoryService interface.

Defines the contract that any storage backend must satisfy.
Current implementation: SqlHistoryService (see sql_history.py).

Design rules:
- Never fabricate history. If nothing is found, return [] + "No relevant history found".
- All queries are tenant-scoped by organisation_id.
- Results carry match_score and plain-English match_reason only — never raw SQL.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.history.schemas import ControlTimeline, RelatedFindingResult


class HistoryService(ABC):
    """
    Abstract history service interface.

    Both methods are read-only. Writes (storing related_findings rows) are
    handled by the findings API so they go through proper auth and audit logs.
    """

    @abstractmethod
    def find_related_findings(
        self,
        *,
        organisation_id: str,
        control_id: str | None = None,          # DB UUID of the control
        control_code: str | None = None,         # human code e.g. SEC-014
        department: str | None = None,
        description: str | None = None,
        exclude_finding_id: str | None = None,   # don't return the finding itself
        exclude_cycle_id: str | None = None,     # exclude findings from same audit cycle
        min_score: float = 0.15,
        limit: int = 10,
    ) -> list[RelatedFindingResult]:
        """
        Search earlier findings and return those above min_score, sorted
        by match_score descending.

        Returns [] (and callers should emit "No relevant history found")
        when nothing qualifies. Never invents or fabricates data.
        """

    @abstractmethod
    def get_timeline(
        self,
        *,
        organisation_id: str,
        control_id: str,                         # DB UUID of the control
    ) -> ControlTimeline:
        """
        Return a chronological timeline of audit cycles, findings,
        remediation actions and status changes for a control.
        """

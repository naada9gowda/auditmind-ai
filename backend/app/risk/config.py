"""Risk score configuration, thresholds, and component weights."""

from __future__ import annotations

HIGH_THRESHOLD: int = 7
MEDIUM_THRESHOLD: int = 4

# Score components max values
SEVERITY_SCORES: dict[str, int] = {"High": 3, "Medium": 2, "Low": 1}
RECURRENCE_MAX: int = 3  # 1 per prior cycle, max 3
OVERDUE_PARTIAL: int = 1  # any action overdue
OVERDUE_SEVERE: int = 2   # >30 days overdue or prior closure failed
EVIDENCE_MISSING_EXPIRED: int = 2
EVIDENCE_INCOMPLETE: int = 1

DISCLAIMER: str = "Illustrative prioritisation score, not a validated predictive model."

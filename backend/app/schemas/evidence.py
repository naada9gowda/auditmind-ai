"""Pydantic schemas for Evidence."""

from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel


class EvidenceOut(BaseModel):
    id: str
    organisation_id: str
    document_id: Optional[str] = None
    control_id: str
    evidence_date: Optional[date] = None
    review_status: str
    excerpt: Optional[str] = None
    page_number: Optional[int] = None
    assessment: str
    reviewed_by: Optional[str] = None

    model_config = {"from_attributes": True}


class EvidenceMapRequest(BaseModel):
    """Body for POST /api/evidence/map — manually map a document to a control."""
    document_id: str
    control_id: str
    page_number: Optional[int] = None
    excerpt: Optional[str] = None


class EvidenceReviewRequest(BaseModel):
    """Body for POST /api/evidence/{id}/review."""
    decision: str           # "Approved" | "Rejected"
    assessment: Optional[str] = None    # reviewer may override assessment
    note: Optional[str] = None

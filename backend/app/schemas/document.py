"""
schemas/document.py — Pydantic v2 schemas for Document and DocumentPage.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel

DocType = Literal["policy", "audit_report", "evidence"]


class DocumentPageOut(BaseModel):
    id: str
    document_id: str
    page_number: int
    text: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: str
    organisation_id: str
    filename: str
    doc_type: str
    version: Optional[str] = None
    uploaded_at: datetime
    storage_ref: Optional[str] = None
    processing_status: str
    extracted_date: Optional[date] = None
    extracted_title: Optional[str] = None
    extracted_reference: Optional[str] = None
    processing_error: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentDetailOut(DocumentOut):
    """DocumentOut with embedded pages list."""
    pages: List[DocumentPageOut] = []

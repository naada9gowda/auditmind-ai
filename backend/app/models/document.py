"""
models/document.py — Document and DocumentPage ORM models.

Phase 2 adds extracted metadata fields:
  extracted_date, extracted_title, extracted_reference, processing_error
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

DOC_TYPES = ("policy", "audit_report", "evidence")
# Lifecycle: Uploaded -> Processing -> Processed | Failed
PROCESSING_STATUSES = ("Uploaded", "Processing", "Processed", "Failed")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id: Mapped[str] = mapped_column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)          # original client filename (display only)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)           # policy | audit_report | evidence
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    storage_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)  # uuid-based safe filename under UPLOAD_DIR
    processing_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Uploaded")

    # Extracted metadata (populated by /process)
    extracted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    extracted_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    extracted_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    pages: Mapped[list["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan",
        order_by="DocumentPage.page_number",
    )
    evidence_items: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="document")  # noqa: F821


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="pages")

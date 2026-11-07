"""Evidence model — maps document excerpts to controls."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ASSESSMENT_VALUES = (
    "Candidate Match",
    "Missing",
    "Expired",
    "Incomplete",
    "Requires Human Review",
)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id: Mapped[str] = mapped_column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    control_id: Mapped[str] = mapped_column(String(36), ForeignKey("controls.id"), nullable=False, index=True)
    evidence_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Draft")  # Draft | Approved | Rejected
    excerpt: Mapped[str] = mapped_column(Text, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assessment: Mapped[str] = mapped_column(String(50), nullable=False, default="Requires Human Review")
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)  # user id

    document: Mapped["Document"] = relationship("Document", back_populates="evidence_items")  # noqa: F821
    control: Mapped["Control"] = relationship("Control", back_populates="evidence_items")  # noqa: F821

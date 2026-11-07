"""RemediationAction model."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

REMEDIATION_STATUSES = ("Planned", "In Progress", "Ready for Review", "Completed")


class RemediationAction(Base):
    __tablename__ = "remediation_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id: Mapped[str] = mapped_column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("findings.id"), nullable=False, index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Planned")  # Planned | In Progress | Ready for Review | Completed
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    finding: Mapped["Finding"] = relationship("Finding", back_populates="remediation_actions")  # noqa: F821

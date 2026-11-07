"""Finding model — audit findings linked to controls and audit cycles."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

FINDING_STATUSES = ("Open", "In Remediation", "Ready for Review", "Closed")
REVIEW_STATUSES = ("Draft", "Approved", "Rejected")
SEVERITIES = ("High", "Medium", "Low")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id: Mapped[str] = mapped_column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    audit_cycle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("audit_cycles.id"), nullable=True, index=True)
    control_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("controls.id"), nullable=True, index=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="Medium")  # High | Medium | Low
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Open")          # Open | In Remediation | Ready for Review | Closed
    source_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Draft")  # Draft | Approved | Rejected
    is_recurrence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # True when a reviewer confirms this repeats an earlier finding

    audit_cycle: Mapped["AuditCycle"] = relationship("AuditCycle", back_populates="findings")  # noqa: F821
    control: Mapped["Control"] = relationship("Control", back_populates="findings")  # noqa: F821
    remediation_actions: Mapped[list["RemediationAction"]] = relationship("RemediationAction", back_populates="finding", cascade="all, delete-orphan")  # noqa: F821

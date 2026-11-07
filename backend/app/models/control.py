"""Control model — ISO/IEC 27001-inspired control register."""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Allowed status values
CONTROL_STATUSES = ("Compliant", "Needs Review", "Gap Identified", "Not Assessed")


class Control(Base):
    __tablename__ = "controls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id: Mapped[str] = mapped_column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    control_code: Mapped[str] = mapped_column(String(50), nullable=False)       # e.g. SEC-014
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=True)              # responsible person / role
    cadence: Mapped[str] = mapped_column(String(100), nullable=True)            # e.g. quarterly, annual
    evidence_expectation: Mapped[str] = mapped_column(Text, nullable=True)      # what evidence is expected
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Not Assessed")

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="controls")  # noqa: F821
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="control")  # noqa: F821
    evidence_items: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="control")  # noqa: F821

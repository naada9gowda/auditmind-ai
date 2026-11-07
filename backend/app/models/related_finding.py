"""RelatedFinding model — links similar findings from audit history."""

import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RelatedFinding(Base):
    __tablename__ = "related_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id: Mapped[str] = mapped_column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("findings.id"), nullable=False, index=True)
    related_finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("findings.id"), nullable=False)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)   # plain-language reason for the match
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True) # 0.0 – 1.0 similarity
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)  # user id who confirmed the link

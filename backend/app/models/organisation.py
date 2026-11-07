"""Organisation model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships (back-populated by child models)
    users: Mapped[list["User"]] = relationship("User", back_populates="organisation", cascade="all, delete-orphan")  # noqa: F821
    controls: Mapped[list["Control"]] = relationship("Control", back_populates="organisation", cascade="all, delete-orphan")  # noqa: F821

"""Pydantic schemas for RemediationAction."""

from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel

RemediationStatus = Literal["Planned", "In Progress", "Ready for Review", "Completed"]


class RemediationCreate(BaseModel):
    finding_id: str
    owner: Optional[str] = None
    action: str
    due_date: Optional[date] = None
    evidence_note: Optional[str] = None


class RemediationUpdate(BaseModel):
    owner: Optional[str] = None
    action: Optional[str] = None
    due_date: Optional[date] = None
    evidence_note: Optional[str] = None


class RemediationOut(BaseModel):
    id: str
    organisation_id: str
    finding_id: str
    owner: Optional[str] = None
    action: str
    due_date: Optional[date] = None
    status: str
    evidence_note: Optional[str] = None
    is_overdue: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_overdue(cls, obj: "RemediationOut") -> "RemediationOut":
        """Construct from ORM object and compute is_overdue."""
        from datetime import date as _date
        instance = cls.model_validate(obj)
        if instance.due_date and instance.status != "Completed":
            instance.is_overdue = instance.due_date < _date.today()
        return instance

"""Pydantic schemas for AuditCycle."""

from datetime import date
from typing import Optional
from pydantic import BaseModel


class AuditCycleCreate(BaseModel):
    name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class AuditCycleOut(BaseModel):
    id: str
    organisation_id: str
    name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    model_config = {"from_attributes": True}

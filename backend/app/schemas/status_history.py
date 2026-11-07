"""Pydantic schema for StatusHistory."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class StatusHistoryOut(BaseModel):
    id: str
    organisation_id: str
    entity_type: str
    entity_id: str
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[str] = None
    changed_at: datetime
    note: Optional[str] = None

    model_config = {"from_attributes": True}

"""Pydantic schemas for Organisation."""

from datetime import datetime
from pydantic import BaseModel


class OrganisationOut(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}

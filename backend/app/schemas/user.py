"""Pydantic schemas for User."""

from typing import Literal
from pydantic import BaseModel, EmailStr

UserRole = Literal["admin", "compliance_officer", "control_owner", "auditor"]


class UserOut(BaseModel):
    id: str
    organisation_id: str
    name: str
    email: str
    role: str

    model_config = {"from_attributes": True}

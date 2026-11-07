"""Pydantic schemas for Control."""

from typing import Literal, Optional
from pydantic import BaseModel

ControlStatus = Literal["Compliant", "Needs Review", "Gap Identified", "Not Assessed"]


class ControlCreate(BaseModel):
    control_code: str
    title: str
    description: Optional[str] = None
    owner: Optional[str] = None
    cadence: Optional[str] = None
    evidence_expectation: Optional[str] = None
    status: ControlStatus = "Not Assessed"


class ControlUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    cadence: Optional[str] = None
    evidence_expectation: Optional[str] = None
    # Status changes must go through the status-transition service, not direct update.


class ControlOut(BaseModel):
    id: str
    organisation_id: str
    control_code: str
    title: str
    description: Optional[str] = None
    owner: Optional[str] = None
    cadence: Optional[str] = None
    evidence_expectation: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


class ControlWithComputedStatus(ControlOut):
    """
    Extends ControlOut with a computed_status field.

    computed_status is derived at query time from approved findings and
    evidence records. It is a READ-ONLY display hint — it does NOT modify
    the stored control.status.

    "Compliant" is never auto-set here; it only appears if a human explicitly
    set it via the status-transition endpoint.
    """
    computed_status: Optional[str] = None


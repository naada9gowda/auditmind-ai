"""Pydantic schemas for Finding."""

from typing import Literal, Optional
from pydantic import BaseModel

FindingStatus = Literal["Open", "In Remediation", "Ready for Review", "Closed"]
FindingReviewStatus = Literal["Draft", "Approved", "Rejected"]
Severity = Literal["High", "Medium", "Low"]


class FindingCreate(BaseModel):
    audit_cycle_id: Optional[str] = None
    control_id: Optional[str] = None
    department: Optional[str] = None
    severity: Severity = "Medium"
    description: str
    source_document_id: Optional[str] = None
    source_page: Optional[int] = None
    source_excerpt: Optional[str] = None
    ai_generated: bool = False


class FindingUpdate(BaseModel):
    department: Optional[str] = None
    severity: Optional[Severity] = None
    description: Optional[str] = None
    source_excerpt: Optional[str] = None


class FindingOut(BaseModel):
    id: str
    organisation_id: str
    audit_cycle_id: Optional[str] = None
    control_id: Optional[str] = None
    department: Optional[str] = None
    severity: str
    description: str
    status: str
    source_document_id: Optional[str] = None
    source_page: Optional[int] = None
    source_excerpt: Optional[str] = None
    ai_generated: bool
    review_status: str
    is_recurrence: bool = False

    model_config = {"from_attributes": True}

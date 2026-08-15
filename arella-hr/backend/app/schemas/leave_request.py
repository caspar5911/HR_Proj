"""Pydantic schemas for leave request resources."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class LeaveRequestCreate(BaseModel):
    """Schema for creating a leave request."""

    leave_type_id: int = Field(..., ge=1)
    start_date: date
    end_date: date
    reason: Optional[str] = Field(None, max_length=500)


class LeaveRequestUpdate(BaseModel):
    """Schema for approving or rejecting a leave request."""

    status: str = Field(..., pattern="^(approved|rejected)$")
    manager_note: Optional[str] = None


class LeaveRequestOut(BaseModel):
    """Leave request response schema."""

    id: int
    employee_id: int
    employee_name: str
    employee_avatar_url: str | None
    leave_type_id: int
    leave_type_name: str
    leave_type_color: str
    leave_type_is_paid: bool
    department_id: int | None
    department_name: str | None
    start_date: date
    end_date: date
    days_requested: float
    status: str
    reason: str | None
    approved_by: int | None
    approver_name: str | None
    manager_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaveRequestListParams(BaseModel):
    """Query parameters for listing leave requests."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Optional[str] = None  # pending | approved | rejected
    leave_type_id: Optional[int] = None


class PaginatedLeaveResponse(BaseModel):
    """Wrapper for paginated leave request responses."""

    items: list[LeaveRequestOut]
    total: int
    page: int
    page_size: int
    total_pages: int

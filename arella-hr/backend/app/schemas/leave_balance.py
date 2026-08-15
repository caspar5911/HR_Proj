"""Pydantic schemas for leave balance resources."""

from datetime import datetime

from pydantic import BaseModel, Field


class LeaveBalanceOut(BaseModel):
    """Leave balance response schema."""

    id: int
    employee_id: int
    leave_type_id: int
    leave_type_name: str
    year: int
    allocated: float
    used: float
    carried_over: float
    remaining: float
    utilization_pct: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaveBalanceCreate(BaseModel):
    """Schema for creating an initial leave balance."""

    employee_id: int = Field(..., ge=1)
    leave_type_id: int = Field(..., ge=1)
    year: int = Field(..., ge=2000, le=2100)
    allocated: float = Field(..., ge=0, le=365)
    carried_over: float = Field(default=0.0, ge=0, le=365)

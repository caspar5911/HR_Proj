"""Pydantic schemas for leave type resources."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LeaveTypeCreate(BaseModel):
    """Schema for creating a leave type."""

    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    days_per_year: Optional[float] = Field(default=25.0, ge=0, le=365)
    max_consecutive_days: Optional[int] = Field(default=5, ge=1, le=365)
    is_paid: Optional[bool] = True
    color: Optional[str] = Field(default="#3b82f6", pattern="^#[0-9a-fA-F]{6}$")
    requires_approval: Optional[bool] = True
    active: Optional[bool] = True


class LeaveTypeUpdate(BaseModel):
    """Schema for updating a leave type."""

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    days_per_year: Optional[float] = Field(None, ge=0, le=365)
    max_consecutive_days: Optional[int] = Field(None, ge=1, le=365)
    is_paid: Optional[bool] = None
    color: Optional[str] = Field(None, pattern="^#[0-9a-fA-F]{6}$")
    requires_approval: Optional[bool] = None
    active: Optional[bool] = None


class LeaveTypeOut(BaseModel):
    """Leave type response schema."""

    id: int
    name: str
    description: str | None
    days_per_year: float
    max_consecutive_days: int
    is_paid: bool
    color: str
    requires_approval: bool
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

"""Pydantic schemas for performance review resources."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ReviewCycleCreate(BaseModel):
    """Schema for creating a review cycle (admin only)."""

    name: str = Field(..., min_length=3, max_length=100)
    period_start: date
    period_end: date
    description: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _check_period(self) -> "ReviewCycleCreate":
        if self.period_start > self.period_end:
            raise ValueError("period_start must be before period_end")
        return self


class ReviewCycleOut(BaseModel):
    """Review cycle response with live progress counts."""

    id: int
    name: str
    period_start: date
    period_end: date
    status: str  # active | closed
    description: str | None
    created_at: datetime
    total_reviews: int
    drafts: int
    submitted: int
    shared: int

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    """Schema for creating a review (manager or admin)."""

    employee_id: int = Field(..., ge=1)
    rating: Optional[int] = Field(None, ge=1, le=5)
    strengths: Optional[str] = Field(None, max_length=4000)
    improvements: Optional[str] = Field(None, max_length=4000)
    goals: Optional[str] = Field(None, max_length=4000)
    submit: bool = False  # False = save as draft, True = submit for sharing


class ReviewUpdate(BaseModel):
    """Schema for editing a review; only provided fields change."""

    rating: Optional[int] = Field(None, ge=1, le=5)
    strengths: Optional[str] = Field(None, max_length=4000)
    improvements: Optional[str] = Field(None, max_length=4000)
    goals: Optional[str] = Field(None, max_length=4000)
    status: Optional[str] = Field(None, pattern="^(draft|submitted)$")


class ReviewOut(BaseModel):
    """Review response schema."""

    id: int
    cycle_id: int
    cycle_name: str
    cycle_status: str
    employee_id: int
    employee_name: str
    employee_position: str | None
    employee_department: str | None
    reviewer_user_id: int | None
    reviewer_name: str | None
    rating: int | None
    strengths: str | None
    improvements: str | None
    goals: str | None
    status: str  # draft | submitted | shared
    submitted_at: datetime | None
    shared_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

"""Pydantic schemas for goal resources."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    """Schema for creating a goal (owner, their manager, or admin)."""

    employee_id: int = Field(..., ge=1)
    title: str = Field(..., min_length=3, max_length=150)
    description: Optional[str] = Field(None, max_length=4000)
    period: str = Field(..., min_length=2, max_length=20)
    progress: int = Field(default=0, ge=0, le=100)


class GoalUpdate(BaseModel):
    """Schema for updating a goal; only provided fields change."""

    title: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = Field(None, max_length=4000)
    progress: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = Field(None, pattern="^(active|completed|archived)$")


class GoalOut(BaseModel):
    """Goal response schema."""

    id: int
    employee_id: int
    employee_name: str
    employee_position: str | None
    employee_department: str | None
    title: str
    description: str | None
    period: str
    progress: int
    status: str  # active | completed | archived
    completed_at: datetime | None
    created_by_user_id: int | None
    creator_name: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

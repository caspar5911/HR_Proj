"""Pydantic schemas for department resources."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    """Schema for creating a department."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    manager_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    """Schema for updating a department."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    manager_id: Optional[int] = None


class DepartmentOut(BaseModel):
    """Department response schema."""

    id: int
    name: str
    description: str | None
    manager_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

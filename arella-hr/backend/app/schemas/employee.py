"""Pydantic schemas for employee resources."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── request schemas ──────────────────────────────────────────────────────────


class EmployeeCreate(BaseModel):
    """Schema for creating a new employee."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    hire_date: Optional[date] = None
    salary_base: Optional[float] = Field(None, ge=0, le=9999999)
    address: Optional[str] = None
    manager_id: Optional[int] = None
    status: str = Field(default="active", pattern="^(active|inactive|on_leave)$")
    avatar_url: Optional[str] = None


class EmployeeUpdate(BaseModel):
    """Schema for updating an existing employee (all fields optional)."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    hire_date: Optional[date] = None
    salary_base: Optional[float] = Field(None, ge=0, le=9999999)
    address: Optional[str] = None
    manager_id: Optional[int] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|on_leave)$")
    avatar_url: Optional[str] = None


# ── response schemas ─────────────────────────────────────────────────────────


class EmployeeOut(BaseModel):
    """Public employee response (no sensitive internal fields)."""

    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None
    department: str | None
    position: str | None
    hire_date: date | None
    salary_base: float | None
    address: str | None
    manager_id: int | None
    manager_name: str | None  # denormalised display name of the manager
    status: str
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeOutWithManager(BaseModel):
    """Employee response with manager info nested (for org tree)."""

    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None
    department: str | None
    position: str | None
    hire_date: date | None
    salary_base: float | None
    address: str | None
    manager_id: int | None
    manager: "EmployeeOutWithManager | None" = None
    reports: list["EmployeeOutWithManager"] = []
    status: str
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── query / list schemas ─────────────────────────────────────────────────────


class EmployeeListParams(BaseModel):
    """Query parameters for listing employees."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None  # search across name & email
    department: Optional[str] = None
    status: Optional[str] = None  # active | inactive | on_leave
    position: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Wrapper for paginated list responses."""

    items: list[EmployeeOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── circular reference forward reference ─────────────────────────────────────


EmployeeOutWithManager.model_rebuild()
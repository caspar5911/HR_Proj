"""Pydantic schemas for payroll resources."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── request schemas ──────────────────────────────────────────────────────────


class PayrollRunCreate(BaseModel):
    """Schema for creating a new payroll run."""

    period_start: date
    period_end: date
    notes: Optional[str] = None

    model_post_init = lambda self: setattr(
        self, "period_end",
        self.period_end if self.period_end > self.period_start else self.period_start,
    )


class PayrollRunUpdate(BaseModel):
    """Schema for updating a payroll run (all fields optional)."""

    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(draft|processed|paid)$")
    notes: Optional[str] = None


# ── response schemas ─────────────────────────────────────────────────────────


class PayrollRunOut(BaseModel):
    """Public payroll run response."""

    id: int
    period_start: date
    period_end: date
    status: str
    notes: str | None
    generated_at: datetime | None
    total_gross: float = 0.0
    total_net: float = 0.0
    entry_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── query / list schemas ─────────────────────────────────────────────────────


class PayrollRunListParams(BaseModel):
    """Query parameters for listing payroll runs."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Optional[str] = None  # draft | processed | paid
    search: Optional[str] = None  # search in notes


class PaginatedPayrollRunResponse(BaseModel):
    """Wrapper for paginated payroll run list responses."""

    items: list[PayrollRunOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── PayrollEntry schemas ─────────────────────────────────────────────────────


class PayrollEntryOut(BaseModel):
    """Public payroll entry response."""

    id: int
    payroll_run_id: int
    employee_id: int
    employee_name: str  # denormalised
    gross_salary: float
    bonuses: float
    deductions: float
    net_pay: float
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedPayrollEntryResponse(BaseModel):
    """Wrapper for paginated payroll entry list responses."""

    items: list[PayrollEntryOut]
    total: int
    page: int
    page_size: int
    total_pages: int
    run_id: int
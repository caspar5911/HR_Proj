"""Pydantic schemas for deduction rules."""

from typing import Optional

from pydantic import BaseModel, Field


# ── request schemas ──────────────────────────────────────────────────────────


class DeductionRuleCreate(BaseModel):
    """Schema for creating a deduction rule."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    deduction_type: str = Field(default="fixed", pattern="^(fixed|percentage)$")
    value: float = Field(..., gt=0)
    active: bool = True


class DeductionRuleUpdate(BaseModel):
    """Schema for updating a deduction rule (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    deduction_type: Optional[str] = Field(None, pattern="^(fixed|percentage)$")
    value: Optional[float] = Field(None, gt=0)
    active: Optional[bool] = None


# ── response schemas ─────────────────────────────────────────────────────────


class DeductionRuleOut(BaseModel):
    """Public deduction rule response."""

    id: int
    name: str
    description: str | None
    deduction_type: str
    value: float
    active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ── query / list schemas ─────────────────────────────────────────────────────


class DeductionRuleListParams(BaseModel):
    """Query parameters for listing deduction rules."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    active_only: bool = False


class PaginatedDeductionRuleResponse(BaseModel):
    """Wrapper for paginated deduction rule list responses."""

    items: list[DeductionRuleOut]
    total: int
    page: int
    page_size: int
    total_pages: int
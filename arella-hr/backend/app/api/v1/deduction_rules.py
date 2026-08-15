"""Deduction rule API endpoints."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import deduction_rule as crud
from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.deduction_rule import (
    DeductionRuleCreate,
    DeductionRuleListParams,
    DeductionRuleOut,
    DeductionRuleUpdate,
    PaginatedDeductionRuleResponse,
)
from app.services.audit import diff_changes, record_audit

router = APIRouter()


def _build_out(rule):
    """Convert a DeductionRule ORM instance to the response schema."""
    return DeductionRuleOut(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        deduction_type=rule.deduction_type,
        value=float(rule.value),
        active=rule.active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


# ── list ─────────────────────────────────────────────────────────────────────


@router.get(
    "/",
    response_model=PaginatedDeductionRuleResponse,
    dependencies=[Depends(get_current_user)],
)
async def api_list_deduction_rules(
    params: DeductionRuleListParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of deduction rules."""
    items, total = await crud.list_deduction_rules(
        db,
        page=params.page,
        page_size=params.page_size,
        active_only=params.active_only,
    )
    total_pages = math.ceil(total / params.page_size) if total else 0

    return PaginatedDeductionRuleResponse(
        items=[_build_out(r) for r in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


# ── detail ───────────────────────────────────────────────────────────────────


@router.get(
    "/{rule_id}",
    response_model=DeductionRuleOut,
    dependencies=[Depends(get_current_user)],
)
async def api_get_deduction_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return a single deduction rule by ID."""
    rule = await crud.get_deduction_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Deduction rule not found")
    return _build_out(rule)


# ── create ───────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=DeductionRuleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def api_create_deduction_rule(
    payload: DeductionRuleCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new deduction rule."""
    rule = await crud.create_deduction_rule(
        db,
        name=payload.name,
        description=payload.description,
        deduction_type=payload.deduction_type,
        value=payload.value,
        active=payload.active,
    )
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="deduction_rule.created",
        entity="deduction_rule",
        entity_id=rule.id,
        changes={"new": payload.model_dump(mode="json")},
    )
    return _build_out(rule)


# ── update ───────────────────────────────────────────────────────────────────


@router.put(
    "/{rule_id}",
    response_model=DeductionRuleOut,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def api_update_deduction_rule(
    rule_id: int,
    payload: DeductionRuleUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a deduction rule."""
    rule = await crud.get_deduction_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Deduction rule not found")

    update_kwargs = {
        k: v for k, v in {
            "name": payload.name,
            "description": payload.description,
            "deduction_type": payload.deduction_type,
            "value": payload.value,
            "active": payload.active,
        }.items()
        if v is not None
    }
    old_snapshot = {k: getattr(rule, k, None) for k in update_kwargs}
    changes = diff_changes(old_snapshot, update_kwargs)
    updated = await crud.update_deduction_rule(db, rule, **update_kwargs)
    if changes is not None:
        await record_audit(
            db,
            user=current_user,
            request=request,
            action="deduction_rule.updated",
            entity="deduction_rule",
            entity_id=updated.id,
            changes=changes,
        )
    return _build_out(updated)


# ── delete ───────────────────────────────────────────────────────────────────


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def api_delete_deduction_rule(
    rule_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a deduction rule."""
    rule = await crud.get_deduction_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Deduction rule not found")

    snapshot = {"name": rule.name, "deduction_type": rule.deduction_type}
    await crud.delete_deduction_rule(db, rule)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="deduction_rule.deleted",
        entity="deduction_rule",
        entity_id=rule_id,
        changes={"old": snapshot},
    )
    return None
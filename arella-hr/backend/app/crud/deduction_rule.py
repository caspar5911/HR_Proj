"""CRUD operations for deduction rules."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deduction_rule import DeductionRule


async def get_deduction_rule(db: AsyncSession, rule_id: int) -> DeductionRule | None:
    """Return a single deduction rule by ID, or None."""
    stmt = select(DeductionRule).where(DeductionRule.id == rule_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_deduction_rules(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    active_only: bool = False,
) -> tuple[list[DeductionRule], int]:
    """Return (items, total_count) with optional active filter."""
    conditions: list = []
    if active_only:
        conditions.append(DeductionRule.active == True)  # noqa: E712

    # Total count
    count_stmt = select(func.count(DeductionRule.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginated results
    stmt = select(DeductionRule)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(DeductionRule.name)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return items, total


async def create_deduction_rule(
    db: AsyncSession,
    *,
    name: str,
    description: Optional[str] = None,
    deduction_type: str = "fixed",
    value: float,
    active: bool = True,
) -> DeductionRule:
    """Create a new deduction rule."""
    rule = DeductionRule(
        name=name,
        description=description,
        deduction_type=deduction_type,
        value=value,
        active=active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_deduction_rule(
    db: AsyncSession,
    rule: DeductionRule,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    deduction_type: Optional[str] = None,
    value: Optional[float] = None,
    active: Optional[bool] = None,
) -> DeductionRule:
    """Update fields on an existing deduction rule."""
    update_data = {
        "name": name,
        "description": description,
        "deduction_type": deduction_type,
        "value": value,
        "active": active,
    }
    for field, field_value in update_data.items():
        if field_value is not None:
            setattr(rule, field, field_value)

    rule.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_deduction_rule(db: AsyncSession, rule: DeductionRule) -> None:
    """Permanently delete a deduction rule."""
    await db.delete(rule)
    await db.commit()
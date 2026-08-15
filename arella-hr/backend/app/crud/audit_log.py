"""CRUD operations for the audit log."""

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_log import AuditLog


async def get_audit_log(db: AsyncSession, log_id: int) -> AuditLog | None:
    """Return a single audit log entry by ID."""
    stmt = select(AuditLog).where(AuditLog.id == log_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_audit_logs(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 50,
    user_id: Optional[int] = None,
    entity: Optional[str] = None,
    action: Optional[str] = None,
    entity_id: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> tuple[list[AuditLog], int]:
    """Return (items, total_count) with optional filters.

    Results are ordered newest-first.
    """
    conditions: list = []

    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)
    if entity:
        conditions.append(AuditLog.entity == entity)
    if action:
        conditions.append(AuditLog.action == action)
    if entity_id is not None:
        conditions.append(AuditLog.entity_id == entity_id)
    if start is not None:
        conditions.append(AuditLog.timestamp >= start)
    if end is not None:
        conditions.append(AuditLog.timestamp <= end)

    # Total count
    count_stmt = select(func.count(AuditLog.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginated results
    stmt = select(AuditLog).options(selectinload(AuditLog.user))
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return items, total

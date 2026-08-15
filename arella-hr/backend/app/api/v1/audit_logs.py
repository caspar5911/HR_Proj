"""Audit log API endpoints (read-only, admin-only)."""

import math

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.audit_log import get_audit_log, list_audit_logs
from app.database import get_db
from app.middleware.auth import require_role
from app.models.user import User, UserRole
from app.schemas.audit_log import (
    AuditLogListParams,
    AuditLogOut,
    PaginatedAuditLogResponse,
)
from app.utils.errors import NotFoundError

router = APIRouter()


def _build_out(log) -> AuditLogOut:
    """Convert an AuditLog ORM instance to the response schema."""
    user_email = log.user.email if (log.user is not None) else None
    return AuditLogOut(
        id=log.id,
        user_id=log.user_id,
        user_email=user_email,
        action=log.action,
        entity=log.entity,
        entity_id=log.entity_id,
        changes=log.changes,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        timestamp=log.timestamp,
    )


@router.get(
    "/",
    response_model=PaginatedAuditLogResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def api_list_audit_logs(
    params: AuditLogListParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated, filterable audit log (newest first)."""
    items, total = await list_audit_logs(
        db,
        page=params.page,
        page_size=params.page_size,
        user_id=params.user_id,
        entity=params.entity,
        action=params.action,
        entity_id=params.entity_id,
        start=params.start,
        end=params.end,
    )
    total_pages = math.ceil(total / params.page_size) if total else 0

    return PaginatedAuditLogResponse(
        items=[_build_out(log) for log in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{log_id}",
    response_model=AuditLogOut,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def api_get_audit_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return a single audit log entry by ID."""
    log = await get_audit_log(db, log_id)
    if not log:
        raise NotFoundError("Audit log entry not found")
    return _build_out(log)

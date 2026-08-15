"""Notification API endpoints — the in-app notification center.

Every endpoint is scoped to the current user's own notifications; there is
no way to list or modify another user's bell.
"""

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notifications import (
    NotificationOut,
    PaginatedNotificationResponse,
    UnreadCountResponse,
)
from app.utils.errors import NotFoundError

router = APIRouter()


def _build_out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        type=n.type,
        title=n.title,
        body=n.body,
        link=n.link,
        read=n.read,
        created_at=n.created_at,
        read_at=n.read_at,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def api_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the number of unread notifications for the current user."""
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
    )
    return UnreadCountResponse(unread=result.scalar() or 0)


@router.post("/read-all", response_model=UnreadCountResponse)
async def api_mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all of the current user's notifications as read."""
    from datetime import datetime, timezone

    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return UnreadCountResponse(unread=0)


@router.get("/", response_model=PaginatedNotificationResponse)
async def api_list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's notifications, newest first."""
    base = select(Notification).where(Notification.user_id == current_user.id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    result = await db.execute(
        base.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedNotificationResponse(
        items=[_build_out(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def api_mark_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a single notification as read (only the owner may do this)."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise NotFoundError("Notification not found")

    if notification.read_at is None:
        from datetime import datetime, timezone

        notification.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notification)
    return _build_out(notification)

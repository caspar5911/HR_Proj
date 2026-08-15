"""Pydantic schemas for the in-app notification center."""

from datetime import datetime

from pydantic import BaseModel, Field


class NotificationOut(BaseModel):
    """A single in-app notification."""

    id: int
    type: str
    title: str
    body: str
    link: str | None
    read: bool
    created_at: datetime
    read_at: datetime | None

    model_config = {"from_attributes": True}


class NotificationListParams(BaseModel):
    """Query parameters for listing notifications."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)


class PaginatedNotificationResponse(BaseModel):
    """Wrapper for paginated notification responses."""

    items: list[NotificationOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class UnreadCountResponse(BaseModel):
    """Unread notification count for the current user."""

    unread: int

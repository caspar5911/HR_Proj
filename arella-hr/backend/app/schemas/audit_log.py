"""Pydantic schemas for the audit log."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditLogOut(BaseModel):
    """A single audit log entry as returned to clients."""

    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    action: str
    entity: str
    entity_id: Optional[int] = None
    changes: Optional[Any] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class AuditLogListParams(BaseModel):
    """Query parameters for listing audit logs."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
    user_id: Optional[int] = None
    entity: Optional[str] = None
    action: Optional[str] = None
    entity_id: Optional[int] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class PaginatedAuditLogResponse(BaseModel):
    """Wrapper for paginated audit log responses."""

    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int
    total_pages: int

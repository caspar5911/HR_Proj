"""Audit log model — records who changed what, when, and from where."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class AuditLog(Base):
    """Immutable audit trail of significant changes made through the API.

    Conventions:
    - ``action``  uses the form ``"<entity>.<verb>"`` e.g. ``"employee.created"``
    - ``entity``  is the resource name e.g. ``"employee"``
    - ``changes`` holds a JSON snapshot:
        - create:  ``{"new": {...}}``
        - update:  ``{"old": {...}, "new": {...}}`` (only fields that changed)
        - delete:  ``{"old": {...}}``
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", lazy="selectin")

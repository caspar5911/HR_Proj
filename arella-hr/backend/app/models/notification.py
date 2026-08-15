"""Notification model — in-app notification center.

One row per notification delivered to a single user account (``user_id``).
Notifications are complementary to the email service: the same event that
emails a manager or employee also drops a bell entry they can open in-app.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Notification(Base):
    """ORM model for in-app user notifications."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Recipient — the user account that will see this in the bell.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Event discriminator: leave_requested | leave_approved | leave_rejected
    # | payroll_processed (free-form on purpose so new events don't need a
    # schema change).
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional frontend hash-route the bell should open on click (e.g. "/leave").
    link: Mapped[str | None] = mapped_column(String(200), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    @property
    def read(self) -> bool:
        return self.read_at is not None

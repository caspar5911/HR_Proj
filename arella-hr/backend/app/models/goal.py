"""Goal model — OKR-style objectives an employee works toward in a period."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Goal(Base):
    """One objective owned by an employee for a labeled period.

    Periods use human labels such as ``"H2 2026"`` so goals line up with
    review cycles without needing a foreign key into the cycles table.
    """

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    status: Mapped[str] = mapped_column(
        String(20), default="active", index=True
    )  # active, completed, archived
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")
    creator: Mapped["User | None"] = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Goal emp={self.employee_id} {self.title!r} {self.progress}% {self.status}>"

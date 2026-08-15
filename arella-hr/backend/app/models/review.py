"""Performance review models — cycles and individual reviews."""

from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class ReviewCycle(Base):
    """ORM model for a review period (e.g. "2026 Mid-Year Review")."""

    __tablename__ = "review_cycles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", index=True
    )  # active, closed
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="cycle", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ReviewCycle {self.name!r} status={self.status}>"


class Review(Base):
    """ORM model for one manager's review of one employee in a cycle."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("cycle_id", "employee_id", name="uq_review_cycle_employee"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cycle_id: Mapped[int] = mapped_column(
        ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvements: Mapped[str | None] = mapped_column(Text, nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", index=True
    )  # draft, submitted, shared
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    shared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    cycle: Mapped["ReviewCycle"] = relationship("ReviewCycle", back_populates="reviews", lazy="selectin")
    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")
    reviewer: Mapped["User | None"] = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Review cycle={self.cycle_id} emp={self.employee_id} status={self.status}>"

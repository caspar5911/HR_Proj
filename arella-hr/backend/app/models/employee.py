"""Employee model — core directory entity."""

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Employee(Base):
    """ORM model for employee directory records."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    salary_base: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    # Auth link — an employee directory record may be backed by a user account.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Normalized department reference (alongside the denormalized `department` string).
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="active", index=True
    )  # active, inactive, on_leave
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
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
    user: Mapped["User | None"] = relationship("User", back_populates="employee_profile", lazy="selectin")
    # Adjacency list: manager_id points at the manager; `manager` is many-to-one,
    # `reports` is the one-to-many inverse. remote_side pins the PK side.
    reports: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="manager", lazy="selectin"
    )
    manager: Mapped["Employee | None"] = relationship(
        "Employee", back_populates="reports", remote_side=[id], lazy="selectin"
    )

    # Department association — pinned to the normalized FK since departments
    # also reference employees (manager_id), which would otherwise be ambiguous.
    department_obj: Mapped["Department | None"] = relationship(
        "Department", back_populates="employees",
        foreign_keys=[department_id], lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
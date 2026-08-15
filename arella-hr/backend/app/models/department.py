"""Department model - organisational units."""

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone

from app.models import Base


class Department(Base):
    """ORM model for departments."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"), nullable=True
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
    manager: Mapped["Employee | None"] = relationship(
        "Employee", foreign_keys=[manager_id], lazy="selectin"
    )
    employees: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="department_obj",
        foreign_keys="Employee.department_id", lazy="selectin",
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        "LeaveRequest", back_populates="department", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Department {self.name}>"

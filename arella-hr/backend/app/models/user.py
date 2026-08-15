"""User model — authentication entity."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class UserRole:
    """Enumerated user roles."""

    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class User(Base):
    """ORM model for system users."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(UserRole.ADMIN, UserRole.MANAGER, UserRole.EMPLOYEE, name="user_role"),
        default=UserRole.EMPLOYEE,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    employee_profile: Mapped["Employee | None"] = relationship(
        "Employee", back_populates="user", uselist=False, lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
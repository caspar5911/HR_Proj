"""Shared fixtures and seeding helpers for the API test suite.

Every test gets a pristine in-memory SQLite schema and a clean set of
in-memory rate limiters, so tests never interfere with each other.
"""

from collections.abc import AsyncGenerator

import bcrypt
import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.middleware import rate_limit
from app.models import Base
from app.services import token_revocation
from app.models.employee import Employee
from app.models.leave_balance import LeaveBalance
from app.models.leave_type import LeaveType
from app.models.user import User

TEST_PASSWORD = "test-password-123"
API = "/api/v1"

# Single shared in-memory database: StaticPool pins everything to one
# connection so sessions (and the per-test DDL below) all see the same data.
_engine = create_async_engine(
    "sqlite+aiosqlite://",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


# ── autouse isolation fixtures ───────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Wipe the in-memory sliding windows so tests never trip a 429."""
    rate_limit.LOGIN_LIMITER._hits.clear()
    rate_limit.REFRESH_LIMITER._hits.clear()
    rate_limit.REGISTER_LIMITER._hits.clear()


@pytest.fixture(autouse=True)
def _reset_token_revocations():
    """Empty the refresh-token revocation store so tests start clean."""
    token_revocation.REVOKED_REFRESH_TOKENS.clear()


@pytest_asyncio.fixture(autouse=True)
async def _database():
    """Create the full schema before each test, drop it afterwards."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── core fixtures ────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """A fresh AsyncSession for seeding / asserting directly against the DB."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """ASGI test client with ``get_db`` overridden to the in-memory DB."""

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


# ── seeding helpers (plain functions, imported by the test modules) ─────────


def make_user(
    email: str = "admin@test.com",
    role: str = "admin",
    password: str = TEST_PASSWORD,
    is_active: bool = True,
) -> User:
    """Build a (not yet persisted) User with a bcrypt-hashed password."""
    return User(
        email=email,
        hashed_password=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        role=role,
        is_active=is_active,
    )


async def seed_user(
    db: AsyncSession,
    email: str = "admin@test.com",
    role: str = "admin",
    password: str = TEST_PASSWORD,
    is_active: bool = True,
) -> User:
    user = make_user(email=email, role=role, password=password, is_active=is_active)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login(client: httpx.AsyncClient, email: str, password: str = TEST_PASSWORD) -> dict:
    """POST to /auth/login and return the parsed token response."""
    resp = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
    return resp.json()


async def make_tokens(
    client: httpx.AsyncClient, db: AsyncSession
) -> dict[str, str]:
    """Seed one user per role and return ``{role: access_token}``."""
    tokens: dict[str, str] = {}
    for role, email in (
        ("admin", "admin@test.com"),
        ("manager", "manager@test.com"),
        ("employee", "employee@test.com"),
    ):
        await seed_user(db, email=email, role=role)
        tokens[role] = (await login(client, email))["access_token"]
    return tokens


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def seed_employee(
    db: AsyncSession,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    email: str = "ada@acme.co",
    salary_base: float | None = 5000.0,
    user: User | None = None,
    status: str = "active",
    department: str = "Engineering",
) -> Employee:
    emp = Employee(
        first_name=first_name,
        last_name=last_name,
        email=email,
        department=department,
        position="Engineer",
        salary_base=salary_base,
        status=status,
        user_id=user.id if user else None,
    )
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return emp


async def seed_leave_type(
    db: AsyncSession,
    name: str = "Annual Leave",
    days_per_year: float = 25.0,
    max_consecutive_days: int = 5,
) -> LeaveType:
    lt = LeaveType(name=name, days_per_year=days_per_year, max_consecutive_days=max_consecutive_days)
    db.add(lt)
    await db.commit()
    await db.refresh(lt)
    return lt


async def seed_balance(
    db: AsyncSession,
    employee: Employee,
    leave_type: LeaveType,
    year: int,
    allocated: float = 25.0,
) -> LeaveBalance:
    balance = LeaveBalance(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        year=year,
        allocated=allocated,
    )
    db.add(balance)
    await db.commit()
    await db.refresh(balance)
    return balance

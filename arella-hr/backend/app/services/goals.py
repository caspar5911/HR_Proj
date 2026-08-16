"""Goal access control.

Visibility rules (mirror the review scoping):

* **Admins** see and manage every goal.
* **Managers** see and manage goals for themselves and their direct reports.
* **Employees** see and manage only their own goals.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.goal import Goal
from app.models.user import User, UserRole
from app.utils.errors import PermissionDeniedError


async def _profile_ids(db: AsyncSession, user: User) -> set[int]:
    """Employee profile ID(s) backing a user's login account (usually one)."""
    result = await db.execute(select(Employee.id).where(Employee.user_id == user.id))
    return {row for (row,) in result.all()}


async def my_employee_id(db: AsyncSession, user: User) -> int:
    """Resolve the Employee.id backing a user's login account.

    Raises :class:`PermissionDeniedError` when the account has no employee
    profile (same policy as the leave-request endpoints).
    """
    ids = await _profile_ids(db, user)
    if not ids:
        raise PermissionDeniedError("No employee profile found for your account")
    return next(iter(ids))


async def direct_report_ids(db: AsyncSession, user: User) -> set[int]:
    """Employee IDs that a manager user directly manages.

    Managers without an employee profile manage nobody (empty set).
    """
    if user.role != UserRole.MANAGER:
        return set()
    profile_ids = await _profile_ids(db, user)
    if not profile_ids:
        return set()
    result = await db.execute(
        select(Employee.id).where(Employee.manager_id.in_(profile_ids))
    )
    return {row for (row,) in result.all()}


async def visible_employee_ids(db: AsyncSession, user: User) -> set[int]:
    """Employees whose goals this user may see.

    Managers get themselves plus their direct reports; employees get
    themselves. Admins are handled by the caller (they see everything).
    """
    ids = await _profile_ids(db, user)
    if user.role == UserRole.MANAGER:
        ids |= await direct_report_ids(db, user)
    return ids


async def can_view_goal(db: AsyncSession, user: User, goal: Goal) -> bool:
    """Admins see all; managers their reports (and themselves); employees their own."""
    if user.role == UserRole.ADMIN:
        return True
    return goal.employee_id in await visible_employee_ids(db, user)


async def can_modify_goal(db: AsyncSession, user: User, goal: Goal) -> bool:
    """Owners always manage their own; managers manage their reports' too."""
    if user.role == UserRole.ADMIN:
        return True
    if goal.employee_id in await _profile_ids(db, user):
        return True
    if user.role == UserRole.MANAGER:
        return goal.employee_id in await direct_report_ids(db, user)
    return False


async def can_create_for(db: AsyncSession, user: User, employee: Employee) -> bool:
    """Who may set a goal for ``employee``.

    Admins for anyone, a manager for their direct reports (and themselves),
    an employee for themselves.
    """
    if user.role == UserRole.ADMIN:
        return True
    own = await _profile_ids(db, user)
    if employee.id in own:
        return True
    if user.role == UserRole.MANAGER:
        return employee.manager_id in own
    raise PermissionDeniedError("You can only set goals for yourself")


async def can_delete_goal(db: AsyncSession, user: User, goal: Goal) -> bool:
    """Deleting is stricter than editing: owners and admins only."""
    if user.role == UserRole.ADMIN:
        return True
    return goal.employee_id in await _profile_ids(db, user)

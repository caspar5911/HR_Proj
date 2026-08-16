"""Goal API endpoints — OKR-style objectives per employee and period.

Roles:
* Admins manage every goal.
* Managers manage goals for themselves and their direct reports.
* Employees manage only their own goals.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.employee import Employee
from app.models.goal import Goal
from app.models.user import User, UserRole
from app.schemas.goal import GoalCreate, GoalOut, GoalUpdate
from app.services.audit import record_audit
from app.services import goals as goal_service
from app.utils.errors import NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter()


def _build_out(g: Goal) -> GoalOut:
    """Convert a Goal ORM instance to the response schema."""
    emp = g.employee
    return GoalOut(
        id=g.id,
        employee_id=g.employee_id,
        employee_name=emp.full_name if emp else "Unknown",
        employee_position=emp.position if emp else None,
        employee_department=emp.department if emp else None,
        title=g.title,
        description=g.description,
        period=g.period,
        progress=g.progress,
        status=g.status,
        completed_at=g.completed_at,
        created_by_user_id=g.created_by_user_id,
        creator_name=g.creator.email if g.creator else None,
        created_at=g.created_at,
        updated_at=g.updated_at,
    )


@router.get("/", response_model=list[GoalOut])
async def api_list_goals(
    period: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    employee_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Goals scoped by role, with optional period / status / employee filters.

    Admins: everything (``employee_id`` narrows the result).
    Managers: themselves + direct reports; an ``employee_id`` outside that
    set yields an empty list rather than leaking existence.
    Employees: their own goals only.
    """
    if current_user.role == UserRole.ADMIN:
        q = select(Goal).join(Employee, Goal.employee_id == Employee.id)
        if employee_id is not None:
            q = q.where(Goal.employee_id == employee_id)
    elif current_user.role == UserRole.MANAGER:
        visible = await goal_service.visible_employee_ids(db, current_user)
        if employee_id is not None and employee_id not in visible:
            return []
        q = select(Goal).join(Employee, Goal.employee_id == Employee.id).where(
            Goal.employee_id.in_(visible)
        )
        if employee_id is not None:
            q = q.where(Goal.employee_id == employee_id)
    else:
        emp_id = await goal_service.my_employee_id(db, current_user)
        q = select(Goal).join(Employee, Goal.employee_id == Employee.id).where(
            Goal.employee_id == emp_id
        )

    if period:
        q = q.where(Goal.period == period)
    if status_filter:
        q = q.where(Goal.status == status_filter)

    result = await db.execute(
        q.order_by(
            Employee.first_name.asc(),
            Employee.last_name.asc(),
            Goal.period.desc(),
            Goal.created_at.desc(),
        )
    )
    return [_build_out(g) for g in result.scalars().all()]


@router.post("/", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def api_create_goal(
    data: GoalCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a goal (for yourself, your direct reports, or anyone — by role)."""
    employee = await db.get(Employee, data.employee_id)
    if not employee:
        raise NotFoundError("Employee not found")

    if not await goal_service.can_create_for(db, current_user, employee):
        if current_user.role == UserRole.MANAGER:
            raise PermissionDeniedError("You can only set goals for your direct reports")
        raise PermissionDeniedError("You can't set a goal for that employee")

    goal = Goal(
        employee_id=employee.id,
        title=data.title,
        description=data.description,
        period=data.period,
        progress=data.progress,
        created_by_user_id=current_user.id,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="goal.created",
        entity="goal",
        entity_id=goal.id,
        changes={"new": data.model_dump(mode="json")},
    )
    return _build_out(goal)


@router.patch("/{goal_id}", response_model=GoalOut)
async def api_update_goal(
    goal_id: int,
    data: GoalUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update progress, status, or text of a visible goal (owner/manager/admin)."""
    goal = await db.get(Goal, goal_id)
    if not goal or not await goal_service.can_modify_goal(db, current_user, goal):
        raise NotFoundError("Goal not found")

    old = {"title": goal.title, "progress": goal.progress, "status": goal.status}
    provided = data.model_fields_set
    if "title" in provided:
        goal.title = data.title
    if "description" in provided:
        goal.description = data.description
    if "progress" in provided:
        goal.progress = data.progress
    if "status" in provided:
        if data.status == "completed" and goal.status != "completed":
            goal.progress = 100
            goal.completed_at = datetime.now(timezone.utc)
        elif goal.status == "completed" and data.status != "completed":
            goal.completed_at = None
        goal.status = data.status

    await db.commit()
    await db.refresh(goal)
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="goal.updated",
        entity="goal",
        entity_id=goal.id,
        changes={
            "old": old,
            "new": {
                "title": goal.title,
                "progress": goal.progress,
                "status": goal.status,
            },
        },
    )
    return _build_out(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_goal(
    goal_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a goal (owner or admin only)."""
    goal = await db.get(Goal, goal_id)
    if not goal or not await goal_service.can_delete_goal(db, current_user, goal):
        raise NotFoundError("Goal not found")

    snapshot = {"title": goal.title, "period": goal.period, "status": goal.status}
    await db.delete(goal)
    await db.commit()
    await record_audit(
        db,
        user=current_user,
        request=request,
        action="goal.deleted",
        entity="goal",
        entity_id=goal_id,
        changes={"old": snapshot, "new": None},
    )
    return None

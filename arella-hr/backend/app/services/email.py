"""Email notification service.

Console-mocked transport: :func:`send_email` prints a formatted message to
stdout instead of sending it over SMTP. To hook up a real provider
(Resend, Postmark, ...), replace the body of :func:`_deliver` and leave the
public helpers unchanged.

The service is deliberately forgiving: a notification failure must never
break the primary operation that triggered it (e.g. approving a leave
request). Every public helper swallows its own errors and logs them.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.employee import Employee
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


# ── transport ────────────────────────────────────────────────────────────────


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email to ``to``. Never raises.

    Returns ``True`` when the message was delivered, ``False`` when it was
    skipped (``EMAIL_ENABLED`` off) or delivery failed.
    """
    try:
        if not settings.EMAIL_ENABLED:
            logger.debug("Email disabled; skipping %r to %s", subject, to)
            return False
        await _deliver(to, subject, body)
        return True
    except Exception:
        logger.exception("Failed to send email to=%s subject=%r", to, subject)
        return False


async def _deliver(to: str, subject: str, body: str) -> None:
    """Mock transport — print to console, simulating an SMTP send."""
    line = "=" * 60
    print(line)
    print(f"TO: {to}")
    print(f"SUBJECT: {subject}")
    print("-" * 60)
    print(body)
    print(line)


# ── recipient resolution ─────────────────────────────────────────────────────


async def _manager_emails_for(db: AsyncSession, employee: Employee) -> list[str]:
    """Emails of the employee's direct manager, falling back to active managers."""
    if employee.manager and employee.manager.email:
        return [employee.manager.email]
    result = await db.execute(
        select(User.email).where(User.role == UserRole.MANAGER, User.is_active.is_(True))
    )
    return [email for (email,) in result.all() if email]


# ── notifications ────────────────────────────────────────────────────────────


async def notify_leave_requested(
    db: AsyncSession,
    request,
    employee: Employee,
) -> None:
    """Email the manager that a new leave request is awaiting review."""
    leave_type_name = request.leave_type.name if request.leave_type else "leave"
    recipients = await _manager_emails_for(db, employee)
    if not recipients:
        logger.warning(
            "No manager found for employee %s; skipping leave-request email",
            employee.id,
        )
        return

    body = (
        f"{employee.full_name} has requested {leave_type_name} leave.\n"
        f"  From: {request.start_date}\n"
        f"  To:   {request.end_date}\n"
        f"  Days: {request.days_requested:g}\n"
    )
    if request.reason:
        body += f"  Reason: {request.reason}\n"
    body += "Please review the request in the Arella HR system."

    for to in recipients:
        await send_email(to, f"New leave request from {employee.full_name}", body)


async def notify_leave_decided(db: AsyncSession, request) -> None:
    """Email the employee that their leave request was approved or rejected."""
    employee = request.employee
    if employee is None or not employee.email:
        logger.warning("No employee email for leave request %s; skipping email", request.id)
        return

    decision = "approved" if request.status == "approved" else "rejected"
    leave_type_name = request.leave_type.name if request.leave_type else "leave"
    body = (
        f"Hi {employee.first_name},\n\n"
        f"Your {leave_type_name} leave request ({request.start_date} to "
        f"{request.end_date}) has been {decision}."
    )
    if request.manager_note:
        body += f"\n\nNote: {request.manager_note}"

    await send_email(
        employee.email,
        f"Your {leave_type_name} leave request was {decision}",
        body,
    )


async def notify_payroll_processed(db: AsyncSession, payroll_run, entries) -> None:
    """Email each employee whose payroll entry was just generated."""
    if not entries:
        return

    emp_ids = {entry.employee_id for entry in entries}
    result = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))
    employees = {emp.id: emp for emp in result.scalars().all()}

    for entry in entries:
        emp = employees.get(entry.employee_id)
        if emp is None or not emp.email:
            continue
        body = (
            f"Hi {emp.first_name},\n\n"
            f"Your payroll for {payroll_run.period_start} to {payroll_run.period_end} "
            f"has been processed.\n\n"
            f"  Gross salary: {float(entry.gross_salary):,.2f}\n"
            f"  Bonuses:      {float(entry.bonuses):,.2f}\n"
            f"  Deductions:   {float(entry.deductions):,.2f}\n"
            f"  Net pay:      {float(entry.net_pay):,.2f}\n"
        )
        await send_email(
            emp.email,
            f"Payroll processed: {payroll_run.period_start} to {payroll_run.period_end}",
            body,
        )

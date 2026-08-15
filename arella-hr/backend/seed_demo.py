"""Seed realistic demo data for a product walkthrough.

Run inside the backend container (guarantees the right DB URL + deps):

    docker cp seed_demo.py backend:/tmp/
    docker compose exec backend python /tmp/seed_demo.py

Idempotent: wipes the demo-owned tables each run and keeps only the
admin user. Payroll entries for the processed July run are generated with
the app's own ``calculate_payroll_for_run`` so numbers match the UI.
"""

import asyncio
import random
from datetime import date, datetime, time, timedelta, timezone

import bcrypt
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models.audit_log import AuditLog
from app.models.deduction_rule import DeductionRule
from app.models.department import Department
from app.models.employee import Employee
from app.models.leave_balance import LeaveBalance
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.payroll_run import PayrollRun
from app.models.time_entry import TimeEntry
from app.models.user import User, UserRole
from app.services.payroll import calculate_payroll_for_run

YEAR = 2026

# Time-entry demo window: late June through the last full week of August.
TIME_ENTRY_START = date(2026, 6, 29)
TIME_ENTRY_END = date(2026, 8, 14)


# ── Demo data ──────────────────────────────────────────────────────────────

DEPARTMENTS = [
    ("Engineering", "Product platform, APIs and infrastructure"),
    ("Design", "Product and brand design"),
    ("Marketing", "Growth, content and demand generation"),
    ("Sales", "Account management and partnerships"),
    ("HR", "People, culture and operations"),
    ("Finance", "Payroll, accounting and reporting"),
]

# (first, last, email, phone, position, dept, salary, status, hire, manager, address)
EMPLOYEES = [
    ("Maya", "Chen", "maya.chen@arellahr.com", "+1-555-0101",
     "Engineering Director", "Engineering", 145000, "active", date(2021, 6, 1), None,
     "12 Harbour St, Boston, MA"),
    ("Sam", "Okafor", "sam.okafor@arellahr.com", "+1-555-0102",
     "Senior Backend Engineer", "Engineering", 115000, "active", date(2022, 1, 10), "Maya Chen",
     "88 Beacon Ave, Somerville, MA"),
    ("Liam", "Torres", "liam.torres@arellahr.com", "+1-555-0103",
     "Frontend Engineer", "Engineering", 95000, "active", date(2025, 11, 12), "Maya Chen",
     "5 Faneuil Plaza, Boston, MA"),
    ("Grace", "Kim", "grace.kim@arellahr.com", "+1-555-0104",
     "QA Engineer", "Engineering", 70000, "inactive", date(2021, 8, 30), "Maya Chen",
     "301 Newbury St, Boston, MA"),
    ("Noa", "Berg", "noa.berg@arellahr.com", "+1-555-0105",
     "Design Lead", "Design", 110000, "active", date(2021, 11, 8), None,
     "10 Beacon St, Boston, MA"),
    ("Priya", "Nair", "priya.nair@arellahr.com", "+1-555-0106",
     "Product Designer", "Design", 98000, "active", date(2026, 1, 15), "Noa Berg",
     "215 Summer St, Boston, MA"),
    ("Elena", "Petrova", "elena.petrova@arellahr.com", "+1-555-0107",
     "Marketing Manager", "Marketing", 92000, "active", date(2022, 5, 16), None,
     "77 Commercial St, Boston, MA"),
    ("Aisha", "Bello", "aisha.bello@arellahr.com", "+1-555-0108",
     "Content Specialist", "Marketing", 60000, "on_leave", date(2025, 10, 6), "Elena Petrova",
     "141 Congress St, Boston, MA"),
    ("Marcus", "Webb", "marcus.webb@arellahr.com", "+1-555-0109",
     "Sales Manager", "Sales", 75000, "active", date(2023, 2, 20), None,
     "450 Park St, Boston, MA"),
    ("David", "Park", "david.park@arellahr.com", "+1-555-0110",
     "Sales Operations Analyst", "Sales", 65000, "active", date(2026, 4, 7), "Marcus Webb",
     "120 Federal St, Boston, MA"),
    ("Tomas", "Silva", "tomas.silva@arellahr.com", "+1-555-0111",
     "Finance Analyst", "Finance", 78000, "on_leave", date(2025, 12, 18), None,
     "60 State St, Boston, MA"),
    ("Jordan", "Avery", "jordan.avery@arellahr.com", "+1-555-0112",
     "Head of HR", "HR", 88000, "active", date(2022, 3, 15), None,
     "225 Franklin St, Boston, MA"),
]

# (name, description, days_per_year, max_consecutive, paid, color, requires_approval)
LEAVE_TYPES = [
    ("Annual Leave", "Paid vacation, accrued yearly", 25.0, 14, True, "#3b82f6", True),
    ("Sick Leave", "Short-term illness, paid", 10.0, 5, True, "#10b981", False),
    ("Personal Leave", "Personal matters, paid", 5.0, 3, True, "#8b5cf6", True),
]

# Per active/on-leave employee: (annual_used, sick_used, personal_used)
LEAVE_BALANCES = {
    "Maya Chen": (6, 2, 1), "Sam Okafor": (4, 1, 0), "Liam Torres": (8, 0, 1),
    "Noa Berg": (3, 1, 0), "Priya Nair": (2, 0, 0), "Elena Petrova": (5, 1, 0),
    "Aisha Bello": (7, 0, 1), "Marcus Webb": (10, 0, 0), "David Park": (1, 0, 0),
    "Tomas Silva": (9, 1, 0), "Jordan Avery": (2, 0, 1),
}

# (employee, leave_type, start, end, status, reason, note, approved)
LEAVE_REQUESTS = [
    ("Sam Okafor", "Annual Leave", date(2026, 9, 7), date(2026, 9, 11), "pending",
     "Family trip to Portugal", None, False),
    ("Liam Torres", "Personal Leave", date(2026, 8, 24), date(2026, 8, 24), "pending",
     "Moving to a new apartment", None, False),
    ("Elena Petrova", "Annual Leave", date(2026, 10, 5), date(2026, 10, 9), "pending",
     "Autumn break with the kids", None, False),
    ("Marcus Webb", "Sick Leave", date(2026, 8, 18), date(2026, 8, 19), "pending",
     "Recovering from the flu", None, False),
    ("Tomas Silva", "Annual Leave", date(2026, 8, 4), date(2026, 8, 15), "approved",
     "Beach vacation in Portugal", None, True),
    ("Jordan Avery", "Personal Leave", date(2026, 8, 24), date(2026, 8, 25), "pending",
     "Personal day — family matter", None, False),
    ("Priya Nair", "Personal Leave", date(2026, 7, 24), date(2026, 7, 24), "approved",
     "Personal errand", None, True),
    ("Aisha Bello", "Annual Leave", date(2026, 8, 10), date(2026, 8, 14), "approved",
     "Visiting family", None, True),
    ("Marcus Webb", "Annual Leave", date(2026, 8, 3), date(2026, 8, 7), "rejected",
     "Requested time off", "Q3 launch week — all hands required", True),
    ("Noa Berg", "Personal Leave", date(2026, 7, 10), date(2026, 7, 10), "rejected",
     "Personal matters", "Portfolio review in progress — try next month", True),
]

# (name, description, type, value, active)
DEDUCTION_RULES = [
    ("Health Insurance", "Monthly company health plan premium", "fixed", 150.00, True),
    ("Income Tax", "Standard income tax withholding", "percentage", 12.00, True),
    ("Student Loan Repayment", "Voluntary student loan repayment plan", "fixed", 50.00, False),
]

MOZILLA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

TIME_ENTRY_NOTES = [
    "WFH",
    "Late start — appointment",
    "Focus day, no meetings",
    "Commuter delay",
    "Covered on-call for part of the day",
]


async def main() -> None:
    async with async_session() as db:
        # 1. Wipe demo-owned tables (CASCADE handles FKs), keep the admin user.
        await db.execute(
            text(
                "TRUNCATE TABLE payroll_entries, payroll_runs, leave_requests, "
                "leave_balances, time_entries, employees, departments, "
                "leave_types, deduction_rules, audit_logs RESTART IDENTITY CASCADE"
            )
        )
        await db.execute(
            text("DELETE FROM users WHERE email != :admin"),
            {"admin": "admin@example.com"},
        )
        await db.commit()

        admin = (
            await db.execute(
                select(User).where(User.email == "admin@example.com")
            )
        ).scalar_one()

        # 2. Departments
        depts: dict[str, Department] = {}
        for name, desc in DEPARTMENTS:
            d = Department(name=name, description=desc)
            db.add(d)
            depts[name] = d
        await db.flush()

        # 3. Employees
        emps: dict[str, Employee] = {}
        for first, last, email, phone, position, dept, salary, status, hire, mgr, addr in EMPLOYEES:
            e = Employee(
                first_name=first, last_name=last, email=email, phone=phone,
                department=dept, position=position, hire_date=hire,
                salary_base=salary, address=addr, status=status,
                department_id=depts[dept].id,
            )
            db.add(e)
            emps[f"{first} {last}"] = e
            await db.flush()
            if mgr:
                e.manager_id = emps[mgr].id

        # ── Demo login accounts (role-aware UI walkthrough) ──────────────
        # Jordan Avery is the admin's employee record so the admin's own
        # self-service pages also show data. A manager and a plain employee
        # account demo the role-aware UI: the manager gets approvals and
        # dashboard views, the employee gets the self-service "My Home".
        demo_accounts = [
            ("manager@example.com", "manager123", UserRole.MANAGER, "Elena Petrova"),
            ("employee@example.com", "employee123", UserRole.EMPLOYEE, "Sam Okafor"),
        ]
        for email, password, role, linked_name in demo_accounts:
            demo_user = User(
                email=email,
                hashed_password=bcrypt.hashpw(
                    password.encode("utf-8"), bcrypt.gensalt()
                ).decode("utf-8"),
                role=role,
                is_active=True,
            )
            db.add(demo_user)
            await db.flush()
            emps[linked_name].user_id = demo_user.id

        emps["Jordan Avery"].user_id = admin.id
        await db.commit()

        # 4. Leave types
        ltypes: dict[str, LeaveType] = {}
        for name, desc, dpy, maxc, paid, color, appr in LEAVE_TYPES:
            lt = LeaveType(
                name=name, description=desc, days_per_year=dpy,
                max_consecutive_days=maxc, is_paid=paid, color=color,
                requires_approval=appr, active=True,
            )
            db.add(lt)
            ltypes[name] = lt
        await db.flush()

        # 5. Leave balances for the current year
        for full, (annual_used, sick_used, personal_used) in LEAVE_BALANCES.items():
            emp = emps[full]
            db.add(LeaveBalance(
                employee_id=emp.id, leave_type_id=ltypes["Annual Leave"].id,
                year=YEAR, allocated=25.0, used=float(annual_used),
            ))
            db.add(LeaveBalance(
                employee_id=emp.id, leave_type_id=ltypes["Sick Leave"].id,
                year=YEAR, allocated=10.0, used=float(sick_used),
            ))
            db.add(LeaveBalance(
                employee_id=emp.id, leave_type_id=ltypes["Personal Leave"].id,
                year=YEAR, allocated=5.0, used=float(personal_used),
            ))
        await db.flush()

        # 6. Leave requests
        for full, ltype_name, start, end, status, reason, note, approved in LEAVE_REQUESTS:
            emp = emps[full]
            db.add(LeaveRequest(
                employee_id=emp.id, leave_type_id=ltypes[ltype_name].id,
                department_id=emp.department_id, start_date=start, end_date=end,
                days_requested=float((end - start).days + 1), status=status,
                reason=reason, manager_note=note,
                approved_by=admin.id if approved else None,
            ))
        await db.commit()

        # 6b. Time entries — realistic clock in/out days per active employee,
        #     skipping weekdays covered by an approved leave request.
        approved_days: dict[str, set[date]] = {}
        for full, _ltype, start, end, lstatus, *_rest in LEAVE_REQUESTS:
            if lstatus != "approved":
                continue
            days = approved_days.setdefault(full, set())
            d = start
            while d <= end:
                days.add(d)
                d += timedelta(days=1)

        # The employee demo account (Sam) keeps the most recent weekday
        # "open" — clocked in but not clocked out — so the UI can show a
        # live clock-out flow.
        open_day = TIME_ENTRY_END
        while open_day.weekday() >= 5:  # Saturday=5, Sunday=6
            open_day -= timedelta(days=1)
        open_emp = emps["Sam Okafor"]

        rng = random.Random(42)
        time_entries = 0
        d = TIME_ENTRY_START
        while d <= TIME_ENTRY_END:
            if d.weekday() < 5:
                for full, e in emps.items():
                    if e.status not in ("active", "on_leave"):
                        continue
                    if d in approved_days.get(full, set()):
                        continue
                    if full == "Sam Okafor" and d == open_day:
                        continue
                    in_min = 9 * 60 + rng.randint(-25, 25)
                    roll = rng.random()
                    work_h = 9.0 + rng.randint(0, 60) / 60.0 if roll < 0.15 else (
                        4.0 if roll < 0.23 else 8.0
                    )
                    breaks = rng.choice([0, 30, 30, 45, 60])
                    out_min = in_min + int(work_h * 60 + breaks)
                    note = rng.choice(TIME_ENTRY_NOTES) if rng.random() < 0.04 else None
                    db.add(TimeEntry(
                        employee_id=e.id, work_date=d,
                        clock_in=time(in_min // 60, in_min % 60),
                        clock_out=time(out_min // 60 % 24, out_min % 60),
                        breaks_minutes=breaks, notes=note,
                    ))
                    time_entries += 1
            d += timedelta(days=1)

        db.add(TimeEntry(
            employee_id=open_emp.id, work_date=open_day,
            clock_in=time(8, 52), clock_out=None, breaks_minutes=0,
        ))
        time_entries += 1
        await db.commit()

        # 7. Deduction rules
        for name, desc, dtype, value, active in DEDUCTION_RULES:
            db.add(DeductionRule(
                name=name, description=desc, deduction_type=dtype,
                value=value, active=active,
            ))
        await db.commit()

        # 8. Payroll runs: processed July (entries via the app's own service),
        #    draft August (processed live during the walkthrough).
        july = PayrollRun(
            period_start=date(2026, 7, 1), period_end=date(2026, 7, 31),
            status="processed", notes="July payroll — all departments",
            generated_at=datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc),
        )
        db.add(july)
        await db.commit()
        # Eager-load entries the same way the API does (lazy="selectin"
        # relationships must be loaded in an awaited query, not on access).
        july = (
            await db.execute(
                select(PayrollRun)
                .options(selectinload(PayrollRun.entries))
                .where(PayrollRun.id == july.id)
            )
        ).scalar_one()
        july_entries = await calculate_payroll_for_run(db, july)
        await db.refresh(july)

        august = PayrollRun(
            period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
            status="draft", notes="August payroll",
        )
        db.add(august)
        await db.commit()

        # 9. Audit trail (most recent first in the UI)
        rows = [
            ("login", "user", None, {"new": {"email": "admin@example.com"}},
             datetime(2026, 8, 15, 8, 5, tzinfo=timezone.utc)),
            ("deduction_rule.created", "deduction_rule", None,
             {"new": {"name": "Student Loan Repayment", "value": 50.0}},
             datetime(2026, 8, 14, 16, 20, tzinfo=timezone.utc)),
            ("leave_request.approved", "leave_request", None,
             {"old": {"status": "pending"}, "new": {"status": "approved"}},
             datetime(2026, 8, 14, 9, 42, tzinfo=timezone.utc)),
            ("employee.created", "employee", None,
             {"new": {"name": "David Park", "position": "Sales Operations Analyst"}},
             datetime(2026, 8, 12, 11, 15, tzinfo=timezone.utc)),
            ("payroll_run.processed", "payroll_run", july.id,
             {"new": {"status": "processed", "entries": len(july_entries)}},
             datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)),
        ]
        for action, entity, entity_id, changes, ts in rows:
            db.add(AuditLog(
                user_id=admin.id, action=action, entity=entity,
                entity_id=entity_id, changes=changes,
                ip_address="192.168.1.42", user_agent=MOZILLA, timestamp=ts,
            ))
        await db.commit()

        n_emp = len(emps)
        print(
            f"[demo-seed] Done: {len(DEPARTMENTS)} departments, {n_emp} employees, "
            f"{len(LEAVE_TYPES)} leave types, {len(LEAVE_BALANCES)} "
            f"balance sets, {len(LEAVE_REQUESTS)} leave requests, "
            f"{len(DEDUCTION_RULES)} deduction rules, {time_entries} time entries, "
            f"July run processed ({len(july_entries)} entries), August run draft."
        )
        print(
            "[demo-seed] Login accounts: admin@example.com (password from "
            "SEED_ADMIN_PASSWORD), manager@example.com / manager123, "
            "employee@example.com / employee123"
        )


if __name__ == "__main__":
    asyncio.run(main())

"""API v1 router barrel — all versioned routes are mounted here."""

from fastapi import APIRouter

from app.api.v1 import auth, employees, departments, leave_types, leave_balances, leave_requests  # noqa: F401
from app.api.v1 import payroll_runs, deduction_rules, audit_logs, dashboard, attendance, notifications  # noqa: F401
from app.api.v1 import reviews  # noqa: F401

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(employees.router, prefix="/employees", tags=["Employees"])
router.include_router(departments.router, prefix="/departments", tags=["Departments"])
router.include_router(leave_types.router, prefix="/leave-types", tags=["Leave Types"])
router.include_router(leave_balances.router, prefix="/leave-balances", tags=["Leave Balances"])
router.include_router(leave_requests.router, prefix="/leave-requests", tags=["Leave Requests"])
router.include_router(payroll_runs.router, prefix="/payroll-runs", tags=["Payroll Runs"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(deduction_rules.router, prefix="/deduction-rules", tags=["Deduction Rules"])
router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
# Review routes own two top-level paths (/review-cycles, /reviews) — no extra prefix.
router.include_router(reviews.router, prefix="", tags=["Performance Reviews"])
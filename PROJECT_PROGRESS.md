# Arella HR — Project Progress

## Project: Arella HR (SMB 50-500 employees)
Stack: FastAPI + SQLAlchemy async + Alembic + PostgreSQL | React + TypeScript + Vite + Tailwind + shadcn/ui + TanStack Router/Query

---

## Phase 1 — Project Scaffold & Foundation

- [x] Backend: FastAPI app, SQLAlchemy engine, Alembic init, pydantic-settings config
- [x] Frontend: Vite + React + TypeScript + Tailwind + TanStack Router + TanStack Query
- [x] Docker Compose: app + PostgreSQL
- [x] Health check endpoint, basic 404 handling
- [x] Base test setup (pytest + vitest)
- [x] shadcn/ui primitives installed
- [x] API client (`frontend/src/lib/api.ts`)
- [x] Auth hook (`frontend/src/lib/auth.ts`)

## Phase 2 — Authentication & Authorization

- [x] User model (email, hashed password, role, is_active, created_at)
- [x] `/auth/register`, `/auth/login`, `/auth/me`, `/auth/refresh` endpoints
- [x] JWT access (15m) + refresh (7d) tokens
- [x] Role-based route guards (frontend + backend decorators)
- [x] Password reset endpoint
- [x] Admin seed script (creates initial superadmin)
- [x] Alembic migration for user table

## Phase 3 — Employee Directory (CRUD)

- [x] Employee model (first_name, last_name, email, phone, department, position, hire_date, manager_id, status, salary_base, address, etc.)
- [x] CRUD endpoints: list (paginated, searchable, filterable), create, read, update, deactivate
- [x] Manager hierarchy (self-referential FK → Employee)
- [x] Org chart endpoint (tree structure)
- [x] Frontend: Employee list page with search/filter, add/edit modal, status toggle
- [x] CSV export
- [x] Alembic migration for employee table

## Phase 4 — Leave & Attendance

> **Goal file:** [goals/phase4-leave-attendance.md](goals/phase4-leave-attendance.md)

- [x] Models: Department, LeaveType, LeaveBalance, LeaveRequest
- [x] Schemas: Pydantic Out/Create/Update for all 4 models
- [x] CRUD: create, list, update, delete departments/leave types; manage leave requests
- [x] API: 13+ endpoints (types CRUD, requests CRUD, approvals, balances, departments)
- [x] Service layer: `services/leave.py` — balance computation, yearly allocation, validation, department leaves
- [x] Frontend: lib/leave.ts API client (190 lines)
- [x] Frontend: routes/leave.tsx (470 lines, embedded components: StatCard, StatusBadge, LeaveFormDialog, LeavePage)
- [ ] ~~Frontend: features/leave/ components (MyLeave, RequestLeave, ApprovalQueue, LeaveCalendar)~~ — directory exists but empty; everything is embedded in routes/leave.tsx
- [x] Frontend: route registration in routes/index.ts (imports LeavePage)
- [x] Backend: router registered in api/v1/__init__.py
- [x] Alembic migration for leave tables: `b2c3d4e5f6a7_add_leave_tables.py` (chain: `fcb3de592fd2` → `a1b2c3d4e5f6` → `b2c3d4e5f6a7`)

## Phase 5 — Payroll & Compensation

- [x] PayrollRun model (period_start, period_end, status, generated_at)
- [x] PayrollEntry model (payroll_run_id, employee_id, gross_salary, deductions, bonuses, net_pay)
- [x] DeductionRule model (name, type, value, description)
- [x] Pydantic schemas + CRUD + API endpoints
- [x] Payroll calculation service (services/payroll.py)
- [x] Frontend: PayrollRuns, DeductionRules, PayrollPage, route
- [x] Alembic migration for payroll tables
- [ ] ~~Payslip generation~~ (PDF/HTML — skipped)
- [ ] ~~CSV import for payroll~~ (skipped)

## Phase 6 — Polish & Production

- [ ] Audit log model (who changed what, when) + API endpoint
- [ ] Email notifications (mocked to console)
- [ ] Rate limiting on auth endpoints
- [ ] Input validation and structured error handling
- [ ] Frontend: responsive layout, navigation sidebar, loading states, empty states
- [ ] Docker production build steps
- [ ] README with setup instructions
- [ ] Frontend tests (vitest)
- [ ] Backend tests (pytest integration)

---

## File Inventory

### Backend
```
backend/app/
├── models/        # user.py, employee.py, payroll.py, department.py, leave_type.py, leave_balance.py, leave_request.py
├── schemas/       # user.py, employee.py, payroll.py, department.py, leave_type.py, leave_balance.py, leave_request.py
├── crud/          # user.py, employee.py, payroll.py, department.py, leave_type.py, leave_balance.py, leave_request.py
├── api/v1/        # auth.py, employees.py, payroll.py, departments.py, leave_types.py, leave_balances.py, leave_requests.py
├── services/      # payroll.py, leave.py
├── middleware/    # auth.py
├── utils/         # [exists]
└── ...
backend/alembic/versions/  # fcb3de592fd2_initial, a1b2c3d4e5f6_payroll, b2c3d4e5f6a7_leave_tables (all verified vs models)
```

### Frontend
```
frontend/src/
├── features/      # employees/, payroll/, leave/ (directory exists but empty)
├── lib/           # employees.ts, payroll.ts, auth.ts, leave.ts
├── routes/        # index.ts, employees.tsx, payroll.tsx, leave.tsx (470 lines, embedded components)
├── components/ui/ # [shadcn components]
└── ...
```

---

## Priority Order

1. ~~**Phase 4 — Alembic migration**~~ ✅ Complete (verified against models)
2. ~~**Phase 4 — Service layer**~~ ✅ Complete (`services/leave.py`)
3. **Phase 4 — Frontend features** — refactor `routes/leave.tsx` into `features/leave/` components or keep as-is
4. **Phase 6 — Polish** (README, Docker, audit log, email, tests)
5. **Phase 5 extras** — Payslip generation, CSV import (nice-to-have)
# Arella HR - Complete Project Goals

## Project: Arella HR (SMB 50-500 employees)

**Stack:** FastAPI + SQLAlchemy async + Alembic + PostgreSQL | React + TypeScript + Vite + Tailwind + shadcn/ui + TanStack Router/Query

**Auth:** JWT access tokens (15m) + refresh tokens (7d), bcrypt password hashing, role-based access (admin / manager / employee)

## Architecture

```
arella-hr/
├── backend/               # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── main.py        # App factory, middleware, lifespan
│   │   ├── config.py       # Settings (pydantic-settings)
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic v2 request/response schemas
│   │   ├── crud/           # Database operations
│   │   ├── api/v1/         # Route endpoints
│   │   ├── services/       # Business logic
│   │   ├── middleware/     # Auth, rate limiting
│   │   └── utils/          # Helpers
│   ├── alembic/            # Migrations
│   ├── tests/              # pytest
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/              # React 19 + TypeScript + Vite
│   ├── src/
│   │   ├── routes/         # TanStack Router pages
│   │   ├── features/       # Domain components
│   │   ├── lib/            # API client, auth hooks, types
│   │   ├── components/ui/  # shadcn/ui primitives
│   │   └── ...
│   ├── tests/              # vitest
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml      # App + PostgreSQL + pgAdmin
├── .env.example
└── README.md
```

## Existing Code Patterns

- Backend models: `Mapped` type annotations, `mapped_column`, declarative Base, relationships with `selectin` lazy loading
- Schemas: Pydantic v2 with `from_attributes = True`
- CRUD: Functions taking `db: AsyncSession`, using SQLAlchemy `select` statements
- API routes: `APIRouter`, `get_db` dependency, `@router.get(..., response_model=...)`
- Frontend: TanStack Router, TanStack Query, shadcn/ui, lucide-react icons, toast notifications
- Pagination: offset-based with `total_pages` on all list endpoints

## Alembic Migration Chain

```
fcb3de592fd2 (initial) -> a1b2c3d4e5f6 (payroll) -> b2c3d4e5f6a7 (leave tables)
```

---

## Phase 1: Project Scaffold & Foundation (COMPLETE)

Create the project structure and build foundation.

### Step 1: Monorepo Structure

Create `arella-hr/` with `backend/` and `frontend/` directories.

### Step 2: Backend Setup

- FastAPI app with `main.py` (app factory, middleware, lifespan)
- SQLAlchemy async engine setup
- Alembic init with `async_support = True`
- pydantic-settings `config.py` with all required settings
- `requirements.txt` with dependencies: fastapi, uvicorn, sqlalchemy[asyncio], alembic, pydantic-settings, asyncpg, psycopg2-binary, python-jose, passlib, bcrypt, httpx, pytest, pytest-asyncio

### Step 3: Frontend Setup

- Vite + React + TypeScript + Tailwind CSS
- TanStack Router with file-based routing
- TanStack Query for data fetching
- shadcn/ui primitives installed
- Base test setup: vitest config

### Step 4: Docker Compose

- `docker-compose.yml` with backend service + PostgreSQL service
- PostgreSQL with named volume for data persistence

### Step 5: Health Check & 404 Handling

- `GET /api/health` returns ok status
- All unknown routes return 404

### Deliverables

```
backend/app/main.py              ← new
backend/app/config.py             ← new
backend/alembic/                  ← new (alembic init)
backend/requirements.txt          ← new
frontend/src/main.tsx             ← new
frontend/src/App.tsx              ← new
frontend/src/routes/              ← new (TanStack Router file routes)
docker-compose.yml                ← new
frontend/tests/                   ← new (vitest setup)
backend/tests/                    ← new (pytest setup)
frontend/package.json             ← new
```

---

## Phase 2: Authentication & Authorization (COMPLETE)

Implement user auth with JWT, role-based access control, and password management.

### Step 1: User Model

Create `backend/app/models/user.py`:

- `id`: int, PK, auto-increment
- `email`: str, unique, indexed, required
- `hashed_password`: str, required
- `role`: str, enum: "admin", "manager", "employee", default "employee"
- `is_active`: bool, default True
- `created_at`: datetime (UTC)
- `refresh_tokens`: relationship to RefreshToken (one-to-many)

### Step 2: Refresh Token Model

Create `backend/app/models/refresh_token.py`:

- `id`: int, PK, auto-increment
- `token`: str, unique, required
- `user_id`: int, FK to User
- `expires_at`: datetime (UTC)
- `created_at`: datetime (UTC)

### Step 3: Pydantic Schemas

Create `backend/app/schemas/user.py`:

- `UserCreate`: email, password
- `UserLogin`: email, password
- `UserOut`: id, email, role, is_active, created_at
- `TokenOut`: access_token, refresh_token, token_type
- `PasswordReset`: email
- `PasswordResetConfirm`: token, new_password

### Step 4: Auth Service

Create `backend/app/services/auth.py`:

- `create_access_token(user_id)` -> str (15 min expiry)
- `create_refresh_token(user_id)` -> str (7 day expiry, stored in DB)
- `decode_access_token(token)` -> user_id or None
- `decode_refresh_token(token)` -> user_id or None
- `hash_password(password)` -> str
- `verify_password(plain, hashed)` -> bool

### Step 5: Auth Middleware

Create `backend/app/middleware/auth.py`:

- `get_current_user` dependency: extracts JWT from Authorization header, validates, returns user
- `require_role(*roles)` decorator: checks user role against required roles
- `get_db` dependency: provides async session

### Step 6: Auth API Routes

Create `backend/app/api/v1/auth.py`:

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | /api/v1/auth/register | public | Register new user (employee role) |
| POST | /api/v1/auth/login | public | Login, returns access + refresh tokens |
| POST | /api/v1/auth/refresh | public | Refresh access token using refresh token |
| GET | /api/v1/auth/me | authenticated | Get current user info |
| POST | /api/v1/auth/password-reset | public | Request password reset (email mock) |
| POST | /api/v1/auth/password-reset-confirm | public | Confirm password reset with token |

### Step 7: Seed Script

Create `backend/seed.py`:

- Creates initial superadmin user (email: admin@example.com, password: Admin123!)
- Hashes password with bcrypt before storing
- Runs within database session

### Step 8: Alembic Migration

Generate migration for user and refresh_token tables: `fcb3de592fd2_initial`

### Frontend Auth Setup

- `frontend/src/lib/auth.ts`: auth hook with login/logout, token management, role checks
- `frontend/src/lib/api.ts`: API client with JWT bearer token attachment, auto-refresh on 401
- Route guards in TanStack Router: protect routes by role
- Login page component
- Protected layout wrapper

### Deliverables

```
backend/app/models/user.py             ← new
backend/app/models/refresh_token.py    ← new (or within user.py)
backend/app/schemas/user.py            ← new
backend/app/services/auth.py           ← new
backend/app/middleware/auth.py         ← new (or auth middleware within existing middleware/)
backend/app/api/v1/auth.py             ← new
backend/seed.py                        ← new
backend/alembic/versions/xxx_initial.py← generated
frontend/src/lib/auth.ts               ← new
frontend/src/lib/api.ts                ← new
frontend/src/routes/login.tsx          ← new
frontend/src/routes/__root.tsx         ← modify (auth layout)
frontend/src/routes/index.ts           ← new (route index)
```

### Success Criteria

1. Can register a new user
2. Can login and receive JWT tokens
3. Can refresh access token with refresh token
4. Current user endpoint returns user info with role
5. Route guards prevent unauthorized access
6. Seed script creates initial superadmin

---

## Phase 3: Employee Directory (COMPLETE)

Full CRUD for employee records with org chart, search, filter, and CSV export.

### Step 1: Employee Model

Create `backend/app/models/employee.py`:

- `id`: int, PK, auto-increment
- `first_name`: str, required
- `last_name`: str, required
- `email`: str, unique, indexed, required
- `phone`: str, nullable
- `department`: str (department name as text, or FK if normalized)
- `position`: str, required
- `hire_date`: date, required
- `manager_id`: int, FK to Employee (self-referential, nullable), sets up hierarchy
- `status`: str, enum: "active", "inactive", "on_leave", default "active"
- `salary_base`: float, nullable
- `address`: str, nullable
- `date_of_birth`: date, nullable
- `emergency_contact`: str, nullable
- `created_at`: datetime (UTC)
- `updated_at`: datetime (UTC)
- Relationships: `manager` (self-ref, backref='direct_reports'), `leaves` (to LeaveRequest), `approved_leaves` (leave requests this employee approved)

### Step 2: Pydantic Schemas

Create `backend/app/schemas/employee.py`:

- `EmployeeCreate`: first_name, last_name, email, phone, department, position, hire_date, manager_id (optional), salary_base (optional), address (optional)
- `EmployeeUpdate`: all updatable fields
- `EmployeeOut`: all fields plus id, status, created_at, updated_at, manager_name (computed)
- `EmployeeSearch`: query (search), department (filter), status (filter), page, page_size
- `PaginationOut`: items, total, page, page_size, total_pages

### Step 3: CRUD Operations

Create `backend/app/crud/employee.py`:

- `create_employee(db, schema)` — create new employee, check email uniqueness
- `get_employee(db, id)` — single employee lookup, returns None if not found
- `list_employees(db, search, department, status, page, page_size)` — paginated, searchable by name/email, filterable by department and status
- `update_employee(db, id, schema)` — partial update
- `deactivate_employee(db, id)` — set status=inactive
- `get_org_chart(db)` — recursive org tree from root managers

### Step 4: API Routes

Create `backend/app/api/v1/employees.py`:

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | /api/v1/employees | admin/manager | Create employee |
| GET | /api/v1/employees | authenticated | List (paginated, searchable, filterable) |
| GET | /api/v1/employees/{id} | authenticated | Get single employee |
| PUT | /api/v1/employees/{id} | admin/manager | Update employee |
| PATCH | /api/v1/employees/{id} | admin/manager | Partial update employee |
| DELETE | /api/v1/employees/{id} | admin | Deactivate employee (soft delete) |
| GET | /api/v1/employees/org-chart | authenticated | Org chart tree structure |
| GET | /api/v1/employees/export/csv | authenticated | Export employees as CSV |

### Step 5: Frontend — Employee Page

Create `frontend/src/routes/employees.tsx`:

- Stat cards: Total Employees, Active, Inactive, New This Month
- Search bar with debounced input
- Department and status filter dropdowns
- Employee table: name, email, department, position, status, actions
- Status badge (color-coded): active=green, inactive=gray, on_leave=yellow
- Add Employee button opens dialog with form
- Edit inline or via dialog
- Pagination controls
- Export CSV button
- Role-based: only admin/manager can add/edit/delete

### Step 6: Frontend — API Client

Create `frontend/src/lib/employees.ts`:

- Types: `EmployeeOut`, `EmployeeCreate`, `EmployeeUpdate`, `PaginationResult`
- Functions: `listEmployees(params?)`, `getEmployee(id)`, `createEmployee(body)`, `updateEmployee(id, body)`, `deactivateEmployee(id)`, `exportCsv()`
- Org chart: `getOrgChart()`

### Deliverables

```
backend/app/models/employee.py       ← new
backend/app/schemas/employee.py      ← new
backend/app/crud/employee.py         ← new
backend/app/api/v1/employees.py      ← new
frontend/src/routes/employees.tsx    ← new
frontend/src/lib/employees.ts        ← new
backend/alembic/versions/a1b2c3d4e5f6.py  ← generated (payroll migration, also covers employee FKs)
```

---

## Phase 4: Leave & Attendance (COMPLETE)

Leave request workflow, balance management, approval queue, and calendar view.

### Step 1: Models

Create models in `backend/app/models/` directory (4 models):

**Department:**
- `id`: int, PK, auto-increment
- `name`: str, unique, indexed, required
- `description`: str (text), nullable
- `manager_id`: int, FK to Employee, nullable, on_delete=SET NULL
- `created_at`: datetime (UTC)
- `updated_at`: datetime (UTC)

**LeaveType:**
- `id`: int, PK, auto-increment
- `name`: str, unique, required
- `description`: str (255 char), nullable
- `days_per_year`: numeric(5,1), default 25.0
- `max_consecutive_days`: int, default 5
- `is_paid`: bool, default True
- `color`: str (hex), default "#3b82f6"
- `requires_approval`: bool, default True
- `active`: bool, default True
- `created_at`: datetime (UTC)

**LeaveBalance:**
- `id`: int, PK, auto-increment
- `employee_id`: int, FK to Employee, cascade delete
- `leave_type_id`: int, FK to LeaveType, cascade delete
- `year`: int, required
- `allocated`: numeric(6,1), default 0
- `used`: numeric(6,1), default 0
- `carried_over`: numeric(6,1), default 0
- `created_at`: datetime (UTC)
- `updated_at`: datetime (UTC)
- Unique constraint: (employee_id, leave_type_id, year)
- Index: (employee_id, year)

**LeaveRequest:**
- `id`: int, PK, auto-increment
- `employee_id`: int, FK to Employee, cascade delete
- `leave_type_id`: int, FK to LeaveType, cascade delete
- `department_id`: int, FK to Department, nullable
- `start_date`: date, required
- `end_date`: date, required
- `days_requested`: float, required
- `status`: str, enum: "pending", "approved", "rejected", "cancelled", default "pending"
- `reason`: str (500 char), nullable
- `approved_by`: int, FK to User, nullable
- `manager_note`: str (text), nullable
- `created_at`: datetime (UTC)
- `updated_at`: datetime (UTC)
- Index: (employee_id, status)

### Step 2: Pydantic Schemas

Create `backend/app/schemas/leave.py`:

- `DepartmentCreate/Update/Out`
- `LeaveTypeCreate/Update/Out`
- `LeaveBalanceOut`: with computed `remaining` property
- `LeaveRequestCreate`: leave_type_id, start_date, end_date, reason (optional)
- `LeaveRequestUpdate`: status, manager_note
- `LeaveRequestOut`: all fields plus employee_name, leave_type_name
- `LeaveSummary`: year, types (list of per-type info), totals
- `LeaveFilter`: employee_id, status, type_id, start_date, end_date, page, page_size

### Step 3: CRUD

Create `backend/app/crud/leave.py`:

- CRUD for Department and LeaveType
- `create_leave_request(db, employee_id, schema)` — validate: end >= start, not in past, sufficient balance, status=pending
- `list_leave_requests(db, filters)` — paginated, filterable
- `get_leave_request(db, id)` — single lookup
- `approve_leave_request(db, id, manager_note)` — set status=approved, update LeaveBalance.used
- `reject_leave_request(db, id, manager_note)` — set status=rejected
- `cancel_leave_request(db, id)` — only if pending, by requesting employee
- `allocate_yearly_balances(db, year)` — create/update balance records for all active employees and active leave types

### Step 4: Service Layer

Create `backend/app/services/leave.py`:

- `validate_request_balance(db, employee_id, leave_type_id, days_requested)` — raises ValueError if insufficient balance or past dates
- `get_employee_leave_summary(db, employee_id, year)` — returns dict with all leave types: name, allocated, used, remaining, carried_over, utilization_pct
- `get_manager_pending_count(db, manager_id)` — returns count of pending requests from direct reports
- `allocate_yearly_balances(db, year)` — for every active employee and active leave type, create or update LeaveBalance
- `get_remaining_days(db, employee_id, leave_type_id, year)` — return allocated, used, remaining, carried_over
- `get_department_leaves(db, department_id, year)` — return leave request counts for all employees in a department

### Step 5: API Routes

Create `backend/app/api/v1/leave.py`:

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | /api/v1/leave/types | admin only | Create leave type |
| GET | /api/v1/leave/types | all | List leave types (paginated) |
| PUT | /api/v1/leave/types/{id} | admin only | Update leave type |
| DELETE | /api/v1/leave/types/{id} | admin only | Delete leave type |
| POST | /api/v1/leave/requests | authenticated | Submit leave request |
| GET | /api/v1/leave/requests | authenticated | List (employees=own, managers=team, admins=all) |
| PUT | /api/v1/leave/requests/{id} | manager/admin | Approve/reject request |
| DELETE | /api/v1/leave/requests/{id} | employee/admin | Cancel request |
| GET | /api/v1/leave/requests/pending-count | manager/admin | Count pending requests |
| GET | /api/v1/leave/balances | authenticated | List balances |
| GET | /api/v1/leave/balance/{employee_id} | authenticated | Single employee balance |
| POST | /api/v1/leave/allocate | admin only | Trigger yearly allocation |
| GET | /api/v1/leave/summary/{employee_id} | authenticated | Leave summary with computed fields |

### Step 6: Frontend — Leave Page

Create `frontend/src/routes/leave.tsx` (embedded components, ~470 lines):

- Tab wrapper with 4 tabs: My Leave, Request Leave, Approval Queue, Calendar
- **StatCard**: reusable stat card component (icon, label, value, color)
- **StatusBadge**: color-coded status badges (pending=yellow, approved=green, rejected=red, cancelled=gray)
- **MyLeave**: employee's leave summary with balance table and past requests table
- **RequestLeave**: date range picker, leave type dropdown, remaining balance display, reason textarea, submit with validation and toast
- **ApprovalQueue**: manager/admin only, table of pending requests with inline approve/reject, reject opens manager note input, approve confirms via AlertDialog
- **LeaveCalendar**: upcoming approved leaves list (placeholder for full calendar)

Frontend also has:
- `frontend/src/lib/leave.ts`: API client with 190 lines (types + API functions)
- `frontend/src/features/leave/` — directory exists but empty (components are embedded in routes/leave.tsx)

### Step 7: Alembic Migration

Generated: `b2c3d4e5f6a7_add_leave_tables.py` creating 4 tables: departments, leave_types, leave_balances, leave_requests with correct constraints, foreign keys, and indexes.

### Deliverables

```
backend/app/models/department.py     ← new
backend/app/models/leave_type.py     ← new
backend/app/models/leave_balance.py  ← new
backend/app/models/leave_request.py  ← new
backend/app/schemas/leave.py         ← new
backend/app/crud/leave.py            ← new
backend/app/services/leave.py        ← new
backend/app/api/v1/leave.py          ← new
frontend/src/routes/leave.tsx        ← new (embedded components)
frontend/src/lib/leave.ts            ← new
backend/alembic/versions/b2c3d4e5f6a7.py  ← generated
```

### Known Gap

The `frontend/src/features/leave/` directory exists but is empty. All leave components are embedded within `routes/leave.tsx` (~470 lines). Refactoring into separate feature components is optional but recommended for long-term maintainability.

---

## Phase 5: Payroll & Compensation (COMPLETE)

Payroll run management, deduction rules, automated salary calculation, and payslip generation.

### Step 1: Models

Create models in `backend/app/models/`:

**PayrollRun:**
- `id`: int, PK, auto-increment
- `period_start`: date, required
- `period_end`: date, required
- `status`: str, enum: "draft", "processing", "processed", "paid", default "draft"
- `generated_at`: datetime (UTC), nullable
- `created_at`: datetime (UTC)
- `updated_at`: datetime (UTC)
- Relationships: entries (one-to-many)

**PayrollEntry:**
- `id`: int, PK, auto-increment
- `payroll_run_id`: int, FK to PayrollRun, cascade delete
- `employee_id`: int, FK to Employee, cascade delete (also unique with payroll_run_id)
- `gross_salary`: numeric(10,2), required, default 0
- `deductions`: numeric(10,2), required, default 0
- `bonuses`: numeric(10,2), required, default 0
- `net_pay`: numeric(10,2), required, default 0
- `created_at`: datetime (UTC)
- Unique constraint: (payroll_run_id, employee_id)

**DeductionRule:**
- `id`: int, PK, auto-increment
- `name`: str, required, unique
- `type`: str, enum: "fixed", "percentage", required
- `value`: numeric(10,2), required (fixed amount or percentage)
- `description`: str (text), nullable
- `created_at`: datetime (UTC)
- Relationships: entries (one-to-many)

### Step 2: Pydantic Schemas

Create `backend/app/schemas/payroll.py`:

- `PayrollRunCreate`: period_start, period_end
- `PayrollRunUpdate`: status (only for draft/processing/processed/paid transitions)
- `PayrollRunOut`: all fields plus entries list, status
- `PayrollEntryOut`: all fields plus employee_name
- `DeductionRuleCreate/Update/Out`

### Step 3: CRUD

Create `backend/app/crud/payroll.py`:

- CRUD for PayrollRun and DeductionRule
- `create_payroll_entry(db, payroll_run_id, employee_id, salary_base)` — create entry with employee's base salary, 0 deductions
- `update_payroll_entry(db, entry_id, deductions, bonuses)` — adjust deductions and bonuses
- `calculate_payroll_run(db, run_id)` — process all entries: apply deduction rules, compute net_pay
- `delete_payroll_run(db, run_id)` — only if status is "draft"
- `get_payroll_run_entries(db, run_id)` — return entries with employee names

### Step 4: Service Layer

Create `backend/app/services/payroll.py`:

- `calculate_payroll_for_run(db, run_id)` — for each employee: gross = salary_base or entry.gross_salary; apply all active deduction rules (fixed = subtract value, percentage = subtract gross * value / 100); net = gross - total_deductions + bonuses
- `get_payroll_summary(db, period_start, period_end)` — aggregate stats: total payroll, avg compensation, per-department breakdown
- `calculate_employee_payslip(db, entry_id)` — return full payslip breakdown

### Step 5: API Routes

Create `backend/app/api/v1/payroll.py`:

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | /api/v1/payroll/runs | admin only | Create payroll run |
| GET | /api/v1/payroll/runs | admin only | List payroll runs (paginated) |
| GET | /api/v1/payroll/runs/{run_id} | admin only | Single run with entries |
| PUT | /api/v1/payroll/runs/{run_id} | admin only | Update status |
| DELETE | /api/v1/payroll/runs/{run_id} | admin only | Delete draft run |
| POST | /api/v1/payroll/runs/{run_id}/calculate | admin only | Calculate all entries in run |
| PATCH | /api/v1/payroll/entries/{entry_id} | admin only | Adjust deductions/bonuses |
| GET | /api/v1/payroll/entries/{entry_id} | admin only | Single payslip |
| POST | /api/v1/payroll/runs/{run_id}/export/csv | admin only | Export run as CSV |
| GET | /api/v1/payroll/summary | admin only | Payroll summary stats |
| CRUD | /api/v1/payroll/deduction-rules | admin only | Deduction rules CRUD |

### Step 6: Frontend — Payroll Pages

Create `frontend/src/routes/payroll.tsx` and `frontend/src/routes/payroll-runs.tsx`:

- **PayrollRuns**: list of payroll runs with status badges, period display, amount totals, create/run button, export button
- **DeductionRules**: table of rules, add/edit/delete with type selector (fixed/percentage), value input
- **PayrollPage**: detailed view of a single run, employee entries table with gross/deductions/bonuses/net, calculation button, export CSV
- **PayrollSummary**: total payroll bar, department breakdown, avg compensation stat

Frontend also has:
- `frontend/src/lib/payroll.ts`: API client with types + functions
- `frontend/src/routes/index.ts`: imports PayrollPage and registers route

### Step 7: Alembic Migration

Generated: `a1b2c3d4e5f6_payroll.py` creating 3 tables: payroll_runs, payroll_entries, deduction_rules with correct constraints, foreign keys, unique index on (payroll_run_id, employee_id).

### Deliverables

```
backend/app/models/payroll.py        ← new (3 models in one file)
backend/app/schemas/payroll.py       ← new
backend/app/crud/payroll.py          ← new
backend/app/services/payroll.py      ← new
backend/app/api/v1/payroll.py        ← new
frontend/src/routes/payroll.tsx      ← new (runs + rules + page)
frontend/src/lib/payroll.ts          ← new
backend/alembic/versions/a1b2c3d4e5f6.py  ← generated
```

### Skipped (nice-to-have)

- **Payslip PDF generation** — No ReportLab or PDF library integrated
- **CSV import for payroll** — No employee bulk import via CSV

---

## Phase 6: Polish & Production (INCOMPLETE — NEXT TO IMPLEMENT)

Production readiness: documentation, Docker, audit logging, email notifications, rate limiting, structured errors, and tests.

### Step 1: README & Environment

Create `README.md` at project root:
- Project title and one-line description ("Full-featured HR system for SMBs (50–500 employees)")
- Tech stack badges/section
- Quick start: `docker-compose up --build`
- Initial setup: seed script, Alembic migration
- Feature list (auth, employee directory, leave management, payroll)
- Architecture overview
- Environment variables section
- Development notes (how to run separately, how to regenerate migrations)
- API docs link (`/docs` — Swagger UI from FastAPI)

Create `.env.example` with all required variables from `config.py` (DATABASE_URL, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, EMAIL_ENABLED, SMTP_HOST, etc.) with placeholder values.

### Step 2: Docker Hardening

Backend Dockerfile: `python:3.12-slim` base, install system deps, `pip install -r requirements.txt`, copy app, expose 8000, uvicorn entrypoint.
Frontend Dockerfile: Node base, install deps, `npm run build`, nginx static server, proxy `/api` to backend.
Update `docker-compose.yml`: backend service with healthcheck, postgres with pg_isready healthcheck, pgadmin service on port 5050, network configuration.

### Step 3: Audit Log Model + API

**Model** (`backend/app/models/audit_log.py`):
- `id`: int, PK, auto-increment
- `user_id`: int, FK to User, nullable (system actions)
- `action`: str (e.g., "CREATE", "UPDATE", "DELETE", "LOGIN")
- `resource`: str (e.g., "Employee/42", "LeaveRequest/7")
- `details`: str (JSON/text, nullable) — what changed
- `ip_address`: str, nullable
- `created_at`: datetime (UTC)

**Service** (`backend/app/services/audit.py`):
- `create_audit_entry(db, user_id, action, resource, details, ip_address)` — async function, called at end of relevant CRUD/API operations

**Schema** (`backend/app/schemas/audit_log.py`): `AuditLogOut`, `AuditLogFilter` for query params

**CRUD** (`backend/app/crud/audit_log.py`): `list_paginated` with filter support

**API** (`backend/app/api/v1/audit_logs.py`):
| Method | Path | Access |
|--------|------|--------|
| GET | /api/v1/audit-logs | admin only |
| Query params: user_id, action, resource, start_date, end_date, page, page_size | | |

Register router in `api/v1/__init__.py`. Generate Alembic migration for audit_logs table.

### Step 4: Email Notifications (Mocked to Console)

Create `backend/app/services/email.py`:
- `send_email(to, subject, body)` — prints to console with formatting, simulating email send
- No SMTP integration (easy to swap in Resend/Postmark later)
- Wrapped in try/except so failures never crash the request
- `settings.email_enabled: bool = True` (always True, but easy to toggle off)

Hook into existing workflows:
- Leave request submission → email to manager
- Leave request approved/rejected → email to employee
- Payroll run processed → email to employee

### Step 5: Rate Limiting on Auth Endpoints

Create `backend/app/middleware/rate_limit.py`:
- Simple in-memory `RateLimiter` class with per-IP tracking, max N requests per sliding window
- Apply to auth endpoints via FastAPI Depends or middleware layer

Limits:
- `/api/v1/auth/login` — max 10 requests per 5 minutes per IP
- `/api/v1/auth/register` — max 5 requests per 5 minutes per IP
- `/api/v1/auth/refresh` — max 20 requests per 5 minutes per IP

### Step 6: Structured Error Handling

Create `backend/app/utils/errors.py`:
- Custom exceptions: `AppException(BaseException)`, `NotFoundError`, `ValidationError`, `PermissionDeniedError`
- Each exception has a `code` field (machine-readable, e.g., "INSUFFICIENT_BALANCE")
- FastAPI exception handler converts them to structured JSON:

```
{"detail": {"code": "INSUFFICIENT_BALANCE", "message": "..."}}
```

Check existing CRUD functions and replace bare `ValueError`/`HTTPException` with these structured exceptions.

### Step 7: Frontend Polish

- Responsive layout: all pages work on mobile (table wrapping, grid breakpoints)
- Navigation sidebar: collapsible on mobile, icon-only mode
- Stat cards: 4-column on desktop, 2-column on tablet, 1-column on mobile
- Loading states: TanStack Query shows loading skeletons/spinners everywhere
- Empty states: consistent "No data found" messages across all tables

### Step 8: Backend Tests

Create `backend/tests/`:
- `conftest.py`: async fixtures (app, httpx.AsyncClient, db, auth helpers)
- `test_auth.py`: register, login, refresh, me, token expiry
- `test_employees.py`: CRUD, search, filter, pagination
- `test_leave.py`: leave request lifecycle, balance validation, approval flow
- `test_payroll.py`: payroll run creation, processing, entries
- Use `pytest.mark.asyncio` pattern with httpx.AsyncClient

### Step 9: Frontend Tests

Create `frontend/tests/`:
- `setup.ts`: vitest setup with mocks
- `components/*.test.tsx`: test rendering, query invalidation on submit, toast messages
- Test at least: auth hook (login/logout state), one CRUD page (EmployeePage or LeavePage)
- Use `@testing-library/react` with `QueryClientProvider` wrapper

### Deliverables

```
README.md                            ← new
.env.example                         ← new
backend/Dockerfile                   ← verify/update
frontend/Dockerfile                  ← verify/update
docker-compose.yml                   ← update (add pgadmin, healthchecks)
backend/app/models/audit_log.py      ← new
backend/app/schemas/audit_log.py     ← new
backend/app/crud/audit_log.py        ← new
backend/app/api/v1/audit_logs.py     ← new
backend/app/services/audit.py        ← new
backend/app/services/email.py        ← new (mocked)
backend/app/middleware/rate_limit.py ← new
backend/app/utils/errors.py          ← new (structured errors)
backend/alembic/versions/zzz_add_audit_logs.py  ← generated
backend/tests/conftest.py            ← new
backend/tests/test_auth.py           ← new
backend/tests/test_employees.py      ← new
backend/tests/test_leave.py          ← new
backend/tests/test_payroll.py        ← new
frontend/tests/setup.ts              ← new
frontend/tests/components/*.test.tsx ← new (at least 2 test files)
```

### Success Criteria

1. `docker-compose up --build` starts all services, health checks pass
2. `.env.example` has all required variables
3. README is comprehensive enough for a developer to set up in < 10 minutes
4. Audit log captures create/update/delete actions and can be queried
5. Rate limiting blocks auth abuse (rapid requests)
6. Structured error responses have machine-readable codes
7. Backend tests run: `cd backend && pytest` — all pass
8. Frontend tests run: `cd frontend && npx vitest run` — all pass
9. No TypeScript errors: `cd frontend && npx tsc --noEmit` — zero errors
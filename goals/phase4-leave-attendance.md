# Goal: Implement Phase 4 — Leave & Attendance

## Context

You are building the complete Leave & Attendance feature from scratch for the Arella HR system. The project is a monorepo HR system: FastAPI backend (SQLAlchemy async + Alembic + PostgreSQL) + React frontend (Vite + TypeScript + Tailwind + shadcn/ui + TanStack Router/Query). The auth, employees, and payroll modules already exist with consistent patterns you must follow exactly.

## Project Structure

```
arella-hr/
├── backend/app/
│   ├── models/      # existing: user.py, employee.py, payroll.py
│   ├── schemas/     # existing: user.py, employee.py, payroll.py
│   ├── crud/        # existing: user.py, employee.py, payroll.py
│   ├── services/    # existing: payroll.py
│   ├── api/         # existing: auth.py, employees.py, payroll.py
│   └── ...
├── frontend/src/
│   ├── features/    # existing: employees/, payroll/
│   ├── lib/         # existing: employees.ts, payroll.ts (API clients + types)
│   ├── routes/      # index.ts already has `LeavePage` imported from "./leave"
│   └── ...
└── backend/alembic/versions/  # existing migrations; add new one here
```

Existing patterns to follow (from employees and payroll features):
- Backend: models use `Mapped` + `mapped_column`, Pydantic v2 schemas with `from_attributes = True`, CRUD functions that take `db: AsyncSession`, API routes using `APIRouter`, `get_db` dependency, `@router.get(...)` with response_model.
- Frontend: `features/` components exported as named exports, `lib/` files export types + API functions, TanStack Query for data fetching, shadcn/ui primitives (Table, Card, Badge, Dialog, AlertDialog, Button, Input, Select, Tabs), lucide-react icons, toast notifications, stat cards with 4-card grid, search debouncing, pagination, role-based guards.

---

## Step 1: Backend — Models

Create `backend/app/models/leave.py`:

**Department**
- id (PK, int, auto-increment), name (str, unique, indexed), description (text, nullable), manager_id (FK → Employee, nullable, on_delete=SET NULL), parent_department_id (FK → Department self-referential, nullable), created_at, updated_at (UTC timestamps)

**LeaveType**
- id (PK), name (str, unique), color (str, hex, default "#3b82f6"), days_per_year (float, default 20.0), accrual_rule (str, enum: "none"/"linear"/"lump_sum", default "lump_sum"), is_paid (bool, default True), active (bool, default True), created_at, updated_at

**LeaveBalance**
- id (PK), employee_id (FK → Employee, unique composite with year), year (int), leave_type_id (FK → LeaveType), allocated (float, default 0), used (float, default 0), carried_over (float, default 0)

**LeaveRequest**
- id (PK), employee_id (FK → Employee), type_id (FK → LeaveType), start_date (date), end_date (date), days_requested (float), status (str, enum: "pending"/"approved"/"rejected"/"cancelled", default "pending"), manager_note (text, nullable), created_at, updated_at

Indexes: (employee_id, status) on LeaveRequest, (employee_id, year) on LeaveBalance.

---

## Step 2: Backend — Pydantic Schemas

Create `backend/app/schemas/leave.py`. Each model gets at least:
- An `Out` schema with all relevant fields (`from_attributes = True`)
- Create/Update schemas with only writable fields
- `LeaveRequestOut` should include `employee_name` (computed via relationship on model)
- `LeaveBalanceOut` should include `remaining` computed property
- `LeaveRequestCreate`: type_id, start_date, end_date, reason (optional)
- `LeaveRequestUpdate`: status, manager_note
- `LeaveTypeCreate`: name, color, days_per_year, accrual_rule, is_paid
- `LeaveTypeUpdate`: all updatable fields
- `DepartmentCreate/Update`: name, description, manager_id, parent_department_id

---

## Step 3: Backend — CRUD

Create `backend/app/crud/leave.py`:

- `create_department(db, schema)` — unique name check
- `list_departments(db, search?, parent_id?, page, page_size)` — paginated, filtered
- `update_department(db, id, schema)` — return updated Department
- `delete_department(db, id)` — hard delete
- `create_leave_type(db, schema)` — return LeaveType
- `list_leave_types(db, active_only?, search?, page, page_size)` — paginated
- `update_leave_type(db, id, schema)` — return updated LeaveType
- `delete_leave_type(db, id)` — hard delete, return bool
- `create_leave_request(db, request)` — validate: end_date >= start_date, not in the past, sufficient balance, set status=pending
- `list_leave_requests(db, employee_id?, status?, type_id?, start_date?, end_date?, page, page_size)` — paginated, filterable
- `get_leave_request(db, id)` — single lookup
- `approve_leave_request(db, id, manager_note?)` — set status=approved, decrement LeaveBalance.used
- `reject_leave_request(db, id, manager_note)` — set status=rejected
- `cancel_leave_request(db, id)` — only if status=pending, by the requesting employee
- `get_remaining_days(db, employee_id, type_id, year)` — return (allocated, used, remaining, carried_over)
- `allocate_yearly_balances(db, year)` — for every active employee and active leave type, create or update LeaveBalance

---

## Step 4: Backend — Service Layer

Create `backend/app/services/leave.py`:

- `validate_request_balance(db, employee_id, type_id, days_requested)` — raises ValueError if insufficient
- `get_employee_leave_summary(db, employee_id, year=None)` — returns dict with all leave types: name, allocated, used, remaining, pending_days
- `get_manager_pending_count(db, manager_id)` — returns count of pending requests from direct reports

---

## Step 5: Backend — API Routes

Create `backend/app/api/leave.py`:

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | /api/leave/types | admin only | Create leave type |
| GET | /api/leave/types | all | List leave types (paginated, filterable) |
| PUT | /api/leave/types/{id} | admin only | Update leave type |
| DELETE | /api/leave/types/{id} | admin only | Delete leave type |
| POST | /api/leave/requests | authenticated | Submit leave request |
| GET | /api/leave/requests | authenticated | List (employees=own, managers=team, admins=all) |
| PUT | /api/leave/requests/{id} | manager/admin | Approve/reject request |
| DELETE | /api/leave/requests/{id} | employee/admin | Cancel request |
| GET | /api/leave/requests/pending-count | manager/admin | Count pending requests |
| GET | /api/leave/balances | authenticated | List balances (filterable by employee_id) |
| GET | /api/leave/balance/{employee_id} | authenticated | Single employee balance |
| POST | /api/leave/allocate | admin only | Trigger yearly allocation |
| GET | /api/leave/summary/{employee_id} | authenticated | Leave summary with computed fields |

Register the router in the main API router (check how employees.py and payroll.py are registered and follow the same pattern).

---

## Step 6: Frontend — API Client

Create `frontend/src/lib/leave.ts`:

- Types: `LeaveTypeOut`, `LeaveBalanceOut`, `LeaveRequestOut`, `LeaveRequestOutSummary`
- Interfaces: `LeaveRequestCreate`, `LeaveRequestUpdate`
- Functions: `createLeaveRequest(body)`, `listLeaveRequests(params?)`, `updateLeaveRequest(id, body)`, `cancelLeaveRequest(id)`, `listLeaveTypes(params?)`, `createLeaveType(body)`, `updateLeaveType(id, body)`, `deleteLeaveType(id)`, `getLeaveBalance(employeeId)`, `getLeaveBalances(params?)`, `allocateBalances(year)`, `getPendingCount()`, `getLeaveSummary(employeeId)`
- Each calls the corresponding `api.get/post/put/delete` using the same `api` import path as `payroll.ts` and `employees.ts`

---

## Step 7: Frontend — Components

Create `frontend/src/features/leave/`:

### LeavePage.tsx
Tab wrapper with 4 tabs:
- "My Leave" → MyLeave component
- "Request Leave" → RequestLeave component
- "Approval Queue" → ApprovalQueue component (manager+admin only)
- "Calendar" → LeaveCalendar component

### MyLeave.tsx
- 4 stat cards: Total Requests, Pending, Approved, Remaining Balance
- Balance summary table per leave type (allocated/used/remaining)
- Past requests table: paginated, sorted by date desc, color-coded status badges (pending=yellow, approved=green, rejected=red, cancelled=gray)

### RequestLeave.tsx
- Date range picker (two date inputs)
- Leave type dropdown (populated from API)
- Remaining balance display above form as contextual helper
- Reason textarea (optional)
- Submit button (disabled while loading)
- Warning if selected days exceed remaining balance
- Toast on success, clears form, invalidates query

### ApprovalQueue.tsx
- Only renders for manager+admin
- Table: Employee, Leave Type, Dates, Days, Status, Actions
- Inline approve/reject per row
- Reject opens dialog or inline input for manager_note
- Approve confirms via AlertDialog
- useMutation with qc.invalidateQueries, toast on success

### LeaveCalendar.tsx
- Simple month view showing leave days. If time is tight, render a simple "Upcoming Approved Leaves" list with a TODO comment.

---

## Step 8: Route Registration

Create `frontend/src/routes/leave.tsx`:
```tsx
export { LeavePage } from "@/features/leave/LeavePage";
```

Verify `frontend/src/routes/index.ts` already imports `LeavePage` from `"./leave"` — it does.

---

## Step 9: Alembic Migration

Run `alembic revision --autogenerate -m "add_leave_tables"` in the backend directory, then verify the migration creates all 4 tables with correct types, constraints, foreign keys, and indexes.

---

## Constraints

- Use the exact same folder structure, naming conventions, and code style as existing modules
- Use `Float` for monetary/decimal values (not Decimal) — consistent with payroll
- Use `Mapped` type annotations on all models
- Admin-only: leave type CRUD, allocate endpoint, delete
- Manager+admin: approval queue, approve/reject
- Employee: submit requests, view own data
- All list endpoints support pagination (page, page_size), search (optional), status filter (optional)

---

## Success Criteria

1. `npx tsc --noEmit` on the frontend — zero errors in new files
2. Backend models exist with correct columns and relationships
3. All 13+ API endpoints exist and work
4. Leave request workflow: submit → pending → approve/reject → balance updates
5. Balances auto-allocate yearly
6. Frontend renders all 4 tabs, stat cards, tables, forms, and dialogs
7. Role enforcement works
8. Search, filter, and pagination work on all list tables

---

## Deliverables Checklist

```
backend/app/models/leave.py            ← new
backend/app/schemas/leave.py           ← new
backend/app/crud/leave.py              ← new
backend/app/services/leave.py          ← new
backend/app/api/leave.py               ← new
backend/app/api/routes.py              ← modify (register leave router)
frontend/src/features/leave/LeavePage.tsx          ← new
frontend/src/features/leave/MyLeave.tsx            ← new
frontend/src/features/leave/RequestLeave.tsx       ← new
frontend/src/features/leave/ApprovalQueue.tsx      ← new
frontend/src/features/leave/LeaveCalendar.tsx      ← new (or simple placeholder)
frontend/src/lib/leave.ts                        ← new
frontend/src/routes/leave.tsx                    ← new
backend/alembic/versions/xxx_add_leave_tables.py ← generated
```
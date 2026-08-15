# Goal: Implement Phase 6 — Polish & Production

## Context

The Arella HR system is functionally complete: auth, employee directory, leave/attendance, and payroll are all implemented with backend models/schemas/crud/routes/services and frontend pages. The remaining work is production readiness: documentation, Docker, audit logging, email notifications, and tests.

## Project Structure

```
arella-hr/
├── backend/
│   ├── app/
│   │   ├── main.py            # App factory, middleware, lifespan
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── models/             # user, employee, payroll, department, leave_type, leave_balance, leave_request
│   │   ├── schemas/            # Pydantic v2 schemas
│   │   ├── crud/               # Database operations
│   │   ├── api/v1/             # Route endpoints
│   │   ├── services/           # payroll.py, leave.py
│   │   ├── middleware/         # auth.py
│   │   └── utils/              # helpers.py (exists, likely empty)
│   ├── alembic/                # Migrations (3: initial, payroll, leave)
│   ├── tests/                  # pytest (exists but empty or minimal)
│   ├── Dockerfile              # Exists but may need hardening
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/             # Dashboard, employees, leave, payroll pages
│   │   ├── features/           # employees/, payroll/ have components; leave/ is empty
│   │   ├── lib/                # api.ts, auth.ts, employees.ts, payroll.ts, leave.ts
│   │   ├── components/ui/      # shadcn/ui primitives
│   │   └── ...
│   ├── tests/                  # vitest (exists but likely empty)
│   ├── Dockerfile              # May need multi-stage build
│   └── package.json
├── docker-compose.yml          # App + PostgreSQL
└── README.md                   # Missing
```

## Existing Patterns to Follow

- **Backend models**: `Mapped` type annotations, `mapped_column`, declarative Base, relationships with `selectin` lazy loading
- **Schemas**: Pydantic v2 with `from_attributes = True`, nested `model_config`
- **CRUD**: Functions taking `db: AsyncSession`, using SQLAlchemy `select` statements
- **API routes**: `APIRouter`, `get_db` dependency, `@router.get(...)` with `response_model`
- **Frontend**: TanStack Router for routing, TanStack Query for data fetching, shadcn/ui primitives, lucide-react icons, toast notifications
- **Docker**: Compose file with app + PostgreSQL services

---

## Step 1: README

Create `README.md` at the project root with:

- Project title and one-line description ("Full-featured HR system for SMBs (50–500 employees)")
- Tech stack badges/section
- Quick start: `docker-compose up --build`
- Initial setup: seed script, Alembic migration
- Feature list (auth, employee directory, leave management, payroll)
- Architecture overview (backend frontend structure)
- Environment variables (`.env.example` file)
- Development notes (how to run separately, how to regenerate migrations)
- API docs link (`/docs` — Swagger UI from FastAPI)

Create `.env.example` with all required environment variables from `config.py` (DATABASE_URL, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, etc.) with placeholder values.

---

## Step 2: Docker Hardening

### Backend Dockerfile

Ensure a proper multi-stage or production Dockerfile:

- Base image: `python:3.12-slim` or `python:3.12`
- Install system deps (gcc for psycopg2 if needed, or use `psycopg2-binary` for dev / `psycopg2-binary` is fine)
- Copy requirements.txt, `pip install -r requirements.txt`
- Copy app code
- Expose port 8000
- Use `uvicorn` as entrypoint

### Docker Compose

Ensure `docker-compose.yml` has:

- `backend` service: depends on postgres, env_file, healthcheck, port 8000
- `postgres` service: data volume, healthcheck via `pg_isready`
- `pgadmin` service (optional, for development): port 5050
- Network configuration
- Environment variables via `.env` or inline

### Frontend Dockerfile

Ensure a production build Dockerfile:

- Node base image, install deps, `npm run build`
- Nginx or static file server to serve the built output
- Proxy `/api` to backend (optional in compose setup)

---

## Step 3: Audit Log Model + API

Create the audit log system to track who changed what, when.

### Model: `backend/app/models/audit_log.py`

```python
class AuditLog(Base):
    id: int (PK)
    user_id: int (FK → users.id, nullable — system actions have no user)
    action: str  # e.g., "CREATE", "UPDATE", "DELETE", "LOGIN"
    resource: str  # e.g., "Employee/42", "LeaveRequest/7"
    details: str (JSON/text, nullable)  # What changed
    ip_address: str (nullable)  # Request IP
    created_at: datetime (UTC)
```

### Service: `backend/app/services/audit.py`

- `create_audit_entry(db, user_id, action, resource, details, ip_address)` — simple async function
- Called at the end of relevant CRUD/API operations (or via a FastAPI `after_request` hook)

### API: `backend/app/api/v1/audit_logs.py`

- `GET /api/audit-logs` — list with pagination, filterable by user_id, action, resource, date range
- Access: admin only

### Schema: `backend/app/schemas/audit_log.py`

- `AuditLogOut` with all fields
- `AuditLogFilter` for query params (user_id, action, resource, start_date, end_date, page, page_size)

### Register router in `backend/app/api/v1/__init__.py`

### Alembic migration

Create migration for `audit_logs` table.

---

## Step 4: Email Notifications (Mocked to Console)

### Service: `backend/app/services/email.py`

- `send_email(to: str, subject: str, body: str)` — prints to console with formatting, simulating email send
- No actual SMTP integration — easy to swap in Resend/Postmark later
- Wrap in a try/except so failures never crash the request

### Usage in existing code

Hook email calls into existing workflows:

- Leave request submission → email to manager
- Leave request approved/rejected → email to employee
- Payroll run processed → email to employee (mocked)

Use `settings.email_enabled: bool = True` (always True, but easy to toggle off). The actual send is mocked.

### No separate API route needed — just add the service calls.

---

## Step 5: Rate Limiting on Auth Endpoints

Create `backend/app/middleware/rate_limit.py`:

- Simple in-memory rate limiter (no Redis needed for MVP)
- Class `RateLimiter` with per-IP tracking: max N requests per sliding window
- Decorator or middleware that checks before hitting auth endpoints

Apply rate limiting to:

- `/api/auth/login` — max 10 requests per 5 minutes per IP
- `/api/auth/register` — max 5 requests per 5 minutes per IP
- `/api/auth/refresh` — max 20 requests per 5 minutes per IP

FastAPI `Depends` pattern or middleware layer.

---

## Step 6: Structured Error Handling

Ensure all API routes have consistent error responses:

```python
{
    "detail": {
        "code": "INSUFFICIENT_BALANCE",  # machine-readable code
        "message": "Insufficient leave balance. Remaining: 3.0 day(s), requested: 5.0 day(s)",
    }
}
```

Create `backend/app/utils/errors.py`:

- Custom exception classes: `AppException(BaseException)`, `NotFoundError`, `ValidationError`, `PermissionDeniedError`
- FastAPI exception handler that converts them to structured JSON responses
- Add an `on_exception` hook to FastAPI app

Check existing CRUD functions and ensure they raise these exceptions instead of bare `ValueError` or `HTTPException`.

---

## Step 7: Frontend Polish

### Responsive layout

- Ensure all pages work on mobile (table wrapping, grid breakpoints)
- Navigation sidebar: collapsible on mobile, icon-only mode
- Stat cards: 4-column on desktop, 2-column on tablet, 1-column on mobile (already has `grid-cols-2 md:grid-cols-4`)

### Loading states

- Verify all TanStack Query data fetching shows loading skeletons or spinners
- No empty state gaps during data fetch

### Empty states

- Tables should show "No data found" messages (already done in some places)
- Add consistent empty state components

---

## Step 8: Backend Tests (pytest + httpx)

Create `backend/tests/`:

- `conftest.py`: async fixtures for app, client (httpx.AsyncClient), db, auth helpers
- `test_auth.py`: register, login, refresh, me, token expiry
- `test_employees.py`: CRUD operations, search, filter, pagination
- `test_leave.py`: leave request lifecycle, balance validation, approval flow
- `test_payroll.py`: payroll run creation, processing, entries

Pattern:

```python
@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_headers(client):
    # Login with test user, return headers
    ...

@pytest.mark.asyncio
async def test_list_employees(client, auth_headers):
    resp = await client.get("/api/v1/employees", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
```

---

## Step 9: Frontend Tests (vitest)

Create `frontend/tests/`:

- `setup.ts`: vitest setup with mocks
- `components/LeavePage.test.tsx` or similar: test rendering, query invalidation on submit, toast messages
- Test at least: auth hook (login/logout state), one CRUD page (e.g., EmployeePage or LeavePage)

Pattern:

```tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LeavePage } from "@/routes/leave";

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
};

test("renders leave page", async () => {
  render(<LeavePage />, { wrapper: createWrapper() });
  await waitFor(() => screen.getByText(/My Leave/i));
});
```

---

## Constraints

- Follow existing code style and patterns exactly
- Use `Mapped` type annotations on all models
- Pydantic v2 `from_attributes = True` on all schemas
- Async SQLAlchemy throughout
- Admin-only access for audit log endpoint
- All new code must be documented with docstrings

## Deliverables Checklist

```
README.md                            ← new
.env.example                         ← new
backend/Dockerfile                   ← verify/update
frontend/Dockerfile                  ← verify/update
docker-compose.yml                   ← update (add pgadmin, healthchecks)
backend/app/models/audit_log.py      ← new
backend/app/schemas/audit_log.py     ← new
backend/app/crud/audit_log.py        ← new (minimal: list_paginated)
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

## Success Criteria

1. `docker-compose up --build` starts all services, health checks pass
2. `.env.example` has all required variables
3. README is comprehensive enough for a developer to set up and run in < 10 minutes
4. Audit log captures create/update/delete actions and can be queried
5. Rate limiting blocks auth abuse (verify with rapid requests)
6. Structured error responses have machine-readable codes
7. Backend tests run: `cd backend && pytest` — all pass
8. Frontend tests run: `cd frontend && npx vitest run` — all pass
9. No TypeScript errors: `cd frontend && npx tsc --noEmit` — zero errors
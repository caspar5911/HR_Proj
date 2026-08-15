# Arella HR System

A full-featured HR management system for small and medium businesses (50–500 employees).

## Features

- **Employee Directory** — Manage employee records, org chart, search & filter
- **Leave Management** — Leave requests, approvals, balance tracking, calendar view
- **Payroll** — Payroll runs, payslip generation, deduction rules
- **Security & Ops** — JWT auth with refresh tokens, audit log, rate-limited auth endpoints, structured error responses, seed admin on first run

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy (async), Alembic, PostgreSQL
- **Frontend:** React 19, TypeScript, Vite, react-router v7, TanStack Query, Tailwind CSS, shadcn/ui
- **Deployment:** Docker Compose (dev / production / tooling profiles)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ and Python 3.12+ (only for local, non-Docker dev)

### Running with Docker

```bash
cd arella-hr
docker compose up --build

# Apply database migrations (first start, and after every new migration)
docker compose exec backend alembic upgrade head
```

- Frontend (dev, hot reload): http://localhost:5173
- Backend API docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/health

With pgAdmin:

```bash
docker compose --profile tools up --build   # pgAdmin on http://localhost:5050
```

Production mode (nginx serving the built frontend on :3000, proxying `/api` to the backend):

```bash
docker compose --profile prod up --build
```

> The dev and production frontends can run side by side on different ports.

### Secrets & configuration

All compose variables default to dev-only values and can be overridden via a `.env` file next to `docker-compose.yml` (never commit real values):

| Variable | Default | Purpose |
|---|---|---|
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — **must be set in production** |
| `SEED_ADMIN_PASSWORD` | `admin123` | Seed admin password — **must be set in production** |
| `PGADMIN_PASSWORD` | `admin` | pgAdmin login (tools profile) |
| `BACKEND_PORT` / `FRONTEND_PORT` / `FRONTEND_PROD_PORT` | `8000` / `5173` / `3000` | Host port mappings |

### Running Locally

```bash
# Backend
cd arella-hr/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # edit if needed
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd arella-hr/frontend
npm install
npm run dev
```

## Testing

```bash
# Backend (in-memory SQLite — no database needed)
cd arella-hr/backend
python -m pytest

# Frontend (unit tests)
cd arella-hr/frontend
npx vitest run

# Type-check (strict mode)
cd arella-hr/frontend
npx tsc --noEmit
```

Or run the backend suite inside the container:

```bash
docker compose exec backend python -m pytest
```

## Migrations

```bash
alembic upgrade head                            # apply
alembic revision --autogenerate -m "description" # create after model changes
```

## Security Notes

- **Auth:** JWT access + refresh tokens; login/register/refresh endpoints are rate-limited (in-memory limiter) to throttle credential-stuffing attempts.
- **Audit log:** writes to `/audit-log` track sensitive operations with actor, action, and payload.
- **Structured errors:** every error response carries a machine-readable `code` (e.g. `NOT_FOUND`, `VALIDATION_ERROR`, `RATE_LIMITED`) in addition to `detail`.
- **Containers:** the backend image runs as a non-root user, disables `--reload` in production, and ships a `/health` healthcheck. `.env` and VCS metadata are excluded from images via `.dockerignore`.

## Project Structure

```
arella-hr/
├── backend/              # FastAPI backend
│   ├── app/              # Application code
│   │   ├── main.py       # App entry point (app factory, /health)
│   │   ├── config.py     # Settings (env-driven)
│   │   ├── database.py   # DB connection
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── crud/         # Database operations
│   │   ├── api/          # Route endpoints (v1)
│   │   ├── services/     # Business logic (audit, email, rate limiting)
│   │   ├── middleware/   # Auth, audit logging
│   │   └── utils/        # Helpers (structured errors, security)
│   ├── alembic/          # DB migrations
│   ├── tests/            # Pytest suite
│   ├── Dockerfile        # Non-root runtime image + healthcheck
│   └── .dockerignore
├── frontend/             # React frontend
│   ├── src/
│   │   ├── routes/       # Page routes + guards
│   │   ├── components/   # UI components (shadcn/ui)
│   │   ├── features/     # Domain feature code
│   │   ├── hooks/        # e.g. toast store
│   │   └── lib/          # API client, auth context
│   ├── Dockerfile        # dev / build / prod(nginx) stages
│   ├── nginx.conf        # SPA fallback + /api proxy (prod stage)
│   └── .dockerignore
├── docker-compose.yml    # dev / prod / tools profiles
└── README.md
```

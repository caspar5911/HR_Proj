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

### One-action start

```bash
cd arella-hr
./start.sh          # dev stack (db + backend + hot-reload frontend)
./start.sh prod     # production stack (nginx frontend + backend + db)
```

The script builds the images, starts everything in the background, waits for the
backend to be healthy, then prints the URLs and the first-login credentials.
The backend applies database migrations and creates the admin account
automatically when it starts, so there are no follow-up steps. It stops cleanly
with `docker compose down`.

To run it without the wrapper, the equivalent is:

```bash
docker compose up --build            # dev
docker compose --profile prod up --build   # production
```

Typical URLs (dev): app on http://localhost:5173, API docs on
http://localhost:8000/api/docs, health on http://localhost:8000/health.

**First login:** `admin@example.com` / `admin123`
(configurable via `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` — see below).

> **Port conflict?** If something else on your machine already uses :8000 or
> :3000 (e.g. an LLM server), don't kill it — create a `.env` file next to
> `docker-compose.yml` and override `BACKEND_PORT` / `FRONTEND_PROD_PORT`
> (see the table below). `start.sh` picks up those ports automatically.

### Other one-command setups

pgAdmin for the database:

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
# Backend — migrations + admin seed run automatically on startup
cd arella-hr/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # edit if needed
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

Migrations are applied **automatically when the backend starts** (`alembic upgrade head`,
with retries while the database boots). You only need to create new ones after changing
the models:

```bash
alembic revision --autogenerate -m "description"  # create after model changes
```

Manual application is still available if you ever want to run it explicitly:

```bash
alembic upgrade head
# or: docker compose exec backend alembic upgrade head
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
│   │   ├── main.py       # App entry point (lifespan: auto-migrations + admin seed)
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
├── start.sh              # One-action launcher (build → start → wait → print URLs)
├── .env                  # Local overrides (ports etc.) — created for this machine
└── README.md
```

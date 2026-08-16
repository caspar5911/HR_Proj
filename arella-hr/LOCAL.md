# Arella HR — Fresh PC → Running Locally

From a clean clone to a fully seeded demo app in ~5 minutes. The whole stack
(PostgreSQL + FastAPI backend + React frontend) runs in Docker, so **Docker
Desktop is the only thing you need installed** to run the app.

## 1. Install

| Tool | Needed for |
|---|---|
| **Docker Desktop** (with the Compose plugin — bundled by default) | Running the app |
| Node.js 20+ (optional) | Running the demo scripts in `demo/` |
| ffmpeg (optional) | Re-recording the walkthrough video |

On Windows, Docker Desktop sets up the WSL 2 integration automatically — no
extra steps.

## 2. Get the code

```bash
git clone https://github.com/caspar5911/HR_Proj.git
cd HR_Proj/arella-hr
```

## 3. Start the stack

In **bash** (Git Bash / WSL / macOS / Linux), the one-action launcher:

```bash
./start.sh
```

It builds the images, starts everything in the background, waits for the
backend to be healthy, then prints the URLs and first-login credentials.

In **PowerShell / cmd** (where `./start.sh` doesn't work), the equivalent is:

```bash
docker compose up -d --build
```

then wait until the health check passes (~30–60 s on a first build):

```bash
curl http://localhost:8010/health
```

The backend applies database migrations and creates the admin account
**automatically when it starts** — there is nothing else to do.

> **Note on ports:** the committed `.env` pins the app to `:5173` and the API
> to `:8010` (chosen so it can coexist with other local services). A fresh
> machine gets the same ports — they're safe defaults. To use the standard
> `:8000` / `:3000` instead, just edit (or delete) `arella-hr/.env`.

| What | URL |
|---|---|
| **App (open this)** | http://localhost:5173 |
| API docs (Swagger) | http://localhost:8010/api/docs |
| Health check | http://localhost:8010/health |

## 4. Log in

```
admin@example.com / admin123
```

(configurable via `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` in `.env`)

## 5. Load demo data (recommended)

Demo data is **not** seeded automatically — on startup the backend only
applies migrations and creates the admin account. To fill the app with a
realistic company (employees, leave requests, payroll runs, time entries,
performance reviews, goals, notifications):

```bash
docker compose exec backend python /app/seed_demo.py
```

then log in as any of the demo accounts:

| Role | Login |
|---|---|
| Admin | `admin@example.com` / `admin123` |
| Manager | `manager@example.com` / `manager123` |
| Employee | `employee@example.com` / `employee123` |

Safe to re-run — it wipes and re-seeds the demo data.

## Stopping & resetting

```bash
docker compose down       # stop everything (database is kept)
docker compose down -v    # stop + delete the database (fully fresh start)
```

## Running the test suites (optional)

```bash
docker compose exec backend python -m pytest    # backend (360+ tests)
cd frontend && npm i && npx vitest run          # frontend
```

## Demo scripts (browser automation — optional)

Needs Node 20+, a running stack, and the demo data from step 5:

```bash
cd demo
npm init -y
npm i playwright && npx playwright install chromium
node smoke.mjs               # full-route smoke test — should print "ALL PASSED"
node record-walkthrough.mjs  # re-record arella-hr-walkthrough.mp4 (needs ffmpeg)
```

## Troubleshooting

- **UI doesn't reflect code edits (Windows)** — Docker's bind-mount file
  watching is flaky on Windows. Fix: `docker compose restart frontend`.
- **Backend not healthy / login fails** — `docker compose logs --tail=50 backend`
- **Port already in use** — change `BACKEND_PORT` / `FRONTEND_PORT` in `.env`,
  then `docker compose up -d --build`.
- **Want pgAdmin for the database** — `docker compose --profile tools up --build`
  → http://localhost:5050 (login `admin@example.com` / `admin`).
- **Production-like mode** (nginx serving the built frontend, proxying `/api`)
  — `docker compose --profile prod up --build` → http://localhost:3010.

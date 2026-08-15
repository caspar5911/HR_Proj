#!/usr/bin/env bash
#
# One-action launcher for Arella HR.
#
#   ./start.sh            start dev stack (db + backend + frontend dev server)
#   ./start.sh prod       start the production stack (nginx frontend + backend + db)
#
# It builds the images, starts the services in the background, waits for the
# backend to be healthy, then prints the URLs and the first-login credentials.
# Migrations + the admin seed run automatically when the backend starts.
#
set -euo pipefail

cd "$(dirname "$0")"

# ── resolve host ports (compose defaults, overridable via .env) ──────────────
# .env sits next to docker-compose.yml; read the port overrides if present.
get_env() { grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2 || true; }

BACKEND_PORT="${BACKEND_PORT:-$(get_env BACKEND_PORT)}"
FRONTEND_PORT="${FRONTEND_PORT:-$(get_env FRONTEND_PORT)}"
FRONTEND_PROD_PORT="${FRONTEND_PROD_PORT:-$(get_env FRONTEND_PROD_PORT)}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
FRONTEND_PROD_PORT="${FRONTEND_PROD_PORT:-3000}"

# ── start ────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "prod" ]]; then
  echo "▶ Building & starting the PRODUCTION stack (detached)…"
  docker compose --profile prod up -d --build
  APP_URL="http://localhost:${FRONTEND_PROD_PORT}"
else
  echo "▶ Building & starting the DEV stack (detached)…"
  docker compose up -d --build
  APP_URL="http://localhost:${FRONTEND_PORT}"
fi

# ── wait for the backend to become healthy ───────────────────────────────────
echo "▶ Waiting for the backend to become healthy (migrations + admin seed run here)…"
HEALTH_URL="http://localhost:${BACKEND_PORT}/health"
deadline=$(( $(date +%s) + 180 ))
ok=""
while (( $(date +%s) < deadline )); do
  if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then ok=1; break; fi
  sleep 3
done

if [[ -z "$ok" ]]; then
  echo
  echo "✖ Backend did not become healthy in time. Recent backend logs:"
  echo "──────────────────────────────────────────────────────────────"
  docker compose logs --tail=40 backend 2>&1 || true
  echo "──────────────────────────────────────────────────────────────"
  exit 1
fi

echo "✔ Arella HR is up."
echo
echo "  App (open this):   ${APP_URL}"
echo "  API docs:          http://localhost:${BACKEND_PORT}/api/docs"
echo "  Health check:      ${HEALTH_URL}"
echo
echo "  First login:       admin@example.com  /  admin123"
echo
echo "  Stop everything:   docker compose down   (or: docker compose --profile prod down)"
echo "  Live logs:         docker compose logs -f"

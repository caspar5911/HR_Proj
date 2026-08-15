# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Dedicated unprivileged user — the container never runs as root
RUN groupadd -r app && useradd -r -g app app

WORKDIR /app

# Dependencies first — this layer stays cached while app code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (filtered by .dockerignore — no .venv, __pycache__, .env, .git)
COPY . .

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

# Production server — no --reload. Use the local dev workflow (README) for hot reload.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

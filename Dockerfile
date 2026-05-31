# ── Production image for Cloud Run ────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# System deps kept minimal; add build-essential only if a wheel needs compiling.
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Cloud Run sends traffic to $PORT. gunicorn serves the WSGI app `server`
# exported by app.py. Threads (not just workers) suit Dash's mostly-I/O load.
EXPOSE 8080
CMD exec gunicorn --bind :$PORT --workers 2 --threads 8 --timeout 120 app:server

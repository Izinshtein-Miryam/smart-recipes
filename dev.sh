#!/usr/bin/env bash
# Starts PostgreSQL (docker compose), then backend (uvicorn :8000) and frontend (vite :5173).
# Ctrl+C stops backend and frontend; the database container keeps running (docker compose stop postgres).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$ROOT/.env" ]; then
  echo "Missing .env - copy .env.example to .env first (POSTGRES_PASSWORD is required)." >&2
  exit 1
fi
(cd "$ROOT" && docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --wait postgres)

(cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --reload --port 8000) &
BACK=$!
(cd "$ROOT/frontend" && npm run dev) &
FRONT=$!

trap 'kill $BACK $FRONT 2>/dev/null' EXIT INT TERM
wait

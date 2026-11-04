#!/usr/bin/env bash
# Runs backend (uvicorn :8000) and frontend (vite :5173) together. Ctrl+C stops both.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

(cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --reload --port 8000) &
BACK=$!
(cd "$ROOT/frontend" && npm run dev) &
FRONT=$!

trap 'kill $BACK $FRONT 2>/dev/null' EXIT INT TERM
wait

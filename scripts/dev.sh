#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"

(cd "$project_dir/backend" && uv run uvicorn socraites_api.main:app --app-dir src --reload --reload-dir src --host 127.0.0.1 --port 8765) &
backend_pid=$!
(cd "$project_dir/frontend" && npm run dev) &
frontend_pid=$!

cleanup() {
  kill "$backend_pid" "$frontend_pid" 2>/dev/null || true
  wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

wait "$backend_pid" "$frontend_pid"

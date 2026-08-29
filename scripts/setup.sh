#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$project_dir/data/courses" "$project_dir/data/progress"

(cd "$project_dir/backend" && uv sync --extra dev)
(cd "$project_dir/frontend" && npm install)
(cd "$project_dir/agent-runtime" && npm install)

echo "Socraites is ready. Run ./scripts/dev.sh"

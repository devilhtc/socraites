#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"

(cd "$project_dir/backend" && uv run pytest)
(cd "$project_dir/frontend" && npm test)
(cd "$project_dir/frontend" && npm run build)

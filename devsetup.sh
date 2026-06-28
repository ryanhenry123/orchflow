#!/bin/bash
set -euo pipefail

require() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: $1 not found" >&2
        echo "$2" >&2
        exit 1
    fi
}

require curl "Install: sudo apt-get update && sudo apt-get install -y curl"
require uv   "Install: curl -LsSf https://astral.sh/uv/install.sh | sh"

uv sync --all-extras
uv run pre-commit install
echo "dev environment ready"

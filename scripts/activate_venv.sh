#!/bin/bash
set -euo pipefail

if [ -f ".venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    . .venv/bin/activate
else
    echo "Error: Virtual environment not found at .venv/bin/activate" >&2
    exit 1
fi

# Execute the rest of the command if any
if [ $# -gt 0 ]; then
    exec "$@"
fi

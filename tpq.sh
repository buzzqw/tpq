#!/bin/bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
cd "$HOME"
exec env PYTHONPATH="$SCRIPT_DIR" "$SCRIPT_DIR/.venv/bin/python3" -m tpq "$@"

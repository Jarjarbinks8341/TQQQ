#!/bin/bash
# Wrapper script to run TQQQ trading bot with environment variables

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load environment variables from .env if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# Run the fetch script
/usr/bin/python3 "$SCRIPT_DIR/scripts/fetch_data.py" "$@"

#!/bin/bash
#
# MCPM Startup Clean Wrapper - Minimal wrapper for clean MCP initialization
#
# This wrapper only suppresses the initial startup contamination that causes
# JSON parsing errors, but then allows normal bidirectional MCP communication
# to flow without interference.
#

# Exit on any error
set -e

# Suppress environment variables that cause startup noise
export RICH_NO_COLOR=1
export NO_COLOR=1
export FORCE_COLOR=0
export TERM=dumb
export PYTHONWARNINGS=ignore
export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=0
export PYTHONDONTWRITEBYTECODE=1

# Find the real mcpm binary
MCPM_PATH=""
if [ -f "/usr/local/bin/mcpm" ]; then
    MCPM_PATH="/usr/local/bin/mcpm"
elif [ -f "/opt/homebrew/bin/mcpm" ]; then
    MCPM_PATH="/opt/homebrew/bin/mcpm"
elif command -v mcpm >/dev/null 2>&1; then
    MCMP_PATH=$(command -v mcpm)
else
    # Silent failure - just exit
    exit 1
fi

# Create a temporary file to capture initial stderr output
TEMP_STDERR=$(mktemp)

# Start mcpm with stderr temporarily redirected
"$MCPM_PATH" "$@" 2>"$TEMP_STDERR" &
MCPM_PID=$!

# Give it a moment to initialize and output any startup messages
sleep 0.5

# Now redirect stderr back to normal and let it run normally
exec 2>&1

# Wait for the process to complete
wait $MCPM_PID
EXIT_CODE=$?

# Clean up
rm -f "$TEMP_STDERR" 2>/dev/null || true

exit $EXIT_CODE

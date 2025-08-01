#!/bin/bash
#
# MCPM Clean Wrapper - Bulletproof stdio-clean launcher for Claude Desktop
#
# This wrapper ensures absolutely no Rich formatting, error messages, or other
# output contamination reaches Claude Desktop or other MCP clients that require
# clean JSON-RPC communication.
#

# Exit on any error
set -e

# Suppress all possible output sources
export RICH_NO_COLOR=1
export NO_COLOR=1
export FORCE_COLOR=0
export TERM=dumb
export PYTHONWARNINGS=ignore
export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=0
export PYTHONDONTWRITEBYTECODE=1
export LOGLEVEL=CRITICAL
export LOG_LEVEL=CRITICAL
export LOGGING_LEVEL=CRITICAL
export MCP_LOG_LEVEL=CRITICAL
export UVICORN_LOG_LEVEL=critical
export FASTAPI_LOG_LEVEL=critical
export _JAVA_OPTIONS=-Xlog:disable
export NODE_NO_WARNINGS=1
export RUST_LOG=error
export RUST_BACKTRACE=0

# Find the real mcpm binary
MCPM_PATH=""
if [ -f "/usr/local/bin/mcpm" ]; then
    MCPM_PATH="/usr/local/bin/mcpm"
elif [ -f "/opt/homebrew/bin/mcpm" ]; then
    MCPM_PATH="/opt/homebrew/bin/mcpm"
elif command -v mcpm >/dev/null 2>&1; then
    MCPM_PATH=$(command -v mcpm)
else
    # Silent failure - just exit
    exit 1
fi

# Execute mcpm with all stderr redirected to /dev/null
# This ensures no Rich formatting, warnings, or error messages can leak through
exec "$MCPM_PATH" "$@" 2>/dev/null

#!/usr/bin/env python3
"""
STDOUT Filter for MCP Servers - Only allows valid JSON-RPC messages through.

This filter sits between MCPM and Claude Desktop, ensuring that only valid
JSON-RPC messages are passed through to stdout while blocking all Rich
formatting, error messages, and other contamination.
"""

import json
import subprocess
import sys
import os
import select
import re


def is_valid_jsonrpc(line):
    """Check if a line contains valid JSON-RPC content."""
    line = line.strip()
    if not line:
        return False

    try:
        data = json.loads(line)
        # Must have jsonrpc field
        if "jsonrpc" not in data:
            return False
        # Must be version 2.0
        if data["jsonrpc"] != "2.0":
            return False
        # Must have either method (request/notification) or result/error (response)
        if "method" not in data and "result" not in data and "error" not in data:
            return False
        return True
    except (json.JSONDecodeError, TypeError, AttributeError):
        return False


def filter_stdout_line(line):
    """Filter a single line of output, returning it only if it's valid JSON-RPC."""
    # Remove any ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean_line = ansi_escape.sub('', line)

    # Remove Rich table characters and other contamination
    rich_chars = ['│', '┃', '┏', '┓', '┗', '┛', '┣', '┫', '┳', '┻', '╋', '╰', '╭', '╮', '╯']
    for char in rich_chars:
        clean_line = clean_line.replace(char, '')

    # Check if it's valid JSON-RPC
    if is_valid_jsonrpc(clean_line):
        return clean_line + '\n'

    return None


def main():
    """Main filter function."""
    if len(sys.argv) < 2:
        sys.exit(1)

    # Set up environment for clean output
    env = os.environ.copy()
    env.update({
        "RICH_NO_COLOR": "1",
        "NO_COLOR": "1",
        "FORCE_COLOR": "0",
        "TERM": "dumb",
        "PYTHONWARNINGS": "ignore",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",  # Important for line buffering
        "PYTHONDONTWRITEBYTECODE": "1",
        "LOGLEVEL": "CRITICAL",
        "LOG_LEVEL": "CRITICAL"
    })

    # Start the subprocess
    try:
        process = subprocess.Popen(
            sys.argv[1:],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # Completely suppress stderr
            text=True,
            bufsize=0,  # Unbuffered
            env=env
        )
    except Exception:
        sys.exit(1)

    # Forward stdin to process
    def forward_stdin():
        try:
            while process.poll() is None:
                try:
                    # Use select to check if stdin has data available
                    ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if ready:
                        line = sys.stdin.readline()
                        if line:
                            process.stdin.write(line)
                            process.stdin.flush()
                        else:
                            # EOF on stdin, but don't close process stdin yet
                            break
                except:
                    break
        except:
            pass
        # Don't close stdin immediately - let the process decide when to exit

    # Start stdin forwarding in background
    import threading
    stdin_thread = threading.Thread(target=forward_stdin, daemon=True)
    stdin_thread.start()

    # Filter stdout
    try:
        while process.poll() is None:
            # Read available output
            ready, _, _ = select.select([process.stdout], [], [], 0.1)
            if ready:
                line = process.stdout.readline()
                if not line:  # EOF
                    break

                # Filter and output only valid JSON-RPC
                filtered = filter_stdout_line(line)
                if filtered:
                    sys.stdout.write(filtered)
                    sys.stdout.flush()

        # Process any remaining output after process exits
        while True:
            line = process.stdout.readline()
            if not line:
                break
            filtered = filter_stdout_line(line)
            if filtered:
                sys.stdout.write(filtered)
                sys.stdout.flush()

    except (KeyboardInterrupt, BrokenPipeError):
        pass

    # Clean up
    try:
        process.terminate()
        process.wait(timeout=5)
    except:
        try:
            process.kill()
        except:
            pass

    sys.exit(process.returncode if process.returncode is not None else 1)


if __name__ == "__main__":
    main()

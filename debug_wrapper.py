#!/usr/bin/env python3
"""
Debug wrapper that logs exactly what's being sent to stdout to help
diagnose the Rich table character contamination issue.
"""

import subprocess
import sys
import os
import time
from datetime import datetime

def log_message(msg):
    """Log a message with timestamp to stderr."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    sys.stderr.write(f"[{timestamp}] DEBUG: {msg}\n")
    sys.stderr.flush()

def main():
    if len(sys.argv) < 2:
        log_message("No command provided")
        sys.exit(1)

    # Set up clean environment
    env = os.environ.copy()
    env.update({
        "RICH_NO_COLOR": "1",
        "NO_COLOR": "1",
        "FORCE_COLOR": "0",
        "TERM": "dumb",
        "PYTHONWARNINGS": "ignore",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1"
    })

    log_message(f"Starting command: {' '.join(sys.argv[1:])}")

    # Start the subprocess
    try:
        process = subprocess.Popen(
            sys.argv[1:],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,
            env=env
        )
    except Exception as e:
        log_message(f"Failed to start process: {e}")
        sys.exit(1)

    log_message("Process started successfully")

    # Forward stdin to process
    import threading

    def forward_stdin():
        try:
            while True:
                try:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    log_message(f"STDIN -> {repr(line.strip())}")
                    if process.poll() is None:
                        process.stdin.write(line)
                        process.stdin.flush()
                    else:
                        break
                except:
                    break
        except:
            pass

    stdin_thread = threading.Thread(target=forward_stdin, daemon=True)
    stdin_thread.start()

    # Monitor stdout and stderr
    import select

    stdout_buffer = ""
    stderr_buffer = ""

    try:
        while process.poll() is None:
            ready, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)

            if process.stdout in ready:
                char = process.stdout.read(1)
                if char:
                    stdout_buffer += char

                    # Log each character with its hex representation
                    if char == '\n':
                        log_message(f"STDOUT LINE: {repr(stdout_buffer)}")
                        # Check for Rich table characters
                        if any(c in stdout_buffer for c in ['│', '┃', '┏', '┓', '┗', '┛', '╰', '╭', '╮', '╯']):
                            log_message("*** RICH TABLE CHARS DETECTED IN STDOUT ***")

                        # Forward to actual stdout
                        sys.stdout.write(stdout_buffer)
                        sys.stdout.flush()
                        stdout_buffer = ""
                    elif len(stdout_buffer) > 1000:  # Prevent buffer overflow
                        log_message(f"STDOUT PARTIAL: {repr(stdout_buffer[:100])}...")
                        sys.stdout.write(stdout_buffer)
                        sys.stdout.flush()
                        stdout_buffer = ""

            if process.stderr in ready:
                char = process.stderr.read(1)
                if char:
                    stderr_buffer += char

                    if char == '\n':
                        log_message(f"STDERR LINE: {repr(stderr_buffer)}")
                        # Check for Rich table characters in stderr too
                        if any(c in stderr_buffer for c in ['│', '┃', '┏', '┓', '┗', '┛', '╰', '╭', '╮', '╯']):
                            log_message("*** RICH TABLE CHARS DETECTED IN STDERR ***")
                        stderr_buffer = ""
                    elif len(stderr_buffer) > 1000:
                        log_message(f"STDERR PARTIAL: {repr(stderr_buffer[:100])}...")
                        stderr_buffer = ""

    except KeyboardInterrupt:
        log_message("Interrupted")

    # Flush any remaining buffers
    if stdout_buffer:
        log_message(f"STDOUT FINAL: {repr(stdout_buffer)}")
        sys.stdout.write(stdout_buffer)
        sys.stdout.flush()

    if stderr_buffer:
        log_message(f"STDERR FINAL: {repr(stderr_buffer)}")

    # Wait for process to complete
    try:
        exit_code = process.wait(timeout=5)
        log_message(f"Process exited with code: {exit_code}")
        sys.exit(exit_code)
    except subprocess.TimeoutExpired:
        log_message("Process timeout, killing")
        process.kill()
        sys.exit(1)

if __name__ == "__main__":
    main()

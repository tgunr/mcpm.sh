#!/usr/bin/env python3
"""
Debug script to simulate Claude Desktop's exact environment and capture all output.
This helps diagnose stdio-clean issues by reproducing the exact conditions Claude Desktop uses.
"""

import subprocess
import sys
import json
import time
import os
from pathlib import Path

# Claude Desktop's typical PATH (based on logs)
CLAUDE_DESKTOP_PATH = [
    "/Users/davec/.nvm/versions/node/v20.19.1/bin",
    "/Users/davec/.nvm/versions/node/v23.9.0/bin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/usr/bin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin"
]

def debug_mcpm_stdio_clean():
    """Debug MCPM stdio-clean mode by simulating Claude Desktop's environment."""

    print("=== MCPM stdio-clean Debug Tool ===")
    print()

    # Test 1: Check if mcpm is found in Claude Desktop's PATH
    print("1. Testing PATH resolution...")
    env = os.environ.copy()
    env['PATH'] = ':'.join(CLAUDE_DESKTOP_PATH)

    try:
        result = subprocess.run(['which', 'mcpm'], env=env, capture_output=True, text=True)
        if result.returncode == 0:
            mcpm_path = result.stdout.strip()
            print(f"   ✅ mcpm found at: {mcpm_path}")
        else:
            print(f"   ❌ mcpm not found in PATH")
            print(f"   PATH: {env['PATH']}")
            return
    except Exception as e:
        print(f"   ❌ Error finding mcpm: {e}")
        return

    # Test 2: Test version command
    print("\n2. Testing version command...")
    try:
        result = subprocess.run([mcpm_path, '--version'], env=env, capture_output=True, text=True)
        print(f"   Return code: {result.returncode}")
        if result.stdout:
            print(f"   STDOUT: {repr(result.stdout[:200])}")
        if result.stderr:
            print(f"   STDERR: {repr(result.stderr[:200])}")
    except Exception as e:
        print(f"   ❌ Error running version: {e}")

    # Test 3: Test MCP initialization sequence
    print("\n3. Testing MCP initialization...")

    init_message = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "claude-ai", "version": "0.1.0"}
        },
        "id": 0
    }

    try:
        # Start the process
        proc = subprocess.Popen(
            [mcpm_path, 'profile', 'run', '--stdio-clean', 'test-simple'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

        # Send initialization message
        init_json = json.dumps(init_message) + '\n'
        print(f"   Sending: {init_json.strip()}")

        # Write and close stdin
        proc.stdin.write(init_json)
        proc.stdin.close()

        # Wait for response with timeout
        try:
            stdout, stderr = proc.communicate(timeout=10)
            print(f"   Return code: {proc.returncode}")

            # Analyze stdout
            if stdout:
                print(f"   STDOUT length: {len(stdout)} chars")
                print(f"   STDOUT (raw): {repr(stdout)}")

                # Try to parse as JSON lines
                lines = stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    if line.strip():
                        try:
                            parsed = json.loads(line)
                            print(f"     Line {i+1}: Valid JSON - {parsed.get('jsonrpc', 'unknown')}")
                        except json.JSONDecodeError as e:
                            print(f"     Line {i+1}: Invalid JSON - {repr(line[:100])}")
                            print(f"                Error: {e}")

            # Analyze stderr
            if stderr:
                print(f"   STDERR length: {len(stderr)} chars")
                print(f"   STDERR: {repr(stderr)}")

        except subprocess.TimeoutExpired:
            print("   ❌ Process timed out")
            proc.kill()
            stdout, stderr = proc.communicate()
            if stdout:
                print(f"   Partial STDOUT: {repr(stdout[:500])}")
            if stderr:
                print(f"   Partial STDERR: {repr(stderr[:500])}")

    except Exception as e:
        print(f"   ❌ Error in MCP test: {e}")

    # Test 4: Test with notifications/initialized and tools/list
    print("\n4. Testing full MCP sequence...")

    messages = [
        init_message,
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        },
        {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1
        }
    ]

    try:
        proc = subprocess.Popen(
            [mcpm_path, 'profile', 'run', '--stdio-clean', 'test-simple'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

        # Send all messages
        input_data = '\n'.join(json.dumps(msg) for msg in messages) + '\n'
        print(f"   Sending {len(messages)} messages...")

        try:
            stdout, stderr = proc.communicate(input=input_data, timeout=15)
            print(f"   Return code: {proc.returncode}")

            if stdout:
                print(f"   STDOUT: {repr(stdout)}")
                # Check for Rich table characters
                if '│' in stdout or '╰' in stdout or '┃' in stdout:
                    print("   ⚠️  Rich table characters detected!")

            if stderr:
                print(f"   STDERR: {repr(stderr)}")

        except subprocess.TimeoutExpired:
            print("   ❌ Full sequence timed out")
            proc.kill()

    except Exception as e:
        print(f"   ❌ Error in full sequence test: {e}")

    # Test 5: Check environment variables
    print("\n5. Environment check...")
    env_vars = [
        'RICH_NO_COLOR', 'NO_COLOR', 'FORCE_COLOR', 'TERM',
        'PYTHONWARNINGS', 'LOGLEVEL', 'LOG_LEVEL'
    ]

    for var in env_vars:
        value = env.get(var, 'Not set')
        print(f"   {var}: {value}")

    print("\n=== Debug Complete ===")

if __name__ == "__main__":
    debug_mcpm_stdio_clean()

#!/usr/bin/env python3
"""
Stdio wrapper for MCP servers in stdio-clean mode.

This wrapper redirects stdout/stderr from child MCP servers to prevent them from
corrupting the JSON-RPC stream when used through FastMCP proxy in stdio-clean mode.
"""

import os
import sys
import subprocess
import json
from typing import List, Dict, Optional


def create_stdio_wrapper_command(
    original_command: str,
    args: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
    stdio_clean: bool = False
) -> List[str]:
    """
    Create a command that wraps the original MCP server command with stdio redirection.

    Args:
        original_command: The original server command (e.g., "uvx", "python")
        args: Arguments for the original command
        env: Environment variables for the original command
        stdio_clean: Whether to enable stdio-clean mode (redirect stderr to devnull)

    Returns:
        List of command parts for the wrapper
    """
    wrapper_script = __file__
    wrapper_args = [
        sys.executable, wrapper_script,
        "--command", original_command
    ]

    if args:
        wrapper_args.extend(["--args"] + args)

    if env:
        env_json = json.dumps(env)
        wrapper_args.extend(["--env", env_json])

    if stdio_clean:
        wrapper_args.append("--stdio-clean")

    return wrapper_args


def main():
    """Main wrapper function that executes the MCP server with proper stdio handling."""
    import argparse

    parser = argparse.ArgumentParser(description="Stdio wrapper for MCP servers")
    parser.add_argument("--command", required=True, help="Command to execute")
    parser.add_argument("--args", nargs="*", help="Arguments for the command")
    parser.add_argument("--env", help="Environment variables as JSON string")
    parser.add_argument("--stdio-clean", action="store_true",
                       help="Enable stdio-clean mode (redirect stderr)")

    args = parser.parse_args()

    # Build the command
    cmd = [args.command]
    if args.args:
        cmd.extend(args.args)

    # Prepare environment
    env = os.environ.copy()
    if args.env:
        try:
            env_vars = json.loads(args.env)
            env.update(env_vars)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in --env: {args.env}", file=sys.stderr)
            sys.exit(1)

    # Set up stdio redirection for stdio-clean mode
    stdin = sys.stdin
    stdout = sys.stdout
    stderr = sys.stderr

    if args.stdio_clean:
        # In stdio-clean mode, redirect stderr to devnull to prevent
        # error messages from corrupting the JSON-RPC stream
        stderr = open(os.devnull, 'w')

        # Also set additional environment variables to suppress output
        env.update({
            "RICH_NO_COLOR": "1",
            "NO_COLOR": "1",
            "FORCE_COLOR": "0",
            "TERM": "dumb",
            "PYTHONWARNINGS": "ignore",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "0"
        })

    try:
        # Execute the command with proper stdio handling
        process = subprocess.Popen(
            cmd,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env=env
        )

        # Wait for completion and return the same exit code
        exit_code = process.wait()
        sys.exit(exit_code)

    except FileNotFoundError:
        if not args.stdio_clean:
            print(f"Error: Command not found: {args.command}", file=sys.stderr)
        sys.exit(127)
    except Exception as e:
        if not args.stdio_clean:
            print(f"Error executing command: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Clean up redirected stderr if we opened it
        if args.stdio_clean and stderr != sys.stderr:
            stderr.close()


if __name__ == "__main__":
    main()

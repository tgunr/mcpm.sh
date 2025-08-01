#!/usr/bin/env python3
"""
MCPM Stdio Clean Launcher - Minimal MCP server launcher with no Rich output.

This is a completely separate launcher designed specifically for Claude Desktop
and other MCP clients that require clean JSON-RPC communication without any
Rich formatting, error messages, or other output contamination.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def suppress_all_output():
    """Aggressively suppress all non-JSON output."""
    # Redirect stderr to devnull
    sys.stderr = open(os.devnull, 'w')

    # Set environment variables to suppress all possible output
    os.environ.update({
        "RICH_NO_COLOR": "1",
        "NO_COLOR": "1",
        "FORCE_COLOR": "0",
        "TERM": "dumb",
        "PYTHONWARNINGS": "ignore",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LOGLEVEL": "CRITICAL",
        "LOG_LEVEL": "CRITICAL",
        "LOGGING_LEVEL": "CRITICAL",
        "MCP_LOG_LEVEL": "CRITICAL",
        "UVICORN_LOG_LEVEL": "critical",
        "FASTAPI_LOG_LEVEL": "critical",
        "_JAVA_OPTIONS": "-Xlog:disable",
        "NODE_NO_WARNINGS": "1",
        "RUST_LOG": "error",
        "RUST_BACKTRACE": "0"
    })


def get_profile_servers(profile_name: str) -> List[Dict]:
    """Get servers for a profile without using Rich output."""
    try:
        # Find MCPM config directory
        home = Path.home()
        config_dirs = [
            home / ".mcpm",
            home / ".config" / "mcpm"
        ]

        profile_file = None
        for config_dir in config_dirs:
            potential_file = config_dir / "profiles" / f"{profile_name}.json"
            if potential_file.exists():
                profile_file = potential_file
                break

        if not profile_file:
            return []

        with open(profile_file) as f:
            profile_data = json.load(f)

        return profile_data.get("servers", [])

    except Exception:
        return []


def get_server_command(server_name: str) -> Optional[Dict]:
    """Get command for a specific server without Rich output."""
    try:
        # Find MCPM config directory
        home = Path.home()
        config_dirs = [
            home / ".mcpm",
            home / ".config" / "mcpm"
        ]

        servers_file = None
        for config_dir in config_dirs:
            potential_file = config_dir / "servers.json"
            if potential_file.exists():
                servers_file = potential_file
                break

        if not servers_file:
            return None

        with open(servers_file) as f:
            servers_data = json.load(f)

        server_info = servers_data.get("servers", {}).get(server_name)
        if not server_info:
            return None

        # Get the first installation method
        installations = server_info.get("installations", {})
        if not installations:
            return None

        install_method = next(iter(installations.values()))
        command_parts = install_method.get("command", "").split()

        return {
            "command": command_parts[0] if command_parts else "",
            "args": command_parts[1:] if len(command_parts) > 1 else [],
            "env": install_method.get("env", {})
        }

    except Exception:
        return None


def run_single_server(server_name: str):
    """Run a single MCP server with clean stdio."""
    server_info = get_server_command(server_name)
    if not server_info:
        sys.exit(1)

    # Build command
    cmd = [server_info["command"]] + server_info["args"]

    # Set up environment
    env = os.environ.copy()
    env.update(server_info.get("env", {}))

    # Execute with stderr redirected
    try:
        process = subprocess.Popen(
            cmd,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=open(os.devnull, 'w'),
            env=env
        )
        sys.exit(process.wait())
    except Exception:
        sys.exit(1)


def run_profile_servers(profile_name: str):
    """Run multiple servers from a profile using minimal FastMCP setup."""
    servers = get_profile_servers(profile_name)
    if not servers:
        sys.exit(1)

    if len(servers) == 1:
        # Single server - run directly
        run_single_server(servers[0]["name"])
        return

    # Multiple servers - use FastMCP with minimal config
    try:
        from fastmcp import FastMCP

        # Build server configs
        server_configs = {}
        for server in servers:
            server_info = get_server_command(server["name"])
            if not server_info:
                continue

            # Wrap command with shell to redirect stderr
            shell_cmd = server_info["command"]
            if server_info["args"]:
                shell_cmd += " " + " ".join(f'"{arg}"' for arg in server_info["args"])
            shell_cmd += " 2>/dev/null"

            server_configs[server["name"]] = {
                "command": "sh",
                "args": ["-c", shell_cmd],
                "env": server_info.get("env", {})
            }

        if not server_configs:
            sys.exit(1)

        # Create FastMCP instance
        config = {"mcpServers": server_configs}
        proxy = FastMCP(config)

        # Run with no banner and clean stdio
        import asyncio
        asyncio.run(proxy.run_stdio_async(show_banner=False))

    except Exception:
        sys.exit(1)


def main():
    """Main entry point."""
    # Suppress all output immediately
    suppress_all_output()

    if len(sys.argv) < 2:
        sys.exit(1)

    command = sys.argv[1]

    if command == "profile" and len(sys.argv) >= 4 and sys.argv[2] == "run":
        profile_name = sys.argv[3]
        run_profile_servers(profile_name)
    elif command == "run" and len(sys.argv) >= 3:
        server_name = sys.argv[2]
        run_single_server(server_name)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

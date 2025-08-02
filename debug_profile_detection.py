#!/usr/bin/env python3
"""
Debug script to examine profile detection logic.

This script helps diagnose why profile detection isn't working correctly
when clients are configured to use profiles.
"""

import sys
import os
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcpm.clients.client_registry import ClientRegistry
from mcpm.clients.managers.claude_desktop import ClaudeDesktopManager

console = Console()

def examine_claude_desktop_config():
    """Examine the actual Claude Desktop configuration"""
    console.print("[bold blue]🔍 Examining Claude Desktop Configuration[/]")
    console.print("=" * 60)

    manager = ClaudeDesktopManager()
    config_path = manager.config_path

    console.print(f"Config path: [cyan]{config_path}[/]")

    if not os.path.exists(config_path):
        console.print("[red]❌ Config file does not exist[/]")
        return

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        console.print("[green]✓ Successfully loaded config file[/]")
        console.print(f"Top-level keys: {list(config.keys())}")

        if 'mcpServers' in config:
            servers = config['mcpServers']
            console.print(f"\n[bold]Found {len(servers)} MCP servers:[/]")

            table = Table(title="MCP Servers in Claude Desktop Config")
            table.add_column("Server Name", style="cyan")
            table.add_column("Command", style="green")
            table.add_column("Args", style="yellow")

            for server_name, server_config in servers.items():
                command = server_config.get('command', 'N/A')
                args = server_config.get('args', [])
                args_str = ' '.join(args) if args else 'None'
                table.add_row(server_name, command, args_str)

            console.print(table)

            # Test profile detection on each server
            console.print(f"\n[bold]Testing Profile Detection:[/]")

            for server_name, server_config in servers.items():
                console.print(f"\n[cyan]Server: {server_name}[/]")
                console.print(f"  Config: {server_config}")

                # Convert to ServerConfig object for testing
                from mcpm.core.schema import STDIOServerConfig

                try:
                    if server_config.get('command') and server_config.get('args'):
                        server_obj = STDIOServerConfig(
                            name=server_name,
                            command=server_config['command'],
                            args=server_config['args']
                        )

                        # Test profile extraction
                        extracted_profile = manager._extract_profile_name(server_obj)
                        console.print(f"  Extracted profile: [yellow]{extracted_profile}[/]")

                        # Test if it's a profile server
                        if extracted_profile:
                            is_profile_server = manager._is_profile_server(server_obj, extracted_profile)
                            console.print(f"  Is profile server: [green]{is_profile_server}[/]")

                        # Show detailed arg analysis
                        args = server_config['args']
                        console.print(f"  Args analysis:")
                        for i, arg in enumerate(args):
                            console.print(f"    [{i}]: '{arg}'")

                        # Check for specific patterns
                        if 'profile' in args and 'run' in args:
                            profile_idx = args.index('profile')
                            run_idx = args.index('run')
                            console.print(f"  Found 'profile' at index {profile_idx}, 'run' at index {run_idx}")

                            if run_idx > profile_idx:
                                console.print(f"  Looking for profile name after 'run'...")
                                for j in range(run_idx + 1, len(args)):
                                    arg = args[j]
                                    console.print(f"    Checking arg[{j}]: '{arg}' (starts with --: {arg.startswith('--')})")
                                    if not arg.startswith('--'):
                                        console.print(f"    [green]Found profile name: '{arg}'[/]")
                                        break
                    else:
                        console.print(f"  [yellow]Server missing command or args[/]")

                except Exception as e:
                    console.print(f"  [red]Error creating ServerConfig: {e}[/]")
        else:
            console.print("[yellow]No 'mcpServers' section found in config[/]")

    except Exception as e:
        console.print(f"[red]❌ Error loading config file: {e}[/]")

def test_profile_detection_logic():
    """Test the profile detection logic with known patterns"""
    console.print(f"\n[bold blue]🧪 Testing Profile Detection Logic[/]")
    console.print("=" * 60)

    from mcpm.core.schema import STDIOServerConfig

    manager = ClaudeDesktopManager()

    # Test cases that should work
    test_cases = [
        {
            "name": "mcpm_profile_minimal",
            "command": "mcpm",
            "args": ["profile", "run", "--stdio-clean", "minimal"],
            "expected": "minimal"
        },
        {
            "name": "mcmp_profile_web-dev",
            "command": "mcpm",
            "args": ["profile", "run", "web-dev"],
            "expected": "web-dev"
        },
        {
            "name": "regular_server",
            "command": "python",
            "args": ["-m", "some_server"],
            "expected": None
        }
    ]

    table = Table(title="Profile Detection Test Cases")
    table.add_column("Server Name", style="cyan")
    table.add_column("Command", style="green")
    table.add_column("Args", style="yellow")
    table.add_column("Expected", style="blue")
    table.add_column("Actual", style="magenta")
    table.add_column("Result", style="bold")

    for test_case in test_cases:
        server_obj = STDIOServerConfig(
            name=test_case["name"],
            command=test_case["command"],
            args=test_case["args"]
        )

        extracted = manager._extract_profile_name(server_obj)
        expected = test_case["expected"]

        result = "✅ PASS" if extracted == expected else "❌ FAIL"

        table.add_row(
            test_case["name"],
            test_case["command"],
            " ".join(test_case["args"]),
            str(expected),
            str(extracted),
            result
        )

    console.print(table)

def examine_all_clients():
    """Examine profile detection across all clients"""
    console.print(f"\n[bold blue]👥 Examining All Clients[/]")
    console.print("=" * 60)

    for client_name in ClientRegistry.get_supported_clients():
        try:
            manager = ClientRegistry.get_client_manager(client_name)
            if not manager or not manager.is_client_installed():
                continue

            console.print(f"\n[cyan]Client: {client_name}[/]")

            profiles = manager.get_associated_profiles()
            console.print(f"  Detected profiles: {profiles}")

            # Get raw servers
            servers = manager.get_servers()
            console.print(f"  Raw servers count: {len(servers)}")

            for server_name, server_config in list(servers.items())[:3]:  # Show first 3
                console.print(f"    {server_name}: {type(server_config).__name__}")

        except Exception as e:
            console.print(f"  [red]Error examining {client_name}: {e}[/]")

def main():
    """Main debug function"""
    console.print("[bold cyan]🔍 Profile Detection Debug Tool[/]")
    console.print("This tool helps diagnose profile detection issues")

    examine_claude_desktop_config()
    test_profile_detection_logic()
    examine_all_clients()

    console.print(f"\n[bold green]🎯 Debug Complete![/]")
    console.print("\n[bold]Common Issues to Check:[/]")
    console.print("• Profile name extraction from command arguments")
    console.print("• Server config object creation and type handling")
    console.print("• Argument parsing logic (especially with --stdio-clean)")
    console.print("• Client manager inheritance and method overrides")

if __name__ == "__main__":
    main()

"""
Client command for MCPM
"""

import json
import os
import subprocess

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.table import Table

from mcpm.clients.client_config import ClientConfigManager
from mcpm.clients.client_registry import ClientRegistry
from mcpm.global_config import GlobalConfigManager
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.display import print_error
from mcpm.utils.rich_click_config import click

console = Console(stderr=True)
client_config_manager = ClientConfigManager()
global_config_manager = GlobalConfigManager()


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def client():
    """Manage MCP client configurations (Claude Desktop, Cursor, Windsurf, etc.).

    MCP clients are applications that can connect to MCP servers. This command helps you
    view installed clients, edit their configurations to enable/disable MCPM servers,
    and import existing server configurations into MCPM's global configuration.

    Supported clients: Claude Desktop, Cursor, Windsurf, Continue, Zed, and more.

    Examples:

    \b
        mcpm client ls                    # List all supported MCP clients and their status
        mcpm client info cursor           # Show detailed info for a specific client
        mcpm client edit cursor           # Interactive server selection for Cursor
        mcpm client edit claude-desktop   # Interactive server selection for Claude Desktop
        mcpm client edit cursor -e        # Open Cursor config in external editor
        mcpm client import cursor         # Import server configurations from Cursor
        mcpm client fix-profiles          # Fix existing profile configurations for better compatibility

    For Claude Desktop integration issues, see: CLAUDE_DESKTOP_INTEGRATION.md
    """
    pass


@client.command(name="ls", context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--verbose", "-v", is_flag=True, help="Show detailed server information")
def list_clients(verbose):
    """List all supported MCP clients and their enabled MCPM servers."""
    # Get the list of supported clients
    supported_clients = ClientRegistry.get_supported_clients()
    installed_clients = ClientRegistry.detect_installed_clients()

    # Count installed clients
    installed_count = sum(1 for c in supported_clients if installed_clients.get(c, False))

    console.print(f"\n[green]Found {installed_count} MCP client(s)[/]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("MCPM Profiles", overflow="fold")
    table.add_column("MCPM Servers", overflow="fold")
    table.add_column("Other Servers", overflow="fold")
    if verbose:
        table.add_column("Server Details", overflow="fold")

    # Separate installed and uninstalled clients
    installed_client_names = [c for c in supported_clients if installed_clients.get(c, False)]
    uninstalled_client_names = [c for c in supported_clients if not installed_clients.get(c, False)]

    # Process only installed clients in the table
    for client_name in sorted(installed_client_names):
        # Get client info
        client_info = ClientRegistry.get_client_info(client_name)
        display_name = client_info.get("name", client_name)

        # Build client name with code
        client_display = f"{display_name} [dim]({client_name})[/]"

        # Get the client manager to check MCPM servers
        client_manager = ClientRegistry.get_client_manager(client_name)
        if not client_manager:
            row = [
                client_display,
                "[dim]Cannot read config[/]",
                "[dim]Cannot read config[/]",
                "[dim]Cannot read config[/]",
            ]
            if verbose:
                row.append("[dim]-[/]")
            table.add_row(*row)
            continue

        # Find MCPM profiles, MCPM servers, and other servers in the client config
        mcpm_profiles = []
        mcpm_servers = []
        other_servers = []
        mcpm_server_details = []

        try:
            client_servers = client_manager.get_servers()
            if not client_servers:
                # No servers found - this could be empty config or parsing issue
                if verbose:
                    console.print(f"[dim]Debug: No servers found for {client_name}[/]")
            else:
                if verbose:
                    console.print(
                        f"[dim]Debug: Found {len(client_servers)} total servers for {client_name}: {list(client_servers.keys())}[/]"
                    )
            for server_name, server_config in client_servers.items():
                # Handle both object attributes and dictionary keys
                if hasattr(server_config, "command"):
                    command = server_config.command
                    args = getattr(server_config, "args", [])
                elif isinstance(server_config, dict):
                    command = server_config.get("command", "")
                    args = server_config.get("args", [])
                else:
                    continue

                # Check if this is an MCPM-managed configuration
                if command == "mcpm":
                    if len(args) >= 3 and args[0] == "profile" and args[1] == "run":
                        # This is an MCPM profile - find profile name after 'run', skipping flags
                        profile_name = None
                        for i in range(2, len(args)):
                            if not args[i].startswith("--"):
                                profile_name = args[i]
                                break
                        if profile_name:
                            mcpm_profiles.append(profile_name)

                        if verbose:
                            mcpm_server_details.append(f"{profile_name}: [magenta]Profile[/]")
                    elif len(args) >= 2 and args[0] == "run":
                        # This is an individual MCPM server
                        actual_server_name = args[1]
                        mcpm_servers.append(actual_server_name)

                        if verbose:
                            # Get the actual server config from global config for details
                            global_server = global_config_manager.get_server(actual_server_name)
                            if global_server:
                                if hasattr(global_server, "command"):
                                    cmd_args = " ".join(global_server.args or [])
                                    mcpm_server_details.append(
                                        f"{actual_server_name}: {global_server.command} {cmd_args}"
                                    )
                                elif hasattr(global_server, "url"):
                                    mcpm_server_details.append(f"{actual_server_name}: {global_server.url}")
                                else:
                                    mcpm_server_details.append(f"{actual_server_name}: Custom")
                            else:
                                mcpm_server_details.append(f"{actual_server_name}: [dim]Not in global config[/]")
                elif server_name.startswith("mcpm_"):
                    # Legacy handling for servers with mcpm_ prefix
                    if command == "mcpm":
                        if len(args) >= 3 and args[0] == "profile" and args[1] == "run":
                            profile_name = args[2]
                            mcpm_profiles.append(profile_name)
                        elif len(args) >= 2 and args[0] == "run":
                            actual_server_name = args[1]
                            mcpm_servers.append(actual_server_name)
                else:
                    # This is a non-MCPM server
                    other_servers.append(server_name)
                    if verbose:
                        console.print(f"[dim]Debug: Found non-MCPM server '{server_name}' with command '{command}'[/]")

        except Exception as e:
            # If we can't read the client config, note it
            if verbose:
                error_msg = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
                row = [
                    client_display,
                    f"[red]Error: {error_msg}[/]",
                    f"[red]Error: {error_msg}[/]",
                    f"[red]Error: {error_msg}[/]",
                    f"[red]Error: {error_msg}[/]",
                ]
            else:
                row = [
                    client_display,
                    "[red]Error reading config[/]",
                    "[red]Error reading config[/]",
                    "[red]Error reading config[/]",
                ]
                if verbose:
                    row.append("[dim]-[/]")
            table.add_row(*row)
            continue

        # Format server lists
        if mcpm_profiles:
            profiles_display = ", ".join([f"[magenta]{p}[/]" for p in mcpm_profiles])
        else:
            profiles_display = "[dim]None[/]"

        if mcpm_servers:
            servers_display = ", ".join(mcpm_servers)
        else:
            servers_display = "[dim]None[/]"

        if other_servers:
            # Show first few servers, with count if many
            if len(other_servers) <= 3:
                other_display = ", ".join(other_servers)
            else:
                other_display = f"{', '.join(other_servers[:3])} +{len(other_servers) - 3} more"
        else:
            other_display = "[dim]None[/]"

        detail_display = "\n".join(mcpm_server_details) if verbose and mcpm_server_details else "[dim]-[/]"

        # Add row
        row = [client_display, profiles_display, servers_display, other_display]
        if verbose:
            row.append(detail_display)
        table.add_row(*row)

    console.print(table)
    console.print()

    # Show uninstalled clients in compact format with client codes
    if uninstalled_client_names:
        uninstalled_display_names = []
        for client_name in sorted(uninstalled_client_names):
            client_info = ClientRegistry.get_client_info(client_name)
            display_name = client_info.get("name", client_name)
            # Include client code for undetected clients
            uninstalled_display_names.append(f"{display_name} ({client_name})")

        console.print(f"[dim]Additional supported clients (not detected): {', '.join(uninstalled_display_names)}[/]")
        console.print()

    console.print("[dim]Tips:[/]")
    console.print("[dim]  • Use 'mcpm client edit <client>' to enable/disable MCPM servers in a client[/]")
    console.print("[dim]  • Use 'mcpm client edit <client> -e' to open client config in your default editor[/]\n")


@client.command(name="info", context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("client_name")
@click.option(
    "-f", "--file", "config_path_override", type=click.Path(), help="Specify a custom path to the client's config file."
)
def info_client(client_name, config_path_override):
    """Display detailed information about a specific MCP client configuration.

    Shows the config file path, installation status, and all currently enabled
    MCP servers (both MCPM-managed and non-MCPM servers) for the specified client.

    CLIENT_NAME is the name of the MCP client to inspect (e.g., cursor, claude-desktop, windsurf).
    """
    # Get the client manager for the specified client
    client_manager = ClientRegistry.get_client_manager(client_name, config_path_override=config_path_override)
    if client_manager is None:
        console.print(f"[red]Error: Client '{client_name}' is not supported.[/]")
        console.print("[yellow]Available clients:[/]")
        supported_clients = ClientRegistry.get_supported_clients()
        for supported_client in sorted(supported_clients):
            console.print(f"  [cyan]{supported_client}[/]")
        return

    client_info = ClientRegistry.get_client_info(client_name)
    display_name = client_info.get("name", client_name)

    # Check if the client is installed
    client_is_installed = client_manager.is_client_installed()
    config_path = client_manager.config_path
    config_exists = os.path.exists(config_path)

    # Header
    console.print(f"\n[bold]{display_name} Client Information[/]")
    console.print("─" * 50)

    # Basic info
    console.print(f"[bold]Client Code:[/] [cyan]{client_name}[/]")
    console.print(f"[bold]Display Name:[/] {display_name}")
    console.print(f"[bold]Installation Status:[/] {'[green]Installed[/]' if client_is_installed else '[yellow]Not detected[/]'}")
    console.print(f"[bold]Config File:[/] [cyan]{config_path}[/]")
    console.print(f"[bold]Config Exists:[/] {'[green]Yes[/]' if config_exists else '[red]No[/]'}")

    if not config_exists:
        console.print(f"\n[yellow]No configuration file found for {display_name}.[/]")
        console.print(f"[dim]You can create a config by running: mcpm client edit {client_name}[/]")
        return

    # Get current profiles and individual servers from client config
    current_profiles, current_individual_servers = _get_current_client_mcpm_state(client_manager)

    # Get all servers from client config
    try:
        all_client_servers = client_manager.get_servers()
    except Exception as e:
        console.print(f"\n[red]Error reading client configuration: {e}[/]")
        return

    # Categorize servers
    mcpm_profile_servers = []
    mcpm_individual_servers = []
    other_servers = []

    for server_name, server_config in all_client_servers.items():
        # Handle both object attributes and dictionary keys
        if hasattr(server_config, "command"):
            command = server_config.command
            args = getattr(server_config, "args", [])
        elif isinstance(server_config, dict):
            command = server_config.get("command", "")
            args = server_config.get("args", [])
        else:
            other_servers.append((server_name, "Unknown configuration"))
            continue

        # Check if this is an MCPM-managed configuration
        if command == "mcpm":
            if len(args) >= 3 and args[0] == "profile" and args[1] == "run":
                # This is an MCPM profile
                profile_name = args[2] if len(args) > 2 else "unknown"
                mcpm_profile_servers.append((server_name, profile_name))
            elif len(args) >= 2 and args[0] == "run":
                # This is an individual MCPM server
                actual_server_name = args[1]
                mcpm_individual_servers.append((server_name, actual_server_name))
            else:
                other_servers.append((server_name, f"mcpm {' '.join(args)}"))
        elif server_name.startswith("mcpm_"):
            # Legacy handling for servers with mcpm_ prefix
            if command == "mcpm":
                if len(args) >= 3 and args[0] == "profile" and args[1] == "run":
                    profile_name = args[2]
                    mcpm_profile_servers.append((server_name, profile_name))
                elif len(args) >= 2 and args[0] == "run":
                    actual_server_name = args[1]
                    mcpm_individual_servers.append((server_name, actual_server_name))
                else:
                    other_servers.append((server_name, f"mcpm {' '.join(args)}"))
            else:
                other_servers.append((server_name, f"{command} {' '.join(args)}"))
        else:
            # This is a non-MCPM server
            cmd_display = f"{command} {' '.join(args)}" if args else command
            other_servers.append((server_name, cmd_display))

    # Display server information
    console.print("\n[bold]MCP Server Configuration:[/]")

    total_servers = len(mcpm_profile_servers) + len(mcpm_individual_servers) + len(other_servers)
    console.print(f"[bold]Total Servers:[/] {total_servers}")

    if mcpm_profile_servers:
        console.print(f"\n[bold magenta]MCPM Profiles ({len(mcpm_profile_servers)}):[/]")
        for client_server_name, profile_name in mcpm_profile_servers:
            console.print(f"  • [cyan]{client_server_name}[/] → Profile: [magenta]{profile_name}[/]")

    if mcpm_individual_servers:
        console.print(f"\n[bold green]MCPM Individual Servers ({len(mcpm_individual_servers)}):[/]")
        for client_server_name, actual_server_name in mcpm_individual_servers:
            console.print(f"  • [cyan]{client_server_name}[/] → Server: [green]{actual_server_name}[/]")

    if other_servers:
        console.print(f"\n[bold yellow]Other Servers ({len(other_servers)}):[/]")
        for server_name, command_info in other_servers:
            console.print(f"  • [cyan]{server_name}[/] → [dim]{command_info[:60]}{'...' if len(command_info) > 60 else ''}[/]")

    if total_servers == 0:
        console.print("  [dim]No MCP servers configured[/]")

    # Footer with helpful commands
    console.print("\n[bold]Helpful Commands:[/]")
    console.print(f"  • [cyan]mcpm client edit {client_name}[/] - Configure servers for this client")
    console.print(f"  • [cyan]mcpm client edit {client_name} -e[/] - Open config file in editor")

    if not client_is_installed:
        console.print(f"\n[yellow]⚠️  Note: {display_name} is not detected as installed.[/]")
        console.print(f"[dim]Install {display_name} for the configuration to take effect.[/]")

    console.print()


@client.command(name="edit", context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("client_name")
@click.option("-e", "--external", is_flag=True, help="Open config file in external editor instead of interactive mode")
@click.option(
    "-f", "--file", "config_path_override", type=click.Path(), help="Specify a custom path to the client's config file."
)
@click.option("--only-mcpm", is_flag=True, help="Remove all non-MCPM servers from the client configuration")
def edit_client(client_name, external, config_path_override, only_mcpm):
    """Enable/disable MCPM-managed servers in the specified client configuration.

    This command provides an interactive interface to integrate MCPM-managed
    servers into your MCP client by adding or removing 'mcpm run {server}'
    entries in the client config. Uses checkbox selection for easy management.

    Use --external/-e to open the config file directly in your default editor
    instead of using the interactive interface.

    Use --only-mcpm to remove all non-MCPM servers from the configuration,
    keeping only MCPM-managed servers and profiles.

    CLIENT_NAME is the name of the MCP client to configure (e.g., cursor, claude-desktop, windsurf).
    """
    # Get the client manager for the specified client
    client_manager = ClientRegistry.get_client_manager(client_name, config_path_override=config_path_override)
    if client_manager is None:
        console.print(f"[red]Error: Client '{client_name}' is not supported.[/]")
        console.print("[yellow]Available clients:[/]")
        supported_clients = ClientRegistry.get_supported_clients()
        for supported_client in sorted(supported_clients):
            console.print(f"  [cyan]{supported_client}[/]")
        return

    client_info = ClientRegistry.get_client_info(client_name)
    display_name = client_info.get("name", client_name)

    # Check if the client is installed
    client_is_installed = client_manager.is_client_installed()
    if not client_is_installed:
        console.print(f"[yellow]⚠️  {display_name} installation not detected.[/]")
        console.print(f"[yellow]Config file will be created at: {client_manager.config_path}[/]")
        console.print(f"[dim]You can still configure servers, but make sure to install {display_name} later.[/]\n")

    # Get the client config file path
    config_path = client_manager.config_path
    config_exists = os.path.exists(config_path)

    console.print(f"[bold]{display_name} Configuration Management[/]")
    console.print(f"[dim]Config file: {config_path}[/]\n")

    # If external editor requested, handle that directly
    if external:
        # Ensure config file exists before opening
        if not config_exists:
            console.print("[yellow]Config file does not exist. Creating basic config...[/]")
            _create_basic_config(config_path)

        _open_in_editor(config_path, display_name)
        return

    # Handle --only-mcpm flag to remove non-MCPM servers
    if only_mcpm:
        if not config_exists:
            console.print("[yellow]Config file does not exist. Nothing to clean.[/]")
            return

        removed_servers = _remove_non_mcpm_servers(client_manager, config_path, display_name)
        if removed_servers:
            console.print(
                f"[green]Removed {len(removed_servers)} non-MCPM server(s) from {display_name} configuration.[/]"
            )
            console.print("[bold]Removed servers:[/]")
            for server_name in sorted(removed_servers):
                console.print(f"  • [red]{server_name}[/]")
            console.print("[bold]Modified files:[/]")
            console.print(f"  [cyan]{config_path}[/]")
            console.print(f"[italic]Restart {display_name} for changes to take effect.[/]")
        else:
            console.print(f"[yellow]No non-MCPM servers found in {display_name} configuration.[/]")
        return

    # Load current client configuration
    current_config = {}
    mcpm_servers = set()  # Servers currently managed by MCPM in client config

    if config_exists:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                current_config = json.load(f)

            # Find servers currently using 'mcpm run' (with mcpm_ prefix)
            mcp_servers = current_config.get("mcpServers", {})
            for client_server_name, server_config in mcp_servers.items():
                command = server_config.get("command", "")
                args = server_config.get("args", [])

                # Check if this is an MCPM-managed server (prefixed with mcpm_)
                if client_server_name.startswith("mcpm_") and (
                    command == "mcpm" and len(args) >= 2 and args[0] == "run"
                ):
                    if len(args) >= 2 and args[0] == "run":
                        # Remove mcpm_ prefix to get actual server name
                        actual_server_name = args[1]
                        mcpm_servers.add(actual_server_name)

        except (json.JSONDecodeError, FileNotFoundError) as e:
            console.print(f"[yellow]Warning: Could not read existing config: {e}[/]")

    # Get all MCPM global servers
    global_servers = global_config_manager.list_servers()

    if not global_servers:
        console.print("[yellow]No servers found in MCPM global configuration.[/]")
        console.print("[dim]Install servers first using: mcpm install <server>[/]")
        return

    # Get current profiles and individual servers from client config
    current_profiles, current_individual_servers = _get_current_client_mcpm_state(client_manager)

    # Display current status
    console.print("[bold]Current MCPM Configuration:[/]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Status in Client", style="green")
    table.add_column("Description", style="white")

    # Show current profiles
    from mcpm.profile.profile_config import ProfileConfigManager

    profile_manager = ProfileConfigManager()
    available_profiles = profile_manager.list_profiles()

    for profile_name in sorted(available_profiles.keys()):
        profile_servers = available_profiles[profile_name]
        status = "[green]Enabled[/]" if profile_name in current_profiles else "[red]Disabled[/]"
        server_names = [server.name for server in profile_servers]
        if len(server_names) <= 3:
            description = f"Profile: {', '.join(server_names)}"
        else:
            description = f"Profile: {', '.join(server_names[:3])} +{len(server_names) - 3} more"
        table.add_row(profile_name, "[magenta]Profile[/]", status, description)

    # Show individual servers
    for server_name, server_config in global_servers.items():
        status = "[green]Enabled[/]" if server_name in current_individual_servers else "[red]Disabled[/]"
        description = getattr(server_config, "description", "") or ""
        table.add_row(server_name, "Server", status, description[:40] + "..." if len(description) > 40 else description)

    console.print(table)
    console.print()

    # Use InquirerPy for interactive profile/server selection
    _interactive_profile_server_selection(
        client_manager,
        config_path,
        current_config,
        current_profiles,
        current_individual_servers,
        available_profiles,
        global_servers,
        display_name,
    )


def _get_current_client_mcpm_state(client_manager):
    """Get current profiles and individual servers from client config."""
    profiles = []
    individual_servers = []

    try:
        client_servers = client_manager.get_servers()
        for server_name, server_config in client_servers.items():
            # Handle both object attributes and dictionary keys
            if hasattr(server_config, "command"):
                command = server_config.command
                args = getattr(server_config, "args", [])
            elif isinstance(server_config, dict):
                command = server_config.get("command", "")
                args = server_config.get("args", [])
            else:
                continue

            # Check if this is an MCPM-managed configuration
            if command == "mcpm":
                if len(args) >= 3 and args[0] == "profile" and args[1] == "run":
                    # This is an MCPM profile
                    profile_name = args[2]
                    profiles.append(profile_name)
                elif len(args) >= 2 and args[0] == "run":
                    # This is an individual MCPM server
                    actual_server_name = args[1]
                    individual_servers.append(actual_server_name)
            elif server_name.startswith("mcpm_"):
                # Legacy handling for servers with mcpm_ prefix
                if command == "mcpm":
                    if len(args) >= 3 and args[0] == "profile" and args[1] == "run":
                        profile_name = args[2]
                        profiles.append(profile_name)
                    elif len(args) >= 2 and args[0] == "run":
                        actual_server_name = args[1]
                        individual_servers.append(actual_server_name)
    except Exception:
        pass  # Return empty lists if we can't read config

    return profiles, individual_servers


def _interactive_profile_server_selection(
    client_manager,
    config_path,
    current_config,
    current_profiles,
    current_individual_servers,
    available_profiles,
    global_servers,
    client_name,
):
    """Interactive profile and server selection using InquirerPy with checkboxes."""
    try:
        # Build choices with current status - profiles first, then servers
        choices = []

        # Add profiles (without Rich markup since InquirerPy doesn't support it)
        for profile_name in sorted(available_profiles.keys()):
            profile_servers = available_profiles[profile_name]
            server_names = [server.name for server in profile_servers]
            server_list = ", ".join(server_names[:3])  # Show first 3 servers
            if len(server_names) > 3:
                server_list += f" +{len(server_names) - 3} more"
            choice_name = f"📦 {profile_name} - Profile ({server_list})"
            is_currently_enabled = profile_name in current_profiles
            choices.append(Choice(value=f"profile:{profile_name}", name=choice_name, enabled=is_currently_enabled))

        # Add individual servers with server emoji
        for server_name in sorted(global_servers.keys()):
            server_config = global_servers[server_name]
            description = getattr(server_config, "description", "") or ""
            choice_name = f"🔧 {server_name} - {description[:40]}" + ("..." if len(description) > 40 else "")
            is_currently_enabled = server_name in current_individual_servers
            choices.append(Choice(value=f"server:{server_name}", name=choice_name, enabled=is_currently_enabled))

        if not choices:
            console.print("[yellow]No MCPM profiles or servers available to configure.[/]")
            return

        # Use InquirerPy checkbox for selection with retry loop for conflicts
        console.print(f"\n[bold]Select profiles/servers to enable in {client_name}:[/]")
        console.print(
            "[dim]📦 = Profiles, 🔧 = Individual servers. Use space to toggle, enter to confirm, ESC to cancel[/]"
        )

        while True:  # Retry loop for conflict resolution
            selected_items = inquirer.checkbox(
                message="Select profiles/servers to enable:",
                choices=choices,
                keybindings={"interrupt": [{"key": "escape"}]},
            ).execute()

            if selected_items is None:
                console.print("[yellow]Operation cancelled.[/]")
                return

            # Separate profiles and servers from selection
            selected_profiles = []
            selected_servers = []

            for item in selected_items:
                if item.startswith("profile:"):
                    profile_name = item[8:]  # Remove "profile:" prefix
                    selected_profiles.append(profile_name)
                elif item.startswith("server:"):
                    server_name = item[7:]  # Remove "server:" prefix
                    selected_servers.append(server_name)

            # Check for conflicts
            conflicts = _check_profile_server_conflicts(selected_profiles, selected_servers, available_profiles)
            if conflicts:
                console.print("\n[red]⚠️  Configuration conflicts detected:[/]")
                for conflict in conflicts:
                    console.print(f"  [yellow]•[/] {conflict}")
                console.print("\n[dim]Profiles and individual servers cannot both contain the same server.[/]")
                console.print("[dim]Please adjust your selection below:[/]\n")

                # Update the choices to reflect current selection for retry
                for choice in choices:
                    if choice.value in selected_items:
                        choice.enabled = True
                    else:
                        choice.enabled = False
                continue  # Go back to selection
            else:
                break  # No conflicts, proceed

        # Check if changes were made
        current_profiles_set = set(current_profiles)
        current_servers_set = set(current_individual_servers)
        new_profiles_set = set(selected_profiles)
        new_servers_set = set(selected_servers)

        if new_profiles_set == current_profiles_set and new_servers_set == current_servers_set:
            console.print("[yellow]No changes made.[/]")
            return

        # Save the updated configuration
        _save_config_with_profiles_and_servers(
            client_manager, config_path, current_config, selected_profiles, selected_servers, client_name
        )

        # Show what changed
        added_profiles = new_profiles_set - current_profiles_set
        removed_profiles = current_profiles_set - new_profiles_set
        added_servers = new_servers_set - current_servers_set
        removed_servers = current_servers_set - new_servers_set

        if added_profiles:
            console.print(f"[green]Enabled profiles: {', '.join(sorted(added_profiles))}[/]")
        if removed_profiles:
            console.print(f"[red]Disabled profiles: {', '.join(sorted(removed_profiles))}[/]")
        if added_servers:
            console.print(f"[green]Enabled servers: {', '.join(sorted(added_servers))}[/]")
        if removed_servers:
            console.print(f"[red]Disabled servers: {', '.join(sorted(removed_servers))}[/]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/]")
    except OSError as e:
        if e.errno == 22:  # Invalid argument - likely terminal issue
            console.print("\n[red]Error: Cannot run interactive selection in this environment.[/]")
            console.print("[yellow]This command requires a proper terminal for interactive selection.[/]")
            console.print("[dim]Try running from a standard terminal or shell.[/]")
        else:
            print_error("System error during selection", str(e))
    except Exception as e:
        console.print(f"[red]Error running interactive selection: {e}[/]")


def _check_profile_server_conflicts(selected_profiles, selected_servers, available_profiles):
    """Check for conflicts between selected profiles and individual servers."""
    conflicts = []

    # Get all servers that are in selected profiles
    profile_servers = set()
    for profile_name in selected_profiles:
        if profile_name in available_profiles:
            profile_server_configs = available_profiles[profile_name]
            for server_config in profile_server_configs:
                profile_servers.add(server_config.name)

    # Check for overlaps
    conflicting_servers = profile_servers.intersection(set(selected_servers))

    for server_name in conflicting_servers:
        # Find which profiles contain this server
        containing_profiles = []
        for profile_name in selected_profiles:
            if profile_name in available_profiles:
                profile_server_configs = available_profiles[profile_name]
                for server_config in profile_server_configs:
                    if server_config.name == server_name:
                        containing_profiles.append(profile_name)
                        break

        profile_list = "', '".join(containing_profiles)
        conflicts.append(f"Server '{server_name}' is in profile(s) '{profile_list}' and also selected individually")

    return conflicts


def _save_config_with_profiles_and_servers(
    client_manager, config_path, current_config, selected_profiles, selected_servers, client_name
):
    """Save the client config with updated profile and server entries using the client manager."""
    try:
        from mcpm.core.schema import STDIOServerConfig

        # Get list of current servers
        current_server_list = client_manager.list_servers()

        # Remove existing MCPM-managed entries (those with mcpm_ prefix or mcpm commands)
        servers_to_remove = []
        for server_name in current_server_list:
            if server_name.startswith("mcpm_"):
                servers_to_remove.append(server_name)
            else:
                # Check if it's an MCPM command
                server_config = client_manager.get_server(server_name)
                if server_config and hasattr(server_config, "command") and server_config.command == "mcpm":
                    servers_to_remove.append(server_name)

        # Remove old MCPM servers and profiles
        for server_name in servers_to_remove:
            client_manager.remove_server(server_name)

        # Add new MCPM profile entries
        for profile_name in selected_profiles:
            prefixed_name = f"mcpm_profile_{profile_name}"
            server_config = STDIOServerConfig(
                name=prefixed_name, command="mcpm", args=["profile", "run", "--stdio-clean", profile_name]
            )
            client_manager.add_server(server_config)

        # Add new MCPM server entries
        for server_name in selected_servers:
            prefixed_name = f"mcpm_{server_name}"
            server_config = STDIOServerConfig(name=prefixed_name, command="mcpm", args=["run", server_name])
            client_manager.add_server(server_config)

        console.print(f"[green]Successfully updated {client_name} configuration![/]")
        console.print("[bold]Modified files:[/]")
        console.print(f"  [cyan]{config_path}[/]")
        console.print(f"[italic]Restart {client_name} for changes to take effect.[/]")

    except Exception as e:
        print_error("Error saving configuration", str(e))


def _interactive_server_selection_inquirer(
    client_manager, config_path, current_config, mcpm_servers, global_servers, client_name
):
    """Interactive server selection using InquirerPy with checkboxes."""
    try:
        # Build choices with current status
        server_choices = []
        for server_name in sorted(global_servers.keys()):
            server_config = global_servers[server_name]
            # Get server description for display
            description = getattr(server_config, "description", "") or ""

            # Show server name and description
            choice_name = f"{server_name} - {description[:40]}" + ("..." if len(description) > 40 else "")

            # Set enabled=True only for servers currently in the client config
            is_currently_enabled = server_name in mcpm_servers
            server_choices.append(Choice(value=server_name, name=choice_name, enabled=is_currently_enabled))

        if not server_choices:
            console.print("[yellow]No MCPM servers available to configure.[/]")
            return

        # Use InquirerPy checkbox for selection
        console.print(f"\n[bold]Select servers to enable in {client_name}:[/]")
        console.print("[dim]Use space to toggle, enter to confirm, ESC to cancel[/]")

        selected_servers = inquirer.checkbox(
            message="Select servers to enable:", choices=server_choices, keybindings={"interrupt": [{"key": "escape"}]}
        ).execute()

        if selected_servers is None:
            console.print("[yellow]Operation cancelled.[/]")
            return

        # Convert to set for comparison
        new_mcpm_servers = set(selected_servers)

        # Check if changes were made
        if new_mcpm_servers == mcpm_servers:
            console.print("[yellow]No changes made.[/]")
            return

        # Save the updated configuration
        _save_config_with_mcpm_servers(client_manager, config_path, current_config, new_mcpm_servers, client_name)

        # Show what changed
        added = new_mcpm_servers - mcpm_servers
        removed = mcpm_servers - new_mcpm_servers

        if added:
            console.print(f"[green]Enabled: {', '.join(sorted(added))}[/]")
        if removed:
            console.print(f"[red]Disabled: {', '.join(sorted(removed))}[/]")

        # Inform about external editor option
        console.print(
            "\n[dim]Tip: Use 'mcpm client edit {client_name} -e' to open config directly in your editor.[/]".format(
                client_name=client_name.replace(" ", "-")
            )
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/]")
    except Exception as e:
        console.print(f"[red]Error running interactive selection: {e}[/]")


def _save_config_with_mcpm_servers(client_manager, config_path, current_config, mcpm_servers, client_name):
    """Save the client config with updated MCPM server entries using the client manager."""
    try:
        from mcpm.core.schema import STDIOServerConfig

        # Get list of current servers
        current_server_list = client_manager.list_servers()

        # Remove existing MCPM-managed entries (those with mcpm_ prefix)
        servers_to_remove = []
        for server_name in current_server_list:
            if server_name.startswith("mcpm_"):
                # Check if it's actually an MCPM server by getting its config
                server_config = client_manager.get_server(server_name)
                if server_config and hasattr(server_config, "command") and server_config.command == "mcpm":
                    args = getattr(server_config, "args", [])
                    if len(args) >= 2 and args[0] == "run":
                        servers_to_remove.append(server_name)

        # Remove old MCPM servers
        for server_name in servers_to_remove:
            client_manager.remove_server(server_name)

        # Add new MCPM-managed entries with mcpm_ prefix
        for server_name in mcpm_servers:
            prefixed_name = f"mcpm_{server_name}"
            # Create a proper ServerConfig object for MCPM server
            server_config = STDIOServerConfig(name=prefixed_name, command="mcpm", args=["run", server_name])
            client_manager.add_server(server_config)

        console.print(f"[green]Successfully updated {client_name} configuration![/]")
        console.print("[bold]Modified files:[/]")
        console.print(f"  [cyan]{config_path}[/]")
        console.print(f"[italic]Restart {client_name} for changes to take effect.[/]")

    except Exception as e:
        print_error("Error saving configuration", str(e))


def _create_basic_config(config_path):
    """Create a basic MCP client config file."""
    basic_config = {"mcpServers": {}}

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # Write the basic config to file
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(basic_config, f, indent=2)
        console.print("[green]Basic config file created successfully![/]")
    except Exception as e:
        print_error("Error creating config file", str(e))
        raise


def _open_in_editor(config_path, client_name):
    """Open the config file in the default editor."""
    try:
        console.print("[bold green]Opening config file in your default editor...[/]")

        # Use appropriate command based on platform
        if os.name == "nt":  # Windows
            os.startfile(config_path)
        elif os.name == "posix":  # macOS and Linux
            subprocess.run(["open", config_path] if os.uname().sysname == "Darwin" else ["xdg-open", config_path])

        console.print(f"[italic]After editing, {client_name} must be restarted for changes to take effect.[/]")
    except Exception as e:
        print_error("Error opening editor", str(e))
        console.print(f"You can manually edit the file at: {config_path}")


@client.command(name="import", context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("client_name")
def import_client(client_name):
    """Import and manage MCP server configurations from a client.

    This command imports server configurations from a supported MCP client,
    shows non-MCPM servers as a selection list, and offers to create profiles
    and replace client config with MCPM managed servers.

    CLIENT_NAME is the name of the MCP client to import from (e.g., cursor, claude-desktop, windsurf).
    """
    # Get client manager
    client_manager = ClientRegistry.get_client_manager(client_name)
    if not client_manager:
        console.print(f"[red]Error: Client '{client_name}' is not supported.[/]")
        console.print("[yellow]Available clients:[/]")
        supported_clients = ClientRegistry.get_supported_clients()
        for supported_client in sorted(supported_clients):
            console.print(f"  [cyan]{supported_client}[/]")
        return

    client_info = ClientRegistry.get_client_info(client_name)
    display_name = client_info.get("name", client_name)

    # Check if client is installed
    if not client_manager.is_client_installed():
        print_error(f"{display_name} installation not detected.")
        return

    # Get client config path
    config_path = client_manager.config_path
    if not os.path.exists(config_path):
        console.print(f"[yellow]No configuration found for {display_name}.[/]")
        return

    console.print(f"[bold]{display_name} Configuration Import[/]")
    console.print(f"[dim]Config file: {config_path}[/]\n")

    # Get all servers from client config
    try:
        client_servers = client_manager.get_servers()
    except Exception as e:
        print_error("Error reading client configuration", str(e))
        return

    if not client_servers:
        console.print(f"[yellow]No MCP servers found in {display_name} configuration.[/]")
        return

    # Separate MCPM-managed servers from non-MCPM servers
    mcpm_servers = []
    non_mcpm_servers = []

    for server_name, server_config in client_servers.items():
        # Check if this is an MCPM-managed server
        is_mcpm_server = False

        # Handle both object attributes and dictionary keys
        if hasattr(server_config, "command"):
            command = server_config.command
            args = getattr(server_config, "args", [])
        elif isinstance(server_config, dict):
            command = server_config.get("command", "")
            args = server_config.get("args", [])
        else:
            continue

        if command == "mcpm" and len(args) >= 2 and args[0] == "run":
            is_mcpm_server = True
            mcpm_servers.append((server_name, args[1]))
        elif server_name.startswith("mcpm_") and command == "mcpm":
            if len(args) >= 2 and args[0] == "run":
                is_mcpm_server = True
                mcpm_servers.append((server_name, args[1]))

        if not is_mcpm_server:
            non_mcpm_servers.append((server_name, server_config))

    # Display current status
    console.print(f"[bold]Found {len(client_servers)} server(s) in {display_name} configuration:[/]")
    console.print(f"  [green]MCPM-managed servers: {len(mcpm_servers)}[/]")
    console.print(f"  [yellow]Non-MCPM servers: {len(non_mcpm_servers)}[/]\n")

    if mcpm_servers:
        console.print("[bold green]MCPM-managed servers:[/]")
        for client_server_name, actual_server_name in mcpm_servers:
            console.print(f"  [cyan]{client_server_name}[/] → [dim]{actual_server_name}[/]")
        console.print()

    if not non_mcpm_servers:
        console.print("[yellow]No non-MCPM servers found to import.[/]")
        return

    # Show non-MCPM servers as InquirerPy selection list
    console.print("[bold yellow]Non-MCPM servers available for import:[/]")

    # Build choices for selection
    server_choices = []
    for server_name, server_config in non_mcpm_servers:
        # Get command info for display
        if hasattr(server_config, "command"):
            command = server_config.command
            args = getattr(server_config, "args", [])
        elif isinstance(server_config, dict):
            command = server_config.get("command", "")
            args = server_config.get("args", [])
        else:
            command = "unknown"
            args = []

        # Create display name with command info
        cmd_display = f"{command} {' '.join(args)}" if args else command
        choice_name = f"{server_name} - {cmd_display[:50]}{'...' if len(cmd_display) > 50 else ''}"
        server_choices.append(Choice(value=server_name, name=choice_name))

    try:
        # Select servers to import
        selected_servers = inquirer.checkbox(
            message="Select servers to import into MCPM global configuration:",
            choices=server_choices,
            keybindings={"interrupt": [{"key": "escape"}]},
        ).execute()

        if not selected_servers:
            console.print("[yellow]No servers selected for import.[/]")
            return

        # Import selected servers to global configuration
        _import_servers_to_global(selected_servers, non_mcpm_servers, client_name)

        # Ask if user wants to create a profile for these servers
        if _ask_create_profile(selected_servers):
            profile_name = _create_profile_for_servers(selected_servers, client_name)
            if profile_name:
                console.print(f"[green]Profile '{profile_name}' created with {len(selected_servers)} server(s).[/]")

                # Ask if user wants to replace client config with the profile
                if _ask_replace_client_config_with_profile(profile_name, client_name):
                    _replace_client_config_with_profile(
                        client_manager, profile_name, client_name, len(selected_servers)
                    )
                    # Skip the individual server replacement since we're using profile
                    return

        # Ask if user wants to replace client config with MCPM managed servers
        if _ask_replace_client_config(selected_servers, client_name):
            _replace_client_config_with_mcpm(client_manager, selected_servers, client_name)

    except KeyboardInterrupt:
        console.print("\n[yellow]Import cancelled.[/]")
    except OSError as e:
        if e.errno == 22:  # Invalid argument - likely terminal issue
            console.print("\n[red]Error: Cannot run interactive selection in this environment.[/]")
            console.print("[yellow]This command requires a proper terminal for interactive selection.[/]")
            console.print("[dim]Try running from a standard terminal or shell.[/]")
        else:
            print_error("System error during import", str(e))
    except Exception as e:
        print_error("Error during import", str(e))


def _import_servers_to_global(selected_servers, non_mcpm_servers, client_name):
    """Import selected servers to global configuration."""
    from mcpm.core.schema import CustomServerConfig, STDIOServerConfig

    console.print(f"\n[bold green]Importing {len(selected_servers)} server(s) to global configuration...[/]")

    imported_count = 0
    table = Table(show_header=True, header_style="bold")
    table.add_column("Server Name", style="cyan")
    table.add_column("Command", style="dim")
    table.add_column("Status", style="green")

    for server_name in selected_servers:
        # Find the server config
        server_config = None
        for name, config in non_mcpm_servers:
            if name == server_name:
                server_config = config
                break

        if not server_config:
            table.add_row(server_name, "Error", "❌ Not found")
            continue

        try:
            # Extract server configuration
            if hasattr(server_config, "command"):
                command = server_config.command
                args = getattr(server_config, "args", [])
                env = getattr(server_config, "env", {})
                cwd = getattr(server_config, "cwd", None)
            elif isinstance(server_config, dict):
                command = server_config.get("command", "")
                args = server_config.get("args", [])
                env = server_config.get("env", {})
                cwd = server_config.get("cwd")
            else:
                # Handle custom server config
                custom_config = CustomServerConfig(name=server_name, config=server_config)
                global_config_manager.add_server(custom_config)
                table.add_row(server_name, "Custom", "✅ Imported")
                imported_count += 1
                continue

            # Create server config object
            server_config_obj = STDIOServerConfig(name=server_name, command=command, args=args, env=env, cwd=cwd)

            # Add to global configuration
            global_config_manager.add_server(server_config_obj)
            imported_count += 1

            # Display command for table
            cmd_display = f"{command} {' '.join(args)}" if args else command
            table.add_row(
                server_name, cmd_display[:30] + "..." if len(cmd_display) > 30 else cmd_display, "✅ Imported"
            )

        except Exception as e:
            table.add_row(server_name, "Error", f"❌ {str(e)[:20]}...")

    console.print(table)
    console.print(f"\n[green]Successfully imported {imported_count} server(s) from {client_name}.[/]")


def _ask_create_profile(selected_servers):
    """Ask user if they want to create a profile for selected servers."""
    if len(selected_servers) == 1:
        message = f"Create a profile for the imported server '{selected_servers[0]}'?"
    else:
        message = f"Create a profile for the {len(selected_servers)} imported servers?"

    try:
        return inquirer.confirm(message=message, default=True).execute()
    except OSError as e:
        if e.errno == 22:  # Invalid argument - likely terminal issue
            console.print("[yellow]Cannot run interactive prompt in this environment. Defaulting to 'yes'.[/]")
            return True
        raise


def _create_profile_for_servers(selected_servers, client_name):
    """Create a profile and add selected servers to it."""
    profile_manager = ProfileConfigManager()

    # Ask for profile name with client code as default
    default_name = client_name.replace("-", "_")  # Replace hyphens with underscores for profile names
    try:
        profile_name = inquirer.text(message="Enter profile name:", default=default_name).execute()
    except OSError as e:
        if e.errno == 22:  # Invalid argument - likely terminal issue
            console.print(
                f"[yellow]Cannot run interactive prompt in this environment. Using default name '{default_name}'.[/]"
            )
            profile_name = default_name
        else:
            raise

    if not profile_name:
        console.print("[yellow]No profile name provided.[/]")
        return None

    try:
        # Create profile if it doesn't exist
        if profile_name not in profile_manager.list_profiles():
            profile_manager.new_profile(profile_name)
            console.print(f"[green]Created profile '{profile_name}'.[/]")

        # Add servers to profile
        for server_name in selected_servers:
            server_config = global_config_manager.get_server(server_name)
            if server_config:
                profile_manager.set_profile(profile_name, server_config)

        return profile_name

    except Exception as e:
        print_error("Error creating profile", str(e))
        return None


def _ask_replace_client_config_with_profile(profile_name, client_name):
    """Ask user if they want to replace client config with profile command."""
    message = f"Replace all servers in {client_name} config with 'mcpm profile run {profile_name}'?"

    console.print(
        f"\n[yellow]This will replace the original server configurations with a single 'mcpm profile run {profile_name}' command.[/]"
    )
    console.print(f"[dim]You can always manually edit the config later using 'mcpm client edit {client_name} -e'[/]")

    try:
        return inquirer.confirm(message=message, default=True).execute()
    except OSError as e:
        if e.errno == 22:  # Invalid argument - likely terminal issue
            console.print("[yellow]Cannot run interactive prompt in this environment. Defaulting to 'yes'.[/]")
            return True
        raise


def _ask_replace_client_config(selected_servers, client_name):
    """Ask user if they want to replace client config with MCPM managed servers."""
    if len(selected_servers) == 1:
        message = f"Replace '{selected_servers[0]}' in {client_name} config with MCPM managed version?"
    else:
        message = f"Replace {len(selected_servers)} servers in {client_name} config with MCPM managed versions?"

    console.print(
        "\n[yellow]This will replace the original server configurations with 'mcpm run <server-name>' commands.[/]"
    )
    console.print(f"[dim]You can always manually edit the config later using 'mcpm client edit {client_name} -e'[/]")

    try:
        return inquirer.confirm(message=message, default=False).execute()
    except OSError as e:
        if e.errno == 22:  # Invalid argument - likely terminal issue
            console.print("[yellow]Cannot run interactive prompt in this environment. Defaulting to 'no'.[/]")
            return False
        raise


def _replace_client_config_with_profile(client_manager, profile_name, client_name, server_count):
    """Replace client config with a single profile command."""
    try:
        from mcpm.core.schema import STDIOServerConfig

        # Get all current servers to remove them
        current_server_list = client_manager.list_servers()

        # Remove all existing servers
        for server_name in current_server_list:
            try:
                client_manager.remove_server(server_name)
            except Exception:
                pass  # Server might not exist or might fail to remove

        # Add single profile command
        profile_server_name = f"mcpm_profile_{profile_name}"
        server_config = STDIOServerConfig(
            name=profile_server_name, command="mcpm", args=["profile", "run", "--stdio-clean", profile_name]
        )
        client_manager.add_server(server_config)

        console.print(f"\n[green]Successfully replaced {client_name} configuration with profile '{profile_name}'.[/]")
        console.print(f"[italic]Restart {client_name} for changes to take effect.[/]")
        console.print(f"[dim]The profile will run all {server_count} servers together.[/]")

    except Exception as e:
        print_error("Error replacing client config with profile", str(e))


def _replace_client_config_with_mcpm(client_manager, selected_servers, client_name):
    """Replace client config servers with MCPM managed versions."""
    try:
        from mcpm.core.schema import STDIOServerConfig

        # Remove original servers
        for server_name in selected_servers:
            try:
                client_manager.remove_server(server_name)
            except Exception:
                pass  # Server might not exist in client config

        # Add MCPM managed versions
        for server_name in selected_servers:
            prefixed_name = f"mcpm_{server_name}"
            server_config = STDIOServerConfig(name=prefixed_name, command="mcpm", args=["run", server_name])
            client_manager.add_server(server_config)

        console.print(
            f"\n[green]Successfully replaced {len(selected_servers)} server(s) in {client_name} config with MCPM managed versions.[/]"
        )
        console.print(f"[italic]Restart {client_name} for changes to take effect.[/]")

    except Exception as e:
        print_error("Error replacing client config", str(e))


@client.command(name="fix-profiles", context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("client_name", required=False)
@click.option("--all", "-a", is_flag=True, help="Fix all detected client configurations")
def fix_profiles(client_name, all):
    """Fix existing MCPM profile configurations to use --stdio-clean flag.

    This command updates existing MCPM profile configurations in client configs
    to use the --stdio-clean flag, which prevents JSON parsing errors in clients
    like Claude Desktop by suppressing banner output and logging.

    Examples:

    \b
        mcpm client fix-profiles claude-desktop    # Fix Claude Desktop profile configs
        mcpm client fix-profiles --all             # Fix all detected clients

    For detailed troubleshooting, see: CLAUDE_DESKTOP_INTEGRATION.md
    """
    from mcpm.clients.client_registry import ClientRegistry

    if all and client_name:
        console.print("[red]Error: Cannot specify both client name and --all flag[/]")
        return

    if not all and not client_name:
        console.print("[red]Error: Must specify either a client name or use --all flag[/]")
        return

    # Get clients to process
    if all:
        installed_clients = ClientRegistry.detect_installed_clients()
        clients_to_process = [name for name, installed in installed_clients.items() if installed]
        if not clients_to_process:
            console.print("[yellow]No installed MCP clients detected[/]")
            return
    else:
        # Validate single client
        supported_clients = ClientRegistry.get_supported_clients()
        if client_name not in supported_clients:
            console.print(f"[red]Error: '{client_name}' is not a supported client[/]")
            console.print(f"Supported clients: {', '.join(supported_clients)}")
            return

        installed_clients = ClientRegistry.detect_installed_clients()
        if not installed_clients.get(client_name, False):
            console.print(f"[yellow]Warning: '{client_name}' is not detected as installed[/]")

        clients_to_process = [client_name]

    total_fixed = 0

    for client in clients_to_process:
        console.print(f"\n[cyan]Checking {client}...[/]")

        # Get client manager
        client_manager = ClientRegistry.get_client_manager(client)
        if not client_manager:
            console.print(f"[yellow]  Skipping {client}: Cannot access configuration[/]")
            continue

        # Find MCPM profile servers that need fixing
        servers_to_fix = []
        try:
            all_servers = client_manager.get_servers()
            for server_name, server_config in all_servers.items():
                # Check if this is an MCPM profile server
                if (
                    server_name.startswith("mcpm_profile_")
                    and hasattr(server_config, "command")
                    and server_config.command == "mcpm"
                    and hasattr(server_config, "args")
                    and len(server_config.args) >= 3
                    and server_config.args[0] == "profile"
                    and server_config.args[1] == "run"
                ):
                    # Check if it already has --stdio-clean
                    if "--stdio-clean" not in server_config.args:
                        servers_to_fix.append((server_name, server_config))

        except Exception as e:
            console.print(f"[yellow]  Skipping {client}: Error reading configuration - {e}[/]")
            continue

        if not servers_to_fix:
            console.print(f"[green]  ✓ No profile configurations need fixing in {client}[/]")
            continue

        # Fix the configurations
        fixed_count = 0
        for server_name, server_config in servers_to_fix:
            try:
                # Extract profile name from args
                profile_name = server_config.args[2] if len(server_config.args) > 2 else "unknown"

                # Create new config with --stdio-clean flag
                from mcpm.core.schema import STDIOServerConfig
                new_server_config = STDIOServerConfig(
                    name=server_name, command="mcpm", args=["profile", "run", "--stdio-clean", profile_name]
                )

                # Replace the server configuration
                client_manager.remove_server(server_name)
                client_manager.add_server(new_server_config)

                console.print(f"[green]  ✓ Fixed profile '{profile_name}' in {server_name}[/]")
                fixed_count += 1

            except Exception as e:
                console.print(f"[red]  ✗ Failed to fix {server_name}: {e}[/]")

        if fixed_count > 0:
            console.print(f"[green]  Fixed {fixed_count} profile configuration(s) in {client}[/]")
            total_fixed += fixed_count

    if total_fixed > 0:
        console.print(
            f"\n[green]Successfully fixed {total_fixed} profile configuration(s) across {len(clients_to_process)} client(s)[/]"
        )
        console.print("[italic]Restart your MCP clients for changes to take effect.[/]")
    else:
        console.print("\n[green]All profile configurations are already up to date![/]")


def _remove_non_mcpm_servers(client_manager, config_path, client_name):
    """Remove all non-MCPM servers from the client configuration.

    Returns a list of removed server names.
    """
    try:
        # Get all servers from client config
        all_servers = client_manager.get_servers()
        if not all_servers:
            return []

        # Identify non-MCPM servers
        non_mcpm_servers = []
        for server_name, server_config in all_servers.items():
            is_mcpm_server = False

            # Handle both object attributes and dictionary keys
            if hasattr(server_config, "command"):
                command = server_config.command
                args = getattr(server_config, "args", [])
            elif isinstance(server_config, dict):
                command = server_config.get("command", "")
                args = server_config.get("args", [])
            else:
                # Unknown config type, consider it non-MCPM
                non_mcpm_servers.append(server_name)
                continue

            # Check if this is an MCPM-managed server
            if command == "mcpm":
                # This is an MCPM command
                if (len(args) >= 2 and args[0] == "run") or (
                    len(args) >= 3 and args[0] == "profile" and args[1] == "run"
                ):
                    is_mcpm_server = True
            elif server_name.startswith("mcpm_"):
                # Legacy MCPM server with prefix
                if command == "mcpm":
                    is_mcpm_server = True

            if not is_mcpm_server:
                non_mcpm_servers.append(server_name)

        # Remove non-MCPM servers
        removed_servers = []
        for server_name in non_mcpm_servers:
            try:
                client_manager.remove_server(server_name)
                removed_servers.append(server_name)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not remove server '{server_name}': {e}[/]")

        return removed_servers

    except Exception as e:
        print_error("Error removing non-MCPM servers", str(e))
        return []

"""Profile status command."""

import logging
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.rich_click_config import click

profile_config_manager = ProfileConfigManager()
logger = logging.getLogger(__name__)
console = Console(stderr=True)


@click.command()
@click.argument("profile_name")
@click.help_option("-h", "--help")
def status(profile_name):
    """Show which clients are using a profile and their current state.

    Displays comprehensive information about a profile including:
    - Profile metadata (description, server count)
    - Which clients are currently using this profile
    - Current deployment status

    Examples:

    \b
        mcpm profile status web-dev      # Show status of web-dev profile
        mcpm profile status minimal      # Show status of minimal profile
    """

    # Validate profile name
    if not profile_name or not profile_name.strip():
        logger.error("Profile name cannot be empty")
        return 1

    profile_name = profile_name.strip()

    # Get profile info
    try:
        profile_servers = profile_config_manager.get_profile(profile_name)
        if profile_servers is None:
            console.print(f"[red]Profile '{profile_name}' not found[/]")
            console.print("\n[dim]Available profiles:[/]")
            profiles = profile_config_manager.list_profiles()
            if profiles:
                for p_name in profiles.keys():
                    console.print(f"  • {p_name}")
            else:
                console.print("  [dim](no profiles found)[/]")
            console.print(f"\n[dim]Create profile with:[/] mcpm profile create {profile_name}")
            return 1
    except Exception as e:
        logger.error(f"Error accessing profile '{profile_name}': {e}")
        return 1

    # Get profile metadata
    profile_metadata = profile_config_manager.get_profile_metadata(profile_name)

    # Find clients using profile
    from mcpm.clients.client_registry import ClientRegistry
    clients_using_profile = ClientRegistry.find_clients_using_profile(profile_name)

    # Create main info panel
    profile_info = f"[bold]Profile:[/] {profile_name}\n"

    if profile_metadata and profile_metadata.description:
        profile_info += f"[bold]Description:[/] {profile_metadata.description}\n"

    profile_info += f"[bold]Servers:[/] {len(profile_servers)}\n"
    profile_info += f"[bold]Clients using profile:[/] {len(clients_using_profile)}"

    # Add deployment status
    if clients_using_profile:
        profile_info += "\n[bold]Status:[/] [green]Active (deployed to clients)[/]"
    else:
        profile_info += "\n[bold]Status:[/] [yellow]Inactive (no clients using profile)[/]"

    panel = Panel(
        profile_info,
        title=f"📋 Profile Status",
        title_align="left",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(panel)

    # Show servers in profile
    if profile_servers:
        console.print(f"\n[bold]Servers in profile:[/]")
        server_table = Table(show_header=True, header_style="bold magenta")
        server_table.add_column("Name", style="cyan")
        server_table.add_column("Type", style="green")
        server_table.add_column("Command/URL", style="dim")

        for server in profile_servers:
            server_type = type(server).__name__.replace("ServerConfig", "")
            if hasattr(server, 'command'):
                cmd_info = f"{server.command}"
                if hasattr(server, 'args') and server.args:
                    cmd_info += f" {' '.join(server.args[:3])}"  # Show first 3 args
                    if len(server.args) > 3:
                        cmd_info += "..."
            elif hasattr(server, 'url'):
                cmd_info = server.url
            else:
                cmd_info = "Unknown"

            server_table.add_row(server.name, server_type, cmd_info)

        console.print(server_table)

    # Show clients using profile
    if clients_using_profile:
        console.print(f"\n[bold]Clients using this profile:[/]")
        client_table = Table(show_header=True, header_style="bold green")
        client_table.add_column("Client", style="cyan")
        client_table.add_column("Status", style="green")
        client_table.add_column("Config Path", style="dim")

        for client_name, client_manager in clients_using_profile:
            try:
                status_text = "✓ Installed" if client_manager.is_client_installed() else "✗ Not Installed"
                config_path = getattr(client_manager, 'config_path', 'Unknown')
                client_table.add_row(client_name, status_text, config_path)
            except Exception as e:
                client_table.add_row(client_name, f"✗ Error: {e}", "Unknown")

        console.print(client_table)
    else:
        console.print(f"\n[yellow]No clients are currently using this profile.[/]")
        console.print(f"[dim]To assign this profile to a client:[/]")
        console.print(f"  • Run [cyan]mcpm client list[/] to see available clients")
        console.print(f"  • Run [cyan]mcpm client edit <client>[/] to configure a client")

    # Show deployment suggestions - always show regardless of client usage
    console.print(f"\n[bold]Available actions:[/]")
    console.print(f"  • [cyan]mcpm profile deploy {profile_name}[/] - Deploy servers directly to client configs (zen approach)")
    console.print(f"  • [cyan]mcpm profile run {profile_name}[/] - Run as FastMCP proxy server (traditional approach)")
    console.print(f"  • [cyan]mcpm profile edit {profile_name}[/] - Modify profile servers")

    return 0

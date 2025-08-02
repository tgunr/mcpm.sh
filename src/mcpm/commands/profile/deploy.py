"""Profile deploy command."""

import logging
import sys
from rich.console import Console
from rich.panel import Panel

from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.rich_click_config import click

profile_config_manager = ProfileConfigManager()
logger = logging.getLogger(__name__)
console = Console(stderr=True)


@click.command()
@click.argument("profile_name")
@click.help_option("-h", "--help")
def deploy(profile_name):
    """Deploy profile servers directly to client configurations.

    This command finds all clients using the specified profile and updates
    their configuration files with the individual servers from the profile,
    eliminating the need for a proxy server.

    The zen deployment approach provides:
    - Direct client-to-server connections (better performance)
    - No single point of failure (better reliability)
    - Transparent configuration (easier debugging)
    - Persistent setup (survives client restarts)

    Examples:

    \b
        mcpm profile deploy web-dev      # Deploy web-dev profile to all clients using it
        mcpm profile deploy minimal      # Deploy minimal profile to all clients using it

    To rollback to proxy mode, use:
        mcpm profile run profile-name

    After deployment, restart your MCP clients for changes to take effect.
    """

    # Validate profile name
    if not profile_name:
        console.print("[red]Profile name cannot be empty[/]")
        sys.exit(1)

    profile_name = profile_name.strip()
    if not profile_name:
        console.print("[red]Profile name cannot be empty[/]")
        sys.exit(1)

    # Validate profile exists
    try:
        profile_servers = profile_config_manager.get_profile(profile_name)
        if profile_servers is None:
            console.print(f"[red]Profile '{profile_name}' not found[/]")
            console.print("[dim]Available options:[/]")
            console.print("[dim]  • Run 'mcpm profile ls' to see available profiles[/]")
            console.print(f"[dim]  • Run 'mcpm profile create {profile_name}' to create a profile[/]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error accessing profile '{profile_name}': {e}[/]")
        sys.exit(1)

    if not profile_servers:
        console.print(f"[yellow]Profile '{profile_name}' has no servers configured[/]")
        console.print("[dim]Add servers to this profile with:[/]")
        console.print(f"[dim]  mcpm profile edit {profile_name}[/]")
        sys.exit(1)

    # Find clients using this profile
    from mcpm.clients.client_registry import ClientRegistry

    try:
        clients_using_profile = ClientRegistry.find_clients_using_profile(profile_name)
    except Exception as e:
        console.print(f"[red]Error discovering clients using profile '{profile_name}': {e}[/]")
        sys.exit(1)

    if not clients_using_profile:
        console.print(f"[yellow]No clients found using profile '{profile_name}'[/]")
        console.print("[dim]To assign this profile to a client:[/]")
        console.print("[dim]  • Run 'mcpm client list' to see available clients[/]")
        console.print("[dim]  • Run 'mcpm client edit <client>' to configure a client with this profile[/]")
        sys.exit(1)

    console.print(f"[blue]Found {len(clients_using_profile)} client(s) using profile '{profile_name}'[/]")

    # Expand profile to individual servers
    try:
        expanded_servers = profile_config_manager.expand_profile_to_client_configs(profile_name)
    except Exception as e:
        console.print(f"[red]Error expanding profile '{profile_name}': {e}[/]")
        sys.exit(1)

    if not expanded_servers:
        console.print(f"[red]Failed to expand profile '{profile_name}' to server configurations[/]")
        sys.exit(1)

    console.print(f"[blue]Expanding profile to {len(expanded_servers)} individual servers[/]")

    # Display deployment plan
    console.print(f"\n[bold blue]🚀 Deployment Plan[/]")
    console.print(f"Profile: [cyan]{profile_name}[/]")
    console.print(f"Servers to deploy: [green]{len(expanded_servers)}[/]")
    console.print(f"Clients to update: [yellow]{len(clients_using_profile)}[/]")

    # List servers being deployed
    console.print(f"\n[bold]Servers:[/]")
    for server in expanded_servers:
        server_type = type(server).__name__.replace("ServerConfig", "")
        console.print(f"  • [cyan]{server.name}[/] ({server_type})")

    # List clients being updated
    console.print(f"\n[bold]Clients:[/]")
    for client_name, _ in clients_using_profile:
        console.print(f"  • [yellow]{client_name}[/]")

    # Update each client
    console.print(f"\n[bold blue]📁 Updating Client Configurations[/]")
    success_count = 0
    total_clients = len(clients_using_profile)
    modified_files = []

    for client_name, client_manager in clients_using_profile:
        console.print(f"Updating [yellow]{client_name}[/]...", end=" ")

        try:
            if client_manager.replace_profile_with_servers(profile_name, expanded_servers):
                console.print("[green]✓[/]")
                success_count += 1
                # Track the modified config file
                modified_files.append((client_name, client_manager.config_path))
            else:
                console.print("[red]✗[/]")
                logger.error(f"Failed to update {client_name}")
        except Exception as e:
            console.print("[red]✗[/]")
            logger.error(f"Error updating {client_name}: {e}")

    # Report results
    if success_count > 0:
        # Success panel
        success_panel = Panel(
            f"[green]Successfully deployed profile '[bold]{profile_name}[/]' to {success_count}/{total_clients} client(s)[/]\n\n"
            f"[bold]Deployed:[/] {len(expanded_servers)} servers\n"
            f"[bold]Updated:[/] {success_count} client configurations\n\n"
            f"[yellow]⚠️  Important:[/] [bold]Restart your MCP clients[/] for changes to take effect\n\n"
            f"[dim]To rollback to proxy mode, run:[/]\n"
            f"[cyan]mcpm profile run {profile_name}[/]",
            title="🎉 Deployment Successful",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        )
        console.print(success_panel)

        # Show updated clients and modified files
        console.print(f"\n[bold]Updated clients:[/]")
        for client_name, _ in clients_using_profile:
            console.print(f"  • [green]{client_name}[/]")
        
        console.print(f"\n[bold]Modified files:[/]")
        for client_name, config_path in modified_files:
            console.print(f"  • [cyan]{config_path}[/] [dim]({client_name})[/]")

    else:
        # Failure panel
        failure_panel = Panel(
            f"[red]Failed to deploy profile '[bold]{profile_name}[/]' to any clients[/]\n\n"
            f"[bold]Common issues:[/]\n"
            f"• Client configuration files may not be writable\n"
            f"• Client config paths may be incorrect\n"
            f"• Profile servers may not be compatible with clients\n\n"
            f"[dim]For debugging, run with:[/]\n"
            f"[cyan]MCPM_DEBUG=1 mcpm profile deploy {profile_name}[/]",
            title="❌ Deployment Failed",
            title_align="left",
            border_style="red",
            padding=(1, 2),
        )
        console.print(failure_panel)

    if success_count == 0:
        sys.exit(1)
    return 0

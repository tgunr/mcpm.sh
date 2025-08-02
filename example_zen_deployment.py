#!/usr/bin/env python3
"""
Practical Example: Zen Profile Deployment

This example demonstrates the zen approach to profile deployment,
showing how to move from proxy-based profile execution to direct
client configuration updates.

Run this script to see the zen deployment approach in action.
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def run_command(cmd, capture_output=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def print_step(step_num, title, description):
    """Print a formatted step"""
    console.print(f"\n[bold blue]Step {step_num}: {title}[/]")
    console.print(f"[dim]{description}[/]")

def print_success(message):
    """Print success message"""
    console.print(f"[green]✓ {message}[/]")

def print_error(message):
    """Print error message"""
    console.print(f"[red]✗ {message}[/]")

def print_info(message):
    """Print info message"""
    console.print(f"[blue]ℹ {message}[/]")

def main():
    """Demonstrate zen profile deployment"""

    console.print("[bold cyan]🧘 Zen Profile Deployment Example[/]")
    console.print("=" * 50)

    # Step 1: Create a demonstration profile
    print_step(1, "Create Demo Profile", "Setting up a 'zen-demo' profile with common servers")

    success, stdout, stderr = run_command("mcpm profile create zen-demo")
    if success:
        print_success("Created 'zen-demo' profile")
    else:
        print_error(f"Failed to create profile: {stderr}")
        return

    # Step 2: Add servers to the profile
    print_step(2, "Add Servers to Profile", "Adding filesystem and memory servers to the profile")

    # Install servers if they don't exist
    servers_to_add = ["filesystem", "memory"]

    for server in servers_to_add:
        success, stdout, stderr = run_command(f"mcpm install {server}")
        if success:
            print_success(f"Installed {server} server")
        else:
            print_info(f"Server {server} already exists or installation skipped")

    # Add servers to profile (this would typically be done through interactive edit)
    for server in servers_to_add:
        success, stdout, stderr = run_command(f"mcpm profile add zen-demo {server}")
        if success:
            print_success(f"Added {server} to zen-demo profile")
        else:
            print_info(f"Server {server} may already be in profile")

    # Step 3: Show profile status
    print_step(3, "Check Profile Status", "Viewing the current state of our demo profile")

    success, stdout, stderr = run_command("mcpm profile status zen-demo", capture_output=False)
    if not success:
        print_error("Could not get profile status")

    # Step 4: List available clients
    print_step(4, "Discover Available Clients", "Finding MCP clients that can use our profile")

    success, stdout, stderr = run_command("mcpm client list")
    if success:
        console.print("\n[bold]Available Clients:[/]")
        lines = stdout.strip().split('\n')
        for line in lines[1:]:  # Skip header
            if line.strip():
                console.print(f"  • {line.strip()}")
    else:
        print_error("Could not list clients")

    # Step 5: Demonstrate profile assignment (simulation)
    print_step(5, "Profile Assignment", "How to assign the profile to a client")

    console.print("\n[yellow]To assign this profile to a client, you would run:[/]")
    console.print("[dim]mcpm client edit claude-desktop[/]")
    console.print("[dim]Then select the 'zen-demo' profile from the interactive menu[/]")

    # Step 6: Compare deployment approaches
    print_step(6, "Deployment Approaches", "Comparing legacy proxy vs zen deployment")

    table = Table(title="Proxy vs Zen Deployment Comparison")
    table.add_column("Aspect", style="cyan")
    table.add_column("Legacy Proxy", style="yellow")
    table.add_column("Zen Deployment", style="green")

    table.add_row("Command",
                  "mcpm profile run zen-demo",
                  "mcpm profile run --deploy zen-demo")
    table.add_row("Process",
                  "Starts proxy server",
                  "Updates client configs directly")
    table.add_row("Connection",
                  "Client → Proxy → Servers",
                  "Client → Servers (direct)")
    table.add_row("Reliability",
                  "Single point of failure",
                  "Independent server processes")
    table.add_row("Performance",
                  "Proxy overhead",
                  "Direct connections")
    table.add_row("Transparency",
                  "Hidden behind proxy",
                  "Visible in client config")
    table.add_row("Persistence",
                  "Lost on proxy restart",
                  "Survives client restarts")

    console.print(table)

    # Step 7: Show zen deployment command
    print_step(7, "Zen Deployment", "How to deploy the profile using the zen approach")

    console.print("\n[bold green]Zen Deployment Command:[/]")
    console.print("[cyan]mcpm profile run --deploy zen-demo[/]")

    console.print("\n[bold]What this command does:[/]")
    console.print("1. [dim]Finds all clients using the 'zen-demo' profile[/]")
    console.print("2. [dim]Expands the profile to individual server configurations[/]")
    console.print("3. [dim]Updates each client's config file with the servers[/]")
    console.print("4. [dim]Reports success/failure for each client[/]")

    # Step 8: Demonstrate deployment (if clients are available)
    print_step(8, "Live Deployment Demo", "Attempting to deploy the profile")

    success, stdout, stderr = run_command("mcpm profile run --deploy zen-demo", capture_output=False)
    if success:
        print_success("Zen deployment completed successfully!")
    else:
        print_info("No clients found using the zen-demo profile (this is expected)")
        console.print("\n[dim]To see zen deployment in action:[/]")
        console.print("[dim]1. Assign the zen-demo profile to a client[/]")
        console.print("[dim]2. Run: mcpm profile run --deploy zen-demo[/]")
        console.print("[dim]3. Restart the client to see the changes[/]")

    # Step 9: Cleanup and best practices
    print_step(9, "Best Practices", "Tips for effective zen deployment")

    practices_panel = Panel(
        """[bold]Zen Deployment Best Practices:[/]

• [green]Test profiles first[/] with 'mcpm profile status profile-name'
• [green]Start small[/] - deploy to one client first, then expand
• [green]Use descriptive names[/] - 'web-dev', 'data-analysis', not 'profile1'
• [green]Monitor deployments[/] - check that all clients updated successfully
• [green]Restart clients[/] after deployment for changes to take effect
• [green]Keep profiles focused[/] - group related servers together
• [green]Regular maintenance[/] - review and clean up unused profiles

[bold]Troubleshooting:[/]

• [yellow]No clients found?[/] Check profile assignment with 'mcpm profile status'
• [yellow]Deployment failed?[/] Verify client config permissions and paths
• [yellow]Client not responding?[/] Restart the client after deployment
• [yellow]Need help?[/] Use 'MCPM_DEBUG=1' for verbose output""",
        title="🧘 Zen Wisdom",
        border_style="blue"
    )
    console.print(practices_panel)

    # Step 10: Cleanup
    print_step(10, "Cleanup", "Removing the demo profile")

    console.print("\n[yellow]Would you like to remove the demo profile? (y/n)[/]", end=" ")
    try:
        response = input().strip().lower()
        if response in ['y', 'yes']:
            success, stdout, stderr = run_command("mcpm profile remove zen-demo")
            if success:
                print_success("Removed zen-demo profile")
            else:
                print_error(f"Failed to remove profile: {stderr}")
        else:
            print_info("Keeping zen-demo profile for your experimentation")
    except KeyboardInterrupt:
        print_info("\nKeeping zen-demo profile")

    # Final summary
    console.print("\n" + "=" * 50)
    console.print("[bold cyan]🎉 Zen Deployment Example Complete![/]")
    console.print("\n[bold]Key Takeaways:[/]")
    console.print("• [green]Zen deployment is simpler and more reliable[/]")
    console.print("• [green]Direct client config updates eliminate proxy complexity[/]")
    console.print("• [green]One command deploys entire development environments[/]")
    console.print("• [green]Full transparency into what's running where[/]")

    console.print(f"\n[bold]Start your zen journey:[/] [cyan]mcpm profile run --deploy your-profile[/] 🧘")

if __name__ == "__main__":
    main()

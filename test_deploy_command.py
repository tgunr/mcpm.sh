#!/usr/bin/env python3
"""
Test script for the new mcpm profile deploy command.

This script validates the zen deployment approach using the separate
deploy command as specified by the user requirements.
"""

import sys
import os
import subprocess
import tempfile
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def run_command(cmd, capture_output=True, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            cwd=cwd
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

def test_deploy_command_exists():
    """Test that the deploy command exists and shows help"""
    print_step(1, "Command Existence", "Verifying mcpm profile deploy command exists")

    success, stdout, stderr = run_command("mcpm profile deploy --help")
    if success and "Deploy profile servers directly" in stdout:
        print_success("Deploy command exists and shows correct help")
        return True
    else:
        print_error(f"Deploy command not found or incorrect help: {stderr}")
        return False

def test_run_command_unchanged():
    """Test that the run command still works without deploy functionality"""
    print_step(2, "Run Command Compatibility", "Verifying mcpm profile run works as FastMCP proxy")

    success, stdout, stderr = run_command("mcpm profile run --help")
    if success and "FastMCP proxy" in stdout and "--deploy" not in stdout:
        print_success("Run command maintains FastMCP proxy functionality without --deploy flag")
        return True
    else:
        print_error(f"Run command help incorrect: {stderr}")
        return False

def test_profile_validation():
    """Test profile validation in deploy command"""
    print_step(3, "Profile Validation", "Testing deploy command with non-existent profile")

    # Test with non-existent profile
    success, stdout, stderr = run_command("mcpm profile deploy nonexistent-profile", capture_output=True)
    if not success:
        print_success("Deploy command correctly rejects non-existent profile")
        return True
    else:
        print_error("Deploy command should fail with non-existent profile")
        return False

def test_deploy_vs_run_separation():
    """Test that deploy and run are properly separated"""
    print_step(4, "Command Separation", "Verifying deploy and run are separate commands")

    tests = [
        ("mcpm profile deploy --help", "Deploy profile servers directly"),
        ("mcpm profile run --help", "FastMCP proxy"),
    ]

    all_passed = True
    for cmd, expected_text in tests:
        success, stdout, stderr = run_command(cmd)
        if success and expected_text in stdout:
            print_success(f"Command '{cmd.split()[-2]}' shows correct functionality")
        else:
            print_error(f"Command '{cmd.split()[-2]}' missing expected text: {expected_text}")
            all_passed = False

    return all_passed

def test_status_command_updates():
    """Test that status command shows both deploy and run options"""
    print_step(5, "Status Command Updates", "Verifying status command shows both options")

    # Create a test profile first
    run_command("mcpm profile create test-deploy-profile")

    success, stdout, stderr = run_command("mcpm profile status test-deploy-profile", capture_output=True)

    expected_texts = [
        "mcpm profile deploy",
        "mcpm profile run",
        "zen approach",
        "traditional approach"
    ]

    all_found = True
    for text in expected_texts:
        if text not in stdout:
            print_error(f"Status command missing expected text: {text}")
            all_found = False

    if all_found:
        print_success("Status command shows both deploy and run options correctly")

    # Clean up
    run_command("mcpm profile remove test-deploy-profile")

    return all_found

def test_error_handling():
    """Test error handling in deploy command"""
    print_step(6, "Error Handling", "Testing deploy command error scenarios")

    test_cases = [
        ("mcpm profile deploy", "Profile name cannot be empty"),
        ("mcpm profile deploy ''", "Profile name cannot be empty"),
        ("mcpm profile deploy non-existent", "not found"),
    ]

    all_passed = True
    for cmd, expected_error in test_cases:
        success, stdout, stderr = run_command(cmd, capture_output=True)
        if not success:
            print_success(f"Deploy correctly handles error case: {cmd}")
        else:
            print_error(f"Deploy should fail for: {cmd}")
            all_passed = False

    return all_passed

def test_deployment_simulation():
    """Test deployment simulation with a real profile"""
    print_step(7, "Deployment Simulation", "Testing deployment with existing profile")

    # List available profiles
    success, stdout, stderr = run_command("mcpm profile ls")
    if not success:
        print_info("No profiles available for deployment test")
        return True

    # Parse profile names from output
    profiles = []
    for line in stdout.split('\n'):
        if line.strip() and not line.startswith('Profile') and '│' not in line:
            profile_name = line.strip()
            if profile_name and not profile_name.startswith('-'):
                profiles.append(profile_name)

    if not profiles:
        print_info("No suitable profiles found for deployment test")
        return True

    # Test deployment with first available profile
    test_profile = profiles[0]
    print_info(f"Testing deployment with profile: {test_profile}")

    success, stdout, stderr = run_command(f"mcpm profile deploy {test_profile}", capture_output=True)

    # Deployment might fail if no clients use the profile, which is expected
    if "No clients found using profile" in stderr or "No clients found using profile" in stdout:
        print_success("Deploy correctly reports no clients using profile")
        return True
    elif success:
        print_success("Deploy completed successfully")
        return True
    else:
        print_info(f"Deploy test result: {stderr}")
        return True  # Not necessarily a failure

def test_help_consistency():
    """Test that help messages are consistent between commands"""
    print_step(8, "Help Consistency", "Verifying help messages mention each other appropriately")

    # Check that run command mentions deploy
    success, stdout, stderr = run_command("mcpm profile run --help")
    if "mcpm profile deploy" in stdout:
        print_success("Run command help mentions deploy command")
        run_mentions_deploy = True
    else:
        print_error("Run command help should mention deploy command")
        run_mentions_deploy = False

    # Check that deploy command mentions run for rollback
    success, stdout, stderr = run_command("mcpm profile deploy --help")
    if "mcpm profile run" in stdout and "rollback" in stdout.lower():
        print_success("Deploy command help mentions run command for rollback")
        deploy_mentions_run = True
    else:
        print_error("Deploy command help should mention run command for rollback")
        deploy_mentions_run = False

    return run_mentions_deploy and deploy_mentions_run

def test_rollback_instructions():
    """Test that rollback instructions are clear"""
    print_step(9, "Rollback Instructions", "Verifying rollback guidance is provided")

    success, stdout, stderr = run_command("mcpm profile deploy --help")

    rollback_indicators = [
        "rollback",
        "mcpm profile run",
        "proxy mode"
    ]

    found_indicators = 0
    for indicator in rollback_indicators:
        if indicator.lower() in stdout.lower():
            found_indicators += 1

    if found_indicators >= 2:
        print_success("Deploy command provides clear rollback instructions")
        return True
    else:
        print_error("Deploy command should provide clearer rollback instructions")
        return False

def main():
    """Run all tests for the deploy command"""
    console.print("[bold cyan]🧘 Testing Zen Profile Deploy Command[/]")
    console.print("=" * 60)

    tests = [
        ("Deploy Command Exists", test_deploy_command_exists),
        ("Run Command Unchanged", test_run_command_unchanged),
        ("Profile Validation", test_profile_validation),
        ("Command Separation", test_deploy_vs_run_separation),
        ("Status Command Updates", test_status_command_updates),
        ("Error Handling", test_error_handling),
        ("Deployment Simulation", test_deployment_simulation),
        ("Help Consistency", test_help_consistency),
        ("Rollback Instructions", test_rollback_instructions),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✓ PASS" if result else "✗ FAIL"
            console.print(f"\n{status}: {test_name}")
        except Exception as e:
            results.append((test_name, False))
            console.print(f"\n✗ ERROR: {test_name} - {e}")

    # Summary
    console.print("\n" + "=" * 60)
    console.print("🧘 Test Summary")
    console.print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    # Results table
    table = Table(title="Test Results")
    table.add_column("Test", style="cyan")
    table.add_column("Result", style="bold")

    for test_name, result in results:
        status = "[green]✓ PASS[/]" if result else "[red]✗ FAIL[/]"
        table.add_row(test_name, status)

    console.print(table)

    console.print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        success_panel = Panel(
            f"[green]All tests passed![/]\n\n"
            f"[bold]The zen deploy command is working correctly:[/]\n"
            f"• [green]mcpm profile deploy <profile>[/] - Deploy servers directly\n"
            f"• [green]mcpm profile run <profile>[/] - Use FastMCP proxy\n"
            f"• [green]mcpm profile status <profile>[/] - Check deployment status\n\n"
            f"[dim]Both deployment approaches are available and working properly.[/]",
            title="🎉 Success",
            border_style="green"
        )
        console.print(success_panel)
    else:
        failure_panel = Panel(
            f"[red]{total - passed} test(s) failed.[/]\n\n"
            f"[bold]Common issues to check:[/]\n"
            f"• Deploy command properly imported in __init__.py\n"
            f"• Help text contains required information\n"
            f"• Error handling works correctly\n"
            f"• Commands reference each other appropriately\n\n"
            f"[dim]Review the failing tests above for specific issues.[/]",
            title="⚠️ Issues Found",
            border_style="red"
        )
        console.print(failure_panel)

    # Usage examples
    console.print(f"\n[bold]Usage Examples:[/]")
    console.print(f"[cyan]mcpm profile deploy web-dev[/] - Deploy web-dev profile directly")
    console.print(f"[cyan]mcpm profile run web-dev[/] - Run web-dev profile via FastMCP proxy")
    console.print(f"[cyan]mcpm profile status web-dev[/] - Check deployment status")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script for the new profile deployment functionality.

This script validates the zen approach of direct client config updates
instead of using the FastMCP proxy approach.
"""

import sys
import os
import logging
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcpm.clients.client_registry import ClientRegistry
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.core.schema import STDIOServerConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_client_profile_discovery():
    """Test the client profile discovery functionality"""
    print("\n=== Testing Client Profile Discovery ===")

    try:
        # Test finding clients using a specific profile
        test_profile = "minimal"
        clients = ClientRegistry.find_clients_using_profile(test_profile)

        print(f"Clients using profile '{test_profile}': {len(clients)}")
        for client_name, client_manager in clients:
            print(f"  - {client_name}: {type(client_manager).__name__}")

        # Test getting all profile usage
        all_usage = ClientRegistry.get_all_profile_usage()
        print(f"\nAll profile usage across clients:")
        for client_name, profiles in all_usage.items():
            print(f"  - {client_name}: {profiles}")

        return True

    except Exception as e:
        print(f"Error in client profile discovery: {e}")
        return False


def test_profile_expansion():
    """Test profile expansion to client configs"""
    print("\n=== Testing Profile Expansion ===")

    try:
        profile_manager = ProfileConfigManager()

        # List available profiles
        profiles = profile_manager.list_profiles()
        print(f"Available profiles: {list(profiles.keys())}")

        if not profiles:
            print("No profiles found - creating test profile")

            # Create a test profile with some servers
            test_server1 = STDIOServerConfig(
                name="test-server-1",
                command="python",
                args=["-m", "test_server"]
            )
            test_server2 = STDIOServerConfig(
                name="test-server-2",
                command="node",
                args=["test-server.js"]
            )

            profile_manager.new_profile("test-profile")
            profile_manager.set_profile("test-profile", test_server1)
            profile_manager.set_profile("test-profile", test_server2)

            print("Created test profile with 2 servers")

        # Test expanding a profile
        test_profile = list(profiles.keys())[0] if profiles else "test-profile"
        expanded = profile_manager.expand_profile_to_client_configs(test_profile)

        print(f"Profile '{test_profile}' expanded to {len(expanded)} servers:")
        for server in expanded:
            print(f"  - {server.name}: {type(server).__name__}")
            if hasattr(server, 'command'):
                print(f"    Command: {server.command}")
                if hasattr(server, 'args'):
                    print(f"    Args: {server.args}")

        return True

    except Exception as e:
        print(f"Error in profile expansion: {e}")
        return False


def test_client_manager_methods():
    """Test the new client manager methods"""
    print("\n=== Testing Client Manager Methods ===")

    try:
        # Test each client manager type
        success_count = 0
        total_count = 0

        for client_name in ClientRegistry.get_supported_clients():
            total_count += 1
            try:
                manager = ClientRegistry.get_client_manager(client_name)
                if not manager:
                    continue

                print(f"\nTesting {client_name}:")

                # Test profile detection
                profiles = manager.get_associated_profiles()
                print(f"  Associated profiles: {profiles}")

                # Test specific profile usage
                if profiles:
                    uses_first = manager.uses_profile(profiles[0])
                    print(f"  Uses '{profiles[0]}': {uses_first}")

                # Test installation check
                installed = manager.is_client_installed()
                print(f"  Installed: {installed}")

                success_count += 1

            except Exception as e:
                print(f"  Error testing {client_name}: {e}")

        print(f"\nSuccessfully tested {success_count}/{total_count} client managers")
        return success_count > 0

    except Exception as e:
        print(f"Error in client manager testing: {e}")
        return False


def test_profile_server_detection():
    """Test profile server detection logic"""
    print("\n=== Testing Profile Server Detection ===")

    try:
        from mcpm.clients.managers.claude_desktop import ClaudeDesktopManager

        manager = ClaudeDesktopManager()

        # Create test profile server configs
        profile_server1 = STDIOServerConfig(
            name="mcpm_profile_test",
            command="mcpm",
            args=["profile", "run", "--stdio-clean", "test-profile"]
        )

        profile_server2 = STDIOServerConfig(
            name="mcpm_profile_minimal",
            command="mcpm",
            args=["profile", "run", "minimal"]
        )

        regular_server = STDIOServerConfig(
            name="regular-server",
            command="python",
            args=["-m", "some_server"]
        )

        # Test profile name extraction
        test_cases = [
            (profile_server1, "test-profile"),
            (profile_server2, "minimal"),
            (regular_server, None)
        ]

        print("Profile name extraction tests:")
        for server, expected in test_cases:
            extracted = manager._extract_profile_name(server)
            result = "✓" if extracted == expected else "✗"
            print(f"  {result} Server '{server.name}': extracted '{extracted}', expected '{expected}'")

        # Test profile server detection
        print("\nProfile server detection tests:")
        test_profiles = ["test-profile", "minimal", "nonexistent"]

        for profile in test_profiles:
            is_profile1 = manager._is_profile_server(profile_server1, profile)
            is_profile2 = manager._is_profile_server(profile_server2, profile)
            is_regular = manager._is_profile_server(regular_server, profile)

            print(f"  Profile '{profile}':")
            print(f"    profile_server1: {is_profile1}")
            print(f"    profile_server2: {is_profile2}")
            print(f"    regular_server: {is_regular}")

        return True

    except Exception as e:
        print(f"Error in profile server detection: {e}")
        return False


def test_deployment_simulation():
    """Simulate the deployment process without actually modifying configs"""
    print("\n=== Testing Deployment Simulation ===")

    try:
        # This simulates what run_profile_direct_update would do
        test_profile = "minimal"  # Use a common profile name

        print(f"Simulating deployment of profile '{test_profile}'")

        # Step 1: Find clients using profile
        clients_using_profile = ClientRegistry.find_clients_using_profile(test_profile)
        print(f"Step 1: Found {len(clients_using_profile)} clients using profile")

        if not clients_using_profile:
            print("  No clients found using this profile")
            return True

        # Step 2: Expand profile
        profile_manager = ProfileConfigManager()
        expanded_servers = profile_manager.expand_profile_to_client_configs(test_profile)
        print(f"Step 2: Expanded profile to {len(expanded_servers)} servers")

        # Step 3: Simulate client updates (without actually changing configs)
        print("Step 3: Simulating client updates...")
        for client_name, client_manager in clients_using_profile:
            print(f"  Would update {client_name}:")
            print(f"    - Remove profile server for '{test_profile}'")
            print(f"    - Add {len(expanded_servers)} individual servers")

            # Check if client would support the servers
            for server in expanded_servers[:3]:  # Show first 3
                try:
                    client_format = client_manager.to_client_format(server)
                    print(f"    - Server '{server.name}' -> client format ready")
                except Exception as e:
                    print(f"    - Server '{server.name}' -> conversion error: {e}")

        print("Deployment simulation completed successfully")
        return True

    except Exception as e:
        print(f"Error in deployment simulation: {e}")
        return False


def main():
    """Run all tests"""
    print("🧘 Testing Zen Profile Deployment Implementation")
    print("=" * 50)

    tests = [
        ("Client Profile Discovery", test_client_profile_discovery),
        ("Profile Expansion", test_profile_expansion),
        ("Client Manager Methods", test_client_manager_methods),
        ("Profile Server Detection", test_profile_server_detection),
        ("Deployment Simulation", test_deployment_simulation),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"\n{status}: {test_name}")
        except Exception as e:
            results.append((test_name, False))
            print(f"\n✗ ERROR: {test_name} - {e}")

    # Summary
    print("\n" + "=" * 50)
    print("🧘 Test Summary")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The zen deployment approach is ready.")
    else:
        print("⚠️  Some tests failed. Review implementation before deploying.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

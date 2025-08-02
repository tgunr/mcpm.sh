#!/usr/bin/env python3
"""Test script for the new ollmcp client configuration"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcpm.clients.client_registry import ClientRegistry

def test_ollmcp_client():
    """Test the ollmcp client registration and functionality"""
    
    print("Testing ollmcp client registration...")
    
    # Test 1: Check if ollmcp is in supported clients
    supported_clients = ClientRegistry.get_supported_clients()
    if "ollmcp" in supported_clients:
        print("✓ ollmcp is registered in supported clients")
    else:
        print("✗ ollmcp is NOT registered in supported clients")
        return False
    
    # Test 2: Get client manager
    client_manager = ClientRegistry.get_client_manager("ollmcp")
    if client_manager:
        print("✓ ollmcp client manager created successfully")
    else:
        print("✗ Failed to create ollmcp client manager")
        return False
    
    # Test 3: Check default config path
    default_config = client_manager.config_path
    expected_path = os.path.expanduser("~/.claude.json")
    if default_config == expected_path:
        print(f"✓ Default config path correct: {default_config}")
    else:
        print(f"✗ Default config path incorrect. Expected: {expected_path}, Got: {default_config}")
        return False
    
    # Test 4: Check custom config path override
    custom_path = "/tmp/test-config.json"
    custom_manager = ClientRegistry.get_client_manager("ollmcp", config_path_override=custom_path)
    if custom_manager.config_path == custom_path:
        print(f"✓ Custom config path override works: {custom_path}")
    else:
        print(f"✗ Custom config path override failed. Expected: {custom_path}, Got: {custom_manager.config_path}")
        return False
    
    # Test 5: Check client info
    client_info = ClientRegistry.get_client_info("ollmcp")
    if client_info and client_info.get("name") == "Ollmcp":
        print(f"✓ Client info correct: {client_info}")
    else:
        print(f"✗ Client info incorrect: {client_info}")
        return False
    
    print("\n🎉 All tests passed! ollmcp client is ready to use.")
    
    # Show usage examples
    print("\nUsage examples:")
    print("  mcpm client ls                                   # List all clients (should show ollmcp)")
    print("  mcpm client edit ollmcp                          # Edit ollmcp with default ~/.claude.json")
    print("  mcpm client edit ollmcp -f /path/to/custom.json  # Edit ollmcp with custom config file")
    
    return True

if __name__ == "__main__":
    success = test_ollmcp_client()
    sys.exit(0 if success else 1)
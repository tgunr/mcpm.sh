#!/usr/bin/env python3
"""
Simple test script for Zed client implementation
"""

import sys
import os
import tempfile
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_zed_manager():
    """Test the ZedManager implementation."""
    try:
        # Import required modules
        from mcpm.clients.managers.zed import ZedManager
        from mcpm.core.schema import STDIOServerConfig
        
        print("✅ ZedManager imports successfully")
        
        # Create a temporary config file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_config = {
                "servers": {
                    "test-server": {
                        "command": "python",
                        "args": ["-m", "test_server"],
                        "env": {"TEST_VAR": "test_value"}
                    }
                }
            }
            json.dump(test_config, f, indent=2)
            temp_config_path = f.name
        
        try:
            # Test ZedManager with temporary config
            manager = ZedManager(config_path_override=temp_config_path)
            print(f"✅ ZedManager created with config: {temp_config_path}")
            
            # Test basic functionality
            servers = manager.get_servers()
            print(f"✅ Retrieved servers: {list(servers.keys())}")
            
            # Test getting a specific server
            test_server = manager.get_server("test-server")
            if test_server:
                print(f"✅ Retrieved test-server: {test_server.name}")
                print(f"   Command: {test_server.command}")
                print(f"   Args: {test_server.args}")
            
            # Test client info
            client_info = manager.get_client_info()
            print(f"✅ Client info: {client_info}")
            
            # Test adding a new server
            new_server = STDIOServerConfig(
                name="new-test-server",
                command="mcpm",
                args=["run", "test-server"]
            )
            
            success = manager.add_server(new_server)
            if success:
                print("✅ Successfully added new server")
                
                # Verify it was added
                updated_servers = manager.get_servers()
                if "new-test-server" in updated_servers:
                    print("✅ New server appears in server list")
                else:
                    print("❌ New server not found in updated list")
            else:
                print("❌ Failed to add new server")
            
            print("\n🎉 All Zed manager tests passed!")
            return True
            
        finally:
            # Clean up temp file
            os.unlink(temp_config_path)
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_client_registry():
    """Test that Zed is registered in the client registry."""
    try:
        from mcpm.clients.client_registry import ClientRegistry
        
        print("\n--- Testing Client Registry ---")
        
        # Test that Zed is in supported clients
        supported = ClientRegistry.get_supported_clients()
        if "zed" in supported:
            print("✅ Zed is in supported clients list")
        else:
            print("❌ Zed not found in supported clients")
            print(f"   Supported clients: {supported}")
            return False
        
        # Test getting Zed manager from registry
        zed_manager = ClientRegistry.get_client_manager("zed")
        if zed_manager:
            print("✅ Can retrieve Zed manager from registry")
            print(f"   Manager type: {type(zed_manager).__name__}")
        else:
            print("❌ Failed to get Zed manager from registry")
            return False
        
        # Test client info
        zed_info = ClientRegistry.get_client_info("zed")
        if zed_info:
            print(f"✅ Zed client info: {zed_info}")
        else:
            print("❌ Failed to get Zed client info")
            return False
        
        print("🎉 Client registry tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Registry test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Zed Client Implementation")
    print("=" * 50)
    
    success1 = test_zed_manager()
    success2 = test_client_registry()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Zed client implementation is working.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)
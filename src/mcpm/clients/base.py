"""
Base client manager module that defines the interface for all client managers.
"""

import abc
import json
import logging
import os
import platform
import re
from typing import Any, Dict, List, Optional, Union

from pydantic import TypeAdapter
from ruamel.yaml import YAML

from mcpm.core.schema import ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


class BaseClientManager(abc.ABC):
    """
    Abstract base class that defines the interface for all client managers.

    This class establishes the contract that all client managers must fulfill,
    but does not provide implementations.
    """

    # Client information properties
    client_key = ""  # Client identifier (e.g., "claude-desktop")
    display_name = ""  # Human-readable name (e.g., "Claude Desktop")
    download_url = ""  # URL to download the client
    config_path: str

    def __init__(self, config_path_override: Optional[str] = None):
        """Initialize the client manager"""
        self._system = platform.system()
        if config_path_override:
            self.config_path = config_path_override

    @abc.abstractmethod
    def get_servers(self) -> Dict[str, Any]:
        """Get all MCP servers configured for this client

        Returns:
            Dict of server configurations by name
        """
        pass

    @abc.abstractmethod
    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a server configuration

        Args:
            server_name: Name of the server

        Returns:
            ServerConfig object if found, None otherwise
        """
        pass

    @abc.abstractmethod
    def add_server(self, server_config: ServerConfig) -> bool:
        """Add or update a server in the client config

        Args:
            server_config: ServerConfig object

        Returns:
            bool: Success or failure
        """
        pass

    @abc.abstractmethod
    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to client-specific format

        Args:
            server_config: ServerConfig object

        Returns:
            Dict containing client-specific configuration
        """
        pass

    @abc.abstractmethod
    def from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert client format to ServerConfig

        Args:
            server_name: Name of the server
            client_config: Client-specific configuration

        Returns:
            ServerConfig object
        """
        pass

    @abc.abstractmethod
    def list_servers(self) -> List[str]:
        """List all MCP servers in client config

        Returns:
            List of server names
        """
        pass

    @abc.abstractmethod
    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from client config

        Args:
            server_name: Name of the server to remove

        Returns:
            bool: Success or failure
        """
        pass

    @abc.abstractmethod
    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        pass

    @abc.abstractmethod
    def is_client_installed(self) -> bool:
        """Check if this client is installed

        Returns:
            bool: True if client is installed, False otherwise
        """
        pass

    def get_associated_profiles(self) -> List[str]:
        """
        Get the associated profile for this client

        Returns:
            List[str]: List of associated profile names
        """
        profiles = []
        for server_name, server_config in self.get_servers().items():
            profile_name = self._extract_profile_name(server_config)
            if profile_name and profile_name not in profiles:
                profiles.append(profile_name)
        return profiles

    def uses_profile(self, profile_name: str) -> bool:
        """Check if this client uses the specified profile

        Args:
            profile_name: Name of the profile to check for

        Returns:
            bool: True if client uses the profile, False otherwise
        """
        servers = self.get_servers()
        for server_name, server_config in servers.items():
            if self._is_profile_server(server_config, profile_name):
                return True
        return False

    def _is_profile_server(self, server_config, profile_name: str) -> bool:
        """Check if a server config represents a profile command

        Args:
            server_config: Server configuration to check (dict or ServerConfig object)
            profile_name: Profile name to match against

        Returns:
            bool: True if server config is for the specified profile
        """
        extracted_name = self._extract_profile_name(server_config)
        return extracted_name == profile_name

    def _extract_profile_name(self, server_config) -> Optional[str]:
        """Extract profile name from a server config if it's a profile server

        Args:
            server_config: Server configuration to analyze (dict or ServerConfig object)

        Returns:
            Optional[str]: Profile name if found, None otherwise
        """
        # Handle both dict and ServerConfig object formats
        if isinstance(server_config, dict):
            command = server_config.get('command')
            args = server_config.get('args', [])
            url = server_config.get('url')
        else:
            command = getattr(server_config, 'command', None)
            args = getattr(server_config, 'args', [])
            url = getattr(server_config, 'url', None)

        # Check for STDIO profile servers (mcpm profile run --stdio-clean profile_name)
        if command == 'mcpm' and args:
            try:
                # Look for pattern: ["profile", "run", "--stdio-clean", profile_name]
                # or ["profile", "run", profile_name]
                if 'profile' in args and 'run' in args:
                    profile_idx = args.index('profile')
                    run_idx = args.index('run')

                    # Profile name should be after 'run', potentially after '--stdio-clean'
                    if run_idx > profile_idx:
                        # Look for profile name after 'run'
                        for i in range(run_idx + 1, len(args)):
                            arg = args[i]
                            # Skip flags like --stdio-clean
                            if not arg.startswith('--'):
                                return arg
            except (ValueError, IndexError):
                pass

        # Check for HTTP/SSE profile servers (URL contains profile parameter)
        if url and "profile=" in url:
            matched = re.search(r"profile=([^&]+)", url)
            if matched:
                return matched.group(1)

        return None

    def replace_profile_with_servers(self, profile_name: str, servers: List[ServerConfig]) -> bool:
        """Replace profile command with individual servers

        Args:
            profile_name: Name of the profile to replace
            servers: List of individual servers to add

        Returns:
            bool: True if replacement was successful
        """
        try:
            # Find and remove profile server(s)
            profile_servers_to_remove = []
            for server_name, server_config in self.get_servers().items():
                if self._is_profile_server(server_config, profile_name):
                    profile_servers_to_remove.append(server_name)

            # Remove profile servers
            for server_name in profile_servers_to_remove:
                if not self.remove_server(server_name):
                    logger.warning(f"Failed to remove profile server {server_name}")

            # Add individual servers with deduplication
            success_count = 0
            added_servers = set()  # Track already-added server names
            existing_servers = set(self.get_servers().keys())  # Get current server names
            
            for server in servers:
                # Skip if server already exists or was already added in this operation
                if server.name in existing_servers or server.name in added_servers:
                    logger.info(f"Skipping duplicate server '{server.name}' during profile expansion")
                    continue
                    
                if self.add_server(server):
                    success_count += 1
                    added_servers.add(server.name)
                else:
                    logger.warning(f"Failed to add server {server.name}")

            skipped_count = len(servers) - len([s for s in servers if s.name not in existing_servers and s.name not in added_servers]) - success_count
            if skipped_count > 0:
                logger.info(f"Skipped {skipped_count} duplicate server(s) during profile '{profile_name}' expansion")
            logger.info(f"Replaced profile '{profile_name}' with {success_count}/{len(servers)} servers")
            return success_count > 0

        except Exception as e:
            logger.error(f"Error replacing profile {profile_name} with servers: {e}")
            return False


class JSONClientManager(BaseClientManager):
    """
    JSON-based implementation of the client manager interface.

    This class implements the BaseClientManager interface using JSON files
    for configuration storage.
    """

    configure_key_name: str = "mcpServers"

    def __init__(self, config_path_override: Optional[str] = None):
        """Initialize the JSON client manager"""
        super().__init__(config_path_override=config_path_override)
        self._config = None

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file

        Returns:
            Dict containing the client configuration with at least {"mcpServers": {}}
        """
        # Create empty config with the correct structure
        empty_config = {self.configure_key_name: {}}

        if not os.path.exists(self.config_path):
            logger.debug(f"Client config file not found at: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Ensure mcpServers section exists
                if self.configure_key_name not in config:
                    config[self.configure_key_name] = {}
                return config
        except json.JSONDecodeError:
            logger.error(f"Error parsing client config file: {self.config_path}")

            # Backup the corrupt file
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.bak"
                try:
                    os.rename(self.config_path, backup_path)
                    logger.info(f"Backed up corrupt config file to: {backup_path}")
                except Exception as e:
                    logger.error(f"Failed to backup corrupt file: {str(e)}")

            # Return empty config
            return empty_config

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to client config file

        Args:
            config: Configuration to save

        Returns:
            bool: Success or failure
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving client config: {str(e)}")
            return False

    def get_servers(self) -> Dict[str, Any]:
        """Get all MCP servers configured for this client

        Returns:
            Dict of server configurations by name
        """
        config = self._load_config()
        return config.get(self.configure_key_name, {})

    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a server configuration

        Args:
            server_name: Name of the server

        Returns:
            ServerConfig object if found, None otherwise
        """
        servers = self.get_servers()

        # Check if the server exists
        if server_name not in servers:
            logger.debug(f"Server {server_name} not found in {self.display_name} config")
            return None

        # Get the server config and convert to ServerConfig
        client_config = servers[server_name]
        return self.from_client_format(server_name, client_config)

    def add_server(self, server_config: ServerConfig) -> bool:
        """Add or update a server in the client config

        Can accept either a ServerConfig object or a raw dictionary in client format.
        When using a dictionary, a name must be provided.

        Args:
            server_config: ServerConfig object or dictionary in client format

        Returns:
            bool: Success or failure
        """
        # Handle ServerConfig objects
        server_name = server_config.name
        client_config = self.to_client_format(server_config)

        # Update config directly
        config = self._load_config()
        config[self.configure_key_name][server_name] = client_config

        return self._save_config(config)

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to client-specific format with common core fields

        This implementation provides the common core fields (command, args, env)
        that are used by all client managers. Subclasses can override this method
        if they need to add additional client-specific fields.

        Args:
            server_config: ServerConfig object

        Returns:
            Dict containing client-specific configuration with core fields
        """
        # Base result containing only essential execution information
        if isinstance(server_config, STDIOServerConfig):
            result = {
                "command": server_config.command,
                "args": server_config.args,
            }

            # Add filtered environment variables if present
            non_empty_env = server_config.get_filtered_env_vars(os.environ)
            if non_empty_env:
                result["env"] = non_empty_env
        else:
            result = server_config.to_dict()

        return result

    @classmethod
    def from_client_format(cls, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert client format to ServerConfig

        This is a helper method used by subclasses to convert from client-specific format to ServerConfig.

        Args:
            server_name: Name of the server
            client_config: Client-specific configuration

        Returns:
            ServerConfig object
        """
        server_data = {
            "name": server_name,
        }
        
        # Make a copy to avoid modifying the original
        config_copy = client_config.copy()
        
        # Handle command arrays: convert to string + args format for STDIOServerConfig
        if "command" in config_copy and isinstance(config_copy["command"], list):
            command_list = config_copy["command"]
            if command_list:
                # First element becomes the command string
                config_copy["command"] = command_list[0]
                # Rest get prepended to existing args
                existing_args = config_copy.get("args", [])
                config_copy["args"] = command_list[1:] + existing_args
        
        server_data.update(config_copy)
        return TypeAdapter(ServerConfig).validate_python(server_data)

    def list_servers(self) -> List[str]:
        """List all MCP servers in client config

        Returns:
            List of server names
        """
        return list(self.get_servers().keys())

    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from client config

        Args:
            server_name: Name of the server to remove

        Returns:
            bool: Success or failure
        """
        servers = self.get_servers()

        # Check if the server exists
        if server_name not in servers:
            logger.warning(f"Server {server_name} not found in {self.display_name} config")
            return False

        # Load full config and remove the server
        config = self._load_config()
        del config[self.configure_key_name][server_name]

        return self._save_config(config)

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {"name": self.display_name, "download_url": self.download_url, "config_file": self.config_path}

    def is_client_installed(self) -> bool:
        """Check if this client is installed

        Returns:
            bool: True if client is installed, False otherwise
        """
        # Default implementation checks if the config directory exists
        # Can be overridden by subclasses
        return os.path.isdir(os.path.dirname(self.config_path))


class YAMLClientManager(BaseClientManager):
    """
    YAML-based implementation of the client manager interface.

    This class implements the BaseClientManager interface using YAML files
    for configuration storage. It provides common functionality for different
    YAML-based client managers with varying configuration formats.
    """

    def __init__(self, config_path_override: Optional[str] = None):
        """Initialize the YAML client manager"""
        super().__init__(config_path_override=config_path_override)
        self.yaml_handler: YAML = YAML()

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file

        Returns:
            Dict containing the client configuration
        """
        # Create empty config with the correct structure
        empty_config = self._get_empty_config()

        if not os.path.exists(self.config_path):
            logger.debug(f"Client config file not found at: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r") as f:
                config = self.yaml_handler.load(f)
                return config if config else empty_config
        except Exception as e:
            logger.error(f"Error parsing client config file: {self.config_path} - {str(e)}")
            # Return empty config
            return empty_config

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to client config file

        Args:
            config: Configuration to save

        Returns:
            bool: Success or failure
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w") as f:
                self.yaml_handler.dump(config, f)
            return True
        except Exception as e:
            logger.error(f"Error saving client config: {str(e)}")
            return False

    @abc.abstractmethod
    def _get_empty_config(self) -> Dict[str, Any]:
        """Get an empty configuration structure for this client

        Returns:
            Dict containing the empty configuration structure
        """
        pass

    @abc.abstractmethod
    def _get_server_config(self, config: Dict[str, Any], server_name: str) -> Optional[Dict[str, Any]]:
        """Get a server configuration from the config by name

        Args:
            config: The loaded configuration
            server_name: Name of the server to find

        Returns:
            Server configuration if found, None otherwise
        """
        pass

    @abc.abstractmethod
    def _get_all_server_names(self, config: Dict[str, Any]) -> List[str]:
        """Get all server names from the configuration

        Args:
            config: The loaded configuration

        Returns:
            List of server names
        """
        pass

    @abc.abstractmethod
    def _add_server_to_config(
        self, config: Dict[str, Any], server_name: str, server_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add or update a server in the config

        Args:
            config: The loaded configuration
            server_name: Name of the server to add or update
            server_config: Server configuration to add or update

        Returns:
            Updated configuration
        """
        pass

    @abc.abstractmethod
    def _remove_server_from_config(self, config: Dict[str, Any], server_name: str) -> Dict[str, Any]:
        """Remove a server from the config

        Args:
            config: The loaded configuration
            server_name: Name of the server to remove

        Returns:
            Updated configuration
        """
        pass

    def get_servers(self) -> Dict[str, Any]:
        """Get all MCP servers configured for this client

        Returns:
            Dict of server configurations by name
        """
        config = self._load_config()
        result = {}

        for server_name in self._get_all_server_names(config):
            server_config = self._get_server_config(config, server_name)
            if server_config:
                # Normalize configuration for external use
                result[server_name] = self._normalize_server_config(server_config)

        return result

    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a server configuration

        Args:
            server_name: Name of the server

        Returns:
            ServerConfig object if found, None otherwise
        """
        config = self._load_config()
        server_config = self._get_server_config(config, server_name)

        if not server_config:
            logger.debug(f"Server {server_name} not found in {self.display_name} config")
            return None

        return self.from_client_format(server_name, self._normalize_server_config(server_config))

    def add_server(self, server_config: Union[ServerConfig, Dict[str, Any]], name: Optional[str] = None) -> bool:
        """Add or update a server in the client config

        Args:
            server_config: ServerConfig object or dictionary in client format
            name: Required server name when using dictionary format

        Returns:
            bool: Success or failure
        """
        # Handle direct dictionary input
        if isinstance(server_config, dict):
            if name is None:
                raise ValueError("Name must be provided when using dictionary format")
            server_name = name
            client_config = server_config  # Already in client format
        # Handle ServerConfig objects
        else:
            server_name = server_config.name
            client_config = self.to_client_format(server_config)

        config = self._load_config()
        config = self._add_server_to_config(config, server_name, client_config)

        return self._save_config(config)

    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from client config

        Args:
            server_name: Name of the server to remove

        Returns:
            bool: Success or failure
        """
        config = self._load_config()
        server_config = self._get_server_config(config, server_name)

        if not server_config:
            logger.warning(f"Server {server_name} not found in {self.display_name} config")
            return False

        config = self._remove_server_from_config(config, server_name)
        return self._save_config(config)

    def list_servers(self) -> List[str]:
        """List all MCP servers in client config

        Returns:
            List of server names
        """
        config = self._load_config()
        return self._get_all_server_names(config)

    def _normalize_server_config(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize server configuration for external use

        This method can be overridden by subclasses to transform client-specific
        configuration formats to a standard format expected by external components.

        Args:
            server_config: Client-specific server configuration

        Returns:
            Normalized server configuration
        """
        return server_config

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {"name": self.display_name, "download_url": self.download_url, "config_file": self.config_path}

    def is_client_installed(self) -> bool:
        """Check if this client is installed

        Returns:
            bool: True if client is installed, False otherwise
        """
        # Check if the config directory exists
        return os.path.isdir(os.path.dirname(self.config_path))

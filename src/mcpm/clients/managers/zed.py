import json
import logging
import os
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class ZedManager(JSONClientManager):
    """Manages Zed MCP server configurations"""

    # Client information
    client_key = "zed"
    display_name = "Zed"
    download_url = "https://zed.dev/"
    configure_key_name = "servers"

    def __init__(self, config_path_override: str | None = None):
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Set config path based on detected platform
            if self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "Zed", "mcp.json")
            elif self._system == "Darwin":
                self.config_path = os.path.expanduser("~/Library/Application Support/Zed/mcp.json")
            else:
                # Linux
                self.config_path = os.path.expanduser("~/.config/zed/mcp.json")

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file

        Zed uses a dedicated mcp.json file with this structure:
        {
            "servers": {
                "server_name": {
                    "command": "path/to/server",
                    "args": ["arg1", "arg2"],
                    "env": {...}
                }
            }
        }

        Returns:
            Dict containing the client configuration with at least {"servers": {}}
        """
        # Create empty config with the correct structure
        empty_config = {self.configure_key_name: {}}

        if not os.path.exists(self.config_path):
            logger.debug(f"Zed config file not found at: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Ensure servers section exists
                if self.configure_key_name not in config:
                    config[self.configure_key_name] = {}
                return config
        except json.JSONDecodeError:
            logger.error(f"Error parsing Zed config file: {self.config_path}")

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

    def to_client_format(self, server_config) -> dict:
        """Convert ServerConfig to Zed-specific format

        Zed expects command, args, and optionally env fields.
        """
        from mcpm.core.schema import STDIOServerConfig

        if isinstance(server_config, STDIOServerConfig):
            result = {
                "command": server_config.command,
                "args": server_config.args,
            }

            # Add environment variables if present
            non_empty_env = server_config.get_filtered_env_vars(os.environ)
            if non_empty_env:
                result["env"] = non_empty_env

            return result
        else:
            # For other server types, use the default implementation
            return super().to_client_format(server_config)
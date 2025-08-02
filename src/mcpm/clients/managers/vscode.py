import json
import logging
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class VSCodeManager(JSONClientManager):
    """Manages VSCode MCP server configurations"""

    # Client information
    client_key = "vscode"
    display_name = "VSCode"
    download_url = "https://code.visualstudio.com/"
    configure_key_name = "servers"

    def __init__(self, config_path_override: str | None = None):
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Set config path based on detected platform
            if self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "Code", "User", "settings.json")
            elif self._system == "Darwin":
                self.config_path = os.path.expanduser("~/Library/Application Support/Code/User/settings.json")
            else:
                # MacOS or Linux
                self.config_path = os.path.expanduser("~/.config/Code/User/settings.json")

    def _sanitize_json5(self, content: str) -> str:
        """Sanitize JSON5-like content to valid JSON

        VS Code settings.json allows some JSON5 features like trailing commas,
        but Python's json module doesn't support them.

        Args:
            content: Raw JSON5-like content

        Returns:
            Sanitized JSON content
        """
        # Remove control characters that can break JSON parsing
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)

        # Remove trailing commas before closing brackets/braces
        # This handles cases like: { "key": "value", } or [ "item", ]
        content = re.sub(r',(\s*[}\]])', r'\1', content)

        # Remove single-line comments, but be careful not to remove // from URLs
        # Only remove // comments that start at beginning of line or after whitespace
        content = re.sub(r'(^|\s)//.*?$', r'\1', content, flags=re.MULTILINE)

        # Remove multi-line comments, but be more careful about context
        # Only remove /* */ that aren't part of strings (basic heuristic)
        lines = content.split('\n')
        cleaned_lines = []
        in_string = False
        escape_next = False

        for line in lines:
            cleaned_line = ""
            i = 0
            while i < len(line):
                char = line[i]

                if escape_next:
                    cleaned_line += char
                    escape_next = False
                elif char == '\\' and in_string:
                    cleaned_line += char
                    escape_next = True
                elif char == '"' and not escape_next:
                    cleaned_line += char
                    in_string = not in_string
                elif not in_string and i < len(line) - 1:
                    if line[i:i+2] == '/*':
                        # Skip until */
                        j = line.find('*/', i + 2)
                        if j != -1:
                            i = j + 1  # Skip the */
                        else:
                            break  # Rest of line is comment
                    else:
                        cleaned_line += char
                else:
                    cleaned_line += char
                i += 1

            cleaned_lines.append(cleaned_line)

        return '\n'.join(cleaned_lines)

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file

        {
            "mcp": {
                "servers": {
                    "server_name": {
                        ...
                    }
                }
            }
        }

        Returns:
            Dict containing the client configuration with at least {"mcpServers": {}}
        """
        # Create empty config with the correct structure
        empty_config = {"mcp": {self.configure_key_name: {}}}

        if not os.path.exists(self.config_path):
            logger.warning(f"Client config file not found at: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()

            # First try standard JSON parsing
            try:
                config = json.loads(content)
            except json.JSONDecodeError:
                # If that fails, try sanitizing JSON5-like syntax
                logger.debug(f"Standard JSON parsing failed, trying JSON5 sanitization for: {self.config_path}")
                sanitized_content = self._sanitize_json5(content)
                config = json.loads(sanitized_content)

            if "mcp" not in config:
                config["mcp"] = {}
            # Ensure mcpServers section exists
            if self.configure_key_name not in config["mcp"]:
                config["mcp"][self.configure_key_name] = {}
            return config["mcp"]
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing client config file: {self.config_path}")
            logger.debug(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error reading config file: {self.config_path}")
            logger.debug(f"Error: {e}")

        # Vscode config includes other information, so we makes no change on it
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
            if not os.path.exists(self.config_path):
                current_config = {}
            else:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    current_config = json.load(f)
            current_config["mcp"] = config
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(current_config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving client config: {str(e)}")
            # Only print traceback if not in stdio-clean mode
            if "--stdio-clean" not in sys.argv:
                traceback.print_exc()
            return False

    def to_client_format(self, server_config) -> dict:
        """Convert ServerConfig to VSCode-specific format

        VSCode expects a "type" field in addition to command and args.
        """
        from mcpm.core.schema import STDIOServerConfig

        if isinstance(server_config, STDIOServerConfig):
            result = {
                "type": "stdio",
                "command": server_config.command,
                "args": server_config.args,
            }

            # Add environment variables if present
            import os

            non_empty_env = server_config.get_filtered_env_vars(os.environ)
            if non_empty_env:
                result["env"] = non_empty_env

            return result
        else:
            # For other server types, use the default implementation
            return super().to_client_format(server_config)

"""
Client manager implementations for various MCP clients

This package contains specific implementations of client managers for MCP clients.
"""

from mcpm.clients.managers.claude_code import ClaudeCodeManager
from mcpm.clients.managers.claude_desktop import ClaudeDesktopManager
from mcpm.clients.managers.cline import ClineManager
from mcpm.clients.managers.codex_cli import CodexCliManager
from mcpm.clients.managers.continue_extension import ContinueManager
from mcpm.clients.managers.cursor import CursorManager
from mcpm.clients.managers.fiveire import FiveireManager
from mcpm.clients.managers.gemini_cli import GeminiCliManager
from mcpm.clients.managers.goose import GooseClientManager
from mcpm.clients.managers.ollmcp import OllmcpManager
from mcpm.clients.managers.trae import TraeManager
from mcpm.clients.managers.vscode import VSCodeManager
from mcpm.clients.managers.windsurf import WindsurfManager
from mcpm.clients.managers.zed import ZedManager

__all__ = [
    "ClaudeCodeManager",
    "ClaudeDesktopManager",
    "CursorManager",
    "WindsurfManager",
    "ClineManager",
    "ContinueManager",
    "FiveireManager",
    "GooseClientManager",
    "OllmcpManager",
    "TraeManager",
    "VSCodeManager",
    "GeminiCliManager",
    "CodexCliManager",
    "ZedManager",
]

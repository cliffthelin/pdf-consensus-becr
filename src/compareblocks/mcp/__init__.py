# src/compareblocks/mcp/__init__.py

"""
Model Context Protocol (MCP) integration module for BECR system.

This module provides MCP compatibility layer for external system integration,
standardized protocol endpoints for data exchange, real-time updates and 
notifications for processing status changes, and validation and processing 
of external extraction submissions.
"""

from .server import MCPServer
from .client import MCPClient
from .protocol import MCPProtocol
from .handlers import ExtractionHandler, StatusHandler
from .validation import MCPValidator

__all__ = [
    'MCPServer',
    'MCPClient', 
    'MCPProtocol',
    'ExtractionHandler',
    'StatusHandler',
    'MCPValidator'
]
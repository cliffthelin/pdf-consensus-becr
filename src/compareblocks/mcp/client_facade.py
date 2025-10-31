# src/compareblocks/mcp/client_facade.py

"""
MCP Client Facade - NEW FILE (simplified interface for MCP engine access)

Provides an easy-to-use interface for accessing engines through MCP protocol.
Does not modify existing code.
"""

import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from .client import MCPClient
from .protocol import MCPMethod


class MCPEngineFacade:
    """
    Simplified facade for MCP-based engine access.
    
    Provides synchronous and asynchronous methods for common operations.
    """
    
    def __init__(self, server_url: str = "ws://localhost:8765"):
        self.server_url = server_url
        self.client = MCPClient(server_url)
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to MCP server."""
        if not self._connected:
            self._connected = await self.client.connect()
        return self._connected
    
    async def disconnect(self):
        """Disconnect from MCP server."""
        if self._connected:
            await self.client.disconnect()
            self._connected = False
    
    async def extract_pdf(self, engine: str, pdf_path: str, 
                         options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract text from PDF using specified engine via MCP.
        
        Args:
            engine: Engine name (pymupdf, tesseract, paddleocr, docling, kreuzberg)
            pdf_path: Path to PDF file
            options: Optional engine-specific options
            
        Returns:
            Extraction results
        """
        if not self._connected:
            await self.connect()
        
        params = {
            "engine": engine,
            "pdf_path": pdf_path
        }
        
        if options:
            params["options"] = options
        
        response = await self.client.send_request(
            MCPMethod.CUSTOM,
            params,
            method_name="extract_pdf"
        )
        
        return response
    
    async def list_engines(self) -> List[Dict[str, Any]]:
        """
        List available engines.
        
        Returns:
            List of engine information
        """
        if not self._connected:
            await self.connect()
        
        response = await self.client.send_request(
            MCPMethod.CUSTOM,
            {},
            method_name="list_engines"
        )
        
        return response.get('engines', [])
    
    async def get_engine_info(self, engine: str) -> Dict[str, Any]:
        """
        Get detailed information about an engine.
        
        Args:
            engine: Engine name
            
        Returns:
            Engine details
        """
        if not self._connected:
            await self.connect()
        
        response = await self.client.send_request(
            MCPMethod.CUSTOM,
            {"engine": engine},
            method_name="engine_info"
        )
        
        return response
    
    async def batch_extract(self, engines: List[str], pdf_path: str,
                           options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract PDF using multiple engines.
        
        Args:
            engines: List of engine names
            pdf_path: Path to PDF file
            options: Optional engine-specific options
            
        Returns:
            Results from all engines
        """
        if not self._connected:
            await self.connect()
        
        params = {
            "engines": engines,
            "pdf_path": pdf_path
        }
        
        if options:
            params["options"] = options
        
        response = await self.client.send_request(
            MCPMethod.CUSTOM,
            params,
            method_name="batch_extract"
        )
        
        return response
    
    # Synchronous wrappers for convenience
    
    def extract_pdf_sync(self, engine: str, pdf_path: str,
                        options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronous version of extract_pdf."""
        return asyncio.run(self.extract_pdf(engine, pdf_path, options))
    
    def list_engines_sync(self) -> List[Dict[str, Any]]:
        """Synchronous version of list_engines."""
        return asyncio.run(self.list_engines())
    
    def get_engine_info_sync(self, engine: str) -> Dict[str, Any]:
        """Synchronous version of get_engine_info."""
        return asyncio.run(self.get_engine_info(engine))
    
    def batch_extract_sync(self, engines: List[str], pdf_path: str,
                          options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronous version of batch_extract."""
        return asyncio.run(self.batch_extract(engines, pdf_path, options))
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    def __enter__(self):
        """Sync context manager entry."""
        asyncio.run(self.connect())
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        asyncio.run(self.disconnect())

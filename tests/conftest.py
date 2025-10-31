#!/usr/bin/env python3
"""
Pytest configuration and fixtures for BECR test suite.
Includes embedded MCP server for automated testing.
"""

import sys
import asyncio
import pytest
import pytest_asyncio
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


# Embedded MCP Server Fixture for Automated Testing
@pytest_asyncio.fixture(scope="function")
async def mcp_test_server():
    """
    Function-scoped embedded MCP server for automated testing.
    Automatically starts/stops for each test.
    Enables 95%+ coverage without manual server management.
    Perfect for CI/CD integration.
    """
    from src.compareblocks.mcp.server import MCPServer
    
    # Use unique port for test server
    test_port = 8769
    server = MCPServer(host="localhost", port=test_port)
    
    # Start server
    await server.start()
    await asyncio.sleep(0.15)  # Give server time to start
    
    # Yield server info to tests
    server_info = {
        "server": server,
        "url": f"ws://localhost:{test_port}",
        "port": test_port
    }
    
    yield server_info
    
    # Cleanup: stop server
    await server.stop()
    await asyncio.sleep(0.1)  # Give server time to stop


@pytest.fixture
def pdf_path():
    """Fixture providing path to test PDF."""
    from src.compareblocks.config.file_manager import file_manager
    try:
        path = file_manager.get_target_pdf_path()
        if path and Path(path).exists():
            return path
    except Exception:
        pass
    return None


@pytest.fixture
def pdf_exists(pdf_path):
    """Fixture indicating if test PDF exists."""
    return pdf_path is not None and Path(pdf_path).exists()

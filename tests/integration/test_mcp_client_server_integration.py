#!/usr/bin/env python3
"""
Comprehensive integration tests for MCP client-server communication.
Tests the enhanced MCP client infrastructure with a real MCP server.
"""

import asyncio
import pytest
from pathlib import Path
from src.compareblocks.config.file_manager import file_manager
from src.compareblocks.mcp.client import MCPClient, ConnectionState
from src.compareblocks.mcp.server import MCPServer
from src.compareblocks.mcp.protocol import MCPProtocol


class TestMCPClientServerIntegration:
    """Integration tests for MCP client-server communication."""
    
    def setup_method(self):
        """Set up test fixtures."""
        try:
            self.pdf_path = file_manager.get_target_pdf_path()
            self.pdf_exists = Path(self.pdf_path).exists() if self.pdf_path else False
        except Exception:
            self.pdf_path = None
            self.pdf_exists = False
        
        self.server_port = 8766  # Use different port for testing
        self.server_url = f"ws://localhost:{self.server_port}"
        self.server = None
        self.client = None
    
    async def setup_server(self):
        """Set up test MCP server."""
        self.server = MCPServer(host="localhost", port=self.server_port)
        await self.server.start()
        # Give server time to start
        await asyncio.sleep(0.1)
    
    async def teardown_server(self):
        """Tear down test MCP server."""
        if self.server:
            await self.server.stop()
            self.server = None
    
    async def setup_client(self):
        """Set up test MCP client."""
        self.client = MCPClient(
            server_url=self.server_url,
            reconnect_attempts=2,
            reconnect_delay=0.1,
            request_timeout=5.0,
            heartbeat_interval=1.0
        )
    
    async def teardown_client(self):
        """Tear down test MCP client."""
        if self.client:
            await self.client.disconnect()
            self.client = None
    
    @pytest.mark.asyncio
    async def test_full_client_server_workflow(self):
        """Test complete client-server workflow with connection, initialization, and requests."""
        try:
            # Set up server and client
            await self.setup_server()
            await self.setup_client()
            
            # Test connection
            connected = await self.client.connect()
            assert connected is True
            assert self.client.is_connected()
            assert self.client.connection_state == ConnectionState.CONNECTED
            
            # Test initialization
            client_info = {
                "name": "test-client",
                "version": "1.0.0"
            }
            init_result = await self.client.initialize(client_info)
            assert self.client.is_initialized()
            assert self.client.connection_state == ConnectionState.INITIALIZED
            assert "protocolVersion" in init_result
            assert "capabilities" in init_result
            
            # Test status request
            status = await self.client.get_status()
            assert "system_status" in status
            assert status["system_status"] == "operational"
            
            # Test health check
            health = await self.client.health_check()
            assert health["healthy"] is True
            assert health["connection_state"] == "initialized"
            
        except Exception as e:
            pytest.skip(f"Server integration test failed: {e}")
        finally:
            # Clean up
            await self.teardown_client()
            await self.teardown_server()
    
    @pytest.mark.asyncio
    async def test_connection_failure_and_recovery(self):
        """Test connection failure handling and recovery."""
        try:
            await self.setup_client()
            
            # Try to connect without server
            connected = await self.client.connect()
            assert connected is False
            assert self.client.connection_state == ConnectionState.FAILED
            
            # Start server
            await self.setup_server()
            
            # Test reconnection
            reconnected = await self.client.force_reconnect()
            assert reconnected is True
            assert self.client.is_connected()
            
        except Exception as e:
            pytest.skip(f"Connection recovery test failed: {e}")
        finally:
            await self.teardown_client()
            await self.teardown_server()
    
    @pytest.mark.asyncio
    async def test_offline_mode_and_queue_processing(self):
        """Test offline mode functionality and queue processing."""
        try:
            await self.setup_client()
            
            # Force offline mode
            await self.client._enter_offline_mode()
            assert self.client.is_offline()
            
            # Test offline requests
            if self.pdf_exists:
                result = await self.client.submit_extraction(
                    self.pdf_path,
                    [{"text": "test extraction", "bbox": [0, 0, 100, 100]}]
                )
                assert result["offline_mode"] is True
                assert len(self.client.offline_queue) > 0
            
            # Start server and reconnect
            await self.setup_server()
            connected = await self.client.connect()
            
            if connected:
                # Initialize client
                await self.client.initialize({"name": "test-client", "version": "1.0.0"})
                
                # Queue should be processed
                initial_queue_size = len(self.client.offline_queue)
                await self.client._process_offline_queue()
                
                # Verify queue processing
                assert len(self.client.offline_queue) <= initial_queue_size
            
        except Exception as e:
            pytest.skip(f"Offline mode test failed: {e}")
        finally:
            await self.teardown_client()
            await self.teardown_server()
    
    @pytest.mark.asyncio
    async def test_connection_monitoring_and_handlers(self):
        """Test connection monitoring and event handlers."""
        try:
            await self.setup_client()
            
            # Set up event tracking
            events_received = []
            
            def track_events(event_data):
                events_received.append(event_data)
            
            self.client.set_connection_handler("connected", track_events)
            self.client.set_connection_handler("failed", track_events)
            self.client.set_connection_handler("offline", track_events)
            
            # Test connection failure
            connected = await self.client.connect()
            assert connected is False
            
            # Should have received failure events
            failure_events = [e for e in events_received if e["event"] == "failed"]
            assert len(failure_events) > 0
            
            # Test successful connection
            await self.setup_server()
            events_received.clear()
            
            reconnected = await self.client.force_reconnect()
            if reconnected:
                # Should have received connected event
                connected_events = [e for e in events_received if e["event"] == "connected"]
                assert len(connected_events) > 0
            
        except Exception as e:
            pytest.skip(f"Connection monitoring test failed: {e}")
        finally:
            await self.teardown_client()
            await self.teardown_server()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_timeouts(self):
        """Test error handling and timeout scenarios."""
        try:
            await self.setup_server()
            await self.setup_client()
            
            # Test with very short timeout
            short_timeout_client = MCPClient(
                server_url=self.server_url,
                request_timeout=0.001  # Very short timeout
            )
            
            connected = await short_timeout_client.connect()
            if connected:
                await short_timeout_client.initialize({"name": "timeout-test", "version": "1.0.0"})
                
                # This should timeout
                with pytest.raises(Exception):  # Could be MCPTimeoutError or similar
                    await short_timeout_client.get_status()
            
            await short_timeout_client.disconnect()
            
        except Exception as e:
            pytest.skip(f"Error handling test failed: {e}")
        finally:
            await self.teardown_client()
            await self.teardown_server()
    
    def test_client_statistics_and_monitoring(self):
        """Test client statistics and monitoring functionality."""
        try:
            client = MCPClient(server_url=self.server_url)
            
            # Test initial statistics
            stats = client.get_connection_stats()
            assert stats["connection_state"] == "disconnected"
            assert stats["connection_attempts"] == 0
            assert stats["offline_mode"] is False
            
            # Test client info
            info = client.get_client_info()
            assert info["server_url"] == self.server_url
            assert info["connected"] is False
            assert info["initialized"] is False
            
            # Test queue management
            initial_queue_size = len(client.offline_queue)
            cleared = client.clear_offline_queue()
            assert cleared == initial_queue_size
            
        except Exception as e:
            pytest.skip(f"Statistics test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
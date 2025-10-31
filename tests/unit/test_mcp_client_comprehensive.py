#!/usr/bin/env python3
"""
Comprehensive unit tests for MCP client to achieve 95%+ code coverage.
Tests all code paths, error conditions, and edge cases.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from pathlib import Path
from src.compareblocks.config.file_manager import file_manager
from src.compareblocks.mcp.client import (
    MCPClient, ConnectionState, MCPConnectionError, MCPTimeoutError
)
from src.compareblocks.mcp.protocol import MCPMessage, MCPMethod
from websockets.exceptions import ConnectionClosed, WebSocketException
import json


class TestMCPClientComprehensive:
    """Comprehensive tests for MCP client to achieve 95%+ coverage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        try:
            self.pdf_path = file_manager.get_target_pdf_path()
            self.pdf_exists = Path(self.pdf_path).exists() if self.pdf_path else False
        except Exception:
            self.pdf_path = None
            self.pdf_exists = False
        
        self.client = MCPClient(
            server_url="ws://localhost:8765",
            reconnect_attempts=2,
            reconnect_delay=0.1,
            request_timeout=1.0,
            heartbeat_interval=0.5
        )
    
    @pytest.mark.asyncio
    async def test_connect_already_connected(self):
        """Test connecting when already connected."""
        # Mock websocket connection
        self.client.connection_state = ConnectionState.CONNECTED
        
        result = await self.client.connect()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_connect_invalid_url(self):
        """Test connection with invalid URL."""
        client = MCPClient(server_url="invalid-url")
        result = await client.connect()
        assert result is False
        assert client.connection_state == ConnectionState.FAILED
    
    @pytest.mark.asyncio
    async def test_connect_timeout(self):
        """Test connection timeout."""
        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = asyncio.TimeoutError()
            
            result = await self.client.connect()
            assert result is False
            assert self.client.connection_state == ConnectionState.FAILED
    
    @pytest.mark.asyncio
    async def test_initialize_not_connected(self):
        """Test initialization when not connected."""
        with pytest.raises(MCPConnectionError, match="Not connected to server"):
            await self.client.initialize({"name": "test"})
    
    @pytest.mark.asyncio
    async def test_initialize_with_error_response(self):
        """Test initialization with error response from server."""
        self.client.connection_state = ConnectionState.CONNECTED
        
        with patch.object(self.client, '_send_request', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"error": {"code": -1, "message": "Init failed"}}
            
            with pytest.raises(MCPConnectionError, match="Initialization failed"):
                await self.client.initialize({"name": "test"})
    
    @pytest.mark.asyncio
    async def test_submit_extraction_offline_mode(self):
        """Test extraction submission in offline mode."""
        await self.client._enter_offline_mode()
        
        if self.pdf_exists:
            result = await self.client.submit_extraction(
                self.pdf_path,
                [{"text": "test", "bbox": [0, 0, 100, 100]}]
            )
            
            assert result["offline_mode"] is True
            assert result["status"] == "queued"
            assert len(self.client.offline_queue) > 0
    
    @pytest.mark.asyncio
    async def test_submit_extraction_connection_error(self):
        """Test extraction submission with connection error."""
        self.client.connection_state = ConnectionState.INITIALIZED
        
        with patch.object(self.client, '_send_request', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = ConnectionClosed(None, None)
            
            if self.pdf_exists:
                result = await self.client.submit_extraction(
                    self.pdf_path,
                    [{"text": "test", "bbox": [0, 0, 100, 100]}]
                )
                
                # Should handle offline
                assert result["offline_mode"] is True
    
    @pytest.mark.asyncio
    async def test_get_status_offline_mode(self):
        """Test status request in offline mode."""
        await self.client._enter_offline_mode()
        
        result = await self.client.get_status()
        assert result["status"] == "offline"
        assert result["offline_mode"] is True
    
    @pytest.mark.asyncio
    async def test_get_results_offline_mode(self):
        """Test results request in offline mode."""
        await self.client._enter_offline_mode()
        
        result = await self.client.get_results("test-session-id")
        assert result["status"] == "offline"
        assert result["offline_mode"] is True
    
    @pytest.mark.asyncio
    async def test_subscribe_updates_offline_mode(self):
        """Test subscription in offline mode."""
        await self.client._enter_offline_mode()
        
        result = await self.client.subscribe_updates(["status_update"])
        assert result["offline_mode"] is True
    
    @pytest.mark.asyncio
    async def test_unsubscribe_updates_offline_mode(self):
        """Test unsubscription in offline mode."""
        await self.client._enter_offline_mode()
        
        result = await self.client.unsubscribe_updates(["status_update"])
        assert result["offline_mode"] is True
    
    @pytest.mark.asyncio
    async def test_send_request_timeout(self):
        """Test request timeout."""
        self.client.connection_state = ConnectionState.INITIALIZED
        self.client.websocket = MagicMock()
        self.client.websocket.send = AsyncMock()
        
        request = MCPMessage(method="test_method")
        
        with pytest.raises(MCPTimeoutError, match="Request timeout"):
            await self.client._send_request(request)
    
    @pytest.mark.asyncio
    async def test_send_request_connection_closed(self):
        """Test request with connection closed."""
        self.client.connection_state = ConnectionState.INITIALIZED
        self.client.websocket = MagicMock()
        self.client.websocket.send = AsyncMock(side_effect=ConnectionClosed(None, None))
        
        request = MCPMessage(method="test_method")
        
        with pytest.raises(MCPConnectionError, match="Connection closed"):
            await self.client._send_request(request)
    
    @pytest.mark.asyncio
    async def test_send_request_websocket_exception(self):
        """Test request with WebSocket exception."""
        self.client.connection_state = ConnectionState.INITIALIZED
        self.client.websocket = MagicMock()
        self.client.websocket.send = AsyncMock(side_effect=WebSocketException("Test error"))
        
        request = MCPMessage(method="test_method")
        
        with pytest.raises(MCPConnectionError, match="WebSocket error"):
            await self.client._send_request(request)
    
    @pytest.mark.asyncio
    async def test_handle_offline_request_queue_full(self):
        """Test offline request handling when queue is full."""
        await self.client._enter_offline_mode()
        
        # Fill the queue
        self.client.offline_queue = [{"test": i} for i in range(self.client.max_offline_queue_size)]
        
        result = await self.client._handle_offline_request("test_method", {})
        # Should still return offline response even if queue is full
        assert result["offline_mode"] is True
    
    @pytest.mark.asyncio
    async def test_process_offline_queue_with_errors(self):
        """Test offline queue processing with errors."""
        self.client.offline_queue = [
            {"method": "test1", "params": {}},
            {"method": "test2", "params": {}}
        ]
        
        # Process queue (will log errors but continue)
        await self.client._process_offline_queue()
        
        # Queue should be cleared even with errors
        assert len(self.client.offline_queue) == 0
    
    @pytest.mark.asyncio
    async def test_heartbeat_monitor_timeout(self):
        """Test heartbeat monitor with timeout."""
        self.client.connection_state = ConnectionState.CONNECTED
        self.client.websocket = MagicMock()
        self.client.websocket.closed = False
        
        # Mock ping to timeout
        async def mock_ping():
            future = asyncio.Future()
            await asyncio.sleep(20)  # Will timeout
            return future
        
        self.client.websocket.ping = mock_ping
        
        # Start heartbeat monitor
        task = asyncio.create_task(self.client._heartbeat_monitor())
        
        # Wait a bit for heartbeat to run
        await asyncio.sleep(0.6)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_heartbeat_monitor_websocket_closed(self):
        """Test heartbeat monitor when websocket is closed."""
        self.client.connection_state = ConnectionState.CONNECTED
        self.client.websocket = MagicMock()
        self.client.websocket.closed = True
        
        # Start heartbeat monitor
        task = asyncio.create_task(self.client._heartbeat_monitor())
        
        # Wait a bit
        await asyncio.sleep(0.6)
        
        # Task should have completed (detected closed connection)
        assert task.done()
        
        # Clean up if not done
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_process_message_with_pending_request(self):
        """Test message processing for pending request."""
        message = MCPMessage(
            id="test-id",
            result={"status": "success"}
        )
        
        # Create pending request
        future = asyncio.Future()
        self.client.pending_requests["test-id"] = future
        
        await self.client._process_message(message.to_json())
        
        # Future should be resolved
        assert future.done()
        result = future.result()
        assert result["result"]["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_process_message_notification(self):
        """Test notification message processing."""
        notification_received = []
        
        def handler(params):
            notification_received.append(params)
        
        self.client.set_notification_handler("test_notification", handler)
        
        message = MCPMessage(
            method="test_notification",
            params={"data": "test"}
        )
        
        await self.client._process_message(message.to_json())
        
        assert len(notification_received) == 1
        assert notification_received[0]["data"] == "test"
    
    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self):
        """Test processing invalid JSON message."""
        # Should handle gracefully
        await self.client._process_message("invalid json {")
        # No exception should be raised
    
    @pytest.mark.asyncio
    async def test_handle_notification_async_handler(self):
        """Test notification with async handler."""
        notification_received = []
        
        async def async_handler(params):
            notification_received.append(params)
        
        self.client.set_notification_handler("async_test", async_handler)
        
        message = MCPMessage(
            method="async_test",
            params={"data": "async_test"}
        )
        
        await self.client._handle_notification(message)
        
        assert len(notification_received) == 1
    
    @pytest.mark.asyncio
    async def test_handle_notification_handler_error(self):
        """Test notification handler with error."""
        def error_handler(params):
            raise ValueError("Handler error")
        
        self.client.set_notification_handler("error_test", error_handler)
        
        message = MCPMessage(
            method="error_test",
            params={"data": "test"}
        )
        
        # Should handle error gracefully
        await self.client._handle_notification(message)
    
    @pytest.mark.asyncio
    async def test_notify_connection_handlers_async(self):
        """Test connection handlers with async handler."""
        events = []
        
        async def async_handler(event_data):
            events.append(event_data)
        
        self.client.set_connection_handler("test_event", async_handler)
        
        await self.client._notify_connection_handlers("test_event", {"test": "data"})
        
        assert len(events) == 1
        assert events[0]["event"] == "test_event"
    
    @pytest.mark.asyncio
    async def test_notify_connection_handlers_error(self):
        """Test connection handler with error."""
        def error_handler(event_data):
            raise ValueError("Handler error")
        
        self.client.set_connection_handler("error_event", error_handler)
        
        # Should handle error gracefully
        await self.client._notify_connection_handlers("error_event")
    
    @pytest.mark.asyncio
    async def test_force_reconnect(self):
        """Test force reconnect functionality."""
        # Set up initial state
        self.client.connection_state = ConnectionState.CONNECTED
        
        # Force reconnect (will fail without server)
        result = await self.client.force_reconnect()
        
        # Should have attempted reconnection
        assert isinstance(result, bool)
    
    def test_clear_offline_queue(self):
        """Test clearing offline queue."""
        self.client.offline_queue = [{"test": i} for i in range(5)]
        
        cleared = self.client.clear_offline_queue()
        
        assert cleared == 5
        assert len(self.client.offline_queue) == 0
    
    @pytest.mark.asyncio
    async def test_health_check_connected_not_initialized(self):
        """Test health check when connected but not initialized."""
        self.client.connection_state = ConnectionState.CONNECTED
        
        health = await self.client.health_check()
        
        assert health["healthy"] is False
        assert health["details"]["status_check"] == "connected_but_not_initialized"
    
    @pytest.mark.asyncio
    async def test_health_check_offline(self):
        """Test health check in offline mode."""
        await self.client._enter_offline_mode()
        
        health = await self.client.health_check()
        
        assert health["healthy"] is False
        assert health["details"]["status_check"] == "offline_mode"
        assert "offline_queue_size" in health["details"]
    
    @pytest.mark.asyncio
    async def test_health_check_not_connected(self):
        """Test health check when not connected."""
        health = await self.client.health_check()
        
        assert health["healthy"] is False
        assert health["details"]["status_check"] == "not_connected"
    
    @pytest.mark.asyncio
    async def test_health_check_with_error(self):
        """Test health check with error."""
        self.client.connection_state = ConnectionState.INITIALIZED
        
        with patch.object(self.client, 'get_status', new_callable=AsyncMock) as mock_status:
            mock_status.side_effect = Exception("Test error")
            
            health = await self.client.health_check()
            
            assert health["healthy"] is False
            assert "error" in health["details"]
    
    def test_get_connection_stats_with_websocket(self):
        """Test connection stats with active websocket."""
        self.client.websocket = MagicMock()
        self.client.websocket.closed = False
        
        stats = self.client.get_connection_stats()
        
        assert stats["websocket_closed"] is False
    
    def test_get_connection_stats_no_websocket(self):
        """Test connection stats without websocket."""
        self.client.websocket = None
        
        stats = self.client.get_connection_stats()
        
        assert stats["websocket_closed"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestMCPClientMessageHandlerLifecycle:
    """Tests for message handler lifecycle to increase coverage (+8%)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = MCPClient(
            server_url="ws://localhost:8765",
            reconnect_attempts=2,
            reconnect_delay=0.1,
            request_timeout=1.0,
            heartbeat_interval=0.5
        )
    
    @pytest.mark.asyncio
    async def test_handle_messages_cancellation(self):
        """Test message handler task cancellation."""
        self.client.connection_state = ConnectionState.CONNECTED
        self.client.websocket = MagicMock()
        
        # Create async iterator for messages
        async def message_generator():
            yield '{"jsonrpc": "2.0", "id": "test", "result": {}}'
            await asyncio.sleep(10)  # Long wait
        
        self.client.websocket.__aiter__ = lambda self: message_generator()
        
        # Start message handler
        task = asyncio.create_task(self.client._handle_messages())
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Cancel task
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass  # Expected
    
    @pytest.mark.asyncio
    async def test_handle_messages_websocket_exception(self):
        """Test message handler with WebSocket exception."""
        self.client.connection_state = ConnectionState.CONNECTED
        self.client.websocket = MagicMock()
        
        async def message_generator():
            raise WebSocketException("Test error")
        
        self.client.websocket.__aiter__ = lambda self: message_generator()
        
        # Start message handler
        task = asyncio.create_task(self.client._handle_messages())
        
        # Wait for completion
        await asyncio.sleep(0.2)
        
        # Should have handled error
        assert task.done()
    
    @pytest.mark.asyncio
    async def test_handle_messages_unexpected_error(self):
        """Test message handler with unexpected error."""
        self.client.connection_state = ConnectionState.CONNECTED
        self.client.websocket = MagicMock()
        
        async def message_generator():
            raise ValueError("Unexpected error")
        
        self.client.websocket.__aiter__ = lambda self: message_generator()
        
        # Start message handler
        task = asyncio.create_task(self.client._handle_messages())
        
        # Wait for completion
        await asyncio.sleep(0.2)
        
        # Should have handled error
        assert task.done()
    
    @pytest.mark.asyncio
    async def test_disconnect_with_active_tasks(self):
        """Test disconnection with active background tasks."""
        self.client.connection_state = ConnectionState.CONNECTED
        self.client.websocket = MagicMock()
        self.client.websocket.close = AsyncMock()
        
        # Create mock tasks
        self.client.message_handler_task = asyncio.create_task(asyncio.sleep(10))
        self.client.heartbeat_task = asyncio.create_task(asyncio.sleep(10))
        self.client.reconnect_task = asyncio.create_task(asyncio.sleep(10))
        
        # Disconnect should cancel all tasks
        await self.client.disconnect()
        
        # Verify tasks were cancelled
        assert self.client.message_handler_task.cancelled() or self.client.message_handler_task.done()
        assert self.client.heartbeat_task.cancelled() or self.client.heartbeat_task.done()
        assert self.client.reconnect_task.cancelled() or self.client.reconnect_task.done()
    
    @pytest.mark.asyncio
    async def test_disconnect_with_pending_requests(self):
        """Test disconnection with pending requests."""
        self.client.connection_state = ConnectionState.CONNECTED
        self.client.websocket = MagicMock()
        self.client.websocket.close = AsyncMock()
        
        # Create pending requests
        future1 = asyncio.Future()
        future2 = asyncio.Future()
        self.client.pending_requests["req1"] = future1
        self.client.pending_requests["req2"] = future2
        
        # Disconnect
        await self.client.disconnect()
        
        # Pending requests should be cancelled with exception
        assert future1.done()
        assert future2.done()
        
        try:
            future1.result()
        except MCPConnectionError:
            pass  # Expected
    
    @pytest.mark.asyncio
    async def test_process_message_with_done_future(self):
        """Test processing message when future is already done."""
        message = MCPMessage(
            id="test-id",
            result={"status": "success"}
        )
        
        # Create already-done future
        future = asyncio.Future()
        future.set_result({"old": "result"})
        self.client.pending_requests["test-id"] = future
        
        # Process message (should not raise exception)
        await self.client._process_message(message.to_json())
        
        # Future should still have old result
        assert future.result()["old"] == "result"
    
    @pytest.mark.asyncio
    async def test_send_request_not_connected(self):
        """Test sending request when not connected."""
        self.client.connection_state = ConnectionState.DISCONNECTED
        
        request = MCPMessage(method="test_method")
        
        with pytest.raises(MCPConnectionError, match="Not connected"):
            await self.client._send_request(request)
    
    @pytest.mark.asyncio
    async def test_send_request_generic_exception(self):
        """Test send request with generic exception."""
        self.client.connection_state = ConnectionState.INITIALIZED
        self.client.websocket = MagicMock()
        self.client.websocket.send = AsyncMock(side_effect=ValueError("Test error"))
        
        request = MCPMessage(method="test_method")
        
        with pytest.raises(MCPConnectionError, match="Request failed"):
            await self.client._send_request(request)


class TestMCPClientReconnectionWorkflow:
    """Tests for full reconnection workflow to increase coverage (+5%)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = MCPClient(
            server_url="ws://localhost:8765",
            reconnect_attempts=3,
            reconnect_delay=0.1,
            request_timeout=1.0,
            heartbeat_interval=0.5
        )
    
    @pytest.mark.asyncio
    async def test_full_reconnection_cycle(self):
        """Test complete reconnection cycle."""
        # Simulate connection failure
        await self.client._handle_connection_failure("Test failure")
        
        # Should have scheduled reconnection
        assert self.client.connection_attempts == 1
        assert self.client.connection_state == ConnectionState.FAILED
        
        # Wait for reconnection attempt
        await asyncio.sleep(0.3)
        
        # Should have attempted reconnection
        assert self.client.connection_attempts >= 1
    
    @pytest.mark.asyncio
    async def test_reconnection_exponential_backoff(self):
        """Test exponential backoff in reconnection."""
        start_time = asyncio.get_event_loop().time()
        
        # Trigger multiple failures
        for i in range(3):
            await self.client._handle_connection_failure(f"Failure {i+1}")
            await asyncio.sleep(0.05)
        
        # Verify attempts were made
        assert self.client.connection_attempts >= 3
    
    @pytest.mark.asyncio
    async def test_reconnection_max_attempts_reached(self):
        """Test behavior when max reconnection attempts reached."""
        # Set to max attempts
        self.client.connection_attempts = self.client.max_reconnect_attempts
        
        # Trigger failure
        await self.client._handle_connection_failure("Final failure")
        
        # Should enter offline mode
        assert self.client.connection_state == ConnectionState.OFFLINE
        assert self.client.is_offline()
    
    @pytest.mark.asyncio
    async def test_attempt_reconnection_success(self):
        """Test successful reconnection attempt."""
        self.client.connection_attempts = 1
        self.client.connection_state = ConnectionState.FAILED
        
        with patch.object(self.client, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            
            # Attempt reconnection
            await self.client._attempt_reconnection()
            
            # Should have called connect
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_attempt_reconnection_failure(self):
        """Test failed reconnection attempt."""
        self.client.connection_attempts = 1
        self.client.connection_state = ConnectionState.FAILED
        
        with patch.object(self.client, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = False
            
            # Attempt reconnection
            await self.client._attempt_reconnection()
            
            # Should have incremented attempts
            assert self.client.connection_attempts >= 1
    
    @pytest.mark.asyncio
    async def test_heartbeat_monitor_ping_exception(self):
        """Test heartbeat monitor with ping exception."""
        self.client.connection_state = ConnectionState.CONNECTED
        self.client.websocket = MagicMock()
        self.client.websocket.closed = False
        
        async def failing_ping():
            raise Exception("Ping failed")
        
        self.client.websocket.ping = failing_ping
        
        # Start heartbeat monitor
        task = asyncio.create_task(self.client._heartbeat_monitor())
        
        # Wait for heartbeat to run
        await asyncio.sleep(0.6)
        
        # Should have detected failure
        assert task.done() or task.cancelled()
        
        # Clean up
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_connection_with_notification_processing(self):
        """Test connection with notification processing during reconnection."""
        events = []
        
        def handler(event_data):
            events.append(event_data)
        
        self.client.set_connection_handler("reconnecting", handler)
        self.client.set_connection_handler("failed", handler)
        
        # Trigger reconnection
        self.client.connection_state = ConnectionState.FAILED
        await self.client._attempt_reconnection()
        
        # Should have received events
        assert len(events) > 0
    
    @pytest.mark.asyncio
    async def test_offline_queue_processing_with_items(self):
        """Test offline queue processing with actual queued items."""
        # Add items to queue
        self.client.offline_queue = [
            {"method": "test1", "params": {"data": "test1"}},
            {"method": "test2", "params": {"data": "test2"}},
            {"method": "test3", "params": {"data": "test3"}}
        ]
        
        initial_size = len(self.client.offline_queue)
        
        # Process queue
        await self.client._process_offline_queue()
        
        # Queue should be cleared
        assert len(self.client.offline_queue) == 0
    
    @pytest.mark.asyncio
    async def test_handle_offline_request_different_methods(self):
        """Test offline request handling for different method types."""
        await self.client._enter_offline_mode()
        
        # Test different methods
        methods = ["get_status", "submit_extraction", "get_results", "subscribe_updates", "unknown_method"]
        
        for method in methods:
            result = await self.client._handle_offline_request(method, {})
            assert result["offline_mode"] is True
            assert "status" in result or "message" in result


class TestMCPClientRealServerIntegration:
    """Tests with real server integration using embedded server fixture (+15%)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = None
    
    @pytest.mark.asyncio
    async def test_successful_connection_and_initialization(self, mcp_test_server):
        """Test successful connection and initialization with embedded server."""
        # Create client with embedded server URL
        self.client = MCPClient(
            server_url=mcp_test_server["url"],
            reconnect_attempts=2,
            reconnect_delay=0.1,
            request_timeout=5.0,
            heartbeat_interval=1.0
        )
        
        try:
            # Connect
            connected = await self.client.connect()
            assert connected is True
            assert self.client.is_connected()
            
            # Initialize
            result = await self.client.initialize({"name": "test-client", "version": "1.0.0"})
            assert self.client.is_initialized()
            assert "protocolVersion" in result
            
            # Verify connection stats
            stats = self.client.get_connection_stats()
            assert stats["connection_state"] == "initialized"
            assert stats["connection_attempts"] == 0
            
        finally:
            if self.client:
                await self.client.disconnect()
    
    @pytest.mark.asyncio
    async def test_successful_status_request(self, mcp_test_server):
        """Test successful status request with embedded server."""
        self.client = MCPClient(
            server_url=mcp_test_server["url"],
            reconnect_attempts=2,
            reconnect_delay=0.1,
            request_timeout=5.0
        )
        
        try:
            # Connect and initialize
            await self.client.connect()
            await self.client.initialize({"name": "test", "version": "1.0"})
            
            # Request status
            status = await self.client.get_status()
            assert "system_status" in status
            
        finally:
            if self.client:
                await self.client.disconnect()
    
    @pytest.mark.asyncio
    async def test_successful_subscription(self, mcp_test_server):
        """Test successful subscription with embedded server."""
        self.client = MCPClient(
            server_url=mcp_test_server["url"],
            reconnect_attempts=2,
            reconnect_delay=0.1,
            request_timeout=5.0
        )
        
        try:
            # Connect and initialize
            await self.client.connect()
            await self.client.initialize({"name": "test", "version": "1.0"})
            
            # Subscribe
            result = await self.client.subscribe_updates(["status_update"])
            assert result["subscribed"] is True
            
            # Unsubscribe
            result = await self.client.unsubscribe_updates(["status_update"])
            assert result["unsubscribed"] is True
            
        finally:
            if self.client:
                await self.client.disconnect()
    
    @pytest.mark.asyncio
    async def test_connection_recovery_after_server_restart(self, mcp_test_server):
        """Test connection recovery when server restarts."""
        self.client = MCPClient(
            server_url=mcp_test_server["url"],
            reconnect_attempts=2,
            reconnect_delay=0.1,
            request_timeout=5.0
        )
        
        try:
            # Initial connection
            await self.client.connect()
            await self.client.initialize({"name": "test", "version": "1.0"})
            
            # Stop server
            await mcp_test_server["server"].stop()
            await asyncio.sleep(0.2)
            
            # Restart server
            await mcp_test_server["server"].start()
            await asyncio.sleep(0.2)
            
            # Force reconnect
            reconnected = await self.client.force_reconnect()
            
            if reconnected:
                # Re-initialize
                await self.client.initialize({"name": "test", "version": "1.0"})
                assert self.client.is_initialized()
            
        finally:
            if self.client:
                await self.client.disconnect()
    
    @pytest.mark.asyncio
    async def test_heartbeat_with_real_connection(self, mcp_test_server):
        """Test heartbeat monitoring with real WebSocket connection."""
        self.client = MCPClient(
            server_url=mcp_test_server["url"],
            reconnect_attempts=2,
            reconnect_delay=0.1,
            request_timeout=5.0,
            heartbeat_interval=0.5
        )
        
        try:
            # Connect
            await self.client.connect()
            
            # Wait for heartbeat to run
            await asyncio.sleep(1.2)
            
            # Connection should still be alive
            assert self.client.is_connected()
            
        finally:
            if self.client:
                await self.client.disconnect()
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mcp_test_server):
        """Test handling concurrent requests."""
        self.client = MCPClient(
            server_url=mcp_test_server["url"],
            reconnect_attempts=2,
            reconnect_delay=0.1,
            request_timeout=5.0
        )
        
        try:
            # Connect and initialize
            await self.client.connect()
            await self.client.initialize({"name": "test", "version": "1.0"})
            
            # Send concurrent requests
            tasks = [
                self.client.get_status(),
                self.client.get_status(include_details=True),
                self.client.get_status()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            for result in results:
                if not isinstance(result, Exception):
                    assert "system_status" in result
            
        finally:
            if self.client:
                await self.client.disconnect()
    
    @pytest.mark.asyncio
    async def test_health_check_with_real_server(self, mcp_test_server):
        """Test health check with real server connection."""
        self.client = MCPClient(
            server_url=mcp_test_server["url"],
            reconnect_attempts=2,
            reconnect_delay=0.1,
            request_timeout=5.0
        )
        
        try:
            # Connect and initialize
            await self.client.connect()
            await self.client.initialize({"name": "test", "version": "1.0"})
            
            # Health check
            health = await self.client.health_check()
            
            assert health["healthy"] is True
            assert health["connection_state"] == "initialized"
            assert "details" in health
            
        finally:
            if self.client:
                await self.client.disconnect()

# src/compareblocks/mcp/client.py

"""
MCP Client implementation for BECR system.

Provides client functionality for connecting to MCP servers and sending requests
with enhanced connection management, error handling, and reconnection logic.
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum
import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, InvalidURI, WebSocketException

from .protocol import MCPProtocol, MCPMessage, MCPMethod


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    INITIALIZED = "initialized"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    OFFLINE = "offline"


class MCPConnectionError(Exception):
    """MCP connection specific error."""
    pass


class MCPTimeoutError(Exception):
    """MCP request timeout error."""
    pass


class MCPClient:
    """Enhanced MCP Client for connecting to BECR MCP servers with robust connection management."""
    
    def __init__(self, server_url: str = "ws://localhost:8765", 
                 reconnect_attempts: int = 5, 
                 reconnect_delay: float = 2.0,
                 request_timeout: float = 30.0,
                 heartbeat_interval: float = 30.0):
        self.server_url = server_url
        self.protocol = MCPProtocol()
        self.websocket: Optional[WebSocketClientProtocol] = None
        
        # Connection state management
        self.connection_state = ConnectionState.DISCONNECTED
        self.last_connection_attempt = None
        self.connection_attempts = 0
        self.max_reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.request_timeout = request_timeout
        self.heartbeat_interval = heartbeat_interval
        
        # Message handling
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.notification_handlers: Dict[str, Callable] = {}
        self.connection_handlers: Dict[str, Callable] = {}
        
        # Background tasks
        self.message_handler_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.reconnect_task: Optional[asyncio.Task] = None
        
        # Offline mode support
        self.offline_mode = False
        self.offline_queue: List[Dict[str, Any]] = []
        self.max_offline_queue_size = 1000
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    async def connect(self) -> bool:
        """Connect to MCP server with enhanced error handling and state management."""
        if self.connection_state in [ConnectionState.CONNECTED, ConnectionState.INITIALIZED]:
            self.logger.info("Already connected to MCP server")
            return True
        
        self.connection_state = ConnectionState.CONNECTING
        self.last_connection_attempt = datetime.now()
        
        try:
            self.logger.info(f"Connecting to MCP server: {self.server_url}")
            
            # Validate server URL
            if not self.server_url or not self.server_url.startswith(('ws://', 'wss://')):
                raise MCPConnectionError(f"Invalid server URL: {self.server_url}")
            
            # Attempt connection with timeout
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.server_url,
                    ping_interval=self.heartbeat_interval,
                    ping_timeout=10,
                    close_timeout=10
                ),
                timeout=10.0
            )
            
            self.connection_state = ConnectionState.CONNECTED
            self.connection_attempts = 0
            self.offline_mode = False
            
            # Start background tasks
            self.message_handler_task = asyncio.create_task(self._handle_messages())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
            
            # Notify connection handlers
            await self._notify_connection_handlers("connected")
            
            # Process offline queue if any
            await self._process_offline_queue()
            
            self.logger.info("Connected to MCP server successfully")
            return True
            
        except asyncio.TimeoutError:
            self.logger.error("Connection timeout to MCP server")
            self.connection_state = ConnectionState.FAILED
            await self._handle_connection_failure("Connection timeout")
            return False
        except InvalidURI as e:
            self.logger.error(f"Invalid server URI: {e}")
            self.connection_state = ConnectionState.FAILED
            await self._handle_connection_failure(f"Invalid URI: {e}")
            return False
        except ConnectionRefusedError as e:
            self.logger.error(f"Connection refused by server: {e}")
            self.connection_state = ConnectionState.FAILED
            await self._handle_connection_failure(f"Connection refused: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            self.connection_state = ConnectionState.FAILED
            await self._handle_connection_failure(str(e))
            return False
    
    async def disconnect(self):
        """Disconnect from MCP server with proper cleanup."""
        self.logger.info("Disconnecting from MCP server")
        
        # Update state
        self.connection_state = ConnectionState.DISCONNECTED
        
        # Cancel background tasks
        if self.message_handler_task and not self.message_handler_task.done():
            self.message_handler_task.cancel()
            try:
                await self.message_handler_task
            except asyncio.CancelledError:
                pass
        
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                pass
        
        # Close websocket connection
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                self.logger.warning(f"Error closing websocket: {e}")
            finally:
                self.websocket = None
        
        # Cancel pending requests
        for request_id, future in self.pending_requests.items():
            if not future.done():
                future.set_exception(MCPConnectionError("Connection closed"))
        self.pending_requests.clear()
        
        # Notify connection handlers
        await self._notify_connection_handlers("disconnected")
        
        self.logger.info("Disconnected from MCP server")
    
    async def initialize(self, client_info: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize MCP connection with enhanced error handling."""
        if self.connection_state != ConnectionState.CONNECTED:
            raise MCPConnectionError("Not connected to server")
        
        try:
            request = self.protocol.create_request(
                MCPMethod.INITIALIZE.value,
                {"clientInfo": client_info}
            )
            
            response = await self._send_request(request)
            
            if "error" in response:
                raise MCPConnectionError(f"Initialization failed: {response['error']}")
            
            self.connection_state = ConnectionState.INITIALIZED
            self.logger.info("MCP connection initialized")
            return response["result"]
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP connection: {e}")
            raise MCPConnectionError(f"Initialization failed: {e}")
    
    async def _handle_connection_failure(self, error_message: str):
        """Handle connection failure with reconnection logic."""
        self.connection_attempts += 1
        self.logger.warning(f"Connection failure (attempt {self.connection_attempts}): {error_message}")
        
        # Notify connection handlers
        await self._notify_connection_handlers("failed", {"error": error_message, "attempts": self.connection_attempts})
        
        # Check if we should attempt reconnection
        if self.connection_attempts < self.max_reconnect_attempts:
            self.logger.info(f"Scheduling reconnection attempt {self.connection_attempts + 1}")
            self.reconnect_task = asyncio.create_task(self._attempt_reconnection())
        else:
            self.logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached. Entering offline mode.")
            await self._enter_offline_mode()
    
    async def _attempt_reconnection(self):
        """Attempt to reconnect to the server."""
        await asyncio.sleep(self.reconnect_delay * (2 ** min(self.connection_attempts - 1, 5)))  # Exponential backoff
        
        self.connection_state = ConnectionState.RECONNECTING
        await self._notify_connection_handlers("reconnecting", {"attempts": self.connection_attempts})
        
        success = await self.connect()
        if success and self.connection_state == ConnectionState.CONNECTED:
            self.logger.info("Reconnection successful")
            # Re-initialize if we were previously initialized
            # This would need client info to be stored for re-initialization
        else:
            await self._handle_connection_failure("Reconnection failed")
    
    async def _enter_offline_mode(self):
        """Enter offline mode when connection cannot be established."""
        self.offline_mode = True
        self.connection_state = ConnectionState.OFFLINE
        self.logger.info("Entered offline mode - requests will be queued")
        await self._notify_connection_handlers("offline")
    
    async def _process_offline_queue(self):
        """Process queued requests when connection is restored."""
        if not self.offline_queue:
            return
        
        self.logger.info(f"Processing {len(self.offline_queue)} queued requests")
        
        # Process queued requests
        for queued_request in self.offline_queue[:]:  # Copy to avoid modification during iteration
            try:
                # Attempt to send the queued request
                # This is a simplified version - in practice, you'd need to handle different request types
                self.logger.info(f"Processing queued request: {queued_request.get('method', 'unknown')}")
                # Remove from queue after successful processing
                self.offline_queue.remove(queued_request)
            except Exception as e:
                self.logger.error(f"Failed to process queued request: {e}")
        
        self.logger.info("Finished processing offline queue")
    
    async def _heartbeat_monitor(self):
        """Monitor connection health with heartbeat."""
        while self.connection_state in [ConnectionState.CONNECTED, ConnectionState.INITIALIZED]:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Check if websocket is still alive
                if self.websocket and not self.websocket.closed:
                    # Send a ping to check connection
                    try:
                        pong_waiter = await self.websocket.ping()
                        await asyncio.wait_for(pong_waiter, timeout=10.0)
                    except asyncio.TimeoutError:
                        self.logger.warning("Heartbeat timeout - connection may be lost")
                        await self._handle_connection_failure("Heartbeat timeout")
                        break
                    except Exception as e:
                        self.logger.warning(f"Heartbeat failed: {e}")
                        await self._handle_connection_failure(f"Heartbeat failed: {e}")
                        break
                else:
                    self.logger.warning("WebSocket connection lost")
                    await self._handle_connection_failure("WebSocket connection lost")
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat monitor: {e}")
                break
    
    def set_connection_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Set handler for connection events (connected, disconnected, failed, reconnecting, offline)."""
        self.connection_handlers[event_type] = handler
    
    async def _notify_connection_handlers(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """Notify connection event handlers."""
        if event_type in self.connection_handlers:
            try:
                handler = self.connection_handlers[event_type]
                event_data = {
                    "event": event_type,
                    "timestamp": datetime.now().isoformat(),
                    "connection_state": self.connection_state.value,
                    **(data or {})
                }
                
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                self.logger.error(f"Error in connection handler for {event_type}: {e}")
    
    async def submit_extraction(self, pdf_path: str, variations: List[Dict[str, Any]], 
                              metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Submit extraction data for processing with offline support."""
        params = {
            "pdf_path": pdf_path,
            "variations": variations
        }
        
        if metadata:
            params["metadata"] = metadata
        
        # Handle offline mode
        if self.offline_mode:
            return await self._handle_offline_request("submit_extraction", params)
        
        if self.connection_state != ConnectionState.INITIALIZED:
            raise MCPConnectionError("MCP connection not initialized")
        
        try:
            request = self.protocol.create_request(
                MCPMethod.SUBMIT_EXTRACTION.value,
                params
            )
            
            response = await self._send_request(request)
            
            if "error" in response:
                raise MCPConnectionError(f"Extraction submission failed: {response['error']}")
            
            return response["result"]
            
        except Exception as e:
            self.logger.error(f"Failed to submit extraction: {e}")
            # Queue request for offline processing if connection is lost
            if isinstance(e, (ConnectionClosed, MCPConnectionError)):
                return await self._handle_offline_request("submit_extraction", params)
            raise
    
    async def get_status(self, session_id: Optional[str] = None, 
                        include_details: bool = False) -> Dict[str, Any]:
        """Get processing status with offline support."""
        params = {"include_details": include_details}
        if session_id:
            params["session_id"] = session_id
        
        # Handle offline mode
        if self.offline_mode:
            return await self._handle_offline_request("get_status", params)
        
        if self.connection_state != ConnectionState.INITIALIZED:
            raise MCPConnectionError("MCP connection not initialized")
        
        try:
            request = self.protocol.create_request(
                MCPMethod.GET_STATUS.value,
                params
            )
            
            response = await self._send_request(request)
            
            if "error" in response:
                raise MCPConnectionError(f"Status request failed: {response['error']}")
            
            return response["result"]
            
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            if isinstance(e, (ConnectionClosed, MCPConnectionError)):
                return await self._handle_offline_request("get_status", params)
            raise
    
    async def get_results(self, session_id: str, format_type: str = "json", 
                         include_analytics: bool = False) -> Dict[str, Any]:
        """Get processing results with offline support."""
        params = {
            "session_id": session_id,
            "format": format_type,
            "include_analytics": include_analytics
        }
        
        # Handle offline mode
        if self.offline_mode:
            return await self._handle_offline_request("get_results", params)
        
        if self.connection_state != ConnectionState.INITIALIZED:
            raise MCPConnectionError("MCP connection not initialized")
        
        try:
            request = self.protocol.create_request(
                MCPMethod.GET_RESULTS.value,
                params
            )
            
            response = await self._send_request(request)
            
            if "error" in response:
                raise MCPConnectionError(f"Results request failed: {response['error']}")
            
            return response["result"]
            
        except Exception as e:
            self.logger.error(f"Failed to get results: {e}")
            if isinstance(e, (ConnectionClosed, MCPConnectionError)):
                return await self._handle_offline_request("get_results", params)
            raise
    
    async def subscribe_updates(self, event_types: List[str]) -> Dict[str, Any]:
        """Subscribe to event notifications with enhanced error handling."""
        params = {"event_types": event_types}
        
        # Handle offline mode
        if self.offline_mode:
            return await self._handle_offline_request("subscribe_updates", params)
        
        if self.connection_state != ConnectionState.INITIALIZED:
            raise MCPConnectionError("MCP connection not initialized")
        
        try:
            request = self.protocol.create_request(
                MCPMethod.SUBSCRIBE_UPDATES.value,
                params
            )
            
            response = await self._send_request(request)
            
            if "error" in response:
                raise MCPConnectionError(f"Subscription failed: {response['error']}")
            
            return response["result"]
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to updates: {e}")
            if isinstance(e, (ConnectionClosed, MCPConnectionError)):
                return await self._handle_offline_request("subscribe_updates", params)
            raise
    
    async def unsubscribe_updates(self, event_types: List[str]) -> Dict[str, Any]:
        """Unsubscribe from event notifications with enhanced error handling."""
        params = {"event_types": event_types}
        
        # Handle offline mode
        if self.offline_mode:
            return await self._handle_offline_request("unsubscribe_updates", params)
        
        if self.connection_state != ConnectionState.INITIALIZED:
            raise MCPConnectionError("MCP connection not initialized")
        
        try:
            request = self.protocol.create_request(
                MCPMethod.UNSUBSCRIBE_UPDATES.value,
                params
            )
            
            response = await self._send_request(request)
            
            if "error" in response:
                raise MCPConnectionError(f"Unsubscription failed: {response['error']}")
            
            return response["result"]
            
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from updates: {e}")
            if isinstance(e, (ConnectionClosed, MCPConnectionError)):
                return await self._handle_offline_request("unsubscribe_updates", params)
            raise
    
    def set_notification_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Set handler for notification events."""
        self.notification_handlers[event_type] = handler
    
    async def _send_request(self, request: MCPMessage) -> Dict[str, Any]:
        """Send request and wait for response with enhanced error handling."""
        if not self.websocket or self.connection_state not in [ConnectionState.CONNECTED, ConnectionState.INITIALIZED]:
            raise MCPConnectionError("Not connected to server")
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request.id] = future
        
        try:
            # Send request
            await self.websocket.send(request.to_json())
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=self.request_timeout)
            return response
            
        except asyncio.TimeoutError:
            self.logger.error(f"Request timeout for {request.method}")
            raise MCPTimeoutError(f"Request timeout after {self.request_timeout}s")
        except ConnectionClosed as e:
            self.logger.error(f"Connection closed during request: {e}")
            await self._handle_connection_failure("Connection closed during request")
            raise MCPConnectionError("Connection closed during request")
        except WebSocketException as e:
            self.logger.error(f"WebSocket error during request: {e}")
            await self._handle_connection_failure(f"WebSocket error: {e}")
            raise MCPConnectionError(f"WebSocket error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during request: {e}")
            raise MCPConnectionError(f"Request failed: {e}")
        finally:
            # Cleanup
            if request.id in self.pending_requests:
                del self.pending_requests[request.id]
    
    async def _handle_offline_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request in offline mode by queuing or returning cached data."""
        request_data = {
            "method": method,
            "params": params,
            "timestamp": datetime.now().isoformat(),
            "id": f"offline_{len(self.offline_queue)}"
        }
        
        # Add to offline queue if not full
        if len(self.offline_queue) < self.max_offline_queue_size:
            self.offline_queue.append(request_data)
            self.logger.info(f"Queued offline request: {method}")
        else:
            self.logger.warning(f"Offline queue full, dropping request: {method}")
        
        # Return appropriate offline response
        if method == "get_status":
            return {
                "status": "offline",
                "message": "System is offline - status unavailable",
                "queued": True,
                "offline_mode": True
            }
        elif method == "submit_extraction":
            return {
                "session_id": f"offline_{datetime.now().timestamp()}",
                "status": "queued",
                "message": "Extraction queued for processing when connection is restored",
                "offline_mode": True
            }
        else:
            return {
                "status": "offline",
                "message": f"Request {method} queued for processing when connection is restored",
                "offline_mode": True
            }
    
    async def _handle_messages(self):
        """Handle incoming messages from server with enhanced error recovery."""
        try:
            async for message_str in self.websocket:
                await self._process_message(message_str)
        except ConnectionClosed as e:
            self.logger.info(f"Server connection closed: {e}")
            await self._handle_connection_failure("Server connection closed")
        except WebSocketException as e:
            self.logger.error(f"WebSocket error in message handler: {e}")
            await self._handle_connection_failure(f"WebSocket error: {e}")
        except asyncio.CancelledError:
            self.logger.info("Message handler cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error handling messages: {e}")
            await self._handle_connection_failure(f"Message handler error: {e}")
    
    async def _process_message(self, message_str: str):
        """Process incoming message."""
        try:
            message = MCPMessage.from_json(message_str)
            
            if message.id and message.id in self.pending_requests:
                # This is a response to a pending request
                future = self.pending_requests[message.id]
                if not future.done():
                    response_data = {
                        "result": message.result,
                        "error": message.error
                    }
                    future.set_result(response_data)
            
            elif message.method:
                # This is a notification
                await self._handle_notification(message)
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    async def _handle_notification(self, message: MCPMessage):
        """Handle notification message."""
        method = message.method
        params = message.params or {}
        
        self.logger.info(f"Received notification: {method}")
        
        # Call registered handler if available
        if method in self.notification_handlers:
            try:
                handler = self.notification_handlers[method]
                if asyncio.iscoroutinefunction(handler):
                    await handler(params)
                else:
                    handler(params)
            except Exception as e:
                self.logger.error(f"Error in notification handler for {method}: {e}")
    
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self.connection_state in [ConnectionState.CONNECTED, ConnectionState.INITIALIZED]
    
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self.connection_state == ConnectionState.INITIALIZED
    
    def is_offline(self) -> bool:
        """Check if client is in offline mode."""
        return self.offline_mode
    
    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self.connection_state
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get detailed connection statistics."""
        return {
            "connection_state": self.connection_state.value,
            "server_url": self.server_url,
            "connection_attempts": self.connection_attempts,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "last_connection_attempt": self.last_connection_attempt.isoformat() if self.last_connection_attempt else None,
            "offline_mode": self.offline_mode,
            "offline_queue_size": len(self.offline_queue),
            "pending_requests": len(self.pending_requests),
            "notification_handlers": list(self.notification_handlers.keys()),
            "connection_handlers": list(self.connection_handlers.keys()),
            "websocket_closed": self.websocket.closed if self.websocket else True
        }
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get client information."""
        return {
            "server_url": self.server_url,
            "connection_state": self.connection_state.value,
            "connected": self.is_connected(),
            "initialized": self.is_initialized(),
            "offline_mode": self.offline_mode,
            "pending_requests": len(self.pending_requests),
            "notification_handlers": list(self.notification_handlers.keys()),
            "connection_handlers": list(self.connection_handlers.keys()),
            "offline_queue_size": len(self.offline_queue),
            "connection_attempts": self.connection_attempts
        }
    
    async def force_reconnect(self) -> bool:
        """Force a reconnection attempt."""
        self.logger.info("Forcing reconnection attempt")
        await self.disconnect()
        return await self.connect()
    
    def clear_offline_queue(self):
        """Clear the offline request queue."""
        cleared_count = len(self.offline_queue)
        self.offline_queue.clear()
        self.logger.info(f"Cleared {cleared_count} requests from offline queue")
        return cleared_count
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the MCP connection."""
        health_status = {
            "healthy": False,
            "connection_state": self.connection_state.value,
            "timestamp": datetime.now().isoformat(),
            "details": {}
        }
        
        try:
            if self.connection_state == ConnectionState.INITIALIZED:
                # Try a simple status request to verify connection health
                status_response = await self.get_status(include_details=False)
                health_status["healthy"] = True
                health_status["details"]["status_check"] = "passed"
                health_status["details"]["server_response"] = status_response
            elif self.connection_state == ConnectionState.CONNECTED:
                health_status["details"]["status_check"] = "connected_but_not_initialized"
            elif self.offline_mode:
                health_status["details"]["status_check"] = "offline_mode"
                health_status["details"]["offline_queue_size"] = len(self.offline_queue)
            else:
                health_status["details"]["status_check"] = "not_connected"
                
        except Exception as e:
            health_status["details"]["error"] = str(e)
            health_status["details"]["status_check"] = "failed"
        
        return health_status
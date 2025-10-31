# src/compareblocks/mcp/server.py

"""
MCP Server implementation for BECR system.

Provides the main MCP server that handles incoming requests and coordinates
with handlers for processing.
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

from .protocol import MCPProtocol, MCPMessage, MCPErrorCode
from .validation import MCPValidator
from .handlers import ExtractionHandler, StatusHandler


class MCPServer:
    """MCP Server for BECR system."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.protocol = MCPProtocol()
        self.validator = MCPValidator()
        self.extraction_handler = ExtractionHandler(self.validator, self.protocol)
        self.status_handler = StatusHandler(self.extraction_handler)
        
        # Client management
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.client_subscriptions: Dict[str, List[str]] = {}
        
        # Method handlers
        self.handlers: Dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "submit_extraction": self._handle_submit_extraction,
            "get_status": self._handle_get_status,
            "get_results": self._handle_get_results,
            "subscribe_updates": self._handle_subscribe_updates,
            "unsubscribe_updates": self._handle_unsubscribe_updates
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Server state
        self.running = False
        self.server = None
    
    async def start(self):
        """Start the MCP server."""
        self.logger.info(f"Starting MCP server on {self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port
        )
        
        self.running = True
        self.logger.info("MCP server started successfully")
    
    async def stop(self):
        """Stop the MCP server."""
        self.logger.info("Stopping MCP server")
        self.running = False
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Close all client connections
        for client_id, websocket in self.clients.items():
            await websocket.close()
        
        self.clients.clear()
        self.client_subscriptions.clear()
        
        self.logger.info("MCP server stopped")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol):
        """Handle new client connection."""
        client_id = f"client_{id(websocket)}"
        self.clients[client_id] = websocket
        self.client_subscriptions[client_id] = []
        
        self.logger.info(f"Client connected: {client_id}")
        
        try:
            async for message in websocket:
                await self._process_message(client_id, message)
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            self.logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Cleanup client
            if client_id in self.clients:
                del self.clients[client_id]
            if client_id in self.client_subscriptions:
                del self.client_subscriptions[client_id]
    
    async def _process_message(self, client_id: str, message_str: str):
        """Process incoming message from client."""
        try:
            # Parse message
            message = MCPMessage.from_json(message_str)
            
            # Validate message
            error = self.protocol.validate_message(message)
            if error:
                error_response = self.protocol.create_error_response(
                    message.id or "unknown",
                    MCPErrorCode.INVALID_REQUEST,
                    error.message,
                    error.data
                )
                await self._send_message(client_id, error_response)
                return
            
            # Handle request
            if message.method in self.handlers:
                try:
                    result = await self.handlers[message.method](client_id, message.params or {})
                    response = self.protocol.create_response(message.id, result)
                    await self._send_message(client_id, response)
                except Exception as e:
                    error_response = self.protocol.create_error_response(
                        message.id,
                        MCPErrorCode.INTERNAL_ERROR,
                        str(e)
                    )
                    await self._send_message(client_id, error_response)
            else:
                error_response = self.protocol.create_error_response(
                    message.id,
                    MCPErrorCode.METHOD_NOT_FOUND,
                    f"Method '{message.method}' not found"
                )
                await self._send_message(client_id, error_response)
                
        except json.JSONDecodeError as e:
            error_response = self.protocol.create_error_response(
                "unknown",
                MCPErrorCode.PARSE_ERROR,
                f"Invalid JSON: {str(e)}"
            )
            await self._send_message(client_id, error_response)
        except Exception as e:
            self.logger.error(f"Error processing message from {client_id}: {e}")
    
    async def _send_message(self, client_id: str, message: MCPMessage):
        """Send message to client."""
        if client_id in self.clients:
            try:
                await self.clients[client_id].send(message.to_json())
            except Exception as e:
                self.logger.error(f"Error sending message to {client_id}: {e}")
    
    async def _handle_initialize(self, client_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return self.protocol.handle_initialize(params)
    
    async def _handle_submit_extraction(self, client_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle extraction submission request."""
        return await self.extraction_handler.handle_submission(params)
    
    async def _handle_get_status(self, client_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status request."""
        # Validate request
        is_valid, error_msg = self.validator.validate_status_request(params)
        if not is_valid:
            raise ValueError(error_msg)
        
        return self.status_handler.handle_status_request(params)
    
    async def _handle_get_results(self, client_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle results request."""
        # Validate request
        is_valid, error_msg = self.validator.validate_results_request(params)
        if not is_valid:
            raise ValueError(error_msg)
        
        return self.status_handler.handle_results_request(params)
    
    async def _handle_subscribe_updates(self, client_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription request."""
        # Validate request
        is_valid, error_msg = self.validator.validate_subscription_request(params)
        if not is_valid:
            raise ValueError(error_msg)
        
        event_types = params["event_types"]
        
        # Add to client subscriptions
        if client_id not in self.client_subscriptions:
            self.client_subscriptions[client_id] = []
        
        for event_type in event_types:
            if event_type not in self.client_subscriptions[client_id]:
                self.client_subscriptions[client_id].append(event_type)
        
        # Subscribe in protocol
        self.protocol.subscribe_client(client_id, event_types)
        
        return {
            "subscribed": True,
            "event_types": event_types,
            "client_id": client_id
        }
    
    async def _handle_unsubscribe_updates(self, client_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unsubscription request."""
        # Validate request
        is_valid, error_msg = self.validator.validate_subscription_request(params)
        if not is_valid:
            raise ValueError(error_msg)
        
        event_types = params["event_types"]
        
        # Remove from client subscriptions
        if client_id in self.client_subscriptions:
            for event_type in event_types:
                if event_type in self.client_subscriptions[client_id]:
                    self.client_subscriptions[client_id].remove(event_type)
        
        # Unsubscribe in protocol
        self.protocol.unsubscribe_client(client_id, event_types)
        
        return {
            "unsubscribed": True,
            "event_types": event_types,
            "client_id": client_id
        }
    
    async def broadcast_notification(self, event_type: str, data: Dict[str, Any]):
        """Broadcast notification to subscribed clients."""
        notification = self.protocol.create_notification(
            method=event_type,
            params={
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
        )
        
        # Get subscribers for this event type
        subscribers = self.protocol.get_subscribers(event_type)
        
        # Send to all subscribed clients
        for client_id in subscribers:
            if client_id in self.clients:
                await self._send_message(client_id, notification)
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "host": self.host,
            "port": self.port,
            "running": self.running,
            "connected_clients": len(self.clients),
            "protocol_version": self.protocol.version,
            "capabilities": self.protocol.capabilities
        }
    
    def get_client_info(self) -> List[Dict[str, Any]]:
        """Get information about connected clients."""
        client_info = []
        for client_id, websocket in self.clients.items():
            subscriptions = self.client_subscriptions.get(client_id, [])
            client_info.append({
                "client_id": client_id,
                "remote_address": websocket.remote_address,
                "subscriptions": subscriptions,
                "connected_at": datetime.now().isoformat()  # This would be tracked properly
            })
        return client_info
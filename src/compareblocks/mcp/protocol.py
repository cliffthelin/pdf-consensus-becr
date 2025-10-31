# src/compareblocks/mcp/protocol.py

"""
MCP Protocol implementation for BECR system.

Provides standardized Model Context Protocol endpoints and message handling
for external system integration.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum


class MCPMessageType(Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPMethod(Enum):
    """Supported MCP methods."""
    INITIALIZE = "initialize"
    SUBMIT_EXTRACTION = "submit_extraction"
    GET_STATUS = "get_status"
    GET_RESULTS = "get_results"
    SUBSCRIBE_UPDATES = "subscribe_updates"
    UNSUBSCRIBE_UPDATES = "unsubscribe_updates"


@dataclass
class MCPMessage:
    """Base MCP message structure."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """Create message from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPMessage':
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class MCPError:
    """MCP error structure."""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class MCPErrorCode(Enum):
    """Standard MCP error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000


class MCPProtocol:
    """MCP Protocol handler for BECR system."""
    
    def __init__(self):
        self.version = "1.0.0"
        self.capabilities = {
            "extraction_submission": True,
            "status_monitoring": True,
            "real_time_updates": True,
            "result_retrieval": True
        }
        self.subscribers: Dict[str, List[str]] = {}
    
    def create_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Create an MCP request message."""
        return MCPMessage(
            method=method,
            params=params
        )
    
    def create_response(self, request_id: str, result: Any) -> MCPMessage:
        """Create an MCP response message."""
        return MCPMessage(
            id=request_id,
            result=result
        )
    
    def create_error_response(self, request_id: str, error_code: MCPErrorCode, 
                            message: str, data: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Create an MCP error response."""
        error = MCPError(
            code=error_code.value,
            message=message,
            data=data
        )
        return MCPMessage(
            id=request_id,
            error=asdict(error)
        )
    
    def create_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Create an MCP notification message."""
        return MCPMessage(
            method=method,
            params=params
        )
    
    def validate_message(self, message: MCPMessage) -> Optional[MCPError]:
        """Validate MCP message structure."""
        if message.jsonrpc != "2.0":
            return MCPError(
                code=MCPErrorCode.INVALID_REQUEST.value,
                message="Invalid JSON-RPC version"
            )
        
        # Request validation
        if message.method is not None:
            if message.method not in [m.value for m in MCPMethod]:
                return MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND.value,
                    message=f"Method '{message.method}' not found"
                )
        
        return None
    
    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        client_info = params.get("clientInfo", {})
        
        return {
            "protocolVersion": self.version,
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": "BECR-MCP-Server",
                "version": self.version,
                "description": "Blockwise Extraction Comparison & Review MCP Server"
            }
        }
    
    def subscribe_client(self, client_id: str, event_types: List[str]) -> bool:
        """Subscribe client to event notifications."""
        for event_type in event_types:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            if client_id not in self.subscribers[event_type]:
                self.subscribers[event_type].append(client_id)
        return True
    
    def unsubscribe_client(self, client_id: str, event_types: List[str]) -> bool:
        """Unsubscribe client from event notifications."""
        for event_type in event_types:
            if event_type in self.subscribers:
                if client_id in self.subscribers[event_type]:
                    self.subscribers[event_type].remove(client_id)
        return True
    
    def get_subscribers(self, event_type: str) -> List[str]:
        """Get list of subscribers for an event type."""
        return self.subscribers.get(event_type, [])
    
    def create_status_update(self, status_data: Dict[str, Any]) -> MCPMessage:
        """Create status update notification."""
        return self.create_notification(
            method="status_update",
            params={
                "timestamp": datetime.now().isoformat(),
                "status": status_data
            }
        )
    
    def create_processing_complete(self, result_data: Dict[str, Any]) -> MCPMessage:
        """Create processing complete notification."""
        return self.create_notification(
            method="processing_complete",
            params={
                "timestamp": datetime.now().isoformat(),
                "result": result_data
            }
        )
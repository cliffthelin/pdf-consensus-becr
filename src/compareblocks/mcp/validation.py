# src/compareblocks/mcp/validation.py

"""
MCP validation module for BECR system.

Provides validation for MCP messages and external extraction submissions.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import jsonschema
from jsonschema import validate, ValidationError

from ..io.schemas import INPUT_VARIATION_SCHEMA, CONSENSUS_OUTPUT_SCHEMA


class MCPValidator:
    """Validator for MCP messages and extraction data."""
    
    def __init__(self):
        self.mcp_schemas = self._load_mcp_schemas()
    
    def _load_mcp_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load MCP message schemas."""
        return {
            "extraction_submission": {
                "type": "object",
                "required": ["pdf_path", "variations"],
                "properties": {
                    "pdf_path": {"type": "string"},
                    "variations": {
                        "type": "array",
                        "items": INPUT_VARIATION_SCHEMA
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "engine_name": {"type": "string"},
                            "engine_version": {"type": "string"},
                            "processing_timestamp": {"type": "string"},
                            "configuration": {"type": "object"}
                        }
                    }
                }
            },
            "status_request": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "include_details": {"type": "boolean"}
                }
            },
            "results_request": {
                "type": "object",
                "required": ["session_id"],
                "properties": {
                    "session_id": {"type": "string"},
                    "format": {
                        "type": "string",
                        "enum": ["ndjson", "json", "summary"]
                    },
                    "include_analytics": {"type": "boolean"}
                }
            },
            "subscription_request": {
                "type": "object",
                "required": ["event_types"],
                "properties": {
                    "event_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["status_update", "processing_complete", "error"]
                        }
                    }
                }
            }
        }
    
    def validate_extraction_submission(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate extraction submission data."""
        try:
            # Validate overall structure
            validate(data, self.mcp_schemas["extraction_submission"])
            
            # Validate each variation against INPUT_VARIATION_SCHEMA
            for i, variation in enumerate(data.get("variations", [])):
                try:
                    validate(variation, INPUT_VARIATION_SCHEMA)
                except ValidationError as e:
                    return False, f"Variation {i} validation error: {e.message}"
            
            # Additional business logic validation
            pdf_path = data.get("pdf_path")
            if pdf_path and not Path(pdf_path).exists():
                return False, f"PDF file not found: {pdf_path}"
            
            return True, None
            
        except ValidationError as e:
            return False, f"Schema validation error: {e.message}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def validate_status_request(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate status request data."""
        try:
            validate(data, self.mcp_schemas["status_request"])
            return True, None
        except ValidationError as e:
            return False, f"Status request validation error: {e.message}"
    
    def validate_results_request(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate results request data."""
        try:
            validate(data, self.mcp_schemas["results_request"])
            return True, None
        except ValidationError as e:
            return False, f"Results request validation error: {e.message}"
    
    def validate_subscription_request(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate subscription request data."""
        try:
            validate(data, self.mcp_schemas["subscription_request"])
            return True, None
        except ValidationError as e:
            return False, f"Subscription request validation error: {e.message}"
    
    def validate_consensus_output(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate consensus output data."""
        try:
            validate(data, CONSENSUS_OUTPUT_SCHEMA)
            return True, None
        except ValidationError as e:
            return False, f"Consensus output validation error: {e.message}"
    
    def sanitize_extraction_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize extraction data for security."""
        sanitized = data.copy()
        
        # Remove potentially dangerous fields
        dangerous_fields = ["__proto__", "constructor", "prototype"]
        for field in dangerous_fields:
            if field in sanitized:
                del sanitized[field]
        
        # Sanitize variations
        if "variations" in sanitized:
            sanitized_variations = []
            for variation in sanitized["variations"]:
                sanitized_variation = variation.copy()
                
                # Limit text length to prevent DoS
                if "text" in sanitized_variation:
                    text = sanitized_variation["text"]
                    if len(text) > 100000:  # 100KB limit
                        sanitized_variation["text"] = text[:100000]
                        sanitized_variation["truncated"] = True
                
                # Remove dangerous metadata
                if "metadata" in sanitized_variation:
                    metadata = sanitized_variation["metadata"]
                    for field in dangerous_fields:
                        if field in metadata:
                            del metadata[field]
                
                sanitized_variations.append(sanitized_variation)
            
            sanitized["variations"] = sanitized_variations
        
        return sanitized
    
    def validate_pdf_path(self, pdf_path: str) -> Tuple[bool, Optional[str]]:
        """Validate PDF file path for security."""
        try:
            path = Path(pdf_path).resolve()
            
            # Check if file exists
            if not path.exists():
                return False, f"PDF file not found: {pdf_path}"
            
            # Check if it's actually a file
            if not path.is_file():
                return False, f"Path is not a file: {pdf_path}"
            
            # Check file extension
            if path.suffix.lower() != '.pdf':
                return False, f"File is not a PDF: {pdf_path}"
            
            # Check file size (limit to 100MB)
            file_size = path.stat().st_size
            if file_size > 100 * 1024 * 1024:
                return False, f"PDF file too large: {file_size} bytes (max 100MB)"
            
            # Path traversal protection
            cwd = Path.cwd().resolve()
            if not str(path).startswith(str(cwd)):
                return False, f"PDF path outside working directory: {pdf_path}"
            
            return True, None
            
        except Exception as e:
            return False, f"PDF path validation error: {str(e)}"
    
    def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """Get MCP schema by name."""
        return self.mcp_schemas.get(schema_name)
    
    def list_schemas(self) -> List[str]:
        """List available schema names."""
        return list(self.mcp_schemas.keys())
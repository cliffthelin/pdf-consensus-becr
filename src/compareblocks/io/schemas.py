# src/compareblocks/io/schemas.py

"""
JSON Schema definitions for NDJSON input variations and consensus output formats.
Provides strict validation schemas for external engine outputs and internal consensus decisions.
"""

from typing import Dict, Any

# Input variation schema for external engine outputs
INPUT_VARIATION_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["doc_id", "page", "engine", "raw_text"],
    "properties": {
        # Required fields
        "doc_id": {
            "type": "string",
            "description": "Unique identifier for the source document"
        },
        "page": {
            "type": "integer",
            "minimum": 1,
            "description": "Page number (1-based)"
        },
        "engine": {
            "type": "string",
            "description": "Name of the extraction engine"
        },
        "raw_text": {
            "type": "string",
            "description": "Extracted text content"
        },
        
        # Optional fields
        "block_id": {
            "type": "string",
            "description": "Global Block Grid identifier (if available)"
        },
        "bbox": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 4,
            "maxItems": 4,
            "description": "Bounding box as [x, y, width, height]"
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Engine confidence score"
        },
        "orientation": {
            "type": "number",
            "description": "Text orientation in degrees"
        },
        "metadata": {
            "type": "object",
            "description": "Additional engine-specific metadata"
        }
    },
    "additionalProperties": False
}

# Consensus output schema for final decisions and analytics
CONSENSUS_OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "doc_id", "page", "block_id", "selected_engine", 
        "final_text", "decision_reason", "engine_scores", "anomaly_score", "character_consistency_score"
    ],
    "properties": {
        # Required consensus fields
        "doc_id": {
            "type": "string",
            "description": "Unique identifier for the source document"
        },
        "page": {
            "type": "integer",
            "minimum": 1,
            "description": "Page number (1-based)"
        },
        "block_id": {
            "type": "string",
            "description": "Global Block Grid identifier"
        },
        "selected_engine": {
            "type": "string",
            "description": "Engine that provided the selected text"
        },
        "final_text": {
            "type": "string",
            "description": "Final consensus text after processing"
        },
        "decision_reason": {
            "type": "string",
            "enum": ["highest_score", "manual_override", "merged_result", "flagged_review"],
            "description": "Reason for the consensus decision"
        },
        "engine_scores": {
            "type": "object",
            "patternProperties": {
                "^.+$": {"type": "number"}
            },
            "description": "Scores for each engine that provided variations"
        },
        "anomaly_score": {
            "type": "number",
            "minimum": 0.0,
            "description": "Anomaly detection score for quality assessment"
        },
        "character_consistency_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Character-level consistency score across all variations"
        },
        
        # Optional consensus fields
        "bbox": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 4,
            "maxItems": 4,
            "description": "Final bounding box as [x, y, width, height]"
        },
        "consensus_score": {
            "type": "number",
            "description": "Overall consensus confidence score"
        },
        "variations_count": {
            "type": "integer",
            "minimum": 1,
            "description": "Number of variations considered"
        },
        "manual_override": {
            "type": "boolean",
            "description": "Whether this was manually overridden"
        },
        "processing_metadata": {
            "type": "object",
            "description": "Additional processing information"
        },
        "word_consistency_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Word-level consistency score across variations"
        },
        "spelling_accuracy_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Spelling accuracy score for the block"
        },
        "consistency_details": {
            "type": "object",
            "properties": {
                "total_characters": {"type": "integer", "minimum": 0},
                "consistent_characters": {"type": "integer", "minimum": 0},
                "unique_variations": {"type": "integer", "minimum": 0},
                "normalized_for_comparison": {"type": "boolean"},
                "override_terms_count": {"type": "integer", "minimum": 0}
            },
            "description": "Detailed consistency analysis metrics"
        }
    },
    "additionalProperties": False
}

def get_input_schema() -> Dict[str, Any]:
    """Get the input variation schema for validation."""
    return INPUT_VARIATION_SCHEMA

def get_consensus_schema() -> Dict[str, Any]:
    """Get the consensus output schema for validation."""
    return CONSENSUS_OUTPUT_SCHEMA
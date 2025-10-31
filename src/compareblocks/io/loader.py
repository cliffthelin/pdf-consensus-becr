# src/compareblocks/io/loader.py

"""
NDJSON validation and loading functionality with strict schema validation.
Provides clear error messages for malformed records and handles both block_id and bbox-only records.
"""

import json
from typing import List, Dict, Any, Iterator, Optional
from pathlib import Path
import jsonschema
from jsonschema import ValidationError

from .schemas import get_input_schema


class ValidationException(Exception):
    """Exception raised when NDJSON validation fails."""
    
    def __init__(self, message: str, line_number: Optional[int] = None, record: Optional[Dict[str, Any]] = None):
        self.message = message
        self.line_number = line_number
        self.record = record
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format the error message with context."""
        if self.line_number is not None:
            return f"Line {self.line_number}: {self.message}"
        return self.message


class NDJSONLoader:
    """Loads and validates NDJSON files containing text extraction variations."""
    
    def __init__(self):
        self.schema = get_input_schema()
        self.validator = jsonschema.Draft7Validator(self.schema)
    
    def load_file(self, file_path) -> List[Dict[str, Any]]:
        """
        Load and validate an entire NDJSON file.
        
        Args:
            file_path: Path to the NDJSON file (str or Path)
            
        Returns:
            List of validated records
            
        Raises:
            ValidationException: If any record fails validation
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON parsing fails
        """
        # Convert to Path object if string
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        if not file_path.exists():
            raise FileNotFoundError(f"NDJSON file not found: {file_path}")
        
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                
                try:
                    record = json.loads(line)
                    validated_record = self.validate_record(record, line_num)
                    records.append(validated_record)
                except json.JSONDecodeError as e:
                    raise ValidationException(
                        f"Invalid JSON: {e.msg}",
                        line_number=line_num,
                        record=None
                    )
        
        return records
    
    def load_stream(self, file_path: Path) -> Iterator[Dict[str, Any]]:
        """
        Stream and validate NDJSON records one at a time.
        
        Args:
            file_path: Path to the NDJSON file
            
        Yields:
            Validated records
            
        Raises:
            ValidationException: If any record fails validation
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON parsing fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"NDJSON file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                
                try:
                    record = json.loads(line)
                    validated_record = self.validate_record(record, line_num)
                    yield validated_record
                except json.JSONDecodeError as e:
                    raise ValidationException(
                        f"Invalid JSON: {e.msg}",
                        line_number=line_num,
                        record=None
                    )
    
    def validate_record(self, record: Dict[str, Any], line_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate a single record against the input schema.
        
        Args:
            record: The record to validate
            line_number: Optional line number for error reporting
            
        Returns:
            The validated record (potentially with normalized fields)
            
        Raises:
            ValidationException: If validation fails
        """
        try:
            # Validate against schema
            self.validator.validate(record)
            
            # Additional validation for mapping flexibility
            self._validate_mapping_requirements(record, line_number)
            
            # Normalize and return
            return self._normalize_record(record)
            
        except ValidationError as e:
            error_msg = self._format_validation_error(e)
            raise ValidationException(error_msg, line_number, record)
    
    def _validate_mapping_requirements(self, record: Dict[str, Any], line_number: Optional[int] = None):
        """
        Validate that record has either block_id or bbox for mapping flexibility.
        
        Args:
            record: The record to validate
            line_number: Optional line number for error reporting
            
        Raises:
            ValidationException: If neither block_id nor bbox is present
        """
        has_block_id = 'block_id' in record and record['block_id']
        has_bbox = 'bbox' in record and record['bbox']
        
        if not has_block_id and not has_bbox:
            raise ValidationException(
                "Record must have either 'block_id' or 'bbox' for block mapping",
                line_number,
                record
            )
    
    def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize record fields for consistent processing.
        
        Args:
            record: The record to normalize
            
        Returns:
            Normalized record
        """
        normalized = record.copy()
        
        # Ensure confidence is present with default value
        if 'confidence' not in normalized:
            normalized['confidence'] = 1.0
        
        # Ensure metadata is present as empty dict
        if 'metadata' not in normalized:
            normalized['metadata'] = {}
        
        # Normalize bbox to ensure it's exactly 4 elements
        if 'bbox' in normalized and normalized['bbox']:
            bbox = normalized['bbox']
            if len(bbox) != 4:
                raise ValidationException(f"Bounding box must have exactly 4 elements, got {len(bbox)}")
            normalized['bbox'] = [float(x) for x in bbox]
        
        return normalized
    
    def _format_validation_error(self, error: ValidationError) -> str:
        """
        Format a jsonschema ValidationError into a clear error message.
        
        Args:
            error: The validation error
            
        Returns:
            Formatted error message
        """
        if error.path:
            field_path = '.'.join(str(p) for p in error.path)
            return f"Field '{field_path}': {error.message}"
        else:
            return f"Validation error: {error.message}"


def load_ndjson_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Convenience function to load and validate an NDJSON file.
    
    Args:
        file_path: Path to the NDJSON file
        
    Returns:
        List of validated records
        
    Raises:
        ValidationException: If validation fails
    """
    loader = NDJSONLoader()
    return loader.load_file(file_path)


def validate_ndjson_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to validate a single NDJSON record.
    
    Args:
        record: The record to validate
        
    Returns:
        Validated and normalized record
        
    Raises:
        ValidationException: If validation fails
    """
    loader = NDJSONLoader()
    return loader.validate_record(record)
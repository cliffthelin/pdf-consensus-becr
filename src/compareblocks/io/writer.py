# src/compareblocks/io/writer.py

"""
NDJSON export functionality for consensus decisions and analytics.
Ensures exported NDJSON maintains compatibility with import schema and includes all required fields.
"""

import json
from typing import List, Dict, Any, Optional, TextIO
from pathlib import Path
import jsonschema
from jsonschema import ValidationError

from .schemas import get_consensus_schema


class ExportException(Exception):
    """Exception raised when NDJSON export fails."""
    pass


class NDJSONWriter:
    """Writes consensus decisions and analytics to NDJSON format."""
    
    def __init__(self, validate_output: bool = True):
        """
        Initialize the NDJSON writer.
        
        Args:
            validate_output: Whether to validate records against schema before writing
        """
        self.validate_output = validate_output
        if validate_output:
            self.schema = get_consensus_schema()
            self.validator = jsonschema.Draft7Validator(self.schema)
    
    def write_file(self, records: List[Dict[str, Any]], file_path, overwrite: bool = False) -> None:
        """
        Write consensus records to an NDJSON file.
        
        Args:
            records: List of consensus decision records
            file_path: Output file path (str or Path)
            overwrite: Whether to overwrite existing files
            
        Raises:
            ExportException: If export fails
            FileExistsError: If file exists and overwrite=False
        """
        # Convert to Path object if string
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        if file_path.exists() and not overwrite:
            raise FileExistsError(f"Output file already exists: {file_path}")
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                self.write_stream(records, f)
        except Exception as e:
            raise ExportException(f"Failed to write NDJSON file {file_path}: {e}")
    
    def write_stream(self, records: List[Dict[str, Any]], stream: TextIO) -> None:
        """
        Write consensus records to a stream.
        
        Args:
            records: List of consensus decision records
            stream: Output stream
            
        Raises:
            ExportException: If export fails
        """
        for i, record in enumerate(records):
            try:
                # Validate record if validation is enabled
                if self.validate_output:
                    validated_record = self.validate_consensus_record(record)
                else:
                    validated_record = record
                
                # Write as single-line JSON
                json_line = json.dumps(validated_record, ensure_ascii=False, separators=(',', ':'))
                stream.write(json_line + '\n')
                
            except Exception as e:
                raise ExportException(f"Failed to write record {i}: {e}")
    
    def write_consensus_records(self, records: List[Dict[str, Any]], file_path) -> None:
        """
        Write consensus records to NDJSON file.
        
        Args:
            records: List of consensus decision records
            file_path: Output file path (str or Path)
            
        Raises:
            ExportException: If export fails
        """
        self.write_file(records, file_path, overwrite=True)
    
    def validate_consensus_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a consensus record against the output schema.
        
        Args:
            record: The consensus record to validate
            
        Returns:
            The validated record (potentially with normalized fields)
            
        Raises:
            ExportException: If validation fails
        """
        try:
            # Validate against schema
            self.validator.validate(record)
            
            # Normalize and return
            return self._normalize_consensus_record(record)
            
        except ValidationError as e:
            error_msg = self._format_validation_error(e)
            raise ExportException(f"Consensus record validation failed: {error_msg}")
    
    def _normalize_consensus_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize consensus record fields for consistent output.
        
        Args:
            record: The record to normalize
            
        Returns:
            Normalized record
        """
        normalized = record.copy()
        
        # Ensure engine_scores is a proper dict
        if 'engine_scores' in normalized:
            engine_scores = normalized['engine_scores']
            if not isinstance(engine_scores, dict):
                raise ExportException("engine_scores must be a dictionary")
            # Ensure all scores are numbers
            normalized['engine_scores'] = {k: float(v) for k, v in engine_scores.items()}
        
        # Ensure anomaly_score is a number
        if 'anomaly_score' in normalized:
            normalized['anomaly_score'] = float(normalized['anomaly_score'])
        
        # Normalize bbox if present
        if 'bbox' in normalized and normalized['bbox']:
            bbox = normalized['bbox']
            if len(bbox) != 4:
                raise ExportException(f"Bounding box must have exactly 4 elements, got {len(bbox)}")
            normalized['bbox'] = [float(x) for x in bbox]
        
        # Ensure boolean fields are proper booleans
        if 'manual_override' in normalized:
            normalized['manual_override'] = bool(normalized['manual_override'])
        
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


class AnalyticsWriter:
    """Specialized writer for analytics and reporting data."""
    
    def __init__(self):
        self.writer = NDJSONWriter(validate_output=False)  # Analytics may have flexible schema
    
    def write_analytics_report(self, analytics_data: Dict[str, Any], file_path: Path, overwrite: bool = False) -> None:
        """
        Write analytics report to NDJSON format.
        
        Args:
            analytics_data: Analytics data dictionary
            file_path: Output file path
            overwrite: Whether to overwrite existing files
            
        Raises:
            ExportException: If export fails
        """
        # Convert analytics data to list of records for NDJSON format
        records = []
        
        # Add summary record
        if 'summary' in analytics_data:
            summary_record = {
                'record_type': 'summary',
                'timestamp': analytics_data.get('timestamp'),
                **analytics_data['summary']
            }
            records.append(summary_record)
        
        # Add per-engine statistics
        if 'engine_stats' in analytics_data:
            for engine, stats in analytics_data['engine_stats'].items():
                engine_record = {
                    'record_type': 'engine_stats',
                    'engine': engine,
                    'timestamp': analytics_data.get('timestamp'),
                    **stats
                }
                records.append(engine_record)
        
        # Add per-block statistics if available
        if 'block_stats' in analytics_data:
            for block_id, stats in analytics_data['block_stats'].items():
                block_record = {
                    'record_type': 'block_stats',
                    'block_id': block_id,
                    'timestamp': analytics_data.get('timestamp'),
                    **stats
                }
                records.append(block_record)
        
        self.writer.write_file(records, file_path, overwrite)


def write_consensus_file(records: List[Dict[str, Any]], file_path: Path, overwrite: bool = False) -> None:
    """
    Convenience function to write consensus records to NDJSON file.
    
    Args:
        records: List of consensus decision records
        file_path: Output file path
        overwrite: Whether to overwrite existing files
        
    Raises:
        ExportException: If export fails
    """
    writer = NDJSONWriter()
    writer.write_file(records, file_path, overwrite)


def write_analytics_file(analytics_data: Dict[str, Any], file_path: Path, overwrite: bool = False) -> None:
    """
    Convenience function to write analytics data to NDJSON file.
    
    Args:
        analytics_data: Analytics data dictionary
        file_path: Output file path
        overwrite: Whether to overwrite existing files
        
    Raises:
        ExportException: If export fails
    """
    writer = AnalyticsWriter()
    writer.write_analytics_report(analytics_data, file_path, overwrite)
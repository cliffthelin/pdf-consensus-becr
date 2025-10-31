#!/usr/bin/env python3
"""
Comprehensive tests for io validation functionality.
Tests all functions with real data following TDD principles.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.compareblocks.io.schemas import INPUT_VARIATION_SCHEMA, CONSENSUS_OUTPUT_SCHEMA
from src.compareblocks.io.loader import NDJSONLoader, ValidationException
from src.compareblocks.io.writer import NDJSONWriter, AnalyticsWriter
import jsonschema
import tempfile
import os


class TestIoValidation:
    """Comprehensive test class for io validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures with real data."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Valid test data
        self.valid_input_variation = {
            "doc_id": "test_document",
            "page": 1,
            "engine": "tesseract",
            "raw_text": "Sample extracted text",
            "block_id": "page_1_block_1",
            "bbox": [100.0, 200.0, 300.0, 50.0],
            "confidence": 0.95,
            "orientation": 0.0,
            "metadata": {"version": "5.0"}
        }
        
        self.valid_consensus_output = {
            "doc_id": "test_document",
            "page": 1,
            "block_id": "page_1_block_1",
            "selected_engine": "tesseract",
            "final_text": "Sample extracted text",
            "decision_reason": "highest_score",
            "engine_scores": {"tesseract": 0.95, "pymupdf": 0.87},
            "anomaly_score": 0.1,
            "character_consistency_score": 0.98,
            "bbox": [100.0, 200.0, 300.0, 50.0],
            "consensus_score": 0.92,
            "variations_count": 2,
            "manual_override": False,
            "word_consistency_score": 0.96
        }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_input_variation_schema_validation(self):
        """Test INPUT_VARIATION_SCHEMA validates correctly."""
        # Test valid data passes validation
        jsonschema.validate(self.valid_input_variation, INPUT_VARIATION_SCHEMA)
        
        # Test required fields
        required_fields = ["doc_id", "page", "engine", "raw_text"]
        for field in required_fields:
            invalid_data = self.valid_input_variation.copy()
            del invalid_data[field]
            
            with pytest.raises(jsonschema.ValidationError):
                jsonschema.validate(invalid_data, INPUT_VARIATION_SCHEMA)
        
        # Test field types
        invalid_data = self.valid_input_variation.copy()
        invalid_data["page"] = "not_a_number"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_data, INPUT_VARIATION_SCHEMA)
        
        # Test bbox format
        invalid_data = self.valid_input_variation.copy()
        invalid_data["bbox"] = [100.0, 200.0]  # Too few items
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_data, INPUT_VARIATION_SCHEMA)
        
        # Test confidence range
        invalid_data = self.valid_input_variation.copy()
        invalid_data["confidence"] = 1.5  # Out of range
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_data, INPUT_VARIATION_SCHEMA)

    def test_consensus_output_schema_validation(self):
        """Test CONSENSUS_OUTPUT_SCHEMA validates correctly."""
        # Test valid data passes validation
        jsonschema.validate(self.valid_consensus_output, CONSENSUS_OUTPUT_SCHEMA)
        
        # Test required fields
        required_fields = [
            "doc_id", "page", "block_id", "selected_engine", 
            "final_text", "decision_reason", "engine_scores", 
            "anomaly_score", "character_consistency_score"
        ]
        for field in required_fields:
            invalid_data = self.valid_consensus_output.copy()
            del invalid_data[field]
            
            with pytest.raises(jsonschema.ValidationError):
                jsonschema.validate(invalid_data, CONSENSUS_OUTPUT_SCHEMA)
        
        # Test decision_reason enum
        invalid_data = self.valid_consensus_output.copy()
        invalid_data["decision_reason"] = "invalid_reason"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_data, CONSENSUS_OUTPUT_SCHEMA)
        
        # Test character_consistency_score range
        invalid_data = self.valid_consensus_output.copy()
        invalid_data["character_consistency_score"] = 1.5  # Out of range
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_data, CONSENSUS_OUTPUT_SCHEMA)

    def test_bbox_validation(self):
        """Test bounding box validation in records."""
        # Test valid bbox format
        valid_bbox = [100.0, 200.0, 300.0, 50.0]
        record_with_bbox = self.valid_input_variation.copy()
        record_with_bbox["bbox"] = valid_bbox
        
        # Should pass validation
        jsonschema.validate(record_with_bbox, INPUT_VARIATION_SCHEMA)
        
        # Test invalid bbox (wrong number of elements)
        invalid_bbox = [100.0, 200.0]  # Too few elements
        record_with_invalid_bbox = self.valid_input_variation.copy()
        record_with_invalid_bbox["bbox"] = invalid_bbox
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(record_with_invalid_bbox, INPUT_VARIATION_SCHEMA)

    def test_ndjsonloader__init_(self):
        """Test NDJSONLoader.__init__: Initialize NDJSON loader with schema validation."""
        loader = NDJSONLoader()
        assert loader.schema is not None
        assert hasattr(loader, 'validator')

    def test_ndjsonloader_validate_record(self):
        """Test NDJSONLoader.validate_record: Validate a single NDJSON record."""
        loader = NDJSONLoader()
        
        # Test valid record
        validated_record = loader.validate_record(self.valid_input_variation)
        assert validated_record is not None
        assert validated_record["doc_id"] == "test_document"
        
        # Test invalid record
        invalid_record = {"doc_id": "test"}  # Missing required fields
        with pytest.raises(ValidationException):
            loader.validate_record(invalid_record)

    def test_ndjsonloader_normalize_record(self):
        """Test NDJSONLoader.normalize_record: Normalize record fields."""
        loader = NDJSONLoader(INPUT_VARIATION_SCHEMA)
        
        # Test record with bbox as list
        record_with_list_bbox = self.valid_input_variation.copy()
        normalized = loader.normalize_record(record_with_list_bbox)
        
        assert "bbox" in normalized
        assert isinstance(normalized["bbox"], list)
        assert len(normalized["bbox"]) == 4
        
        # Test record without bbox
        record_without_bbox = self.valid_input_variation.copy()
        del record_without_bbox["bbox"]
        normalized = loader.normalize_record(record_without_bbox)
        
        assert "bbox" not in normalized or normalized["bbox"] is None

    def test_ndjsonloader_validate_mapping_requirements(self):
        """Test NDJSONLoader.validate_mapping_requirements: Validate block_id or bbox presence."""
        loader = NDJSONLoader(INPUT_VARIATION_SCHEMA)
        
        # Test record with block_id
        record_with_block_id = self.valid_input_variation.copy()
        is_valid = loader.validate_mapping_requirements(record_with_block_id)
        assert is_valid is True
        
        # Test record with bbox but no block_id
        record_with_bbox = self.valid_input_variation.copy()
        del record_with_bbox["block_id"]
        is_valid = loader.validate_mapping_requirements(record_with_bbox)
        assert is_valid is True
        
        # Test record with neither
        record_without_either = self.valid_input_variation.copy()
        del record_without_either["block_id"]
        del record_without_either["bbox"]
        is_valid = loader.validate_mapping_requirements(record_without_either)
        assert is_valid is False

    def test_ndjsonloader_format_validation_error(self):
        """Test NDJSONLoader.format_validation_error: Format validation error messages."""
        loader = NDJSONLoader(INPUT_VARIATION_SCHEMA)
        
        # Create a validation error
        try:
            jsonschema.validate({"invalid": "data"}, INPUT_VARIATION_SCHEMA)
        except jsonschema.ValidationError as e:
            formatted = loader.format_validation_error(e, line_number=5)
            
            assert "Line 5" in formatted
            assert "ValidationError" in formatted
            assert isinstance(formatted, str)

    def test_ndjsonloader_load_file(self):
        """Test NDJSONLoader.load_file: Load and validate NDJSON file."""
        loader = NDJSONLoader(INPUT_VARIATION_SCHEMA)
        
        # Create test file
        test_file = Path(self.temp_dir) / "test_input.ndjson"
        with open(test_file, 'w') as f:
            f.write(json.dumps(self.valid_input_variation) + '\n')
            f.write(json.dumps(self.valid_input_variation) + '\n')
        
        # Test loading valid file
        records = loader.load_file(str(test_file))
        assert len(records) == 2
        assert all(record["doc_id"] == "test_document" for record in records)
        
        # Test loading non-existent file
        with pytest.raises(FileNotFoundError):
            loader.load_file("non_existent_file.ndjson")

    def test_ndjsonloader_load_stream(self):
        """Test NDJSONLoader.load_stream: Load and validate NDJSON from stream."""
        loader = NDJSONLoader(INPUT_VARIATION_SCHEMA)
        
        # Create test stream
        test_data = [
            json.dumps(self.valid_input_variation),
            json.dumps(self.valid_input_variation)
        ]
        
        records = loader.load_stream(test_data)
        assert len(records) == 2
        assert all(record["doc_id"] == "test_document" for record in records)

    def test_ndjsonwriter__init_(self):
        """Test NDJSONWriter.__init__: Initialize NDJSON writer with schema validation."""
        writer = NDJSONWriter(CONSENSUS_OUTPUT_SCHEMA)
        assert writer.schema == CONSENSUS_OUTPUT_SCHEMA
        assert writer.validation_errors == []

    def test_ndjsonwriter_validate_consensus_record(self):
        """Test NDJSONWriter.validate_consensus_record: Validate consensus record."""
        writer = NDJSONWriter(CONSENSUS_OUTPUT_SCHEMA)
        
        # Test valid record
        is_valid = writer.validate_consensus_record(self.valid_consensus_output)
        assert is_valid is True
        
        # Test invalid record
        invalid_record = {"doc_id": "test"}  # Missing required fields
        is_valid = writer.validate_consensus_record(invalid_record)
        assert is_valid is False

    def test_ndjsonwriter_normalize_consensus_record(self):
        """Test NDJSONWriter.normalize_consensus_record: Normalize consensus record."""
        writer = NDJSONWriter(CONSENSUS_OUTPUT_SCHEMA)
        
        normalized = writer.normalize_consensus_record(self.valid_consensus_output)
        
        assert normalized["doc_id"] == "test_document"
        assert normalized["page"] == 1
        assert "engine_scores" in normalized
        assert isinstance(normalized["engine_scores"], dict)

    def test_ndjsonwriter_format_validation_error(self):
        """Test NDJSONWriter.format_validation_error: Format validation error messages."""
        writer = NDJSONWriter(CONSENSUS_OUTPUT_SCHEMA)
        
        # Create a validation error
        try:
            jsonschema.validate({"invalid": "data"}, CONSENSUS_OUTPUT_SCHEMA)
        except jsonschema.ValidationError as e:
            formatted = writer.format_validation_error(e, line_number=3)
            
            assert "Line 3" in formatted
            assert "ValidationError" in formatted
            assert isinstance(formatted, str)

    def test_ndjsonwriter_write_file(self):
        """Test NDJSONWriter.write_file: Write consensus records to file."""
        writer = NDJSONWriter(CONSENSUS_OUTPUT_SCHEMA)
        
        test_file = Path(self.temp_dir) / "test_output.ndjson"
        records = [self.valid_consensus_output, self.valid_consensus_output]
        
        # Test writing valid records
        writer.write_file(str(test_file), records)
        
        assert test_file.exists()
        
        # Verify file content
        with open(test_file, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        for line in lines:
            record = json.loads(line.strip())
            assert record["doc_id"] == "test_document"

    def test_ndjsonwriter_write_stream(self):
        """Test NDJSONWriter.write_stream: Write consensus records to stream."""
        writer = NDJSONWriter(CONSENSUS_OUTPUT_SCHEMA)
        
        records = [self.valid_consensus_output, self.valid_consensus_output]
        output_lines = []
        
        # Mock stream
        def mock_write(line):
            output_lines.append(line)
        
        writer.write_stream(records, mock_write)
        
        assert len(output_lines) == 2
        for line in output_lines:
            record = json.loads(line.strip())
            assert record["doc_id"] == "test_document"

    def test_analyticswriter__init_(self):
        """Test AnalyticsWriter.__init__: Initialize analytics writer."""
        writer = AnalyticsWriter()
        assert writer is not None

    def test_analyticswriter_write_analytics_report(self):
        """Test AnalyticsWriter.write_analytics_report: Write analytics report to file."""
        writer = AnalyticsWriter()
        
        test_file = Path(self.temp_dir) / "analytics.json"
        analytics_data = {
            "total_blocks": 100,
            "consensus_decisions": 95,
            "manual_overrides": 5,
            "average_confidence": 0.92
        }
        
        writer.write_analytics_report(str(test_file), analytics_data)
        
        assert test_file.exists()
        
        # Verify content
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data["total_blocks"] == 100
        assert loaded_data["consensus_decisions"] == 95

    def test_validationexception__init_(self):
        """Test ValidationException.__init__: Initialize validation exception."""
        exception = ValidationException("Test error message", line_number=5)
        
        assert str(exception) == "Test error message"
        assert exception.line_number == 5

    def test_validationexception_format_message(self):
        """Test ValidationException.format_message: Format error message with context."""
        exception = ValidationException("Test error", line_number=5)
        
        formatted = exception.format_message("additional context")
        
        assert "Test error" in formatted
        assert "Line 5" in formatted
        assert "additional context" in formatted

    def test_orientationhints__post_init_(self):
        """Test OrientationHints.__post_init__: Validate orientation hints."""
        from src.compareblocks.io.loader import OrientationHints
        
        # Test valid orientation
        hints = OrientationHints(rotation=90.0, confidence=0.95)
        assert hints.rotation == 90.0
        assert hints.confidence == 0.95
        
        # Test invalid rotation (out of range)
        with pytest.raises(ValueError, match="Rotation must be between -360 and 360"):
            OrientationHints(rotation=400.0, confidence=0.95)
        
        # Test invalid confidence (out of range)
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            OrientationHints(rotation=90.0, confidence=1.5)

    def test_get_input_schema(self):
        """Test get_input_schema: Get input validation schema."""
        from src.compareblocks.io.schemas import get_input_schema
        
        schema = get_input_schema()
        assert schema == INPUT_VARIATION_SCHEMA
        assert "required" in schema
        assert "properties" in schema

    def test_get_consensus_schema(self):
        """Test get_consensus_schema: Get consensus validation schema."""
        from src.compareblocks.io.schemas import get_consensus_schema
        
        schema = get_consensus_schema()
        assert schema == CONSENSUS_OUTPUT_SCHEMA
        assert "required" in schema
        assert "properties" in schema

    def test_validate_ndjson_record(self):
        """Test validate_ndjson_record: Validate individual NDJSON record."""
        from src.compareblocks.io.schemas import validate_ndjson_record
        
        # Test valid input record
        is_valid = validate_ndjson_record(self.valid_input_variation, INPUT_VARIATION_SCHEMA)
        assert is_valid is True
        
        # Test invalid record
        invalid_record = {"doc_id": "test"}  # Missing required fields
        is_valid = validate_ndjson_record(invalid_record, INPUT_VARIATION_SCHEMA)
        assert is_valid is False

    def test_load_ndjson_file(self):
        """Test load_ndjson_file: Load and validate NDJSON file."""
        from src.compareblocks.io.schemas import load_ndjson_file
        
        # Create test file
        test_file = Path(self.temp_dir) / "test.ndjson"
        with open(test_file, 'w') as f:
            f.write(json.dumps(self.valid_input_variation) + '\n')
        
        records = load_ndjson_file(str(test_file), INPUT_VARIATION_SCHEMA)
        assert len(records) == 1
        assert records[0]["doc_id"] == "test_document"

    def test_write_consensus_file(self):
        """Test write_consensus_file: Write consensus records to file."""
        from src.compareblocks.io.schemas import write_consensus_file
        
        test_file = Path(self.temp_dir) / "consensus.ndjson"
        records = [self.valid_consensus_output]
        
        write_consensus_file(str(test_file), records)
        
        assert test_file.exists()
        
        # Verify content
        with open(test_file, 'r') as f:
            line = f.readline().strip()
            record = json.loads(line)
        
        assert record["doc_id"] == "test_document"

    def test_write_analytics_file(self):
        """Test write_analytics_file: Write analytics data to file."""
        from src.compareblocks.io.schemas import write_analytics_file
        
        test_file = Path(self.temp_dir) / "analytics.json"
        analytics_data = {"total_blocks": 50, "accuracy": 0.95}
        
        write_analytics_file(str(test_file), analytics_data)
        
        assert test_file.exists()
        
        # Verify content
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data["total_blocks"] == 50
        assert loaded_data["accuracy"] == 0.95
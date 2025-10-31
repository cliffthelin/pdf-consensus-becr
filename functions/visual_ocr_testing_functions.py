#!/usr/bin/env python3
"""
Visual OCR Testing Tool Functions Catalog

This module contains all the functions and classes from the Visual OCR Testing Tool
for inclusion in the functions catalog. These functions provide comprehensive
OCR testing, optimization, and multi-input feed capabilities.

Functions included:
- Input feed management
- JSON browsing and validation
- Source_docs integration
- Configuration management
- Database operations
- OCR optimization
- Test result tracking
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict


@dataclass
class InputFeedConfig:
    """
    Configuration for input feed sources.
    
    Attributes:
        name: Unique name for the feed
        type: Feed type ('mcp', 'json', 'api', 'file', 'database', 'code')
        source: Source path or URL for the feed
        enabled: Whether the feed is active
        refresh_interval: Refresh interval in seconds
        parameters: Additional parameters for the feed
    
    Example:
        config = InputFeedConfig(
            name="gbg_analysis",
            type="json",
            source="Source_docs/English Language Arts Standards/Processing_Inprogress/gbg_full_analysis.json",
            enabled=True,
            refresh_interval=60,
            parameters={"auto_discovered": True}
        )
    """
    name: str
    type: str  # 'mcp', 'json', 'api', 'file', 'database', 'code'
    source: str
    enabled: bool = True
    refresh_interval: int = 30  # seconds
    parameters: Dict[str, Any] = None


@dataclass
class TestResult:
    """
    Standardized test result structure for OCR testing.
    
    Attributes:
        timestamp: When the test was performed
        source: Source of the test (e.g., 'cli_optimization', 'gui_testing')
        test_type: Type of test performed
        page_num: PDF page number tested
        block_index: Block index within the page
        similarity: Similarity score (0-100) between expected and actual text
        confidence: OCR confidence score (0-1)
        extracted_text: Text extracted by OCR
        expected_text: Expected text from reference
        preprocessing: Preprocessing method used
        tesseract_config: Tesseract configuration used
        success: Whether the test was successful
        metadata: Additional test metadata
    
    Example:
        result = TestResult(
            timestamp=datetime.now(),
            source="ocr_optimization",
            test_type="parameter_testing",
            page_num=15,
            block_index=0,
            similarity=98.0,
            confidence=0.95,
            extracted_text="UTAH STATE STANDARDS for P-12 ENGLISH LANGUAGE ARTS",
            expected_text="UTAH STATE STANDARDS for P–12 ENGLISH LANGUAGE ARTS",
            preprocessing="light",
            tesseract_config="--psm 6",
            success=True,
            metadata={"optimization_round": 1}
        )
    """
    timestamp: datetime
    source: str
    test_type: str
    page_num: int
    block_index: int
    similarity: float
    confidence: float
    extracted_text: str
    expected_text: str
    preprocessing: str
    tesseract_config: str
    success: bool
    metadata: Dict[str, Any] = None


def validate_json_format(data: Any) -> Dict[str, Any]:
    """
    Validate JSON format and return validation result with examples.
    
    Args:
        data: Parsed JSON data to validate
        
    Returns:
        Dictionary with validation results:
        - valid: Boolean indicating if format is valid
        - type: Detected JSON type
        - error: Error message if invalid
        - example: Example of correct format if invalid
    
    Example:
        # Valid GBG analysis JSON
        gbg_data = {
            "pages": {"0": {"blocks": []}},
            "summary": {"total_pages": 1}
        }
        result = validate_json_format(gbg_data)
        # Returns: {"valid": True, "type": "gbg_analysis"}
        
        # Invalid JSON missing required fields
        invalid_data = {"random": "data"}
        result = validate_json_format(invalid_data)
        # Returns: {"valid": True, "type": "configuration"}
    """
    try:
        if isinstance(data, dict):
            if "pages" in data and "summary" in data:
                return validate_gbg_json_format(data)
            elif "corrections" in data or "verified" in data:
                return {"valid": True, "type": "corrections_data"}
            elif "doc_id" in str(data)[:200]:  # Quick check for doc_id
                return {"valid": True, "type": "processing_results"}
            else:
                return {"valid": True, "type": "configuration"}
        elif isinstance(data, list):
            if data and isinstance(data[0], dict) and "doc_id" in data[0]:
                return validate_consensus_json_format(data)
            else:
                return {"valid": True, "type": "list_data"}
        else:
            return {
                "valid": False, 
                "error": "JSON must be an object {} or array []", 
                "type": "invalid_root_type",
                "example": {"valid_object": "example"} 
            }
    except Exception as e:
        return {"valid": False, "error": str(e), "type": "validation_error"}


def validate_gbg_json_format(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate GBG analysis JSON format with detailed examples.
    
    Args:
        data: Dictionary containing GBG analysis data
        
    Returns:
        Dictionary with validation results and examples if invalid
    
    Example:
        # Valid GBG data
        gbg_data = {
            "pdf_name": "document.pdf",
            "summary": {"total_pages": 10, "total_blocks": 100},
            "pages": {
                "0": {
                    "blocks": [
                        {
                            "block_id": "blk_123",
                            "text_content": "Sample text",
                            "bbox": {"x": 0, "y": 0, "width": 100, "height": 20}
                        }
                    ]
                }
            }
        }
        result = validate_gbg_json_format(gbg_data)
        # Returns: {"valid": True, "type": "gbg_analysis"}
    """
    required_fields = ["pages", "summary"]
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        example = {
            "pdf_name": "English Language Arts Standards.pdf",
            "summary": {
                "total_pages": 62,
                "total_blocks": 1066,
                "extraction_engine": "PyMuPDF",
                "processing_type": "gbg_analysis"
            },
            "pages": {
                "0": {
                    "page_number": 0,
                    "blocks": [
                        {
                            "block_id": "blk_27e0e0e663d732b0",
                            "text_content": "UTAH STATE STANDARDS for P–12 ENGLISH LANGUAGE ARTS",
                            "bbox": {
                                "x": 72.0,
                                "y": 72.0,
                                "width": 451.2,
                                "height": 36.0
                            },
                            "orientation_hints": {
                                "confidence": 0.95,
                                "angle": 0
                            }
                        }
                    ]
                }
            }
        }
        
        return {
            "valid": False,
            "error": f"Missing required fields for GBG analysis: {', '.join(missing_fields)}",
            "type": "gbg_analysis",
            "example": example
        }
    
    # Validate pages structure
    if not isinstance(data["pages"], dict):
        return {
            "valid": False,
            "error": "Field 'pages' must be a dictionary with page numbers as keys",
            "type": "gbg_analysis",
            "example": {"pages": {"0": {"blocks": []}, "1": {"blocks": []}}}
        }
    
    # Validate summary structure
    if not isinstance(data["summary"], dict):
        return {
            "valid": False,
            "error": "Field 'summary' must be a dictionary with metadata",
            "type": "gbg_analysis",
            "example": {"summary": {"total_pages": 10, "total_blocks": 100}}
        }
    
    return {"valid": True, "type": "gbg_analysis"}


def validate_consensus_json_format(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate consensus decisions JSON format with detailed examples.
    
    Args:
        data: List of consensus decision dictionaries
        
    Returns:
        Dictionary with validation results and examples if invalid
    
    Example:
        # Valid consensus data
        consensus_data = [
            {
                "doc_id": "document.pdf",
                "page": 1,
                "block_id": "blk_123",
                "selected_engine": "tesseract",
                "final_text": "Sample text",
                "decision_reason": "highest_score",
                "engine_scores": {"tesseract": 0.95},
                "anomaly_score": 0.05,
                "bbox": [0, 0, 100, 20]
            }
        ]
        result = validate_consensus_json_format(consensus_data)
        # Returns: {"valid": True, "type": "consensus_decisions"}
    """
    if not isinstance(data, list) or not data:
        return {
            "valid": False,
            "error": "Consensus data must be a non-empty array of decision objects",
            "type": "consensus_decisions",
            "example": [{"doc_id": "document.pdf", "page": 1, "block_id": "blk_123"}]
        }
    
    required_fields = ["doc_id", "page", "block_id", "selected_engine", "final_text"]
    first_item = data[0]
    missing_fields = [field for field in required_fields if field not in first_item]
    
    if missing_fields:
        example = [
            {
                "doc_id": "English Language Arts Standards.pdf",
                "page": 15,
                "block_id": "blk_27e0e0e663d732b0",
                "selected_engine": "tesseract",
                "final_text": "UTAH STATE STANDARDS for P–12 ENGLISH LANGUAGE ARTS",
                "decision_reason": "highest_score",
                "engine_scores": {
                    "tesseract": 0.95,
                    "pymupdf": 0.87
                },
                "anomaly_score": 0.05,
                "bbox": [72.0, 72.0, 451.2, 36.0]
            }
        ]
        
        return {
            "valid": False,
            "error": f"Missing required fields for consensus decisions: {', '.join(missing_fields)}",
            "type": "consensus_decisions",
            "example": example
        }
    
    return {"valid": True, "type": "consensus_decisions"}


def discover_source_docs_json_files(source_docs_path: str = "Source_docs") -> List[Dict[str, Any]]:
    """
    Discover JSON files in Source_docs directory recursively.
    
    Args:
        source_docs_path: Path to Source_docs directory
        
    Returns:
        List of dictionaries containing file information:
        - path: Full path to the file
        - relative_path: Path relative to Source_docs
        - size: File size in bytes
        - modified: Last modification datetime
        - type: Detected file type based on name patterns
    
    Example:
        files = discover_source_docs_json_files()
        for file_info in files:
            print(f"Found: {file_info['relative_path']} ({file_info['type']})")
    """
    source_docs = Path(source_docs_path)
    if not source_docs.exists():
        return []
    
    discovered_files = []
    
    # Important patterns to look for
    important_patterns = [
        "**/gbg_full_analysis.json",
        "**/consensus_decisions.ndjson", 
        "**/*_corrections*.json",
        "**/*_verified*.json",
        "**/*_diff_decisions*.json"
    ]
    
    # Find all JSON files
    all_json_files = list(source_docs.rglob("*.json"))
    
    for json_file in all_json_files:
        try:
            stat = json_file.stat()
            relative_path = json_file.relative_to(source_docs)
            
            # Determine file type based on name patterns
            file_type = "unknown"
            file_stem = json_file.stem.lower()
            
            if "gbg_full_analysis" in file_stem:
                file_type = "gbg_analysis"
            elif "consensus" in file_stem:
                file_type = "consensus_decisions"
            elif "corrections" in file_stem:
                file_type = "corrections"
            elif "verified" in file_stem:
                file_type = "verified"
            elif "diff_decisions" in file_stem:
                file_type = "diff_decisions"
            else:
                file_type = "configuration"
            
            file_info = {
                "path": str(json_file),
                "relative_path": str(relative_path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "type": file_type,
                "directory": str(relative_path.parent),
                "filename": json_file.name
            }
            
            discovered_files.append(file_info)
            
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    # Sort by type and then by path
    discovered_files.sort(key=lambda x: (x["type"], x["relative_path"]))
    
    return discovered_files


def create_input_feed_config(name: str, file_path: str, feed_type: str = None) -> InputFeedConfig:
    """
    Create an InputFeedConfig from a file path with automatic type detection.
    
    Args:
        name: Name for the feed
        file_path: Path to the file or directory
        feed_type: Override automatic type detection
        
    Returns:
        InputFeedConfig object ready for use
    
    Example:
        # Auto-detect JSON feed
        config = create_input_feed_config(
            "gbg_analysis",
            "Source_docs/English Language Arts Standards/Processing_Inprogress/gbg_full_analysis.json"
        )
        
        # Override type detection
        config = create_input_feed_config(
            "custom_api",
            "http://api.example.com/data",
            feed_type="api"
        )
    """
    path = Path(file_path)
    
    # Auto-detect feed type if not provided
    if feed_type is None:
        if path.suffix == ".json":
            feed_type = "json"
        elif path.suffix == ".db" or path.suffix == ".sqlite":
            feed_type = "database"
        elif path.is_dir():
            feed_type = "file"
        elif file_path.startswith("http"):
            feed_type = "api"
        else:
            feed_type = "file"
    
    # Determine appropriate refresh interval based on type
    refresh_intervals = {
        "json": 60,      # JSON files change less frequently
        "file": 30,      # File system monitoring
        "api": 120,      # API calls should be less frequent
        "database": 90,  # Database queries
        "code": 300,     # Code execution
        "mcp": 60        # MCP configuration
    }
    
    refresh_interval = refresh_intervals.get(feed_type, 60)
    
    # Create parameters based on file type
    parameters = {}
    
    if feed_type == "json" and path.exists():
        # Add metadata for JSON files
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
                validation = validate_json_format(data)
                
                parameters = {
                    "file_size": len(content),
                    "json_type": validation["type"],
                    "valid_format": validation["valid"],
                    "auto_created": True
                }
        except Exception:
            parameters = {"auto_created": True, "parse_error": True}
    
    return InputFeedConfig(
        name=name,
        type=feed_type,
        source=str(file_path),
        enabled=True,
        refresh_interval=refresh_interval,
        parameters=parameters
    )


def load_and_validate_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load and validate a JSON file with comprehensive error handling.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary with loading results:
        - success: Boolean indicating if loading was successful
        - data: Parsed JSON data if successful
        - error: Error message if unsuccessful
        - validation: Validation results
        - file_info: File metadata
    
    Example:
        result = load_and_validate_json_file("config.json")
        if result["success"]:
            data = result["data"]
            print(f"Loaded {result['validation']['type']} with {len(data)} items")
        else:
            print(f"Error: {result['error']}")
    """
    file_path = Path(file_path)
    
    result = {
        "success": False,
        "data": None,
        "error": None,
        "validation": None,
        "file_info": {}
    }
    
    # Check if file exists
    if not file_path.exists():
        result["error"] = f"File not found: {file_path}"
        return result
    
    try:
        # Get file info
        stat = file_path.stat()
        result["file_info"] = {
            "path": str(file_path),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "name": file_path.name
        }
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse JSON
        try:
            data = json.loads(content)
            result["data"] = data
            
            # Validate format
            validation = validate_json_format(data)
            result["validation"] = validation
            
            if validation["valid"]:
                result["success"] = True
            else:
                result["error"] = f"Invalid JSON structure: {validation['error']}"
                
        except json.JSONDecodeError as e:
            result["error"] = f"JSON syntax error: {str(e)}"
            if hasattr(e, 'lineno'):
                result["error"] += f" (line {e.lineno}, column {e.colno})"
                
    except Exception as e:
        result["error"] = f"File reading error: {str(e)}"
    
    return result


def create_test_result_database(db_path: str = "output/ocr_test_results.db") -> bool:
    """
    Create and initialize a test results database.
    
    Args:
        db_path: Path where the database should be created
        
    Returns:
        Boolean indicating if database was created successfully
    
    Example:
        success = create_test_result_database("test_results.db")
        if success:
            print("Database created successfully")
    """
    try:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create test_results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                test_type TEXT NOT NULL,
                page_num INTEGER,
                block_index INTEGER,
                similarity REAL,
                confidence REAL,
                extracted_text TEXT,
                expected_text TEXT,
                preprocessing TEXT,
                tesseract_config TEXT,
                success BOOLEAN,
                metadata TEXT
            )
        ''')
        
        # Create feed_data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feed_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                feed_name TEXT NOT NULL,
                feed_type TEXT NOT NULL,
                data TEXT NOT NULL
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_results_timestamp ON test_results(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_results_type ON test_results(test_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_data_name ON feed_data(feed_name)')
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error creating database: {e}")
        return False


def save_test_result_to_database(result: TestResult, db_path: str = "output/ocr_test_results.db") -> bool:
    """
    Save a test result to the database.
    
    Args:
        result: TestResult object to save
        db_path: Path to the database
        
    Returns:
        Boolean indicating if save was successful
    
    Example:
        result = TestResult(
            timestamp=datetime.now(),
            source="optimization_test",
            test_type="parameter_testing",
            page_num=15,
            block_index=0,
            similarity=98.0,
            confidence=0.95,
            extracted_text="Test text",
            expected_text="Expected text",
            preprocessing="light",
            tesseract_config="--psm 6",
            success=True
        )
        
        success = save_test_result_to_database(result)
        if success:
            print("Test result saved successfully")
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO test_results 
            (timestamp, source, test_type, page_num, block_index, similarity, 
             confidence, extracted_text, expected_text, preprocessing, 
             tesseract_config, success, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.timestamp.isoformat(),
            result.source,
            result.test_type,
            result.page_num,
            result.block_index,
            result.similarity,
            result.confidence,
            result.extracted_text,
            result.expected_text,
            result.preprocessing,
            result.tesseract_config,
            result.success,
            json.dumps(result.metadata) if result.metadata else None
        ))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error saving test result: {e}")
        return False


def get_test_results_from_database(db_path: str = "output/ocr_test_results.db", 
                                 limit: int = 100, 
                                 test_type: str = None) -> List[TestResult]:
    """
    Retrieve test results from the database.
    
    Args:
        db_path: Path to the database
        limit: Maximum number of results to return
        test_type: Filter by test type (optional)
        
    Returns:
        List of TestResult objects
    
    Example:
        # Get all recent results
        results = get_test_results_from_database(limit=50)
        
        # Get only optimization results
        opt_results = get_test_results_from_database(
            test_type="ocr_optimization",
            limit=20
        )
        
        for result in results:
            print(f"{result.timestamp}: {result.similarity}% similarity")
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM test_results"
        params = []
        
        if test_type:
            query += " WHERE test_type = ?"
            params.append(test_type)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            metadata = json.loads(row[13]) if row[13] else None
            result = TestResult(
                timestamp=datetime.fromisoformat(row[1]),
                source=row[2],
                test_type=row[3],
                page_num=row[4],
                block_index=row[5],
                similarity=row[6],
                confidence=row[7],
                extracted_text=row[8],
                expected_text=row[9],
                preprocessing=row[10],
                tesseract_config=row[11],
                success=bool(row[12]),
                metadata=metadata
            )
            results.append(result)
            
        conn.close()
        return results
        
    except Exception as e:
        print(f"Error retrieving test results: {e}")
        return []


# Example usage and testing functions
def example_usage():
    """
    Example usage of the Visual OCR Testing Tool functions.
    
    This function demonstrates how to use the various functions
    for JSON validation, feed management, and database operations.
    """
    print("Visual OCR Testing Tool Functions - Example Usage")
    print("=" * 60)
    
    # 1. Discover Source_docs JSON files
    print("\n1. Discovering Source_docs JSON files...")
    json_files = discover_source_docs_json_files()
    print(f"Found {len(json_files)} JSON files:")
    for file_info in json_files[:3]:  # Show first 3
        print(f"   - {file_info['relative_path']} ({file_info['type']})")
    
    # 2. Create input feed configurations
    print("\n2. Creating input feed configurations...")
    if json_files:
        config = create_input_feed_config(
            "example_gbg_feed",
            json_files[0]["path"]
        )
        print(f"Created feed: {config.name} ({config.type})")
    
    # 3. Validate JSON format
    print("\n3. Validating JSON formats...")
    test_data = {
        "pages": {"0": {"blocks": []}},
        "summary": {"total_pages": 1}
    }
    validation = validate_json_format(test_data)
    print(f"Validation result: {validation['type']} (valid: {validation['valid']})")
    
    # 4. Create test result
    print("\n4. Creating test result...")
    result = TestResult(
        timestamp=datetime.now(),
        source="example_test",
        test_type="function_demo",
        page_num=15,
        block_index=0,
        similarity=95.5,
        confidence=0.92,
        extracted_text="Example text",
        expected_text="Expected text",
        preprocessing="light",
        tesseract_config="--psm 6",
        success=True,
        metadata={"demo": True}
    )
    print(f"Created test result: {result.similarity}% similarity")
    
    # 5. Database operations
    print("\n5. Database operations...")
    db_created = create_test_result_database("example_test.db")
    if db_created:
        saved = save_test_result_to_database(result, "example_test.db")
        if saved:
            retrieved = get_test_results_from_database("example_test.db", limit=1)
            print(f"Database operations successful: {len(retrieved)} results retrieved")
    
    print("\nExample usage completed!")


if __name__ == "__main__":
    example_usage()
# BECR Utility Files Index

This document provides a comprehensive index of all utility files in the BECR project that serve ongoing operational purposes for processes, troubleshooting, and system maintenance.

## Application Entry Points

### `run_becr.py`
**Path:** `./run_becr.py`
**Purpose:** Immutable entry point for the main BECR GUI application
**Description:** Primary launcher that initializes the PySide6 GUI interface for PDF text extraction comparison and review. This entry point never changes to ensure system stability and provides a consistent way to start the application regardless of environment setup.

### `run_tests.py`
**Path:** `./run_tests.py`
**Purpose:** Immutable entry point for the complete test suite
**Description:** Standardized test runner that executes the full pytest suite with proper coverage reporting. Ensures consistent test execution across different environments and maintains the TDD workflow requirements.

### `src/compareblocks/utils/test_runner.py`
**Path:** `./src/compareblocks/utils/test_runner.py`
**Purpose:** Internal test execution utilities
**Description:** Provides programmatic test running capabilities for internal system validation and automated testing workflows. Used by other components that need to trigger test execution programmatically.

## Processing & Analysis Tools

### `optimize_tesseract_for_clear_text.py`
**Path:** `./optimize_tesseract_for_clear_text.py`
**Purpose:** Tesseract OCR optimization for high-quality text documents
**Description:** Analyzes and optimizes Tesseract OCR settings specifically for clear, high-quality text documents. Provides parameter tuning recommendations and performance benchmarking for different document types. Essential for achieving optimal OCR accuracy on clean documents.

### `process_all_engines_gbg.py`
**Path:** `./process_all_engines_gbg.py`
**Purpose:** Comprehensive engine processing with Global Block Grid integration
**Description:** Orchestrates processing across all available OCR engines while maintaining GBG block alignment. Handles multi-engine workflows, result aggregation, and ensures consistent block-level comparison across different extraction methods. Critical for full-system validation and performance testing.

### `visual_ocr_testing_tool.py`
**Path:** `./visual_ocr_testing_tool.py`
**Purpose:** Visual debugging and testing interface for OCR results
**Description:** Interactive tool for visually inspecting OCR extraction results, comparing engine outputs side-by-side, and debugging spatial alignment issues. Provides image overlays, block highlighting, and detailed extraction metrics for troubleshooting OCR accuracy problems.

## Validation & Monitoring Tools

### `show_remaining_issues.py`
**Path:** `./show_remaining_issues.py`
**Purpose:** System health monitoring and issue identification
**Description:** Scans the entire codebase for remaining issues, missing tests, configuration problems, and potential system inconsistencies. Provides comprehensive health reports and identifies areas requiring attention for maintenance and improvement.

### `validate_configuration.py`
**Path:** `./validate_configuration.py`
**Purpose:** Configuration validation and consistency checking
**Description:** Validates all system configuration files including engine settings, file paths, schema definitions, and runtime parameters. Ensures configuration consistency across different environments and identifies potential configuration conflicts or missing settings.

### `validate_function_catalog.py`
**Path:** `./validate_function_catalog.py`
**Purpose:** Function catalog integrity validation
**Description:** Validates the function catalog NDJSON structure, ensures all documented functions exist in the codebase, and verifies catalog completeness. Critical for maintaining accurate documentation and MCP integration functionality.

### `validate_setup.py`
**Path:** `./validate_setup.py`
**Purpose:** Complete system setup validation
**Description:** Comprehensive validation of the entire BECR system setup including dependencies, file structure, configuration files, test environment, and runtime requirements. Provides detailed setup diagnostics and identifies missing components or configuration issues.

## Function Analysis & Management Tools

### `functions/analyze_project_test_coverage.py`
**Path:** `./functions/analyze_project_test_coverage.py`
**Purpose:** Test coverage analysis and reporting
**Description:** Analyzes test coverage across the entire project, identifies untested functions and modules, generates coverage reports, and provides recommendations for improving test coverage. Essential for maintaining the 95%+ coverage requirement and TDD compliance.

### `functions/detect_missing_functions.py`
**Path:** `./functions/detect_missing_functions.py`
**Purpose:** Missing function detection and catalog maintenance
**Description:** Scans the codebase to identify functions that exist in code but are missing from the function catalog, and vice versa. Helps maintain catalog accuracy and ensures all functionality is properly documented and accessible via MCP integration.

### `functions/enhance_catalog_fields.py`
**Path:** `./functions/enhance_catalog_fields.py`
**Purpose:** Function catalog field enhancement and metadata management
**Description:** Enhances the function catalog with additional metadata fields, improves function descriptions, adds parameter documentation, and ensures catalog entries contain comprehensive information for MCP integration and system documentation.

### `functions/run_mcp_tests.py`
**Path:** `./functions/run_mcp_tests.py`
**Purpose:** MCP integration testing and validation
**Description:** Specialized test runner for Model Context Protocol integration functionality. Validates MCP server communication, function catalog accessibility, and ensures proper integration between BECR and external MCP clients.

### `functions/validate_catalog.py`
**Path:** `./functions/validate_catalog.py`
**Purpose:** Function catalog validation and consistency checking
**Description:** Validates the structure, format, and content of the function catalog NDJSON file. Ensures all entries conform to the expected schema, validates function signatures, and checks for catalog consistency with the actual codebase.

### `functions/visual_ocr_testing_functions.py`
**Path:** `./functions/visual_ocr_testing_functions.py`
**Purpose:** Visual OCR testing function library
**Description:** Collection of specialized functions for visual OCR testing, debugging, and analysis. Provides utilities for image processing, result visualization, spatial analysis, and comparative testing across different OCR engines. Used by the visual testing tool and other debugging utilities.

## Usage Guidelines

### Regular Maintenance
- Run `show_remaining_issues.py` weekly to monitor system health
- Use `validate_setup.py` after environment changes or updates
- Execute `validate_configuration.py` when modifying system settings

### Development Workflow
- Use `run_tests.py` for all test execution (never run pytest directly)
- Run `functions/analyze_project_test_coverage.py` before releases
- Validate function catalog with `functions/validate_catalog.py` after adding new functions

### Troubleshooting
- Use `visual_ocr_testing_tool.py` for OCR accuracy issues
- Run `optimize_tesseract_for_clear_text.py` for Tesseract performance problems
- Execute `process_all_engines_gbg.py` for comprehensive engine testing

### System Integration
- Use `functions/run_mcp_tests.py` for MCP integration validation
- Run `validate_function_catalog.py` before MCP server deployment
- Execute `functions/detect_missing_functions.py` after major code changes

All utility files follow the project's TDD principles and use real data rather than mocks or stubs. They are designed to work with the actual system configuration and provide accurate, actionable information for system maintenance and troubleshooting.
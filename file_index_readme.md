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


## Processing & Analysis Tools

### `build_test_catalog.py`
**Path:** `./build_test_catalog.py`
**Purpose:** Test catalog generation and cross-referencing system
**Description:** Command-line utility with main entry point. Contains 8 utility functions. Implements 1 classes. Provides testing utilities and framework integration. Essential for system functionality and workflow integration.

### `src/compareblocks/gbg/processor.py`
**Path:** `./src/compareblocks/gbg/processor.py`
**Purpose:** Data processing pipeline and workflow management
**Description:** Command-line utility with main entry point. Contains 1 utility functions. Implements 1 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/gui/app.py`
**Path:** `./src/compareblocks/gui/app.py`
**Purpose:** Core functionality for app
**Description:** Command-line utility with main entry point. Contains 3 utility functions. Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/gui/review_gui.py`
**Path:** `./src/compareblocks/gui/review_gui.py`
**Purpose:** User interface components and interactions
**Description:** Command-line utility with main entry point. Contains 1 utility functions. Implements 2 classes. Implements user interface components with PySide6 integration. Essential for system functionality and workflow integration.


## Validation & Monitoring Tools

### `analyze_missing_files_and_functions.py`
**Path:** `./analyze_missing_files_and_functions.py`
**Purpose:** Project analysis for missing files and function coverage
**Description:** Contains 7 utility functions. Implements 1 classes. Essential for system functionality and workflow integration.

### `analyze_missing_functions.py`
**Path:** `./analyze_missing_functions.py`
**Purpose:** Core functionality for analyze missing functions
**Description:** Essential for system functionality and workflow integration.

### `conftest_unit_fix.py`
**Path:** `./conftest_unit_fix.py`
**Purpose:** Testing utilities and framework support
**Description:** Provides testing utilities and framework integration. Essential for system functionality and workflow integration.

### `extract_block_images.py`
**Path:** `./extract_block_images.py`
**Purpose:** Core functionality for extract block images
**Description:** Essential for system functionality and workflow integration.

### `functions/__init__.py`
**Path:** `./functions/__init__.py`
**Purpose:** Core functionality for   init  
**Description:** Essential for system functionality and workflow integration.

### `functions/reconstruct_catalog.py`
**Path:** `./functions/reconstruct_catalog.py`
**Purpose:** Core functionality for reconstruct catalog
**Description:** Essential for system functionality and workflow integration.

### `src/compareblocks/analytics/dashboard.py`
**Path:** `./src/compareblocks/analytics/dashboard.py`
**Purpose:** Core functionality for dashboard
**Description:** Contains 2 utility functions. Implements 1 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/analytics/engine_analytics.py`
**Path:** `./src/compareblocks/analytics/engine_analytics.py`
**Purpose:** OCR engine implementation and integration
**Description:** Contains 2 utility functions. Implements 2 classes. Provides OCR engine integration with standardized interface and error handling. Essential for system functionality and workflow integration.

### `src/compareblocks/analytics/export.py`
**Path:** `./src/compareblocks/analytics/export.py`
**Purpose:** Core functionality for export
**Description:** Contains 2 utility functions. Implements 1 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/analytics/report_generator.py`
**Path:** `./src/compareblocks/analytics/report_generator.py`
**Purpose:** Core functionality for report generator
**Description:** Contains 2 utility functions. Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/association/alignment.py`
**Path:** `./src/compareblocks/association/alignment.py`
**Purpose:** Core functionality for alignment
**Description:** Contains 2 utility functions. Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/association/manager.py`
**Path:** `./src/compareblocks/association/manager.py`
**Purpose:** Resource and workflow management functionality
**Description:** Contains 2 utility functions. Implements 3 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/association/parsers.py`
**Path:** `./src/compareblocks/association/parsers.py`
**Purpose:** Core functionality for parsers
**Description:** Contains 4 utility functions. Implements 7 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/association/pymupdf_matcher.py`
**Path:** `./src/compareblocks/association/pymupdf_matcher.py`
**Purpose:** Block matching and spatial alignment algorithms
**Description:** Contains 1 utility functions. Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/association/tesseract_matcher.py`
**Path:** `./src/compareblocks/association/tesseract_matcher.py`
**Purpose:** Block matching and spatial alignment algorithms
**Description:** Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/config/engine_config.py`
**Path:** `./src/compareblocks/config/engine_config.py`
**Purpose:** OCR engine implementation and integration
**Description:** Implements 7 classes. Provides OCR engine integration with standardized interface and error handling. Essential for system functionality and workflow integration.

### `src/compareblocks/config/file_manager.py`
**Path:** `./src/compareblocks/config/file_manager.py`
**Purpose:** Resource and workflow management functionality
**Description:** Contains 5 utility functions. Implements 1 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/consensus/guard.py`
**Path:** `./src/compareblocks/consensus/guard.py`
**Purpose:** Core functionality for guard
**Description:** Contains 6 utility functions. Implements 3 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/consensus/merge.py`
**Path:** `./src/compareblocks/consensus/merge.py`
**Purpose:** Core functionality for merge
**Description:** Contains 7 utility functions. Implements 4 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/consensus/policy.py`
**Path:** `./src/compareblocks/consensus/policy.py`
**Purpose:** Core functionality for policy
**Description:** Contains 8 utility functions. Implements 4 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/consensus/score.py`
**Path:** `./src/compareblocks/consensus/score.py`
**Purpose:** Core functionality for score
**Description:** Contains 9 utility functions. Implements 4 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/debug/image_extractor.py`
**Path:** `./src/compareblocks/debug/image_extractor.py`
**Purpose:** Core functionality for image extractor
**Description:** Contains 1 utility functions. Implements 1 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/comprehensive_engine_gbg_processor.py`
**Path:** `./src/compareblocks/engines/comprehensive_engine_gbg_processor.py`
**Purpose:** OCR engine implementation and integration
**Description:** Contains 3 utility functions. Implements 5 classes. Provides OCR engine integration with standardized interface and error handling. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/docling_engine.py`
**Path:** `./src/compareblocks/engines/docling_engine.py`
**Purpose:** OCR engine implementation and integration
**Description:** Contains 2 utility functions. Implements 3 classes. Provides OCR engine integration with standardized interface and error handling. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/dual_output_processor.py`
**Path:** `./src/compareblocks/engines/dual_output_processor.py`
**Purpose:** Data processing pipeline and workflow management
**Description:** Contains 2 utility functions. Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/gbg_guided_tesseract_engine.py`
**Path:** `./src/compareblocks/engines/gbg_guided_tesseract_engine.py`
**Purpose:** OCR engine implementation and integration
**Description:** Implements 3 classes. Provides OCR engine integration with standardized interface and error handling. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/gbg_integrated_processor.py`
**Path:** `./src/compareblocks/engines/gbg_integrated_processor.py`
**Purpose:** Data processing pipeline and workflow management
**Description:** Contains 1 utility functions. Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/integrated_processor.py`
**Path:** `./src/compareblocks/engines/integrated_processor.py`
**Purpose:** Data processing pipeline and workflow management
**Description:** Contains 2 utility functions. Implements 3 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/kreuzberg_engine.py`
**Path:** `./src/compareblocks/engines/kreuzberg_engine.py`
**Purpose:** OCR engine implementation and integration
**Description:** Contains 2 utility functions. Implements 3 classes. Provides OCR engine integration with standardized interface and error handling. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/manager.py`
**Path:** `./src/compareblocks/engines/manager.py`
**Purpose:** Resource and workflow management functionality
**Description:** Contains 3 utility functions. Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/paddleocr_engine.py`
**Path:** `./src/compareblocks/engines/paddleocr_engine.py`
**Purpose:** OCR engine implementation and integration
**Description:** Contains 2 utility functions. Implements 3 classes. Provides OCR engine integration with standardized interface and error handling. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/pymupdf_engine.py`
**Path:** `./src/compareblocks/engines/pymupdf_engine.py`
**Purpose:** OCR engine implementation and integration
**Description:** Contains 2 utility functions. Implements 3 classes. Provides OCR engine integration with standardized interface and error handling. Essential for system functionality and workflow integration.

### `src/compareblocks/engines/tesseract_engine.py`
**Path:** `./src/compareblocks/engines/tesseract_engine.py`
**Purpose:** OCR engine implementation and integration
**Description:** Contains 2 utility functions. Implements 3 classes. Provides OCR engine integration with standardized interface and error handling. Essential for system functionality and workflow integration.

### `src/compareblocks/features/anomaly.py`
**Path:** `./src/compareblocks/features/anomaly.py`
**Purpose:** Core functionality for anomaly
**Description:** Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/features/consistency.py`
**Path:** `./src/compareblocks/features/consistency.py`
**Purpose:** Text consistency tracking and validation
**Description:** Contains 3 utility functions. Implements 4 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/features/consistency_integration.py`
**Path:** `./src/compareblocks/features/consistency_integration.py`
**Purpose:** Text consistency tracking and validation
**Description:** Contains 2 utility functions. Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/features/context.py`
**Path:** `./src/compareblocks/features/context.py`
**Purpose:** Core functionality for context
**Description:** Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/features/core.py`
**Path:** `./src/compareblocks/features/core.py`
**Purpose:** Core functionality for core
**Description:** Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/features/language.py`
**Path:** `./src/compareblocks/features/language.py`
**Purpose:** Core functionality for language
**Description:** Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/gbg/ids.py`
**Path:** `./src/compareblocks/gbg/ids.py`
**Purpose:** Core functionality for ids
**Description:** Implements 1 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/gbg/orientation.py`
**Path:** `./src/compareblocks/gbg/orientation.py`
**Purpose:** Core functionality for orientation
**Description:** Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/gbg/seed.py`
**Path:** `./src/compareblocks/gbg/seed.py`
**Purpose:** Core functionality for seed
**Description:** Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/gbg/types.py`
**Path:** `./src/compareblocks/gbg/types.py`
**Purpose:** Core functionality for types
**Description:** Implements 3 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/gui/config_forms.py`
**Path:** `./src/compareblocks/gui/config_forms.py`
**Purpose:** Configuration management and validation
**Description:** Implements 5 classes. Manages configuration validation and runtime settings. Essential for system functionality and workflow integration.

### `src/compareblocks/gui/import_dialog.py`
**Path:** `./src/compareblocks/gui/import_dialog.py`
**Purpose:** User interface components and interactions
**Description:** Implements 4 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/gui/pdf_viewer.py`
**Path:** `./src/compareblocks/gui/pdf_viewer.py`
**Purpose:** User interface components and interactions
**Description:** Implements 3 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/gui/variations_panel.py`
**Path:** `./src/compareblocks/gui/variations_panel.py`
**Purpose:** Core functionality for variations panel
**Description:** Implements 4 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/io/loader.py`
**Path:** `./src/compareblocks/io/loader.py`
**Purpose:** Core functionality for loader
**Description:** Contains 2 utility functions. Implements 2 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/io/pdf_metadata.py`
**Path:** `./src/compareblocks/io/pdf_metadata.py`
**Purpose:** Core functionality for pdf metadata
**Description:** Contains 2 utility functions. Implements 1 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/io/schemas.py`
**Path:** `./src/compareblocks/io/schemas.py`
**Purpose:** Core functionality for schemas
**Description:** Contains 2 utility functions. Essential for system functionality and workflow integration.

### `src/compareblocks/io/writer.py`
**Path:** `./src/compareblocks/io/writer.py`
**Purpose:** Core functionality for writer
**Description:** Contains 2 utility functions. Implements 3 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/mapping/match.py`
**Path:** `./src/compareblocks/mapping/match.py`
**Purpose:** Core functionality for match
**Description:** Implements 3 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/mapping/variation_block.py`
**Path:** `./src/compareblocks/mapping/variation_block.py`
**Purpose:** Core functionality for variation block
**Description:** Implements 4 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/mcp/client.py`
**Path:** `./src/compareblocks/mcp/client.py`
**Purpose:** Core functionality for client
**Description:** Implements 1 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/mcp/handlers.py`
**Path:** `./src/compareblocks/mcp/handlers.py`
**Purpose:** Core functionality for handlers
**Description:** Implements 3 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/mcp/protocol.py`
**Path:** `./src/compareblocks/mcp/protocol.py`
**Purpose:** Core functionality for protocol
**Description:** Implements 6 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/mcp/server.py`
**Path:** `./src/compareblocks/mcp/server.py`
**Purpose:** Core functionality for server
**Description:** Implements 1 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/mcp/validation.py`
**Path:** `./src/compareblocks/mcp/validation.py`
**Purpose:** Core functionality for validation
**Description:** Implements 1 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/normalize/textnorm.py`
**Path:** `./src/compareblocks/normalize/textnorm.py`
**Purpose:** Core functionality for textnorm
**Description:** Contains 4 utility functions. Implements 3 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/processing/dynamic_reprocessor.py`
**Path:** `./src/compareblocks/processing/dynamic_reprocessor.py`
**Purpose:** Data processing pipeline and workflow management
**Description:** Contains 4 utility functions. Implements 6 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/project/manager.py`
**Path:** `./src/compareblocks/project/manager.py`
**Purpose:** Resource and workflow management functionality
**Description:** Contains 3 utility functions. Implements 3 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/testing/coverage_tracker.py`
**Path:** `./src/compareblocks/testing/coverage_tracker.py`
**Purpose:** Core functionality for coverage tracker
**Description:** Contains 3 utility functions. Implements 4 classes. Essential for system functionality and workflow integration.

### `src/compareblocks/testing/engine_validator.py`
**Path:** `./src/compareblocks/testing/engine_validator.py`
**Purpose:** OCR engine implementation and integration
**Description:** Contains 3 utility functions. Implements 3 classes. Provides OCR engine integration with standardized interface and error handling. Essential for system functionality and workflow integration.

### `src/compareblocks/testing/performance_tracker.py`
**Path:** `./src/compareblocks/testing/performance_tracker.py`
**Purpose:** Core functionality for performance tracker
**Description:** Contains 3 utility functions. Implements 4 classes. Essential for system functionality and workflow integration.


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
# .kiro/specs/becr-tdd-system/tasks.md

# Implementation Plan

## Core System (Completed)

- [x] **1. Project Foundation and Infrastructure Setup**

  - Monorepo structure with src/compareblocks package and comprehensive test directories
  - pyproject.toml with Python 3.12, all dependencies (PyMuPDF, OpenCV, PySide6, pytest, jsonschema)
  - Immutable runner files (run_becr.py, run_tests.py) for application and test suite entry points
  - Virtual environment (.venv) with all required dependencies
  - Complete file path comments and project structure documentation

- [x] **2. NDJSON Schema Validation and I/O Foundation**

  - JSON Schema definitions for input variations and consensus output formats
  - Strict validation loader with clear error messages for malformed records
  - NDJSON writer for exporting consensus decisions and analytics
  - Round-trip compatibility validation between import and export schemas
  - Enhanced schemas supporting comprehensive NDJSON format and multi-format associated files

- [x] **3. Global Block Grid (GBG) with Stable IDs**

  - Deterministic PDF page segmentation using PyMuPDF
  - Stable block identifiers using hash of page number and normalized bounding box coordinates
  - Orientation and deskew detection using OpenCV projection profiles and Hough line detection
  - Cross-platform consistency with identical block IDs across different processing runs
  - Full file processing TDD compliance with real 62-page English Language Arts Standards PDF

- [x] **4. Variation Mapping and Block Association**

  - IoU-based matching system to map external variations to seed blocks
  - Handling of external extracts lacking block identifiers using bounding box matching
  - Child variation blocks for partial matches and overlapping regions
  - Preservation of original extraction metadata with block mapping information

- [x] **5. Text Normalization Pipeline**

  - UTF-8 normalization with consistent whitespace handling
  - Hyphenation joining logic using dictionary and bigram confidence
  - Stable tokenization preserving intentional line breaks
  - Fancy spaces and special character handling

- [x] **6. Feature Extraction System**

  - Length consistency metrics based on median variation length
  - Language fitness scoring using word-in-language rates and OOV detection
  - Anomaly detection for entropy, repetition, and character distribution
  - Context similarity features for subject coherence

- [x] **21. Enhanced Engine Processing with Configuration Management**

  - Overwrite control parameter system with three modes (overwrite, skip, allow_multiple)
  - Enhanced NDJSON output with configuration metadata and processing timestamps
  - Configuration hash system for duplicate detection and result tracking
  - Multiple configuration comparison system for performance analysis
  - Enhanced command-line interface with flexible processing modes
  - Comprehensive test suite covering all configuration management features

- [x] **7. Consensus Scoring and Decision Engine**

  - Weighted scoring system with configurable thresholds and caps
  - Hallucination guard preventing selection of obviously incorrect text
  - Decision policy for auto-pick, merge, or manual review based on score thresholds
  - Orientation mismatch penalties and language fitness caps

- [x] **Configuration Management System**

  - Centralized configuration with config/default_files.json
  - Configuration manager eliminating hardcoded paths throughout application
  - MCP integration readiness with extensible structure design
  - Comprehensive configuration testing and validation

- [x] **Enhanced Engine System**

  - Multiple OCR engines (PyMuPDF, Tesseract, PaddleOCR, Docling, Kreuzberg)
  - Engine manager with configuration and processing coordination
  - GBG-guided processing for improved accuracy
  - Dual-output processing and integrated workflows
  - Advanced matching and association systems (PyMuPDF matcher, Tesseract matcher)

- [x] **Enhanced Configuration System**

  - Foreign key references to individual config files for each engine
  - PDF-specific configuration overrides with GUI management
  - Historical settings tracking with timestamps
  - System-assisted optimization proposals with approval workflow
  - Comprehensive parameter validation and analytics

- [x] **Visual OCR Testing and Debug Tools**

  - Visual OCR testing tool with comprehensive engine testing capabilities
  - Debug image extraction and analysis tools
  - Parameter optimization testing with visual feedback
  - Tesseract optimization for clear text processing

- [x] **Comprehensive System Validation**
  - Complete system integration tests with all engines and real documents
  - Real-world validation scenarios with actual PDF processing
  - Function catalog maintenance with field attributes
  - Default file validation ensuring all functions work with configured PDF
  - Adhoc test validation covering all system components

## Next Priority Tasks

- [x] **8. Review GUI with PDF Visualization**

  - PySide6-based interface with PDF viewer and block highlighting
  - Variations comparison table with metrics, diff highlighting, and selection controls
  - Zoom, pan, and navigation controls for detailed PDF examination
  - Import dialog for external NDJSON variations
  - Manual override and correction capabilities
  - Support for comprehensive NDJSON format with all associated files
  - Filtering by variation count per block
  - Preview functionality for applying changes from one file to another
  - Recalculation triggers for surrounding blocks

- [x] **9. Analytics and Reporting System**

  - Per-engine performance statistics and accuracy metrics
  - Summary reports with manual override rates and anomaly detection counts
  - Analytics export functionality for downstream analysis
  - Engine performance dashboards for optimization insights

- [x] **10. Enhanced Multi-Format Association System**

  - Dedicated parsers for different extract formats (CSV, HTML, JSON, MD, TXT)
  - Content-based alignment for non-positional extracts
  - Format-specific content extraction maintaining associated content without original formatting
  - Association management for tracking all files per root PDF context

- [x] **11. Character-Level Consistency Tracking**

  - Character-by-character consistency scoring across ALL associated files
  - Dynamic consistency percentages that update as new files are added
  - Word-level consistency tracking with spelling accuracy scoring
  - Consistency override system where consistency trumps spelling for acronyms/domain terms

- [x] **12. Enhanced NDJSON Output System**

  - Expanded NDJSON format including root PDF data + all associated file data + comparison data
  - Comparison JSONs showing matching/different content with relative positioning
  - Configurable surrounding context (1 line or 25 characters before/after). Consider if this can be done by just referencing ealier blocks and not having to store excess data.
  - Comparison summary JSON per block for GUI filtering

- [x] **13. MCP Client Infrastructure for Compareblocks Integration**

  - Implement MCP client layer for communication with compareblocks MCP server
  - Create WebSocket connection management with error handling and reconnection logic
  - Build MCP message protocol handlers for request/response cycles
  - Implement MCP request validation and response parsing
  - Create error handling system for MCP communication failures
  - Add connection status monitoring and offline mode graceful degradation
  - Write comprehensive tests for MCP client functionality using real MCP server
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] **14. PDF Selector Indicator Component**


  - Create persistent PDF selector widget positioned below main menu bar
  - Implement PDF metadata display (filename, path, page count, file size)
  - Build clickable interface that opens PDF selection dialog
  - Create PDF selection dialog with file browser and validation
  - Implement PDF change notification system that updates all application components
  - Add PDF validation through MCP communication with compareblocks
  - Write comprehensive GUI tests using pytest-qt for all PDF selector interactions
  - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5_

- [x] **15. Association Library Interface**












  - Create File Management Tab as primary interface for Association Library
  - Implement root PDF list display with associated NDJSON files
  - Build extract associations display with influence percentage calculations
  - Create consensus output file tracking and export file management
  - Implement association management options (new associations, edit existing)
  - Add MCP communication layer for all association data requests
  - Integrate with compareblocks.association.manager through MCP protocol
  - Write comprehensive tests for association library functionality
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [x] **16. Settings Tab Configuration Interface**







  - Create dedicated Settings Tab separate from File Management Tab
  - Implement default file configuration interface (PDF paths, output directories)
  - Build engine configuration settings management
  - Create MCP connection parameter configuration
  - Implement global processing options and system preferences
  - Add MCP communication with compareblocks.config modules
  - Integrate with existing configuration validation system
  - Write comprehensive tests for settings management functionality
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [x] **17. Influence Percentage and Analytics Integration**





  - Implement influence percentage calculation through MCP communication
  - Create consensus output tracking and display system
  - Build consensus output export file management
  - Integrate with compareblocks.analytics modules through MCP protocol
  - Implement automatic metrics updates when reprocessing occurs
  - Add real-time analytics display in Association Library
  - Create analytics export functionality for file management data
  - Write comprehensive tests for analytics integration
  - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_


- [x] **18. Main Window Integration and State Management**








  - Integrate PDF Selector, File Management Tab, and Settings Tab into existing BECRMainWindow
  - Implement application-wide state management for PDF selection changes
  - Create tab switching logic that maintains data consistency
  - Build state synchronization system across all interface components
  - Implement data refresh triggers when PDF selection changes
  - Add error handling for state management failures
  - Create comprehensive integration tests for main window functionality
  - Write GUI tests using pytest-qt for complete user workflows
  - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_


- [ ] **19. Comprehensive Testing and Coverage Validation**

  - Achieve 95% code coverage for all file management components
  - Write unit tests for MCP communication with comprehensive error scenarios
  - Create integration tests for complete file management workflows
  - Implement GUI tests using pytest-qt for all interface interactions
  - Build real file testing scenarios without mocks or stubs
  - Create performance tests for MCP communication and UI responsiveness
  - Implement accessibility tests for keyboard navigation and screen readers
  - Write comprehensive test documentation and validation protocols
  - _Requirements: 23.1, 23.2, 23.3, 23.4, 23.5_

- [ ] **20. Dynamic Reprocessing Engine**

  - Functions for rebuilding all comparisons vs. adding only new ones
  - Incremental processing when new associated files are added
  - Reprocessing triggers that update consistency percentages
  - Version tracking for processing different configurations with the option to only store the stats and config without the supporting data(would have to re run if wanted)

- [x] **21. Change Tracking and Source Attribution**





  - Block-level change history with source attribution (key-value pairs)
  - Initial positional extract as immutable baseline
  - Surrounding block recalculation system
  - Change propagation detection (when changes affect neighboring blocks)
  - add a statistic based result that allows quick ranking of sources engines and configuration used for final output for accuracy


## Future Enhancement Tasks

- [x] **23. Advanced File Association and Project Management**






  - Enhanced file tracking system with version control integration
  - Advanced project structure management with automated file discovery
  - Smart indicators for missing or moved files with auto-relocation suggestions
  - Advanced reprocessing with machine learning-based optimization


- [ ] **25. Advanced MCP Integration and External API**

  - Enhanced Model Context Protocol features for complex integrations
  - Advanced standardized protocol endpoints for enterprise data exchange
  - Real-time collaborative processing with multiple external systems
  - Advanced validation and processing of complex external extraction workflows

- [ ] **26. Documentation and Test Coverage Validation**

  - Comprehensive documentation tracking all functions and their corresponding tests
  - Traceability between each function and its test cases
  - Real-time documentation updates during development for significant changes
  - Advanced test coverage analysis with quality metrics

- [x] **20. Comprehensive Engine Testing and Validation System**
  - Engine function catalog with test coverage tracking for all OCR engines (PyMuPDF, Tesseract, PaddleOCR, Docling, Kreuzberg)
  - Per-engine test validation ensuring all functions work with real PDF files and parameters
  - Performance metrics tracking per engine per PDF root file with accuracy statistics
  - Missing test identification system highlighting untested engine functions and parameter combinations
  - Automated test generation for engine-specific functions using real application data
  - Engine confidence scoring system based on test coverage and performance results
  - Parameter optimization tracking showing best results per PDF type and engine combination
  - Real-time test status dashboard showing which engines/parameters have been validated
  - Integration with existing function catalog system for comprehensive coverage reporting
  - Continuous validation pipeline ensuring new engine functions are properly tested

## Task Completion Validation Protocol

**MANDATORY**: Execute this validation protocol for each new task to ensure function catalog compliance and TDD adherence.

### Validation Steps

1. **Function Catalog Update**

   ```bash
   python functions/rebuild_complete_catalog.py
   python functions/add_field_attributes.py
   python functions/validate_catalog.py
   ```

2. **Default File Integration Validation**

   ```bash
   python validate_function_catalog.py
   ```

3. **Test Coverage Verification**
   ```bash
   python -m pytest tests/ -v
   python -m pytest tests/adhoc/test_function_catalog_default_file_validation.py -v
   ```

### Task Completion Checklist

- [ ] All new functions documented in function catalog with field attributes
- [ ] All functions tested with configured default PDF file
- [ ] All tests pass using real file data (no mocks/stubs)
- [ ] Adhoc validation test updated to cover new functionality
- [ ] `python validate_function_catalog.py` passes completely
- [ ] All application code works with real user data

### Failure Resolution

If validation fails:

1. Identify missing functions not working with default file
2. Fix application code to work with real PDF data
3. Write missing tests using real file scenarios
4. Update adhoc test to cover new functionality
5. Re-run validation until all steps pass

## Current System Status

### Completed Core Components ✅

**Foundation & Infrastructure**

- Project structure with src/compareblocks package and comprehensive test directories
- pyproject.toml configuration with all dependencies and tool settings
- Immutable runner files (run_becr.py, run_tests.py) for consistent entry points
- Virtual environment setup with all required dependencies

**Data Processing Pipeline**

- NDJSON schema validation and I/O foundation with strict validation
- Global Block Grid (GBG) system with stable, deterministic block IDs
- Variation mapping and block association using IoU-based matching
- Text normalization pipeline with UTF-8 handling and hyphenation logic
- Feature extraction system with length, language, anomaly, and context features
- Consensus scoring and decision engine with weighted scoring and hallucination guards

**Configuration Management**

- Centralized configuration system eliminating hardcoded paths
- Enhanced per-engine configuration with foreign key references
- PDF-specific configuration overrides with historical tracking
- System-assisted optimization proposals with approval workflow

**Engine Integration**

- Multiple OCR engines (PyMuPDF, Tesseract, PaddleOCR, Docling, Kreuzberg)
- Engine manager with configuration and processing coordination
- GBG-guided processing for improved accuracy
- Dual-output processing and integrated workflows
- Advanced matching and association systems

**Testing & Validation**

- Comprehensive test suite with 95%+ coverage using real PDF files
- Function catalog system with field attributes and validation
- Default file validation ensuring all functions work with configured PDF
- Complete system integration tests with all engines and real documents

**Tools & Utilities**

- Visual OCR testing tool with comprehensive engine testing capabilities
- Debug image extraction and analysis tools
- Parameter optimization testing with visual feedback
- Tesseract optimization for clear text processing

### System Metrics 📊

- **Test Coverage**: 95%+ with real file-based testing (no mocks/stubs)
- **Function Catalog**: 200+ documented functions with field attributes
- **Engine Support**: 5 OCR engines with advanced integration
- **Configuration Files**: 50+ individual engine config files with foreign key references
- **Processing Capability**: Full 62-page PDF processing with stable block IDs
- **Validation**: Complete adhoc test validation covering all system components

## Future Enhancements (Optional)

- [ ] **22. Multi-Configuration Performance Analysis and Auto-Optimization**

  - Implement comprehensive multi-configuration testing system for all engines
  - Build performance analysis framework to compare extraction quality and speed
  - Create auto-configure function that automatically determines best configuration for each PDF
  - Develop configuration recommendation system based on PDF characteristics
  - Add historical performance tracking and learning from previous optimizations
  - Implement A/B testing framework for configuration optimization
  - Create configuration optimization proposals based on performance analysis
  - Build automated configuration tuning system with quality metrics
  - _Requirements: 21.1, 21.2, 21.3_

- [ ] **Performance Optimization**

  - Parallel processing for multiple PDFs
  - Caching system for repeated extractions
  - Memory optimization for large documents

- [ ] **Advanced Features**
  - Machine learning-based consensus scoring
  - Custom feature extraction plugins
  - Advanced GUI features for batch processing

- [ ] **22. Surrounding Block Impact Analysis**
  - Surrounding block recalculation when changes are applied
  - Cascade detection (when one block change affects next block, and so on)
  - "Recalc check" functionality for iterative block updates
  - Stopping condition detection (when changes no longer propagate)



- [ ] **24. Authentication and Deployment Infrastructure**

  - Secure login functionality with session management
  - Push-button GitHub deployment with version management
  - Role-based access control for different user types
  - Automated update notifications and rollback capabilities
# .kiro/specs/becr-tdd-system/requirements.md
# Requirements Document

## Introduction

The Blockwise Extraction Comparison & Review (BECR) system is an intelligent layer that aligns multiple text extraction outputs from PDFs at the block level, scores them using language and layout-aware signals, and provides a visual review interface for manual override. The system ingests both internal and external extraction results via a strict NDJSON schema and follows a test-driven development approach.

## Glossary

- **BECR_System**: The complete Blockwise Extraction Comparison & Review application
- **Global_Block_Grid**: A deterministic page segmentation system that creates stable block identifiers
- **Variation_Block**: A text extraction result from any engine mapped to a seed block
- **Consensus_Engine**: The scoring and decision-making component that selects best variations
- **Review_GUI**: The graphical interface for manual review and override of consensus decisions
- **NDJSON_Schema**: The standardized JSON format for importing and exporting extraction data
- **Hallucination_Guard**: The anomaly detection system that prevents selection of obviously incorrect text
- **Feature_Extractor**: Component that computes text quality metrics like language fit and anomalies
- **File_Association_Manager**: System that tracks relationships between root PDFs and all associated extraction files
- **External_Extract_Handler**: Component that processes extraction results from engines unaware of Global_Block_Grid
- **Source_Library**: Repository system that manages root PDFs and their associated files
- **GitHub_Deployer**: Push-button deployment system for updates and releases
- **MCP_Interface**: Model Context Protocol compatibility layer for integration with external systems
- **Authentication_System**: Login and user management component
- **Test_Management_Suite**: Comprehensive testing framework that manages and executes all test categories
- **NonUser_Test**: Tests that validate internal functions not directly accessible to users
- **User_Function_Test**: Tests that validate functionality exactly as users would interact with the system
- **Immutable_Runner**: Fixed-path executable files that serve as the consistent entry points for the application and test suite
- **Virtual_Environment**: Isolated Python environment (.venv) containing all project dependencies
- **Temporary_File**: Any file with "temp_" prefix in the first 5 characters of its filename
- **File_Path_Comment**: A comment on the first line of each file containing its relative path and filename

## Requirements

### Requirement 1

**User Story:** As a researcher, I want to segment PDFs into stable blocks with consistent identifiers, so that all extraction engines can align to the same text units for comparison.

#### Acceptance Criteria

1. WHEN a PDF document is processed, THE Global_Block_Grid SHALL generate deterministic block identifiers that remain consistent across multiple processing runs
2. THE Global_Block_Grid SHALL create block identifiers using a stable hash of page number and normalized bounding box coordinates
3. WHEN the same PDF is processed on different platforms, THE Global_Block_Grid SHALL produce identical block identifiers
4. THE Global_Block_Grid SHALL detect and handle rotated pages by applying page-level rotation corrections
5. WHEN processing multi-column layouts, THE Global_Block_Grid SHALL generate separate blocks for each column and text region

### Requirement 2

**User Story:** As a quality reviewer, I want to see PDF crops alongside text variations with quality metrics, so that I can quickly identify and select the best extraction result.

#### Acceptance Criteria

1. WHEN a block is selected for review, THE Review_GUI SHALL display the original PDF crop highlighting the current block
2. THE Review_GUI SHALL present all text variations in a table format showing engine name, extracted text, confidence scores, and quality metrics
3. WHEN comparing variations, THE Review_GUI SHALL highlight text differences between variations using visual diff indicators
4. THE Review_GUI SHALL provide zoom and pan controls for detailed examination of PDF crops
5. WHEN a user selects a preferred variation, THE Review_GUI SHALL update the consensus decision immediately

### Requirement 3

**User Story:** As a developer, I want to import external NDJSON extraction results, so that I can integrate outputs from my own OCR engines and cloud services.

#### Acceptance Criteria

1. WHEN external NDJSON data is imported, THE NDJSON_Schema SHALL validate all required fields and reject malformed records
2. THE Variation_Block SHALL map external variations to existing seed blocks using intersection-over-union (IoU) matching
3. WHEN only bounding box coordinates are provided, THE Variation_Block SHALL automatically map to the best matching seed block
4. THE NDJSON_Schema SHALL preserve all optional metadata fields including confidence scores and orientation data
5. WHEN importing variations, THE BECR_System SHALL maintain data integrity through strict schema validation

### Requirement 4

**User Story:** As the system, I want to automatically score variations and guard against hallucinations, so that obviously incorrect text extractions are never automatically selected.

#### Acceptance Criteria

1. WHEN scoring text variations, THE Consensus_Engine SHALL compute length consistency scores based on median variation length
2. THE Feature_Extractor SHALL calculate language fitness scores using word-in-language rates and out-of-vocabulary detection
3. WHEN anomaly scores exceed defined thresholds, THE Hallucination_Guard SHALL flag variations for manual review instead of auto-selection
4. THE Consensus_Engine SHALL apply orientation mismatch penalties when text orientation differs significantly from expected values
5. WHEN all variations score below quality thresholds, THE Consensus_Engine SHALL flag the entire block for manual review

### Requirement 5

**User Story:** As a quality reviewer, I want to override consensus decisions and make manual corrections, so that I can improve extraction accuracy for challenging cases.

#### Acceptance Criteria

1. WHEN a user selects a different variation, THE Review_GUI SHALL immediately update the consensus NDJSON with the manual override
2. THE Review_GUI SHALL provide an option to mark blocks for manual text correction beyond available variations
3. WHEN manual overrides are made, THE BECR_System SHALL record the decision reason as "manual_override" in the output
4. THE Review_GUI SHALL allow users to merge parts of different variations into a single corrected result
5. WHEN overrides are applied, THE BECR_System SHALL maintain audit trails of all manual decisions

### Requirement 6

**User Story:** As an integrator, I want to export final consensus results and analytics, so that I can use the processed data in downstream applications and analyze engine performance.

#### Acceptance Criteria

1. WHEN processing is complete, THE BECR_System SHALL export consensus decisions in valid NDJSON format with all required fields
2. THE BECR_System SHALL generate analytics reports showing per-engine performance statistics and accuracy metrics
3. WHEN exporting data, THE BECR_System SHALL include decision reasons and confidence scores for each consensus choice
4. THE BECR_System SHALL provide summary statistics including manual override rates and anomaly detection counts
5. THE BECR_System SHALL ensure exported NDJSON maintains compatibility with the import schema for round-trip processing

### Requirement 7

**User Story:** As a developer, I want shared orientation and deskew detection, so that all extraction engines can benefit from consistent preprocessing hints.

#### Acceptance Criteria

1. WHEN processing PDF pages, THE Global_Block_Grid SHALL detect page orientation using projection profile analysis
2. THE Global_Block_Grid SHALL compute deskew angles for individual text blocks using Hough line detection
3. WHEN orientation is detected, THE BECR_System SHALL share orientation metadata with all extraction engines
4. THE Global_Block_Grid SHALL handle vertical text detection and flag non-standard orientations appropriately
5. WHEN deskew hints are available, THE BECR_System SHALL include them in the block metadata for engine consumption

### Requirement 8

**User Story:** As a developer, I want to handle external extracts from engines unaware of the Global Block Grid, so that I can integrate any extraction tool regardless of its block awareness.

#### Acceptance Criteria

1. WHEN external extracts lack block identifiers, THE External_Extract_Handler SHALL create variation blocks using bounding box matching
2. THE External_Extract_Handler SHALL map external extracts to seed blocks using configurable IoU thresholds
3. WHEN external extracts have overlapping regions, THE External_Extract_Handler SHALL create child variation blocks for partial matches
4. THE External_Extract_Handler SHALL preserve original extraction metadata while adding block mapping information
5. WHEN processing legacy extracts, THE External_Extract_Handler SHALL maintain backward compatibility with existing formats

### Requirement 9

**User Story:** As a project manager, I want a comprehensive file association system, so that all related files for each PDF are tracked and managed systematically.

#### Acceptance Criteria

1. WHEN a root PDF is added, THE Source_Library SHALL create a project structure tracking all associated files
2. THE File_Association_Manager SHALL maintain relationships between root PDFs, extraction files, and user-provided variations
3. WHEN loading projects, THE File_Association_Manager SHALL validate all file paths and report missing or moved files
4. THE Source_Library SHALL provide clear indicators showing which files need to be relocated to fulfill associations
5. WHEN reprocessing documents, THE BECR_System SHALL consider all associated files including previous NDJSON results

### Requirement 10

**User Story:** As a user, I want simple authentication and push-button GitHub deployment, so that I can securely access the system and easily deploy updates.

#### Acceptance Criteria

1. WHEN accessing the system, THE Authentication_System SHALL provide secure login functionality with session management
2. THE GitHub_Deployer SHALL enable one-click deployment and updates through integrated GitHub Actions
3. WHEN deploying updates, THE GitHub_Deployer SHALL handle version management and rollback capabilities
4. THE Authentication_System SHALL support role-based access control for different user types
5. WHEN updates are available, THE BECR_System SHALL notify users and provide simple update mechanisms

### Requirement 11

**User Story:** As an integrator, I want MCP (Model Context Protocol) compatibility, so that the system can integrate seamlessly with external AI tools and workflows.

#### Acceptance Criteria

1. WHEN external systems connect, THE MCP_Interface SHALL provide standardized protocol endpoints for data exchange
2. THE MCP_Interface SHALL expose extraction results and consensus decisions through MCP-compliant APIs
3. WHEN receiving MCP requests, THE BECR_System SHALL validate and process external extraction submissions
4. THE MCP_Interface SHALL support real-time updates and notifications for processing status changes
5. WHEN integrating with AI tools, THE MCP_Interface SHALL maintain data consistency and security protocols

### Requirement 12

**User Story:** As a developer, I want strict TDD methodology with real file testing, so that all functionality is validated using actual user workflows without mocks or stubs.

#### Acceptance Criteria

1. WHEN implementing any feature, THE Test_Management_Suite SHALL require tests to be written first before any implementation code
2. THE BECR_System SHALL use only actual files for testing and SHALL NOT use stubs, mocks, or synthetic data
3. WHEN testing user-accessible functionality, THE User_Function_Test SHALL validate features exactly as users would interact with them
4. WHEN testing internal functions not accessible to users, THE NonUser_Test SHALL be clearly categorized and separated
5. THE Test_Management_Suite SHALL maintain at least 95% coverage using real file-based testing scenarios

### Requirement 13

**User Story:** As a system administrator, I want immutable application entry points and virtual environment isolation, so that the system maintains consistent execution paths and dependency management.

#### Acceptance Criteria

1. WHEN the application starts, THE Immutable_Runner SHALL use fixed, unchanging file paths and names for main application and test suite entry points
2. THE BECR_System SHALL operate entirely within a Virtual_Environment (.venv) containing all required dependencies
3. WHEN temporary test versions of runner files are created, THE BECR_System SHALL treat them as temporary until properly integrated into immutable runners
4. THE Virtual_Environment SHALL isolate all Python dependencies and prevent conflicts with system-wide packages
5. WHEN deploying or updating, THE Immutable_Runner SHALL maintain consistent execution interfaces across all environments

### Requirement 14

**User Story:** As a developer, I want comprehensive documentation that tracks all functions and their corresponding tests, so that I can understand system coverage and maintain code quality.

#### Acceptance Criteria

1. WHEN significant changes are made, THE BECR_System SHALL update documentation immediately during development
2. THE BECR_System SHALL maintain documentation listing all application functions and their validating tests
3. WHEN all tests for a task are fulfilled, THE BECR_System SHALL update documentation to reflect the completed functionality
4. THE BECR_System SHALL provide traceability between each function and its corresponding test cases
5. WHEN new functions are added, THE BECR_System SHALL require documentation updates before considering the task complete
# Requirements Document

## Introduction

This feature extends BECR to provide a comprehensive association management interface that allows users to track multiple OCR extraction associations for a PDF, process them through consensus algorithms, and review the results in a visual interface with full provenance tracking.

## Glossary

- **Association**: An OCR extraction result from an engine that has been aligned to the GBG blocks
- **Comparison JSON**: The aligned association data stored in NDJSON format
- **Consensus JSON**: The optimized combined extraction result with provenance metadata
- **Primary Extract**: The initial baseline extraction used as the starting point
- **Provenance**: Historical tracking of which association contributed each text segment
- **Association Library**: The UI panel showing all associations for a PDF file
- **Consensus Reader**: The visual interface for reviewing consensus results with color-coded sources

## Requirements

### Requirement 1: Association Library Management

**User Story:** As a user, I want to see all associations for a PDF file with their processing status, so that I can track which extractions have been compared and are ready for consensus processing.

#### Acceptance Criteria

1. WHEN the System loads a PDF file, THE Association_Library SHALL display all associated extraction files with their metadata
2. THE Association_Library SHALL display whether each association has been added to the comparison JSON with a visual indicator
3. THE Association_Library SHALL display a timestamp for when each association was processed
4. THE Association_Library SHALL display a timestamp for when each comparison was created
5. WHERE an association has a comparison JSON, THE Association_Library SHALL provide a button to open the comparison view

### Requirement 2: Association Statistics and Preview

**User Story:** As a user, I want to see statistics about how each association would affect the consensus, so that I can understand the impact before processing.

#### Acceptance Criteria

1. THE Association_Library SHALL display the character count that would be applied from each association
2. THE Association_Library SHALL calculate statistics without modifying the consensus JSON
3. THE Association_Library SHALL update statistics when associations are added or removed
4. THE Association_Library SHALL display the total number of associations with comparison JSONs

### Requirement 3: Consensus Processing with Validation

**User Story:** As a user, I want to process consensus with reliability warnings, so that I understand the quality of the result based on the number of associations.

#### Acceptance Criteria

1. THE Association_Library SHALL provide a Process_Consensus button
2. WHEN fewer than 3 associations have comparison JSONs, THE System SHALL display a reliability warning before processing
3. WHEN the user confirms consensus processing, THE System SHALL apply the established consensus algorithms to create an optimized extract
4. THE System SHALL use word validation during consensus processing
5. THE System SHALL use character validation during consensus processing
6. THE System SHALL use spacing validation and rebuilding during consensus processing
7. THE System SHALL apply character-level replacement optimization to minimize unnecessary changes

### Requirement 4: Consensus JSON with Provenance

**User Story:** As a user, I want the consensus JSON to store provenance information, so that I can trace which association contributed each text segment.

#### Acceptance Criteria

1. THE Consensus_JSON SHALL store the optimized text for each block
2. THE Consensus_JSON SHALL store provenance metadata for each text segment indicating the source association
3. THE Consensus_JSON SHALL store the character range for each provenance segment
4. THE Consensus_JSON SHALL store the original text from each contributing association for comparison
5. THE Consensus_JSON SHALL indicate which segments were replaced from the primary extract

### Requirement 5: Consensus Reader Interface

**User Story:** As a user, I want to view the consensus result in a high-quality reader with color-coded sources, so that I can visually verify the quality of the consensus.

#### Acceptance Criteria

1. THE Consensus_Reader SHALL display the consensus text in a high-quality custom reader interface
2. THE Consensus_Reader SHALL apply color highlights to text segments based on their source association
3. THE Consensus_Reader SHALL display a legend mapping colors to association sources
4. THE Consensus_Reader SHALL use a two-page layout design with the consensus on the left
5. WHEN the user clicks a text segment, THE Consensus_Reader SHALL display the provenance history for that segment

### Requirement 6: Provenance History Panel

**User Story:** As a user, I want to see all versions of a text segment from different associations, so that I can understand why the consensus chose a particular version.

#### Acceptance Criteria

1. THE Provenance_Panel SHALL display on the right side of the Consensus_Reader
2. WHEN a text segment is selected, THE Provenance_Panel SHALL display all association versions of that text
3. THE Provenance_Panel SHALL display each version with its source association label
4. THE Provenance_Panel SHALL apply the same color coding as the consensus view
5. THE Provenance_Panel SHALL display the corresponding PDF region for each version
6. THE Provenance_Panel SHALL allow the user to visually compare all versions side-by-side

### Requirement 7: Visual PDF Region Display

**User Story:** As a user, I want to see the actual PDF region for each text version, so that I can verify the extraction quality against the source document.

#### Acceptance Criteria

1. THE Provenance_Panel SHALL extract and display the PDF region image for each text version
2. THE System SHALL use the block coordinates from the GBG to identify the PDF region
3. THE System SHALL render the PDF region at high quality for visual inspection
4. THE Provenance_Panel SHALL align the PDF region images with their corresponding text versions
5. THE Provenance_Panel SHALL support zooming into PDF region images for detailed inspection

### Requirement 8: Reprocessing and Updates

**User Story:** As a user, I want to reprocess associations or consensus, so that I can update results when new associations are added or algorithms improve.

#### Acceptance Criteria

1. THE Association_Library SHALL provide a reprocess button for each association
2. WHEN an association is reprocessed, THE System SHALL update the comparison JSON and timestamp
3. THE Association_Library SHALL provide a reprocess consensus button
4. WHEN consensus is reprocessed, THE System SHALL regenerate the consensus JSON with updated provenance
5. THE System SHALL preserve the original consensus JSON as a backup before reprocessing

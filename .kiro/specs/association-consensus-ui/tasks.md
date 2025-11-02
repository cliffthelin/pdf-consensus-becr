# Implementation Plan

- [ ] 1. Implement Association Status Tracking System
  - Create AssociationStatus dataclass with all required fields
  - Implement status persistence to JSON files
  - Create methods to update status on processing events
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. Implement Association Statistics Calculator
  - Create AssociationStatisticsCalculator class
  - Implement character impact calculation method
  - Implement block impact calculation method
  - Implement reliability score calculation based on association count
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 3. Extend Consensus Engine with Provenance Tracking
  - Create ProvenanceSegment dataclass
  - Create ConsensusWithProvenance dataclass
  - Modify consensus processing to track source for each text segment
  - Implement character range tracking for provenance segments
  - Store original text from each contributing association
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 4. Implement Character-Level Replacement Optimization
  - Create CharacterLevelOptimizer class
  - Implement minimal replacement finding using dynamic programming
  - Implement replacement application method
  - Integrate with consensus engine to minimize changes
  - _Requirements: 3.7_

- [ ] 5. Implement Consensus Validation System
  - Create ConsensusValidator class
  - Implement association count validation with warning generation
  - Implement word validation method
  - Implement character validation method
  - Implement spacing validation and rebuilding method
  - _Requirements: 3.1, 3.2, 3.4, 3.5, 3.6_

- [ ] 6. Create Consensus JSON Schema with Provenance
  - Define CONSENSUS_WITH_PROVENANCE_SCHEMA in schemas.py
  - Implement schema validation for provenance data
  - Create writer methods for consensus JSON with provenance
  - Create loader methods for consensus JSON with provenance
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 7. Implement Association Library UI Widget
  - Create AssociationLibraryWidget class inheriting from QWidget
  - Implement association list display with tree structure
  - Implement status indicator rendering (checkmarks, warnings)
  - Implement timestamp display formatting
  - Implement statistics display for each association
  - Add action buttons (View Comparison, Reprocess, Add Association)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4_

- [ ] 8. Implement Process Consensus Button with Validation
  - Add Process Consensus button to Association Library UI
  - Implement pre-processing validation check
  - Create warning dialog for insufficient associations
  - Implement consensus processing trigger
  - Display processing progress indicator
  - Show success/error messages after processing
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 9. Implement Color Coding System
  - Create ColorCodingSystem class
  - Implement color assignment algorithm
  - Create color map persistence
  - Implement color retrieval methods
  - Define default color palette
  - _Requirements: 5.2, 5.3_

- [ ] 10. Implement PDF Region Extractor
  - Create PDFRegionExtractor class
  - Implement region extraction using PyMuPDF
  - Implement high-quality rendering at configurable DPI
  - Implement region extraction with highlighting
  - Add caching for extracted regions
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 11. Implement Consensus Reader UI Widget
  - Create ConsensusReaderWidget class with dual-pane layout
  - Implement consensus text display area
  - Implement provenance history panel area
  - Create splitter for resizable panes
  - Add legend display for color coding
  - _Requirements: 5.1, 5.4_

- [ ] 12. Implement Color-Coded Text Highlighting
  - Implement text highlighting based on provenance segments
  - Apply colors from ColorCodingSystem to text ranges
  - Handle overlapping segments gracefully
  - Implement hover effects for highlighted segments
  - _Requirements: 5.2, 5.3_

- [ ] 13. Implement Text Selection and Provenance Display
  - Implement text selection handling in consensus reader
  - Detect which provenance segment was selected
  - Trigger provenance panel update on selection
  - Highlight selected segment in consensus view
  - _Requirements: 5.5, 6.2_

- [ ] 14. Implement Provenance History Panel
  - Create ProvenanceHistoryPanel class
  - Display all association versions for selected segment
  - Apply color coding to each version
  - Display source association labels
  - Implement scrollable layout for multiple versions
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 15. Implement PDF Region Display in Provenance Panel
  - Integrate PDFRegionExtractor with provenance panel
  - Display PDF region image for each variation
  - Implement image alignment with text versions
  - Add zoom controls for PDF region images
  - Handle extraction errors gracefully with placeholder images
  - _Requirements: 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 16. Implement Reprocessing Functionality
  - Add reprocess button for individual associations
  - Implement association reprocessing logic
  - Update comparison JSON and timestamps
  - Add reprocess consensus button
  - Implement consensus backup before reprocessing
  - Regenerate consensus JSON with updated provenance
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 17. Integrate Association Library into Main GUI
  - Add Association Library tab to main BECR window
  - Connect PDF selection to association loading
  - Implement tab switching and state management
  - Add menu items for association management
  - _Requirements: 1.1_

- [ ] 18. Integrate Consensus Reader into Main GUI
  - Add Consensus Reader tab or window to main BECR
  - Implement navigation from Association Library to Consensus Reader
  - Connect consensus JSON loading to reader display
  - Add menu items for consensus review
  - _Requirements: 5.1_

- [ ] 19. Write comprehensive unit tests for all components
  - Test AssociationStatus tracking and persistence
  - Test statistics calculation accuracy
  - Test provenance tracking in consensus engine
  - Test character-level optimization algorithms
  - Test validation rules (word, character, spacing)
  - Test color coding assignment and consistency
  - Test PDF region extraction
  - Test UI component rendering and interactions
  - _Requirements: All_

- [ ] 20. Write integration tests for end-to-end workflows
  - Test complete workflow: load PDF → view associations → process consensus → review
  - Test reprocessing workflow with provenance updates
  - Test multiple associations with consensus validation
  - Test real file scenarios with actual OCR outputs
  - _Requirements: All_

- [ ] 21. Write GUI tests using pytest-qt
  - Test association library user interactions
  - Test consensus processing with confirmation dialogs
  - Test text selection in consensus reader
  - Test provenance panel updates
  - Test PDF region image display
  - Test responsive layout and window resizing
  - _Requirements: All_

- [ ] 22. Create documentation and user guide
  - Document association management workflows
  - Document consensus processing with provenance
  - Document consensus reader usage
  - Create screenshots and examples
  - Document configuration options
  - _Requirements: All_

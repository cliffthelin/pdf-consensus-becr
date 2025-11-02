# Design Document

## Overview

This feature extends BECR with a comprehensive Association Management and Consensus Review system. It provides users with a visual interface to track multiple OCR extraction associations for each PDF, process them through advanced consensus algorithms with provenance tracking, and review results in a dual-pane interface that shows both the consensus text and the source variations with visual PDF region verification.

The system integrates with existing BECR components (GBG, consensus engine, association manager) and adds new UI components for association library management and consensus review.

## Architecture

### High-Level Component Structure

```
Association Management Layer
├── Association Library UI (File Management Tab)
├── Association Status Tracker
├── Statistics Calculator
└── Reprocessing Controller

Consensus Processing Layer
├── Enhanced Consensus Engine (with provenance)
├── Validation & Warning System
├── Character-Level Optimization
└── Consensus JSON Writer

Consensus Review Layer
├── Consensus Reader UI (Dual-Pane Layout)
├── Provenance History Panel
├── Color-Coded Source Highlighting
└── PDF Region Extractor & Viewer
```

### Integration with Existing BECR Architecture

```
Existing BECR:
PDF → GBG → Variations → Features → Consensus → Review GUI

New Extension:
PDF → Association Library UI
       ↓
    Multiple Associations → Enhanced Consensus (with provenance)
       ↓
    Consensus JSON → Consensus Reader UI → Provenance Panel
```

## Components and Interfaces

### 1. Association Library UI Component

**Purpose**: Provide a centralized interface for managing all associations related to a PDF file.

**Location**: New tab in main BECR GUI (File Management Tab)

**Key Classes**:

```python
class AssociationLibraryWidget(QWidget):
    """Main widget for association library management."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.association_manager = AssociationManager()
        self.associations = {}
        self.comparison_status = {}
        self.setup_ui()
    
    def load_associations(self):
        """Load all associations for current PDF."""
        pass
    
    def display_association_status(self, association_id: str):
        """Display status indicators for an association."""
        pass
    
    def calculate_statistics(self):
        """Calculate impact statistics for all associations."""
        pass
    
    def trigger_reprocessing(self, association_id: str):
        """Trigger reprocessing of a specific association."""
        pass
```

**UI Layout**:

```
┌─────────────────────────────────────────────────────────┐
│ Association Library for: document.pdf                   │
├─────────────────────────────────────────────────────────┤
│ ┌─ Association 1: tesseract_output.json                 │
│ │  Status: ✓ Comparison JSON created                    │
│ │  Processed: 2024-10-30 14:23:15                       │
│ │  Comparison: 2024-10-30 14:25:42                      │
│ │  Impact: 1,234 characters would be applied            │
│ │  [View Comparison] [Reprocess]                        │
│ ├─ Association 2: paddleocr_output.json                 │
│ │  Status: ✓ Comparison JSON created                    │
│ │  Processed: 2024-10-30 14:30:01                       │
│ │  Comparison: 2024-10-30 14:31:18                      │
│ │  Impact: 892 characters would be applied              │
│ │  [View Comparison] [Reprocess]                        │
│ ├─ Association 3: pymupdf_output.json                   │
│ │  Status: ⚠ Not yet compared                           │
│ │  Processed: 2024-10-30 15:00:00                       │
│ │  [Create Comparison]                                  │
├─────────────────────────────────────────────────────────┤
│ Summary: 3 associations, 2 with comparisons             │
│ [Process Consensus] [Add Association] [Refresh]         │
└─────────────────────────────────────────────────────────┘
```

### 2. Association Status Tracker

**Purpose**: Track processing status and timestamps for each association.

**Data Model**:

```python
@dataclass
class AssociationStatus:
    """Status information for an association."""
    association_id: str
    file_path: str
    added_to_json: bool
    processed_timestamp: Optional[datetime]
    comparison_created: bool
    comparison_timestamp: Optional[datetime]
    character_count: int
    block_count: int
    error_message: Optional[str] = None
```

### 3. Statistics Calculator

**Purpose**: Calculate impact statistics without modifying consensus.

**Key Methods**:

```python
class AssociationStatisticsCalculator:
    """Calculate statistics for associations."""
    
    def calculate_character_impact(self, association_id: str, 
                                   primary_extract: str) -> int:
        """Calculate how many characters would be applied."""
        pass
    
    def calculate_block_impact(self, association_id: str) -> Dict[str, int]:
        """Calculate impact per block."""
        pass
    
    def get_reliability_score(self, num_associations: int) -> float:
        """Calculate reliability based on association count."""
        pass
```

### 4. Enhanced Consensus Engine with Provenance

**Purpose**: Extend existing consensus engine to track provenance.

**Enhanced Data Model**:

```python
@dataclass
class ProvenanceSegment:
    """Provenance information for a text segment."""
    start_char: int
    end_char: int
    source_association: str
    original_text: str
    confidence: float
    replaced_from_primary: bool

@dataclass
class ConsensusWithProvenance:
    """Consensus result with full provenance tracking."""
    block_id: str
    final_text: str
    provenance_segments: List[ProvenanceSegment]
    primary_text: str
    all_variations: Dict[str, str]  # association_id -> text
    consensus_score: float
    validation_results: Dict[str, Any]
```

### 5. Consensus Processing with Validation

**Purpose**: Process consensus with warnings and validation.

**Validation Rules**:

```python
class ConsensusValidator:
    """Validate consensus processing."""
    
    MINIMUM_RELIABLE_ASSOCIATIONS = 3
    
    def validate_before_processing(self, associations: List[str]) -> ValidationResult:
        """Validate before processing consensus."""
        if len(associations) < self.MINIMUM_RELIABLE_ASSOCIATIONS:
            return ValidationResult(
                is_valid=True,
                warnings=[f"Only {len(associations)} associations available. "
                         f"Reliability improves with {self.MINIMUM_RELIABLE_ASSOCIATIONS}+ associations."]
            )
        return ValidationResult(is_valid=True, warnings=[])
    
    def apply_word_validation(self, text: str) -> bool:
        """Validate words in text."""
        pass
    
    def apply_character_validation(self, text: str) -> bool:
        """Validate characters in text."""
        pass
    
    def apply_spacing_validation(self, text: str) -> str:
        """Validate and rebuild spacing."""
        pass
```

### 6. Character-Level Replacement Optimization

**Purpose**: Minimize unnecessary changes by replacing only necessary characters.

**Algorithm**:

```python
class CharacterLevelOptimizer:
    """Optimize replacements at character level."""
    
    def find_minimal_replacement(self, original: str, replacement: str) -> List[Tuple[int, int, str]]:
        """Find minimal character ranges to replace."""
        # Use dynamic programming to find minimal edit distance
        # Return list of (start, end, new_text) tuples
        pass
    
    def apply_minimal_replacements(self, text: str, 
                                   replacements: List[Tuple[int, int, str]]) -> str:
        """Apply minimal replacements to text."""
        pass
```



### 7. Consensus JSON Schema with Provenance

**Purpose**: Define schema for consensus output with provenance metadata.

**Schema Extension**:

```python
CONSENSUS_WITH_PROVENANCE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["block_id", "final_text", "provenance_segments"],
    "properties": {
        "block_id": {"type": "string"},
        "final_text": {"type": "string"},
        "primary_text": {"type": "string"},
        "provenance_segments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["start_char", "end_char", "source_association"],
                "properties": {
                    "start_char": {"type": "integer", "minimum": 0},
                    "end_char": {"type": "integer", "minimum": 0},
                    "source_association": {"type": "string"},
                    "original_text": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "replaced_from_primary": {"type": "boolean"}
                }
            }
        },
        "all_variations": {
            "type": "object",
            "patternProperties": {
                "^.+$": {"type": "string"}
            }
        },
        "consensus_score": {"type": "number"},
        "validation_results": {"type": "object"}
    }
}
```

### 8. Consensus Reader UI Component

**Purpose**: Provide visual interface for reviewing consensus with provenance.

**Layout Design**:

```
┌─────────────────────────────────────────────────────────┐
│ Consensus Reader - document.pdf                         │
├──────────────────────────┬──────────────────────────────┤
│ Consensus Text           │ Provenance History           │
│                          │                              │
│ This is the consensus    │ Selected: "consensus text"   │
│ text with color-coded    │                              │
│ highlighting based on    │ ┌─ tesseract (green)        │
│ source associations.     │ │  "consensus text"          │
│                          │ │  [PDF Region Image]        │
│ [Text continues with     │ │                            │
│  different colors for    │ ├─ paddleocr (blue)         │
│  different sources]      │ │  "consensus text"          │
│                          │ │  [PDF Region Image]        │
│                          │ │                            │
│                          │ ├─ pymupdf (orange)         │
│                          │ │  "consensus texl"          │
│                          │ │  [PDF Region Image]        │
│                          │ │                            │
│                          │ └─ Primary (gray)           │
│                          │    "consensus text"          │
│                          │    [PDF Region Image]        │
├──────────────────────────┴──────────────────────────────┤
│ Legend: ■ tesseract ■ paddleocr ■ pymupdf ■ primary    │
└─────────────────────────────────────────────────────────┘
```

**Key Classes**:

```python
class ConsensusReaderWidget(QWidget):
    """Main consensus reader widget."""
    
    def __init__(self, consensus_json_path: str):
        self.consensus_data = None
        self.color_map = {}
        self.setup_ui()
    
    def load_consensus(self, json_path: str):
        """Load consensus JSON with provenance."""
        pass
    
    def apply_color_highlighting(self):
        """Apply color highlighting based on provenance."""
        pass
    
    def handle_text_selection(self, start: int, end: int):
        """Handle user text selection."""
        pass
```

### 9. Provenance History Panel

**Purpose**: Display all variations of selected text segment.

**Key Classes**:

```python
class ProvenanceHistoryPanel(QWidget):
    """Panel showing provenance history for selected text."""
    
    def __init__(self):
        self.current_segment = None
        self.variations = []
        self.setup_ui()
    
    def display_variations(self, segment: ProvenanceSegment):
        """Display all variations for a segment."""
        pass
    
    def render_pdf_region(self, association_id: str, bbox: BoundingBox):
        """Render PDF region for a variation."""
        pass
```

### 10. PDF Region Extractor

**Purpose**: Extract and render PDF regions for visual verification.

**Key Methods**:

```python
class PDFRegionExtractor:
    """Extract PDF regions for display."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf_document = None
    
    def extract_region(self, page: int, bbox: BoundingBox, 
                      dpi: int = 300) -> QPixmap:
        """Extract PDF region as high-quality image."""
        # Use PyMuPDF to render specific region
        pass
    
    def extract_with_highlight(self, page: int, bbox: BoundingBox,
                              highlight_color: str) -> QPixmap:
        """Extract region with highlighting."""
        pass
```

### 11. Color Coding System

**Purpose**: Assign consistent colors to associations for visual identification.

**Color Assignment**:

```python
class ColorCodingSystem:
    """Manage color assignments for associations."""
    
    DEFAULT_COLORS = [
        "#4CAF50",  # Green
        "#2196F3",  # Blue
        "#FF9800",  # Orange
        "#9C27B0",  # Purple
        "#F44336",  # Red
        "#00BCD4",  # Cyan
        "#FFEB3B",  # Yellow
        "#795548",  # Brown
    ]
    
    def __init__(self):
        self.color_map = {}
        self.next_color_index = 0
    
    def assign_color(self, association_id: str) -> str:
        """Assign color to association."""
        if association_id not in self.color_map:
            self.color_map[association_id] = self.DEFAULT_COLORS[self.next_color_index]
            self.next_color_index = (self.next_color_index + 1) % len(self.DEFAULT_COLORS)
        return self.color_map[association_id]
    
    def get_color(self, association_id: str) -> str:
        """Get assigned color for association."""
        return self.color_map.get(association_id, "#808080")  # Gray default
```

## Data Models

### Core Data Structures

```python
@dataclass
class AssociationRecord:
    """Record of an association file."""
    association_id: str
    file_path: str
    format_type: str
    status: AssociationStatus
    statistics: Dict[str, Any]

@dataclass
class ComparisonJSON:
    """Comparison JSON data."""
    association_id: str
    blocks: List[Dict[str, Any]]
    created_timestamp: datetime
    character_count: int

@dataclass
class ConsensusJSON:
    """Consensus JSON with provenance."""
    pdf_path: str
    blocks: List[ConsensusWithProvenance]
    created_timestamp: datetime
    associations_used: List[str]
    validation_summary: Dict[str, Any]
```

## Error Handling

### Validation Errors

- **Insufficient Associations**: Warning dialog when < 3 associations
- **Invalid Association Format**: Clear error message with format requirements
- **Consensus Processing Failure**: Detailed error with recovery options

### Processing Errors

- **Character Validation Failure**: Log warnings, continue with best effort
- **Spacing Rebuild Failure**: Fall back to original spacing
- **Provenance Tracking Error**: Continue without provenance for affected segments

### UI Error Handling

- **PDF Region Extraction Failure**: Show placeholder image with error message
- **Color Assignment Overflow**: Reuse colors with visual distinction
- **Large Document Performance**: Implement pagination and lazy loading



## Testing Strategy

### Unit Tests

**Association Library Components**:
- Test association loading and status tracking
- Test statistics calculation accuracy
- Test reprocessing triggers
- Test UI state management

**Consensus Processing**:
- Test provenance tracking accuracy
- Test character-level optimization
- Test validation rules (word, character, spacing)
- Test warning generation for insufficient associations

**Consensus Reader**:
- Test color coding assignment and consistency
- Test text selection and provenance display
- Test PDF region extraction
- Test dual-pane layout rendering

### Integration Tests

**End-to-End Workflows**:
- Load PDF → View associations → Process consensus → Review in reader
- Add new association → Reprocess → Verify provenance updates
- Multiple associations → Consensus with warnings → Visual verification

**Real File Testing**:
- Use actual PDF files with multiple OCR outputs
- Verify consensus quality with known ground truth
- Test with various association formats (JSON, CSV, TXT)
- Validate provenance accuracy across different scenarios

### GUI Tests (pytest-qt)

**User Interactions**:
- Click association items to view details
- Trigger consensus processing with confirmation dialog
- Select text in consensus reader to view provenance
- Navigate between different PDF regions

**Visual Validation**:
- Verify color highlighting renders correctly
- Check PDF region images display properly
- Validate legend updates with associations
- Test responsive layout with different window sizes

## Performance Considerations

### Scalability Targets

- **Association Loading**: < 500ms for 10+ associations
- **Statistics Calculation**: < 200ms for impact preview
- **Consensus Processing**: < 2s per page with 5 associations
- **Consensus Reader Rendering**: < 100ms for text highlighting
- **PDF Region Extraction**: < 300ms per region at 300 DPI

### Optimization Strategies

- **Lazy Loading**: Load association details on demand
- **Caching**: Cache PDF region images for reuse
- **Background Processing**: Run consensus in separate thread
- **Incremental Updates**: Update UI progressively during processing

## Security Considerations

### Input Validation

- Validate association file formats before parsing
- Sanitize file paths to prevent directory traversal
- Validate JSON schema for consensus data
- Limit file sizes to prevent memory exhaustion

### Data Integrity

- Backup original consensus before reprocessing
- Validate provenance data consistency
- Verify character ranges don't overlap
- Ensure all referenced associations exist

## Integration Points

### Existing BECR Components

**Global Block Grid (GBG)**:
- Use GBG block IDs for association alignment
- Extract block coordinates for PDF region display
- Leverage orientation detection for region extraction

**Consensus Engine**:
- Extend with provenance tracking
- Integrate validation algorithms
- Use existing scoring mechanisms

**Association Manager**:
- Build on existing association loading
- Extend with status tracking
- Add comparison JSON management

**Review GUI**:
- Add new tabs for association library and consensus reader
- Integrate with existing PDF viewer
- Share color coding with variation display

### New External Dependencies

**None required** - All functionality uses existing BECR dependencies:
- PyMuPDF for PDF region extraction
- PySide6 for UI components
- Existing consensus and validation modules

## Deployment Considerations

### Configuration

**Default Settings**:
```python
CONSENSUS_CONFIG = {
    "minimum_associations_warning": 3,
    "character_optimization_enabled": True,
    "word_validation_enabled": True,
    "spacing_validation_enabled": True,
    "pdf_region_dpi": 300,
    "max_provenance_history": 10,
    "color_coding_enabled": True
}
```

### File Organization

```
project_root/
├── associations/
│   ├── document1/
│   │   ├── tesseract.json
│   │   ├── paddleocr.json
│   │   ├── comparison_tesseract.json
│   │   ├── comparison_paddleocr.json
│   │   └── consensus_with_provenance.json
│   └── document2/
│       └── ...
└── output/
    └── consensus_reports/
```

### Backward Compatibility

- Existing consensus JSON files remain valid
- New provenance fields are optional
- Association library works with existing file structures
- Consensus reader falls back gracefully without provenance

## User Workflows

### Workflow 1: Process Consensus with Multiple Associations

1. User opens PDF in BECR
2. User navigates to Association Library tab
3. System displays all associations with status indicators
4. User reviews statistics showing character impact
5. User clicks "Process Consensus" button
6. System shows warning if < 3 associations
7. User confirms processing
8. System processes consensus with provenance tracking
9. System displays success message with consensus JSON path
10. User clicks to open Consensus Reader

### Workflow 2: Review Consensus with Provenance

1. User opens Consensus Reader for a PDF
2. System displays consensus text with color-coded sources
3. User clicks on a text segment
4. System highlights segment and shows provenance panel
5. Provenance panel displays all variations with PDF regions
6. User visually compares variations
7. User can zoom into PDF regions for detailed inspection
8. User navigates to different segments to review

### Workflow 3: Add and Reprocess Association

1. User has existing consensus
2. User adds new OCR output as association
3. User clicks "Reprocess" for the new association
4. System creates comparison JSON
5. User clicks "Reprocess Consensus"
6. System backs up original consensus
7. System regenerates consensus with new association
8. User reviews updated consensus in reader
9. System shows which segments changed due to new association

## Future Enhancements

### Potential Extensions

- **Manual Override in Consensus Reader**: Allow users to edit consensus text directly
- **Confidence Visualization**: Show confidence scores as opacity or border thickness
- **Diff View**: Show before/after comparison when reprocessing
- **Export Options**: Export consensus with provenance to various formats
- **Batch Processing**: Process consensus for multiple PDFs simultaneously
- **Association Templates**: Save association configurations for reuse
- **Quality Metrics Dashboard**: Show aggregate quality metrics across associations

### API Considerations

Design components with API-first approach for potential future integrations:

```python
class ConsensusAPI:
    """API for consensus processing."""
    
    def process_consensus(self, pdf_path: str, 
                         association_ids: List[str]) -> ConsensusJSON:
        """Process consensus programmatically."""
        pass
    
    def get_provenance(self, block_id: str, 
                      char_range: Tuple[int, int]) -> List[ProvenanceSegment]:
        """Get provenance for specific text range."""
        pass
    
    def export_consensus(self, consensus_json: ConsensusJSON, 
                        format: str) -> str:
        """Export consensus to various formats."""
        pass
```

## Accessibility Considerations

- **Keyboard Navigation**: Full keyboard support for all UI components
- **Screen Reader Support**: Proper ARIA labels and descriptions
- **Color Blind Friendly**: Use patterns in addition to colors
- **High Contrast Mode**: Support system high contrast settings
- **Font Scaling**: Respect system font size preferences
- **Focus Indicators**: Clear visual focus indicators for all interactive elements

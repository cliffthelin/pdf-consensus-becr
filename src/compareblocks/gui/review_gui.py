# src/compareblocks/gui/review_gui.py
"""
Main Review GUI with PDF Visualization.
Integrates PDF viewer, variations panel, and import capabilities for comprehensive review workflow.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QStatusBar, QLabel, QPushButton, QComboBox, QSpinBox,
    QGroupBox, QMessageBox, QProgressBar, QFileDialog, QCheckBox,
    QFrame, QTabWidget, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QAction, QFont, QColor

from .pdf_viewer import PDFViewer, BlockHighlight
from .variations_panel import VariationsPanel, VariationDisplayData
from .import_dialog import ImportDialog
from ..gbg.types import BoundingBox
from ..gbg.processor import GBGProcessor
from ..consensus.score import ConsensusScorer, VariationScore
from ..mapping.variation_block import VariationBlock, VariationType
from ..io.loader import NDJSONLoader
from ..io.writer import NDJSONWriter
from ..config.file_manager import file_manager


class ReviewDataManager:
    """Manages data for the review GUI."""
    
    def __init__(self):
        self.current_pdf_path = None
        self.gbg_results = None
        self.variation_blocks: Dict[str, List[VariationBlock]] = {}  # block_id -> variations
        self.consensus_decisions: Dict[str, str] = {}  # block_id -> selected_variation_id
        self.manual_corrections: Dict[str, str] = {}  # block_id -> corrected_text
        
        # Components
        self.gbg_processor = GBGProcessor()
        self.consensus_scorer = ConsensusScorer()
        self.ndjson_loader = NDJSONLoader()
        self.ndjson_writer = NDJSONWriter()
    
    def load_pdf(self, pdf_path: str) -> bool:
        """Load a PDF and generate GBG analysis."""
        try:
            self.current_pdf_path = pdf_path
            
            # Generate GBG analysis
            output_path = Path("output") / f"{Path(pdf_path).stem}_gbg_analysis.json"
            self.gbg_results = self.gbg_processor.process_pdf(pdf_path, str(output_path))
            
            # Initialize variation blocks from GBG results
            self._initialize_seed_variations()
            
            return True
        except Exception as e:
            print(f"Error loading PDF: {e}")
            return False
    
    def _initialize_seed_variations(self):
        """Initialize seed variations from GBG results."""
        self.variation_blocks.clear()
        
        if not self.gbg_results:
            return
        
        for page_num, page_data in self.gbg_results["pages"].items():
            for block in page_data["blocks"]:
                if not block.get("text_content"):
                    continue
                
                block_id = block["block_id"]
                
                # Create seed variation
                seed_variation = VariationBlock(
                    variation_id=f"seed_{block_id}",
                    doc_id=self.gbg_results["pdf_name"],
                    page=int(page_num) + 1,  # Convert to 1-based
                    raw_text=block["text_content"],
                    engine="pymupdf",
                    bbox=BoundingBox(
                        x=block["bbox"]["x"],
                        y=block["bbox"]["y"],
                        width=block["bbox"]["width"],
                        height=block["bbox"]["height"]
                    ),
                    block_id=block_id,
                    confidence=block["orientation_hints"]["confidence"],
                    variation_type=VariationType.SEED
                )
                
                self.variation_blocks[block_id] = [seed_variation]
                self.consensus_decisions[block_id] = seed_variation.variation_id
    
    def add_external_variations(self, variations: List[Dict[str, Any]]) -> int:
        """Add external variations from NDJSON import."""
        added_count = 0
        
        for var_data in variations:
            try:
                # Create variation block
                variation = VariationBlock(
                    variation_id=f"ext_{var_data['engine']}_{added_count}",
                    doc_id=var_data["doc_id"],
                    page=var_data["page"],
                    raw_text=var_data["raw_text"],
                    engine=var_data["engine"],
                    bbox=BoundingBox(*var_data.get("bbox", [0, 0, 0, 0])),
                    block_id=var_data.get("block_id"),
                    confidence=var_data.get("confidence", 0.0),
                    orientation=var_data.get("orientation"),
                    variation_type=VariationType.EXTERNAL,
                    original_metadata=var_data.get("metadata", {})
                )
                
                # Map to existing block or create new one
                target_block_id = self._map_variation_to_block(variation)
                
                if target_block_id:
                    if target_block_id not in self.variation_blocks:
                        self.variation_blocks[target_block_id] = []
                    
                    self.variation_blocks[target_block_id].append(variation)
                    added_count += 1
                
            except Exception as e:
                print(f"Error adding variation: {e}")
                continue
        
        return added_count
    
    def _map_variation_to_block(self, variation: VariationBlock) -> Optional[str]:
        """Map a variation to an existing block."""
        # If block_id is provided, use it directly
        if variation.block_id and variation.block_id in self.variation_blocks:
            return variation.block_id
        
        # Otherwise, find best matching block by IoU
        best_match = None
        best_iou = 0.0
        
        for block_id, existing_variations in self.variation_blocks.items():
            if not existing_variations:
                continue
            
            seed_variation = existing_variations[0]  # Use seed variation for comparison
            
            # Check if same page
            if seed_variation.page != variation.page:
                continue
            
            # Calculate IoU
            iou = self._calculate_iou(variation.bbox, seed_variation.bbox)
            
            if iou > best_iou and iou > 0.3:  # Minimum IoU threshold
                best_match = block_id
                best_iou = iou
        
        return best_match
    
    def _calculate_iou(self, bbox1: BoundingBox, bbox2: BoundingBox) -> float:
        """Calculate Intersection over Union for two bounding boxes."""
        # Calculate intersection
        x1 = max(bbox1.x, bbox2.x)
        y1 = max(bbox1.y, bbox2.y)
        x2 = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        y2 = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        
        # Calculate union
        area1 = bbox1.width * bbox1.height
        area2 = bbox2.width * bbox2.height
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def get_page_blocks(self, page_num: int) -> List[Tuple[str, BoundingBox]]:
        """Get all blocks for a specific page."""
        page_blocks = []
        
        for block_id, variations in self.variation_blocks.items():
            if variations and variations[0].page == page_num:
                seed_variation = variations[0]
                page_blocks.append((block_id, seed_variation.bbox))
        
        return page_blocks
    
    def get_block_variations(self, block_id: str) -> List[VariationDisplayData]:
        """Get variation display data for a block."""
        if block_id not in self.variation_blocks:
            return []
        
        variations = self.variation_blocks[block_id]
        display_data = []
        
        # Score variations
        scored_variations = self._score_variations(variations)
        
        for i, (variation, score) in enumerate(zip(variations, scored_variations)):
            is_consensus = (self.consensus_decisions.get(block_id) == variation.variation_id)
            
            display_data.append(VariationDisplayData(
                variation_id=variation.variation_id,
                engine_name=variation.engine,
                raw_text=variation.raw_text,
                confidence=variation.confidence,
                length_score=score.length_score if score else 0.0,
                language_score=score.language_score if score else 0.0,
                anomaly_score=score.anomaly_score if score else 0.0,
                final_score=score.final_score if score else 0.0,
                flags=score.flags if score else [],
                is_consensus=is_consensus
            ))
        
        return display_data
    
    def _score_variations(self, variations: List[VariationBlock]) -> List[Optional[VariationScore]]:
        """Score variations using consensus scorer."""
        if len(variations) <= 1:
            return [None] * len(variations)
        
        try:
            # Convert to format expected by scorer
            variation_texts = [v.raw_text for v in variations]
            
            # Score variations (simplified - full implementation would use all features)
            scores = []
            for i, variation in enumerate(variations):
                # Create a basic score
                score = VariationScore(
                    variation_index=i,
                    engine_name=variation.engine,
                    raw_text=variation.raw_text,
                    length_score=min(1.0, len(variation.raw_text) / 100.0),
                    language_score=variation.confidence,
                    anomaly_score=1.0 - variation.confidence,
                    context_score=0.5,
                    orientation_penalty=0.0,
                    weighted_score=variation.confidence,
                    final_score=variation.confidence,
                    score_components={},
                    flags=[]
                )
                scores.append(score)
            
            return scores
        except Exception as e:
            print(f"Error scoring variations: {e}")
            return [None] * len(variations)
    
    def set_consensus_decision(self, block_id: str, variation_id: str):
        """Set the consensus decision for a block."""
        self.consensus_decisions[block_id] = variation_id
    
    def set_manual_correction(self, block_id: str, corrected_text: str):
        """Set a manual correction for a block."""
        self.manual_corrections[block_id] = corrected_text
        
        # Create a manual variation
        manual_variation_id = f"manual_{block_id}"
        self.consensus_decisions[block_id] = manual_variation_id
    
    def export_consensus(self, output_path: str) -> bool:
        """Export consensus decisions to NDJSON."""
        try:
            consensus_records = []
            
            for block_id, selected_variation_id in self.consensus_decisions.items():
                if block_id not in self.variation_blocks:
                    continue
                
                variations = self.variation_blocks[block_id]
                selected_variation = None
                
                # Find selected variation
                for variation in variations:
                    if variation.variation_id == selected_variation_id:
                        selected_variation = variation
                        break
                
                if not selected_variation:
                    continue
                
                # Check for manual correction
                final_text = self.manual_corrections.get(block_id, selected_variation.raw_text)
                decision_reason = "manual_override" if block_id in self.manual_corrections else "highest_score"
                
                # Create consensus record
                record = {
                    "doc_id": selected_variation.doc_id,
                    "page": selected_variation.page,
                    "block_id": block_id,
                    "selected_engine": selected_variation.engine,
                    "final_text": final_text,
                    "decision_reason": decision_reason,
                    "engine_scores": {selected_variation.engine: selected_variation.confidence},
                    "anomaly_score": 1.0 - selected_variation.confidence,
                    "bbox": [
                        selected_variation.bbox.x,
                        selected_variation.bbox.y,
                        selected_variation.bbox.width,
                        selected_variation.bbox.height
                    ]
                }
                
                consensus_records.append(record)
            
            # Write to file
            self.ndjson_writer.write_file(consensus_records, output_path, overwrite=True)
            return True
            
        except Exception as e:
            print(f"Error exporting consensus: {e}")
            return False


class ReviewGUI(QMainWindow):
    """Main Review GUI with PDF Visualization."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BECR Review GUI - PDF Visualization & Variations Comparison")
        self.setMinimumSize(1200, 800)
        
        # Data manager
        self.data_manager = ReviewDataManager()
        
        # Current state
        self.current_page = 1
        self.selected_block_id = None
        
        self.setup_ui()
        self.setup_menus()
        self.setup_status_bar()
        
        # Connect signals
        self.connect_signals()
    
    def setup_ui(self):
        """Setup the main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        
        # Main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - PDF viewer
        pdf_group = QGroupBox("PDF Document")
        pdf_layout = QVBoxLayout(pdf_group)
        
        self.pdf_viewer = PDFViewer()
        pdf_layout.addWidget(self.pdf_viewer)
        
        main_splitter.addWidget(pdf_group)
        
        # Right panel - Variations and controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Filter controls
        filter_group = QGroupBox("Filters & Navigation")
        filter_layout = QHBoxLayout(filter_group)
        
        filter_layout.addWidget(QLabel("Min Variations:"))
        self.min_variations_filter = QSpinBox()
        self.min_variations_filter.setMinimum(1)
        self.min_variations_filter.setMaximum(10)
        self.min_variations_filter.setValue(2)
        self.min_variations_filter.valueChanged.connect(self.apply_block_filters)
        filter_layout.addWidget(self.min_variations_filter)
        
        self.flagged_only_checkbox = QCheckBox("Flagged blocks only")
        self.flagged_only_checkbox.stateChanged.connect(self.apply_block_filters)
        filter_layout.addWidget(self.flagged_only_checkbox)
        
        filter_layout.addStretch()
        
        # Navigation buttons
        self.prev_block_button = QPushButton("◀ Previous Block")
        self.prev_block_button.clicked.connect(self.previous_block)
        filter_layout.addWidget(self.prev_block_button)
        
        self.next_block_button = QPushButton("Next Block ▶")
        self.next_block_button.clicked.connect(self.next_block)
        filter_layout.addWidget(self.next_block_button)
        
        right_layout.addWidget(filter_group)
        
        # Variations panel
        self.variations_panel = VariationsPanel()
        right_layout.addWidget(self.variations_panel)
        
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions (60% PDF, 40% variations)
        main_splitter.setSizes([600, 400])
        
        layout.addWidget(main_splitter)
    
    def setup_menus(self):
        """Setup application menus."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_pdf_action = QAction("Open PDF...", self)
        open_pdf_action.triggered.connect(self.open_pdf)
        file_menu.addAction(open_pdf_action)
        
        file_menu.addSeparator()
        
        import_variations_action = QAction("Import Variations...", self)
        import_variations_action.triggered.connect(self.import_variations)
        file_menu.addAction(import_variations_action)
        
        file_menu.addSeparator()
        
        export_consensus_action = QAction("Export Consensus...", self)
        export_consensus_action.triggered.connect(self.export_consensus)
        file_menu.addAction(export_consensus_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        fit_width_action = QAction("Fit Width", self)
        fit_width_action.triggered.connect(self.pdf_viewer.fit_width)
        view_menu.addAction(fit_width_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        recalc_surrounding_action = QAction("Recalculate Surrounding Blocks", self)
        recalc_surrounding_action.triggered.connect(self.recalculate_surrounding_blocks)
        tools_menu.addAction(recalc_surrounding_action)
        
        preview_changes_action = QAction("Preview Changes", self)
        preview_changes_action.triggered.connect(self.preview_changes)
        tools_menu.addAction(preview_changes_action)
    
    def setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = self.statusBar()
        
        # Status labels
        self.pdf_status_label = QLabel("No PDF loaded")
        self.status_bar.addWidget(self.pdf_status_label)
        
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        self.block_status_label = QLabel("No block selected")
        self.status_bar.addPermanentWidget(self.block_status_label)
        
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        self.variations_status_label = QLabel("0 variations")
        self.status_bar.addPermanentWidget(self.variations_status_label)
    
    def connect_signals(self):
        """Connect UI signals."""
        # PDF viewer signals
        self.pdf_viewer.pageChanged.connect(self.on_page_changed)
        self.pdf_viewer.blockSelected.connect(self.on_block_selected)
        
        # Variations panel signals
        self.variations_panel.variationSelected.connect(self.on_variation_selected)
        self.variations_panel.consensusChanged.connect(self.on_consensus_changed)
        self.variations_panel.manualCorrectionRequested.connect(self.on_manual_correction)
    
    def open_pdf(self):
        """Open a PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf)"
        )
        
        if file_path:
            self.load_pdf(file_path)
    
    def load_pdf(self, pdf_path: str):
        """Load a PDF file."""
        # Show progress
        progress = QProgressBar()
        progress.setRange(0, 0)  # Indeterminate
        self.status_bar.addWidget(progress)
        
        try:
            # Load PDF in data manager
            if self.data_manager.load_pdf(pdf_path):
                # Load PDF in viewer
                if self.pdf_viewer.load_pdf(pdf_path):
                    self.pdf_status_label.setText(f"PDF: {Path(pdf_path).name}")
                    
                    # Go to first page
                    self.pdf_viewer.go_to_page(1)
                    self.on_page_changed(1)
                    
                    QMessageBox.information(self, "Success", "PDF loaded successfully!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to load PDF in viewer.")
            else:
                QMessageBox.critical(self, "Error", "Failed to process PDF.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PDF: {str(e)}")
        
        finally:
            self.status_bar.removeWidget(progress)
    
    def import_variations(self):
        """Import external variations."""
        dialog = ImportDialog(self)
        dialog.importRequested.connect(self.on_import_requested)
        dialog.exec()
    
    def on_import_requested(self, file_path: str, options: Dict[str, Any], 
                           records: List[Dict[str, Any]]):
        """Handle import request."""
        try:
            added_count = self.data_manager.add_external_variations(records)
            
            QMessageBox.information(self, "Import Complete", 
                                  f"Successfully imported {added_count} variations.")
            
            # Refresh current view
            if self.selected_block_id:
                self.on_block_selected(self.selected_block_id)
            
            self.update_page_highlights()
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import variations: {str(e)}")
    
    def export_consensus(self):
        """Export consensus decisions."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Consensus", "", "NDJSON Files (*.ndjson)"
        )
        
        if file_path:
            try:
                if self.data_manager.export_consensus(file_path):
                    QMessageBox.information(self, "Export Complete", 
                                          f"Consensus exported to {file_path}")
                else:
                    QMessageBox.critical(self, "Export Error", "Failed to export consensus.")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Export failed: {str(e)}")
    
    def on_page_changed(self, page_num: int):
        """Handle page change."""
        self.current_page = page_num
        self.update_page_highlights()
    
    def update_page_highlights(self):
        """Update block highlights for the current page."""
        if not self.data_manager.gbg_results:
            return
        
        page_blocks = self.data_manager.get_page_blocks(self.current_page)
        
        highlights = []
        for block_id, bbox in page_blocks:
            # Determine highlight color based on variation count
            variations = self.data_manager.variation_blocks.get(block_id, [])
            variation_count = len(variations)
            
            if variation_count == 1:
                color = QColor(100, 100, 100)  # Gray for single variation
            elif variation_count <= 3:
                color = QColor(0, 150, 0)      # Green for few variations
            elif variation_count <= 5:
                color = QColor(255, 165, 0)    # Orange for moderate variations
            else:
                color = QColor(255, 0, 0)      # Red for many variations
            
            # Apply filters
            if self.should_show_block(block_id, variations):
                highlights.append(BlockHighlight(
                    block_id=block_id,
                    bbox=bbox,
                    color=color,
                    label=f"{variation_count}",
                    is_selected=(block_id == self.selected_block_id)
                ))
        
        self.pdf_viewer.set_block_highlights(highlights)
    
    def should_show_block(self, block_id: str, variations: List) -> bool:
        """Check if block should be shown based on filters."""
        # Min variations filter
        if len(variations) < self.min_variations_filter.value():
            return False
        
        # Flagged only filter
        if self.flagged_only_checkbox.isChecked():
            # Check if any variation has flags (simplified check)
            has_flags = any(v.confidence < 0.5 for v in variations)
            if not has_flags:
                return False
        
        return True
    
    def apply_block_filters(self):
        """Apply block filters and update display."""
        self.update_page_highlights()
    
    def on_block_selected(self, block_id: str):
        """Handle block selection."""
        self.selected_block_id = block_id
        
        # Update PDF viewer selection
        self.pdf_viewer.select_block(block_id)
        
        # Update variations panel
        variations = self.data_manager.get_block_variations(block_id)
        self.variations_panel.set_block_variations(block_id, variations)
        
        # Update status
        self.block_status_label.setText(f"Block: {block_id[:12]}...")
        self.variations_status_label.setText(f"{len(variations)} variations")
    
    def on_variation_selected(self, variation_id: str):
        """Handle variation selection."""
        self.variations_panel.select_variation(variation_id)
    
    def on_consensus_changed(self, variation_id: str):
        """Handle consensus decision change."""
        if self.selected_block_id:
            self.data_manager.set_consensus_decision(self.selected_block_id, variation_id)
            self.variations_panel.set_consensus_variation(variation_id)
    
    def on_manual_correction(self, block_id: str, corrected_text: str):
        """Handle manual correction."""
        self.data_manager.set_manual_correction(block_id, corrected_text)
        
        # Refresh variations display
        if block_id == self.selected_block_id:
            variations = self.data_manager.get_block_variations(block_id)
            self.variations_panel.set_block_variations(block_id, variations)
    
    def previous_block(self):
        """Navigate to previous block with variations."""
        # Implementation would find previous block with variations
        pass
    
    def next_block(self):
        """Navigate to next block with variations."""
        # Implementation would find next block with variations
        pass
    
    def recalculate_surrounding_blocks(self):
        """Recalculate surrounding blocks after changes."""
        if not self.selected_block_id:
            QMessageBox.information(self, "No Selection", "Please select a block first.")
            return
        
        # Implementation would recalculate surrounding blocks
        QMessageBox.information(self, "Recalculation", 
                              "Surrounding blocks recalculation not yet implemented.")
    
    def preview_changes(self):
        """Preview changes from one file to another."""
        QMessageBox.information(self, "Preview", 
                              "Change preview functionality not yet implemented.")


def main():
    """Main entry point for the Review GUI."""
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("BECR Review GUI")
    app.setApplicationDisplayName("BECR - PDF Review & Variations Comparison")
    app.setApplicationVersion("1.0.0")
    
    # Create and show main window
    main_window = ReviewGUI()
    main_window.show()
    
    # Load default PDF if available
    try:
        default_pdf = file_manager.get_target_pdf_path()
        if Path(default_pdf).exists():
            main_window.load_pdf(default_pdf)
    except Exception as e:
        print(f"Could not load default PDF: {e}")
    
    return app.exec()


if __name__ == "__main__":
    main()
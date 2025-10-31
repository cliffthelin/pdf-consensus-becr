# src/compareblocks/gui/variations_panel.py
"""
Variations comparison panel with metrics, diff highlighting, and selection controls.
Displays text variations in a table format with quality metrics and manual override capabilities.
"""

import difflib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel, QTextEdit, QSplitter, QGroupBox,
    QComboBox, QSpinBox, QCheckBox, QFrame, QScrollArea, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush, QTextCharFormat, QTextCursor

from ..consensus.score import VariationScore
from ..mapping.variation_block import VariationBlock


@dataclass
class VariationDisplayData:
    """Data for displaying a variation in the comparison table."""
    variation_id: str
    engine_name: str
    raw_text: str
    confidence: float
    length_score: float
    language_score: float
    anomaly_score: float
    final_score: float
    flags: List[str]
    is_selected: bool = False
    is_consensus: bool = False


class TextDiffWidget(QTextEdit):
    """Widget for displaying text with diff highlighting."""
    
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumHeight(150)
        self.setFont(QFont("Consolas", 10))
    
    def set_diff_text(self, text: str, reference_text: str = ""):
        """Set text with diff highlighting against reference."""
        self.clear()
        
        if not reference_text:
            # No diff, just display text
            self.setPlainText(text)
            return
        
        # Generate diff
        diff = list(difflib.unified_diff(
            reference_text.splitlines(keepends=True),
            text.splitlines(keepends=True),
            lineterm='',
            n=0
        ))
        
        cursor = self.textCursor()
        
        # Format for additions (green)
        add_format = QTextCharFormat()
        add_format.setBackground(QColor(200, 255, 200))
        
        # Format for deletions (red)
        del_format = QTextCharFormat()
        del_format.setBackground(QColor(255, 200, 200))
        
        # Format for unchanged (normal)
        normal_format = QTextCharFormat()
        
        if not diff:
            # No differences
            cursor.insertText(text, normal_format)
        else:
            # Process diff and highlight changes
            lines = text.splitlines(keepends=True)
            ref_lines = reference_text.splitlines(keepends=True)
            
            # Simple character-level diff for short texts
            if len(text) < 500 and len(reference_text) < 500:
                self._insert_char_diff(cursor, text, reference_text, add_format, del_format, normal_format)
            else:
                # Line-level diff for longer texts
                cursor.insertText(text, normal_format)
    
    def _insert_char_diff(self, cursor, text, reference_text, add_format, del_format, normal_format):
        """Insert character-level diff highlighting."""
        matcher = difflib.SequenceMatcher(None, reference_text, text)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                cursor.insertText(text[j1:j2], normal_format)
            elif tag == 'replace':
                cursor.insertText(text[j1:j2], add_format)
            elif tag == 'delete':
                # Show deleted text from reference in red
                cursor.insertText(f"[DEL: {reference_text[i1:i2]}]", del_format)
            elif tag == 'insert':
                cursor.insertText(text[j1:j2], add_format)


class VariationsTable(QTableWidget):
    """Table widget for displaying text variations with metrics."""
    
    variationSelected = Signal(str)  # variation_id
    consensusChanged = Signal(str)   # variation_id
    
    def __init__(self):
        super().__init__()
        self.setup_table()
        self.variations_data: List[VariationDisplayData] = []
        
    def setup_table(self):
        """Setup the variations table."""
        # Define columns
        columns = [
            "Engine", "Text Preview", "Confidence", "Length", 
            "Language", "Anomaly", "Final Score", "Flags", "Actions"
        ]
        
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        # Configure table
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        
        # Set column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Engine
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Text Preview
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Confidence
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Length
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Language
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Anomaly
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Final Score
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Flags
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Actions
        
        # Connect selection
        self.itemSelectionChanged.connect(self._on_selection_changed)
    
    def set_variations(self, variations: List[VariationDisplayData]):
        """Set the variations to display."""
        self.variations_data = variations
        self.setRowCount(len(variations))
        
        for row, variation in enumerate(variations):
            self._populate_row(row, variation)
    
    def _populate_row(self, row: int, variation: VariationDisplayData):
        """Populate a single table row."""
        # Engine name
        engine_item = QTableWidgetItem(variation.engine_name)
        if variation.is_consensus:
            engine_item.setBackground(QBrush(QColor(200, 255, 200)))  # Light green
        self.setItem(row, 0, engine_item)
        
        # Text preview (first 100 characters)
        text_preview = variation.raw_text[:100] + ("..." if len(variation.raw_text) > 100 else "")
        text_item = QTableWidgetItem(text_preview)
        text_item.setToolTip(variation.raw_text)  # Full text in tooltip
        if variation.is_consensus:
            text_item.setBackground(QBrush(QColor(200, 255, 200)))
        self.setItem(row, 1, text_item)
        
        # Metrics
        self.setItem(row, 2, QTableWidgetItem(f"{variation.confidence:.3f}"))
        self.setItem(row, 3, QTableWidgetItem(f"{variation.length_score:.3f}"))
        self.setItem(row, 4, QTableWidgetItem(f"{variation.language_score:.3f}"))
        self.setItem(row, 5, QTableWidgetItem(f"{variation.anomaly_score:.3f}"))
        
        # Final score with color coding
        score_item = QTableWidgetItem(f"{variation.final_score:.3f}")
        if variation.final_score > 0.7:
            score_item.setBackground(QBrush(QColor(200, 255, 200)))  # Green
        elif variation.final_score < 0.3:
            score_item.setBackground(QBrush(QColor(255, 200, 200)))  # Red
        else:
            score_item.setBackground(QBrush(QColor(255, 255, 200)))  # Yellow
        self.setItem(row, 6, score_item)
        
        # Flags
        flags_text = ", ".join(variation.flags) if variation.flags else ""
        self.setItem(row, 7, QTableWidgetItem(flags_text))
        
        # Actions button
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(2, 2, 2, 2)
        
        select_button = QPushButton("Select")
        select_button.clicked.connect(lambda: self.consensusChanged.emit(variation.variation_id))
        actions_layout.addWidget(select_button)
        
        self.setCellWidget(row, 8, actions_widget)
    
    def _on_selection_changed(self):
        """Handle row selection changes."""
        current_row = self.currentRow()
        if 0 <= current_row < len(self.variations_data):
            variation = self.variations_data[current_row]
            self.variationSelected.emit(variation.variation_id)
    
    def highlight_consensus(self, variation_id: str):
        """Highlight the consensus variation."""
        for i, variation in enumerate(self.variations_data):
            variation.is_consensus = (variation.variation_id == variation_id)
        
        # Refresh display
        self.set_variations(self.variations_data)


class VariationsPanel(QWidget):
    """Complete variations comparison panel."""
    
    variationSelected = Signal(str)  # variation_id
    consensusChanged = Signal(str)   # variation_id
    manualCorrectionRequested = Signal(str, str)  # block_id, corrected_text
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
        # Current state
        self.current_block_id = None
        self.current_variations: List[VariationDisplayData] = []
        self.selected_variation_id = None
        
    def setup_ui(self):
        """Setup the variations panel UI."""
        layout = QVBoxLayout(self)
        
        # Header with block info
        header_layout = QHBoxLayout()
        
        self.block_info_label = QLabel("No block selected")
        self.block_info_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(self.block_info_label)
        
        header_layout.addStretch()
        
        # Filter controls
        header_layout.addWidget(QLabel("Filter:"))
        self.engine_filter = QComboBox()
        self.engine_filter.addItem("All Engines")
        self.engine_filter.currentTextChanged.connect(self._apply_filters)
        header_layout.addWidget(self.engine_filter)
        
        self.min_variations_filter = QSpinBox()
        self.min_variations_filter.setMinimum(1)
        self.min_variations_filter.setMaximum(10)
        self.min_variations_filter.setValue(1)
        self.min_variations_filter.setPrefix("Min variations: ")
        self.min_variations_filter.valueChanged.connect(self._apply_filters)
        header_layout.addWidget(self.min_variations_filter)
        
        layout.addLayout(header_layout)
        
        # Main content splitter
        splitter = QSplitter(Qt.Vertical)
        
        # Variations table
        table_group = QGroupBox("Text Variations")
        table_layout = QVBoxLayout(table_group)
        
        self.variations_table = VariationsTable()
        self.variations_table.variationSelected.connect(self.variationSelected.emit)
        self.variations_table.consensusChanged.connect(self.consensusChanged.emit)
        table_layout.addWidget(self.variations_table)
        
        splitter.addWidget(table_group)
        
        # Text comparison area
        comparison_group = QGroupBox("Text Comparison")
        comparison_layout = QVBoxLayout(comparison_group)
        
        # Selected variation display
        self.selected_text_widget = TextDiffWidget()
        comparison_layout.addWidget(QLabel("Selected Variation:"))
        comparison_layout.addWidget(self.selected_text_widget)
        
        # Manual correction area
        correction_layout = QHBoxLayout()
        
        self.manual_correction_button = QPushButton("Manual Correction")
        self.manual_correction_button.clicked.connect(self._show_manual_correction_dialog)
        correction_layout.addWidget(self.manual_correction_button)
        
        self.merge_variations_button = QPushButton("Merge Variations")
        self.merge_variations_button.clicked.connect(self._show_merge_dialog)
        correction_layout.addWidget(self.merge_variations_button)
        
        correction_layout.addStretch()
        
        comparison_layout.addLayout(correction_layout)
        
        splitter.addWidget(comparison_group)
        
        # Set splitter proportions
        splitter.setSizes([400, 200])
        layout.addWidget(splitter)
        
        # Initially disable controls
        self.set_controls_enabled(False)
    
    def set_block_variations(self, block_id: str, variations: List[VariationDisplayData]):
        """Set the variations for a specific block."""
        self.current_block_id = block_id
        self.current_variations = variations
        
        # Update block info
        self.block_info_label.setText(f"Block: {block_id[:12]}... ({len(variations)} variations)")
        
        # Update engine filter
        engines = set(v.engine_name for v in variations)
        self.engine_filter.clear()
        self.engine_filter.addItem("All Engines")
        for engine in sorted(engines):
            self.engine_filter.addItem(engine)
        
        # Display variations
        self._apply_filters()
        self.set_controls_enabled(True)
    
    def select_variation(self, variation_id: str):
        """Select a specific variation for detailed view."""
        self.selected_variation_id = variation_id
        
        # Find the variation
        selected_variation = None
        for variation in self.current_variations:
            if variation.variation_id == variation_id:
                selected_variation = variation
                break
        
        if selected_variation:
            # Show text with diff against consensus
            consensus_text = ""
            for v in self.current_variations:
                if v.is_consensus:
                    consensus_text = v.raw_text
                    break
            
            self.selected_text_widget.set_diff_text(selected_variation.raw_text, consensus_text)
    
    def set_consensus_variation(self, variation_id: str):
        """Set the consensus variation."""
        self.variations_table.highlight_consensus(variation_id)
        
        # Update diff display if a variation is selected
        if self.selected_variation_id:
            self.select_variation(self.selected_variation_id)
    
    def _apply_filters(self):
        """Apply current filters to the variations display."""
        if not self.current_variations:
            return
        
        # Filter by engine
        engine_filter = self.engine_filter.currentText()
        filtered_variations = self.current_variations
        
        if engine_filter != "All Engines":
            filtered_variations = [v for v in filtered_variations if v.engine_name == engine_filter]
        
        # Display filtered variations
        self.variations_table.set_variations(filtered_variations)
    
    def _show_manual_correction_dialog(self):
        """Show dialog for manual text correction."""
        if not self.current_block_id:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Manual Text Correction")
        dialog.setMinimumSize(500, 300)
        
        layout = QFormLayout(dialog)
        
        # Current consensus text
        consensus_text = ""
        for variation in self.current_variations:
            if variation.is_consensus:
                consensus_text = variation.raw_text
                break
        
        layout.addRow("Current Text:", QLabel(consensus_text))
        
        # Correction text area
        correction_edit = QTextEdit()
        correction_edit.setPlainText(consensus_text)
        layout.addRow("Corrected Text:", correction_edit)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            corrected_text = correction_edit.toPlainText().strip()
            if corrected_text and corrected_text != consensus_text:
                self.manualCorrectionRequested.emit(self.current_block_id, corrected_text)
    
    def _show_merge_dialog(self):
        """Show dialog for merging multiple variations."""
        if not self.current_variations or len(self.current_variations) < 2:
            QMessageBox.information(self, "Merge Variations", 
                                  "Need at least 2 variations to merge.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Merge Variations")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        layout.addWidget(QLabel("Select text parts from different variations to create a merged result:"))
        
        # Variation selection area
        variations_layout = QVBoxLayout()
        
        checkboxes = []
        text_edits = []
        
        for i, variation in enumerate(self.current_variations):
            var_group = QGroupBox(f"{variation.engine_name} (Score: {variation.final_score:.3f})")
            var_layout = QVBoxLayout(var_group)
            
            checkbox = QCheckBox("Include in merge")
            checkboxes.append(checkbox)
            var_layout.addWidget(checkbox)
            
            text_edit = QTextEdit()
            text_edit.setPlainText(variation.raw_text)
            text_edit.setMaximumHeight(80)
            text_edits.append(text_edit)
            var_layout.addWidget(text_edit)
            
            variations_layout.addWidget(var_group)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(variations_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Merged result preview
        layout.addWidget(QLabel("Merged Result Preview:"))
        merged_preview = QTextEdit()
        merged_preview.setMaximumHeight(100)
        layout.addWidget(merged_preview)
        
        # Update preview when selections change
        def update_preview():
            merged_parts = []
            for i, checkbox in enumerate(checkboxes):
                if checkbox.isChecked():
                    text = text_edits[i].toPlainText().strip()
                    if text:
                        merged_parts.append(text)
            merged_preview.setPlainText(" ".join(merged_parts))
        
        for checkbox in checkboxes:
            checkbox.stateChanged.connect(update_preview)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            merged_text = merged_preview.toPlainText().strip()
            if merged_text:
                self.manualCorrectionRequested.emit(self.current_block_id, merged_text)
    
    def set_controls_enabled(self, enabled: bool):
        """Enable or disable panel controls."""
        self.variations_table.setEnabled(enabled)
        self.engine_filter.setEnabled(enabled)
        self.min_variations_filter.setEnabled(enabled)
        self.manual_correction_button.setEnabled(enabled)
        self.merge_variations_button.setEnabled(enabled)
# src/compareblocks/gui/import_dialog.py
"""
Import dialog for external NDJSON variations.
Supports comprehensive NDJSON format with all associated files.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QCheckBox,
    QComboBox, QSpinBox, QDialogButtonBox, QTabWidget, QSplitter, QWidget
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

from ..io.loader import NDJSONLoader
from ..io.schemas import INPUT_VARIATION_SCHEMA


class ValidationWorker(QThread):
    """Worker thread for validating NDJSON files."""
    
    validationComplete = Signal(bool, str, list)  # success, message, records
    progressUpdate = Signal(int, str)  # progress, status
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.loader = NDJSONLoader()
    
    def run(self):
        """Run validation in background thread."""
        try:
            self.progressUpdate.emit(10, "Loading NDJSON file...")
            
            # Load and validate file
            records = self.loader.load_file(self.file_path)
            
            self.progressUpdate.emit(50, f"Validating {len(records)} records...")
            
            # Additional validation checks
            validation_errors = []
            
            for i, record in enumerate(records):
                if i % 100 == 0:  # Update progress every 100 records
                    progress = 50 + int((i / len(records)) * 40)
                    self.progressUpdate.emit(progress, f"Validating record {i+1}/{len(records)}")
                
                # Check for required fields
                if not record.get('doc_id'):
                    validation_errors.append(f"Record {i+1}: Missing doc_id")
                if not record.get('engine'):
                    validation_errors.append(f"Record {i+1}: Missing engine")
                if 'raw_text' not in record:
                    validation_errors.append(f"Record {i+1}: Missing raw_text")
            
            self.progressUpdate.emit(100, "Validation complete")
            
            if validation_errors:
                error_msg = f"Validation failed with {len(validation_errors)} errors:\n"
                error_msg += "\n".join(validation_errors[:10])  # Show first 10 errors
                if len(validation_errors) > 10:
                    error_msg += f"\n... and {len(validation_errors) - 10} more errors"
                
                self.validationComplete.emit(False, error_msg, [])
            else:
                self.validationComplete.emit(True, f"Successfully validated {len(records)} records", records)
        
        except Exception as e:
            self.validationComplete.emit(False, f"Validation error: {str(e)}", [])


class NDJSONPreviewWidget(QWidget):
    """Widget for previewing NDJSON file contents."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.records: List[Dict[str, Any]] = []
    
    def setup_ui(self):
        """Setup the preview UI."""
        layout = QVBoxLayout(self)
        
        # Summary info
        self.summary_label = QLabel("No file loaded")
        self.summary_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(self.summary_label)
        
        # Records table
        self.records_table = QTableWidget()
        self.records_table.setAlternatingRowColors(True)
        layout.addWidget(self.records_table)
        
        # Sample record display
        layout.addWidget(QLabel("Sample Record:"))
        self.sample_text = QTextEdit()
        self.sample_text.setMaximumHeight(150)
        self.sample_text.setFont(QFont("Consolas", 9))
        self.sample_text.setReadOnly(True)
        layout.addWidget(self.sample_text)
    
    def set_records(self, records: List[Dict[str, Any]]):
        """Set the records to preview."""
        self.records = records
        
        if not records:
            self.summary_label.setText("No records to display")
            self.records_table.setRowCount(0)
            self.sample_text.clear()
            return
        
        # Update summary
        engines = set(r.get('engine', 'unknown') for r in records)
        docs = set(r.get('doc_id', 'unknown') for r in records)
        pages = set(r.get('page', 0) for r in records)
        
        summary = f"{len(records)} records | {len(engines)} engines | {len(docs)} documents | {len(pages)} pages"
        self.summary_label.setText(summary)
        
        # Setup table
        columns = ["Engine", "Doc ID", "Page", "Text Preview", "Confidence", "Block ID"]
        self.records_table.setColumnCount(len(columns))
        self.records_table.setHorizontalHeaderLabels(columns)
        
        # Show first 100 records
        display_records = records[:100]
        self.records_table.setRowCount(len(display_records))
        
        for row, record in enumerate(display_records):
            self.records_table.setItem(row, 0, QTableWidgetItem(str(record.get('engine', ''))))
            self.records_table.setItem(row, 1, QTableWidgetItem(str(record.get('doc_id', ''))))
            self.records_table.setItem(row, 2, QTableWidgetItem(str(record.get('page', ''))))
            
            # Text preview
            text = str(record.get('raw_text', ''))
            preview = text[:50] + ("..." if len(text) > 50 else "")
            self.records_table.setItem(row, 3, QTableWidgetItem(preview))
            
            self.records_table.setItem(row, 4, QTableWidgetItem(str(record.get('confidence', ''))))
            self.records_table.setItem(row, 5, QTableWidgetItem(str(record.get('block_id', ''))))
        
        # Auto-resize columns
        header = self.records_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Text preview column
        
        # Show sample record
        if records:
            sample_json = json.dumps(records[0], indent=2)
            self.sample_text.setPlainText(sample_json)


class ImportOptionsWidget(QWidget):
    """Widget for configuring import options."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the import options UI."""
        layout = QFormLayout(self)
        
        # Engine filtering
        self.engine_filter = QComboBox()
        self.engine_filter.addItem("Import All Engines")
        layout.addRow("Engine Filter:", self.engine_filter)
        
        # Page range
        page_layout = QHBoxLayout()
        self.page_from = QSpinBox()
        self.page_from.setMinimum(1)
        self.page_from.setMaximum(9999)
        self.page_from.setValue(1)
        page_layout.addWidget(self.page_from)
        
        page_layout.addWidget(QLabel("to"))
        
        self.page_to = QSpinBox()
        self.page_to.setMinimum(1)
        self.page_to.setMaximum(9999)
        self.page_to.setValue(9999)
        page_layout.addWidget(self.page_to)
        
        layout.addRow("Page Range:", page_layout)
        
        # Confidence threshold
        self.confidence_threshold = QSpinBox()
        self.confidence_threshold.setRange(0, 100)
        self.confidence_threshold.setValue(0)
        self.confidence_threshold.setSuffix("%")
        layout.addRow("Min Confidence:", self.confidence_threshold)
        
        # Block ID handling
        self.block_id_handling = QComboBox()
        self.block_id_handling.addItems([
            "Use provided block IDs",
            "Generate new block IDs",
            "Map to existing blocks"
        ])
        layout.addRow("Block ID Handling:", self.block_id_handling)
        
        # Duplicate handling
        self.duplicate_handling = QComboBox()
        self.duplicate_handling.addItems([
            "Keep all duplicates",
            "Keep highest confidence",
            "Skip duplicates"
        ])
        layout.addRow("Duplicate Handling:", self.duplicate_handling)
        
        # Associated files
        self.import_associated_files = QCheckBox("Import associated files")
        self.import_associated_files.setChecked(True)
        layout.addRow("Associated Files:", self.import_associated_files)
    
    def get_import_options(self) -> Dict[str, Any]:
        """Get the current import options."""
        return {
            'engine_filter': self.engine_filter.currentText(),
            'page_from': self.page_from.value(),
            'page_to': self.page_to.value(),
            'confidence_threshold': self.confidence_threshold.value() / 100.0,
            'block_id_handling': self.block_id_handling.currentText(),
            'duplicate_handling': self.duplicate_handling.currentText(),
            'import_associated_files': self.import_associated_files.isChecked()
        }
    
    def set_available_engines(self, engines: List[str]):
        """Set the available engines for filtering."""
        current = self.engine_filter.currentText()
        self.engine_filter.clear()
        self.engine_filter.addItem("Import All Engines")
        
        for engine in sorted(engines):
            self.engine_filter.addItem(f"Only {engine}")
        
        # Restore selection if possible
        index = self.engine_filter.findText(current)
        if index >= 0:
            self.engine_filter.setCurrentIndex(index)


class ImportDialog(QDialog):
    """Dialog for importing external NDJSON variations."""
    
    importRequested = Signal(str, dict, list)  # file_path, options, records
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import External NDJSON Variations")
        self.setMinimumSize(800, 600)
        
        self.setup_ui()
        
        # State
        self.current_file_path = ""
        self.validated_records: List[Dict[str, Any]] = []
        self.validation_worker = None
    
    def setup_ui(self):
        """Setup the import dialog UI."""
        layout = QVBoxLayout(self)
        
        # File selection
        file_group = QGroupBox("NDJSON File Selection")
        file_layout = QFormLayout(file_group)
        
        file_path_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        file_path_layout.addWidget(self.file_path_edit)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_file)
        file_path_layout.addWidget(self.browse_button)
        
        file_layout.addRow("File Path:", file_path_layout)
        
        # Validation status
        self.validation_status = QLabel("No file selected")
        file_layout.addRow("Status:", self.validation_status)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        file_layout.addRow("Progress:", self.progress_bar)
        
        layout.addWidget(file_group)
        
        # Main content tabs
        self.tab_widget = QTabWidget()
        
        # Preview tab
        self.preview_widget = NDJSONPreviewWidget()
        self.tab_widget.addTab(self.preview_widget, "Preview")
        
        # Import options tab
        self.options_widget = ImportOptionsWidget()
        self.tab_widget.addTab(self.options_widget, "Import Options")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.validate_button = QPushButton("Validate File")
        self.validate_button.clicked.connect(self.validate_file)
        self.validate_button.setEnabled(False)
        button_layout.addWidget(self.validate_button)
        
        button_layout.addStretch()
        
        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self.import_variations)
        self.import_button.setEnabled(False)
        button_layout.addWidget(self.import_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def browse_file(self):
        """Browse for NDJSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select NDJSON File", "", 
            "NDJSON Files (*.ndjson *.jsonl);;JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self.current_file_path = file_path
            self.validate_button.setEnabled(True)
            self.validation_status.setText("File selected - click Validate to check format")
            
            # Reset state
            self.validated_records = []
            self.import_button.setEnabled(False)
            self.preview_widget.set_records([])
    
    def validate_file(self):
        """Validate the selected NDJSON file."""
        if not self.current_file_path or not Path(self.current_file_path).exists():
            QMessageBox.warning(self, "File Error", "Please select a valid NDJSON file.")
            return
        
        # Start validation in background
        self.validation_worker = ValidationWorker(self.current_file_path)
        self.validation_worker.validationComplete.connect(self.on_validation_complete)
        self.validation_worker.progressUpdate.connect(self.on_progress_update)
        
        # Update UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.validate_button.setEnabled(False)
        self.validation_status.setText("Validating...")
        
        self.validation_worker.start()
    
    def on_progress_update(self, progress: int, status: str):
        """Handle validation progress updates."""
        self.progress_bar.setValue(progress)
        self.validation_status.setText(status)
    
    def on_validation_complete(self, success: bool, message: str, records: List[Dict[str, Any]]):
        """Handle validation completion."""
        self.progress_bar.setVisible(False)
        self.validate_button.setEnabled(True)
        
        if success:
            self.validated_records = records
            self.validation_status.setText(f"✅ {message}")
            self.import_button.setEnabled(True)
            
            # Update preview
            self.preview_widget.set_records(records)
            
            # Update import options
            engines = list(set(r.get('engine', 'unknown') for r in records))
            self.options_widget.set_available_engines(engines)
            
        else:
            self.validation_status.setText(f"❌ {message}")
            self.import_button.setEnabled(False)
            
            # Show detailed error
            QMessageBox.critical(self, "Validation Failed", message)
    
    def import_variations(self):
        """Import the validated variations."""
        if not self.validated_records:
            QMessageBox.warning(self, "Import Error", "No validated records to import.")
            return
        
        # Get import options
        options = self.options_widget.get_import_options()
        
        # Apply filters to records
        filtered_records = self.apply_import_filters(self.validated_records, options)
        
        if not filtered_records:
            QMessageBox.warning(self, "Import Error", 
                              "No records match the specified import criteria.")
            return
        
        # Confirm import
        reply = QMessageBox.question(
            self, "Confirm Import",
            f"Import {len(filtered_records)} variations from {len(self.validated_records)} total records?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.importRequested.emit(self.current_file_path, options, filtered_records)
            self.accept()
    
    def apply_import_filters(self, records: List[Dict[str, Any]], 
                           options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply import filters to records."""
        filtered = records
        
        # Engine filter
        engine_filter = options.get('engine_filter', 'Import All Engines')
        if engine_filter != 'Import All Engines' and engine_filter.startswith('Only '):
            target_engine = engine_filter[5:]  # Remove "Only " prefix
            filtered = [r for r in filtered if r.get('engine') == target_engine]
        
        # Page range filter
        page_from = options.get('page_from', 1)
        page_to = options.get('page_to', 9999)
        filtered = [r for r in filtered 
                   if page_from <= r.get('page', 0) <= page_to]
        
        # Confidence threshold
        confidence_threshold = options.get('confidence_threshold', 0.0)
        filtered = [r for r in filtered 
                   if r.get('confidence', 0.0) >= confidence_threshold]
        
        # Duplicate handling
        duplicate_handling = options.get('duplicate_handling', 'Keep all duplicates')
        if duplicate_handling != 'Keep all duplicates':
            filtered = self.handle_duplicates(filtered, duplicate_handling)
        
        return filtered
    
    def handle_duplicates(self, records: List[Dict[str, Any]], 
                         handling: str) -> List[Dict[str, Any]]:
        """Handle duplicate records based on strategy."""
        if handling == 'Keep all duplicates':
            return records
        
        # Group by (doc_id, page, block_id) or (doc_id, page, bbox)
        groups = {}
        
        for record in records:
            # Create key for grouping
            doc_id = record.get('doc_id', '')
            page = record.get('page', 0)
            block_id = record.get('block_id')
            bbox = record.get('bbox')
            
            if block_id:
                key = (doc_id, page, block_id)
            elif bbox:
                key = (doc_id, page, tuple(bbox) if isinstance(bbox, list) else bbox)
            else:
                key = (doc_id, page, record.get('raw_text', '')[:50])  # Use text prefix as fallback
            
            if key not in groups:
                groups[key] = []
            groups[key].append(record)
        
        # Apply handling strategy
        result = []
        
        for group in groups.values():
            if len(group) == 1:
                result.extend(group)
            elif handling == 'Keep highest confidence':
                # Keep record with highest confidence
                best = max(group, key=lambda r: r.get('confidence', 0.0))
                result.append(best)
            elif handling == 'Skip duplicates':
                # Skip entire group if duplicates found
                continue
        
        return result
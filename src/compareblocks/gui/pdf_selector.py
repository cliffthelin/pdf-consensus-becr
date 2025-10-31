# src/compareblocks/gui/pdf_selector.py

"""
PDF Selector Indicator Component for BECR application.

Provides a persistent PDF selector widget positioned below the main menu bar
that displays current PDF metadata and allows users to change the active PDF.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import fitz  # PyMuPDF

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QFileDialog, QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
    QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QIcon

from ..config.file_manager import file_manager


class PDFSelectorIndicator(QWidget):
    """
    Persistent PDF selector widget that displays current PDF information
    and allows users to change the active PDF.
    
    Signals:
        pdf_changed: Emitted when PDF selection changes, passes new PDF path
    """
    
    pdf_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pdf_path: Optional[str] = None
        self.pdf_metadata: Dict[str, Any] = {}
        self.setup_ui()
        self.load_default_pdf()
    
    def setup_ui(self):
        """Setup the PDF selector UI."""
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Create frame for visual separation
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Raised)
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(10, 5, 10, 5)
        
        # PDF icon/label
        pdf_icon_label = QLabel("📄")
        pdf_icon_label.setFont(QFont("Arial", 16))
        frame_layout.addWidget(pdf_icon_label)
        
        # PDF information display
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Filename label
        self.filename_label = QLabel("No PDF selected")
        filename_font = QFont("Arial", 11, QFont.Bold)
        self.filename_label.setFont(filename_font)
        info_layout.addWidget(self.filename_label)
        
        # Metadata label (path, pages, size)
        self.metadata_label = QLabel("Click 'Browse' to select a PDF")
        metadata_font = QFont("Arial", 9)
        self.metadata_label.setFont(metadata_font)
        self.metadata_label.setStyleSheet("color: gray;")
        info_layout.addWidget(self.metadata_label)
        
        frame_layout.addLayout(info_layout)
        frame_layout.addStretch()
        
        # Browse button
        self.browse_button = QPushButton("📁 Browse...")
        self.browse_button.setToolTip("Select a different PDF file")
        self.browse_button.clicked.connect(self.open_pdf_selection_dialog)
        frame_layout.addWidget(self.browse_button)
        
        # Info button
        self.info_button = QPushButton("ℹ️ Info")
        self.info_button.setToolTip("Show detailed PDF information")
        self.info_button.clicked.connect(self.show_pdf_info_dialog)
        self.info_button.setEnabled(False)
        frame_layout.addWidget(self.info_button)
        
        layout.addWidget(frame)
        
        # Make the entire widget clickable
        self.setToolTip("Click to change PDF")
        self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        """Handle mouse press to open PDF selection dialog."""
        if event.button() == Qt.LeftButton:
            self.open_pdf_selection_dialog()
    
    def load_default_pdf(self):
        """Load the default PDF from configuration."""
        try:
            pdf_path = file_manager.get_target_pdf_path()
            if pdf_path and Path(pdf_path).exists():
                self.update_pdf_selection(pdf_path)
            else:
                # No default PDF - ensure info button is disabled
                self.info_button.setEnabled(False)
                self.logger.warning(f"Default PDF not found: {pdf_path}")
        except Exception as e:
            # Error loading - ensure info button is disabled
            self.info_button.setEnabled(False)
            self.logger.error(f"Failed to load default PDF: {e}")
    
    def open_pdf_selection_dialog(self):
        """Open file dialog to select a new PDF."""
        # Get current directory or default to configured path
        start_dir = ""
        if self.current_pdf_path:
            start_dir = str(Path(self.current_pdf_path).parent)
        else:
            try:
                default_path = file_manager.get_target_pdf_path()
                if default_path:
                    start_dir = str(Path(default_path).parent)
            except:
                pass
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF File",
            start_dir,
            "PDF Files (*.pdf);;All Files (*.*)"
        )
        
        if file_path:
            # Validate PDF before accepting
            if self.validate_pdf(file_path):
                self.update_pdf_selection(file_path)
            else:
                QMessageBox.warning(
                    self,
                    "Invalid PDF",
                    f"The selected file is not a valid PDF or cannot be opened:\n{file_path}"
                )
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """
        Validate that the PDF file is valid and can be opened.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            True if PDF is valid, False otherwise
        """
        try:
            # Check file exists
            if not Path(pdf_path).exists():
                return False
            
            # Check file extension
            if not pdf_path.lower().endswith('.pdf'):
                return False
            
            # Try to open with PyMuPDF
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            
            # Must have at least one page
            return page_count > 0
            
        except Exception as e:
            self.logger.error(f"PDF validation failed: {e}")
            return False
    
    def update_pdf_selection(self, pdf_path: str):
        """
        Update the selected PDF and refresh metadata display.
        
        Args:
            pdf_path: Path to the new PDF file
        """
        try:
            # Extract metadata
            self.pdf_metadata = self.extract_pdf_metadata(pdf_path)
            self.current_pdf_path = pdf_path
            
            # Update UI
            self.refresh_display()
            
            # Enable info button
            self.info_button.setEnabled(True)
            
            # Emit signal to notify other components
            self.pdf_changed.emit(pdf_path)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load PDF metadata:\n{str(e)}"
            )
    
    def extract_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary containing PDF metadata
        """
        metadata = {
            "path": pdf_path,
            "filename": Path(pdf_path).name,
            "file_size": 0,
            "page_count": 0,
            "title": "",
            "author": "",
            "subject": "",
            "creator": "",
            "producer": "",
            "creation_date": "",
            "modification_date": ""
        }
        
        try:
            # Get file size
            file_path = Path(pdf_path)
            metadata["file_size"] = file_path.stat().st_size
            
            # Open PDF and extract metadata
            doc = fitz.open(pdf_path)
            metadata["page_count"] = len(doc)
            
            # Extract PDF metadata
            pdf_meta = doc.metadata
            if pdf_meta:
                metadata["title"] = pdf_meta.get("title", "")
                metadata["author"] = pdf_meta.get("author", "")
                metadata["subject"] = pdf_meta.get("subject", "")
                metadata["creator"] = pdf_meta.get("creator", "")
                metadata["producer"] = pdf_meta.get("producer", "")
                metadata["creation_date"] = pdf_meta.get("creationDate", "")
                metadata["modification_date"] = pdf_meta.get("modDate", "")
            
            doc.close()
            
        except Exception as e:
            self.logger.error(f"Failed to extract PDF metadata: {e}")
        
        return metadata
    
    def refresh_display(self):
        """Refresh the display with current PDF metadata."""
        if not self.current_pdf_path or not self.pdf_metadata:
            self.filename_label.setText("No PDF selected")
            self.metadata_label.setText("Click 'Browse' to select a PDF")
            return
        
        # Update filename
        filename = self.pdf_metadata.get("filename", "Unknown")
        self.filename_label.setText(filename)
        
        # Update metadata line
        page_count = self.pdf_metadata.get("page_count", 0)
        file_size = self.pdf_metadata.get("file_size", 0)
        file_size_mb = file_size / (1024 * 1024)
        
        path = self.pdf_metadata.get("path", "")
        path_display = str(Path(path).parent) if path else ""
        
        metadata_text = f"{path_display} • {page_count} pages • {file_size_mb:.2f} MB"
        self.metadata_label.setText(metadata_text)
    
    def show_pdf_info_dialog(self):
        """Show detailed PDF information dialog."""
        if not self.current_pdf_path or not self.pdf_metadata:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("PDF Information")
        dialog.setMinimumWidth(500)
        
        layout = QFormLayout(dialog)
        
        # Add metadata fields
        layout.addRow("Filename:", QLabel(self.pdf_metadata.get("filename", "N/A")))
        layout.addRow("Path:", QLabel(self.pdf_metadata.get("path", "N/A")))
        layout.addRow("Pages:", QLabel(str(self.pdf_metadata.get("page_count", 0))))
        
        file_size = self.pdf_metadata.get("file_size", 0)
        file_size_mb = file_size / (1024 * 1024)
        layout.addRow("File Size:", QLabel(f"{file_size_mb:.2f} MB ({file_size:,} bytes)"))
        
        # Optional metadata
        if self.pdf_metadata.get("title"):
            layout.addRow("Title:", QLabel(self.pdf_metadata["title"]))
        if self.pdf_metadata.get("author"):
            layout.addRow("Author:", QLabel(self.pdf_metadata["author"]))
        if self.pdf_metadata.get("subject"):
            layout.addRow("Subject:", QLabel(self.pdf_metadata["subject"]))
        if self.pdf_metadata.get("creator"):
            layout.addRow("Creator:", QLabel(self.pdf_metadata["creator"]))
        if self.pdf_metadata.get("producer"):
            layout.addRow("Producer:", QLabel(self.pdf_metadata["producer"]))
        
        # Close button
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addRow(buttons)
        
        dialog.exec()
    
    def get_current_pdf_path(self) -> Optional[str]:
        """Get the currently selected PDF path."""
        return self.current_pdf_path
    
    def get_pdf_metadata(self) -> Dict[str, Any]:
        """Get the current PDF metadata."""
        return self.pdf_metadata.copy()
    
    @property
    def logger(self):
        """Get logger instance."""
        import logging
        return logging.getLogger(__name__)

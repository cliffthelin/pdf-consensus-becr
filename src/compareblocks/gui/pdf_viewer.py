# src/compareblocks/gui/pdf_viewer.py
"""
PDF viewer widget with block highlighting and navigation controls.
Provides zoom, pan, and block selection capabilities for the Review GUI.
"""

import fitz  # PyMuPDF
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QSpinBox, QSlider, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QSize
from PySide6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont, QMouseEvent, QWheelEvent

from ..gbg.types import BoundingBox


@dataclass
class BlockHighlight:
    """Information for highlighting a block on the PDF."""
    block_id: str
    bbox: BoundingBox
    color: QColor
    label: str = ""
    is_selected: bool = False


class PDFPageWidget(QLabel):
    """Widget for displaying a single PDF page with block highlighting."""
    
    blockClicked = Signal(str)  # block_id
    
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid gray;")
        self.setMinimumSize(400, 500)
        
        # PDF rendering state
        self.pdf_document = None
        self.current_page = None
        self.page_pixmap = None
        self.zoom_factor = 1.0
        
        # Block highlighting
        self.block_highlights: List[BlockHighlight] = []
        self.selected_block_id: Optional[str] = None
        
        # Mouse interaction
        self.setMouseTracking(True)
        self.last_pan_point = QPoint()
        self.is_panning = False
        
    def load_pdf(self, pdf_path: str) -> bool:
        """Load a PDF document."""
        try:
            if self.pdf_document:
                self.pdf_document.close()
            
            self.pdf_document = fitz.open(pdf_path)
            return True
        except Exception as e:
            print(f"Error loading PDF: {e}")
            return False
    
    def set_page(self, page_num: int) -> bool:
        """Set the current page to display."""
        if not self.pdf_document or page_num < 0 or page_num >= len(self.pdf_document):
            return False
        
        try:
            self.current_page = self.pdf_document[page_num]
            self._render_page()
            return True
        except Exception as e:
            print(f"Error setting page {page_num}: {e}")
            return False
    
    def set_zoom(self, zoom_factor: float):
        """Set the zoom factor and re-render."""
        self.zoom_factor = max(0.1, min(5.0, zoom_factor))
        if self.current_page:
            self._render_page()
    
    def set_block_highlights(self, highlights: List[BlockHighlight]):
        """Set the blocks to highlight on the page."""
        self.block_highlights = highlights
        if self.current_page:
            self._render_page()
    
    def select_block(self, block_id: str):
        """Select a specific block for highlighting."""
        self.selected_block_id = block_id
        
        # Update highlight selection state
        for highlight in self.block_highlights:
            highlight.is_selected = (highlight.block_id == block_id)
        
        if self.current_page:
            self._render_page()
    
    def _render_page(self):
        """Render the current page with highlights."""
        if not self.current_page:
            return
        
        try:
            # Render page at current zoom
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            pix = self.current_page.get_pixmap(matrix=mat)
            
            # Convert to QPixmap
            img_data = pix.tobytes("png")
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            
            # Draw block highlights
            if self.block_highlights:
                pixmap = self._draw_highlights(pixmap)
            
            self.page_pixmap = pixmap
            self.setPixmap(pixmap)
            
        except Exception as e:
            print(f"Error rendering page: {e}")
    
    def _draw_highlights(self, pixmap: QPixmap) -> QPixmap:
        """Draw block highlights on the pixmap."""
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for highlight in self.block_highlights:
            # Scale bounding box by zoom factor
            x = int(highlight.bbox.x * self.zoom_factor)
            y = int(highlight.bbox.y * self.zoom_factor)
            width = int(highlight.bbox.width * self.zoom_factor)
            height = int(highlight.bbox.height * self.zoom_factor)
            
            # Set pen and brush based on selection state
            if highlight.is_selected:
                pen = QPen(QColor(255, 0, 0), 3)  # Red, thick border for selected
                brush = QBrush(QColor(255, 0, 0, 30))  # Semi-transparent red fill
            else:
                pen = QPen(highlight.color, 2)
                brush = QBrush(QColor(highlight.color.red(), highlight.color.green(), 
                                    highlight.color.blue(), 20))
            
            painter.setPen(pen)
            painter.setBrush(brush)
            
            # Draw rectangle
            painter.drawRect(x, y, width, height)
            
            # Draw label if provided
            if highlight.label:
                painter.setPen(QPen(QColor(0, 0, 0)))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(x + 2, y + 12, highlight.label)
        
        painter.end()
        return pixmap
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events for block selection and panning."""
        if event.button() == Qt.LeftButton:
            # Check if click is on a block
            clicked_block = self._get_block_at_position(event.pos())
            if clicked_block:
                self.blockClicked.emit(clicked_block)
            else:
                # Start panning
                self.is_panning = True
                self.last_pan_point = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events for panning."""
        if self.is_panning and event.buttons() & Qt.LeftButton:
            # Calculate pan delta
            delta = event.pos() - self.last_pan_point
            self.last_pan_point = event.pos()
            
            # Update scroll position (handled by parent scroll area)
            # This is a simplified implementation - full panning would require
            # coordination with the parent scroll area
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events."""
        if event.button() == Qt.LeftButton:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
        
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle wheel events for zooming."""
        if event.modifiers() & Qt.ControlModifier:
            # Zoom with Ctrl+Wheel
            delta = event.angleDelta().y()
            zoom_change = 1.1 if delta > 0 else 0.9
            new_zoom = self.zoom_factor * zoom_change
            self.set_zoom(new_zoom)
            event.accept()
        else:
            super().wheelEvent(event)
    
    def _get_block_at_position(self, pos: QPoint) -> Optional[str]:
        """Get the block ID at the given position."""
        if not self.block_highlights:
            return None
        
        for highlight in self.block_highlights:
            # Scale bounding box by zoom factor
            x = int(highlight.bbox.x * self.zoom_factor)
            y = int(highlight.bbox.y * self.zoom_factor)
            width = int(highlight.bbox.width * self.zoom_factor)
            height = int(highlight.bbox.height * self.zoom_factor)
            
            rect = QRect(x, y, width, height)
            if rect.contains(pos):
                return highlight.block_id
        
        return None


class PDFViewer(QWidget):
    """Complete PDF viewer with navigation and zoom controls."""
    
    pageChanged = Signal(int)  # page_number
    blockSelected = Signal(str)  # block_id
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
        # PDF state
        self.pdf_path = None
        self.total_pages = 0
        self.current_page_num = 0
        
    def setup_ui(self):
        """Setup the PDF viewer UI."""
        layout = QVBoxLayout(self)
        
        # Navigation controls
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self.previous_page)
        nav_layout.addWidget(self.prev_button)
        
        nav_layout.addWidget(QLabel("Page:"))
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.valueChanged.connect(self.go_to_page)
        nav_layout.addWidget(self.page_spinbox)
        
        self.page_label = QLabel("of 0")
        nav_layout.addWidget(self.page_label)
        
        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self.next_page)
        nav_layout.addWidget(self.next_button)
        
        nav_layout.addStretch()
        
        # Zoom controls
        nav_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 500)  # 10% to 500%
        self.zoom_slider.setValue(100)  # 100%
        self.zoom_slider.valueChanged.connect(self.set_zoom_percent)
        nav_layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel("100%")
        nav_layout.addWidget(self.zoom_label)
        
        self.fit_width_button = QPushButton("Fit Width")
        self.fit_width_button.clicked.connect(self.fit_width)
        nav_layout.addWidget(self.fit_width_button)
        
        layout.addLayout(nav_layout)
        
        # PDF display area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        self.pdf_widget = PDFPageWidget()
        self.pdf_widget.blockClicked.connect(self.blockSelected.emit)
        self.scroll_area.setWidget(self.pdf_widget)
        
        layout.addWidget(self.scroll_area)
        
        # Initially disable controls
        self.set_controls_enabled(False)
    
    def load_pdf(self, pdf_path: str) -> bool:
        """Load a PDF file."""
        if not Path(pdf_path).exists():
            return False
        
        if self.pdf_widget.load_pdf(pdf_path):
            self.pdf_path = pdf_path
            self.total_pages = len(self.pdf_widget.pdf_document)
            
            # Update UI
            self.page_spinbox.setMaximum(self.total_pages)
            self.page_label.setText(f"of {self.total_pages}")
            
            # Go to first page
            self.go_to_page(1)
            self.set_controls_enabled(True)
            
            return True
        
        return False
    
    def go_to_page(self, page_num: int):
        """Go to a specific page (1-based)."""
        if not self.pdf_widget.pdf_document:
            return
        
        page_num = max(1, min(self.total_pages, page_num))
        
        if self.pdf_widget.set_page(page_num - 1):  # Convert to 0-based
            self.current_page_num = page_num
            self.page_spinbox.setValue(page_num)
            self.pageChanged.emit(page_num)
            
            # Update navigation buttons
            self.prev_button.setEnabled(page_num > 1)
            self.next_button.setEnabled(page_num < self.total_pages)
    
    def previous_page(self):
        """Go to the previous page."""
        if self.current_page_num > 1:
            self.go_to_page(self.current_page_num - 1)
    
    def next_page(self):
        """Go to the next page."""
        if self.current_page_num < self.total_pages:
            self.go_to_page(self.current_page_num + 1)
    
    def set_zoom_percent(self, percent: int):
        """Set zoom as percentage."""
        zoom_factor = percent / 100.0
        self.pdf_widget.set_zoom(zoom_factor)
        self.zoom_label.setText(f"{percent}%")
    
    def fit_width(self):
        """Fit the page width to the viewer."""
        if not self.pdf_widget.current_page:
            return
        
        # Calculate zoom to fit width
        page_rect = self.pdf_widget.current_page.rect
        viewer_width = self.scroll_area.viewport().width() - 20  # Account for margins
        
        if page_rect.width > 0:
            zoom_factor = viewer_width / page_rect.width
            zoom_percent = int(zoom_factor * 100)
            
            self.zoom_slider.setValue(zoom_percent)
            self.set_zoom_percent(zoom_percent)
    
    def set_block_highlights(self, highlights: List[BlockHighlight]):
        """Set blocks to highlight on the current page."""
        self.pdf_widget.set_block_highlights(highlights)
    
    def select_block(self, block_id: str):
        """Select a specific block."""
        self.pdf_widget.select_block(block_id)
    
    def set_controls_enabled(self, enabled: bool):
        """Enable or disable navigation controls."""
        self.prev_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.page_spinbox.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.zoom_slider.setEnabled(enabled)
        self.fit_width_button.setEnabled(enabled)
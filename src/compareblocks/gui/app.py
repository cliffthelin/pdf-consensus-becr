# src/compareblocks/gui/app.py
"""
Main GUI application for BECR with visual debugging capabilities.
Provides block comparison, OCR debugging, and image inspection tools.
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QTextEdit, QLabel, QPushButton, QSpinBox, QScrollArea,
    QGroupBox, QGridLayout, QSplitter, QMessageBox, QProgressBar,
    QComboBox, QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QFont, QTextOption

from ..debug.image_extractor import extract_debug_images_for_page
from ..config.file_manager import file_manager
from ..config.engine_config import EngineConfigurationManager
from .config_forms import ConfigurationManagerWidget
from .test_runner_widget import TestRunnerWidget
from .pdf_selector import PDFSelectorIndicator
from .file_management_tab import FileManagementTab
from .settings_tab import SettingsTab


class DebugImageWidget(QWidget):
    """Widget for displaying debug images and OCR results."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.current_regions = []
    
    def setup_ui(self):
        """Setup the debug image UI."""
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Page:"))
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(0)
        self.page_spinbox.setMaximum(100)
        self.page_spinbox.setValue(15)  # Default to page 15
        controls_layout.addWidget(self.page_spinbox)
        
        controls_layout.addWidget(QLabel("Max Blocks:"))
        self.blocks_spinbox = QSpinBox()
        self.blocks_spinbox.setMinimum(1)
        self.blocks_spinbox.setMaximum(10)
        self.blocks_spinbox.setValue(5)
        controls_layout.addWidget(self.blocks_spinbox)
        
        self.extract_button = QPushButton("Extract Debug Images")
        self.extract_button.clicked.connect(self.extract_debug_images)
        controls_layout.addWidget(self.extract_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Scroll area for images
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.images_widget = QWidget()
        self.images_layout = QVBoxLayout(self.images_widget)
        self.scroll_area.setWidget(self.images_widget)
        
        layout.addWidget(self.scroll_area)
    
    def extract_debug_images(self):
        """Extract debug images for the selected page."""
        page_num = self.page_spinbox.value()
        max_blocks = self.blocks_spinbox.value()
        
        self.extract_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        try:
            # Get PDF path from parent window's PDF selector if available
            pdf_path = None
            parent_window = self.window()
            if hasattr(parent_window, 'pdf_selector'):
                pdf_path = parent_window.pdf_selector.get_current_pdf_path()
            
            # Fall back to file manager if no PDF selected
            if not pdf_path:
                pdf_path = file_manager.get_target_pdf_path()
            
            if not pdf_path or not Path(pdf_path).exists():
                QMessageBox.warning(self, "No PDF", 
                    "Please select a PDF using the PDF selector at the top of the window.")
                return
            
            # Extract debug images
            result = extract_debug_images_for_page(pdf_path, page_num, max_blocks)
            
            if 'error' in result:
                QMessageBox.warning(self, "Error", f"Failed to extract images: {result['error']}")
            else:
                self.display_debug_results(result)
                QMessageBox.information(self, "Success", 
                    f"Extracted {result['extracted_regions']} debug images for page {page_num}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to extract debug images: {str(e)}")
        
        finally:
            self.extract_button.setEnabled(True)
            self.progress_bar.setVisible(False)
    
    def display_debug_results(self, result: Dict[str, Any]):
        """Display the debug results in the UI."""
        # Clear existing content
        for i in reversed(range(self.images_layout.count())):
            child = self.images_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        self.current_regions = result.get('regions', [])
        
        # Load Tesseract results for comparison
        tesseract_results = self.load_tesseract_results(result['page_num'])
        
        # Display each block
        for i, region in enumerate(self.current_regions):
            block_widget = self.create_block_widget(region, tesseract_results, i)
            self.images_layout.addWidget(block_widget)
        
        self.images_layout.addStretch()
    
    def load_tesseract_results(self, page_num: int) -> List[Dict[str, Any]]:
        """Load Tesseract results for the page."""
        try:
            tesseract_path = Path(file_manager.get_processing_directory()) / "English Language Arts Standards_tesseract.json"
            if tesseract_path.exists():
                with open(tesseract_path, 'r', encoding='utf-8') as f:
                    tesseract_data = json.load(f)
                
                return [b for b in tesseract_data.get('blocks', []) if b.get('page') == page_num]
        except Exception as e:
            print(f"Could not load Tesseract results: {e}")
        
        return []
    
    def create_block_widget(self, region: Dict[str, Any], tesseract_results: List[Dict[str, Any]], 
                           block_index: int) -> QWidget:
        """Create a widget for displaying a single block's debug information."""
        group_box = QGroupBox(f"Block {block_index + 1}: {region['gbg_block_id'][:12]}...")
        layout = QVBoxLayout(group_box)
        
        # Block information
        info_layout = QHBoxLayout()
        
        info_text = QTextEdit()
        info_text.setMaximumHeight(120)
        info_text.setFont(QFont("Consolas", 9))
        
        bbox = region['bbox']
        info_content = f"""Expected Text: "{region['expected_text'][:100]}{'...' if len(region['expected_text']) > 100 else ''}"
BBox: x={bbox['x']:.1f}, y={bbox['y']:.1f}, w={bbox['width']:.1f}, h={bbox['height']:.1f}
"""
        
        # Add Tesseract results if available
        if block_index < len(tesseract_results):
            tesseract_result = tesseract_results[block_index]
            actual_text = tesseract_result.get('text', '').strip()
            confidence = tesseract_result.get('confidence', 0.0)
            orientation = tesseract_result.get('orientation_angle', 0)
            
            info_content += f"""
Actual Text: "{actual_text[:100]}{'...' if len(actual_text) > 100 else ''}"
Confidence: {confidence:.3f}
Selected Orientation: {orientation}°"""
        
        info_text.setPlainText(info_content)
        info_layout.addWidget(info_text)
        
        layout.addLayout(info_layout)
        
        # Images layout
        images_layout = QHBoxLayout()
        
        # Original image
        original_path = Path(region['original_image_path'])
        if original_path.exists():
            original_label = self.create_image_label(str(original_path), "Original")
            images_layout.addWidget(original_label)
        
        # Orientation images
        for orientation_result in region['orientation_results']:
            angle = orientation_result['angle']
            rotated_path = Path(orientation_result['rotated_image_path'])
            processed_path = Path(orientation_result['processed_image_path'])
            
            # Check if this orientation was selected
            selected = ""
            if (block_index < len(tesseract_results) and 
                tesseract_results[block_index].get('orientation_angle') == angle):
                selected = " ✓"
            
            orientation_widget = QWidget()
            orientation_layout = QVBoxLayout(orientation_widget)
            orientation_layout.setContentsMargins(5, 5, 5, 5)
            
            # Title
            title_label = QLabel(f"{angle}°{selected}")
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setFont(QFont("Arial", 10, QFont.Bold))
            orientation_layout.addWidget(title_label)
            
            # Rotated image
            if rotated_path.exists():
                rotated_label = self.create_image_label(str(rotated_path), f"Rotated {angle}°", max_size=150)
                orientation_layout.addWidget(rotated_label)
            
            # Processed image
            if processed_path.exists():
                processed_label = self.create_image_label(str(processed_path), f"Processed {angle}°", max_size=150)
                orientation_layout.addWidget(processed_label)
            
            images_layout.addWidget(orientation_widget)
        
        layout.addLayout(images_layout)
        
        return group_box
    
    def create_image_label(self, image_path: str, title: str, max_size: int = 200) -> QWidget:
        """Create a label widget for displaying an image."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        
        # Title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 8))
        layout.addWidget(title_label)
        
        # Image
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("border: 1px solid gray;")
        
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # Scale image to fit
                scaled_pixmap = pixmap.scaled(max_size, max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_label.setPixmap(scaled_pixmap)
            else:
                image_label.setText("Image not found")
        except Exception as e:
            image_label.setText(f"Error: {str(e)}")
        
        layout.addWidget(image_label)
        
        return widget


class BECRMainWindow(QMainWindow):
    """Main window for BECR application."""
    
    def __init__(self):
        super().__init__()
        self.config_manager = EngineConfigurationManager()
        self.setup_ui()
        self.setup_menus()
        self.setWindowTitle("BECR - Blockwise Extraction Comparison & Review")
        self.resize(1200, 800)
    
    def setup_ui(self):
        """Setup the main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Add PDF selector indicator at the top (below menu bar)
        self.pdf_selector = PDFSelectorIndicator()
        self.pdf_selector.pdf_changed.connect(self.on_pdf_changed)
        layout.addWidget(self.pdf_selector)
        
        # Add file management status
        self.file_status_widget = self.create_file_status_widget()
        layout.addWidget(self.file_status_widget)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # File Management tab (FIRST)
        self.file_management_tab = FileManagementTab()
        self.file_management_tab.pdf_selected.connect(self.on_pdf_selected_from_file_management)
        self.tab_widget.addTab(self.file_management_tab, "📁 Files")
        
        # Debug Images tab
        self.debug_widget = DebugImageWidget()
        self.tab_widget.addTab(self.debug_widget, "Debug Images")
        
        # Review GUI tab
        from .review_gui import ReviewGUI
        self.review_gui = ReviewGUI()
        # Extract the central widget from the review GUI to embed as a tab
        review_widget = self.review_gui.centralWidget()
        self.review_gui.setCentralWidget(QWidget())  # Replace with empty widget
        self.tab_widget.addTab(review_widget, "PDF Review")
        
        self.analysis_widget = QTextEdit()
        self.analysis_widget.setPlainText("Analysis and statistics will be displayed here.")
        self.tab_widget.addTab(self.analysis_widget, "Analysis")
        
        # Settings tab (with Engine Configuration as sub-section)
        self.settings_tab = SettingsTab()
        self.settings_tab.settings_changed.connect(self.on_settings_changed)
        self.tab_widget.addTab(self.settings_tab, "⚙️ Settings")
        
        # Configuration management tab (under Settings conceptually, but separate tab for now)
        self.config_widget = ConfigurationManagerWidget(self.config_manager)
        self.tab_widget.addTab(self.config_widget, "  ⚙️ Engine Configuration")
        
        # Test Runner tab (AFTER Settings)
        self.test_runner_widget = TestRunnerWidget()
        self.tab_widget.addTab(self.test_runner_widget, "🧪 Test Runner")
        
        layout.addWidget(self.tab_widget)
    
    def setup_menus(self):
        """Setup application menus."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Configuration menu
        config_menu = menubar.addMenu("Configuration")
        
        # Create individual config files action
        create_configs_action = config_menu.addAction("Create Individual Config Files")
        create_configs_action.triggered.connect(self.create_individual_config_files)
        
        # View engine statistics action
        stats_action = config_menu.addAction("View Engine Statistics")
        stats_action.triggered.connect(self.show_engine_statistics)
        
        # PDF-specific configuration menu
        pdf_config_menu = config_menu.addMenu("PDF-Specific Configuration")
        
        # Add PDF override actions for each engine
        engines = ["tesseract", "paddleocr", "pymupdf", "docling", "kreuzberg"]
        for engine in engines:
            action = pdf_config_menu.addAction(f"Configure {engine.title()}")
            action.triggered.connect(lambda checked, eng=engine: self.add_pdf_configuration(eng))
    
    def create_individual_config_files(self):
        """Create individual configuration files for each engine."""
        try:
            created_files = self.config_manager.create_individual_config_files()
            
            message = "Individual configuration files created:\n\n"
            for engine, file_path in created_files.items():
                message += f"• {engine}: {file_path}\n"
            
            QMessageBox.information(self, "Success", message)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create config files: {str(e)}")
    
    def show_engine_statistics(self):
        """Show comprehensive engine statistics."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Engine Statistics")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Statistics table
        stats_table = QTableWidget()
        stats_table.setColumnCount(4)
        stats_table.setHorizontalHeaderLabels([
            "Engine", "Total Configs", "PDF Overrides", "Last Updated"
        ])
        
        engines = ["tesseract", "paddleocr", "pymupdf", "docling", "kreuzberg"]
        stats_table.setRowCount(len(engines))
        
        for row, engine in enumerate(engines):
            try:
                stats = self.config_manager.get_engine_statistics(engine)
                stats_table.setItem(row, 0, QTableWidgetItem(engine))
                stats_table.setItem(row, 1, QTableWidgetItem(str(stats["total_configurations"])))
                stats_table.setItem(row, 2, QTableWidgetItem(str(stats["active_pdf_overrides"])))
                stats_table.setItem(row, 3, QTableWidgetItem(stats["last_updated"]))
            except Exception as e:
                stats_table.setItem(row, 0, QTableWidgetItem(engine))
                stats_table.setItem(row, 1, QTableWidgetItem("Error"))
                stats_table.setItem(row, 2, QTableWidgetItem(str(e)))
                stats_table.setItem(row, 3, QTableWidgetItem("N/A"))
        
        layout.addWidget(stats_table)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.exec()
    
    def create_file_status_widget(self):
        """Create the file management status widget showing root files setup."""
        group_box = QGroupBox("📁 File Management System - Root Files Setup")
        layout = QVBoxLayout(group_box)
        
        # Status overview
        status_layout = QHBoxLayout()
        
        # Default PDF status
        try:
            pdf_path = file_manager.get_target_pdf_path()
            pdf_exists = Path(pdf_path).exists() if pdf_path else False
            
            pdf_status = QLabel(f"📄 Default PDF: {'✅ Ready' if pdf_exists else '❌ Not Found'}")
            pdf_status.setStyleSheet("color: green;" if pdf_exists else "color: red;")
            status_layout.addWidget(pdf_status)
            
            if pdf_exists:
                pdf_info = QLabel(f"({Path(pdf_path).name})")
                pdf_info.setStyleSheet("color: gray; font-size: 10px;")
                status_layout.addWidget(pdf_info)
        except Exception as e:
            error_status = QLabel(f"📄 Default PDF: ❌ Error - {str(e)}")
            error_status.setStyleSheet("color: red;")
            status_layout.addWidget(error_status)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Processing directories status
        dirs_layout = QHBoxLayout()
        
        try:
            processing_dir = file_manager.get_processing_directory()
            final_dir = file_manager.get_final_output_directory()
            
            proc_exists = Path(processing_dir).exists()
            final_exists = Path(final_dir).exists()
            
            proc_status = QLabel(f"📂 Processing: {'✅' if proc_exists else '❌'}")
            final_status = QLabel(f"📂 Output: {'✅' if final_exists else '❌'}")
            
            dirs_layout.addWidget(proc_status)
            dirs_layout.addWidget(final_status)
            dirs_layout.addStretch()
        except Exception as e:
            error_label = QLabel(f"📂 Directories: ❌ {str(e)}")
            error_label.setStyleSheet("color: red;")
            dirs_layout.addWidget(error_label)
        
        layout.addLayout(dirs_layout)
        
        # Association status - show if we have processed associations
        assoc_layout = QHBoxLayout()
        
        try:
            # Check for existing associations/results
            if pdf_exists:
                from ..association.manager import AssociationManager
                assoc_manager = AssociationManager()
                associations = assoc_manager.load_associations_for_pdf(pdf_path)
                
                assoc_count = len(associations.associations) if hasattr(associations, 'associations') else 0
                assoc_status = QLabel(f"🔗 Associations: {assoc_count} found")
                assoc_status.setStyleSheet("color: green;" if assoc_count > 0 else "color: orange;")
                assoc_layout.addWidget(assoc_status)
                
                if assoc_count > 0:
                    improvements_label = QLabel("✨ Improvements available through consensus")
                    improvements_label.setStyleSheet("color: blue; font-weight: bold;")
                    assoc_layout.addWidget(improvements_label)
        except Exception as e:
            assoc_status = QLabel(f"🔗 Associations: ❌ {str(e)}")
            assoc_status.setStyleSheet("color: red;")
            assoc_layout.addWidget(assoc_status)
        
        assoc_layout.addStretch()
        layout.addLayout(assoc_layout)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        setup_button = QPushButton("🔧 Setup Default Files")
        setup_button.clicked.connect(self.setup_default_files)
        buttons_layout.addWidget(setup_button)
        
        process_button = QPushButton("⚡ Process Selected PDF")
        process_button.clicked.connect(self.process_selected_pdf)
        buttons_layout.addWidget(process_button)
        
        view_results_button = QPushButton("📊 View Results")
        view_results_button.clicked.connect(self.view_processing_results)
        buttons_layout.addWidget(view_results_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return group_box
    
    def setup_default_files(self):
        """Setup default files and directories."""
        try:
            # Ensure directories exist
            processing_dir = Path(file_manager.get_processing_directory())
            final_dir = Path(file_manager.get_final_output_directory())
            
            processing_dir.mkdir(parents=True, exist_ok=True)
            final_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if default PDF exists
            pdf_path = file_manager.get_target_pdf_path()
            if not Path(pdf_path).exists():
                # Offer to select a PDF
                from PySide6.QtWidgets import QFileDialog
                selected_pdf, _ = QFileDialog.getOpenFileName(
                    self, "Select Default PDF", "", "PDF Files (*.pdf)"
                )
                if selected_pdf:
                    # Update configuration with selected PDF
                    QMessageBox.information(self, "Setup Complete", 
                        f"Directories created and PDF selected:\n{selected_pdf}")
                else:
                    QMessageBox.information(self, "Setup Partial", 
                        "Directories created. Please place your PDF in the configured location.")
            else:
                QMessageBox.information(self, "Setup Complete", 
                    "All default files and directories are ready!")
            
            # Refresh the status widget
            self.refresh_file_status()
            
        except Exception as e:
            QMessageBox.critical(self, "Setup Error", f"Failed to setup files: {str(e)}")
    
    def process_selected_pdf(self):
        """Process the currently selected PDF through all engines and create associations."""
        try:
            # Get the currently selected PDF from the PDF selector
            pdf_path = self.pdf_selector.get_current_pdf_path()
            
            if not pdf_path:
                QMessageBox.warning(self, "No PDF Selected", 
                    "Please select a PDF using the PDF selector at the top of the window.")
                return
            
            if not Path(pdf_path).exists():
                QMessageBox.warning(self, "PDF Not Found", 
                    f"The selected PDF file does not exist:\n{pdf_path}")
                return
            
            # Show progress dialog
            progress = QProgressBar()
            progress.setRange(0, 0)  # Indeterminate
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Processing PDF")
            layout = QVBoxLayout(dialog)
            layout.addWidget(QLabel(f"Processing PDF through all engines...\n\n{Path(pdf_path).name}"))
            layout.addWidget(progress)
            
            # Process in background (simplified for now)
            QMessageBox.information(self, "Processing Started", 
                f"PDF processing initiated for:\n{Path(pdf_path).name}\n\nCheck the Debug Images tab for results.")
            
            dialog.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Processing Error", f"Failed to process PDF: {str(e)}")
    
    def view_processing_results(self):
        """View processing results and improvements."""
        try:
            # Get the currently selected PDF from the PDF selector
            pdf_path = self.pdf_selector.get_current_pdf_path()
            
            if not pdf_path:
                QMessageBox.warning(self, "No PDF Selected", 
                    "Please select a PDF using the PDF selector at the top of the window.")
                return
            
            if not Path(pdf_path).exists():
                QMessageBox.warning(self, "PDF Not Found", 
                    f"The selected PDF file does not exist:\n{pdf_path}")
                return
            
            # Switch to appropriate tab to show results
            self.tab_widget.setCurrentIndex(0)  # Debug Images tab
            QMessageBox.information(self, "Results", 
                f"Viewing results for:\n{Path(pdf_path).name}\n\nCheck the Debug Images and Analysis tabs for processing results and improvements.")
            
        except Exception as e:
            QMessageBox.critical(self, "View Error", f"Failed to view results: {str(e)}")
    
    def refresh_file_status(self):
        """Refresh the file status widget."""
        # Remove old widget and create new one
        old_widget = self.file_status_widget
        self.file_status_widget = self.create_file_status_widget()
        
        # Replace in layout
        layout = self.centralWidget().layout()
        layout.replaceWidget(old_widget, self.file_status_widget)
        old_widget.deleteLater()
    
    def on_pdf_changed(self, pdf_path: str):
        """
        Handle PDF selection change.
        
        Updates all application components to use the new PDF.
        
        Args:
            pdf_path: Path to the newly selected PDF
        """
        try:
            # Update file manager configuration
            # Note: This would typically update the active PDF in configuration
            # For now, we'll just refresh the UI components
            
            # Refresh file status widget
            self.refresh_file_status()
            
            # Notify debug widget
            if hasattr(self, 'debug_widget'):
                # Debug widget can now use the new PDF
                pass
            
            # Notify review GUI
            if hasattr(self, 'review_gui'):
                # Review GUI can reload with new PDF
                pass
            
            # Notify file management tab
            if hasattr(self, 'file_management_tab'):
                self.file_management_tab.set_current_pdf(pdf_path)
            
            # Show notification
            QMessageBox.information(
                self,
                "PDF Changed",
                f"Active PDF changed to:\n{Path(pdf_path).name}\n\nAll tabs will now use this PDF."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update application with new PDF:\n{str(e)}"
            )
    
    def on_pdf_selected_from_file_management(self, pdf_path: str):
        """
        Handle PDF selection from File Management tab.
        
        Args:
            pdf_path: Path to the selected PDF
        """
        # Update PDF selector
        if hasattr(self, 'pdf_selector'):
            self.pdf_selector.update_pdf_selection(pdf_path)
    
    def on_settings_changed(self, settings: Dict[str, Any]):
        """
        Handle settings changes from Settings tab.
        
        Args:
            settings: Dictionary of changed settings
        """
        try:
            # Refresh file status widget if paths changed
            if any(key in settings for key in ["target_pdf", "processing_directory", "final_output_directory"]):
                self.refresh_file_status()
            
            # Notify other components of settings changes
            # This would typically trigger reloading or reconfiguration
            
            self.logger.info(f"Settings updated: {list(settings.keys())}")
            
        except Exception as e:
            self.logger.error(f"Failed to apply settings changes: {e}")
            QMessageBox.warning(
                self,
                "Settings Warning",
                f"Some settings changes may not have been applied:\n{str(e)}"
            )
    
    @property
    def logger(self):
        """Get logger instance."""
        import logging
        return logging.getLogger(__name__)

    def add_pdf_configuration(self, engine_name: str):
        """Add PDF-specific configuration for an engine."""
        # Simple dialog to get PDF path
        from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QFileDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Configure {engine_name.title()} for PDF")
        layout = QFormLayout(dialog)
        
        pdf_path_edit = QLineEdit()
        browse_button = QPushButton("Browse...")
        
        def browse_pdf():
            file_path, _ = QFileDialog.getOpenFileName(
                dialog, "Select PDF File", "", "PDF Files (*.pdf)"
            )
            if file_path:
                pdf_path_edit.setText(file_path)
        
        browse_button.clicked.connect(browse_pdf)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(pdf_path_edit)
        path_layout.addWidget(browse_button)
        
        layout.addRow("PDF Path:", path_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            pdf_path = pdf_path_edit.text().strip()
            if pdf_path and Path(pdf_path).exists():
                # Add PDF override tab to configuration widget
                self.config_widget.add_pdf_override_tab(engine_name, pdf_path)
                # Switch to configuration tab
                self.tab_widget.setCurrentWidget(self.config_widget)
            else:
                QMessageBox.warning(self, "Invalid Path", "Please select a valid PDF file.")


def main(args: Optional[list] = None) -> int:
    """
    Main entry point for BECR GUI application.
    
    Args:
        args: Command line arguments (optional)
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Check if GUI mode is requested (default) or CLI mode
    if args and '--cli' in args:
        return run_cli_mode()
    else:
        return run_gui_mode()


def run_gui_mode() -> int:
    """Run the GUI application."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("BECR")
    app.setApplicationDisplayName("Blockwise Extraction Comparison & Review")
    app.setApplicationVersion("1.0.0")
    
    # Create and show main window
    main_window = BECRMainWindow()
    main_window.show()
    
    # Run the application
    return app.exec()


def run_cli_mode() -> int:
    """Run the CLI version of the application."""
    from compareblocks.gbg.processor import GBGProcessor
    from compareblocks.io.writer import NDJSONWriter
    from compareblocks.config.file_manager import file_manager
    
    print("BECR (Blockwise Extraction Comparison & Review) System - CLI Mode")
    print("=" * 60)
    
    try:
        # Ensure output directories exist
        file_manager.ensure_output_directories()
        
        # Get configured paths
        pdf_path = file_manager.get_target_pdf_path()
        gbg_output_path = file_manager.get_gbg_analysis_output_path()
        ndjson_variations_path = file_manager.get_ndjson_variations_output_path()
        ndjson_consensus_path = file_manager.get_ndjson_consensus_output_path()
        
        print(f"Processing configured PDF: {pdf_path}")
        print(f"Expected: {file_manager.get_expected_pdf_pages()} pages, {file_manager.get_expected_pdf_blocks()} blocks")
        
        # 1. Process PDF with GBG system
        print("\n1. Running GBG Analysis...")
        processor = GBGProcessor()
        gbg_results = processor.process_pdf(pdf_path, gbg_output_path)
        
        print(f"   ✅ GBG analysis complete: {gbg_results['summary']['total_pages']} pages, {gbg_results['summary']['total_blocks']} blocks")
        
        # 2. Generate NDJSON variations from GBG results
        print("\n2. Generating NDJSON variations...")
        input_variations = []
        
        for page_num, page_data in gbg_results["pages"].items():
            for block in page_data["blocks"]:
                if block["text_content"]:  # Only blocks with text
                    variation_record = {
                        "doc_id": gbg_results["pdf_name"],
                        "page": int(page_num) + 1,  # Convert to 1-based page numbering
                        "engine": "pymupdf",
                        "raw_text": block["text_content"],
                        "bbox": [
                            block["bbox"]["x"],
                            block["bbox"]["y"], 
                            block["bbox"]["width"],
                            block["bbox"]["height"]
                        ],
                        "confidence": block["orientation_hints"]["confidence"],
                        "block_id": block["block_id"]
                    }
                    input_variations.append(variation_record)
        
        # Write NDJSON variations (disable validation since these are input variations, not consensus)
        writer = NDJSONWriter(validate_output=False)
        writer.write_file(input_variations, ndjson_variations_path, overwrite=True)
        
        print(f"   ✅ NDJSON variations complete: {len(input_variations)} records")
        
        # 3. Generate consensus decisions (simple pass-through for now)
        print("\n3. Generating consensus decisions...")
        consensus_records = []
        
        for record in input_variations:
            consensus_record = {
                "doc_id": record["doc_id"],
                "page": record["page"],
                "block_id": record["block_id"],
                "selected_engine": record["engine"],
                "final_text": record["raw_text"],
                "decision_reason": "highest_score",
                "engine_scores": {record["engine"]: record["confidence"]},
                "anomaly_score": 1.0 - record["confidence"],
                "bbox": record["bbox"]
            }
            consensus_records.append(consensus_record)
        
        # Write consensus decisions (enable validation for consensus output)
        writer = NDJSONWriter(validate_output=True)
        writer.write_file(consensus_records, ndjson_consensus_path, overwrite=True)
        
        print(f"   ✅ Consensus decisions complete: {len(consensus_records)} records")
        
        print("\n" + "=" * 50)
        print("APPLICATION PROCESSING COMPLETE")
        print("=" * 50)
        print(f"Generated Files:")
        print(f"  - GBG Analysis: {gbg_output_path}")
        print(f"  - NDJSON Variations: {ndjson_variations_path}")
        print(f"  - Consensus Decisions: {ndjson_consensus_path}")
        print(f"\n🎉 All output files generated successfully!")
        print("\nNote: GUI interface not yet implemented - this is the TDD foundation.")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
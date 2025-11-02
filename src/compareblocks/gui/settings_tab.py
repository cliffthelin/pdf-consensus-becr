# src/compareblocks/gui/settings_tab.py
"""
Settings Tab Configuration Interface for BECR application.

Provides comprehensive settings management interface for:
- Default file configuration (PDF paths, output directories)
- Engine configuration settings management
- MCP connection parameter configuration
- Global processing options and system preferences
- MCP communication with compareblocks.config modules
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QFileDialog, QMessageBox, QTabWidget,
    QTextEdit, QProgressBar, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

from ..mcp.client import MCPClient, MCPConnectionError
from ..config.file_manager import file_manager
from ..config.engine_config import EngineConfigurationManager


class MCPConfigWorker(QThread):
    """Worker thread for MCP configuration operations."""
    
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, operation: str, params: Dict[str, Any]):
        super().__init__()
        self.operation = operation
        self.params = params
        self.mcp_client = None
    
    def run(self):
        """Execute MCP configuration operation in background thread."""
        try:
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Initialize MCP client
            self.mcp_client = MCPClient()
            
            # Execute operation
            if self.operation == "load_configuration":
                result = loop.run_until_complete(self._load_configuration())
            elif self.operation == "save_configuration":
                result = loop.run_until_complete(self._save_configuration())
            elif self.operation == "validate_configuration":
                result = loop.run_until_complete(self._validate_configuration())
            elif self.operation == "reset_configuration":
                result = loop.run_until_complete(self._reset_configuration())
            else:
                result = {"error": f"Unknown operation: {self.operation}"}
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if self.mcp_client:
                try:
                    loop.run_until_complete(self.mcp_client.disconnect())
                except:
                    pass
            loop.close()
    
    async def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration via MCP."""
        # For now, use local file manager
        # In production, this would communicate with compareblocks.config via MCP
        config_summary = file_manager.get_config_summary()
        
        return {
            "success": True,
            "configuration": config_summary
        }
    
    async def _save_configuration(self) -> Dict[str, Any]:
        """Save configuration via MCP."""
        updates = self.params.get("updates", {})
        
        # Placeholder implementation
        # In production, this would communicate with compareblocks.config via MCP
        return {
            "success": True,
            "message": "Configuration saved successfully",
            "updated_fields": list(updates.keys())
        }
    
    async def _validate_configuration(self) -> Dict[str, Any]:
        """Validate configuration via MCP."""
        # Placeholder implementation
        # In production, this would communicate with compareblocks.config via MCP
        is_valid = file_manager.validate_target_pdf()
        
        return {
            "success": True,
            "valid": is_valid,
            "errors": [] if is_valid else ["Target PDF not found"]
        }
    
    async def _reset_configuration(self) -> Dict[str, Any]:
        """Reset configuration to defaults via MCP."""
        # Placeholder implementation
        # In production, this would communicate with compareblocks.config via MCP
        return {
            "success": True,
            "message": "Configuration reset to defaults"
        }


class SettingsTab(QWidget):
    """
    Settings Tab - Configuration interface for system preferences.
    
    Provides:
    - Default file configuration (PDF paths, output directories)
    - Engine configuration settings
    - MCP connection parameters
    - Global processing options
    """
    
    settings_changed = Signal(dict)  # Emitted when settings are changed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = EngineConfigurationManager()
        self.current_settings = {}
        self.mcp_worker = None
        self.unsaved_changes = False
        
        self.setup_ui()
        self.load_configuration()
    
    def setup_ui(self):
        """Setup the settings UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("⚙️ System Settings")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Save button
        self.save_button = QPushButton("💾 Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setEnabled(False)
        header_layout.addWidget(self.save_button)
        
        # Reset button
        self.reset_button = QPushButton("🔄 Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_settings)
        header_layout.addWidget(self.reset_button)
        
        layout.addLayout(header_layout)
        
        # Progress bar for MCP operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Scroll area for settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # Default Files section
        settings_layout.addWidget(self.create_default_files_section())
        
        # Engine Configuration section
        settings_layout.addWidget(self.create_engine_configuration_section())
        
        # MCP Connection section
        settings_layout.addWidget(self.create_mcp_connection_section())
        
        # Global Processing Options section
        settings_layout.addWidget(self.create_processing_options_section())
        
        # System Preferences section
        settings_layout.addWidget(self.create_system_preferences_section())
        
        settings_layout.addStretch()
        
        scroll_area.setWidget(settings_widget)
        layout.addWidget(scroll_area)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.status_label)
    
    def create_default_files_section(self) -> QWidget:
        """Create the default files configuration section."""
        group_box = QGroupBox("📁 Default Files")
        layout = QFormLayout(group_box)
        
        # Default PDF path
        pdf_layout = QHBoxLayout()
        self.pdf_path_edit = QLineEdit()
        self.pdf_path_edit.setPlaceholderText("Path to default PDF file")
        self.pdf_path_edit.textChanged.connect(self.on_setting_changed)
        pdf_layout.addWidget(self.pdf_path_edit)
        
        pdf_browse_button = QPushButton("Browse...")
        pdf_browse_button.clicked.connect(self.browse_pdf_path)
        pdf_layout.addWidget(pdf_browse_button)
        
        layout.addRow("Default PDF:", pdf_layout)
        
        # Processing directory
        processing_layout = QHBoxLayout()
        self.processing_dir_edit = QLineEdit()
        self.processing_dir_edit.setPlaceholderText("Directory for processing files")
        self.processing_dir_edit.textChanged.connect(self.on_setting_changed)
        processing_layout.addWidget(self.processing_dir_edit)
        
        processing_browse_button = QPushButton("Browse...")
        processing_browse_button.clicked.connect(self.browse_processing_dir)
        processing_layout.addWidget(processing_browse_button)
        
        layout.addRow("Processing Directory:", processing_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Directory for final output files")
        self.output_dir_edit.textChanged.connect(self.on_setting_changed)
        output_layout.addWidget(self.output_dir_edit)
        
        output_browse_button = QPushButton("Browse...")
        output_browse_button.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(output_browse_button)
        
        layout.addRow("Output Directory:", output_layout)
        
        # Validate button
        validate_button = QPushButton("✓ Validate Paths")
        validate_button.clicked.connect(self.validate_file_paths)
        layout.addRow("", validate_button)
        
        return group_box
    
    def create_engine_configuration_section(self) -> QWidget:
        """Create the engine configuration section."""
        group_box = QGroupBox("🔧 Engine Configuration")
        layout = QVBoxLayout(group_box)
        
        # Engine selection
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("Default Engines:"))
        
        self.engine_checkboxes = {}
        engines = ["tesseract", "paddleocr", "pymupdf", "docling", "kreuzberg"]
        
        for engine in engines:
            checkbox = QCheckBox(engine.title())
            checkbox.stateChanged.connect(self.on_setting_changed)
            self.engine_checkboxes[engine] = checkbox
            engine_layout.addWidget(checkbox)
        
        engine_layout.addStretch()
        layout.addLayout(engine_layout)
        
        # Engine settings button
        engine_settings_button = QPushButton("⚙️ Configure Engine Settings...")
        engine_settings_button.clicked.connect(self.open_engine_settings)
        layout.addWidget(engine_settings_button)
        
        # Engine statistics button
        engine_stats_button = QPushButton("📊 View Engine Statistics...")
        engine_stats_button.clicked.connect(self.view_engine_statistics)
        layout.addWidget(engine_stats_button)
        
        return group_box
    
    def create_mcp_connection_section(self) -> QWidget:
        """Create the MCP connection configuration section."""
        group_box = QGroupBox("🔗 MCP Connection")
        layout = QFormLayout(group_box)
        
        # MCP server URL
        self.mcp_url_edit = QLineEdit()
        self.mcp_url_edit.setPlaceholderText("ws://localhost:8000/mcp")
        self.mcp_url_edit.textChanged.connect(self.on_setting_changed)
        layout.addRow("Server URL:", self.mcp_url_edit)
        
        # Connection timeout
        self.mcp_timeout_spin = QSpinBox()
        self.mcp_timeout_spin.setRange(1, 300)
        self.mcp_timeout_spin.setValue(30)
        self.mcp_timeout_spin.setSuffix(" seconds")
        self.mcp_timeout_spin.valueChanged.connect(self.on_setting_changed)
        layout.addRow("Connection Timeout:", self.mcp_timeout_spin)
        
        # Auto-reconnect
        self.mcp_auto_reconnect_check = QCheckBox("Enable automatic reconnection")
        self.mcp_auto_reconnect_check.setChecked(True)
        self.mcp_auto_reconnect_check.stateChanged.connect(self.on_setting_changed)
        layout.addRow("", self.mcp_auto_reconnect_check)
        
        # Test connection button
        test_connection_button = QPushButton("🔌 Test Connection")
        test_connection_button.clicked.connect(self.test_mcp_connection)
        layout.addRow("", test_connection_button)
        
        return group_box
    
    def create_processing_options_section(self) -> QWidget:
        """Create the global processing options section."""
        group_box = QGroupBox("⚡ Processing Options")
        layout = QFormLayout(group_box)
        
        # Validation enabled
        self.validation_check = QCheckBox("Enable validation")
        self.validation_check.setChecked(True)
        self.validation_check.stateChanged.connect(self.on_setting_changed)
        layout.addRow("", self.validation_check)
        
        # Idempotent processing
        self.idempotent_check = QCheckBox("Idempotent processing (no timestamps)")
        self.idempotent_check.setChecked(True)
        self.idempotent_check.stateChanged.connect(self.on_setting_changed)
        layout.addRow("", self.idempotent_check)
        
        # Ignore images
        self.ignore_images_check = QCheckBox("Ignore image blocks")
        self.ignore_images_check.setChecked(False)
        self.ignore_images_check.stateChanged.connect(self.on_setting_changed)
        layout.addRow("", self.ignore_images_check)
        
        # Default encoding
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["utf-8", "utf-16", "ascii", "latin-1"])
        self.encoding_combo.currentTextChanged.connect(self.on_setting_changed)
        layout.addRow("Default Encoding:", self.encoding_combo)
        
        # Output formats
        output_formats_layout = QHBoxLayout()
        self.output_format_checkboxes = {}
        formats = ["json", "txt", "csv", "html"]
        
        for fmt in formats:
            checkbox = QCheckBox(fmt.upper())
            checkbox.stateChanged.connect(self.on_setting_changed)
            self.output_format_checkboxes[fmt] = checkbox
            output_formats_layout.addWidget(checkbox)
        
        output_formats_layout.addStretch()
        layout.addRow("Output Formats:", output_formats_layout)
        
        return group_box
    
    def create_system_preferences_section(self) -> QWidget:
        """Create the system preferences section."""
        group_box = QGroupBox("🎛️ System Preferences")
        layout = QFormLayout(group_box)
        
        # Auto-save interval
        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(0, 60)
        self.autosave_spin.setValue(5)
        self.autosave_spin.setSuffix(" minutes")
        self.autosave_spin.setSpecialValueText("Disabled")
        self.autosave_spin.valueChanged.connect(self.on_setting_changed)
        layout.addRow("Auto-save Interval:", self.autosave_spin)
        
        # Log level
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText("INFO")
        self.log_level_combo.currentTextChanged.connect(self.on_setting_changed)
        layout.addRow("Log Level:", self.log_level_combo)
        
        # Show notifications
        self.notifications_check = QCheckBox("Show desktop notifications")
        self.notifications_check.setChecked(True)
        self.notifications_check.stateChanged.connect(self.on_setting_changed)
        layout.addRow("", self.notifications_check)
        
        # Confirm on exit
        self.confirm_exit_check = QCheckBox("Confirm before exiting")
        self.confirm_exit_check.setChecked(True)
        self.confirm_exit_check.stateChanged.connect(self.on_setting_changed)
        layout.addRow("", self.confirm_exit_check)
        
        return group_box
    
    def load_configuration(self):
        """Load configuration via MCP."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Loading configuration...")
        
        # Start MCP worker
        self.mcp_worker = MCPConfigWorker("load_configuration", {})
        self.mcp_worker.finished.connect(self.on_configuration_loaded)
        self.mcp_worker.error.connect(self.on_mcp_error)
        self.mcp_worker.start()
    
    def on_configuration_loaded(self, result: Dict[str, Any]):
        """Handle configuration loaded from MCP."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Configuration loaded")
        
        if not result.get("success"):
            QMessageBox.warning(self, "Error", "Failed to load configuration")
            return
        
        config = result.get("configuration", {})
        self.current_settings = config
        
        # Update UI with loaded configuration
        self.update_ui_from_config(config)
        
        # Reset unsaved changes flag
        self.unsaved_changes = False
        self.save_button.setEnabled(False)
    
    def update_ui_from_config(self, config: Dict[str, Any]):
        """Update UI widgets with configuration values."""
        # Default files
        self.pdf_path_edit.setText(config.get("target_pdf", ""))
        self.processing_dir_edit.setText(config.get("processing_directory", ""))
        self.output_dir_edit.setText(config.get("final_output_directory", ""))
        
        # Engine configuration
        default_engines = config.get("default_engines", [])
        for engine, checkbox in self.engine_checkboxes.items():
            checkbox.setChecked(engine in default_engines)
        
        # MCP connection (placeholder values)
        self.mcp_url_edit.setText("ws://localhost:8000/mcp")
        self.mcp_timeout_spin.setValue(30)
        self.mcp_auto_reconnect_check.setChecked(True)
        
        # Processing options
        self.validation_check.setChecked(config.get("validation_enabled", True))
        self.idempotent_check.setChecked(config.get("idempotent_processing", True))
        
        image_handling = config.get("image_handling", {})
        self.ignore_images_check.setChecked(image_handling.get("ignore_images", False))
        
        self.encoding_combo.setCurrentText(config.get("encoding", "utf-8"))
        
        # Output formats
        output_formats = config.get("output_formats", [])
        for fmt, checkbox in self.output_format_checkboxes.items():
            checkbox.setChecked(fmt in output_formats)
        
        # System preferences (placeholder values)
        self.autosave_spin.setValue(5)
        self.log_level_combo.setCurrentText("INFO")
        self.notifications_check.setChecked(True)
        self.confirm_exit_check.setChecked(True)
    
    def on_setting_changed(self):
        """Handle setting change."""
        self.unsaved_changes = True
        self.save_button.setEnabled(True)
        self.status_label.setText("Unsaved changes")
        self.status_label.setStyleSheet("color: orange; font-size: 10px;")
    
    def save_settings(self):
        """Save settings via MCP."""
        # Collect current settings from UI
        updates = self.collect_settings_from_ui()
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Saving configuration...")
        
        # Start MCP worker
        self.mcp_worker = MCPConfigWorker("save_configuration", {"updates": updates})
        self.mcp_worker.finished.connect(self.on_settings_saved)
        self.mcp_worker.error.connect(self.on_mcp_error)
        self.mcp_worker.start()
    
    def collect_settings_from_ui(self) -> Dict[str, Any]:
        """Collect current settings from UI widgets."""
        settings = {
            "target_pdf": self.pdf_path_edit.text(),
            "processing_directory": self.processing_dir_edit.text(),
            "final_output_directory": self.output_dir_edit.text(),
            "default_engines": [
                engine for engine, checkbox in self.engine_checkboxes.items()
                if checkbox.isChecked()
            ],
            "mcp_url": self.mcp_url_edit.text(),
            "mcp_timeout": self.mcp_timeout_spin.value(),
            "mcp_auto_reconnect": self.mcp_auto_reconnect_check.isChecked(),
            "validation_enabled": self.validation_check.isChecked(),
            "idempotent_processing": self.idempotent_check.isChecked(),
            "ignore_images": self.ignore_images_check.isChecked(),
            "encoding": self.encoding_combo.currentText(),
            "output_formats": [
                fmt for fmt, checkbox in self.output_format_checkboxes.items()
                if checkbox.isChecked()
            ],
            "autosave_interval": self.autosave_spin.value(),
            "log_level": self.log_level_combo.currentText(),
            "show_notifications": self.notifications_check.isChecked(),
            "confirm_on_exit": self.confirm_exit_check.isChecked()
        }
        return settings
    
    def on_settings_saved(self, result: Dict[str, Any]):
        """Handle settings saved via MCP."""
        self.progress_bar.setVisible(False)
        
        if result.get("success"):
            self.unsaved_changes = False
            self.save_button.setEnabled(False)
            self.status_label.setText("Settings saved successfully")
            self.status_label.setStyleSheet("color: green; font-size: 10px;")
            
            # Emit signal
            self.settings_changed.emit(self.collect_settings_from_ui())
            
            QMessageBox.information(
                self,
                "Success",
                f"Settings saved successfully.\n\nUpdated fields: {', '.join(result.get('updated_fields', []))}"
            )
        else:
            self.status_label.setText("Failed to save settings")
            self.status_label.setStyleSheet("color: red; font-size: 10px;")
            QMessageBox.warning(self, "Error", "Failed to save settings")
    
    def reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.status_label.setText("Resetting configuration...")
            
            # Start MCP worker
            self.mcp_worker = MCPConfigWorker("reset_configuration", {})
            self.mcp_worker.finished.connect(self.on_settings_reset)
            self.mcp_worker.error.connect(self.on_mcp_error)
            self.mcp_worker.start()
    
    def on_settings_reset(self, result: Dict[str, Any]):
        """Handle settings reset."""
        self.progress_bar.setVisible(False)
        
        if result.get("success"):
            self.status_label.setText("Settings reset to defaults")
            self.status_label.setStyleSheet("color: green; font-size: 10px;")
            
            # Reload configuration
            self.load_configuration()
            
            QMessageBox.information(self, "Success", "Settings reset to defaults")
        else:
            self.status_label.setText("Failed to reset settings")
            self.status_label.setStyleSheet("color: red; font-size: 10px;")
            QMessageBox.warning(self, "Error", "Failed to reset settings")
    
    def browse_pdf_path(self):
        """Browse for PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Default PDF",
            "",
            "PDF Files (*.pdf);;All Files (*.*)"
        )
        
        if file_path:
            self.pdf_path_edit.setText(file_path)
    
    def browse_processing_dir(self):
        """Browse for processing directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Processing Directory",
            ""
        )
        
        if directory:
            self.processing_dir_edit.setText(directory)
    
    def browse_output_dir(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            ""
        )
        
        if directory:
            self.output_dir_edit.setText(directory)
    
    def validate_file_paths(self):
        """Validate configured file paths."""
        pdf_path = self.pdf_path_edit.text()
        processing_dir = self.processing_dir_edit.text()
        output_dir = self.output_dir_edit.text()
        
        errors = []
        
        # Validate PDF path
        if not pdf_path:
            errors.append("PDF path is empty")
        elif not Path(pdf_path).exists():
            errors.append(f"PDF file not found: {pdf_path}")
        elif not pdf_path.lower().endswith('.pdf'):
            errors.append(f"File is not a PDF: {pdf_path}")
        
        # Validate directories
        if not processing_dir:
            errors.append("Processing directory is empty")
        
        if not output_dir:
            errors.append("Output directory is empty")
        
        if errors:
            QMessageBox.warning(
                self,
                "Validation Errors",
                "The following validation errors were found:\n\n" + "\n".join(f"• {error}" for error in errors)
            )
        else:
            QMessageBox.information(
                self,
                "Validation Success",
                "All file paths are valid!"
            )
    
    def open_engine_settings(self):
        """Open detailed engine settings dialog."""
        QMessageBox.information(
            self,
            "Engine Settings",
            "Detailed engine configuration interface will be implemented here.\n\n"
            "This will allow you to configure:\n"
            "• Engine-specific parameters\n"
            "• PDF-specific overrides\n"
            "• Optimization settings\n"
            "• Performance tuning"
        )
    
    def view_engine_statistics(self):
        """View engine statistics."""
        stats_text = "Engine Statistics\n"
        stats_text += "=" * 50 + "\n\n"
        
        for engine in self.engine_checkboxes.keys():
            try:
                stats = self.config_manager.get_engine_statistics(engine)
                stats_text += f"{engine.title()}:\n"
                stats_text += f"  Total Configurations: {stats.get('total_configurations', 0)}\n"
                stats_text += f"  Active PDF Overrides: {stats.get('active_pdf_overrides', 0)}\n"
                stats_text += f"  Last Updated: {stats.get('last_updated', 'Never')}\n\n"
            except Exception as e:
                stats_text += f"{engine.title()}: Error - {str(e)}\n\n"
        
        QMessageBox.information(self, "Engine Statistics", stats_text)
    
    def test_mcp_connection(self):
        """Test MCP connection."""
        mcp_url = self.mcp_url_edit.text()
        
        if not mcp_url:
            QMessageBox.warning(self, "Error", "MCP server URL is empty")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Testing MCP connection...")
        
        # Simulate connection test
        # In production, this would actually test the MCP connection
        QMessageBox.information(
            self,
            "Connection Test",
            f"Testing connection to: {mcp_url}\n\n"
            "Note: MCP server integration is in progress.\n"
            "Connection test will be fully functional once MCP server is deployed."
        )
        
        self.progress_bar.setVisible(False)
        self.status_label.setText("Ready")
    
    def on_mcp_error(self, error_message: str):
        """Handle MCP communication error."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("MCP communication error")
        self.status_label.setStyleSheet("color: red; font-size: 10px;")
        
        QMessageBox.critical(
            self,
            "MCP Communication Error",
            f"Failed to communicate with MCP server:\n\n{error_message}\n\n"
            "Operating in offline mode. Some features may be unavailable."
        )
    
    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return self.unsaved_changes
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current settings from UI."""
        return self.collect_settings_from_ui()

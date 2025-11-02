# tests/gui/test_settings_tab.py
"""
Comprehensive tests for Settings Tab Configuration Interface.

Tests cover:
- Settings Tab UI initialization and layout
- Default file configuration interface
- Engine configuration settings management
- MCP connection parameter configuration
- Global processing options and system preferences
- MCP communication with compareblocks.config modules
- Settings validation and error handling
- User interactions and workflows
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from src.compareblocks.gui.settings_tab import SettingsTab, MCPConfigWorker
from src.compareblocks.config.file_manager import file_manager


@pytest.fixture
def app(qapp):
    """Provide QApplication instance."""
    return qapp


@pytest.fixture
def settings_tab(qtbot):
    """Create SettingsTab instance for testing."""
    tab = SettingsTab()
    qtbot.addWidget(tab)
    return tab


class TestSettingsTabInitialization:
    """Test Settings Tab initialization and UI setup."""
    
    def test_settings_tab_creation(self, settings_tab):
        """Test that Settings Tab is created successfully."""
        assert settings_tab is not None
        assert settings_tab.windowTitle() == "" or "Settings" in settings_tab.windowTitle()
    
    def test_ui_components_exist(self, settings_tab):
        """Test that all major UI components are created."""
        # Check for main sections
        assert settings_tab.pdf_path_edit is not None
        assert settings_tab.processing_dir_edit is not None
        assert settings_tab.output_dir_edit is not None
        assert settings_tab.engine_checkboxes is not None
        assert settings_tab.mcp_url_edit is not None
        assert settings_tab.save_button is not None
        assert settings_tab.reset_button is not None
    
    def test_engine_checkboxes_created(self, settings_tab):
        """Test that engine checkboxes are created for all engines."""
        expected_engines = ["tesseract", "paddleocr", "pymupdf", "docling", "kreuzberg"]
        
        for engine in expected_engines:
            assert engine in settings_tab.engine_checkboxes
            assert settings_tab.engine_checkboxes[engine] is not None
    
    def test_output_format_checkboxes_created(self, settings_tab):
        """Test that output format checkboxes are created."""
        expected_formats = ["json", "txt", "csv", "html"]
        
        for fmt in expected_formats:
            assert fmt in settings_tab.output_format_checkboxes
            assert settings_tab.output_format_checkboxes[fmt] is not None
    
    def test_initial_state(self, settings_tab):
        """Test initial state of Settings Tab."""
        assert settings_tab.unsaved_changes == False
        assert settings_tab.save_button.isEnabled() == False


class TestDefaultFilesConfiguration:
    """Test default files configuration interface."""
    
    def test_pdf_path_edit(self, settings_tab, qtbot):
        """Test PDF path editing."""
        test_path = "/path/to/test.pdf"
        
        qtbot.keyClicks(settings_tab.pdf_path_edit, test_path)
        
        assert settings_tab.pdf_path_edit.text() == test_path
        assert settings_tab.unsaved_changes == True
        assert settings_tab.save_button.isEnabled() == True
    
    def test_processing_directory_edit(self, settings_tab, qtbot):
        """Test processing directory editing."""
        test_dir = "/path/to/processing"
        
        qtbot.keyClicks(settings_tab.processing_dir_edit, test_dir)
        
        assert settings_tab.processing_dir_edit.text() == test_dir
        assert settings_tab.unsaved_changes == True
    
    def test_output_directory_edit(self, settings_tab, qtbot):
        """Test output directory editing."""
        test_dir = "/path/to/output"
        
        qtbot.keyClicks(settings_tab.output_dir_edit, test_dir)
        
        assert settings_tab.output_dir_edit.text() == test_dir
        assert settings_tab.unsaved_changes == True
    
    def test_browse_pdf_path(self, settings_tab, qtbot, monkeypatch):
        """Test browsing for PDF file."""
        test_path = "/path/to/selected.pdf"
        
        # Mock file dialog
        monkeypatch.setattr(
            'PySide6.QtWidgets.QFileDialog.getOpenFileName',
            lambda *args, **kwargs: (test_path, "PDF Files (*.pdf)")
        )
        
        settings_tab.browse_pdf_path()
        
        assert settings_tab.pdf_path_edit.text() == test_path
    
    def test_browse_processing_directory(self, settings_tab, qtbot, monkeypatch):
        """Test browsing for processing directory."""
        test_dir = "/path/to/processing"
        
        # Mock directory dialog
        monkeypatch.setattr(
            'PySide6.QtWidgets.QFileDialog.getExistingDirectory',
            lambda *args, **kwargs: test_dir
        )
        
        settings_tab.browse_processing_dir()
        
        assert settings_tab.processing_dir_edit.text() == test_dir
    
    def test_validate_file_paths_success(self, settings_tab, qtbot, monkeypatch, tmp_path):
        """Test file path validation with valid paths."""
        # Create temporary PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("test")
        
        settings_tab.pdf_path_edit.setText(str(pdf_file))
        settings_tab.processing_dir_edit.setText(str(tmp_path / "processing"))
        settings_tab.output_dir_edit.setText(str(tmp_path / "output"))
        
        # Mock message box
        mock_info = Mock()
        monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.information', mock_info)
        
        settings_tab.validate_file_paths()
        
        # Should show success message
        mock_info.assert_called_once()
        assert "valid" in mock_info.call_args[0][2].lower()
    
    def test_validate_file_paths_errors(self, settings_tab, qtbot, monkeypatch):
        """Test file path validation with invalid paths."""
        settings_tab.pdf_path_edit.setText("/nonexistent/file.pdf")
        settings_tab.processing_dir_edit.setText("")
        settings_tab.output_dir_edit.setText("")
        
        # Mock message box
        mock_warning = Mock()
        monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.warning', mock_warning)
        
        settings_tab.validate_file_paths()
        
        # Should show error message
        mock_warning.assert_called_once()
        assert "error" in mock_warning.call_args[0][2].lower()


class TestEngineConfiguration:
    """Test engine configuration settings management."""
    
    def test_engine_checkbox_selection(self, settings_tab, qtbot):
        """Test selecting engines via checkboxes."""
        # Select tesseract
        tesseract_checkbox = settings_tab.engine_checkboxes["tesseract"]
        qtbot.mouseClick(tesseract_checkbox, Qt.LeftButton)
        
        assert tesseract_checkbox.isChecked()
        assert settings_tab.unsaved_changes == True
    
    def test_multiple_engine_selection(self, settings_tab, qtbot):
        """Test selecting multiple engines."""
        engines_to_select = ["tesseract", "pymupdf", "paddleocr"]
        
        for engine in engines_to_select:
            checkbox = settings_tab.engine_checkboxes[engine]
            qtbot.mouseClick(checkbox, Qt.LeftButton)
        
        # Verify all selected
        for engine in engines_to_select:
            assert settings_tab.engine_checkboxes[engine].isChecked()
    
    def test_collect_selected_engines(self, settings_tab, qtbot):
        """Test collecting selected engines from UI."""
        # Select specific engines
        settings_tab.engine_checkboxes["tesseract"].setChecked(True)
        settings_tab.engine_checkboxes["pymupdf"].setChecked(True)
        
        settings = settings_tab.collect_settings_from_ui()
        
        assert "tesseract" in settings["default_engines"]
        assert "pymupdf" in settings["default_engines"]
        assert "paddleocr" not in settings["default_engines"]
    
    def test_open_engine_settings(self, settings_tab, qtbot, monkeypatch):
        """Test opening engine settings dialog."""
        mock_info = Mock()
        monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.information', mock_info)
        
        settings_tab.open_engine_settings()
        
        # Should show info dialog
        mock_info.assert_called_once()
    
    def test_view_engine_statistics(self, settings_tab, qtbot, monkeypatch):
        """Test viewing engine statistics."""
        mock_info = Mock()
        monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.information', mock_info)
        
        settings_tab.view_engine_statistics()
        
        # Should show statistics dialog
        mock_info.assert_called_once()
        assert "statistics" in mock_info.call_args[0][2].lower()


class TestMCPConnectionConfiguration:
    """Test MCP connection parameter configuration."""
    
    def test_mcp_url_edit(self, settings_tab, qtbot):
        """Test MCP URL editing."""
        test_url = "ws://localhost:9000/mcp"
        
        qtbot.keyClicks(settings_tab.mcp_url_edit, test_url)
        
        assert settings_tab.mcp_url_edit.text() == test_url
        assert settings_tab.unsaved_changes == True
    
    def test_mcp_timeout_setting(self, settings_tab, qtbot):
        """Test MCP timeout configuration."""
        settings_tab.mcp_timeout_spin.setValue(60)
        
        assert settings_tab.mcp_timeout_spin.value() == 60
        assert settings_tab.unsaved_changes == True
    
    def test_mcp_auto_reconnect_toggle(self, settings_tab, qtbot):
        """Test MCP auto-reconnect toggle."""
        initial_state = settings_tab.mcp_auto_reconnect_check.isChecked()
        
        qtbot.mouseClick(settings_tab.mcp_auto_reconnect_check, Qt.LeftButton)
        
        assert settings_tab.mcp_auto_reconnect_check.isChecked() != initial_state
        assert settings_tab.unsaved_changes == True
    
    def test_test_mcp_connection(self, settings_tab, qtbot, monkeypatch):
        """Test MCP connection testing."""
        settings_tab.mcp_url_edit.setText("ws://localhost:8000/mcp")
        
        mock_info = Mock()
        monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.information', mock_info)
        
        settings_tab.test_mcp_connection()
        
        # Should show connection test dialog
        mock_info.assert_called_once()
    
    def test_test_mcp_connection_empty_url(self, settings_tab, qtbot, monkeypatch):
        """Test MCP connection test with empty URL."""
        settings_tab.mcp_url_edit.setText("")
        
        mock_warning = Mock()
        monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.warning', mock_warning)
        
        settings_tab.test_mcp_connection()
        
        # Should show warning
        mock_warning.assert_called_once()


class TestProcessingOptions:
    """Test global processing options configuration."""
    
    def test_validation_toggle(self, settings_tab, qtbot):
        """Test validation enabled toggle."""
        initial_state = settings_tab.validation_check.isChecked()
        
        qtbot.mouseClick(settings_tab.validation_check, Qt.LeftButton)
        
        assert settings_tab.validation_check.isChecked() != initial_state
        assert settings_tab.unsaved_changes == True
    
    def test_idempotent_processing_toggle(self, settings_tab, qtbot):
        """Test idempotent processing toggle."""
        initial_state = settings_tab.idempotent_check.isChecked()
        
        qtbot.mouseClick(settings_tab.idempotent_check, Qt.LeftButton)
        
        assert settings_tab.idempotent_check.isChecked() != initial_state
        assert settings_tab.unsaved_changes == True
    
    def test_ignore_images_toggle(self, settings_tab, qtbot):
        """Test ignore images toggle."""
        initial_state = settings_tab.ignore_images_check.isChecked()
        
        qtbot.mouseClick(settings_tab.ignore_images_check, Qt.LeftButton)
        
        assert settings_tab.ignore_images_check.isChecked() != initial_state
        assert settings_tab.unsaved_changes == True
    
    def test_encoding_selection(self, settings_tab, qtbot):
        """Test encoding selection."""
        settings_tab.encoding_combo.setCurrentText("utf-16")
        
        assert settings_tab.encoding_combo.currentText() == "utf-16"
        assert settings_tab.unsaved_changes == True
    
    def test_output_format_selection(self, settings_tab, qtbot):
        """Test output format selection."""
        # Select JSON and CSV
        settings_tab.output_format_checkboxes["json"].setChecked(True)
        settings_tab.output_format_checkboxes["csv"].setChecked(True)
        
        settings = settings_tab.collect_settings_from_ui()
        
        assert "json" in settings["output_formats"]
        assert "csv" in settings["output_formats"]
        assert "txt" not in settings["output_formats"]


class TestSystemPreferences:
    """Test system preferences configuration."""
    
    def test_autosave_interval_setting(self, settings_tab, qtbot):
        """Test autosave interval configuration."""
        settings_tab.autosave_spin.setValue(10)
        
        assert settings_tab.autosave_spin.value() == 10
        assert settings_tab.unsaved_changes == True
    
    def test_log_level_selection(self, settings_tab, qtbot):
        """Test log level selection."""
        settings_tab.log_level_combo.setCurrentText("DEBUG")
        
        assert settings_tab.log_level_combo.currentText() == "DEBUG"
        assert settings_tab.unsaved_changes == True
    
    def test_notifications_toggle(self, settings_tab, qtbot):
        """Test notifications toggle."""
        initial_state = settings_tab.notifications_check.isChecked()
        
        qtbot.mouseClick(settings_tab.notifications_check, Qt.LeftButton)
        
        assert settings_tab.notifications_check.isChecked() != initial_state
        assert settings_tab.unsaved_changes == True
    
    def test_confirm_exit_toggle(self, settings_tab, qtbot):
        """Test confirm on exit toggle."""
        initial_state = settings_tab.confirm_exit_check.isChecked()
        
        qtbot.mouseClick(settings_tab.confirm_exit_check, Qt.LeftButton)
        
        assert settings_tab.confirm_exit_check.isChecked() != initial_state
        assert settings_tab.unsaved_changes == True


class TestSettingsPersistence:
    """Test settings loading, saving, and persistence."""
    
    def test_load_configuration(self, settings_tab, qtbot):
        """Test loading configuration."""
        # Configuration should be loaded on initialization
        assert settings_tab.current_settings is not None
    
    def test_collect_settings_from_ui(self, settings_tab, qtbot):
        """Test collecting all settings from UI."""
        # Set some values
        settings_tab.pdf_path_edit.setText("/test/path.pdf")
        settings_tab.engine_checkboxes["tesseract"].setChecked(True)
        settings_tab.validation_check.setChecked(True)
        
        settings = settings_tab.collect_settings_from_ui()
        
        assert settings["target_pdf"] == "/test/path.pdf"
        assert "tesseract" in settings["default_engines"]
        assert settings["validation_enabled"] == True
    
    def test_update_ui_from_config(self, settings_tab, qtbot):
        """Test updating UI from configuration."""
        test_config = {
            "target_pdf": "/test/config.pdf",
            "processing_directory": "/test/processing",
            "final_output_directory": "/test/output",
            "default_engines": ["tesseract", "pymupdf"],
            "validation_enabled": False,
            "idempotent_processing": True,
            "image_handling": {"ignore_images": True},
            "encoding": "utf-16",
            "output_formats": ["json", "csv"]
        }
        
        settings_tab.update_ui_from_config(test_config)
        
        assert settings_tab.pdf_path_edit.text() == "/test/config.pdf"
        assert settings_tab.engine_checkboxes["tesseract"].isChecked()
        assert settings_tab.engine_checkboxes["pymupdf"].isChecked()
        assert not settings_tab.engine_checkboxes["paddleocr"].isChecked()
        assert settings_tab.validation_check.isChecked() == False
        assert settings_tab.ignore_images_check.isChecked() == True
        assert settings_tab.encoding_combo.currentText() == "utf-16"
    
    def test_save_settings_workflow(self, settings_tab, qtbot, monkeypatch):
        """Test complete save settings workflow."""
        # Make some changes
        settings_tab.pdf_path_edit.setText("/new/path.pdf")
        
        assert settings_tab.unsaved_changes == True
        assert settings_tab.save_button.isEnabled() == True
        
        # Mock MCP worker
        mock_worker = Mock()
        mock_worker.start = Mock()
        
        with patch('src.compareblocks.gui.settings_tab.MCPConfigWorker', return_value=mock_worker):
            settings_tab.save_settings()
            
            # Worker should be started
            mock_worker.start.assert_called_once()
    
    def test_reset_settings_workflow(self, settings_tab, qtbot, monkeypatch):
        """Test reset settings workflow."""
        # Mock confirmation dialog
        monkeypatch.setattr(
            'PySide6.QtWidgets.QMessageBox.question',
            lambda *args, **kwargs: QMessageBox.Yes
        )
        
        # Mock MCP worker
        mock_worker = Mock()
        mock_worker.start = Mock()
        
        with patch('src.compareblocks.gui.settings_tab.MCPConfigWorker', return_value=mock_worker):
            settings_tab.reset_settings()
            
            # Worker should be started
            mock_worker.start.assert_called_once()
    
    def test_reset_settings_cancelled(self, settings_tab, qtbot, monkeypatch):
        """Test reset settings when user cancels."""
        # Mock confirmation dialog to return No
        monkeypatch.setattr(
            'PySide6.QtWidgets.QMessageBox.question',
            lambda *args, **kwargs: QMessageBox.No
        )
        
        # Mock MCP worker
        mock_worker = Mock()
        mock_worker.start = Mock()
        
        with patch('src.compareblocks.gui.settings_tab.MCPConfigWorker', return_value=mock_worker):
            settings_tab.reset_settings()
            
            # Worker should NOT be started
            mock_worker.start.assert_not_called()


class TestMCPCommunication:
    """Test MCP communication for settings management."""
    
    def test_mcp_worker_load_configuration(self, qtbot):
        """Test MCP worker loading configuration."""
        worker = MCPConfigWorker("load_configuration", {})
        
        # Mock the run method to avoid actual MCP communication
        with patch.object(worker, 'run'):
            worker.start()
    
    def test_mcp_worker_save_configuration(self, qtbot):
        """Test MCP worker saving configuration."""
        updates = {"target_pdf": "/new/path.pdf"}
        worker = MCPConfigWorker("save_configuration", {"updates": updates})
        
        # Mock the run method
        with patch.object(worker, 'run'):
            worker.start()
    
    def test_on_configuration_loaded_success(self, settings_tab, qtbot):
        """Test handling successful configuration load."""
        result = {
            "success": True,
            "configuration": {
                "target_pdf": "/test/path.pdf",
                "default_engines": ["tesseract"],
                "validation_enabled": True
            }
        }
        
        settings_tab.on_configuration_loaded(result)
        
        assert settings_tab.unsaved_changes == False
        assert settings_tab.save_button.isEnabled() == False
    
    def test_on_configuration_loaded_failure(self, settings_tab, qtbot, monkeypatch):
        """Test handling failed configuration load."""
        result = {"success": False}
        
        mock_warning = Mock()
        monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.warning', mock_warning)
        
        settings_tab.on_configuration_loaded(result)
        
        # Should show warning
        mock_warning.assert_called_once()
    
    def test_on_settings_saved_success(self, settings_tab, qtbot, monkeypatch):
        """Test handling successful settings save."""
        settings_tab.unsaved_changes = True
        settings_tab.save_button.setEnabled(True)
        
        result = {
            "success": True,
            "updated_fields": ["target_pdf", "default_engines"]
        }
        
        mock_info = Mock()
        monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.information', mock_info)
        
        settings_tab.on_settings_saved(result)
        
        assert settings_tab.unsaved_changes == False
        assert settings_tab.save_button.isEnabled() == False
        mock_info.assert_called_once()
    
    def test_on_mcp_error(self, settings_tab, qtbot, monkeypatch):
        """Test handling MCP communication error."""
        mock_critical = Mock()
        monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.critical', mock_critical)
        
        settings_tab.on_mcp_error("Connection failed")
        
        # Should show error dialog
        mock_critical.assert_called_once()
        assert "connection failed" in mock_critical.call_args[0][2].lower()


class TestUserWorkflows:
    """Test complete user workflows."""
    
    def test_complete_configuration_workflow(self, settings_tab, qtbot, monkeypatch, tmp_path):
        """Test complete configuration workflow from load to save."""
        # Create temporary PDF
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("test")
        
        # 1. Load configuration (already done in initialization)
        assert settings_tab.current_settings is not None
        
        # 2. Modify settings
        settings_tab.pdf_path_edit.setText(str(pdf_file))
        settings_tab.engine_checkboxes["tesseract"].setChecked(True)
        settings_tab.validation_check.setChecked(False)
        
        # 3. Verify unsaved changes
        assert settings_tab.unsaved_changes == True
        assert settings_tab.save_button.isEnabled() == True
        
        # 4. Collect settings
        settings = settings_tab.collect_settings_from_ui()
        assert settings["target_pdf"] == str(pdf_file)
        assert "tesseract" in settings["default_engines"]
        assert settings["validation_enabled"] == False
    
    def test_validation_before_save_workflow(self, settings_tab, qtbot, monkeypatch, tmp_path):
        """Test validating paths before saving."""
        # Create temporary PDF
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("test")
        
        # Set valid paths
        settings_tab.pdf_path_edit.setText(str(pdf_file))
        settings_tab.processing_dir_edit.setText(str(tmp_path / "processing"))
        settings_tab.output_dir_edit.setText(str(tmp_path / "output"))
        
        # Mock message box
        mock_info = Mock()
        monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.information', mock_info)
        
        # Validate
        settings_tab.validate_file_paths()
        
        # Should show success
        mock_info.assert_called_once()
        assert "valid" in mock_info.call_args[0][2].lower()


class TestIntegrationWithFileManager:
    """Test integration with file manager."""
    
    def test_load_from_file_manager(self, settings_tab, qtbot):
        """Test loading configuration from file manager."""
        # Configuration should be loaded from file manager
        config = settings_tab.current_settings
        
        # Should have key configuration fields
        assert "target_pdf" in config
        assert "default_engines" in config
        assert "validation_enabled" in config
    
    def test_settings_match_file_manager(self, settings_tab, qtbot):
        """Test that loaded settings match file manager configuration."""
        config = settings_tab.current_settings
        
        # Compare with file manager
        fm_config = file_manager.get_config_summary()
        
        assert config["target_pdf"] == fm_config["target_pdf"]
        assert config["validation_enabled"] == fm_config["validation_enabled"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

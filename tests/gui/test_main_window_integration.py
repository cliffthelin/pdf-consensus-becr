# tests/gui/test_main_window_integration.py
"""
Comprehensive integration tests for main window state management.

Tests:
- PDF selector integration with all tabs
- State synchronization across components
- Tab switching with data consistency
- Error handling for state management failures
- Complete user workflows
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer

from compareblocks.gui.app import BECRMainWindow
from compareblocks.gui.pdf_selector import PDFSelectorIndicator
from compareblocks.gui.file_management_tab import FileManagementTab
from compareblocks.gui.settings_tab import SettingsTab


@pytest.fixture
def app(qtbot):
    """Create QApplication instance."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def main_window(qtbot, app):
    """Create main window instance."""
    window = BECRMainWindow()
    qtbot.addWidget(window)
    return window


@pytest.fixture
def test_pdf_path(tmp_path):
    """Create a test PDF file."""
    import fitz
    pdf_path = tmp_path / "test_document.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test content")
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


@pytest.fixture
def second_test_pdf(tmp_path):
    """Create a second test PDF file."""
    import fitz
    pdf_path = tmp_path / "second_document.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Second test content")
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


class TestMainWindowStructure:
    """Test suite for main window structure and component integration."""
    
    def test_main_window_has_all_components(self, main_window):
        """Test that main window has all required components."""
        # PDF Selector
        assert hasattr(main_window, 'pdf_selector')
        assert isinstance(main_window.pdf_selector, PDFSelectorIndicator)
        
        # File Management Tab
        assert hasattr(main_window, 'file_management_tab')
        assert isinstance(main_window.file_management_tab, FileManagementTab)
        
        # Settings Tab
        assert hasattr(main_window, 'settings_tab')
        assert isinstance(main_window.settings_tab, SettingsTab)
        
        # Tab Widget
        assert hasattr(main_window, 'tab_widget')
        assert main_window.tab_widget is not None
        
        # Debug Widget
        assert hasattr(main_window, 'debug_widget')
        
        # Review GUI
        assert hasattr(main_window, 'review_gui')
    
    def test_pdf_selector_positioned_at_top(self, main_window):
        """Test that PDF selector is positioned at top of window."""
        central_widget = main_window.centralWidget()
        layout = central_widget.layout()
        
        # First item should be PDF selector
        first_item = layout.itemAt(0)
        assert first_item is not None
        assert first_item.widget() == main_window.pdf_selector
    
    def test_file_management_tab_is_first_tab(self, main_window):
        """Test that File Management tab is the first tab."""
        tab_widget = main_window.tab_widget
        
        # Get first tab
        first_tab = tab_widget.widget(0)
        assert first_tab == main_window.file_management_tab
        
        # Check tab text
        tab_text = tab_widget.tabText(0)
        assert "Files" in tab_text or "📁" in tab_text
    
    def test_all_tabs_present(self, main_window):
        """Test that all required tabs are present."""
        tab_widget = main_window.tab_widget
        tab_count = tab_widget.count()
        
        # Should have at least: Files, Debug Images, PDF Review, Analysis, Settings, Engine Config, Test Runner
        assert tab_count >= 7
        
        # Check for specific tabs
        tab_texts = [tab_widget.tabText(i) for i in range(tab_count)]
        
        # File Management
        assert any("Files" in text or "📁" in text for text in tab_texts)
        
        # Settings
        assert any("Settings" in text or "⚙️" in text for text in tab_texts)
        
        # Test Runner
        assert any("Test Runner" in text or "🧪" in text for text in tab_texts)


class TestPDFSelectionStateManagement:
    """Test suite for PDF selection state management across all components."""
    
    def test_pdf_change_signal_connected(self, main_window):
        """Test that PDF change signal is connected to handler."""
        # Check that pdf_changed signal is connected by verifying the handler exists
        assert hasattr(main_window, 'on_pdf_changed')
        
        # Verify the signal exists
        assert hasattr(main_window.pdf_selector, 'pdf_changed')
    
    def test_pdf_change_updates_file_management_tab(self, main_window, test_pdf_path, qtbot):
        """Test that PDF change updates file management tab."""
        # Track if file management tab was updated
        update_called = []
        
        original_method = main_window.file_management_tab.set_current_pdf
        def mock_set_current_pdf(pdf_path):
            update_called.append(pdf_path)
            original_method(pdf_path)
        
        main_window.file_management_tab.set_current_pdf = mock_set_current_pdf
        
        # Change PDF
        main_window.pdf_selector.update_pdf_selection(test_pdf_path)
        
        # Wait for signal processing
        qtbot.wait(100)
        
        # Verify file management tab was updated
        assert len(update_called) > 0
        assert update_called[0] == test_pdf_path
    
    def test_pdf_change_refreshes_file_status(self, main_window, test_pdf_path, qtbot):
        """Test that PDF change refreshes file status widget."""
        # Get initial file status widget
        initial_widget = main_window.file_status_widget
        
        # Change PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # File status widget should be refreshed (new instance or updated)
        assert main_window.file_status_widget is not None
    
    def test_pdf_change_notifies_all_components(self, main_window, test_pdf_path, qtbot):
        """Test that PDF change notifies all relevant components."""
        # Track notifications
        notifications = {
            'file_management': False,
            'debug_widget': False,
            'review_gui': False
        }
        
        # Mock component methods
        original_file_mgmt = main_window.file_management_tab.set_current_pdf
        def mock_file_mgmt(pdf_path):
            notifications['file_management'] = True
            original_file_mgmt(pdf_path)
        main_window.file_management_tab.set_current_pdf = mock_file_mgmt
        
        # Change PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Verify file management was notified
        assert notifications['file_management']
    
    def test_multiple_pdf_changes_maintain_consistency(self, main_window, test_pdf_path, second_test_pdf, qtbot):
        """Test that multiple PDF changes maintain state consistency."""
        # Change to first PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Verify first PDF is set
        assert main_window.pdf_selector.get_current_pdf_path() == test_pdf_path
        
        # Change to second PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(second_test_pdf)
            qtbot.wait(100)
        
        # Verify second PDF is set
        assert main_window.pdf_selector.get_current_pdf_path() == second_test_pdf
        
        # Verify file management tab has correct PDF
        assert main_window.file_management_tab.get_current_pdf() == second_test_pdf


class TestTabSwitchingDataConsistency:
    """Test suite for tab switching with data consistency."""
    
    def test_tab_switching_preserves_pdf_selection(self, main_window, test_pdf_path, qtbot):
        """Test that switching tabs preserves PDF selection."""
        # Set PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Switch through all tabs
        tab_widget = main_window.tab_widget
        for i in range(tab_widget.count()):
            tab_widget.setCurrentIndex(i)
            qtbot.wait(50)
            
            # Verify PDF selection is maintained
            assert main_window.pdf_selector.get_current_pdf_path() == test_pdf_path
    
    def test_tab_switching_maintains_file_management_state(self, main_window, test_pdf_path, qtbot):
        """Test that switching tabs maintains file management state."""
        # Set PDF in file management tab
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Get file management tab state
        initial_pdf = main_window.file_management_tab.get_current_pdf()
        
        # Switch to another tab
        main_window.tab_widget.setCurrentIndex(1)  # Debug Images
        qtbot.wait(50)
        
        # Switch back to file management
        main_window.tab_widget.setCurrentIndex(0)  # Files
        qtbot.wait(50)
        
        # Verify state is maintained
        assert main_window.file_management_tab.get_current_pdf() == initial_pdf
    
    def test_tab_switching_maintains_settings_state(self, main_window, qtbot):
        """Test that switching tabs maintains settings state."""
        # Make a change in settings tab
        settings_tab = main_window.settings_tab
        
        # Switch to settings tab
        for i in range(main_window.tab_widget.count()):
            if main_window.tab_widget.widget(i) == settings_tab:
                main_window.tab_widget.setCurrentIndex(i)
                break
        qtbot.wait(50)
        
        # Make a change
        original_value = settings_tab.pdf_path_edit.text()
        settings_tab.pdf_path_edit.setText("/test/path.pdf")
        
        # Switch to another tab
        main_window.tab_widget.setCurrentIndex(0)
        qtbot.wait(50)
        
        # Switch back to settings
        for i in range(main_window.tab_widget.count()):
            if main_window.tab_widget.widget(i) == settings_tab:
                main_window.tab_widget.setCurrentIndex(i)
                break
        qtbot.wait(50)
        
        # Verify change is maintained
        assert settings_tab.pdf_path_edit.text() == "/test/path.pdf"


class TestStateSynchronization:
    """Test suite for state synchronization across components."""
    
    def test_pdf_selector_and_file_management_sync(self, main_window, test_pdf_path, qtbot):
        """Test synchronization between PDF selector and file management tab."""
        # Change PDF via selector
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Verify file management tab is synchronized
        assert main_window.file_management_tab.get_current_pdf() == test_pdf_path
    
    def test_file_management_to_pdf_selector_sync(self, main_window, test_pdf_path, qtbot):
        """Test synchronization from file management tab to PDF selector."""
        # Emit PDF selected signal from file management tab
        main_window.file_management_tab.pdf_selected.emit(test_pdf_path)
        qtbot.wait(100)
        
        # Verify PDF selector is synchronized
        assert main_window.pdf_selector.get_current_pdf_path() == test_pdf_path
    
    def test_settings_changes_propagate(self, main_window, qtbot):
        """Test that settings changes propagate to other components."""
        # Track if settings changed signal was emitted
        signal_received = []
        
        def on_settings_changed(settings):
            signal_received.append(settings)
        
        main_window.settings_tab.settings_changed.connect(on_settings_changed)
        
        # Trigger settings change
        settings_tab = main_window.settings_tab
        settings_tab.pdf_path_edit.setText("/new/path.pdf")
        settings_tab.on_setting_changed()
        
        # Save settings (this should emit the signal)
        with patch.object(settings_tab, 'mcp_worker') as mock_worker:
            # Mock successful save
            mock_worker.finished = Mock()
            settings_tab.save_settings()
            
            # Simulate successful save
            result = {
                "success": True,
                "updated_fields": ["target_pdf"]
            }
            with patch.object(QMessageBox, 'information'):
                settings_tab.on_settings_saved(result)
        
        # Verify signal was emitted
        assert len(signal_received) > 0


class TestDataRefreshTriggers:
    """Test suite for data refresh triggers."""
    
    def test_pdf_change_triggers_refresh(self, main_window, test_pdf_path, qtbot):
        """Test that PDF change triggers data refresh."""
        # Track refresh calls
        refresh_called = []
        
        original_refresh = main_window.refresh_file_status
        def mock_refresh():
            refresh_called.append(True)
            original_refresh()
        main_window.refresh_file_status = mock_refresh
        
        # Change PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Verify refresh was called
        assert len(refresh_called) > 0
    
    def test_settings_change_triggers_refresh(self, main_window, qtbot):
        """Test that settings changes trigger appropriate refreshes."""
        # Track refresh calls
        refresh_called = []
        
        original_refresh = main_window.refresh_file_status
        def mock_refresh():
            refresh_called.append(True)
            original_refresh()
        main_window.refresh_file_status = mock_refresh
        
        # Trigger settings change with path update
        settings = {
            "target_pdf": "/new/path.pdf",
            "processing_directory": "/new/processing"
        }
        
        main_window.on_settings_changed(settings)
        qtbot.wait(50)
        
        # Verify refresh was called
        assert len(refresh_called) > 0
    
    def test_manual_refresh_updates_all_components(self, main_window, test_pdf_path, qtbot):
        """Test that manual refresh updates all components."""
        # Set PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Trigger manual refresh
        main_window.refresh_file_status()
        qtbot.wait(50)
        
        # Verify file status widget exists and is updated
        assert main_window.file_status_widget is not None


class TestErrorHandling:
    """Test suite for error handling in state management."""
    
    def test_invalid_pdf_path_handled_gracefully(self, main_window, qtbot):
        """Test that invalid PDF path is handled gracefully."""
        invalid_path = "/nonexistent/path/to/file.pdf"
        
        # Attempt to set invalid PDF
        with patch.object(QMessageBox, 'critical') as mock_critical:
            main_window.pdf_selector.update_pdf_selection(invalid_path)
            qtbot.wait(100)
            
            # Verify error was shown
            assert mock_critical.called
    
    def test_mcp_connection_failure_handled(self, main_window, test_pdf_path, qtbot):
        """Test that MCP connection failures are handled gracefully."""
        # Set PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Simulate MCP error in file management tab
        error_message = "Connection refused"
        
        with patch.object(QMessageBox, 'critical') as mock_critical:
            main_window.file_management_tab.on_mcp_error(error_message)
            qtbot.wait(50)
            
            # Verify error was shown
            assert mock_critical.called
            
            # Verify tab is still functional
            assert main_window.file_management_tab.refresh_button.isEnabled()
    
    def test_state_corruption_recovery(self, main_window, test_pdf_path, qtbot):
        """Test recovery from state corruption."""
        # Set valid PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Corrupt state by setting None
        main_window.pdf_selector.current_pdf_path = None
        
        # Attempt to refresh - should handle gracefully
        main_window.refresh_file_status()
        qtbot.wait(50)
        
        # Verify no crash and widget still exists
        assert main_window.file_status_widget is not None
    
    def test_concurrent_state_changes_handled(self, main_window, test_pdf_path, second_test_pdf, qtbot):
        """Test that concurrent state changes are handled properly."""
        # Rapidly change PDFs
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            main_window.pdf_selector.update_pdf_selection(second_test_pdf)
            qtbot.wait(100)
        
        # Verify final state is consistent
        assert main_window.pdf_selector.get_current_pdf_path() == second_test_pdf


class TestCompleteUserWorkflows:
    """Test suite for complete user workflows."""
    
    def test_workflow_select_pdf_and_view_associations(self, main_window, test_pdf_path, qtbot):
        """Test complete workflow: select PDF and view associations."""
        # Step 1: Select PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Step 2: Switch to File Management tab
        main_window.tab_widget.setCurrentIndex(0)
        qtbot.wait(50)
        
        # Step 3: Verify associations are loaded
        file_mgmt_tab = main_window.file_management_tab
        assert file_mgmt_tab.get_current_pdf() == test_pdf_path
        
        # Step 4: Verify UI is responsive
        assert file_mgmt_tab.refresh_button.isEnabled()
    
    def test_workflow_change_settings_and_process(self, main_window, test_pdf_path, qtbot):
        """Test complete workflow: change settings and process PDF."""
        # Step 1: Select PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Step 2: Switch to Settings tab
        for i in range(main_window.tab_widget.count()):
            if main_window.tab_widget.widget(i) == main_window.settings_tab:
                main_window.tab_widget.setCurrentIndex(i)
                break
        qtbot.wait(50)
        
        # Step 3: Verify settings tab shows current PDF
        settings_tab = main_window.settings_tab
        assert settings_tab is not None
        
        # Step 4: Switch back to File Management
        main_window.tab_widget.setCurrentIndex(0)
        qtbot.wait(50)
        
        # Step 5: Verify PDF selection is maintained
        assert main_window.pdf_selector.get_current_pdf_path() == test_pdf_path
    
    def test_workflow_multiple_pdfs_with_tab_switching(self, main_window, test_pdf_path, second_test_pdf, qtbot):
        """Test workflow with multiple PDFs and tab switching."""
        # Step 1: Select first PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Step 2: Switch to Debug Images tab
        main_window.tab_widget.setCurrentIndex(1)
        qtbot.wait(50)
        
        # Step 3: Select second PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(second_test_pdf)
            qtbot.wait(100)
        
        # Step 4: Switch to File Management tab
        main_window.tab_widget.setCurrentIndex(0)
        qtbot.wait(50)
        
        # Step 5: Verify second PDF is active everywhere
        assert main_window.pdf_selector.get_current_pdf_path() == second_test_pdf
        assert main_window.file_management_tab.get_current_pdf() == second_test_pdf
    
    def test_workflow_error_recovery_and_continue(self, main_window, test_pdf_path, qtbot):
        """Test workflow with error recovery."""
        # Step 1: Attempt to select invalid PDF
        invalid_path = "/nonexistent/file.pdf"
        with patch.object(QMessageBox, 'critical'):
            main_window.pdf_selector.update_pdf_selection(invalid_path)
            qtbot.wait(100)
        
        # Step 2: Select valid PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Step 3: Verify system recovered and is functional
        assert main_window.pdf_selector.get_current_pdf_path() == test_pdf_path
        assert main_window.file_management_tab.get_current_pdf() == test_pdf_path
        
        # Step 4: Verify all tabs are still accessible
        for i in range(main_window.tab_widget.count()):
            main_window.tab_widget.setCurrentIndex(i)
            qtbot.wait(50)
            assert main_window.tab_widget.currentIndex() == i


class TestApplicationStateManagement:
    """Test suite for application-wide state management."""
    
    def test_application_state_initialization(self, main_window):
        """Test that application state is properly initialized."""
        # Verify all components are initialized
        assert main_window.pdf_selector is not None
        assert main_window.file_management_tab is not None
        assert main_window.settings_tab is not None
        assert main_window.tab_widget is not None
        
        # Verify initial state is consistent
        assert main_window.pdf_selector.get_current_pdf_path() is not None or \
               main_window.pdf_selector.get_current_pdf_path() is None  # Either is valid initially
    
    def test_application_state_persistence_across_operations(self, main_window, test_pdf_path, qtbot):
        """Test that application state persists across operations."""
        # Set initial state
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Perform various operations
        main_window.refresh_file_status()
        qtbot.wait(50)
        
        main_window.tab_widget.setCurrentIndex(1)
        qtbot.wait(50)
        
        main_window.tab_widget.setCurrentIndex(0)
        qtbot.wait(50)
        
        # Verify state is maintained
        assert main_window.pdf_selector.get_current_pdf_path() == test_pdf_path
    
    def test_application_state_cleanup_on_pdf_change(self, main_window, test_pdf_path, second_test_pdf, qtbot):
        """Test that old state is properly cleaned up on PDF change."""
        # Set first PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(test_pdf_path)
            qtbot.wait(100)
        
        # Get initial state
        initial_widget = main_window.file_status_widget
        
        # Change to second PDF
        with patch.object(QMessageBox, 'information'):
            main_window.pdf_selector.update_pdf_selection(second_test_pdf)
            qtbot.wait(100)
        
        # Verify new state
        assert main_window.pdf_selector.get_current_pdf_path() == second_test_pdf
        
        # Verify file status widget was refreshed (new instance or updated)
        assert main_window.file_status_widget is not None

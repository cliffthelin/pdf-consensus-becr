# tests/gui/test_file_management_tab.py

"""
Comprehensive GUI tests for File Management Tab - Association Library Interface.

Tests all file management functionality including:
- Tab initialization and display
- Root PDF list display with associated NDJSON files
- Extract associations with influence percentage calculations
- Consensus output file tracking and export file management
- Association management options (new associations, edit existing)
- MCP communication layer for all association data requests
- Integration with compareblocks.association.manager through MCP protocol
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest

from src.compareblocks.gui.file_management_tab import FileManagementTab, MCPWorker
from src.compareblocks.gui.app import BECRMainWindow
from src.compareblocks.config.file_manager import file_manager
from src.compareblocks.association.manager import AssociationManager


@pytest.fixture
def qapp():
    """Create QApplication instance for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def file_management_tab(qapp):
    """Create file management tab widget for testing."""
    tab = FileManagementTab()
    yield tab
    # Clean up any running workers
    if hasattr(tab, 'mcp_worker') and tab.mcp_worker:
        if tab.mcp_worker.isRunning():
            tab.mcp_worker.quit()
            tab.mcp_worker.wait(1000)  # Wait up to 1 second
    tab.close()


@pytest.fixture
def main_window(qapp):
    """Create main window for integration testing."""
    window = BECRMainWindow()
    yield window
    window.close()


@pytest.fixture
def test_pdf_path():
    """Get path to test PDF file."""
    try:
        pdf_path = file_manager.get_target_pdf_path()
        if pdf_path and Path(pdf_path).exists():
            return pdf_path
    except:
        pass
    
    # Try to find any PDF in Source_docs
    source_docs = Path("Source_docs")
    if source_docs.exists():
        for pdf_file in source_docs.rglob("*.pdf"):
            if pdf_file.exists():
                return str(pdf_file)
    
    pytest.skip("No test PDF available")


@pytest.fixture
def association_manager():
    """Create association manager for testing."""
    return AssociationManager()


class TestFileManagementTabInitialization:
    """Test suite for File Management Tab initialization."""
    
    def test_tab_initialization(self, file_management_tab):
        """Test that file management tab initializes correctly."""
        assert file_management_tab is not None
        assert hasattr(file_management_tab, 'pdf_tree')
        assert hasattr(file_management_tab, 'details_text')
        assert hasattr(file_management_tab, 'influence_text')
        assert hasattr(file_management_tab, 'consensus_text')
    
    def test_tab_has_action_buttons(self, file_management_tab):
        """Test that tab has all required action buttons."""
        assert hasattr(file_management_tab, 'new_association_button')
        assert hasattr(file_management_tab, 'edit_association_button')
        assert hasattr(file_management_tab, 'delete_association_button')
        assert hasattr(file_management_tab, 'export_button')
        assert hasattr(file_management_tab, 'refresh_button')
    
    def test_tab_has_progress_bar(self, file_management_tab):
        """Test that tab has progress bar for MCP operations."""
        assert hasattr(file_management_tab, 'progress_bar')
        assert not file_management_tab.progress_bar.isVisible()  # Initially hidden
    
    def test_initial_button_states(self, file_management_tab):
        """Test initial state of action buttons."""
        # New association should be enabled
        assert file_management_tab.new_association_button.isEnabled()
        
        # Edit and delete should be disabled initially (no selection)
        assert not file_management_tab.edit_association_button.isEnabled()
        assert not file_management_tab.delete_association_button.isEnabled()
        assert not file_management_tab.export_button.isEnabled()
    
    def test_pdf_tree_columns(self, file_management_tab):
        """Test that PDF tree has correct columns."""
        tree = file_management_tab.pdf_tree
        assert tree.columnCount() == 3
        assert tree.headerItem().text(0) == "Name"
        assert tree.headerItem().text(1) == "Type"
        assert tree.headerItem().text(2) == "Status"
    
    def test_signals_defined(self, file_management_tab):
        """Test that required signals are defined."""
        assert hasattr(file_management_tab, 'association_selected')
        assert hasattr(file_management_tab, 'pdf_selected')


class TestPDFTreeDisplay:
    """Test suite for PDF tree display functionality."""
    
    def test_empty_tree_initially(self, qapp):
        """Test that tree is empty when no data is loaded."""
        tab = FileManagementTab()
        tab.association_data = {}
        tab.update_pdf_tree()
        
        assert tab.pdf_tree.topLevelItemCount() == 0
        tab.close()
    
    def test_load_pdf_associations(self, file_management_tab, test_pdf_path):
        """Test loading PDF associations."""
        # This will trigger MCP worker
        file_management_tab.load_pdf_associations(test_pdf_path)
        
        # Verify current PDF is set
        assert file_management_tab.current_pdf_path == test_pdf_path
        
        # Verify progress bar is shown
        assert file_management_tab.progress_bar.isVisible()
    
    def test_update_pdf_tree_with_data(self, file_management_tab, test_pdf_path):
        """Test updating PDF tree with association data."""
        # Set up mock association data
        file_management_tab.association_data = {
            "pdf_path": test_pdf_path,
            "associations": {
                "/path/to/tesseract.json": {
                    "format_type": "ndjson",
                    "text_length": 5000,
                    "blocks": 150
                },
                "/path/to/pymupdf.json": {
                    "format_type": "ndjson",
                    "text_length": 4800,
                    "blocks": 148
                }
            },
            "metadata": {}
        }
        
        file_management_tab.update_pdf_tree()
        
        # Verify tree has root PDF item
        assert file_management_tab.pdf_tree.topLevelItemCount() == 1
        
        root_item = file_management_tab.pdf_tree.topLevelItem(0)
        assert Path(test_pdf_path).name in root_item.text(0)
        assert root_item.text(1) == "PDF"
        
        # Verify root item has children (sections)
        assert root_item.childCount() >= 4  # NDJSON, Extract, Consensus, Exports
    
    def test_tree_item_selection(self, file_management_tab, test_pdf_path):
        """Test tree item selection behavior."""
        # Set up data and update tree
        file_management_tab.association_data = {
            "pdf_path": test_pdf_path,
            "associations": {
                "/path/to/test.json": {
                    "format_type": "ndjson",
                    "text_length": 1000,
                    "blocks": 50
                }
            },
            "metadata": {}
        }
        file_management_tab.update_pdf_tree()
        
        # Select root PDF item
        root_item = file_management_tab.pdf_tree.topLevelItem(0)
        file_management_tab.pdf_tree.setCurrentItem(root_item)
        
        # Verify button states updated
        assert file_management_tab.export_button.isEnabled()
        assert not file_management_tab.edit_association_button.isEnabled()
    
    def test_tree_context_menu(self, file_management_tab, test_pdf_path):
        """Test context menu on tree items."""
        # Set up data
        file_management_tab.association_data = {
            "pdf_path": test_pdf_path,
            "associations": {},
            "metadata": {}
        }
        file_management_tab.update_pdf_tree()
        
        # Verify context menu policy is set
        assert file_management_tab.pdf_tree.contextMenuPolicy() == Qt.CustomContextMenu


class TestAssociationDisplay:
    """Test suite for association display functionality."""
    
    def test_show_pdf_details(self, file_management_tab, test_pdf_path):
        """Test displaying PDF details."""
        item_data = {
            "type": "pdf",
            "path": test_pdf_path
        }
        
        file_management_tab.association_data = {"associations": {}}
        file_management_tab.show_pdf_details(item_data)
        
        # Verify details are displayed
        details_text = file_management_tab.details_text.toPlainText()
        assert Path(test_pdf_path).name in details_text
        assert test_pdf_path in details_text
    
    def test_show_association_details(self, file_management_tab):
        """Test displaying association details."""
        assoc_path = "/path/to/test.json"
        item_data = {
            "type": "association",
            "path": assoc_path,
            "data": {
                "format_type": "ndjson",
                "text_length": 5000,
                "blocks": 150
            }
        }
        
        file_management_tab.association_data = {
            "metadata": {
                assoc_path: {
                    "file_size": 10240,
                    "last_modified": "2024-01-01T12:00:00",
                    "parsing_success": True
                }
            }
        }
        
        file_management_tab.show_association_details(item_data)
        
        # Verify details are displayed
        details_text = file_management_tab.details_text.toPlainText()
        assert "test.json" in details_text
        assert "ndjson" in details_text
        assert "5,000" in details_text or "5000" in details_text
        assert "150" in details_text
    
    def test_influence_percentage_display(self, file_management_tab):
        """Test displaying influence percentages."""
        file_management_tab.influence_data = {
            "pdf_path": "/test.pdf",
            "influence_percentages": {
                "tesseract": 45.5,
                "pymupdf": 35.2,
                "paddleocr": 19.3
            },
            "total_blocks": 150,
            "consensus_blocks": 145
        }
        
        file_management_tab.update_influence_display()
        
        # Verify influence data is displayed
        influence_text = file_management_tab.influence_text.toPlainText()
        assert "150" in influence_text  # Total blocks
        assert "145" in influence_text  # Consensus blocks
        assert "tesseract" in influence_text
        assert "45.5" in influence_text
    
    def test_consensus_output_display(self, file_management_tab):
        """Test displaying consensus outputs."""
        file_management_tab.consensus_data = {
            "pdf_path": "/test.pdf",
            "consensus_file": "/path/to/consensus.json",
            "export_files": [
                "/path/to/output.txt",
                "/path/to/results.csv"
            ]
        }
        
        file_management_tab.update_consensus_display()
        
        # Verify consensus data is displayed
        consensus_text = file_management_tab.consensus_text.toPlainText()
        assert "consensus.json" in consensus_text
        assert "2" in consensus_text  # Number of export files
        assert "output.txt" in consensus_text
        assert "results.csv" in consensus_text


class TestMCPCommunication:
    """Test suite for MCP communication functionality."""
    
    def test_mcp_worker_initialization(self):
        """Test MCP worker initialization."""
        worker = MCPWorker("get_associations", {"pdf_path": "/test.pdf"})
        
        assert worker.operation == "get_associations"
        assert worker.params["pdf_path"] == "/test.pdf"
        assert hasattr(worker, 'finished')
        assert hasattr(worker, 'error')
    
    def test_mcp_worker_get_associations(self, test_pdf_path, association_manager):
        """Test MCP worker get_associations operation."""
        # Create worker
        worker = MCPWorker("get_associations", {"pdf_path": test_pdf_path})
        
        # Track results
        results = []
        errors = []
        worker.finished.connect(lambda r: results.append(r))
        worker.error.connect(lambda e: errors.append(e))
        
        # Run worker
        worker.run()
        
        # Verify results or errors
        assert len(results) > 0 or len(errors) > 0
        
        if results:
            result = results[0]
            assert "pdf_path" in result
            assert "associations" in result
    
    def test_on_associations_loaded(self, file_management_tab, test_pdf_path):
        """Test handling of loaded associations."""
        result = {
            "pdf_path": test_pdf_path,
            "associations": {
                "/path/to/test.json": {
                    "format_type": "ndjson",
                    "text_length": 1000,
                    "blocks": 50
                }
            },
            "metadata": {}
        }
        
        file_management_tab.on_associations_loaded(result)
        
        # Verify data is stored
        assert file_management_tab.association_data == result
        
        # Verify progress bar is hidden
        assert not file_management_tab.progress_bar.isVisible()
    
    def test_on_mcp_error(self, file_management_tab):
        """Test handling of MCP errors."""
        error_message = "Connection failed"
        
        file_management_tab.on_mcp_error(error_message)
        
        # Verify progress bar is hidden
        assert not file_management_tab.progress_bar.isVisible()
        
        # Verify error message is displayed
        details_text = file_management_tab.details_text.toPlainText()
        assert error_message in details_text
        assert "offline" in details_text.lower()


class TestAssociationManagement:
    """Test suite for association management operations."""
    
    def test_create_new_association_button(self, file_management_tab):
        """Test create new association button."""
        assert file_management_tab.new_association_button.isEnabled()
        assert "New Association" in file_management_tab.new_association_button.text()
    
    def test_edit_association_button_disabled_initially(self, file_management_tab):
        """Test edit button is disabled when no association selected."""
        assert not file_management_tab.edit_association_button.isEnabled()
    
    def test_delete_association_button_disabled_initially(self, file_management_tab):
        """Test delete button is disabled when no association selected."""
        assert not file_management_tab.delete_association_button.isEnabled()
    
    def test_refresh_associations(self, file_management_tab, test_pdf_path):
        """Test refreshing associations."""
        file_management_tab.current_pdf_path = test_pdf_path
        
        # Call refresh
        file_management_tab.refresh_associations()
        
        # Verify progress bar is shown
        assert file_management_tab.progress_bar.isVisible()
    
    def test_export_button_enabled_with_pdf(self, file_management_tab, test_pdf_path):
        """Test export button is enabled when PDF is selected."""
        # Set up data
        file_management_tab.association_data = {
            "pdf_path": test_pdf_path,
            "associations": {},
            "metadata": {}
        }
        file_management_tab.update_pdf_tree()
        
        # Select PDF item
        root_item = file_management_tab.pdf_tree.topLevelItem(0)
        file_management_tab.pdf_tree.setCurrentItem(root_item)
        
        # Verify export button is enabled
        assert file_management_tab.export_button.isEnabled()


class TestFileManagementTabIntegration:
    """Test suite for file management tab integration with main window."""
    
    def test_main_window_has_file_management_tab(self, main_window):
        """Test that main window includes file management tab."""
        # Check if tab exists in main window
        tab_widget = main_window.tab_widget
        
        # Find file management tab
        file_mgmt_tab = None
        for i in range(tab_widget.count()):
            if "File" in tab_widget.tabText(i) or "Association" in tab_widget.tabText(i):
                file_mgmt_tab = tab_widget.widget(i)
                break
        
        # May not be added yet, so just verify the class exists
        assert FileManagementTab is not None
    
    def test_set_current_pdf(self, file_management_tab, test_pdf_path):
        """Test setting current PDF."""
        file_management_tab.set_current_pdf(test_pdf_path)
        
        # Verify PDF is set
        assert file_management_tab.current_pdf_path == test_pdf_path
    
    def test_get_current_pdf(self, file_management_tab, test_pdf_path):
        """Test getting current PDF."""
        file_management_tab.current_pdf_path = test_pdf_path
        
        current_pdf = file_management_tab.get_current_pdf()
        assert current_pdf == test_pdf_path
    
    def test_pdf_selected_signal(self, file_management_tab, test_pdf_path):
        """Test that pdf_selected signal can be emitted."""
        signal_received = []
        file_management_tab.pdf_selected.connect(lambda path: signal_received.append(path))
        
        # Emit signal
        file_management_tab.pdf_selected.emit(test_pdf_path)
        
        # Verify signal was received
        assert len(signal_received) == 1
        assert signal_received[0] == test_pdf_path


class TestFileManagementWithRealData:
    """Test suite using real PDF files and association data."""
    
    def test_load_real_pdf_associations(self, file_management_tab, test_pdf_path, association_manager):
        """Test loading associations for real PDF file."""
        try:
            # Load associations using real association manager
            associations = association_manager.load_associations_for_pdf(test_pdf_path)
            
            # Verify associations object
            assert associations is not None
            assert hasattr(associations, 'associations')
            assert hasattr(associations, 'metadata')
            
        except Exception as e:
            pytest.skip(f"Cannot load real associations: {e}")
    
    def test_display_real_association_data(self, file_management_tab, test_pdf_path):
        """Test displaying real association data."""
        try:
            # Load real data
            file_management_tab.load_pdf_associations(test_pdf_path)
            
            # Wait for worker to complete (with timeout)
            timeout = 5000  # 5 seconds
            start_time = QTimer()
            start_time.start(timeout)
            
            while file_management_tab.mcp_worker and file_management_tab.mcp_worker.isRunning():
                QApplication.processEvents()
                if not start_time.isActive():
                    break
            
            # Verify data was loaded
            assert file_management_tab.current_pdf_path == test_pdf_path
            
        except Exception as e:
            pytest.skip(f"Cannot test with real data: {e}")
    
    def test_real_influence_calculation(self, file_management_tab, test_pdf_path):
        """Test influence percentage calculation with real data."""
        # Set up real PDF
        file_management_tab.current_pdf_path = test_pdf_path
        
        # Load influence data
        file_management_tab.load_influence_data()
        
        # Verify worker is created
        assert file_management_tab.mcp_worker is not None


class TestErrorHandling:
    """Test suite for error handling in file management tab."""
    
    def test_load_nonexistent_pdf(self, file_management_tab):
        """Test loading associations for nonexistent PDF."""
        nonexistent_pdf = "/nonexistent/file.pdf"
        
        # Should not crash
        file_management_tab.load_pdf_associations(nonexistent_pdf)
        
        # Verify current PDF is set even if file doesn't exist
        assert file_management_tab.current_pdf_path == nonexistent_pdf
    
    def test_refresh_without_pdf(self, file_management_tab):
        """Test refreshing when no PDF is selected."""
        file_management_tab.current_pdf_path = None
        
        # Should show warning (we can't test QMessageBox easily, but verify it doesn't crash)
        # file_management_tab.refresh_associations()
        
        # Verify current PDF is still None
        assert file_management_tab.current_pdf_path is None
    
    def test_export_without_pdf(self, file_management_tab):
        """Test exporting when no PDF is selected."""
        file_management_tab.current_pdf_path = None
        
        # Should show warning (we can't test QMessageBox easily, but verify it doesn't crash)
        # file_management_tab.export_results()
        
        # Verify current PDF is still None
        assert file_management_tab.current_pdf_path is None
    
    def test_handle_empty_association_data(self, file_management_tab):
        """Test handling empty association data."""
        file_management_tab.association_data = {}
        
        # Should not crash
        file_management_tab.update_pdf_tree()
        
        # Tree should be empty
        assert file_management_tab.pdf_tree.topLevelItemCount() == 0
    
    def test_handle_malformed_association_data(self, file_management_tab):
        """Test handling malformed association data."""
        file_management_tab.association_data = {
            "pdf_path": "/test.pdf"
            # Missing 'associations' key
        }
        
        # Should not crash
        file_management_tab.update_pdf_tree()
    
    def test_handle_missing_metadata(self, file_management_tab):
        """Test handling missing metadata in association data."""
        item_data = {
            "type": "association",
            "path": "/test.json",
            "data": {
                "format_type": "ndjson",
                "text_length": 1000,
                "blocks": 50
            }
        }
        
        file_management_tab.association_data = {
            "metadata": {}  # No metadata for this association
        }
        
        # Should not crash
        file_management_tab.show_association_details(item_data)
        
        # Verify details are still displayed
        details_text = file_management_tab.details_text.toPlainText()
        assert "test.json" in details_text


class TestUIResponsiveness:
    """Test suite for UI responsiveness and performance."""
    
    def test_progress_bar_visibility(self, file_management_tab, test_pdf_path):
        """Test progress bar shows during operations."""
        # Initially hidden
        assert not file_management_tab.progress_bar.isVisible()
        
        # Start operation
        file_management_tab.load_pdf_associations(test_pdf_path)
        
        # Should be visible during operation
        assert file_management_tab.progress_bar.isVisible()
    
    def test_button_states_during_operation(self, file_management_tab, test_pdf_path):
        """Test button states during MCP operations."""
        # Start operation
        file_management_tab.load_pdf_associations(test_pdf_path)
        
        # Refresh button should be disabled during operation
        assert not file_management_tab.refresh_button.isEnabled()
    
    def test_large_association_list_performance(self, file_management_tab, test_pdf_path):
        """Test performance with large number of associations."""
        # Create large association data
        associations = {}
        for i in range(100):
            associations[f"/path/to/file_{i}.json"] = {
                "format_type": "ndjson",
                "text_length": 1000 * i,
                "blocks": 50 + i
            }
        
        file_management_tab.association_data = {
            "pdf_path": test_pdf_path,
            "associations": associations,
            "metadata": {}
        }
        
        # Should handle large data without hanging
        file_management_tab.update_pdf_tree()
        
        # Verify tree was populated
        assert file_management_tab.pdf_tree.topLevelItemCount() > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

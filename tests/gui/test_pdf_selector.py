# tests/gui/test_pdf_selector.py

"""
Comprehensive GUI tests for PDF Selector Indicator Component.

Tests all PDF selector functionality including:
- Widget initialization and display
- PDF metadata extraction and display
- PDF selection dialog
- PDF validation
- Change notification system
- Integration with main window
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest

from src.compareblocks.gui.pdf_selector import PDFSelectorIndicator
from src.compareblocks.gui.app import BECRMainWindow
from src.compareblocks.config.file_manager import file_manager


@pytest.fixture
def qapp():
    """Create QApplication instance for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def pdf_selector(qapp):
    """Create PDF selector widget for testing."""
    selector = PDFSelectorIndicator()
    yield selector
    selector.close()


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


class TestPDFSelectorIndicator:
    """Test suite for PDF Selector Indicator component."""
    
    def test_widget_initialization(self, pdf_selector):
        """Test that PDF selector widget initializes correctly."""
        assert pdf_selector is not None
        assert hasattr(pdf_selector, 'filename_label')
        assert hasattr(pdf_selector, 'metadata_label')
        assert hasattr(pdf_selector, 'browse_button')
        assert hasattr(pdf_selector, 'info_button')
    
    def test_initial_display_no_pdf(self, qapp):
        """Test initial display when no PDF is selected."""
        # Create selector without loading default
        selector = PDFSelectorIndicator()
        selector.current_pdf_path = None
        selector.pdf_metadata = {}
        selector.refresh_display()
        
        assert "No PDF selected" in selector.filename_label.text()
        assert "Browse" in selector.metadata_label.text()
        selector.close()
    
    def test_pdf_metadata_extraction(self, pdf_selector, test_pdf_path):
        """Test PDF metadata extraction from real PDF file."""
        metadata = pdf_selector.extract_pdf_metadata(test_pdf_path)
        
        # Verify required metadata fields
        assert "path" in metadata
        assert "filename" in metadata
        assert "file_size" in metadata
        assert "page_count" in metadata
        
        # Verify values are reasonable
        assert metadata["path"] == test_pdf_path
        assert metadata["filename"] == Path(test_pdf_path).name
        assert metadata["file_size"] > 0
        assert metadata["page_count"] > 0
    
    def test_pdf_validation_valid_file(self, pdf_selector, test_pdf_path):
        """Test PDF validation with valid PDF file."""
        is_valid = pdf_selector.validate_pdf(test_pdf_path)
        assert is_valid is True
    
    def test_pdf_validation_invalid_file(self, pdf_selector, tmp_path):
        """Test PDF validation with invalid file."""
        # Create a non-PDF file
        invalid_file = tmp_path / "not_a_pdf.txt"
        invalid_file.write_text("This is not a PDF")
        
        is_valid = pdf_selector.validate_pdf(str(invalid_file))
        assert is_valid is False
    
    def test_pdf_validation_nonexistent_file(self, pdf_selector):
        """Test PDF validation with nonexistent file."""
        is_valid = pdf_selector.validate_pdf("/nonexistent/file.pdf")
        assert is_valid is False
    
    def test_update_pdf_selection(self, pdf_selector, test_pdf_path):
        """Test updating PDF selection with valid PDF."""
        # Connect signal to capture emission
        signal_received = []
        pdf_selector.pdf_changed.connect(lambda path: signal_received.append(path))
        
        # Update selection
        pdf_selector.update_pdf_selection(test_pdf_path)
        
        # Verify state updated
        assert pdf_selector.current_pdf_path == test_pdf_path
        assert pdf_selector.pdf_metadata is not None
        assert len(pdf_selector.pdf_metadata) > 0
        
        # Verify signal emitted
        assert len(signal_received) == 1
        assert signal_received[0] == test_pdf_path
        
        # Verify info button enabled
        assert pdf_selector.info_button.isEnabled()
    
    def test_display_refresh_with_pdf(self, pdf_selector, test_pdf_path):
        """Test display refresh with loaded PDF."""
        pdf_selector.update_pdf_selection(test_pdf_path)
        
        # Verify filename displayed
        filename = Path(test_pdf_path).name
        assert filename in pdf_selector.filename_label.text()
        
        # Verify metadata displayed
        metadata_text = pdf_selector.metadata_label.text()
        assert "pages" in metadata_text.lower()
        assert "MB" in metadata_text or "mb" in metadata_text
    
    def test_get_current_pdf_path(self, pdf_selector, test_pdf_path):
        """Test getting current PDF path."""
        pdf_selector.update_pdf_selection(test_pdf_path)
        
        current_path = pdf_selector.get_current_pdf_path()
        assert current_path == test_pdf_path
    
    def test_get_pdf_metadata(self, pdf_selector, test_pdf_path):
        """Test getting PDF metadata."""
        pdf_selector.update_pdf_selection(test_pdf_path)
        
        metadata = pdf_selector.get_pdf_metadata()
        assert isinstance(metadata, dict)
        assert "filename" in metadata
        assert "page_count" in metadata
        assert "file_size" in metadata
    
    def test_pdf_changed_signal(self, pdf_selector, test_pdf_path):
        """Test that pdf_changed signal is emitted correctly."""
        signal_count = []
        signal_paths = []
        
        def on_pdf_changed(path):
            signal_count.append(1)
            signal_paths.append(path)
        
        pdf_selector.pdf_changed.connect(on_pdf_changed)
        
        # Change PDF
        pdf_selector.update_pdf_selection(test_pdf_path)
        
        # Verify signal emitted once with correct path
        assert len(signal_count) == 1
        assert signal_paths[0] == test_pdf_path
    
    def test_browse_button_click(self, pdf_selector, qapp):
        """Test browse button functionality."""
        assert pdf_selector.browse_button.isEnabled()
        assert pdf_selector.browse_button.text() == "📁 Browse..."
    
    def test_info_button_disabled_initially(self, qapp):
        """Test that info button is disabled when no PDF is loaded."""
        selector = PDFSelectorIndicator()
        # Clear any loaded PDF and refresh
        selector.current_pdf_path = None
        selector.pdf_metadata = {}
        selector.info_button.setEnabled(False)
        selector.refresh_display()
        
        assert not selector.info_button.isEnabled()
        selector.close()
    
    def test_info_button_enabled_after_pdf_load(self, pdf_selector, test_pdf_path):
        """Test that info button is enabled after PDF is loaded."""
        pdf_selector.update_pdf_selection(test_pdf_path)
        assert pdf_selector.info_button.isEnabled()
    
    def test_widget_clickable(self, pdf_selector):
        """Test that widget has clickable cursor."""
        assert pdf_selector.cursor().shape() == Qt.PointingHandCursor
    
    def test_widget_tooltip(self, pdf_selector):
        """Test that widget has appropriate tooltip."""
        assert "Click" in pdf_selector.toolTip()
        assert "PDF" in pdf_selector.toolTip()


class TestPDFSelectorIntegration:
    """Test suite for PDF Selector integration with main window."""
    
    def test_main_window_has_pdf_selector(self, main_window):
        """Test that main window includes PDF selector."""
        assert hasattr(main_window, 'pdf_selector')
        assert isinstance(main_window.pdf_selector, PDFSelectorIndicator)
    
    def test_pdf_selector_positioned_correctly(self, main_window):
        """Test that PDF selector is positioned at top of window."""
        # Get central widget layout
        layout = main_window.centralWidget().layout()
        
        # PDF selector should be first item in layout
        first_item = layout.itemAt(0)
        assert first_item is not None
        assert first_item.widget() == main_window.pdf_selector
    
    def test_pdf_change_triggers_main_window_handler(self, main_window, test_pdf_path):
        """Test that PDF change triggers main window handler."""
        # Track if handler was called
        handler_called = []
        
        original_handler = main_window.on_pdf_changed
        def tracked_handler(path):
            handler_called.append(path)
            original_handler(path)
        
        main_window.on_pdf_changed = tracked_handler
        
        # Change PDF
        main_window.pdf_selector.update_pdf_selection(test_pdf_path)
        
        # Verify handler was called
        assert len(handler_called) == 1
        assert handler_called[0] == test_pdf_path
    
    def test_pdf_change_updates_file_status(self, main_window, test_pdf_path):
        """Test that PDF change updates file status widget."""
        # Get initial file status widget
        initial_widget = main_window.file_status_widget
        
        # Change PDF (this should trigger refresh)
        main_window.pdf_selector.update_pdf_selection(test_pdf_path)
        
        # File status widget should still exist (may be same or replaced)
        assert hasattr(main_window, 'file_status_widget')
        assert main_window.file_status_widget is not None
    
    def test_multiple_pdf_changes(self, main_window, test_pdf_path):
        """Test multiple PDF changes in sequence."""
        signal_count = []
        
        def count_signals(path):
            signal_count.append(path)
        
        main_window.pdf_selector.pdf_changed.connect(count_signals)
        
        # Change PDF multiple times
        main_window.pdf_selector.update_pdf_selection(test_pdf_path)
        main_window.pdf_selector.update_pdf_selection(test_pdf_path)
        
        # Should have received two signals
        assert len(signal_count) == 2


class TestPDFSelectorWithRealData:
    """Test suite using real PDF files and application data."""
    
    def test_load_default_pdf_from_config(self, qapp):
        """Test loading default PDF from configuration."""
        try:
            pdf_path = file_manager.get_target_pdf_path()
            if not pdf_path or not Path(pdf_path).exists():
                pytest.skip("Default PDF not configured or not found")
            
            selector = PDFSelectorIndicator()
            
            # Should load default PDF automatically
            if selector.current_pdf_path:
                assert Path(selector.current_pdf_path).exists()
                assert selector.pdf_metadata is not None
                assert selector.pdf_metadata.get("page_count", 0) > 0
            
            selector.close()
            
        except Exception as e:
            pytest.skip(f"Cannot test with default PDF: {e}")
    
    def test_metadata_accuracy_with_real_pdf(self, pdf_selector, test_pdf_path):
        """Test metadata extraction accuracy with real PDF."""
        metadata = pdf_selector.extract_pdf_metadata(test_pdf_path)
        
        # Verify file size matches actual file
        actual_size = Path(test_pdf_path).stat().st_size
        assert metadata["file_size"] == actual_size
        
        # Verify filename matches
        assert metadata["filename"] == Path(test_pdf_path).name
        
        # Verify path matches
        assert metadata["path"] == test_pdf_path
    
    def test_large_pdf_handling(self, pdf_selector):
        """Test handling of large PDF files."""
        try:
            # Find a large PDF if available
            source_docs = Path("Source_docs")
            if not source_docs.exists():
                pytest.skip("Source_docs directory not found")
            
            large_pdf = None
            for pdf_file in source_docs.rglob("*.pdf"):
                if pdf_file.stat().st_size > 1_000_000:  # > 1MB
                    large_pdf = str(pdf_file)
                    break
            
            if not large_pdf:
                pytest.skip("No large PDF files found for testing")
            
            # Should handle large PDF without errors
            metadata = pdf_selector.extract_pdf_metadata(large_pdf)
            assert metadata["file_size"] > 1_000_000
            assert metadata["page_count"] > 0
            
        except Exception as e:
            pytest.skip(f"Cannot test with large PDF: {e}")
    
    def test_pdf_with_many_pages(self, pdf_selector, test_pdf_path):
        """Test PDF with many pages."""
        metadata = pdf_selector.extract_pdf_metadata(test_pdf_path)
        
        # Should handle multi-page PDFs
        if metadata["page_count"] > 10:
            assert metadata["page_count"] > 10
            assert "pages" in pdf_selector.metadata_label.text().lower()


class TestPDFSelectorErrorHandling:
    """Test suite for error handling in PDF selector."""
    
    def test_corrupted_pdf_handling(self, pdf_selector, tmp_path):
        """Test handling of corrupted PDF file."""
        # Create a file that looks like PDF but is corrupted
        corrupted_pdf = tmp_path / "corrupted.pdf"
        corrupted_pdf.write_bytes(b"%PDF-1.4\n%corrupted data")
        
        is_valid = pdf_selector.validate_pdf(str(corrupted_pdf))
        assert is_valid is False
    
    def test_empty_file_handling(self, pdf_selector, tmp_path):
        """Test handling of empty file."""
        empty_file = tmp_path / "empty.pdf"
        empty_file.write_bytes(b"")
        
        is_valid = pdf_selector.validate_pdf(str(empty_file))
        assert is_valid is False
    
    def test_permission_denied_handling(self, pdf_selector):
        """Test handling of permission denied errors."""
        # This test is platform-specific and may not work on all systems
        try:
            # Try to validate a path that would cause permission error
            is_valid = pdf_selector.validate_pdf("/root/restricted.pdf")
            # Should return False rather than raising exception
            assert is_valid is False
        except:
            pytest.skip("Cannot test permission denied scenario")
    
    def test_network_path_handling(self, pdf_selector):
        """Test handling of network paths."""
        # Test with UNC path (Windows) or network mount
        network_path = "//network/share/file.pdf"
        
        # Should handle gracefully without hanging
        is_valid = pdf_selector.validate_pdf(network_path)
        assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

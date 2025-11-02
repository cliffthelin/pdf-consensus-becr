# tests/integration/test_settings_tab_integration.py
"""
Integration tests for Settings Tab within the main application.

Tests the complete integration of Settings Tab with:
- Main application window
- PDF selector
- File management tab
- Configuration system
- MCP communication layer
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from src.compareblocks.gui.app import BECRMainWindow
from src.compareblocks.config.file_manager import file_manager


@pytest.fixture
def main_window(qtbot):
    """Create main window instance for testing."""
    window = BECRMainWindow()
    qtbot.addWidget(window)
    return window


class TestSettingsTabIntegration:
    """Test Settings Tab integration with main application."""
    
    def test_settings_tab_exists_in_main_window(self, main_window):
        """Test that Settings Tab is added to main window."""
        assert hasattr(main_window, 'settings_tab')
        assert main_window.settings_tab is not None
    
    def test_settings_tab_in_tab_widget(self, main_window):
        """Test that Settings Tab is in the tab widget."""
        tab_count = main_window.tab_widget.count()
        
        # Find Settings tab
        settings_tab_index = None
        for i in range(tab_count):
            if "Settings" in main_window.tab_widget.tabText(i):
                settings_tab_index = i
                break
        
        assert settings_tab_index is not None
        assert main_window.tab_widget.widget(settings_tab_index) == main_window.settings_tab

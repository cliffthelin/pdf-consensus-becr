#!/usr/bin/env python3
"""
Comprehensive tests for file_manager functionality.
Tests all functions with real data following TDD principles.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.compareblocks.config.file_manager import FileManager, file_manager
import pytest
import os


class TestFileManager:
    """Comprehensive test class for file_manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures with real data."""
        # Reset singleton for each test
        FileManager._instance = None
        FileManager._config = None
        FileManager._mcp_overrides = None
        
        # Create a temporary config for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        # Create test config file
        self.test_config = {
            "target_files": {
                "primary_pdf": {
                    "path": "Source_docs/test_document.pdf"
                }
            },
            "output_configuration": {
                "base_output_strategy": "pdf_location",
                "idempotent_processing": True,
                "timestamp_format": "%Y%m%d_%H%M",
                "fallback_output_directory": "output"
            },
            "output_files": {
                "gbg": {"filename": "gbg_blocks.ndjson"},
                "consensus": {"filename": "consensus_blocks.ndjson"},
                "analytics": {"filename": "analytics_report.json"}
            },
            "association_files": {
                "patterns": ["*.txt", "*.json", "*.csv"]
            }
        }
        
        config_file = self.config_dir / "default_files.json"
        with open(config_file, 'w') as f:
            json.dump(self.test_config, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_filemanager__new_(self):
        """Test FileManager.__new__: Singleton pattern to ensure consistent configuration across application."""
        # Test singleton behavior
        manager1 = FileManager()
        manager2 = FileManager()
        
        assert manager1 is manager2, "FileManager should be a singleton"
        assert FileManager._instance is not None, "Singleton instance should be set"
    
    @patch('src.compareblocks.config.file_manager.Path')
    def test_filemanager__init_(self, mock_path):
        """Test FileManager.__init__: Initialize the file manager with default configuration."""
        # Mock the path resolution
        mock_file = Mock()
        mock_file.parent.parent.parent.parent = Path(self.temp_dir)
        mock_path.__file__ = str(mock_file)
        mock_path.return_value = mock_file
        
        manager = FileManager()
        
        assert manager._config is not None, "Config should be loaded"
        assert manager._mcp_overrides == {}, "MCP overrides should be empty initially"
    
    @patch('src.compareblocks.config.file_manager.Path')
    def test_filemanager__load_config(self, mock_path):
        """Test FileManager._load_config: Load configuration from default_files.json."""
        # Mock the path resolution to point to our test config
        mock_file = Mock()
        mock_file.parent.parent.parent.parent = Path(self.temp_dir)
        mock_path.__file__ = str(mock_file)
        mock_path.return_value = mock_file
        
        manager = FileManager()
        manager._load_config()
        
        assert manager._config == self.test_config, "Config should match test config"
        assert manager._project_root == Path(self.temp_dir), "Project root should be set correctly"
    
    @patch('src.compareblocks.config.file_manager.Path')
    def test_filemanager_get_target_pdf_path(self, mock_path):
        """Test FileManager.get_target_pdf_path: Get the primary target PDF file path."""
        # Mock the path resolution
        mock_file = Mock()
        mock_file.parent.parent.parent.parent = Path(self.temp_dir)
        mock_path.__file__ = str(mock_file)
        mock_path.return_value = mock_file
        
        manager = FileManager()
        pdf_path = manager.get_target_pdf_path()
        
        expected_path = str(Path(self.temp_dir) / "Source_docs/test_document.pdf")
        assert pdf_path == expected_path, f"PDF path should be {expected_path}"
        
        # Test MCP override
        manager.set_mcp_override("target_pdf_path", "/override/path.pdf")
        override_path = manager.get_target_pdf_path()
        assert override_path == "/override/path.pdf", "MCP override should take precedence"
    
    def test_file_manager(self):
        """Test file_manager: Global instance of FileManager for application use."""
        # Reset singleton to test global instance behavior
        FileManager._instance = None
        FileManager._config = None
        FileManager._mcp_overrides = None
        
        # Test that the global instance is a FileManager
        assert isinstance(file_manager, FileManager), "Global file_manager should be a FileManager instance"
        
        # Test that it's the same instance (singleton)
        another_manager = FileManager()
        assert file_manager is another_manager, "Global instance should be the same as new instances"
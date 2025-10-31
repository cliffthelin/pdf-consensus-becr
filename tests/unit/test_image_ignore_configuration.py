#!/usr/bin/env python3

import pytest
import json
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from compareblocks.config.file_manager import FileManager
from compareblocks.association.pymupdf_matcher import PyMuPDFBlockMatcher


class TestImageIgnoreConfiguration:
    """Test image ignore configuration functionality."""
    
    def test_default_image_ignore_setting(self):
        """Test that image ignore is enabled by default."""
        file_manager = FileManager()
        
        # Should ignore images by default
        assert file_manager.should_ignore_images() is True
        
        # Should have correct placeholder text
        assert file_manager.get_image_placeholder_text() == "[IMAGE]"
    
    def test_image_block_detection(self):
        """Test image block detection logic."""
        file_manager = FileManager()
        
        # Should detect image blocks
        assert file_manager.is_image_block("[IMAGE]") is True
        assert file_manager.is_image_block("  [IMAGE]  ") is True  # With whitespace
        
        # Should not detect regular text as image blocks
        assert file_manager.is_image_block("Regular text") is False
        assert file_manager.is_image_block("") is False
        assert file_manager.is_image_block("IMAGE") is False  # Without brackets
        assert file_manager.is_image_block("[DIAGRAM]") is False  # Different placeholder
    
    def test_image_handling_config(self):
        """Test image handling configuration retrieval."""
        file_manager = FileManager()
        
        config = file_manager.get_image_handling_config()
        
        # Should have all required keys
        assert "ignore_images" in config
        assert "image_placeholder_text" in config
        assert "description" in config
        assert "per_pdf_override_enabled" in config
        
        # Should have correct default values
        assert config["ignore_images"] is True
        assert config["image_placeholder_text"] == "[IMAGE]"
        assert config["per_pdf_override_enabled"] is True
    
    def test_config_summary_includes_image_handling(self):
        """Test that configuration summary includes image handling settings."""
        file_manager = FileManager()
        
        summary = file_manager.get_config_summary()
        
        # Should include image handling in summary
        assert "image_handling" in summary
        assert summary["image_handling"]["ignore_images"] is True
        assert summary["image_handling"]["image_placeholder_text"] == "[IMAGE]"
    
    def test_pymupdf_matcher_filters_images(self):
        """Test that PyMuPDF matcher filters out image blocks when configured."""
        matcher = PyMuPDFBlockMatcher()
        
        # Create test data with image blocks
        gbg_data = {
            "pages": {
                "1": {
                    "blocks": [
                        {
                            "block_id": "gbg_block_1",
                            "text_content": "Regular text content"
                        },
                        {
                            "block_id": "gbg_block_2", 
                            "text_content": "[IMAGE]"
                        },
                        {
                            "block_id": "gbg_block_3",
                            "text_content": "More regular text"
                        }
                    ]
                }
            }
        }
        
        engine_data = {
            "blocks": [
                {
                    "block_id": "engine_block_1",
                    "page": 1,
                    "text": "Regular text content",
                    "bbox": [0, 0, 100, 20]
                },
                {
                    "block_id": "engine_block_2",
                    "page": 1, 
                    "text": "[IMAGE]",
                    "bbox": [0, 30, 100, 50]
                },
                {
                    "block_id": "engine_block_3",
                    "page": 1,
                    "text": "More regular text", 
                    "bbox": [0, 60, 100, 80]
                }
            ]
        }
        
        # Extract blocks by page (this should filter images)
        gbg_blocks_by_page = matcher._extract_gbg_blocks_by_page(gbg_data)
        engine_blocks_by_page = matcher._extract_engine_blocks_by_page(engine_data)
        
        # Should have filtered out image blocks
        assert abs(len(gbg_blocks_by_page[1]) - 2) < 0.01, f"Expected len(gbg_blocks_by_page[1]) to be close to 2"  # Only non-image blocks
        assert abs(len(engine_blocks_by_page[1]) - 2) < 0.01, f"Expected len(engine_blocks_by_page[1]) to be close to 2"  # Only non-image blocks
        
        # Should not contain image blocks
        gbg_texts = [block['text'] for block in gbg_blocks_by_page[1]]
        engine_texts = [block['text'] for block in engine_blocks_by_page[1]]
        
        assert "[IMAGE]" not in gbg_texts
        assert "[IMAGE]" not in engine_texts
        assert "Regular text content" in gbg_texts
        assert "More regular text" in gbg_texts
        assert "Regular text content" in engine_texts
        assert "More regular text" in engine_texts
    
    def test_image_filtering_reduces_unmapped_blocks(self):
        """Test that image filtering should reduce unmapped blocks in real scenarios."""
        # This is more of a documentation test showing the expected behavior
        
        # Before image filtering: 27 unmapped blocks (25 chars + 2 images)
        # After image filtering: 25 unmapped blocks (25 chars only)
        
        file_manager = FileManager()
        
        # Verify image filtering is enabled
        assert file_manager.should_ignore_images() is True
        
        # Verify image detection works
        assert file_manager.is_image_block("[IMAGE]") is True
        
        # This means the 2 image blocks from pages 4 and 61 should be filtered out
        # leaving only the 25 single character blocks that need combination matching


if __name__ == "__main__":
    pytest.main([__file__])
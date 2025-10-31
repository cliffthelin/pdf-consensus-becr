# tests/fixtures/create_test_pdfs.py
"""
Script to create minimal PDF fixtures for testing GBG functionality.
Creates simple PDFs with known text layouts for deterministic testing.
"""

import pytest
import fitz  # PyMuPDF
import os
from pathlib import Path


def create_simple_single_column_pdf(output_path: str):
    """Create a simple single-column PDF for basic testing."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Standard letter size
    
    # Add simple text blocks
    text_blocks = [
        {"text": "Title Block", "rect": fitz.Rect(50, 50, 300, 80), "fontsize": 16},
        {"text": "First paragraph with some content that spans multiple lines and provides enough text for testing.", 
         "rect": fitz.Rect(50, 100, 500, 150), "fontsize": 12},
        {"text": "Second paragraph with different content for variation testing.", 
         "rect": fitz.Rect(50, 170, 500, 220), "fontsize": 12},
        {"text": "Footer text", "rect": fitz.Rect(50, 700, 300, 730), "fontsize": 10}
    ]
    
    for block in text_blocks:
        page.insert_textbox(block["rect"], block["text"], fontsize=block["fontsize"])
    
    doc.save(output_path)
    doc.close()


def create_multi_column_pdf(output_path: str):
    """Create a multi-column PDF for column separation testing."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    
    # Left column
    left_blocks = [
        {"text": "Left Column Title", "rect": fitz.Rect(50, 50, 280, 80), "fontsize": 14},
        {"text": "Left column content with multiple lines of text that should be detected as separate from right column.", 
         "rect": fitz.Rect(50, 100, 280, 200), "fontsize": 11},
        {"text": "More left column text for testing block separation algorithms.", 
         "rect": fitz.Rect(50, 220, 280, 300), "fontsize": 11}
    ]
    
    # Right column
    right_blocks = [
        {"text": "Right Column Title", "rect": fitz.Rect(320, 50, 550, 80), "fontsize": 14},
        {"text": "Right column content that should be detected as separate blocks from the left side.", 
         "rect": fitz.Rect(320, 100, 550, 200), "fontsize": 11},
        {"text": "Additional right column text for comprehensive testing.", 
         "rect": fitz.Rect(320, 220, 550, 300), "fontsize": 11}
    ]
    
    for block in left_blocks + right_blocks:
        page.insert_textbox(block["rect"], block["text"], fontsize=block["fontsize"])
    
    doc.save(output_path)
    doc.close()


def create_rotated_text_pdf(output_path: str):
    """Create a PDF with rotated text for orientation testing."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    
    # Normal text
    page.insert_textbox(fitz.Rect(50, 50, 300, 100), "Normal horizontal text", fontsize=12)
    
    # Rotated text (90 degrees)
    page.insert_textbox(fitz.Rect(400, 100, 450, 300), "Vertical text rotated 90 degrees", 
                       fontsize=12, rotate=90)
    
    # Text for deskew testing (no rotation in PDF, will be tested with synthetic images)
    page.insert_textbox(fitz.Rect(50, 200, 400, 250), "Text for deskew testing with synthetic rotation", 
                       fontsize=12)
    
    doc.save(output_path)
    doc.close()


def main():
    """Create all test PDF fixtures."""
    fixtures_dir = Path(__file__).parent
    
    # Create fixture PDFs
    create_simple_single_column_pdf(str(fixtures_dir / "simple_single_column.pdf"))
    create_multi_column_pdf(str(fixtures_dir / "multi_column.pdf"))
    create_rotated_text_pdf(str(fixtures_dir / "rotated_text.pdf"))
    
    print("Test PDF fixtures created successfully!")


if __name__ == "__main__":
    main()
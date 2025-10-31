# src/compareblocks/debug/__init__.py
"""
Debug utilities for OCR and block analysis.
"""

from .image_extractor import ImageRegionExtractor, extract_debug_images_for_page

__all__ = [
    'ImageRegionExtractor',
    'extract_debug_images_for_page'
]
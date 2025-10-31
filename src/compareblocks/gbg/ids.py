# src/compareblocks/gbg/ids.py
"""
Stable block ID generation using hash of page number and normalized bounding box coordinates.
Ensures deterministic IDs that remain consistent across multiple processing runs.
"""

import hashlib
from typing import Union
from .types import BoundingBox


class BlockIDGenerator:
    """Generates stable, deterministic block identifiers."""
    
    @staticmethod
    def generate_block_id(page: int, bbox: BoundingBox, page_width: float, page_height: float) -> str:
        """
        Generate a stable block ID using hash of page number and normalized coordinates.
        
        Args:
            page: Page number (0-indexed)
            bbox: Bounding box coordinates
            page_width: Width of the page for normalization
            page_height: Height of the page for normalization
            
        Returns:
            Stable block ID string
        """
        # Normalize coordinates to ensure consistency across different page sizes
        normalized_bbox = bbox.normalize_coordinates(page_width, page_height)
        
        # Round coordinates to avoid floating point precision issues
        # Use 6 decimal places for sufficient precision while maintaining stability
        x = round(normalized_bbox.x, 6)
        y = round(normalized_bbox.y, 6)
        width = round(normalized_bbox.width, 6)
        height = round(normalized_bbox.height, 6)
        
        # Create deterministic string representation
        id_string = f"page:{page}|x:{x}|y:{y}|w:{width}|h:{height}"
        
        # Generate SHA-256 hash for stable, compact ID
        hash_object = hashlib.sha256(id_string.encode('utf-8'))
        block_id = hash_object.hexdigest()[:16]  # Use first 16 characters for readability
        
        return f"blk_{block_id}"
    
    @staticmethod
    def validate_block_id(block_id: str) -> bool:
        """
        Validate that a block ID follows the expected format.
        
        Args:
            block_id: Block ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(block_id, str):
            return False
        
        if not block_id.startswith("blk_"):
            return False
        
        # Check that the hash part is exactly 16 hexadecimal characters
        hash_part = block_id[4:]  # Remove "blk_" prefix
        if len(hash_part) != 16:
            return False
        
        try:
            int(hash_part, 16)  # Verify it's valid hexadecimal
            return True
        except ValueError:
            return False
    
    @staticmethod
    def extract_coordinates_from_id_string(id_string: str) -> tuple[int, float, float, float, float]:
        """
        Extract page and normalized coordinates from the ID string (for debugging).
        
        Args:
            id_string: The string used to generate the hash
            
        Returns:
            Tuple of (page, x, y, width, height)
        """
        parts = id_string.split('|')
        if len(parts) != 5:
            raise ValueError("Invalid ID string format")
        
        page = int(parts[0].split(':')[1])
        x = float(parts[1].split(':')[1])
        y = float(parts[2].split(':')[1])
        width = float(parts[3].split(':')[1])
        height = float(parts[4].split(':')[1])
        
        return page, x, y, width, height
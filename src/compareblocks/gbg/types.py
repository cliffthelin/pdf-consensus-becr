# src/compareblocks/gbg/types.py
"""
Core data structures for Global Block Grid (GBG) system.
Defines BoundingBox, SeedBlock, and OrientationHints dataclasses.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class BoundingBox:
    """Represents a rectangular bounding box with normalized coordinates."""
    x: float
    y: float
    width: float
    height: float
    
    def __post_init__(self):
        """Validate bounding box coordinates."""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Width and height must be positive")
        if self.x < 0 or self.y < 0:
            raise ValueError("Coordinates must be non-negative")
    
    def area(self) -> float:
        """Calculate the area of the bounding box."""
        return self.width * self.height
    
    def center(self) -> tuple[float, float]:
        """Get the center point of the bounding box."""
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    def normalize_coordinates(self, page_width: float, page_height: float) -> 'BoundingBox':
        """Normalize coordinates to 0-1 range based on page dimensions."""
        return BoundingBox(
            x=self.x / page_width,
            y=self.y / page_height,
            width=self.width / page_width,
            height=self.height / page_height
        )


@dataclass
class OrientationHints:
    """Metadata about text orientation and skew for a block."""
    page_rotation: float = 0.0  # Page-level rotation in degrees
    block_skew: float = 0.0     # Individual block skew in degrees
    is_vertical: bool = False   # True if text is vertical
    confidence: float = 1.0     # Confidence in orientation detection (0-1)
    
    def __post_init__(self):
        """Validate orientation hints."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")


@dataclass
class SeedBlock:
    """Represents a seed block from the Global Block Grid."""
    block_id: str
    page: int
    bbox: BoundingBox
    orientation_hints: OrientationHints
    text_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate seed block data."""
        if self.page < 0:
            raise ValueError("Page number must be non-negative")
        if not self.block_id:
            raise ValueError("Block ID cannot be empty")
        if self.metadata is None:
            self.metadata = {}
# src/compareblocks/gbg/seed.py
"""
Seed block detection system using PyMuPDF for deterministic PDF page segmentation.
Handles multi-column layouts and page-level rotation corrections.
"""

import fitz  # PyMuPDF
import numpy as np
from typing import List, Optional, Tuple
from .types import BoundingBox, SeedBlock, OrientationHints
from .ids import BlockIDGenerator
from .orientation import OrientationDetector

try:
    import cv2
except ImportError:
    cv2 = None


class SeedBlockDetector:
    """Detects and extracts seed blocks from PDF pages using PyMuPDF."""
    
    def __init__(self, min_block_area: float = 100.0, merge_threshold: float = 10.0):
        """
        Initialize the seed block detector.
        
        Args:
            min_block_area: Minimum area for a block to be considered valid
            merge_threshold: Distance threshold for merging nearby blocks
        """
        self.min_block_area = min_block_area
        self.merge_threshold = merge_threshold
        self.id_generator = BlockIDGenerator()
        self.orientation_detector = OrientationDetector() if cv2 is not None else None
    
    def extract_seed_blocks(self, pdf_path: str, page_num: int) -> List[SeedBlock]:
        """
        Extract seed blocks from a specific PDF page.
        
        Args:
            pdf_path: Path to the PDF file
            page_num: Page number (0-indexed)
            
        Returns:
            List of SeedBlock objects
        """
        doc = fitz.open(pdf_path)
        
        try:
            if page_num >= len(doc):
                raise ValueError(f"Page {page_num} does not exist in PDF")
            
            page = doc[page_num]
            
            # Get page dimensions
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Extract text blocks using PyMuPDF
            text_blocks = self._extract_text_blocks(page)
            
            # Detect page-level orientation if OpenCV is available
            orientation_hints = self._detect_page_orientation(page) if self.orientation_detector else OrientationHints()
            
            # Process blocks and generate stable IDs
            seed_blocks = []
            for block_data in text_blocks:
                bbox, text_content = block_data
                
                # Skip blocks that are too small
                if bbox.area() < self.min_block_area:
                    continue
                
                # Generate stable block ID
                block_id = self.id_generator.generate_block_id(
                    page_num, bbox, page_width, page_height
                )
                
                # Create seed block
                seed_block = SeedBlock(
                    block_id=block_id,
                    page=page_num,
                    bbox=bbox,
                    orientation_hints=orientation_hints,
                    text_content=text_content,
                    metadata={
                        'page_width': page_width,
                        'page_height': page_height,
                        'extraction_method': 'pymupdf'
                    }
                )
                
                seed_blocks.append(seed_block)
            
            # Handle multi-column layouts by separating blocks
            seed_blocks = self._separate_column_blocks(seed_blocks)
            
            return seed_blocks
            
        finally:
            doc.close()
    
    def extract_all_seed_blocks(self, pdf_path: str) -> List[SeedBlock]:
        """
        Extract seed blocks from all pages in a PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of all SeedBlock objects from all pages
        """
        doc = fitz.open(pdf_path)
        all_blocks = []
        
        try:
            for page_num in range(len(doc)):
                page_blocks = self.extract_seed_blocks(pdf_path, page_num)
                all_blocks.extend(page_blocks)
            
            return all_blocks
            
        finally:
            doc.close()
    
    def _extract_text_blocks(self, page: fitz.Page) -> List[Tuple[BoundingBox, str]]:
        """
        Extract text blocks from a PyMuPDF page.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            List of (BoundingBox, text_content) tuples
        """
        blocks = []
        
        # Get text blocks from PyMuPDF
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" not in block:  # Skip image blocks
                continue
            
            # Extract bounding box
            bbox_coords = block["bbox"]  # (x0, y0, x1, y1)
            bbox = BoundingBox(
                x=bbox_coords[0],
                y=bbox_coords[1],
                width=bbox_coords[2] - bbox_coords[0],
                height=bbox_coords[3] - bbox_coords[1]
            )
            
            # Extract text content
            text_content = ""
            for line in block["lines"]:
                for span in line["spans"]:
                    text_content += span["text"]
                text_content += "\n"
            
            text_content = text_content.strip()
            
            if text_content:  # Only include blocks with text
                blocks.append((bbox, text_content))
        
        return blocks
    
    def _detect_page_orientation(self, page: fitz.Page) -> OrientationHints:
        """
        Detect page-level orientation using image analysis.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            OrientationHints for the page
        """
        if self.orientation_detector is None:
            return OrientationHints()
        
        try:
            # Render page as image
            mat = fitz.Matrix(1.0, 1.0)  # Standard resolution
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Convert to OpenCV format
            img_array = np.frombuffer(img_data, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
            
            if img is None:
                return OrientationHints()
            
            # Detect orientation
            return self.orientation_detector.detect_page_orientation(img)
            
        except Exception:
            # Fallback to default orientation if detection fails
            return OrientationHints()
    
    def _separate_column_blocks(self, blocks: List[SeedBlock]) -> List[SeedBlock]:
        """
        Separate blocks that span multiple columns into individual column blocks.
        
        Args:
            blocks: List of seed blocks
            
        Returns:
            List of separated blocks
        """
        if not blocks:
            return blocks
        
        separated_blocks = []
        
        for block in blocks:
            # Check if block is likely multi-column by analyzing text layout
            if self._is_multi_column_block(block):
                column_blocks = self._split_into_columns(block)
                separated_blocks.extend(column_blocks)
            else:
                separated_blocks.append(block)
        
        return separated_blocks
    
    def _is_multi_column_block(self, block: SeedBlock) -> bool:
        """
        Determine if a block likely contains multiple columns.
        
        Args:
            block: SeedBlock to analyze
            
        Returns:
            True if block appears to be multi-column
        """
        # Simple heuristic: very wide blocks with significant text might be multi-column
        aspect_ratio = block.bbox.width / block.bbox.height
        
        # If width is much larger than height and contains substantial text
        if aspect_ratio > 3.0 and block.text_content and len(block.text_content) > 200:
            return True
        
        return False
    
    def _split_into_columns(self, block: SeedBlock) -> List[SeedBlock]:
        """
        Split a multi-column block into separate column blocks.
        
        Args:
            block: Multi-column block to split
            
        Returns:
            List of individual column blocks
        """
        # For now, implement a simple vertical split
        # In a more sophisticated implementation, this would analyze text flow
        
        # Split into 2 columns (can be enhanced to detect actual column count)
        left_bbox = BoundingBox(
            x=block.bbox.x,
            y=block.bbox.y,
            width=block.bbox.width / 2,
            height=block.bbox.height
        )
        
        right_bbox = BoundingBox(
            x=block.bbox.x + block.bbox.width / 2,
            y=block.bbox.y,
            width=block.bbox.width / 2,
            height=block.bbox.height
        )
        
        # Generate new IDs for column blocks
        page_width = block.metadata.get('page_width', 1.0)
        page_height = block.metadata.get('page_height', 1.0)
        
        left_id = self.id_generator.generate_block_id(
            block.page, left_bbox, page_width, page_height
        )
        right_id = self.id_generator.generate_block_id(
            block.page, right_bbox, page_width, page_height
        )
        
        # Split text content (simple approach - can be enhanced)
        text_lines = block.text_content.split('\n') if block.text_content else []
        mid_point = len(text_lines) // 2
        left_text = '\n'.join(text_lines[:mid_point])
        right_text = '\n'.join(text_lines[mid_point:])
        
        left_block = SeedBlock(
            block_id=left_id,
            page=block.page,
            bbox=left_bbox,
            orientation_hints=block.orientation_hints,
            text_content=left_text,
            metadata={**block.metadata, 'column': 'left', 'parent_block_id': block.block_id}
        )
        
        right_block = SeedBlock(
            block_id=right_id,
            page=block.page,
            bbox=right_bbox,
            orientation_hints=block.orientation_hints,
            text_content=right_text,
            metadata={**block.metadata, 'column': 'right', 'parent_block_id': block.block_id}
        )
        
        return [left_block, right_block]


class PDFPageAnalyzer:
    """Analyzes PDF pages for layout and structure information."""
    
    @staticmethod
    def get_page_info(pdf_path: str, page_num: int) -> dict:
        """
        Get basic information about a PDF page.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            
        Returns:
            Dictionary with page information
        """
        doc = fitz.open(pdf_path)
        
        try:
            if page_num >= len(doc):
                raise ValueError(f"Page {page_num} does not exist in PDF")
            
            page = doc[page_num]
            rect = page.rect
            
            return {
                'page_number': page_num,
                'width': rect.width,
                'height': rect.height,
                'rotation': page.rotation,
                'has_text': bool(page.get_text().strip()),
                'block_count': len(page.get_text("dict")["blocks"])
            }
            
        finally:
            doc.close()
    
    @staticmethod
    def analyze_layout_structure(pdf_path: str) -> dict:
        """
        Analyze the overall layout structure of a PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with layout analysis
        """
        doc = fitz.open(pdf_path)
        
        try:
            page_count = len(doc)
            total_blocks = 0
            page_sizes = []
            
            for page_num in range(page_count):
                page = doc[page_num]
                rect = page.rect
                page_sizes.append((rect.width, rect.height))
                
                text_dict = page.get_text("dict")
                total_blocks += len([b for b in text_dict["blocks"] if "lines" in b])
            
            # Calculate average page size
            avg_width = sum(size[0] for size in page_sizes) / len(page_sizes)
            avg_height = sum(size[1] for size in page_sizes) / len(page_sizes)
            
            return {
                'page_count': page_count,
                'total_text_blocks': total_blocks,
                'avg_blocks_per_page': total_blocks / page_count if page_count > 0 else 0,
                'average_page_size': (avg_width, avg_height),
                'consistent_page_sizes': len(set(page_sizes)) == 1
            }
            
        finally:
            doc.close()
# src/compareblocks/engines/gbg_guided_tesseract_engine.py
"""
GBG-guided Tesseract OCR engine that uses GBG analysis to intelligently guide OCR processing.

Key features:
1. Uses GBG block boundaries as OCR regions
2. Applies orientation detection with 90-degree rotation testing
3. Validates orientation using cross-page pattern consistency
4. Mirrors GBG block structure for precise matching
5. Optimizes OCR parameters based on GBG text characteristics
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps
import fitz  # PyMuPDF
from typing import Dict, List, Any, Optional, Tuple
import re
from pathlib import Path
import json
from dataclasses import dataclass
from collections import Counter

from ..config.file_manager import file_manager


@dataclass
class OrientationResult:
    """Result of orientation testing for a text block."""
    angle: int  # 0, 90, 180, 270
    confidence: float
    word_count: int
    pattern_matches: int
    text: str
    ocr_confidence: float


@dataclass
class GBGGuidedBlock:
    """A block processed with GBG guidance."""
    block_id: str
    page: int
    text: str
    bbox: List[float]
    gbg_block_id: str
    orientation: OrientationResult
    ocr_confidence: float
    processing_method: str


class GBGGuidedTesseractEngine:
    """Tesseract OCR engine guided by GBG analysis for optimal text extraction."""
    
    def __init__(self):
        """Initialize the GBG-guided Tesseract engine."""
        self.common_patterns = self._build_common_patterns()
        self.orientation_cache = {}  # Cache orientation results
        
    def _build_common_patterns(self) -> List[str]:
        """Build list of common text patterns for orientation validation."""
        return [
            'english language', 'language arts', 'utah state', 'state standards',
            'p-12 english', 'standard', 'grade', 'strand', 'speaking', 'listening',
            'reading', 'writing', 'board of education', 'adopted', 'may 2023'
        ]
    
    def extract_text_with_gbg_guidance(self, pdf_path: str, gbg_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text using GBG guidance for optimal OCR processing.
        
        Args:
            pdf_path: Path to the PDF file
            gbg_data: GBG analysis data for guidance
            
        Returns:
            Dictionary with extracted blocks and metadata
        """
        print(f"Starting GBG-guided Tesseract extraction from: {pdf_path}")
        
        # Open PDF
        pdf_document = fitz.open(pdf_path)
        
        # Initialize results
        all_blocks = []
        processing_metadata = {
            'engine': 'gbg_guided_tesseract',
            'version': '1.0.0',
            'total_pages': len(pdf_document),
            'gbg_guided': True,
            'orientation_testing': True,
            'pattern_validation': True
        }
        
        # Process each page with GBG guidance
        for page_num in range(len(pdf_document)):
            print(f"Processing page {page_num + 1}/{len(pdf_document)} with GBG guidance")
            
            page_blocks = self._process_page_with_gbg_guidance(
                pdf_document, page_num, gbg_data
            )
            all_blocks.extend(page_blocks)
        
        pdf_document.close()
        
        # Calculate statistics
        processing_metadata.update({
            'total_blocks': len(all_blocks),
            'avg_confidence': np.mean([b.ocr_confidence for b in all_blocks]) if all_blocks else 0.0,
            'orientation_distribution': self._calculate_orientation_distribution(all_blocks),
            'pattern_matches': sum(b.orientation.pattern_matches for b in all_blocks)
        })
        
        # Convert to standard format
        blocks_data = []
        for block in all_blocks:
            blocks_data.append({
                'block_id': block.block_id,
                'page': block.page,
                'text': block.text,
                'bbox': block.bbox,
                'confidence': block.ocr_confidence,
                'gbg_block_id': block.gbg_block_id,
                'orientation_angle': block.orientation.angle,
                'orientation_confidence': block.orientation.confidence,
                'word_count': block.orientation.word_count,
                'pattern_matches': block.orientation.pattern_matches,
                'processing_method': block.processing_method
            })
        
        return {
            'blocks': blocks_data,
            'metadata': processing_metadata,
            'engine_name': 'gbg_guided_tesseract',
            'total_blocks': len(blocks_data)
        }
    
    def _process_page_with_gbg_guidance(self, pdf_document: fitz.Document, page_num: int, 
                                       gbg_data: Dict[str, Any]) -> List[GBGGuidedBlock]:
        """Process a single page using GBG guidance."""
        page = pdf_document[page_num]
        
        # Get GBG blocks for this page
        gbg_blocks = self._get_gbg_blocks_for_page(gbg_data, page_num)
        
        if not gbg_blocks:
            print(f"  No GBG blocks found for page {page_num}, skipping")
            return []
        
        # Render page as image
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image
        pil_image = Image.open(io.BytesIO(img_data))
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        processed_blocks = []
        
        # Process each GBG block as an OCR region
        for i, gbg_block in enumerate(gbg_blocks):
            block_id = f"gbg_guided_tesseract_p{page_num}_b{i}"
            
            try:
                processed_block = self._process_gbg_block_region(
                    cv_image, gbg_block, block_id, page_num
                )
                if processed_block:
                    processed_blocks.append(processed_block)
            except Exception as e:
                print(f"    Error processing block {block_id}: {e}")
                continue
        
        print(f"  Processed {len(processed_blocks)} blocks from {len(gbg_blocks)} GBG regions")
        return processed_blocks
    
    def _get_gbg_blocks_for_page(self, gbg_data: Dict[str, Any], page_num: int) -> List[Dict[str, Any]]:
        """Get GBG blocks for a specific page."""
        pages = gbg_data.get('pages', {})
        page_data = pages.get(str(page_num), {})
        blocks = page_data.get('blocks', [])
        
        # Filter blocks with substantial text content
        substantial_blocks = []
        for block in blocks:
            text_content = block.get('text_content', '').strip()
            if len(text_content) >= 3:  # At least 3 characters
                # Skip image blocks if configured
                if file_manager.should_ignore_images() and file_manager.is_image_block(text_content):
                    continue
                substantial_blocks.append(block)
        
        return substantial_blocks
    
    def _process_gbg_block_region(self, cv_image: np.ndarray, gbg_block: Dict[str, Any], 
                                 block_id: str, page_num: int) -> Optional[GBGGuidedBlock]:
        """Process a single GBG block region with orientation testing."""
        bbox = gbg_block.get('bbox', {})
        gbg_block_id = gbg_block.get('block_id', '')
        expected_text = gbg_block.get('text_content', '').strip()
        
        # Extract region coordinates (scale by 2x for the zoomed image)
        x = int(bbox.get('x', 0) * 2)
        y = int(bbox.get('y', 0) * 2)
        width = int(bbox.get('width', 0) * 2)
        height = int(bbox.get('height', 0) * 2)
        
        # Validate coordinates
        if width <= 0 or height <= 0:
            return None
        
        # Extract region with padding
        padding = 5
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(cv_image.shape[1], x + width + padding)
        y2 = min(cv_image.shape[0], y + height + padding)
        
        region = cv_image[y1:y2, x1:x2]
        
        if region.size == 0:
            return None
        
        # Test different orientations
        best_orientation = self._test_orientations(region, expected_text, page_num)
        
        # Use the best orientation result
        if best_orientation.confidence > 0.1:  # Minimum confidence threshold
            return GBGGuidedBlock(
                block_id=block_id,
                page=page_num,
                text=best_orientation.text,
                bbox=[x/2, y/2, (x+width)/2, (y+height)/2],  # Convert back to original scale
                gbg_block_id=gbg_block_id,
                orientation=best_orientation,
                ocr_confidence=best_orientation.ocr_confidence,
                processing_method='gbg_guided_orientation_tested'
            )
        
        return None
    
    def _test_orientations(self, region: np.ndarray, expected_text: str, page_num: int) -> OrientationResult:
        """Test different orientations (0°, 90°, 180°, 270°) and return the best result."""
        orientations = [0, 90, 180, 270]
        results = []
        
        for angle in orientations:
            try:
                # Rotate image
                if angle == 0:
                    rotated_region = region
                elif angle == 90:
                    rotated_region = cv2.rotate(region, cv2.ROTATE_90_CLOCKWISE)
                elif angle == 180:
                    rotated_region = cv2.rotate(region, cv2.ROTATE_180)
                elif angle == 270:
                    rotated_region = cv2.rotate(region, cv2.ROTATE_90_COUNTERCLOCKWISE)
                
                # Preprocess for OCR
                processed_region = self._preprocess_for_ocr(rotated_region)
                
                # Perform OCR with optimized configuration
                # PSM 6 (single uniform block) works best for clear text blocks
                ocr_result = pytesseract.image_to_data(
                    processed_region, 
                    output_type=pytesseract.Output.DICT,
                    config='--psm 6'
                )
                
                # Extract text and confidence
                text_parts = []
                confidences = []
                
                for i, conf in enumerate(ocr_result['conf']):
                    if int(conf) > 0:  # Valid confidence
                        word = ocr_result['text'][i].strip()
                        if word:
                            text_parts.append(word)
                            confidences.append(int(conf))
                
                text = ' '.join(text_parts)
                avg_confidence = np.mean(confidences) if confidences else 0.0
                
                # Calculate orientation quality metrics
                word_count = len([w for w in text.split() if len(w) >= 2])
                pattern_matches = self._count_pattern_matches(text)
                
                # Calculate overall confidence
                orientation_confidence = self._calculate_orientation_confidence(
                    text, expected_text, word_count, pattern_matches, avg_confidence
                )
                
                results.append(OrientationResult(
                    angle=angle,
                    confidence=orientation_confidence,
                    word_count=word_count,
                    pattern_matches=pattern_matches,
                    text=text,
                    ocr_confidence=avg_confidence / 100.0
                ))
                
            except Exception as e:
                # If orientation fails, create a low-confidence result
                results.append(OrientationResult(
                    angle=angle,
                    confidence=0.0,
                    word_count=0,
                    pattern_matches=0,
                    text="",
                    ocr_confidence=0.0
                ))
        
        # Return the best orientation
        best_result = max(results, key=lambda r: r.confidence)
        return best_result
    
    def _preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image region for optimal OCR - optimized for clear text."""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Light preprocessing only - bilateral filter to reduce noise while preserving edges
        # This is optimal for clear, high-quality text like in educational documents
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        return denoised
    
    def _count_pattern_matches(self, text: str) -> int:
        """Count how many common patterns are found in the text."""
        text_lower = text.lower()
        matches = 0
        
        for pattern in self.common_patterns:
            if pattern in text_lower:
                matches += 1
        
        return matches
    
    def _calculate_orientation_confidence(self, text: str, expected_text: str, 
                                        word_count: int, pattern_matches: int, 
                                        ocr_confidence: float) -> float:
        """Calculate overall confidence for an orientation."""
        if not text.strip():
            return 0.0
        
        # Base confidence from OCR
        base_confidence = ocr_confidence / 100.0
        
        # Word count bonus (more real words = better orientation)
        word_bonus = min(word_count * 0.1, 0.5)
        
        # Pattern match bonus (domain-specific patterns)
        pattern_bonus = min(pattern_matches * 0.15, 0.3)
        
        # Text similarity bonus (if we have expected text)
        similarity_bonus = 0.0
        if expected_text:
            from rapidfuzz import fuzz
            similarity = fuzz.ratio(text.lower(), expected_text.lower()) / 100.0
            similarity_bonus = similarity * 0.2
        
        # Combine all factors
        total_confidence = base_confidence + word_bonus + pattern_bonus + similarity_bonus
        
        return min(total_confidence, 1.0)
    
    def _calculate_orientation_distribution(self, blocks: List[GBGGuidedBlock]) -> Dict[int, int]:
        """Calculate distribution of orientations used."""
        distribution = {0: 0, 90: 0, 180: 0, 270: 0}
        
        for block in blocks:
            angle = block.orientation.angle
            if angle in distribution:
                distribution[angle] += 1
        
        return distribution


# Import required modules at the top
import io
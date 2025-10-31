# src/compareblocks/debug/image_extractor.py
"""
Image extraction and debugging utilities for OCR analysis.
Extracts and saves image regions for visual inspection and debugging.
"""

import cv2
import numpy as np
import fitz  # PyMuPDF
from PIL import Image
import io
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json

from ..config.file_manager import file_manager


class ImageRegionExtractor:
    """Extract and save image regions for OCR debugging."""
    
    def __init__(self):
        """Initialize the image extractor."""
        self.debug_output_dir = Path("output/debug_images")
        self.debug_output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_page_regions(self, pdf_path: str, page_num: int, gbg_blocks: List[Dict[str, Any]], 
                           max_blocks: int = 5) -> List[Dict[str, Any]]:
        """
        Extract image regions for the first few blocks on a page for debugging.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to process
            gbg_blocks: List of GBG blocks for the page
            max_blocks: Maximum number of blocks to extract
            
        Returns:
            List of extracted region information
        """
        print(f"Extracting debug images for page {page_num}, first {max_blocks} blocks...")
        
        # Open PDF and get page
        pdf_document = fitz.open(pdf_path)
        page = pdf_document[page_num]
        
        # Render page as high-resolution image
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image and then to OpenCV
        pil_image = Image.open(io.BytesIO(img_data))
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        extracted_regions = []
        
        # Process first few blocks
        for i, gbg_block in enumerate(gbg_blocks[:max_blocks]):
            try:
                region_info = self._extract_single_region(
                    cv_image, gbg_block, page_num, i, pdf_path
                )
                if region_info:
                    extracted_regions.append(region_info)
            except Exception as e:
                print(f"    Error extracting block {i}: {e}")
                continue
        
        pdf_document.close()
        
        print(f"    Extracted {len(extracted_regions)} debug images")
        return extracted_regions
    
    def _extract_single_region(self, cv_image: np.ndarray, gbg_block: Dict[str, Any], 
                              page_num: int, block_index: int, pdf_path: str) -> Optional[Dict[str, Any]]:
        """Extract a single region and save debug images."""
        bbox = gbg_block.get('bbox', {})
        gbg_block_id = gbg_block.get('block_id', '')
        expected_text = gbg_block.get('text_content', '').strip()
        
        # Extract region coordinates (scale by 2x for the zoomed image)
        x = int(bbox.get('x', 0) * 2)
        y = int(bbox.get('y', 0) * 2)
        width = int(bbox.get('width', 0) * 2)
        height = int(bbox.get('height', 0) * 2)
        
        if width <= 0 or height <= 0:
            return None
        
        # Extract region with padding
        padding = 10  # Increased padding for better context
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(cv_image.shape[1], x + width + padding)
        y2 = min(cv_image.shape[0], y + height + padding)
        
        original_region = cv_image[y1:y2, x1:x2]
        
        if original_region.size == 0:
            return None
        
        # Create filename base
        pdf_name = Path(pdf_path).stem
        filename_base = f"{pdf_name}_p{page_num}_b{block_index}_{gbg_block_id[:8]}"
        
        # Save original region
        original_path = self.debug_output_dir / f"{filename_base}_original.png"
        cv2.imwrite(str(original_path), original_region)
        
        # Test different orientations and save each
        orientation_results = []
        orientations = [0, 90, 180, 270]
        
        for angle in orientations:
            # Rotate image
            if angle == 0:
                rotated_region = original_region
            elif angle == 90:
                rotated_region = cv2.rotate(original_region, cv2.ROTATE_90_CLOCKWISE)
            elif angle == 180:
                rotated_region = cv2.rotate(original_region, cv2.ROTATE_180)
            elif angle == 270:
                rotated_region = cv2.rotate(original_region, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            # Save rotated version
            rotated_path = self.debug_output_dir / f"{filename_base}_rot{angle}.png"
            cv2.imwrite(str(rotated_path), rotated_region)
            
            # Apply preprocessing and save
            processed_region = self._preprocess_for_ocr(rotated_region)
            processed_path = self.debug_output_dir / f"{filename_base}_rot{angle}_processed.png"
            cv2.imwrite(str(processed_path), processed_region)
            
            orientation_results.append({
                'angle': angle,
                'rotated_image_path': str(rotated_path),
                'processed_image_path': str(processed_path)
            })
        
        # Create region info
        region_info = {
            'page_num': page_num,
            'block_index': block_index,
            'gbg_block_id': gbg_block_id,
            'expected_text': expected_text,
            'bbox': {
                'x': bbox.get('x', 0),
                'y': bbox.get('y', 0),
                'width': bbox.get('width', 0),
                'height': bbox.get('height', 0)
            },
            'original_image_path': str(original_path),
            'orientation_results': orientation_results,
            'filename_base': filename_base
        }
        
        return region_info
    
    def _preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Apply the same preprocessing used in the OCR engine."""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Denoise
        denoised = cv2.medianBlur(binary, 3)
        
        # Enhance contrast
        enhanced = cv2.equalizeHist(denoised)
        
        return enhanced
    
    def create_debug_report(self, extracted_regions: List[Dict[str, Any]], 
                           tesseract_results: List[Dict[str, Any]]) -> str:
        """Create an HTML debug report showing images and OCR results."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>OCR Debug Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .block {{ border: 1px solid #ccc; margin: 20px 0; padding: 15px; }}
        .block-header {{ background: #f0f0f0; padding: 10px; margin: -15px -15px 15px -15px; }}
        .images {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .image-group {{ border: 1px solid #ddd; padding: 10px; }}
        .image-group img {{ max-width: 200px; max-height: 150px; }}
        .expected {{ color: #006600; font-weight: bold; }}
        .actual {{ color: #cc0000; font-weight: bold; }}
        .confidence {{ color: #0066cc; }}
        .orientation {{ color: #cc6600; }}
    </style>
</head>
<body>
    <h1>OCR Debug Report</h1>
    <p>Generated: {timestamp}</p>
"""
        
        for i, region in enumerate(extracted_regions):
            # Find corresponding Tesseract result
            tesseract_result = None
            if i < len(tesseract_results):
                tesseract_result = tesseract_results[i]
            
            html_content += f"""
    <div class="block">
        <div class="block-header">
            <h2>Block {i+1}: {region['gbg_block_id']}</h2>
            <p><strong>Page:</strong> {region['page_num']} | 
               <strong>BBox:</strong> x={region['bbox']['x']:.1f}, y={region['bbox']['y']:.1f}, 
               w={region['bbox']['width']:.1f}, h={region['bbox']['height']:.1f}</p>
        </div>
        
        <div class="expected">Expected Text: "{region['expected_text'][:100]}{'...' if len(region['expected_text']) > 100 else ''}"</div>
"""
            
            if tesseract_result:
                actual_text = tesseract_result.get('text', '').strip()
                confidence = tesseract_result.get('confidence', 0.0)
                orientation = tesseract_result.get('orientation_angle', 0)
                
                html_content += f"""
        <div class="actual">Actual Text: "{actual_text[:100]}{'...' if len(actual_text) > 100 else ''}"</div>
        <div class="confidence">Confidence: {confidence:.3f}</div>
        <div class="orientation">Selected Orientation: {orientation}°</div>
"""
            
            html_content += """
        <h3>Images:</h3>
        <div class="images">
"""
            
            # Add original image
            original_path = Path(region['original_image_path'])
            if original_path.exists():
                html_content += f"""
            <div class="image-group">
                <h4>Original</h4>
                <img src="{original_path.name}" alt="Original">
            </div>
"""
            
            # Add orientation images
            for orientation_result in region['orientation_results']:
                angle = orientation_result['angle']
                rotated_path = Path(orientation_result['rotated_image_path'])
                processed_path = Path(orientation_result['processed_image_path'])
                
                selected = ""
                if tesseract_result and tesseract_result.get('orientation_angle') == angle:
                    selected = " (SELECTED)"
                
                html_content += f"""
            <div class="image-group">
                <h4>{angle}°{selected}</h4>
                <div>Rotated:</div>
                <img src="{rotated_path.name}" alt="Rotated {angle}°">
                <div>Processed:</div>
                <img src="{processed_path.name}" alt="Processed {angle}°">
            </div>
"""
            
            html_content += """
        </div>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        # Save HTML report
        report_path = self.debug_output_dir / "debug_report.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(report_path)


def extract_debug_images_for_page(pdf_path: str, page_num: int, max_blocks: int = 5) -> Dict[str, Any]:
    """
    Extract debug images for a specific page.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number to process
        max_blocks: Maximum number of blocks to extract
        
    Returns:
        Dictionary with extraction results and paths
    """
    # Load GBG data
    gbg_analysis_path = file_manager.get_gbg_analysis_output_path()
    
    try:
        with open(gbg_analysis_path, 'r', encoding='utf-8') as f:
            gbg_data = json.load(f)
    except FileNotFoundError:
        return {'error': f'GBG analysis file not found: {gbg_analysis_path}'}
    
    # Get GBG blocks for the page
    gbg_blocks = gbg_data.get('pages', {}).get(str(page_num), {}).get('blocks', [])
    
    if not gbg_blocks:
        return {'error': f'No GBG blocks found for page {page_num}'}
    
    # Filter blocks with substantial text content
    substantial_blocks = []
    for block in gbg_blocks:
        text_content = block.get('text_content', '').strip()
        if len(text_content) >= 3:  # At least 3 characters
            substantial_blocks.append(block)
    
    if not substantial_blocks:
        return {'error': f'No substantial GBG blocks found for page {page_num}'}
    
    # Extract image regions
    extractor = ImageRegionExtractor()
    extracted_regions = extractor.extract_page_regions(pdf_path, page_num, substantial_blocks, max_blocks)
    
    # Try to load corresponding Tesseract results
    tesseract_results = []
    try:
        tesseract_path = Path(file_manager.get_processing_directory()) / "English Language Arts Standards_tesseract.json"
        if tesseract_path.exists():
            with open(tesseract_path, 'r', encoding='utf-8') as f:
                tesseract_data = json.load(f)
            
            # Find blocks for this page
            tesseract_page_blocks = [b for b in tesseract_data.get('blocks', []) if b.get('page') == page_num]
            tesseract_results = tesseract_page_blocks[:max_blocks]
    except Exception as e:
        print(f"Could not load Tesseract results: {e}")
    
    # Create debug report
    report_path = extractor.create_debug_report(extracted_regions, tesseract_results)
    
    return {
        'success': True,
        'page_num': page_num,
        'extracted_regions': len(extracted_regions),
        'debug_images_dir': str(extractor.debug_output_dir),
        'debug_report_path': report_path,
        'regions': extracted_regions
    }
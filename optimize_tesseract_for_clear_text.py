#!/usr/bin/env python3
"""
Optimize Tesseract OCR parameters for clear, high-quality text like Block 1.
Tests different preprocessing and OCR configurations to find optimal settings.
import pytest
import numpy as np

@pytest.fixture
def image():
    """Create a test image for OCR preprocessing tests."""
    # Create a simple test image with text
    return np.ones((100, 200, 3), dtype=np.uint8) * 255

@pytest.fixture  
def region():
    """Create a test region for OCR configuration tests."""
    return {
        'bbox': [10, 10, 100, 50],
        'text': 'Sample text'
    }

@pytest.fixture
def expected_text():
    """Expected text for OCR tests."""
    return "Sample text"

@pytest.fixture
def preprocessing_func():
    """Preprocessing function for tests."""
    return test_minimal_preprocessing

@pytest.fixture
def tesseract_config():
    """Tesseract configuration for tests."""
    return "--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"



This tool is essential for:
- Diagnosing OCR quality issues
- Testing new preprocessing approaches
- Validating OCR parameter changes
- Benchmarking OCR performance on specific blocks
"""

import sys
import cv2
import numpy as np
import pytesseract
from PIL import Image
import fitz
from pathlib import Path
import json
import io

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from compareblocks.config.file_manager import file_manager


def test_minimal_preprocessing(image):
    """Test minimal preprocessing."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    result = gray
    assert result is not None
    return result


def test_light_preprocessing(image):
    """Test light preprocessing."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Very light bilateral filter to reduce noise while preserving edges
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    result = denoised
    assert result is not None
    return result


def test_current_preprocessing(image):
    """Test current preprocessing."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Current aggressive preprocessing
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    denoised = cv2.medianBlur(binary, 3)
    enhanced = cv2.equalizeHist(denoised)
    
    result = enhanced
    assert result is not None
    return result


def test_enhanced_preprocessing(image):
    """Test enhanced preprocessing."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Enhanced preprocessing
    # 1. Bilateral filter for noise reduction
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 2. Morphological operations to clean up text
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)
    
    result = cleaned
    assert result is not None
    return result


def test_tesseract_configs():
    """Test different Tesseract configurations."""
    return [
        {
            'name': 'default',
            'config': '--psm 6'
        },
        {
            'name': 'single_text_block',
            'config': '--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,;:!?()-[]{}"\''
        },
        {
            'name': 'single_text_line',
            'config': '--psm 7'
        },
        {
            'name': 'single_word',
            'config': '--psm 8'
        },
        {
            'name': 'raw_line',
            'config': '--psm 13'
        },
        {
            'name': 'optimized_block',
            'config': '--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,;:!?()-[]{}"\' -c preserve_interword_spaces=1'
        },
        {
            'name': 'high_quality',
            'config': '--psm 6 --oem 1 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,;:!?()-[]{}"\' -c preserve_interword_spaces=1 -c textord_really_old_xheight=1'
        },
        {
            'name': 'lstm_only',
            'config': '--psm 6 --oem 1'
        },
        {
            'name': 'legacy_only',
            'config': '--psm 6 --oem 0'
        },
        {
            'name': 'combined_engines',
            'config': '--psm 6 --oem 2'
        }
    ]


def extract_block_region(pdf_path, page_num, block_index=0):
    """Extract the specific block region for testing."""
    # Load GBG data
    gbg_analysis_path = file_manager.get_gbg_analysis_output_path()
    
    with open(gbg_analysis_path, 'r', encoding='utf-8') as f:
        gbg_data = json.load(f)
    
    # Get GBG blocks for the page
    gbg_blocks = gbg_data.get('pages', {}).get(str(page_num), {}).get('blocks', [])
    
    if block_index >= len(gbg_blocks):
        raise ValueError(f"Block index {block_index} not found on page {page_num}")
    
    gbg_block = gbg_blocks[block_index]
    expected_text = gbg_block.get('text_content', '').strip()
    bbox = gbg_block.get('bbox', {})
    
    # Open PDF and extract region
    pdf_document = fitz.open(pdf_path)
    page = pdf_document[page_num]
    
    # Render page as high-resolution image
    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    
    # Convert to PIL Image and then to OpenCV
    pil_image = Image.open(io.BytesIO(img_data))
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    # Extract region coordinates (scale by 2x for the zoomed image)
    x = int(bbox.get('x', 0) * 2)
    y = int(bbox.get('y', 0) * 2)
    width = int(bbox.get('width', 0) * 2)
    height = int(bbox.get('height', 0) * 2)
    
    # Extract region with padding
    padding = 10
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(cv_image.shape[1], x + width + padding)
    y2 = min(cv_image.shape[0], y + height + padding)
    
    region = cv_image[y1:y2, x1:x2]
    
    pdf_document.close()
    
    return region, expected_text, gbg_block.get('block_id', '')


def test_ocr_configuration(region, expected_text, preprocessing_func, tesseract_config):
    """Test OCR configuration."""
    try:
        # Apply preprocessing
        processed_region = preprocessing_func(region)
        
        # Perform OCR
        ocr_result = pytesseract.image_to_data(
            processed_region,
            output_type=pytesseract.Output.DICT,
            config=tesseract_config['config']
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
        
        extracted_text = ' '.join(text_parts)
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        # Calculate similarity to expected text
        from rapidfuzz import fuzz
        similarity = fuzz.ratio(extracted_text.lower(), expected_text.lower())
        
        result = {
    assert result is not None
    return result
            'extracted_text': extracted_text,
            'confidence': avg_confidence,
            'similarity': similarity,
            'word_count': len(text_parts),
            'success': len(extracted_text.strip()) > 0
        }
        
    except Exception as e:
        return {
            'extracted_text': '',
            'confidence': 0.0,
            'similarity': 0.0,
            'word_count': 0,
            'success': False,
            'error': str(e)
        }


def save_debug_images(region, expected_text, block_id, preprocessing_methods):
    """Save debug images for visual inspection."""
    debug_dir = Path("output/ocr_optimization_debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Save original region
    original_path = debug_dir / f"{block_id}_original.png"
    cv2.imwrite(str(original_path), region)
    
    # Save preprocessed versions
    for prep_name, prep_func in preprocessing_methods:
        processed = prep_func(region)
        processed_path = debug_dir / f"{block_id}_{prep_name}.png"
        cv2.imwrite(str(processed_path), processed)
    
    print(f"🖼️  Debug images saved to: {debug_dir}")
    return debug_dir


def main():
    """Test different OCR configurations to find optimal settings."""
    print("🔧 Tesseract OCR Optimization for Clear Text")
    print("=" * 60)
    
    # Configuration - can be modified for different tests
    pdf_path = "Source_docs/English Language Arts Standards/-English Language Arts Standards.pdf"
    page_num = 15
    block_index = 0  # Block 1 (0-indexed)
    
    # Allow command-line overrides
    if len(sys.argv) > 1:
        try:
            page_num = int(sys.argv[1])
        except ValueError:
            print(f"Invalid page number: {sys.argv[1]}")
            return 1
    
    if len(sys.argv) > 2:
        try:
            block_index = int(sys.argv[2])
        except ValueError:
            print(f"Invalid block index: {sys.argv[2]}")
            return 1
    
    print(f"📄 PDF: {Path(pdf_path).name}")
    print(f"📖 Page: {page_num}")
    print(f"🔢 Block: {block_index + 1}")
    print()
    
    # Extract the block region
    try:
        region, expected_text, block_id = extract_block_region(pdf_path, page_num, block_index)
        print(f"🎯 Target Block: {block_id}")
        print(f"📝 Expected Text: \"{expected_text[:80]}{'...' if len(expected_text) > 80 else ''}\"")
        print(f"🖼️  Region Size: {region.shape[1]}x{region.shape[0]} pixels")
        print()
    except Exception as e:
        print(f"❌ Error extracting block region: {e}")
        return 1
    
    # Test different preprocessing methods
    preprocessing_methods = [
        ('minimal', test_minimal_preprocessing),
        ('light', test_light_preprocessing),
        ('enhanced', test_enhanced_preprocessing),
        ('current_aggressive', test_current_preprocessing)
    ]
    
    # Save debug images for visual inspection
    debug_dir = save_debug_images(region, expected_text, block_id, preprocessing_methods)
    
    # Test different Tesseract configurations
    tesseract_configs = test_tesseract_configs()
    
    print("🧪 Testing OCR Configurations...")
    print("=" * 60)
    
    results = []
    
    for prep_name, prep_func in preprocessing_methods:
        print(f"\n📋 Testing preprocessing: {prep_name}")
        print("-" * 40)
        
        for config in tesseract_configs:
            print(f"  Testing: {config['name']}")
            
            result = test_ocr_configuration(region, expected_text, prep_func, config)
            result['preprocessing'] = prep_name
            result['tesseract_config'] = config['name']
            result['config_string'] = config['config']
            
            results.append(result)
            
            # Show result
            if result['success']:
                print(f"    ✅ Similarity: {result['similarity']:.1f}% | Confidence: {result['confidence']:.1f} | Words: {result['word_count']}")
                if result['similarity'] > 90:
                    print(f"    📝 Text: \"{result['extracted_text'][:60]}{'...' if len(result['extracted_text']) > 60 else ''}\"")
            else:
                error_msg = result.get('error', 'No text extracted')
                print(f"    ❌ Failed: {error_msg}")
    
    # Find best results
    print("\n🏆 Best Results (by similarity to expected text):")
    print("=" * 60)
    
    # Sort by similarity, then by confidence
    best_results = sorted(results, key=lambda r: (r['similarity'], r['confidence']), reverse=True)
    
    for i, result in enumerate(best_results[:5]):  # Top 5 results
        print(f"{i+1}. {result['preprocessing']} + {result['tesseract_config']}")
        print(f"   Similarity: {result['similarity']:.1f}% | Confidence: {result['confidence']:.1f} | Words: {result['word_count']}")
        print(f"   Config: {result['config_string']}")
        if result['similarity'] > 70:  # Only show text for good results
            print(f"   Text: \"{result['extracted_text'][:80]}{'...' if len(result['extracted_text']) > 80 else ''}\"")
        print()
    
    # Show the winner
    if best_results:
        winner = best_results[0]
        print("🥇 OPTIMAL CONFIGURATION:")
        print("=" * 40)
        print(f"Preprocessing: {winner['preprocessing']}")
        print(f"Tesseract Config: {winner['tesseract_config']}")
        print(f"Config String: {winner['config_string']}")
        print(f"Similarity: {winner['similarity']:.1f}%")
        print(f"Confidence: {winner['confidence']:.1f}")
        print(f"Extracted Text: \"{winner['extracted_text']}\"")
        print()
        
        if winner['similarity'] > 95:
            print("🎉 EXCELLENT! This configuration achieves >95% accuracy!")
        elif winner['similarity'] > 80:
            print("✅ GOOD! This configuration achieves >80% accuracy!")
        else:
            print("⚠️  NEEDS IMPROVEMENT! Consider different preprocessing or OCR parameters.")
        
        print()
        print("💡 Recommendation: Update the GBG-guided Tesseract engine with these optimal settings!")
        print(f"🖼️  Visual inspection: Check debug images in {debug_dir}")
    
    return 0


if __name__ == "__main__":
    # Usage examples:
    # python optimize_tesseract_for_clear_text.py           # Test page 15, block 1
    # python optimize_tesseract_for_clear_text.py 20        # Test page 20, block 1  
    # python optimize_tesseract_for_clear_text.py 15 2      # Test page 15, block 3
    sys.exit(main())
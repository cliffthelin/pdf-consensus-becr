#!/usr/bin/env python3

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from compareblocks.debug.image_extractor import extract_debug_images_for_page
from compareblocks.config.file_manager import file_manager

def test_debug_image_extraction():
    """Test the debug image extraction for page 15."""
    print("Testing debug image extraction for page 15...")
    
    # Get PDF path
    pdf_path = file_manager.get_target_pdf_path()
    
    # Extract debug images for page 15, first 3 blocks
    result = extract_debug_images_for_page(pdf_path, page_num=15, max_blocks=3)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return False
    
    print(f"✅ Success!")
    print(f"   Page: {result['page_num']}")
    print(f"   Extracted regions: {result['extracted_regions']}")
    print(f"   Debug images directory: {result['debug_images_dir']}")
    print(f"   Debug report: {result['debug_report_path']}")
    
    # Show details of extracted regions
    print(f"\nExtracted regions:")
    for i, region in enumerate(result['regions']):
        print(f"  Region {i+1}:")
        print(f"    GBG Block: {region['gbg_block_id']}")
        print(f"    Expected: \"{region['expected_text'][:50]}...\"")
        print(f"    Original image: {Path(region['original_image_path']).name}")
        print(f"    Orientations: {len(region['orientation_results'])} images")
    
    print(f"\nDebug images saved to: {result['debug_images_dir']}")
    print(f"Open the debug report in a browser: {result['debug_report_path']}")
    
    return True

if __name__ == "__main__":
    test_debug_image_extraction()
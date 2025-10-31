#!/usr/bin/env python3
"""
Show the 2 remaining similarity matches and 27 unmapped blocks
to understand what needs dynamic alignment.
"""

import json
from pathlib import Path

def show_remaining_issues():
    """Show the remaining matching issues."""
    
    # Load the GBG analysis file
    gbg_file = Path("Source_docs/English Language Arts Standards/Processing_Inprogress/gbg_full_analysis.json")
    with open(gbg_file, 'r', encoding='utf-8') as f:
        gbg_data = json.load(f)
    
    # Load PyMuPDF engine data
    pymupdf_file = Path("Source_docs/English Language Arts Standards/Processing_Inprogress/English Language Arts Standards_pymupdf.json")
    with open(pymupdf_file, 'r', encoding='utf-8') as f:
        pymupdf_data = json.load(f)
    
    # Get association data
    associations = gbg_data['engine_associations']['pymupdf']['associations']
    
    # Find the 2 remaining similarity matches
    similarity_matches = [a for a in associations if a.get('match_type') == 'similarity_text']
    
    print(f"🔍 **2 Remaining Similarity Matches (Legitimate Content Differences):**")
    print("=" * 80)
    
    for i, match in enumerate(similarity_matches, 1):
        print(f"\n**Similarity Match #{i}:**")
        print(f"Engine Block ID: {match['engine_block_id']}")
        print(f"GBG Block ID: {match['gbg_block_id']}")
        print(f"Similarity Score: {match['similarity_score']:.6f}")
        
        # Find full texts
        engine_block = next((b for b in pymupdf_data['blocks'] if b['block_id'] == match['engine_block_id']), None)
        
        gbg_block = None
        if engine_block:
            page_num = str(engine_block['page'])
            if page_num in gbg_data['pages']:
                gbg_block = next((b for b in gbg_data['pages'][page_num]['blocks'] 
                                if b['block_id'] == match['gbg_block_id']), None)
        
        if engine_block and gbg_block:
            engine_text = engine_block['text']
            gbg_text = gbg_block['text_content']
            
            print(f"Engine Text: \"{engine_text}\"")
            print(f"GBG Text:    \"{gbg_text}\"")
            
            # Analyze the difference
            print(f"Engine bytes: {engine_text.encode('utf-8')}")
            print(f"GBG bytes:    {gbg_text.encode('utf-8')}")
            
            # Check for common fixable issues
            issues = []
            
            # Check punctuation differences
            engine_punct = engine_text.replace('.', '').replace(',', '').replace(':', '').replace(';', '')
            gbg_punct = gbg_text.replace('.', '').replace(',', '').replace(':', '').replace(';', '')
            if engine_punct == gbg_punct:
                issues.append("PUNCTUATION_DIFFERENCE")
            
            # Check spacing differences
            engine_spaced = ' '.join(engine_text.split())
            gbg_spaced = ' '.join(gbg_text.split())
            if engine_spaced == gbg_spaced:
                issues.append("SPACING_DIFFERENCE")
            
            # Check case differences
            if engine_text.lower() == gbg_text.lower():
                issues.append("CASE_DIFFERENCE")
            
            if issues:
                print(f"🔧 **Fixable Issues**: {', '.join(issues)}")
            else:
                print(f"❌ **Genuine Content Difference** - needs manual review")
    
    # Find unmapped blocks
    mapped_engine_ids = {assoc['engine_block_id'] for assoc in associations}
    all_engine_blocks = [b for b in pymupdf_data['blocks'] if b.get('text', '').strip()]
    unmapped_blocks = [b for b in all_engine_blocks if b['block_id'] not in mapped_engine_ids]
    
    print(f"\n🔍 **27 Unmapped Blocks (Need Combination Matching):**")
    print("=" * 80)
    
    # Group by page
    unmapped_by_page = {}
    for block in unmapped_blocks:
        page = block.get('page', 0)
        if page not in unmapped_by_page:
            unmapped_by_page[page] = []
        unmapped_by_page[page].append(block)
    
    for page, blocks in unmapped_by_page.items():
        print(f"\n**Page {page}: {len(blocks)} unmapped blocks**")
        
        # Show all blocks on this page
        for i, block in enumerate(blocks, 1):
            text = block.get('text', '').strip()
            bbox = block.get('bbox', [])
            print(f"  {i:2d}. \"{text}\" (ID: {block['block_id']})")
            if bbox and len(bbox) >= 4:
                print(f"      BBox: [{bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f}]")
        
        # Show GBG blocks on this page for comparison
        if str(page) in gbg_data['pages']:
            gbg_blocks = [b for b in gbg_data['pages'][str(page)]['blocks'] 
                         if b.get('text_content', '').strip()]
            print(f"\n  **GBG blocks on page {page} ({len(gbg_blocks)} blocks):**")
            for i, block in enumerate(gbg_blocks, 1):
                text = block.get('text_content', '').strip()[:50]
                print(f"    {i}. \"{text}{'...' if len(block.get('text_content', '')) > 50 else ''}\"")
                print(f"       ID: {block['block_id']}")
        
        print()
    
    print(f"💡 **Dynamic Alignment Strategy Needed:**")
    print(f"1. **Character Combination**: Combine single chars (U,T,A,H) → 'UTAH'")
    print(f"2. **Spatial Grouping**: Group spatially close blocks into logical units")
    print(f"3. **Grammar Correction**: Handle punctuation differences (. vs , vs : vs ;)")
    print(f"4. **Content Reconstruction**: Find partial matches and reconstruct missing parts")
    print(f"5. **Fixable Discrepancy Tracking**: Mark grammar/punctuation issues for correction")

if __name__ == "__main__":
    show_remaining_issues()
# src/compareblocks/gbg/processor.py
"""
Complete Global Block Grid (GBG) processor for full PDF analysis.
Implements deterministic PDF page segmentation with stable IDs and orientation detection.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from .seed import SeedBlockDetector, PDFPageAnalyzer
from .orientation import OrientationDetector
from .types import SeedBlock, OrientationHints
from ..config.file_manager import file_manager
from ..io.pdf_metadata import PDFMetadataExtractor


class GBGProcessor:
    """Complete Global Block Grid processor for PDF analysis."""
    
    def __init__(self):
        """Initialize the GBG processor with all required components."""
        self.seed_detector = SeedBlockDetector()
        self.orientation_detector = OrientationDetector()
        self.pdf_metadata_extractor = PDFMetadataExtractor()
        # Ensure output directories exist
        file_manager.ensure_output_directories()
    
    def process_pdf(self, pdf_path: Optional[str] = None, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Process entire PDF through complete GBG pipeline.
        
        Args:
            pdf_path: Path to PDF file (defaults to configured target PDF)
            output_path: Optional path to save results JSON (defaults to configured output path)
            
        Returns:
            Complete GBG analysis results
        """
        # Use configured paths if not provided
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        if output_path is None:
            output_path = file_manager.get_gbg_analysis_output_path()
            
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"Processing PDF: {pdf_path}")
        
        # Extract proper PDF metadata
        pdf_metadata = self.pdf_metadata_extractor.extract_pdf_metadata(str(pdf_path))
        
        # Initialize results structure with proper metadata
        results = {
            "pdf_path": str(pdf_path),
            "pdf_name": Path(pdf_path).name,
            "pdf_display_name": self.pdf_metadata_extractor.get_display_name(str(pdf_path)),
            "pdf_metadata": pdf_metadata,
            "processing_metadata": {
                "gbg_version": "1.0.0",
                "components": ["seed_detection", "orientation_analysis", "stable_ids"],
                "encoding": file_manager.get_default_encoding(),
                "validation_enabled": file_manager.is_validation_enabled()
            },
            "pages": {},
            "summary": {}
        }
        
        # Determine total pages
        total_pages = self._get_total_pages(str(pdf_path))
        print(f"Total pages: {total_pages}")
        
        all_blocks = []
        page_summaries = []
        
        # Process each page
        for page_num in range(total_pages):
            print(f"Processing page {page_num + 1}/{total_pages}")
            
            try:
                page_result = self.process_page(str(pdf_path), page_num)
                results["pages"][str(page_num)] = page_result
                
                # Collect blocks for summary
                all_blocks.extend(page_result["blocks"])
                page_summaries.append({
                    "page": page_num,
                    "block_count": len(page_result["blocks"]),
                    "has_text": page_result["page_info"]["has_text"],
                    "dimensions": f"{page_result['page_info']['width']}x{page_result['page_info']['height']}"
                })
                
            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
                results["pages"][str(page_num)] = {
                    "error": str(e),
                    "page_info": None,
                    "blocks": []
                }
        
        # Generate summary statistics
        results["summary"] = self._generate_summary(all_blocks, page_summaries, total_pages)
        
        # Save results if output path provided
        if output_path:
            self._save_results(results, output_path)
            print(f"Results saved to: {output_path}")
        
        return results
    
    def process_page(self, pdf_path: str, page_num: int) -> Dict[str, Any]:
        """
        Process single page through complete GBG pipeline.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            
        Returns:
            Complete page analysis results
        """
        # Get page information
        page_info = PDFPageAnalyzer.get_page_info(pdf_path, page_num)
        
        # Extract seed blocks
        blocks = self.seed_detector.extract_seed_blocks(pdf_path, page_num)
        
        # Convert blocks to serializable format
        serializable_blocks = []
        for block in blocks:
            block_data = {
                "block_id": block.block_id,
                "page": block.page,
                "bbox": {
                    "x": block.bbox.x,
                    "y": block.bbox.y,
                    "width": block.bbox.width,
                    "height": block.bbox.height,
                    "area": block.bbox.area(),
                    "center": block.bbox.center(),
                    "normalized": asdict(block.bbox.normalize_coordinates(
                        page_info["width"], page_info["height"]
                    ))
                },
                "orientation_hints": asdict(block.orientation_hints),
                "text_content": block.text_content,
                "text_length": len(block.text_content) if block.text_content else 0,
                "metadata": block.metadata or {},
                "geometric_analysis": self._analyze_block_geometry(block, page_info)
            }
            serializable_blocks.append(block_data)
        
        return {
            "page_info": page_info,
            "blocks": serializable_blocks,
            "block_count": len(blocks),
            "processing_timestamp": self._get_timestamp()
        }
    
    def _analyze_block_geometry(self, block: SeedBlock, page_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze geometric properties of a block."""
        aspect_ratio = block.bbox.width / block.bbox.height if block.bbox.height > 0 else float('inf')
        
        # Classify block type
        if aspect_ratio > 3.0:
            block_type = "horizontal_text"
        elif aspect_ratio < 0.33:
            block_type = "vertical_text"
        else:
            block_type = "square_mixed"
        
        # Position analysis
        center_x, center_y = block.bbox.center()
        rel_x = center_x / page_info['width']
        rel_y = center_y / page_info['height']
        
        # Determine position
        if rel_x < 0.33:
            h_pos = "left"
        elif rel_x > 0.67:
            h_pos = "right"
        else:
            h_pos = "center"
            
        if rel_y < 0.33:
            v_pos = "top"
        elif rel_y > 0.67:
            v_pos = "bottom"
        else:
            v_pos = "middle"
        
        return {
            "aspect_ratio": aspect_ratio,
            "block_type": block_type,
            "position": f"{v_pos}_{h_pos}",
            "relative_position": {"x": rel_x, "y": rel_y},
            "size_category": self._categorize_size(block.bbox.area())
        }
    
    def _categorize_size(self, area: float) -> str:
        """Categorize block size."""
        if area < 1000:
            return "small"
        elif area < 10000:
            return "medium"
        else:
            return "large"
    
    def _generate_summary(self, all_blocks: List[Dict], page_summaries: List[Dict], total_pages: int) -> Dict[str, Any]:
        """Generate summary statistics for the entire PDF."""
        if not all_blocks:
            return {"error": "No blocks found in PDF"}
        
        # Block type analysis
        horizontal_count = sum(1 for b in all_blocks if b["geometric_analysis"]["block_type"] == "horizontal_text")
        vertical_count = sum(1 for b in all_blocks if b["geometric_analysis"]["block_type"] == "vertical_text")
        square_count = sum(1 for b in all_blocks if b["geometric_analysis"]["block_type"] == "square_mixed")
        
        # Orientation analysis
        orientations = [b["orientation_hints"]["page_rotation"] for b in all_blocks]
        unique_orientations = list(set(orientations))
        
        # Confidence analysis
        confidences = [b["orientation_hints"]["confidence"] for b in all_blocks]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Size analysis
        areas = [b["bbox"]["area"] for b in all_blocks]
        avg_area = sum(areas) / len(areas) if areas else 0
        
        # Text analysis
        text_blocks = [b for b in all_blocks if b["text_content"]]
        total_text_length = sum(b["text_length"] for b in text_blocks)
        
        return {
            "total_pages": total_pages,
            "total_blocks": len(all_blocks),
            "blocks_with_text": len(text_blocks),
            "total_text_characters": total_text_length,
            "block_classification": {
                "horizontal": horizontal_count,
                "vertical": vertical_count,
                "square_mixed": square_count,
                "percentages": {
                    "horizontal": (horizontal_count / len(all_blocks)) * 100,
                    "vertical": (vertical_count / len(all_blocks)) * 100,
                    "square_mixed": (square_count / len(all_blocks)) * 100
                }
            },
            "orientation_analysis": {
                "unique_rotations": unique_orientations,
                "average_confidence": avg_confidence,
                "confidence_range": [min(confidences), max(confidences)] if confidences else [0, 0]
            },
            "geometric_analysis": {
                "average_block_area": avg_area,
                "area_range": [min(areas), max(areas)] if areas else [0, 0]
            },
            "page_summaries": page_summaries
        }
    
    def _get_total_pages(self, pdf_path: str) -> int:
        """Get total number of pages in PDF."""
        try:
            # Try to get page info for increasingly higher page numbers
            page_num = 0
            while True:
                try:
                    PDFPageAnalyzer.get_page_info(pdf_path, page_num)
                    page_num += 1
                except:
                    return page_num
        except:
            return 1
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _save_results(self, results: Dict[str, Any], output_path: str) -> None:
        """Save results to JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        encoding = file_manager.get_default_encoding()
        with open(output_path, 'w', encoding=encoding) as f:
            json.dump(results, f, indent=2, ensure_ascii=False)


def main():
    """Main function for command-line usage."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.compareblocks.gbg.processor <pdf_path> [output_path]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    processor = GBGProcessor()
    results = processor.process_pdf(pdf_path, output_path)
    
    # Print summary
    summary = results.get("summary", {})
    print(f"\nProcessing Complete!")
    print(f"Total pages: {summary.get('total_pages', 0)}")
    print(f"Total blocks: {summary.get('total_blocks', 0)}")
    print(f"Blocks with text: {summary.get('blocks_with_text', 0)}")


if __name__ == "__main__":
    main()
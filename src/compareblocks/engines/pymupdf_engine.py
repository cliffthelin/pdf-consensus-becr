# src/compareblocks/engines/pymupdf_engine.py
"""
Raw PyMuPDF extraction engine for direct PDF text extraction.
Provides unprocessed PyMuPDF output before GBG processing.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF

from ..io.pdf_metadata import PDFMetadataExtractor
from ..config.file_manager import file_manager


@dataclass
class PyMuPDFBlock:
    """Raw PyMuPDF block data."""
    block_id: int
    block_type: int
    bbox: List[float]  # [x0, y0, x1, y1]
    text: str
    font_info: Optional[Dict[str, Any]] = None
    flags: Optional[int] = None


@dataclass
class PyMuPDFPage:
    """Raw PyMuPDF page data."""
    page_number: int
    width: float
    height: float
    rotation: int
    blocks: List[PyMuPDFBlock]
    metadata: Dict[str, Any]


class PyMuPDFEngine:
    """Raw PyMuPDF extraction engine."""
    
    def __init__(self):
        """Initialize PyMuPDF engine."""
        self.metadata_extractor = PDFMetadataExtractor()
    
    def extract_pdf(self, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract raw PyMuPDF data from PDF.
        
        Args:
            pdf_path: Path to PDF file (defaults to configured target PDF)
            
        Returns:
            Raw PyMuPDF extraction results
        """
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"Extracting raw PyMuPDF data from: {pdf_path}")
        
        # Extract PDF metadata
        pdf_metadata = self.metadata_extractor.extract_pdf_metadata(str(pdf_path))
        display_name = self.metadata_extractor.get_display_name(str(pdf_path))
        
        # Open PDF document
        doc = fitz.open(str(pdf_path))
        
        try:
            # Initialize results structure
            results = {
                "engine": "pymupdf",
                "engine_version": fitz.version[0],
                "pdf_path": pdf_metadata["file_info"]["relative_path"],
                "pdf_name": pdf_metadata["file_info"]["normalized_filename"],
                "pdf_display_name": display_name,
                "pdf_metadata": pdf_metadata,
                "extraction_metadata": {
                    "total_pages": len(doc),
                    "extraction_type": "raw_pymupdf",
                    "processing_notes": "Unprocessed PyMuPDF output before GBG analysis"
                },
                "pages": {},
                "summary": {}
            }
            
            all_blocks = []
            page_summaries = []
            
            # Process each page
            for page_num in range(len(doc)):
                print(f"Extracting page {page_num + 1}/{len(doc)}")
                
                page = doc[page_num]
                page_data = self._extract_page_data(page, page_num)
                
                results["pages"][str(page_num)] = asdict(page_data)
                
                # Collect blocks for summary
                all_blocks.extend(page_data.blocks)
                page_summaries.append({
                    "page": page_num,
                    "block_count": len(page_data.blocks),
                    "text_blocks": len([b for b in page_data.blocks if b.text.strip()]),
                    "dimensions": f"{page_data.width}x{page_data.height}"
                })
            
            # Generate summary
            results["summary"] = self._generate_summary(all_blocks, page_summaries, len(doc))
            
            return results
            
        finally:
            doc.close()
    
    def _extract_page_data(self, page: fitz.Page, page_num: int) -> PyMuPDFPage:
        """Extract raw data from a single page."""
        # Get page dimensions
        rect = page.rect
        
        # Get page blocks
        blocks = []
        page_dict = page.get_text("dict")
        
        block_id = 0
        for block in page_dict.get("blocks", []):
            if "lines" in block:  # Text block
                # Extract text from lines
                text_parts = []
                font_info = {}
                
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        text_parts.append(span.get("text", ""))
                        
                        # Collect font information
                        if not font_info:
                            font_info = {
                                "font": span.get("font", ""),
                                "size": span.get("size", 0),
                                "flags": span.get("flags", 0),
                                "color": span.get("color", 0)
                            }
                
                text = "".join(text_parts)
                bbox = block.get("bbox", [0, 0, 0, 0])
                
                pymupdf_block = PyMuPDFBlock(
                    block_id=block_id,
                    block_type=block.get("type", 0),
                    bbox=bbox,
                    text=text,
                    font_info=font_info,
                    flags=block.get("flags", 0)
                )
                
                blocks.append(pymupdf_block)
                block_id += 1
            
            elif "image" in block:  # Image block
                bbox = block.get("bbox", [0, 0, 0, 0])
                
                pymupdf_block = PyMuPDFBlock(
                    block_id=block_id,
                    block_type=1,  # Image type
                    bbox=bbox,
                    text="[IMAGE]",
                    font_info=None,
                    flags=None
                )
                
                blocks.append(pymupdf_block)
                block_id += 1
        
        return PyMuPDFPage(
            page_number=page_num,
            width=rect.width,
            height=rect.height,
            rotation=page.rotation,
            blocks=blocks,
            metadata={
                "page_rect": [rect.x0, rect.y0, rect.x1, rect.y1],
                "mediabox": list(page.mediabox),
                "cropbox": list(page.cropbox) if hasattr(page, 'cropbox') else None
            }
        )
    
    def _generate_summary(self, all_blocks: List[PyMuPDFBlock], 
                         page_summaries: List[Dict], total_pages: int) -> Dict[str, Any]:
        """Generate extraction summary."""
        text_blocks = [b for b in all_blocks if b.text.strip()]
        image_blocks = [b for b in all_blocks if b.block_type == 1]
        
        total_characters = sum(len(b.text) for b in text_blocks)
        
        return {
            "total_pages": total_pages,
            "total_blocks": len(all_blocks),
            "text_blocks": len(text_blocks),
            "image_blocks": len(image_blocks),
            "total_characters": total_characters,
            "average_blocks_per_page": len(all_blocks) / total_pages if total_pages > 0 else 0,
            "pages_with_text": len([p for p in page_summaries if p["text_blocks"] > 0]),
            "extraction_engine": "PyMuPDF",
            "processing_type": "raw_extraction"
        }
    
    def save_extraction(self, pdf_path: Optional[str] = None, 
                       output_path: Optional[str] = None) -> str:
        """
        Extract and save raw PyMuPDF data.
        
        Args:
            pdf_path: Path to PDF file
            output_path: Path to save results
            
        Returns:
            Path to saved file
        """
        # Extract data
        results = self.extract_pdf(pdf_path)
        
        # Determine output path
        if output_path is None:
            # Create filename based on PDF display name
            display_name = results["pdf_display_name"]
            filename = f"{display_name}_pymupdf.json"
            
            # Save to processing directory
            processing_dir = Path(file_manager.get_processing_directory())
            output_path = processing_dir / filename
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Raw PyMuPDF extraction saved to: {output_path}")
        return str(output_path)


# Convenience functions
def extract_raw_pymupdf(pdf_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract raw PyMuPDF data from PDF."""
    engine = PyMuPDFEngine()
    return engine.extract_pdf(pdf_path)


def save_raw_pymupdf_extraction(pdf_path: Optional[str] = None, 
                               output_path: Optional[str] = None) -> str:
    """Extract and save raw PyMuPDF data."""
    engine = PyMuPDFEngine()
    return engine.save_extraction(pdf_path, output_path)
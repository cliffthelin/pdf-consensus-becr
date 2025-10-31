# src/compareblocks/engines/tesseract_engine.py
"""
Tesseract OCR engine for PDF text extraction.
Provides OCR-based text extraction using Tesseract.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF for PDF to image conversion

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from ..io.pdf_metadata import PDFMetadataExtractor
from ..config.file_manager import file_manager


@dataclass
class TesseractBlock:
    """Tesseract OCR block data."""
    block_id: str
    bbox: List[float]  # [x0, y0, x1, y1]
    text: str
    confidence: float
    word_count: int


@dataclass
class TesseractPage:
    """Tesseract OCR page data."""
    page_number: int
    width: float
    height: float
    blocks: List[TesseractBlock]
    ocr_confidence: float
    metadata: Dict[str, Any]


class TesseractEngine:
    """Tesseract OCR extraction engine."""
    
    def __init__(self, dpi: int = 300, lang: str = 'eng'):
        """
        Initialize Tesseract engine.
        
        Args:
            dpi: DPI for PDF to image conversion
            lang: Tesseract language code
        """
        self.dpi = dpi
        self.lang = lang
        self.metadata_extractor = PDFMetadataExtractor()
        
        if not TESSERACT_AVAILABLE:
            print("Warning: Tesseract dependencies not available. Install with: pip install pytesseract pillow")
    
    def is_available(self) -> bool:
        """Check if Tesseract is available."""
        if not TESSERACT_AVAILABLE:
            return False
        
        try:
            # Check if tesseract executable is available
            subprocess.run(['tesseract', '--version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def extract_pdf(self, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from PDF using Tesseract OCR.
        
        Args:
            pdf_path: Path to PDF file (defaults to configured target PDF)
            
        Returns:
            Tesseract OCR extraction results
        """
        if not self.is_available():
            return {
                "error": "Tesseract OCR not available",
                "message": "Install tesseract and pytesseract to use OCR extraction"
            }
        
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"Extracting text using Tesseract OCR from: {pdf_path}")
        
        # Extract PDF metadata
        pdf_metadata = self.metadata_extractor.extract_pdf_metadata(str(pdf_path))
        display_name = self.metadata_extractor.get_display_name(str(pdf_path))
        
        # Open PDF document
        doc = fitz.open(str(pdf_path))
        
        try:
            # Initialize results structure
            results = {
                "engine": "tesseract",
                "engine_version": self._get_tesseract_version(),
                "pdf_path": pdf_metadata["file_info"]["relative_path"],
                "pdf_name": pdf_metadata["file_info"]["normalized_filename"],
                "pdf_display_name": display_name,
                "pdf_metadata": pdf_metadata,
                "extraction_metadata": {
                    "total_pages": len(doc),
                    "extraction_type": "tesseract_ocr",
                    "dpi": self.dpi,
                    "language": self.lang,
                    "processing_notes": "OCR-based text extraction using Tesseract"
                },
                "pages": {},
                "summary": {}
            }
            
            all_blocks = []
            page_summaries = []
            
            # Process each page
            for page_num in range(len(doc)):
                print(f"OCR processing page {page_num + 1}/{len(doc)}")
                
                page = doc[page_num]
                page_data = self._extract_page_ocr(page, page_num)
                
                results["pages"][str(page_num)] = asdict(page_data)
                
                # Collect blocks for summary
                all_blocks.extend(page_data.blocks)
                page_summaries.append({
                    "page": page_num,
                    "block_count": len(page_data.blocks),
                    "text_blocks": len([b for b in page_data.blocks if b.text.strip()]),
                    "avg_confidence": page_data.ocr_confidence
                })
            
            # Generate summary
            results["summary"] = self._generate_summary(all_blocks, page_summaries, len(doc))
            
            return results
            
        finally:
            doc.close()
    
    def _extract_page_ocr(self, page: fitz.Page, page_num: int) -> TesseractPage:
        """Extract OCR data from a single page."""
        # Convert page to image
        mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)  # Scale for DPI
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("ppm")
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(img_data))
        
        # Perform OCR with detailed data
        ocr_data = pytesseract.image_to_data(
            image, 
            lang=self.lang,
            output_type=pytesseract.Output.DICT
        )
        
        # Process OCR results into blocks
        blocks = []
        current_block_words = []
        current_block_bbox = None
        block_id = 0
        
        confidences = []
        
        for i in range(len(ocr_data['text'])):
            confidence = int(ocr_data['conf'][i])
            text = ocr_data['text'][i].strip()
            
            if confidence > 0 and text:  # Valid text detection
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                
                # Scale coordinates back to PDF coordinates
                scale_factor = 72 / self.dpi
                bbox = [x * scale_factor, y * scale_factor, 
                       (x + w) * scale_factor, (y + h) * scale_factor]
                
                current_block_words.append({
                    'text': text,
                    'bbox': bbox,
                    'confidence': confidence
                })
                confidences.append(confidence)
                
                # Group words into blocks (simple approach: by line)
                if ocr_data['block_num'][i] != ocr_data.get('block_num', [0])[i-1] if i > 0 else False:
                    if current_block_words:
                        # Create block from accumulated words
                        block_text = ' '.join([w['text'] for w in current_block_words])
                        
                        # Calculate block bounding box
                        min_x = min(w['bbox'][0] for w in current_block_words)
                        min_y = min(w['bbox'][1] for w in current_block_words)
                        max_x = max(w['bbox'][2] for w in current_block_words)
                        max_y = max(w['bbox'][3] for w in current_block_words)
                        
                        block_bbox = [min_x, min_y, max_x, max_y]
                        block_confidence = sum(w['confidence'] for w in current_block_words) / len(current_block_words)
                        
                        tesseract_block = TesseractBlock(
                            block_id=f"ocr_block_{block_id}",
                            bbox=block_bbox,
                            text=block_text,
                            confidence=block_confidence,
                            word_count=len(current_block_words)
                        )
                        
                        blocks.append(tesseract_block)
                        block_id += 1
                        current_block_words = []
        
        # Handle final block
        if current_block_words:
            block_text = ' '.join([w['text'] for w in current_block_words])
            
            min_x = min(w['bbox'][0] for w in current_block_words)
            min_y = min(w['bbox'][1] for w in current_block_words)
            max_x = max(w['bbox'][2] for w in current_block_words)
            max_y = max(w['bbox'][3] for w in current_block_words)
            
            block_bbox = [min_x, min_y, max_x, max_y]
            block_confidence = sum(w['confidence'] for w in current_block_words) / len(current_block_words)
            
            tesseract_block = TesseractBlock(
                block_id=f"ocr_block_{block_id}",
                bbox=block_bbox,
                text=block_text,
                confidence=block_confidence,
                word_count=len(current_block_words)
            )
            
            blocks.append(tesseract_block)
        
        # Calculate page confidence
        page_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        rect = page.rect
        return TesseractPage(
            page_number=page_num,
            width=rect.width,
            height=rect.height,
            blocks=blocks,
            ocr_confidence=page_confidence,
            metadata={
                "dpi": self.dpi,
                "language": self.lang,
                "total_words": len([w for w in ocr_data['text'] if w.strip()]),
                "avg_word_confidence": page_confidence
            }
        )
    
    def _get_tesseract_version(self) -> str:
        """Get Tesseract version."""
        try:
            result = subprocess.run(['tesseract', '--version'], 
                                  capture_output=True, text=True)
            return result.stdout.split('\n')[0] if result.stdout else "unknown"
        except:
            return "unknown"
    
    def _generate_summary(self, all_blocks: List[TesseractBlock], 
                         page_summaries: List[Dict], total_pages: int) -> Dict[str, Any]:
        """Generate OCR extraction summary."""
        text_blocks = [b for b in all_blocks if b.text.strip()]
        
        total_characters = sum(len(b.text) for b in text_blocks)
        total_words = sum(b.word_count for b in text_blocks)
        avg_confidence = sum(b.confidence for b in text_blocks) / len(text_blocks) if text_blocks else 0
        
        return {
            "total_pages": total_pages,
            "total_blocks": len(all_blocks),
            "text_blocks": len(text_blocks),
            "total_characters": total_characters,
            "total_words": total_words,
            "average_confidence": avg_confidence,
            "average_blocks_per_page": len(all_blocks) / total_pages if total_pages > 0 else 0,
            "pages_with_text": len([p for p in page_summaries if p["text_blocks"] > 0]),
            "extraction_engine": "Tesseract OCR",
            "processing_type": "ocr_extraction",
            "dpi": self.dpi,
            "language": self.lang
        }
    
    def save_extraction(self, pdf_path: Optional[str] = None, 
                       output_path: Optional[str] = None) -> str:
        """
        Extract and save Tesseract OCR data.
        
        Args:
            pdf_path: Path to PDF file
            output_path: Path to save results
            
        Returns:
            Path to saved file
        """
        # Extract data
        results = self.extract_pdf(pdf_path)
        
        # Check for errors
        if "error" in results:
            print(f"Tesseract extraction failed: {results['error']}")
            return ""
        
        # Determine output path
        if output_path is None:
            # Create filename based on PDF display name
            display_name = results["pdf_display_name"]
            filename = f"{display_name}_tesseract.json"
            
            # Save to processing directory
            processing_dir = Path(file_manager.get_processing_directory())
            output_path = processing_dir / filename
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Tesseract OCR extraction saved to: {output_path}")
        return str(output_path)


# Add missing import
import io


# Convenience functions
def extract_tesseract_ocr(pdf_path: Optional[str] = None, 
                         dpi: int = 300, lang: str = 'eng') -> Dict[str, Any]:
    """Extract text using Tesseract OCR."""
    engine = TesseractEngine(dpi=dpi, lang=lang)
    return engine.extract_pdf(pdf_path)


def save_tesseract_extraction(pdf_path: Optional[str] = None, 
                             output_path: Optional[str] = None,
                             dpi: int = 300, lang: str = 'eng') -> str:
    """Extract and save Tesseract OCR data."""
    engine = TesseractEngine(dpi=dpi, lang=lang)
    return engine.save_extraction(pdf_path, output_path)
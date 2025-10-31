# src/compareblocks/engines/paddleocr_engine.py
"""
PaddleOCR engine for PDF text extraction.
Provides OCR-based text extraction using PaddleOCR.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF for PDF to image conversion
import numpy as np

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

from ..io.pdf_metadata import PDFMetadataExtractor
from ..config.file_manager import file_manager


@dataclass
class PaddleOCRBlock:
    """PaddleOCR block data."""
    block_id: str
    bbox: List[float]  # [x0, y0, x1, y1]
    text: str
    confidence: float
    detection_box: List[List[float]]  # Original detection polygon


@dataclass
class PaddleOCRPage:
    """PaddleOCR page data."""
    page_number: int
    width: float
    height: float
    blocks: List[PaddleOCRBlock]
    avg_confidence: float
    metadata: Dict[str, Any]


class PaddleOCREngine:
    """PaddleOCR extraction engine."""
    
    def __init__(self, lang: str = 'en', use_gpu: bool = False):
        """
        Initialize PaddleOCR engine.
        
        Args:
            lang: Language code for OCR
            use_gpu: Whether to use GPU acceleration
        """
        self.lang = lang
        self.use_gpu = use_gpu
        self.metadata_extractor = PDFMetadataExtractor()
        self._ocr_engine = None
        
        if not PADDLEOCR_AVAILABLE:
            print("Warning: PaddleOCR not available. Install with: pip install paddleocr")
    
    def _get_ocr_engine(self):
        """Get or create PaddleOCR engine instance."""
        if self._ocr_engine is None and PADDLEOCR_AVAILABLE:
            try:
                self._ocr_engine = PaddleOCR(
                    use_angle_cls=True, 
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False
                )
            except Exception as e:
                print(f"Failed to initialize PaddleOCR: {e}")
                return None
        return self._ocr_engine
    
    def is_available(self) -> bool:
        """Check if PaddleOCR is available."""
        if not PADDLEOCR_AVAILABLE:
            return False
        
        try:
            ocr = self._get_ocr_engine()
            return ocr is not None
        except Exception:
            return False
    
    def extract_pdf(self, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from PDF using PaddleOCR.
        
        Args:
            pdf_path: Path to PDF file (defaults to configured target PDF)
            
        Returns:
            PaddleOCR extraction results
        """
        if not self.is_available():
            return {
                "error": "PaddleOCR not available",
                "message": "Install paddleocr to use PaddleOCR extraction"
            }
        
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"Extracting text using PaddleOCR from: {pdf_path}")
        
        # Extract PDF metadata
        pdf_metadata = self.metadata_extractor.extract_pdf_metadata(str(pdf_path))
        display_name = self.metadata_extractor.get_display_name(str(pdf_path))
        
        # Open PDF document
        doc = fitz.open(str(pdf_path))
        
        try:
            # Initialize results structure
            results = {
                "engine": "paddleocr",
                "engine_version": self._get_paddleocr_version(),
                "pdf_path": pdf_metadata["file_info"]["relative_path"],
                "pdf_name": pdf_metadata["file_info"]["normalized_filename"],
                "pdf_display_name": display_name,
                "pdf_metadata": pdf_metadata,
                "extraction_metadata": {
                    "total_pages": len(doc),
                    "extraction_type": "paddleocr",
                    "language": self.lang,
                    "use_gpu": self.use_gpu,
                    "processing_notes": "OCR-based text extraction using PaddleOCR"
                },
                "pages": {},
                "summary": {}
            }
            
            all_blocks = []
            page_summaries = []
            
            # Get OCR engine
            ocr = self._get_ocr_engine()
            if ocr is None:
                return {
                    "error": "Failed to initialize PaddleOCR engine"
                }
            
            # Process each page
            for page_num in range(len(doc)):
                print(f"PaddleOCR processing page {page_num + 1}/{len(doc)}")
                
                page = doc[page_num]
                page_data = self._extract_page_ocr(page, page_num, ocr)
                
                results["pages"][str(page_num)] = asdict(page_data)
                
                # Collect blocks for summary
                all_blocks.extend(page_data.blocks)
                page_summaries.append({
                    "page": page_num,
                    "block_count": len(page_data.blocks),
                    "text_blocks": len([b for b in page_data.blocks if b.text.strip()]),
                    "avg_confidence": page_data.avg_confidence
                })
            
            # Generate summary
            results["summary"] = self._generate_summary(all_blocks, page_summaries, len(doc))
            
            return results
            
        finally:
            doc.close()
    
    def _extract_page_ocr(self, page: fitz.Page, page_num: int, ocr) -> PaddleOCRPage:
        """Extract OCR data from a single page using PaddleOCR."""
        # Convert page to image
        mat = fitz.Matrix(2.0, 2.0)  # 2x scale for better OCR
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to numpy array for PaddleOCR
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        
        # Perform OCR
        try:
            ocr_results = ocr.ocr(img_array, cls=True)
        except Exception as e:
            print(f"PaddleOCR failed on page {page_num}: {e}")
            ocr_results = []
        
        # Process OCR results into blocks
        blocks = []
        confidences = []
        
        if ocr_results and ocr_results[0]:  # Check if results exist
            for idx, line in enumerate(ocr_results[0]):
                if line and len(line) >= 2:
                    detection_box = line[0]  # Polygon coordinates
                    text_info = line[1]
                    
                    if isinstance(text_info, tuple) and len(text_info) >= 2:
                        text = text_info[0]
                        confidence = text_info[1]
                    else:
                        text = str(text_info)
                        confidence = 0.5  # Default confidence
                    
                    if text and text.strip():
                        # Convert polygon to bounding box
                        bbox = self._polygon_to_bbox(detection_box)
                        
                        # Scale coordinates back to PDF coordinates
                        scale_factor = 0.5  # Inverse of 2x scale
                        scaled_bbox = [coord * scale_factor for coord in bbox]
                        scaled_detection_box = [[coord * scale_factor for coord in point] 
                                              for point in detection_box]
                        
                        paddle_block = PaddleOCRBlock(
                            block_id=f"paddle_block_{idx}",
                            bbox=scaled_bbox,
                            text=text.strip(),
                            confidence=float(confidence),
                            detection_box=scaled_detection_box
                        )
                        
                        blocks.append(paddle_block)
                        confidences.append(float(confidence))
        
        # Calculate page confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        rect = page.rect
        return PaddleOCRPage(
            page_number=page_num,
            width=rect.width,
            height=rect.height,
            blocks=blocks,
            avg_confidence=avg_confidence,
            metadata={
                "language": self.lang,
                "use_gpu": self.use_gpu,
                "total_detections": len(blocks),
                "avg_confidence": avg_confidence
            }
        )
    
    def _polygon_to_bbox(self, polygon: List[List[float]]) -> List[float]:
        """Convert polygon coordinates to bounding box."""
        if not polygon:
            return [0, 0, 0, 0]
        
        x_coords = [point[0] for point in polygon]
        y_coords = [point[1] for point in polygon]
        
        return [
            min(x_coords),  # x0
            min(y_coords),  # y0
            max(x_coords),  # x1
            max(y_coords)   # y1
        ]
    
    def _get_paddleocr_version(self) -> str:
        """Get PaddleOCR version."""
        try:
            import paddleocr
            return getattr(paddleocr, '__version__', 'unknown')
        except:
            return "unknown"
    
    def _generate_summary(self, all_blocks: List[PaddleOCRBlock], 
                         page_summaries: List[Dict], total_pages: int) -> Dict[str, Any]:
        """Generate PaddleOCR extraction summary."""
        text_blocks = [b for b in all_blocks if b.text.strip()]
        
        total_characters = sum(len(b.text) for b in text_blocks)
        avg_confidence = sum(b.confidence for b in text_blocks) / len(text_blocks) if text_blocks else 0
        
        return {
            "total_pages": total_pages,
            "total_blocks": len(all_blocks),
            "text_blocks": len(text_blocks),
            "total_characters": total_characters,
            "average_confidence": avg_confidence,
            "average_blocks_per_page": len(all_blocks) / total_pages if total_pages > 0 else 0,
            "pages_with_text": len([p for p in page_summaries if p["text_blocks"] > 0]),
            "extraction_engine": "PaddleOCR",
            "processing_type": "ocr_extraction",
            "language": self.lang,
            "use_gpu": self.use_gpu
        }
    
    def save_extraction(self, pdf_path: Optional[str] = None, 
                       output_path: Optional[str] = None) -> str:
        """
        Extract and save PaddleOCR data.
        
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
            print(f"PaddleOCR extraction failed: {results['error']}")
            return ""
        
        # Determine output path
        if output_path is None:
            # Create filename based on PDF display name
            display_name = results["pdf_display_name"]
            filename = f"{display_name}_paddleocr.json"
            
            # Save to processing directory
            processing_dir = Path(file_manager.get_processing_directory())
            output_path = processing_dir / filename
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"PaddleOCR extraction saved to: {output_path}")
        return str(output_path)


# Convenience functions
def extract_paddleocr(pdf_path: Optional[str] = None, 
                     lang: str = 'en', use_gpu: bool = False) -> Dict[str, Any]:
    """Extract text using PaddleOCR."""
    engine = PaddleOCREngine(lang=lang, use_gpu=use_gpu)
    return engine.extract_pdf(pdf_path)


def save_paddleocr_extraction(pdf_path: Optional[str] = None, 
                             output_path: Optional[str] = None,
                             lang: str = 'en', use_gpu: bool = False) -> str:
    """Extract and save PaddleOCR data."""
    engine = PaddleOCREngine(lang=lang, use_gpu=use_gpu)
    return engine.save_extraction(pdf_path, output_path)
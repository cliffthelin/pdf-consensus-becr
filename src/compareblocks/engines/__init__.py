# src/compareblocks/engines/__init__.py
"""
PDF extraction engines module.
Provides multiple engines for PDF text extraction including PyMuPDF, Tesseract, PaddleOCR, etc.
"""

from .pymupdf_engine import PyMuPDFEngine, extract_raw_pymupdf, save_raw_pymupdf_extraction
from .tesseract_engine import TesseractEngine, extract_tesseract_ocr, save_tesseract_extraction
from .paddleocr_engine import PaddleOCREngine, extract_paddleocr, save_paddleocr_extraction
from .kreuzberg_engine import KreuzbergEngine, extract_kreuzberg, save_kreuzberg_extraction
from .docling_engine import DoclingEngine, extract_docling, save_docling_extraction
from .manager import (
    ExtractionEngineManager, 
    EngineResult,
    extract_with_all_engines,
    extract_with_engines,
    get_available_engines
)
from .integrated_processor import (
    IntegratedEngineProcessor,
    IntegratedResult,
    BlockAlignment,
    process_pdf_with_integrated_engines,
    save_integrated_engine_processing
)
from .dual_output_processor import (
    DualOutputEngineProcessor,
    DualOutputResult,
    process_engine_dual_output,
    process_all_engines_dual_output
)
from .gbg_integrated_processor import (
    GBGIntegratedEngineProcessor,
    GBGIntegratedResult,
    process_engines_with_gbg_integration
)

__all__ = [
    # Engine classes
    'PyMuPDFEngine',
    'TesseractEngine', 
    'PaddleOCREngine',
    'KreuzbergEngine',
    'DoclingEngine',
    'ExtractionEngineManager',
    'IntegratedEngineProcessor',
    'DualOutputEngineProcessor',
    'GBGIntegratedEngineProcessor',
    
    # Data classes
    'EngineResult',
    'IntegratedResult',
    'BlockAlignment',
    'DualOutputResult',
    'GBGIntegratedResult',
    
    # Convenience functions
    'extract_raw_pymupdf',
    'save_raw_pymupdf_extraction',
    'extract_tesseract_ocr',
    'save_tesseract_extraction',
    'extract_paddleocr',
    'save_paddleocr_extraction',
    'extract_kreuzberg',
    'save_kreuzberg_extraction',
    'extract_docling',
    'save_docling_extraction',
    'extract_with_all_engines',
    'extract_with_engines',
    'get_available_engines',
    'process_pdf_with_integrated_engines',
    'save_integrated_engine_processing',
    'process_engine_dual_output',
    'process_all_engines_dual_output',
    'process_engines_with_gbg_integration'
]
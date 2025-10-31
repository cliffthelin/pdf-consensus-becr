# src/compareblocks/engines/manager.py
"""
Engine manager for coordinating multiple PDF extraction engines.
Manages PyMuPDF, Tesseract, PaddleOCR, and other extraction engines.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .pymupdf_engine import PyMuPDFEngine, save_raw_pymupdf_extraction
from .tesseract_engine import TesseractEngine, save_tesseract_extraction
from .paddleocr_engine import PaddleOCREngine, save_paddleocr_extraction
from .kreuzberg_engine import KreuzbergEngine, save_kreuzberg_extraction
from .docling_engine import DoclingEngine, save_docling_extraction
from .kreuzberg_engine import KreuzbergEngine, save_kreuzberg_extraction
from .docling_engine import DoclingEngine, save_docling_extraction
from ..io.pdf_metadata import PDFMetadataExtractor
from ..config.file_manager import file_manager


@dataclass
class EngineResult:
    """Result from a single extraction engine."""
    engine_name: str
    success: bool
    output_path: str
    extraction_time: float
    error_message: str = ""
    metadata: Dict[str, Any] = None


class ExtractionEngineManager:
    """Manages multiple PDF extraction engines."""
    
    def __init__(self):
        """Initialize the engine manager."""
        self.metadata_extractor = PDFMetadataExtractor()
        self.available_engines = self._detect_available_engines()
    
    def _detect_available_engines(self) -> Dict[str, bool]:
        """Detect which engines are available."""
        engines = {
            'pymupdf': True,  # Always available (required dependency)
            'tesseract': False,
            'paddleocr': False,
            'kreuzberg': False,
            'docling': False
        }
        
        # Check Tesseract
        try:
            tesseract_engine = TesseractEngine()
            engines['tesseract'] = tesseract_engine.is_available()
        except Exception:
            engines['tesseract'] = False
        
        # Check PaddleOCR
        try:
            paddleocr_engine = PaddleOCREngine()
            engines['paddleocr'] = paddleocr_engine.is_available()
        except Exception:
            engines['paddleocr'] = False
        
        # Check Kreuzberg
        try:
            kreuzberg_engine = KreuzbergEngine()
            engines['kreuzberg'] = kreuzberg_engine.is_available()
        except Exception:
            engines['kreuzberg'] = False
        
        # Check Docling
        try:
            docling_engine = DoclingEngine()
            engines['docling'] = docling_engine.is_available()
        except Exception:
            engines['docling'] = False
        
        return engines
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engine names."""
        return [name for name, available in self.available_engines.items() if available]
    
    def extract_with_engine(self, engine_name: str, pdf_path: Optional[str] = None) -> EngineResult:
        """
        Extract text using a specific engine.
        
        Args:
            engine_name: Name of the engine to use
            pdf_path: Path to PDF file
            
        Returns:
            EngineResult with extraction results
        """
        if engine_name not in self.available_engines:
            return EngineResult(
                engine_name=engine_name,
                success=False,
                output_path="",
                extraction_time=0,
                error_message=f"Unknown engine: {engine_name}"
            )
        
        if not self.available_engines[engine_name]:
            return EngineResult(
                engine_name=engine_name,
                success=False,
                output_path="",
                extraction_time=0,
                error_message=f"Engine not available: {engine_name}"
            )
        
        start_time = time.time()
        
        try:
            if engine_name == 'pymupdf':
                output_path = save_raw_pymupdf_extraction(pdf_path)
            elif engine_name == 'tesseract':
                output_path = save_tesseract_extraction(pdf_path)
            elif engine_name == 'paddleocr':
                output_path = save_paddleocr_extraction(pdf_path)
            elif engine_name == 'kreuzberg':
                output_path = save_kreuzberg_extraction(pdf_path)
            elif engine_name == 'docling':
                output_path = save_docling_extraction(pdf_path)
            else:
                raise ValueError(f"Unsupported engine: {engine_name}")
            
            extraction_time = time.time() - start_time
            
            # Load metadata from saved file
            metadata = None
            if output_path and Path(output_path).exists():
                try:
                    with open(output_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        metadata = data.get('summary', {})
                except Exception:
                    pass
            
            return EngineResult(
                engine_name=engine_name,
                success=bool(output_path),
                output_path=output_path,
                extraction_time=extraction_time,
                metadata=metadata
            )
            
        except Exception as e:
            extraction_time = time.time() - start_time
            return EngineResult(
                engine_name=engine_name,
                success=False,
                output_path="",
                extraction_time=extraction_time,
                error_message=str(e)
            )
    
    def extract_with_all_engines(self, pdf_path: Optional[str] = None, 
                                parallel: bool = True) -> Dict[str, EngineResult]:
        """
        Extract text using all available engines.
        
        Args:
            pdf_path: Path to PDF file
            parallel: Whether to run engines in parallel
            
        Returns:
            Dictionary of engine results
        """
        available_engines = self.get_available_engines()
        results = {}
        
        if not available_engines:
            print("No extraction engines available")
            return results
        
        print(f"Running extraction with engines: {available_engines}")
        
        if parallel and len(available_engines) > 1:
            # Run engines in parallel
            with ThreadPoolExecutor(max_workers=len(available_engines)) as executor:
                # Submit all extraction tasks
                future_to_engine = {
                    executor.submit(self.extract_with_engine, engine, pdf_path): engine
                    for engine in available_engines
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_engine):
                    engine = future_to_engine[future]
                    try:
                        result = future.result()
                        results[engine] = result
                        
                        if result.success:
                            print(f"✅ {engine}: {result.extraction_time:.1f}s -> {result.output_path}")
                        else:
                            print(f"❌ {engine}: {result.error_message}")
                            
                    except Exception as e:
                        results[engine] = EngineResult(
                            engine_name=engine,
                            success=False,
                            output_path="",
                            extraction_time=0,
                            error_message=f"Execution failed: {e}"
                        )
                        print(f"❌ {engine}: Execution failed: {e}")
        else:
            # Run engines sequentially
            for engine in available_engines:
                print(f"Running {engine}...")
                result = self.extract_with_engine(engine, pdf_path)
                results[engine] = result
                
                if result.success:
                    print(f"✅ {engine}: {result.extraction_time:.1f}s -> {result.output_path}")
                else:
                    print(f"❌ {engine}: {result.error_message}")
        
        return results
    
    def extract_with_engines(self, engine_names: List[str], 
                           pdf_path: Optional[str] = None,
                           parallel: bool = True) -> Dict[str, EngineResult]:
        """
        Extract text using specified engines.
        
        Args:
            engine_names: List of engine names to use
            pdf_path: Path to PDF file
            parallel: Whether to run engines in parallel
            
        Returns:
            Dictionary of engine results
        """
        # Filter to available engines
        available_engines = [name for name in engine_names 
                           if name in self.available_engines and self.available_engines[name]]
        
        if not available_engines:
            print(f"None of the requested engines are available: {engine_names}")
            return {}
        
        print(f"Running extraction with engines: {available_engines}")
        
        results = {}
        
        if parallel and len(available_engines) > 1:
            # Run engines in parallel
            with ThreadPoolExecutor(max_workers=len(available_engines)) as executor:
                future_to_engine = {
                    executor.submit(self.extract_with_engine, engine, pdf_path): engine
                    for engine in available_engines
                }
                
                for future in as_completed(future_to_engine):
                    engine = future_to_engine[future]
                    try:
                        result = future.result()
                        results[engine] = result
                        
                        if result.success:
                            print(f"✅ {engine}: {result.extraction_time:.1f}s")
                        else:
                            print(f"❌ {engine}: {result.error_message}")
                            
                    except Exception as e:
                        results[engine] = EngineResult(
                            engine_name=engine,
                            success=False,
                            output_path="",
                            extraction_time=0,
                            error_message=f"Execution failed: {e}"
                        )
        else:
            # Run engines sequentially
            for engine in available_engines:
                result = self.extract_with_engine(engine, pdf_path)
                results[engine] = result
                
                if result.success:
                    print(f"✅ {engine}: {result.extraction_time:.1f}s")
                else:
                    print(f"❌ {engine}: {result.error_message}")
        
        return results
    
    def create_extraction_summary(self, results: Dict[str, EngineResult], 
                                pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a summary of all extraction results.
        
        Args:
            results: Dictionary of engine results
            pdf_path: Path to PDF file
            
        Returns:
            Extraction summary
        """
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        # Get PDF metadata
        pdf_metadata = self.metadata_extractor.extract_pdf_metadata(pdf_path)
        display_name = self.metadata_extractor.get_display_name(pdf_path)
        
        # Analyze results
        successful_engines = [name for name, result in results.items() if result.success]
        failed_engines = [name for name, result in results.items() if not result.success]
        
        total_time = sum(result.extraction_time for result in results.values())
        
        # Create summary
        summary = {
            "pdf_path": pdf_metadata["file_info"]["relative_path"],
            "pdf_name": pdf_metadata["file_info"]["normalized_filename"],
            "pdf_display_name": display_name,
            "extraction_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "engines": {
                "requested": list(results.keys()),
                "successful": successful_engines,
                "failed": failed_engines,
                "available": self.get_available_engines()
            },
            "timing": {
                "total_time": total_time,
                "engine_times": {name: result.extraction_time for name, result in results.items()}
            },
            "output_files": {
                name: result.output_path for name, result in results.items() if result.success
            },
            "errors": {
                name: result.error_message for name, result in results.items() if not result.success
            },
            "engine_metadata": {
                name: result.metadata for name, result in results.items() 
                if result.success and result.metadata
            }
        }
        
        return summary
    
    def save_extraction_summary(self, results: Dict[str, EngineResult], 
                              pdf_path: Optional[str] = None,
                              output_path: Optional[str] = None) -> str:
        """
        Save extraction summary to file.
        
        Args:
            results: Dictionary of engine results
            pdf_path: Path to PDF file
            output_path: Path to save summary
            
        Returns:
            Path to saved summary file
        """
        summary = self.create_extraction_summary(results, pdf_path)
        
        # Determine output path
        if output_path is None:
            display_name = summary["pdf_display_name"]
            filename = f"{display_name}_extraction_summary.json"
            
            processing_dir = Path(file_manager.get_processing_directory())
            output_path = processing_dir / filename
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save summary
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"Extraction summary saved to: {output_path}")
        return str(output_path)


# Convenience functions
def extract_with_all_engines(pdf_path: Optional[str] = None, parallel: bool = True) -> Dict[str, EngineResult]:
    """Extract text using all available engines."""
    manager = ExtractionEngineManager()
    return manager.extract_with_all_engines(pdf_path, parallel)


def extract_with_engines(engine_names: List[str], pdf_path: Optional[str] = None, 
                        parallel: bool = True) -> Dict[str, EngineResult]:
    """Extract text using specified engines."""
    manager = ExtractionEngineManager()
    return manager.extract_with_engines(engine_names, pdf_path, parallel)


def get_available_engines() -> List[str]:
    """Get list of available extraction engines."""
    manager = ExtractionEngineManager()
    return manager.get_available_engines()
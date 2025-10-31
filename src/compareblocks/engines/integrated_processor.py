# src/compareblocks/engines/integrated_processor.py
"""
Integrated engine processor that runs PyMuPDF first to establish blocks,
then runs other engines and aligns their output to the established block structure.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import time

from .pymupdf_engine import PyMuPDFEngine
from .tesseract_engine import TesseractEngine
from .paddleocr_engine import PaddleOCREngine
from .kreuzberg_engine import KreuzbergEngine
from .docling_engine import DoclingEngine
from ..io.pdf_metadata import PDFMetadataExtractor
from ..config.file_manager import file_manager
from ..association.alignment import align_content_to_blocks


@dataclass
class BlockAlignment:
    """Alignment of engine output to established blocks."""
    block_id: str
    engine_name: str
    aligned_text: str
    confidence: float
    alignment_type: str
    original_engine_data: Dict[str, Any]


@dataclass
class IntegratedResult:
    """Result from integrated engine processing."""
    pdf_metadata: Dict[str, Any]
    established_blocks: List[Dict[str, Any]]
    engine_results: Dict[str, Dict[str, Any]]
    block_alignments: Dict[str, List[BlockAlignment]]
    processing_summary: Dict[str, Any]


class IntegratedEngineProcessor:
    """Processes PDF with PyMuPDF first, then aligns other engines to established blocks."""
    
    def __init__(self):
        """Initialize the integrated processor."""
        self.metadata_extractor = PDFMetadataExtractor()
        self.pymupdf_engine = PyMuPDFEngine()
        
        # Initialize other engines
        self.other_engines = {
            'tesseract': TesseractEngine(),
            'paddleocr': PaddleOCREngine(),
            'kreuzberg': KreuzbergEngine(),
            'docling': DoclingEngine()
        }
        
        # Check availability
        self.available_engines = self._check_engine_availability()
    
    def _check_engine_availability(self) -> Dict[str, bool]:
        """Check which engines are available."""
        availability = {'pymupdf': True}  # Always available
        
        for name, engine in self.other_engines.items():
            try:
                availability[name] = engine.is_available()
            except Exception:
                availability[name] = False
        
        return availability
    
    def process_pdf_integrated(self, pdf_path: Optional[str] = None) -> IntegratedResult:
        """
        Process PDF with integrated approach: PyMuPDF first, then align other engines.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            IntegratedResult with all engine outputs aligned to established blocks
        """
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"Starting integrated processing of: {pdf_path}")
        
        # Extract PDF metadata
        pdf_metadata = self.metadata_extractor.extract_pdf_metadata(str(pdf_path))
        
        # Step 1: Run PyMuPDF to establish blocks
        print("Step 1: Establishing blocks with PyMuPDF...")
        pymupdf_results = self.pymupdf_engine.extract_pdf(str(pdf_path))
        established_blocks = self._extract_blocks_from_pymupdf(pymupdf_results)
        
        print(f"Established {len(established_blocks)} blocks from PyMuPDF")
        
        # Step 2: Run other available engines
        engine_results = {'pymupdf': pymupdf_results}
        block_alignments = {}
        
        available_other_engines = [name for name, available in self.available_engines.items() 
                                 if available and name != 'pymupdf']
        
        if available_other_engines:
            print(f"Step 2: Running other engines: {available_other_engines}")
            
            for engine_name in available_other_engines:
                print(f"  Running {engine_name}...")
                
                try:
                    engine = self.other_engines[engine_name]
                    engine_result = engine.extract_pdf(str(pdf_path))
                    
                    if "error" not in engine_result:
                        engine_results[engine_name] = engine_result
                        
                        # Step 3: Align engine output to established blocks
                        alignments = self._align_engine_to_blocks(
                            engine_name, engine_result, established_blocks
                        )
                        block_alignments[engine_name] = alignments
                        
                        print(f"    ✅ {engine_name}: {len(alignments)} alignments created")
                    else:
                        print(f"    ❌ {engine_name}: {engine_result.get('error', 'Failed')}")
                        engine_results[engine_name] = engine_result
                        
                except Exception as e:
                    print(f"    ❌ {engine_name}: Exception - {e}")
                    engine_results[engine_name] = {"error": str(e)}
        else:
            print("Step 2: No other engines available")
        
        # Step 4: Create processing summary
        processing_summary = self._create_processing_summary(
            established_blocks, engine_results, block_alignments
        )
        
        return IntegratedResult(
            pdf_metadata=pdf_metadata,
            established_blocks=established_blocks,
            engine_results=engine_results,
            block_alignments=block_alignments,
            processing_summary=processing_summary
        )
    
    def _extract_blocks_from_pymupdf(self, pymupdf_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract block structure from PyMuPDF results."""
        blocks = []
        
        pages = pymupdf_results.get("pages", {})
        for page_num, page_data in pages.items():
            page_blocks = page_data.get("blocks", [])
            
            for block in page_blocks:
                if block.get("text", "").strip():  # Only blocks with text
                    block_info = {
                        "block_id": f"pymupdf_p{page_num}_b{block['block_id']}",
                        "page": int(page_num),
                        "text": block["text"],
                        "bbox": block["bbox"],
                        "source_engine": "pymupdf",
                        "block_type": "text"
                    }
                    blocks.append(block_info)
        
        return blocks
    
    def _align_engine_to_blocks(self, engine_name: str, engine_result: Dict[str, Any], 
                               established_blocks: List[Dict[str, Any]]) -> List[BlockAlignment]:
        """Align engine output to established blocks."""
        alignments = []
        
        # Extract text content from engine result
        engine_texts = self._extract_texts_from_engine_result(engine_name, engine_result)
        
        # Align each engine text to established blocks
        for engine_text_data in engine_texts:
            text_content = engine_text_data["text"]
            
            if text_content and text_content.strip():
                # Find best matching block
                best_matches = align_content_to_blocks(text_content, established_blocks, threshold=0.6)
                
                if best_matches:
                    best_match = best_matches[0]  # Take the best match
                    
                    alignment = BlockAlignment(
                        block_id=best_match.block_id,
                        engine_name=engine_name,
                        aligned_text=text_content,
                        confidence=best_match.confidence,
                        alignment_type=best_match.alignment_type,
                        original_engine_data=engine_text_data
                    )
                    alignments.append(alignment)
        
        return alignments
    
    def _extract_texts_from_engine_result(self, engine_name: str, 
                                        engine_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract text content from engine-specific result format."""
        texts = []
        
        if engine_name == 'tesseract':
            # Extract from Tesseract OCR format
            pages = engine_result.get("pages", {})
            for page_num, page_data in pages.items():
                blocks = page_data.get("blocks", [])
                for block in blocks:
                    if block.get("text", "").strip():
                        texts.append({
                            "text": block["text"],
                            "confidence": block.get("confidence", 0),
                            "bbox": block.get("bbox", []),
                            "page": page_num,
                            "engine_block_id": block.get("block_id", "")
                        })
        
        elif engine_name == 'paddleocr':
            # Extract from PaddleOCR format
            pages = engine_result.get("pages", {})
            for page_num, page_data in pages.items():
                blocks = page_data.get("blocks", [])
                for block in blocks:
                    if block.get("text", "").strip():
                        texts.append({
                            "text": block["text"],
                            "confidence": block.get("confidence", 0),
                            "bbox": block.get("bbox", []),
                            "page": page_num,
                            "engine_block_id": block.get("block_id", ""),
                            "detection_box": block.get("detection_box", [])
                        })
        
        elif engine_name == 'kreuzberg':
            # Extract from Kreuzberg format
            content = engine_result.get("content", {})
            blocks = content.get("blocks", [])
            for block in blocks:
                if block.get("text", "").strip():
                    texts.append({
                        "text": block["text"],
                        "confidence": block.get("confidence", 0.5),
                        "bbox": [],
                        "page": 0,  # Kreuzberg doesn't provide page info by default
                        "engine_block_id": block.get("block_id", ""),
                        "block_type": block.get("block_type", "paragraph")
                    })
        
        elif engine_name == 'docling':
            # Extract from Docling format
            content = engine_result.get("content", {})
            blocks = content.get("blocks", [])
            for block in blocks:
                if block.get("text", "").strip():
                    texts.append({
                        "text": block["text"],
                        "confidence": block.get("confidence", 0.5),
                        "bbox": block.get("bbox", []),
                        "page": block.get("page_number", 0),
                        "engine_block_id": block.get("block_id", ""),
                        "block_type": block.get("block_type", "unknown")
                    })
        
        return texts
    
    def _create_processing_summary(self, established_blocks: List[Dict[str, Any]], 
                                 engine_results: Dict[str, Dict[str, Any]],
                                 block_alignments: Dict[str, List[BlockAlignment]]) -> Dict[str, Any]:
        """Create summary of integrated processing."""
        
        # Count successful engines
        successful_engines = [name for name, result in engine_results.items() 
                            if "error" not in result]
        failed_engines = [name for name, result in engine_results.items() 
                         if "error" in result]
        
        # Count alignments
        total_alignments = sum(len(alignments) for alignments in block_alignments.values())
        
        # Calculate alignment statistics
        alignment_stats = {}
        for engine_name, alignments in block_alignments.items():
            if alignments:
                confidences = [a.confidence for a in alignments]
                alignment_stats[engine_name] = {
                    "total_alignments": len(alignments),
                    "avg_confidence": sum(confidences) / len(confidences),
                    "min_confidence": min(confidences),
                    "max_confidence": max(confidences)
                }
        
        return {
            "processing_type": "integrated_multi_engine",
            "established_blocks_count": len(established_blocks),
            "engines_processed": len(engine_results),
            "successful_engines": successful_engines,
            "failed_engines": failed_engines,
            "total_alignments": total_alignments,
            "alignment_statistics": alignment_stats,
            "blocks_with_alignments": len(set(
                alignment.block_id 
                for alignments in block_alignments.values() 
                for alignment in alignments
            )),
            "coverage_percentage": (len(set(
                alignment.block_id 
                for alignments in block_alignments.values() 
                for alignment in alignments
            )) / len(established_blocks) * 100) if established_blocks else 0
        }
    
    def save_integrated_results(self, result: IntegratedResult, 
                              output_path: Optional[str] = None) -> str:
        """
        Save integrated processing results.
        
        Args:
            result: IntegratedResult to save
            output_path: Path to save results
            
        Returns:
            Path to saved file
        """
        if output_path is None:
            # Create filename based on PDF display name
            display_name = self.metadata_extractor.get_display_name(
                result.pdf_metadata["file_info"]["original_path"]
            )
            filename = f"{display_name}_integrated_engines.json"
            
            # Save to processing directory
            processing_dir = Path(file_manager.get_processing_directory())
            output_path = processing_dir / filename
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        serializable_result = {
            "pdf_metadata": result.pdf_metadata,
            "established_blocks": result.established_blocks,
            "engine_results": result.engine_results,
            "block_alignments": {
                engine: [asdict(alignment) for alignment in alignments]
                for engine, alignments in result.block_alignments.items()
            },
            "processing_summary": result.processing_summary,
            "processing_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_result, f, indent=2, ensure_ascii=False)
        
        print(f"Integrated engine results saved to: {output_path}")
        return str(output_path)


    
    def process_integrated_workflow(self, pdf_path: Optional[str] = None) -> IntegratedResult:
        """Alias for process_pdf_integrated for backward compatibility."""
        return self.process_pdf_integrated(pdf_path)
    
    def optimize_engine_selection(self, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """Optimize engine selection based on PDF characteristics."""
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        # Simple optimization logic
        optimization = {
            'pdf_path': pdf_path,
            'recommended_engines': ['pymupdf', 'tesseract'],
            'optimization_reason': 'Default recommendation for text-based PDFs',
            'confidence': 0.8
        }
        
        return optimization
    
    def optimize_processing_pipeline(self, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """Optimize processing pipeline configuration."""
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        # Simple pipeline optimization
        pipeline = {
            'pdf_path': pdf_path,
            'pipeline_steps': ['pymupdf_extraction', 'ocr_alignment', 'consensus_scoring'],
            'optimization_level': 'balanced',
            'estimated_time': 120  # seconds
        }
        
        return pipeline
    
    def process_with_monitoring(self, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """Process with performance monitoring."""
        start_time = time.time()
        
        # Process normally
        result = self.process_pdf_integrated(pdf_path)
        
        # Add monitoring data
        monitoring_result = {
            'processing_result': result,
            'performance_metrics': {
                'total_time': time.time() - start_time,
                'memory_usage': 'N/A',  # Placeholder
                'cpu_usage': 'N/A'      # Placeholder
            }
        }
        
        return monitoring_result


# Convenience function
def process_pdf_with_integrated_engines(pdf_path: Optional[str] = None) -> IntegratedResult:
    """Process PDF with integrated engine approach."""
    processor = IntegratedEngineProcessor()
    return processor.process_pdf_integrated(pdf_path)


def save_integrated_engine_processing(pdf_path: Optional[str] = None, 
                                    output_path: Optional[str] = None) -> str:
    """Process and save integrated engine results."""
    processor = IntegratedEngineProcessor()
    result = processor.process_pdf_integrated(pdf_path)
    return processor.save_integrated_results(result, output_path)
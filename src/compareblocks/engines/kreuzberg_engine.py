# src/compareblocks/engines/kreuzberg_engine.py
"""
Kreuzberg engine for PDF text extraction.
Provides document intelligence extraction using Kreuzberg framework.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

try:
    from kreuzberg import extract_file_sync
    KREUZBERG_AVAILABLE = True
except ImportError:
    KREUZBERG_AVAILABLE = False

from ..io.pdf_metadata import PDFMetadataExtractor
from ..config.file_manager import file_manager


@dataclass
class KreuzbergBlock:
    """Kreuzberg extraction block data."""
    block_id: str
    text: str
    block_type: str
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class KreuzbergPage:
    """Kreuzberg page data."""
    page_number: int
    blocks: List[KreuzbergBlock]
    metadata: Dict[str, Any]


class KreuzbergEngine:
    """Kreuzberg document intelligence extraction engine."""
    
    def __init__(self, ocr_backend: str = 'tesseract', output_format: str = 'text'):
        """
        Initialize Kreuzberg engine.
        
        Args:
            ocr_backend: OCR backend to use ('tesseract', 'easyocr')
            output_format: Output format ('text', 'markdown', 'json')
        """
        self.ocr_backend = ocr_backend
        self.output_format = output_format
        self.metadata_extractor = PDFMetadataExtractor()
        
        if not KREUZBERG_AVAILABLE:
            print("Warning: Kreuzberg not available. Install with: pip install kreuzberg")
    
    def is_available(self) -> bool:
        """Check if Kreuzberg is available."""
        return KREUZBERG_AVAILABLE
    
    def extract_pdf(self, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from PDF using Kreuzberg.
        
        Args:
            pdf_path: Path to PDF file (defaults to configured target PDF)
            
        Returns:
            Kreuzberg extraction results
        """
        if not self.is_available():
            return {
                "error": "Kreuzberg not available",
                "message": "Install kreuzberg to use Kreuzberg extraction"
            }
        
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"Extracting text using Kreuzberg from: {pdf_path}")
        
        # Extract PDF metadata
        pdf_metadata = self.metadata_extractor.extract_pdf_metadata(str(pdf_path))
        display_name = self.metadata_extractor.get_display_name(str(pdf_path))
        
        try:
            # Use Kreuzberg to extract document
            result = extract_file_sync(str(pdf_path))
            
            # Initialize results structure
            results = {
                "engine": "kreuzberg",
                "engine_version": self._get_kreuzberg_version(),
                "pdf_path": pdf_metadata["file_info"]["relative_path"],
                "pdf_name": pdf_metadata["file_info"]["normalized_filename"],
                "pdf_display_name": display_name,
                "pdf_metadata": pdf_metadata,
                "extraction_metadata": {
                    "extraction_type": "kreuzberg_intelligence",
                    "ocr_backend": self.ocr_backend,
                    "output_format": self.output_format,
                    "processing_notes": "Document intelligence extraction using Kreuzberg framework"
                },
                "content": {},
                "metadata": {},
                "summary": {}
            }
            
            # Extract content and metadata from Kreuzberg result
            if hasattr(result, 'content'):
                content_text = result.content
                
                # Create blocks from content (Kreuzberg doesn't provide block-level data by default)
                blocks = self._create_blocks_from_content(content_text)
                
                results["content"] = {
                    "full_text": content_text,
                    "blocks": [asdict(block) for block in blocks],
                    "block_count": len(blocks)
                }
            
            # Extract metadata if available
            if hasattr(result, 'metadata'):
                kreuzberg_metadata = {}
                metadata_obj = result.metadata
                
                # Extract common metadata fields
                if hasattr(metadata_obj, 'title'):
                    kreuzberg_metadata['title'] = metadata_obj.title
                if hasattr(metadata_obj, 'author'):
                    kreuzberg_metadata['author'] = metadata_obj.author
                if hasattr(metadata_obj, 'page_count'):
                    kreuzberg_metadata['page_count'] = metadata_obj.page_count
                if hasattr(metadata_obj, 'word_count'):
                    kreuzberg_metadata['word_count'] = metadata_obj.word_count
                if hasattr(metadata_obj, 'language'):
                    kreuzberg_metadata['language'] = metadata_obj.language
                if hasattr(metadata_obj, 'created_at'):
                    kreuzberg_metadata['created_at'] = str(metadata_obj.created_at)
                
                results["metadata"] = kreuzberg_metadata
            
            # Generate summary
            results["summary"] = self._generate_summary(results)
            
            return results
            
        except Exception as e:
            return {
                "error": f"Kreuzberg extraction failed: {e}",
                "engine": "kreuzberg",
                "pdf_path": pdf_metadata["file_info"]["relative_path"],
                "pdf_name": pdf_metadata["file_info"]["normalized_filename"],
                "pdf_display_name": display_name
            }
    
    def _create_blocks_from_content(self, content: str) -> List[KreuzbergBlock]:
        """Create blocks from content text."""
        blocks = []
        
        # Split content into paragraphs/sections
        paragraphs = content.split('\n\n')
        
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                block = KreuzbergBlock(
                    block_id=f"kreuzberg_block_{i}",
                    text=paragraph.strip(),
                    block_type="paragraph",
                    confidence=None,
                    metadata={"paragraph_index": i}
                )
                blocks.append(block)
        
        return blocks
    
    def _get_kreuzberg_version(self) -> str:
        """Get Kreuzberg version."""
        try:
            import kreuzberg
            return getattr(kreuzberg, '__version__', 'unknown')
        except:
            return "unknown"
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Kreuzberg extraction summary."""
        content = results.get("content", {})
        metadata = results.get("metadata", {})
        
        full_text = content.get("full_text", "")
        blocks = content.get("blocks", [])
        
        return {
            "extraction_engine": "Kreuzberg",
            "processing_type": "document_intelligence",
            "total_blocks": len(blocks),
            "total_characters": len(full_text),
            "total_words": len(full_text.split()) if full_text else 0,
            "ocr_backend": self.ocr_backend,
            "output_format": self.output_format,
            "document_metadata": metadata,
            "has_structured_content": len(blocks) > 0
        }
    
    def save_extraction(self, pdf_path: Optional[str] = None, 
                       output_path: Optional[str] = None) -> str:
        """
        Extract and save Kreuzberg data.
        
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
            print(f"Kreuzberg extraction failed: {results['error']}")
            return ""
        
        # Determine output path
        if output_path is None:
            # Create filename based on PDF display name
            display_name = results["pdf_display_name"]
            filename = f"{display_name}_kreuzberg.json"
            
            # Save to processing directory
            processing_dir = Path(file_manager.get_processing_directory())
            output_path = processing_dir / filename
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Kreuzberg extraction saved to: {output_path}")
        return str(output_path)


# Convenience functions
def extract_kreuzberg(pdf_path: Optional[str] = None, 
                     ocr_backend: str = 'tesseract',
                     output_format: str = 'text') -> Dict[str, Any]:
    """Extract text using Kreuzberg."""
    engine = KreuzbergEngine(ocr_backend=ocr_backend, output_format=output_format)
    return engine.extract_pdf(pdf_path)


def save_kreuzberg_extraction(pdf_path: Optional[str] = None, 
                             output_path: Optional[str] = None,
                             ocr_backend: str = 'tesseract',
                             output_format: str = 'text') -> str:
    """Extract and save Kreuzberg data."""
    engine = KreuzbergEngine(ocr_backend=ocr_backend, output_format=output_format)
    return engine.save_extraction(pdf_path, output_path)
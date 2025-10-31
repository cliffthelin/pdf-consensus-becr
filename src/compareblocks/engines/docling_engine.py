# src/compareblocks/engines/docling_engine.py
"""
Docling engine for PDF text extraction.
Provides advanced PDF understanding using Docling framework.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

from ..io.pdf_metadata import PDFMetadataExtractor
from ..config.file_manager import file_manager


@dataclass
class DoclingBlock:
    """Docling extraction block data."""
    block_id: str
    text: str
    block_type: str
    bbox: Optional[List[float]] = None
    page_number: Optional[int] = None
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DoclingPage:
    """Docling page data."""
    page_number: int
    blocks: List[DoclingBlock]
    layout_info: Dict[str, Any]
    metadata: Dict[str, Any]


class DoclingEngine:
    """Docling advanced PDF understanding extraction engine."""
    
    def __init__(self, pipeline: str = 'default', export_format: str = 'markdown'):
        """
        Initialize Docling engine.
        
        Args:
            pipeline: Processing pipeline ('default', 'vlm', 'ocr')
            export_format: Export format ('markdown', 'html', 'json', 'doctags')
        """
        self.pipeline = pipeline
        self.export_format = export_format
        self.metadata_extractor = PDFMetadataExtractor()
        self._converter = None
        
        if not DOCLING_AVAILABLE:
            print("Warning: Docling not available. Install with: pip install docling")
    
    def _get_converter(self):
        """Get or create Docling converter instance."""
        if self._converter is None and DOCLING_AVAILABLE:
            try:
                self._converter = DocumentConverter()
            except Exception as e:
                print(f"Failed to initialize Docling converter: {e}")
                return None
        return self._converter
    
    def is_available(self) -> bool:
        """Check if Docling is available."""
        if not DOCLING_AVAILABLE:
            return False
        
        try:
            converter = self._get_converter()
            return converter is not None
        except Exception:
            return False
    
    def extract_pdf(self, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from PDF using Docling.
        
        Args:
            pdf_path: Path to PDF file (defaults to configured target PDF)
            
        Returns:
            Docling extraction results
        """
        if not self.is_available():
            return {
                "error": "Docling not available",
                "message": "Install docling to use Docling extraction"
            }
        
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"Extracting text using Docling from: {pdf_path}")
        
        # Extract PDF metadata
        pdf_metadata = self.metadata_extractor.extract_pdf_metadata(str(pdf_path))
        display_name = self.metadata_extractor.get_display_name(str(pdf_path))
        
        try:
            # Get Docling converter
            converter = self._get_converter()
            if converter is None:
                return {
                    "error": "Failed to initialize Docling converter"
                }
            
            # Convert document
            result = converter.convert(str(pdf_path))
            
            # Initialize results structure
            results = {
                "engine": "docling",
                "engine_version": self._get_docling_version(),
                "pdf_path": pdf_metadata["file_info"]["relative_path"],
                "pdf_name": pdf_metadata["file_info"]["normalized_filename"],
                "pdf_display_name": display_name,
                "pdf_metadata": pdf_metadata,
                "extraction_metadata": {
                    "extraction_type": "docling_advanced_pdf",
                    "pipeline": self.pipeline,
                    "export_format": self.export_format,
                    "processing_notes": "Advanced PDF understanding using Docling framework"
                },
                "pages": {},
                "content": {},
                "summary": {}
            }
            
            # Extract content in different formats
            content_data = {}
            
            # Get markdown content
            if hasattr(result.document, 'export_to_markdown'):
                content_data['markdown'] = result.document.export_to_markdown()
            
            # Get HTML content
            if hasattr(result.document, 'export_to_html'):
                content_data['html'] = result.document.export_to_html()
            
            # Get JSON content
            if hasattr(result.document, 'export_to_json'):
                content_data['json'] = result.document.export_to_json()
            
            # Get DocTags content
            if hasattr(result.document, 'export_to_doctags'):
                content_data['doctags'] = result.document.export_to_doctags()
            
            results["content"] = content_data
            
            # Extract pages and blocks if available
            if hasattr(result.document, 'pages'):
                pages_data = {}
                all_blocks = []
                
                for page_idx, page in enumerate(result.document.pages):
                    page_blocks = []
                    
                    # Extract blocks from page
                    if hasattr(page, 'elements'):
                        for elem_idx, element in enumerate(page.elements):
                            block_text = ""
                            block_type = "unknown"
                            bbox = None
                            
                            # Extract text content
                            if hasattr(element, 'text'):
                                block_text = element.text
                            elif hasattr(element, 'content'):
                                block_text = str(element.content)
                            
                            # Extract element type
                            if hasattr(element, 'label'):
                                block_type = element.label
                            elif hasattr(element, 'type'):
                                block_type = str(element.type)
                            
                            # Extract bounding box
                            if hasattr(element, 'bbox'):
                                bbox = [element.bbox.l, element.bbox.t, element.bbox.r, element.bbox.b]
                            
                            if block_text and block_text.strip():
                                docling_block = DoclingBlock(
                                    block_id=f"docling_p{page_idx}_b{elem_idx}",
                                    text=block_text.strip(),
                                    block_type=block_type,
                                    bbox=bbox,
                                    page_number=page_idx,
                                    confidence=None,
                                    metadata={
                                        "element_index": elem_idx,
                                        "page_index": page_idx
                                    }
                                )
                                page_blocks.append(docling_block)
                                all_blocks.append(docling_block)
                    
                    # Create page data
                    page_data = DoclingPage(
                        page_number=page_idx,
                        blocks=page_blocks,
                        layout_info={
                            "width": getattr(page, 'width', 0) if hasattr(page, 'width') else 0,
                            "height": getattr(page, 'height', 0) if hasattr(page, 'height') else 0
                        },
                        metadata={
                            "block_count": len(page_blocks),
                            "page_index": page_idx
                        }
                    )
                    
                    pages_data[str(page_idx)] = asdict(page_data)
                
                results["pages"] = pages_data
                
                # Add blocks summary to content
                results["content"]["blocks"] = [asdict(block) for block in all_blocks]
                results["content"]["total_blocks"] = len(all_blocks)
            
            # Generate summary
            results["summary"] = self._generate_summary(results)
            
            return results
            
        except Exception as e:
            return {
                "error": f"Docling extraction failed: {e}",
                "engine": "docling",
                "pdf_path": pdf_metadata["file_info"]["relative_path"],
                "pdf_name": pdf_metadata["file_info"]["normalized_filename"],
                "pdf_display_name": display_name
            }
    
    def _get_docling_version(self) -> str:
        """Get Docling version."""
        try:
            import docling
            return getattr(docling, '__version__', 'unknown')
        except:
            return "unknown"
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Docling extraction summary."""
        content = results.get("content", {})
        pages = results.get("pages", {})
        
        # Calculate text statistics
        markdown_text = content.get("markdown", "")
        total_blocks = content.get("total_blocks", 0)
        
        return {
            "extraction_engine": "Docling",
            "processing_type": "advanced_pdf_understanding",
            "total_pages": len(pages),
            "total_blocks": total_blocks,
            "total_characters": len(markdown_text),
            "total_words": len(markdown_text.split()) if markdown_text else 0,
            "pipeline": self.pipeline,
            "export_format": self.export_format,
            "available_formats": list(content.keys()),
            "has_layout_info": total_blocks > 0,
            "has_structured_content": "blocks" in content
        }
    
    def save_extraction(self, pdf_path: Optional[str] = None, 
                       output_path: Optional[str] = None) -> str:
        """
        Extract and save Docling data.
        
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
            print(f"Docling extraction failed: {results['error']}")
            return ""
        
        # Determine output path
        if output_path is None:
            # Create filename based on PDF display name
            display_name = results["pdf_display_name"]
            filename = f"{display_name}_docling.json"
            
            # Save to processing directory
            processing_dir = Path(file_manager.get_processing_directory())
            output_path = processing_dir / filename
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Docling extraction saved to: {output_path}")
        return str(output_path)


# Convenience functions
def extract_docling(pdf_path: Optional[str] = None, 
                   pipeline: str = 'default',
                   export_format: str = 'markdown') -> Dict[str, Any]:
    """Extract text using Docling."""
    engine = DoclingEngine(pipeline=pipeline, export_format=export_format)
    return engine.extract_pdf(pdf_path)


def save_docling_extraction(pdf_path: Optional[str] = None, 
                           output_path: Optional[str] = None,
                           pipeline: str = 'default',
                           export_format: str = 'markdown') -> str:
    """Extract and save Docling data."""
    engine = DoclingEngine(pipeline=pipeline, export_format=export_format)
    return engine.save_extraction(pdf_path, output_path)
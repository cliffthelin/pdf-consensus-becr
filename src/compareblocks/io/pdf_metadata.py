# src/compareblocks/io/pdf_metadata.py
"""
PDF metadata extraction and normalization utilities.
Provides proper filename handling and PDF attribute extraction.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import fitz  # PyMuPDF


class PDFMetadataExtractor:
    """Extract and normalize PDF metadata with proper filename handling."""
    
    def __init__(self):
        """Initialize the PDF metadata extractor."""
        pass
    
    def extract_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive PDF metadata with proper filename normalization.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing normalized PDF metadata
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Open PDF to extract metadata
        doc = fitz.open(str(pdf_path))
        
        try:
            # Extract basic file information
            file_stats = pdf_path.stat()
            
            # Normalize filename - remove leading dashes and clean up
            original_filename = pdf_path.name
            normalized_filename = self._normalize_filename(original_filename)
            
            # Extract PDF document metadata
            pdf_metadata = doc.metadata
            
            # Get page information
            total_pages = len(doc)
            first_page = doc[0] if total_pages > 0 else None
            page_dimensions = None
            
            if first_page:
                rect = first_page.rect
                page_dimensions = {
                    "width": rect.width,
                    "height": rect.height,
                    "units": "points"
                }
            
            # Build comprehensive metadata
            metadata = {
                "file_info": {
                    "original_path": str(pdf_path),
                    "relative_path": str(pdf_path.relative_to(Path.cwd())) if pdf_path.is_absolute() else str(pdf_path),
                    "original_filename": original_filename,
                    "normalized_filename": normalized_filename,
                    "file_size_bytes": file_stats.st_size,
                    "creation_time": file_stats.st_ctime,
                    "modification_time": file_stats.st_mtime
                },
                "pdf_properties": {
                    "total_pages": total_pages,
                    "pdf_version": getattr(doc, 'pdf_version', None),
                    "is_encrypted": doc.needs_pass,
                    "has_forms": doc.is_form_pdf,
                    "page_count": doc.page_count,
                    "page_dimensions": page_dimensions
                },
                "document_metadata": {
                    "title": pdf_metadata.get("title", ""),
                    "author": pdf_metadata.get("author", ""),
                    "subject": pdf_metadata.get("subject", ""),
                    "creator": pdf_metadata.get("creator", ""),
                    "producer": pdf_metadata.get("producer", ""),
                    "creation_date": pdf_metadata.get("creationDate", ""),
                    "modification_date": pdf_metadata.get("modDate", "")
                }
            }
            
            return metadata
            
        finally:
            doc.close()
    
    def _normalize_filename(self, filename: str) -> str:
        """
        Normalize filename by removing problematic characters and formatting.
        
        Args:
            filename: Original filename
            
        Returns:
            Normalized filename
        """
        # Remove leading dashes and spaces
        normalized = filename.lstrip("- ")
        
        # If the filename becomes empty or just an extension, use a default
        if not normalized or normalized.startswith("."):
            base_name = Path(filename).stem.lstrip("- ")
            extension = Path(filename).suffix
            if not base_name:
                base_name = "document"
            normalized = f"{base_name}{extension}"
        
        return normalized
    
    def get_display_name(self, pdf_path: str) -> str:
        """
        Get a clean display name for the PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Clean display name
        """
        metadata = self.extract_pdf_metadata(pdf_path)
        
        # Try to use document title if available and meaningful
        title = metadata["document_metadata"]["title"]
        if title and len(title.strip()) > 0 and title.strip() != "":
            return title.strip()
        
        # Fall back to normalized filename without extension
        normalized_filename = metadata["file_info"]["normalized_filename"]
        return Path(normalized_filename).stem
    
    def create_root_pdf_json(self, pdf_path: str, associated_files: Optional[list] = None) -> Dict[str, Any]:
        """
        Create comprehensive root PDF JSON with proper metadata.
        
        Args:
            pdf_path: Path to the PDF file
            associated_files: List of associated files (optional)
            
        Returns:
            Complete root PDF JSON structure
        """
        metadata = self.extract_pdf_metadata(pdf_path)
        
        # Build the root PDF JSON structure
        root_pdf_json = {
            "root_pdf": {
                "path": metadata["file_info"]["relative_path"],
                "absolute_path": metadata["file_info"]["original_path"],
                "filename": metadata["file_info"]["normalized_filename"],
                "display_name": self.get_display_name(pdf_path),
                "attributes": {
                    "file_size_bytes": metadata["file_info"]["file_size_bytes"],
                    "total_pages": metadata["pdf_properties"]["total_pages"],
                    "file_type": "pdf",
                    "encoding": "utf-8",
                    "creation_date": metadata["document_metadata"]["creation_date"],
                    "modification_date": metadata["document_metadata"]["modification_date"],
                    "pdf_version": metadata["pdf_properties"]["pdf_version"],
                    "is_encrypted": metadata["pdf_properties"]["is_encrypted"],
                    "has_forms": metadata["pdf_properties"]["has_forms"],
                    "page_dimensions": metadata["pdf_properties"]["page_dimensions"],
                    "document_title": metadata["document_metadata"]["title"],
                    "document_author": metadata["document_metadata"]["author"],
                    "document_subject": metadata["document_metadata"]["subject"],
                    "document_creator": metadata["document_metadata"]["creator"],
                    "document_producer": metadata["document_metadata"]["producer"]
                }
            }
        }
        
        # Add associated files if provided
        if associated_files:
            root_pdf_json["root_pdf"]["associated_files"] = {
                "count": len(associated_files),
                "files": associated_files
            }
        
        return root_pdf_json


# Convenience function for direct use
def extract_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """Extract PDF metadata using the PDFMetadataExtractor."""
    extractor = PDFMetadataExtractor()
    return extractor.extract_pdf_metadata(pdf_path)


def create_root_pdf_json(pdf_path: str, associated_files: Optional[list] = None) -> Dict[str, Any]:
    """Create root PDF JSON using the PDFMetadataExtractor."""
    extractor = PDFMetadataExtractor()
    return extractor.create_root_pdf_json(pdf_path, associated_files)
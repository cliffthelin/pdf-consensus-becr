# src/compareblocks/association/manager.py
"""
Association management for tracking all files per root PDF context.
Implements dynamic association loading and metadata tracking.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import json

from .parsers import parse_association_file, ParsedContent


@dataclass
class AssociationMetadata:
    """Metadata for an association file."""
    file_path: str
    format_type: str
    file_size: int
    last_modified: datetime
    content_length: int
    parsing_success: bool
    error_message: Optional[str] = None


@dataclass
class PDFAssociations:
    """All associations for a PDF file."""
    pdf_path: str
    associations: Dict[str, ParsedContent] = field(default_factory=dict)
    metadata: Dict[str, AssociationMetadata] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


class AssociationManager:
    """Manages associations for PDF files."""
    
    def __init__(self):
        """Initialize association manager."""
        self.pdf_associations: Dict[str, PDFAssociations] = {}
    
    def load_associations_for_pdf(self, pdf_path: str) -> PDFAssociations:
        """Load all associations for a PDF file."""
        pdf_path = str(Path(pdf_path).resolve())
        
        if pdf_path in self.pdf_associations:
            return self.pdf_associations[pdf_path]
        
        # Create new associations object
        associations = PDFAssociations(pdf_path=pdf_path)
        
        # Find association files in the same directory
        pdf_file = Path(pdf_path)
        pdf_dir = pdf_file.parent
        pdf_stem = pdf_file.stem
        
        # Look for files with similar names
        association_files = []
        for file_path in pdf_dir.glob(f"*{pdf_stem}*"):
            if file_path.suffix.lower() in ['.csv', '.html', '.json', '.md', '.txt'] and file_path != pdf_file:
                association_files.append(file_path)
        
        # Also look for files with the PDF name prefix
        for file_path in pdf_dir.glob(f"-{pdf_stem}*"):
            if file_path.suffix.lower() in ['.csv', '.html', '.json', '.md', '.txt']:
                association_files.append(file_path)
        
        # Parse each association file
        for file_path in association_files:
            try:
                parsed_content = parse_association_file(str(file_path))
                
                # Store parsed content
                associations.associations[str(file_path)] = parsed_content
                
                # Store metadata
                stat = file_path.stat()
                associations.metadata[str(file_path)] = AssociationMetadata(
                    file_path=str(file_path),
                    format_type=parsed_content.format_type,
                    file_size=stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                    content_length=len(parsed_content.text_content),
                    parsing_success=True
                )
                
            except Exception as e:
                # Store error metadata
                stat = file_path.stat()
                associations.metadata[str(file_path)] = AssociationMetadata(
                    file_path=str(file_path),
                    format_type="unknown",
                    file_size=stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                    content_length=0,
                    parsing_success=False,
                    error_message=str(e)
                )
        
        # Cache and return
        self.pdf_associations[pdf_path] = associations
        return associations
    
    def get_associations(self, pdf_path: str) -> Optional[PDFAssociations]:
        """Get cached associations for a PDF."""
        pdf_path = str(Path(pdf_path).resolve())
        return self.pdf_associations.get(pdf_path)
    
    def refresh_associations(self, pdf_path: str) -> PDFAssociations:
        """Refresh associations for a PDF (reload from disk)."""
        pdf_path = str(Path(pdf_path).resolve())
        if pdf_path in self.pdf_associations:
            del self.pdf_associations[pdf_path]
        return self.load_associations_for_pdf(pdf_path)
    
    def get_association_summary(self, pdf_path: str) -> Dict[str, Any]:
        """Get summary of associations for a PDF."""
        associations = self.get_associations(pdf_path)
        if not associations:
            return {"error": "No associations found"}
        
        successful = sum(1 for meta in associations.metadata.values() if meta.parsing_success)
        total = len(associations.metadata)
        
        formats = {}
        for meta in associations.metadata.values():
            if meta.parsing_success:
                formats[meta.format_type] = formats.get(meta.format_type, 0) + 1
        
        return {
            "pdf_path": pdf_path,
            "total_files": total,
            "successful_parses": successful,
            "failed_parses": total - successful,
            "formats": formats,
            "last_updated": associations.last_updated.isoformat()
        }


def load_associations_for_pdf(pdf_path: str) -> PDFAssociations:
    """Convenience function to load associations for a PDF."""
    manager = AssociationManager()
    return manager.load_associations_for_pdf(pdf_path)


def track_association_metadata(pdf_path: str) -> Dict[str, AssociationMetadata]:
    """Convenience function to get association metadata."""
    manager = AssociationManager()
    associations = manager.load_associations_for_pdf(pdf_path)
    return associations.metadata
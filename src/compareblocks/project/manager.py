# src/compareblocks/project/manager.py
"""
Comprehensive project management system for BECR.
Handles file tracking, validation, and project structure management.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib

from ..association.manager import AssociationManager, PDFAssociations
from ..config.file_manager import FileManager


@dataclass
class FileStatus:
    """Status information for a tracked file."""
    path: str
    exists: bool
    last_modified: Optional[datetime] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ProjectStructure:
    """Project structure information."""
    root_pdf: str
    processing_directory: str
    final_output_directory: str
    associated_files: List[str] = field(default_factory=list)
    previous_results: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    moved_files: Dict[str, str] = field(default_factory=dict)  # old_path -> new_path
    last_validated: Optional[datetime] = None


class ProjectManager:
    """Comprehensive project management for BECR system."""
    
    def __init__(self):
        """Initialize project manager."""
        self.file_manager = FileManager()
        self.association_manager = AssociationManager()
        self._file_cache: Dict[str, FileStatus] = {}
        self._project_cache: Dict[str, ProjectStructure] = {}
    
    def create_project_structure(self, pdf_path: str) -> ProjectStructure:
        """Create comprehensive project structure for a PDF."""
        pdf_path = str(Path(pdf_path).resolve())
        
        # Get basic structure from file manager
        processing_dir = self.file_manager.get_processing_directory()
        final_dir = self.file_manager.get_final_output_directory()
        
        # Load associations
        associations = self.association_manager.load_associations_for_pdf(pdf_path)
        
        # Find previous results
        previous_results = self._find_previous_results(pdf_path)
        
        # Create project structure
        structure = ProjectStructure(
            root_pdf=pdf_path,
            processing_directory=processing_dir,
            final_output_directory=final_dir,
            associated_files=list(associations.associations.keys()),
            previous_results=previous_results,
            last_validated=datetime.now()
        )
        
        # Validate all files
        self._validate_project_files(structure)
        
        # Cache the structure
        self._project_cache[pdf_path] = structure
        
        return structure
    
    def _find_previous_results(self, pdf_path: str) -> List[str]:
        """Find previous processing results for a PDF."""
        previous_results = []
        
        # Check processing directory
        processing_dir = Path(self.file_manager.get_processing_directory())
        if processing_dir.exists():
            for file_path in processing_dir.glob("*.ndjson"):
                previous_results.append(str(file_path))
            for file_path in processing_dir.glob("*.json"):
                previous_results.append(str(file_path))
        
        # Check final output directory
        final_dir = Path(self.file_manager.get_final_output_directory())
        if final_dir.exists():
            for file_path in final_dir.glob("*.ndjson"):
                previous_results.append(str(file_path))
            for file_path in final_dir.glob("*.json"):
                previous_results.append(str(file_path))
        
        return previous_results
    
    def _validate_project_files(self, structure: ProjectStructure) -> None:
        """Validate all files in project structure."""
        all_files = [structure.root_pdf] + structure.associated_files + structure.previous_results
        
        structure.missing_files = []
        
        for file_path in all_files:
            status = self.get_file_status(file_path)
            if not status.exists:
                structure.missing_files.append(file_path)
    
    def get_file_status(self, file_path: str) -> FileStatus:
        """Get comprehensive status for a file."""
        file_path = str(Path(file_path).resolve())
        
        # Check cache first
        if file_path in self._file_cache:
            cached_status = self._file_cache[file_path]
            # Refresh cache if file exists and we have no recent check
            if cached_status.exists and cached_status.last_modified:
                try:
                    current_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                    if current_mtime == cached_status.last_modified:
                        return cached_status
                except (OSError, FileNotFoundError):
                    pass
        
        # Create new status
        status = FileStatus(path=file_path, exists=False)
        
        try:
            path_obj = Path(file_path)
            if path_obj.exists():
                stat = path_obj.stat()
                status.exists = True
                status.last_modified = datetime.fromtimestamp(stat.st_mtime)
                status.file_size = stat.st_size
                
                # Calculate checksum for small files
                if stat.st_size < 10 * 1024 * 1024:  # 10MB limit
                    status.checksum = self._calculate_checksum(file_path)
                else:
                    status.checksum = ""  # Empty string for large files
            else:
                status.error_message = "File not found"
        
        except Exception as e:
            status.error_message = str(e)
        
        # Cache the status
        self._file_cache[file_path] = status
        
        return status
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum for a file."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def validate_project_structure(self, pdf_path: str) -> Dict[str, Any]:
        """Validate project structure and return detailed report."""
        structure = self.get_project_structure(pdf_path)
        
        # Re-validate all files to ensure current status
        self._validate_project_files(structure)
        
        validation_report = {
            "pdf_path": pdf_path,
            "validation_time": datetime.now().isoformat(),
            "root_pdf_exists": self.get_file_status(structure.root_pdf).exists,
            "processing_directory_exists": Path(structure.processing_directory).exists(),
            "final_output_directory_exists": Path(structure.final_output_directory).exists(),
            "total_associated_files": len(structure.associated_files),
            "missing_files": structure.missing_files,
            "moved_files": structure.moved_files,
            "previous_results_count": len(structure.previous_results),
            "file_details": {}
        }
        
        # Add detailed file status
        all_files = [structure.root_pdf] + structure.associated_files + structure.previous_results
        for file_path in all_files:
            status = self.get_file_status(file_path)
            validation_report["file_details"][file_path] = {
                "exists": status.exists,
                "size": status.file_size,
                "last_modified": status.last_modified.isoformat() if status.last_modified else None,
                "error": status.error_message
            }
        
        return validation_report
    
    def get_project_structure(self, pdf_path: str) -> ProjectStructure:
        """Get project structure, creating if necessary."""
        pdf_path = str(Path(pdf_path).resolve())
        
        if pdf_path in self._project_cache:
            structure = self._project_cache[pdf_path]
            # Refresh if validation is old
            if structure.last_validated and (datetime.now() - structure.last_validated).seconds > 300:  # 5 minutes
                return self.create_project_structure(pdf_path)
            return structure
        
        return self.create_project_structure(pdf_path)
    
    def find_moved_files(self, pdf_path: str) -> Dict[str, List[str]]:
        """Find files that may have been moved by searching for similar names."""
        structure = self.get_project_structure(pdf_path)
        moved_candidates = {}
        
        pdf_dir = Path(pdf_path).parent
        pdf_stem = Path(pdf_path).stem
        
        for missing_file in structure.missing_files:
            missing_name = Path(missing_file).name
            missing_stem = Path(missing_file).stem
            
            # Search for files with similar names
            candidates = []
            
            # Search in PDF directory
            for file_path in pdf_dir.rglob("*"):
                if file_path.is_file():
                    file_name = file_path.name
                    file_stem = file_path.stem
                    
                    # Check for similar names
                    if (missing_stem in file_name or 
                        file_stem in missing_name or
                        pdf_stem in file_name):
                        candidates.append(str(file_path))
            
            if candidates:
                moved_candidates[missing_file] = candidates
        
        return moved_candidates
    
    def relocate_file(self, old_path: str, new_path: str, pdf_path: str) -> bool:
        """Relocate a file in the project structure."""
        try:
            structure = self.get_project_structure(pdf_path)
            
            # Update structure
            if old_path in structure.associated_files:
                structure.associated_files.remove(old_path)
                structure.associated_files.append(new_path)
            
            if old_path in structure.previous_results:
                structure.previous_results.remove(old_path)
                structure.previous_results.append(new_path)
            
            if old_path in structure.missing_files:
                structure.missing_files.remove(old_path)
            
            # Record the move
            structure.moved_files[old_path] = new_path
            
            # Clear file cache for old path
            if old_path in self._file_cache:
                del self._file_cache[old_path]
            
            # Update cache
            self._project_cache[pdf_path] = structure
            
            return True
        
        except Exception:
            return False
    
    def get_reprocessing_files(self, pdf_path: str) -> Dict[str, List[str]]:
        """Get all files that should be considered for reprocessing."""
        structure = self.get_project_structure(pdf_path)
        
        reprocessing_files = {
            "root_pdf": [structure.root_pdf],
            "associated_files": [f for f in structure.associated_files if self.get_file_status(f).exists],
            "previous_results": [f for f in structure.previous_results if self.get_file_status(f).exists],
            "missing_files": structure.missing_files
        }
        
        return reprocessing_files
    
    def create_project_manifest(self, pdf_path: str) -> Dict[str, Any]:
        """Create a comprehensive project manifest."""
        structure = self.get_project_structure(pdf_path)
        validation_report = self.validate_project_structure(pdf_path)
        reprocessing_files = self.get_reprocessing_files(pdf_path)
        
        manifest = {
            "project_info": {
                "root_pdf": structure.root_pdf,
                "created": datetime.now().isoformat(),
                "processing_directory": structure.processing_directory,
                "final_output_directory": structure.final_output_directory
            },
            "file_structure": {
                "associated_files": structure.associated_files,
                "previous_results": structure.previous_results,
                "missing_files": structure.missing_files,
                "moved_files": structure.moved_files
            },
            "validation_report": validation_report,
            "reprocessing_files": reprocessing_files,
            "statistics": {
                "total_files": len(structure.associated_files) + len(structure.previous_results) + 1,
                "missing_count": len(structure.missing_files),
                "moved_count": len(structure.moved_files),
                "valid_files": len([f for f in structure.associated_files + structure.previous_results 
                                 if self.get_file_status(f).exists])
            }
        }
        
        return manifest
    
    def save_project_manifest(self, pdf_path: str, output_path: Optional[str] = None) -> str:
        """Save project manifest to file."""
        manifest = self.create_project_manifest(pdf_path)
        
        if output_path is None:
            processing_dir = Path(self.file_manager.get_processing_directory())
            processing_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(processing_dir / "project_manifest.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._file_cache.clear()
        self._project_cache.clear()
    
    def get_project_summary(self, pdf_path: str) -> Dict[str, Any]:
        """Get a summary of the project status."""
        structure = self.get_project_structure(pdf_path)
        
        return {
            "pdf_path": pdf_path,
            "total_associated_files": len(structure.associated_files),
            "missing_files_count": len(structure.missing_files),
            "moved_files_count": len(structure.moved_files),
            "previous_results_count": len(structure.previous_results),
            "last_validated": structure.last_validated.isoformat() if structure.last_validated else None,
            "directories": {
                "processing": structure.processing_directory,
                "final_output": structure.final_output_directory
            }
        }


def create_project_structure(pdf_path: str) -> ProjectStructure:
    """Convenience function to create project structure."""
    manager = ProjectManager()
    return manager.create_project_structure(pdf_path)


def validate_project_structure(pdf_path: str) -> Dict[str, Any]:
    """Convenience function to validate project structure."""
    manager = ProjectManager()
    return manager.validate_project_structure(pdf_path)


def get_project_summary(pdf_path: str) -> Dict[str, Any]:
    """Convenience function to get project summary."""
    manager = ProjectManager()
    return manager.get_project_summary(pdf_path)
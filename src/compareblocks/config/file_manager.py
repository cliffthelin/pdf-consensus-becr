# src/compareblocks/config/file_manager.py
"""
Centralized file path and configuration management.
Eliminates hardcoded paths throughout the application.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
import os


class FileManager:
    """Manages all file paths and configuration for the application."""
    
    _instance = None
    _config = None
    _mcp_overrides = None
    
    def __new__(cls):
        """Singleton pattern to ensure consistent configuration across application."""
        if cls._instance is None:
            cls._instance = super(FileManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the file manager with default configuration."""
        if self._config is None:
            self._load_config()
            self._mcp_overrides = {}
    
    def _load_config(self) -> None:
        """Load configuration from default_files.json."""
        # Find config file relative to project root
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent  # Go up to project root
        config_path = project_root / "config" / "default_files.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = json.load(f)
        
        # Store project root for path resolution
        self._project_root = project_root
    
    def get_target_pdf_path(self) -> str:
        """Get the primary target PDF file path."""
        # Check for MCP override first (for future MCP integration)
        if self._mcp_overrides and "target_pdf_path" in self._mcp_overrides:
            return self._mcp_overrides["target_pdf_path"]
        
        return str(self._project_root / self._config["target_files"]["primary_pdf"]["path"])
    
    def _get_pdf_base_directory(self) -> Path:
        """Get the base directory where the PDF is located."""
        pdf_path = Path(self.get_target_pdf_path())
        return pdf_path.parent
    
    def _get_output_base_directory(self) -> Path:
        """Get the base output directory based on configuration strategy."""
        output_config = self._config["output_configuration"]
        
        if output_config["base_output_strategy"] == "pdf_location":
            # Create directory structure: Source_docs/{PDF_Display_Name}/
            from ..io.pdf_metadata import PDFMetadataExtractor
            
            pdf_path = self.get_target_pdf_path()
            extractor = PDFMetadataExtractor()
            display_name = extractor.get_display_name(pdf_path)
            
            # Get the Source_docs directory (parent of the PDF's parent directory)
            pdf_parent = Path(pdf_path).parent
            source_docs_dir = pdf_parent.parent
            
            # Create the folder named after the PDF's display name
            pdf_named_folder = source_docs_dir / display_name
            
            return pdf_named_folder
        else:
            # Fallback to configured directory
            fallback = output_config.get("fallback_output_directory", "output")
            return self._project_root / fallback
    
    def _generate_timestamp_suffix(self) -> str:
        """Generate timestamp suffix if idempotent processing is disabled."""
        output_config = self._config["output_configuration"]
        
        if output_config.get("idempotent_processing", True):
            return ""
        
        from datetime import datetime
        timestamp_format = output_config.get("timestamp_format", "%Y%m%d_%H%M")
        return "_" + datetime.now().strftime(timestamp_format)
    
    def _get_filename_with_timestamp(self, base_filename: str) -> str:
        """Get filename with timestamp suffix if needed."""
        timestamp_suffix = self._generate_timestamp_suffix()
        if not timestamp_suffix:
            return base_filename
        
        # Insert timestamp before file extension
        name_parts = base_filename.rsplit('.', 1)
        if len(name_parts) == 2:
            return f"{name_parts[0]}{timestamp_suffix}.{name_parts[1]}"
        else:
            return f"{base_filename}{timestamp_suffix}"
    
    def get_processing_directory(self) -> str:
        """Get the processing in-progress directory path."""
        output_config = self._config["output_configuration"]
        processing_folder = output_config.get("processing_folder", "Processing_Inprogress")
        
        base_dir = self._get_output_base_directory()
        processing_dir = base_dir / processing_folder
        
        return str(processing_dir)
    
    def get_final_output_directory(self) -> str:
        """Get the final output directory path."""
        output_config = self._config["output_configuration"]
        final_folder = output_config.get("final_folder", "Final_output")
        
        base_dir = self._get_output_base_directory()
        final_dir = base_dir / final_folder
        
        return str(final_dir)
    
    def get_output_directory(self) -> str:
        """Get the current output directory (processing directory)."""
        return self.get_processing_directory()
    
    def get_gbg_analysis_output_path(self) -> str:
        """Get the GBG analysis output file path."""
        output_config = self._config["output_configuration"]
        base_filename = output_config["default_filenames"]["gbg_analysis"]
        filename = self._get_filename_with_timestamp(base_filename)
        
        processing_dir = Path(self.get_processing_directory())
        return str(processing_dir / filename)
    
    def get_ndjson_variations_output_path(self) -> str:
        """Get the NDJSON variations output file path."""
        output_config = self._config["output_configuration"]
        base_filename = output_config["default_filenames"]["ndjson_variations"]
        filename = self._get_filename_with_timestamp(base_filename)
        
        processing_dir = Path(self.get_processing_directory())
        return str(processing_dir / filename)
    
    def get_ndjson_consensus_output_path(self) -> str:
        """Get the NDJSON consensus output file path."""
        output_config = self._config["output_configuration"]
        base_filename = output_config["default_filenames"]["ndjson_consensus"]
        filename = self._get_filename_with_timestamp(base_filename)
        
        processing_dir = Path(self.get_processing_directory())
        return str(processing_dir / filename)
    
    def get_analytics_output_path(self) -> str:
        """Get the analytics output file path."""
        output_config = self._config["output_configuration"]
        base_filename = output_config["default_filenames"]["analytics_report"]
        filename = self._get_filename_with_timestamp(base_filename)
        
        processing_dir = Path(self.get_processing_directory())
        return str(processing_dir / filename)
    
    def get_test_output_directory(self) -> str:
        """Get the test output directory path."""
        return str(self._project_root / self._config["test_files"]["test_output_directory"]["path"])
    
    def get_integration_test_output_path(self) -> str:
        """Get the integration test output file path."""
        return str(self._project_root / self._config["test_files"]["integration_test_output"]["path"])
    
    def get_unit_test_output_path(self) -> str:
        """Get the unit test output file path."""
        return str(self._project_root / self._config["test_files"]["unit_test_output"]["path"])
    
    def get_expected_pdf_pages(self) -> int:
        """Get the expected number of pages in the target PDF."""
        return self._config["target_files"]["primary_pdf"]["pages"]
    
    def get_expected_pdf_blocks(self) -> int:
        """Get the expected number of blocks in the target PDF."""
        return self._config["target_files"]["primary_pdf"]["expected_blocks"]
    
    def get_default_engines(self) -> list:
        """Get the list of default processing engines."""
        return self._config["application_settings"]["default_engines"].copy()
    
    def get_default_encoding(self) -> str:
        """Get the default file encoding."""
        return self._config["application_settings"]["encoding"]
    
    def is_validation_enabled(self) -> bool:
        """Check if validation is enabled by default."""
        return self._config["application_settings"]["validation_enabled"]
    
    def get_output_formats(self) -> list:
        """Get the supported output formats."""
        return self._config["application_settings"]["output_formats"].copy()
    
    def get_default_page_range(self) -> Dict[str, int]:
        """Get the default page range for processing."""
        return self._config["application_settings"]["default_page_range"].copy()
    
    def should_ignore_images(self, pdf_path: Optional[str] = None) -> bool:
        """
        Check if image blocks should be ignored in extraction and comparison.
        
        Args:
            pdf_path: Optional PDF path for per-PDF override checking
            
        Returns:
            True if images should be ignored, False otherwise
        """
        # Check for per-PDF override first
        if pdf_path and self._config["application_settings"]["image_handling"]["per_pdf_override_enabled"]:
            # Look for PDF-specific configuration (future enhancement)
            # For now, use global setting
            pass
        
        return self._config["application_settings"]["image_handling"]["ignore_images"]
    
    def get_image_placeholder_text(self) -> str:
        """Get the placeholder text used for image blocks."""
        return self._config["application_settings"]["image_handling"]["image_placeholder_text"]
    
    def is_image_block(self, text: str) -> bool:
        """
        Check if a block represents an image based on its text content.
        
        Args:
            text: The text content of the block
            
        Returns:
            True if the block represents an image, False otherwise
        """
        if not text:
            return False
        
        placeholder = self.get_image_placeholder_text()
        return text.strip() == placeholder
    
    def get_image_handling_config(self) -> Dict[str, Any]:
        """Get the complete image handling configuration."""
        return self._config["application_settings"]["image_handling"].copy()
    
    def ensure_output_directories(self) -> None:
        """Ensure all output directories exist."""
        directories = [
            self.get_processing_directory(),
            self.get_final_output_directory(),
            self.get_test_output_directory()
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Print the created directory structure for verification
        processing_dir = Path(self.get_processing_directory())
        print(f"Output directories created:")
        print(f"  Processing: {processing_dir}")
        print(f"  Final: {Path(self.get_final_output_directory())}")
        print(f"  Test: {Path(self.get_test_output_directory())}")
    
    def move_to_final_output(self) -> None:
        """Move all files from processing directory to final output directory."""
        processing_dir = Path(self.get_processing_directory())
        final_dir = Path(self.get_final_output_directory())
        
        if not processing_dir.exists():
            return
        
        # Ensure final directory exists
        final_dir.mkdir(parents=True, exist_ok=True)
        
        # Move all files from processing to final
        import shutil
        for file_path in processing_dir.iterdir():
            if file_path.is_file():
                dest_path = final_dir / file_path.name
                shutil.move(str(file_path), str(dest_path))
    
    def cleanup_processing_directory(self) -> None:
        """Clean up the processing directory after moving files to final output."""
        processing_dir = Path(self.get_processing_directory())
        if processing_dir.exists():
            import shutil
            shutil.rmtree(processing_dir)
    
    def is_idempotent_processing(self) -> bool:
        """Check if processing is idempotent (no timestamps)."""
        return self._config["output_configuration"].get("idempotent_processing", True)
    
    def get_timestamp_precision(self) -> str:
        """Get the configured timestamp precision."""
        return self._config["output_configuration"].get("timestamp_precision", "minute")
    
    def get_file_info(self, file_key: str) -> Dict[str, Any]:
        """Get complete information about a configured file."""
        # Check target_files first
        if file_key in self._config["target_files"]:
            info = self._config["target_files"][file_key].copy()
            info["absolute_path"] = str(self._project_root / info["path"])
            return info
        
        # Check test_files
        if file_key in self._config["test_files"]:
            info = self._config["test_files"][file_key].copy()
            info["absolute_path"] = str(self._project_root / info["path"])
            return info
        
        raise KeyError(f"File configuration not found: {file_key}")
    
    def validate_target_pdf(self) -> bool:
        """Validate that the target PDF exists and is accessible."""
        pdf_path = Path(self.get_target_pdf_path())
        return pdf_path.exists() and pdf_path.is_file()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        try:
            processing_directory = self.get_processing_directory()
            final_output_directory = self.get_final_output_directory()
        except FileNotFoundError:
            # Handle case where PDF doesn't exist (e.g., during testing with fake paths)
            processing_directory = "N/A (PDF not found)"
            final_output_directory = "N/A (PDF not found)"
        
        return {
            "target_pdf": self.get_target_pdf_path(),
            "target_pdf_exists": self.validate_target_pdf(),
            "expected_pages": self.get_expected_pdf_pages(),
            "expected_blocks": self.get_expected_pdf_blocks(),
            "processing_directory": processing_directory,
            "final_output_directory": final_output_directory,
            "idempotent_processing": self.is_idempotent_processing(),
            "timestamp_precision": self.get_timestamp_precision(),
            "validation_enabled": self.is_validation_enabled(),
            "default_engines": self.get_default_engines(),
            "encoding": self.get_default_encoding(),
            "image_handling": self.get_image_handling_config(),
            "mcp_overrides_active": bool(self._mcp_overrides)
        }
    
    def set_mcp_override(self, key: str, value: str) -> None:
        """Set an MCP override for dynamic file paths (future MCP integration)."""
        if self._mcp_overrides is None:
            self._mcp_overrides = {}
        self._mcp_overrides[key] = value
    
    def clear_mcp_overrides(self) -> None:
        """Clear all MCP overrides."""
        self._mcp_overrides = {}
    
    def get_mcp_overrides(self) -> Dict[str, str]:
        """Get current MCP overrides."""
        return self._mcp_overrides.copy() if self._mcp_overrides else {}
    
    def complete_processing_workflow(self) -> Dict[str, str]:
        """
        Complete the processing workflow by moving files from processing to final output.
        Returns:
            Dictionary with moved file paths
        """
        moved_files = {}
        processing_dir = Path(self.get_processing_directory())
        final_dir = Path(self.get_final_output_directory())
        
        if not processing_dir.exists():
            return moved_files
        
        # Ensure final directory exists
        final_dir.mkdir(parents=True, exist_ok=True)
        
        # Move all files from processing to final
        import shutil
        for file_path in processing_dir.iterdir():
            if file_path.is_file():
                dest_path = final_dir / file_path.name
                shutil.move(str(file_path), str(dest_path))
                moved_files[file_path.name] = str(dest_path)
        
        # Clean up empty processing directory
        if processing_dir.exists() and not any(processing_dir.iterdir()):
            processing_dir.rmdir()
        
        return moved_files
    
    def supports_mcp_integration(self) -> bool:
        """Check if configuration supports MCP integration."""
        return True  # Always true with current structure


# Global instance for easy access
file_manager = FileManager()


def get_target_pdf_path() -> str:
    """Convenience function to get target PDF path."""
    return file_manager.get_target_pdf_path()


def get_output_directory() -> str:
    """Convenience function to get output directory."""
    return file_manager.get_output_directory()


def ensure_output_directories() -> None:
    """Convenience function to ensure output directories exist."""
    file_manager.ensure_output_directories()


def complete_processing_workflow() -> Dict[str, str]:
    """
    Complete the processing workflow by moving files from processing to final output.
    Returns:
        Dictionary with moved file paths
    """
    return file_manager.complete_processing_workflow()


def validate_configuration() -> bool:
    """Validate the current configuration."""
    try:
        # Check if target PDF exists
        if not file_manager.validate_target_pdf():
            print(f"WARNING: Target PDF not found: {file_manager.get_target_pdf_path()}")
            return False
        
        # Ensure output directories can be created
        file_manager.ensure_output_directories()
        
        return True
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


if __name__ == "__main__":
    # Test the configuration
    print("File Manager Configuration Summary:")
    print(json.dumps(file_manager.get_config_summary(), indent=2))
    
    print(f"\nConfiguration valid: {validate_configuration()}")
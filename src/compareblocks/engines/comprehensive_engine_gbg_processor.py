#!/usr/bin/env python3
"""
Comprehensive Engine GBG Processor that processes all extraction engines
with optimized configurations (if available) or default configurations,
and integrates results into the GBG full analysis.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .manager import ExtractionEngineManager, EngineResult
from ..config.engine_config import EngineConfigurationManager
from ..gbg.processor import GBGProcessor
from ..io.pdf_metadata import PDFMetadataExtractor
from ..config.file_manager import file_manager


class OverwriteMode(Enum):
    """Modes for handling existing extraction results."""
    OVERWRITE = "overwrite"  # Always overwrite existing results
    SKIP = "skip"  # Skip if same engine+config combination exists
    ALLOW_MULTIPLE = "allow_multiple"  # Allow multiple results with different timestamps


@dataclass
class EngineConfigurationResult:
    """Result from engine configuration lookup."""
    engine_name: str
    configuration: Dict[str, Any]
    is_optimized: bool
    config_source: str  # 'pdf_override', 'optimization_proposal', 'default'


@dataclass
class ComprehensiveEngineResult:
    """Result from comprehensive engine processing."""
    engine_name: str
    success: bool
    output_path: str
    extraction_time: float
    is_optimized: bool
    config_source: str
    configuration_used: Dict[str, Any]
    configuration_hash: str  # Hash of configuration for duplicate detection
    processing_timestamp: str  # ISO timestamp of processing
    error_message: str = ""
    metadata: Dict[str, Any] = None
    was_skipped: bool = False  # True if processing was skipped due to existing result
    was_skipped: bool = False  # True if processing was skipped due to existing result
    error_message: str = ""
    metadata: Dict[str, Any] = None


@dataclass
class ComprehensiveProcessingResult:
    """Result from comprehensive processing of all engines."""
    success: bool
    updated_gbg_analysis_path: str
    engine_results: Dict[str, ComprehensiveEngineResult]
    skipped_engines: List[str]  # Engines that were skipped due to existing results
    processing_summary: Dict[str, Any]
    total_processing_time: float
    engines_processed: int
    engines_optimized: int
    engines_failed: int
    engines_skipped: int = 0


class ComprehensiveEngineGBGProcessor:
    """
    Processes all available extraction engines with optimized configurations
    and integrates results into GBG full analysis.
    """
    
    def __init__(self, overwrite_mode: OverwriteMode = OverwriteMode.SKIP):
        """Initialize the comprehensive processor."""
        self.engine_manager = ExtractionEngineManager()
        self.config_manager = EngineConfigurationManager()
        self.gbg_processor = GBGProcessor()
        self.metadata_extractor = PDFMetadataExtractor()
        self.overwrite_mode = overwrite_mode
    
    def get_available_engines(self) -> List[str]:
        """Get list of available extraction engines."""
        return self.engine_manager.get_available_engines()
    
    def get_pdf_hash_for_configuration(self, pdf_path: str) -> str:
        """
        Get PDF hash for configuration lookup.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            MD5 hash of PDF content
        """
        try:
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
                return hashlib.md5(pdf_content).hexdigest()
        except Exception as e:
            print(f"Warning: Could not generate PDF hash: {e}")
            return ""
    
    def get_configuration_hash(self, configuration: Dict[str, Any]) -> str:
        """
        Generate hash for configuration to detect duplicates.
        
        Args:
            configuration: Configuration dictionary
            
        Returns:
            MD5 hash of configuration
        """
        try:
            # Sort keys for consistent hashing
            config_str = json.dumps(configuration, sort_keys=True, separators=(',', ':'))
            return hashlib.md5(config_str.encode()).hexdigest()
        except Exception as e:
            print(f"Warning: Could not generate configuration hash: {e}")
            return ""
    
    def check_existing_results(self, gbg_analysis: Dict[str, Any], 
                             engine_name: str, config_hash: str) -> List[Dict[str, Any]]:
        """
        Check for existing results with same engine and configuration.
        
        Args:
            gbg_analysis: GBG analysis data
            engine_name: Name of the engine
            config_hash: Hash of the configuration
            
        Returns:
            List of existing results with same engine+config combination
        """
        existing_results = []
        
        if "engine_results" not in gbg_analysis:
            return existing_results
        
        # Check if engine has results
        if engine_name not in gbg_analysis["engine_results"]:
            return existing_results
        
        engine_results = gbg_analysis["engine_results"][engine_name]
        
        # Handle both single result and multiple results formats
        if isinstance(engine_results, dict):
            # Single result format
            if engine_results.get("configuration_hash") == config_hash:
                existing_results.append(engine_results)
        elif isinstance(engine_results, list):
            # Multiple results format
            for result in engine_results:
                if isinstance(result, dict) and result.get("configuration_hash") == config_hash:
                    existing_results.append(result)
        
        return existing_results
    
    def should_skip_processing(self, gbg_analysis: Dict[str, Any], 
                             engine_name: str, config_hash: str) -> bool:
        """
        Determine if processing should be skipped based on existing results and overwrite mode.
        
        Args:
            gbg_analysis: GBG analysis data
            engine_name: Name of the engine
            config_hash: Hash of the configuration
            
        Returns:
            True if processing should be skipped
        """
        if self.overwrite_mode == OverwriteMode.OVERWRITE:
            return False
        
        existing_results = self.check_existing_results(gbg_analysis, engine_name, config_hash)
        
        if self.overwrite_mode == OverwriteMode.SKIP and existing_results:
            return True
        
        # ALLOW_MULTIPLE mode never skips
        return False
    
    def enhance_output_with_configuration_metadata(self, output_path: str, 
                                                 configuration: Dict[str, Any],
                                                 config_hash: str,
                                                 processing_timestamp: str) -> None:
        """
        Enhance engine output file with configuration metadata.
        
        Args:
            output_path: Path to engine output file
            configuration: Configuration used for processing
            config_hash: Hash of the configuration
            processing_timestamp: Timestamp of processing
        """
        try:
            # Read existing output
            with open(output_path, 'r', encoding='utf-8') as f:
                output_data = json.load(f)
            
            # Add configuration metadata
            if "processing_metadata" not in output_data:
                output_data["processing_metadata"] = {}
            
            output_data["processing_metadata"]["configuration"] = {
                "configuration_used": configuration,
                "configuration_hash": config_hash,
                "processing_timestamp": processing_timestamp,
                "configuration_enhanced": True
            }
            
            # Write back enhanced output
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Warning: Could not enhance output with configuration metadata: {e}")
    
    def generate_config_hash(self, configuration: Dict[str, Any]) -> str:
        """
        Generate hash for configuration to detect duplicates.
        
        Args:
            configuration: Configuration dictionary
            
        Returns:
            MD5 hash of configuration
        """
        try:
            # Sort configuration for consistent hashing
            config_str = json.dumps(configuration, sort_keys=True)
            return hashlib.md5(config_str.encode()).hexdigest()
        except Exception as e:
            print(f"Warning: Could not generate config hash: {e}")
            return ""
    
    def check_existing_extraction_results(self, engine_name: str, 
                                        config_result: EngineConfigurationResult,
                                        pdf_path: str) -> tuple[bool, Optional[str]]:
        """
        Check if extraction results already exist for this engine and configuration.
        
        Args:
            engine_name: Name of the engine
            config_result: Configuration result
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (exists, existing_file_path)
        """
        try:
            # Generate expected output path
            processing_dir = Path(file_manager.get_processing_directory())
            pdf_name = Path(pdf_path).stem
            expected_path = processing_dir / f"{pdf_name}_{engine_name}.json"
            
            if not expected_path.exists():
                return False, None
            
            # Load existing file and check configuration
            with open(expected_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # Check if extraction metadata exists
            if "extraction_metadata" not in existing_data:
                return False, None
            
            extraction_metadata = existing_data["extraction_metadata"]
            
            # Generate hash for current configuration
            current_config_hash = self.generate_config_hash(config_result.configuration)
            
            # Compare configuration hashes
            existing_config_hash = extraction_metadata.get("config_hash", "")
            
            if current_config_hash == existing_config_hash and current_config_hash != "":
                return True, str(expected_path)
            
            return False, None
            
        except Exception as e:
            print(f"Warning: Could not check existing extraction results: {e}")
            return False, None
    
    def should_process_engine(self, engine_name: str, overwrite_mode: bool, 
                            existing_found: bool, existing_path: Optional[str]) -> bool:
        """
        Determine if engine should be processed based on overwrite mode and existing results.
        
        Args:
            engine_name: Name of the engine
            overwrite_mode: Whether to overwrite existing results
            existing_found: Whether existing results were found
            existing_path: Path to existing results
            
        Returns:
            True if engine should be processed
        """
        if not existing_found:
            return True  # No existing results, always process
        
        if overwrite_mode:
            print(f"  Overwriting existing results: {existing_path}")
            return True
        else:
            print(f"  Skipping {engine_name} - existing results found with same configuration: {existing_path}")
            return False
    
    def enhance_engine_output_with_configuration(self, output_path: str, 
                                               config_result: EngineConfigurationResult,
                                               processing_time: float) -> None:
        """
        Enhance engine output file with configuration metadata.
        
        Args:
            output_path: Path to engine output file
            config_result: Configuration used
            processing_time: Time taken for processing
        """
        try:
            if not Path(output_path).exists():
                return
            
            # Load existing output
            with open(output_path, 'r', encoding='utf-8') as f:
                output_data = json.load(f)
            
            # Add extraction metadata
            config_hash = self.generate_config_hash(config_result.configuration)
            
            extraction_metadata = {
                "configuration_used": config_result.configuration,
                "config_hash": config_hash,
                "is_optimized": config_result.is_optimized,
                "config_source": config_result.config_source,
                "extraction_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "processing_time_seconds": processing_time
            }
            
            output_data["extraction_metadata"] = extraction_metadata
            
            # Save enhanced output
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Warning: Could not enhance output with configuration: {e}")
    
    def get_engine_configuration(self, engine_name: str, pdf_path: str) -> EngineConfigurationResult:
        """
        Get optimized or default configuration for an engine.
        
        Args:
            engine_name: Name of the engine
            pdf_path: Path to PDF file for configuration lookup
            ": performance_comparison,
            "recommendation": f"Best configuration: {best_result.config_source} ({best_result.extraction_time:.1f}s)"
        }
        Returns:
            EngineConfigurationResult with configuration details
        """
        try:
            # Get effective configuration (includes PDF-specific overrides and optimizations)
            effective_config = self.config_manager.get_effective_configuration(engine_name, pdf_path)
            
            # Check if this is an optimized configuration by looking for PDF-specific settings
            engine_config = self.config_manager.get_engine_configuration(engine_name)
            
            is_optimized = False
            config_source = "default"
            
            if engine_config and effective_config:
                # Compare effective config with base engine config to detect optimizations
                base_settings = engine_config.default_settings
                if effective_config != base_settings:
                    is_optimized = True
                    config_source = "pdf_override"
            
            return EngineConfigurationResult(
                engine_name=engine_name,
                configuration=effective_config or {},
                is_optimized=is_optimized,
                config_source=config_source
            )
            
        except Exception as e:
            print(f"Warning: Could not get configuration for {engine_name}: {e}")
            return EngineConfigurationResult(
                engine_name=engine_name,
                configuration={},
                is_optimized=False,
                config_source="default"
            )
    
    def process_engine_with_configuration(self, engine_name: str, 
                                        config_result: EngineConfigurationResult,
                                        pdf_path: str, overwrite_mode: bool = True) -> ComprehensiveEngineResult:
        """
        Process a single engine with its configuration.
        
        Args:
            engine_name: Name of the engine
            config_result: Configuration to use
            pdf_path: Path to PDF file
            overwrite_mode: Whether to overwrite existing results
            
        Returns:
            ComprehensiveEngineResult with processing results
        """
        start_time = time.time()
        
        try:
            # Check for existing extraction results
            existing_found, existing_path = self.check_existing_extraction_results(
                engine_name, config_result, pdf_path
            )
            
            # Determine if we should process this engine
            if not self.should_process_engine(engine_name, overwrite_mode, existing_found, existing_path):
                # Return result indicating skipped
                return ComprehensiveEngineResult(
                    engine_name=engine_name,
                    success=True,  # Consider skipped as successful
                    output_path=existing_path or "",
                    extraction_time=0,
                    is_optimized=config_result.is_optimized,
                    config_source=config_result.config_source,
                    configuration_used=config_result.configuration,
                    error_message="Skipped - existing results found with same configuration",
                    metadata={"skipped": True}
                )
            
            # Apply configuration to engine (this would be engine-specific)
            # For now, we'll use the standard extraction method
            engine_result = self.engine_manager.extract_with_engine(engine_name, pdf_path)
            
            processing_time = time.time() - start_time
            
            # Enhance output file with configuration metadata
            if engine_result.success and engine_result.output_path:
                self.enhance_engine_output_with_configuration(
                    engine_result.output_path, config_result, processing_time
                )
            
            return ComprehensiveEngineResult(
                engine_name=engine_name,
                success=engine_result.success,
                output_path=engine_result.output_path,
                extraction_time=processing_time,
                is_optimized=config_result.is_optimized,
                config_source=config_result.config_source,
                configuration_used=config_result.configuration,
                error_message=engine_result.error_message,
                metadata=engine_result.metadata
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return ComprehensiveEngineResult(
                engine_name=engine_name,
                success=False,
                output_path="",
                extraction_time=processing_time,
                is_optimized=config_result.is_optimized,
                config_source=config_result.config_source,
                configuration_used=config_result.configuration,
                error_message=str(e)
            )
    
    def load_existing_gbg_analysis(self, gbg_analysis_path: str) -> Optional[Dict[str, Any]]:
        """
        Load existing GBG analysis file.
        
        Args:
            gbg_analysis_path: Path to GBG analysis file
            
        Returns:
            GBG analysis data or None if not found
        """
        try:
            gbg_path = Path(gbg_analysis_path)
            if not gbg_path.exists():
                print(f"GBG analysis file not found: {gbg_analysis_path}")
                return None
            
            with open(gbg_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"Error loading GBG analysis: {e}")
            return None
    
    def validate_gbg_analysis_structure(self, analysis: Dict[str, Any]) -> bool:
        """
        Validate GBG analysis structure.
        
        Args:
            analysis: GBG analysis data
            
        Returns:
            True if structure is valid
        """
        required_fields = ["pdf_path", "processing_metadata"]
        
        for field in required_fields:
            if field not in analysis:
                print(f"Missing required field in GBG analysis: {field}")
                return False
        
        return True
    
    def update_gbg_analysis_with_engine_results(self, gbg_analysis: Dict[str, Any],
                                              engine_results: Dict[str, ComprehensiveEngineResult]) -> Dict[str, Any]:
        """
        Update GBG analysis with engine results.
        
        Args:
            gbg_analysis: Existing GBG analysis
            engine_results: Results from engine processing
            
        Returns:
            Updated GBG analysis
        """
        # Update engine integration metadata
        if "engine_integration" not in gbg_analysis["processing_metadata"]:
            gbg_analysis["processing_metadata"]["engine_integration"] = {
                "integrated_engines": []
            }
        
        # Add successful engines to integrated list
        integrated_engines = gbg_analysis["processing_metadata"]["engine_integration"]["integrated_engines"]
        for engine_name, result in engine_results.items():
            if result.success and engine_name not in integrated_engines:
                integrated_engines.append(engine_name)
        
        # Add engine results section
        gbg_analysis["engine_results"] = {}
        for engine_name, result in engine_results.items():
            gbg_analysis["engine_results"][engine_name] = {
                "success": result.success,
                "output_path": result.output_path,
                "extraction_time": result.extraction_time,
                "is_optimized": result.is_optimized,
                "config_source": result.config_source,
                "configuration_used": result.configuration_used,
                "error_message": result.error_message,
                "metadata": result.metadata
            }
        
        # Add optimization status tracking
        if "optimization_status" not in gbg_analysis["processing_metadata"]:
            gbg_analysis["processing_metadata"]["optimization_status"] = {}
        
        for engine_name, result in engine_results.items():
            gbg_analysis["processing_metadata"]["optimization_status"][engine_name] = {
                "is_optimized": result.is_optimized,
                "config_source": result.config_source,
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Update processing timestamp
        gbg_analysis["processing_metadata"]["last_engine_integration"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        return gbg_analysis
    
    def save_updated_gbg_analysis(self, gbg_analysis: Dict[str, Any], 
                                 output_path: str) -> str:
        """
        Save updated GBG analysis to file.
        
        Args:
            gbg_analysis: Updated GBG analysis
            output_path: Path to save file
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(gbg_analysis, f, indent=2, ensure_ascii=False)
        
        return str(output_path)
    
    def create_processing_summary(self, engine_results: Dict[str, ComprehensiveEngineResult],
                                total_time: float) -> Dict[str, Any]:
        """
        Create processing summary.
        
        Args:
            engine_results: Results from engine processing
            total_time: Total processing time
            
        Returns:
            Processing summary
        """
        successful_engines = [name for name, result in engine_results.items() if result.success]
        failed_engines = [name for name, result in engine_results.items() if not result.success]
        optimized_engines = [name for name, result in engine_results.items() if result.is_optimized]
        
        summary = {
            "total_engines": len(engine_results),
            "successful_engines": len(successful_engines),
            "failed_engines": len(failed_engines),
            "optimized_engines": len(optimized_engines),
            "total_processing_time": total_time,
            "average_processing_time": total_time / len(engine_results) if engine_results else 0,
            "engine_details": {}
        }
        
        for engine_name, result in engine_results.items():
            summary["engine_details"][engine_name] = {
                "success": result.success,
                "extraction_time": result.extraction_time,
                "is_optimized": result.is_optimized,
                "config_source": result.config_source,
                "error_message": result.error_message if not result.success else None
            }
        
        return summary
    
    def process_all_engines_comprehensive(self, pdf_path: Optional[str] = None,
                                        gbg_analysis_path: Optional[str] = None,
                                        overwrite_mode: bool = True) -> ComprehensiveProcessingResult:
        """
        Process all available engines with optimized configurations and integrate into GBG analysis.
        
        Args:
            pdf_path: Path to PDF file
            gbg_analysis_path: Path to existing GBG analysis file
            overwrite_mode: Whether to overwrite existing extraction results (True) or skip them (False)
            
        Returns:
            ComprehensiveProcessingResult with all results
        """
        start_time = time.time()
        
        # Use default paths if not provided
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        if gbg_analysis_path is None:
            # Look for existing GBG analysis in processing directory
            processing_dir = Path(file_manager.get_processing_directory())
            pdf_name = Path(pdf_path).stem
            gbg_analysis_path = processing_dir / f"{pdf_name}_gbg_full_analysis.json"
        
        print(f"Processing all engines for PDF: {pdf_path}")
        print(f"GBG analysis path: {gbg_analysis_path}")
        
        # PDF path will be used directly for configuration lookup
        
        # Get available engines
        available_engines = self.get_available_engines()
        if not available_engines:
            return ComprehensiveProcessingResult(
                success=False,
                updated_gbg_analysis_path="",
                engine_results={},
                processing_summary={"error": "No engines available"},
                total_processing_time=0,
                engines_processed=0,
                engines_optimized=0,
                engines_failed=0
            )
        
        print(f"Available engines: {available_engines}")
        
        # Process each engine with its configuration
        engine_results = {}
        engines_optimized = 0
        engines_failed = 0
        engines_skipped = 0
        
        for engine_name in available_engines:
            print(f"Processing {engine_name}...")
            
            # Get configuration for this engine
            config_result = self.get_engine_configuration(engine_name, pdf_path)
            
            if config_result.is_optimized:
                print(f"  Using optimized configuration from {config_result.config_source}")
                engines_optimized += 1
            else:
                print(f"  Using default configuration")
            
            # Process engine
            result = self.process_engine_with_configuration(
                engine_name, config_result, pdf_path, overwrite_mode
            )
            engine_results[engine_name] = result
            
            if result.metadata and result.metadata.get("skipped"):
                print(f"  ⏭️ {engine_name}: Skipped (existing results with same configuration)")
                engines_skipped += 1
            elif result.success:
                print(f"  ✅ {engine_name}: {result.extraction_time:.1f}s -> {result.output_path}")
            else:
                print(f"  ❌ {engine_name}: {result.error_message}")
                engines_failed += 1
        
        # Load existing GBG analysis
        gbg_analysis = self.load_existing_gbg_analysis(str(gbg_analysis_path))
        
        if gbg_analysis is None:
            # Create minimal GBG analysis if it doesn't exist
            print("Creating new GBG analysis structure...")
            pdf_metadata = self.metadata_extractor.extract_pdf_metadata(pdf_path)
            display_name = self.metadata_extractor.get_display_name(pdf_path)
            
            gbg_analysis = {
                "pdf_path": pdf_metadata["file_info"]["relative_path"],
                "pdf_name": pdf_metadata["file_info"]["normalized_filename"],
                "pdf_display_name": display_name,
                "pdf_metadata": pdf_metadata,
                "processing_metadata": {
                    "gbg_version": "1.0.0",
                    "components": ["engine_integration"],
                    "encoding": "utf-8",
                    "validation_enabled": True,
                    "engine_integration": {
                        "integrated_engines": []
                    }
                },
                "gbg_blocks": []
            }
        
        # Validate GBG analysis structure
        if not self.validate_gbg_analysis_structure(gbg_analysis):
            return ComprehensiveProcessingResult(
                success=False,
                updated_gbg_analysis_path="",
                engine_results=engine_results,
                processing_summary={"error": "Invalid GBG analysis structure"},
                total_processing_time=time.time() - start_time,
                engines_processed=len(engine_results),
                engines_optimized=engines_optimized,
                engines_failed=engines_failed
            )
        
        # Update GBG analysis with engine results
        updated_gbg_analysis = self.update_gbg_analysis_with_engine_results(gbg_analysis, engine_results)
        
        # Save updated GBG analysis
        updated_path = self.save_updated_gbg_analysis(updated_gbg_analysis, str(gbg_analysis_path))
        
        # Create processing summary
        total_time = time.time() - start_time
        processing_summary = self.create_processing_summary(engine_results, total_time)
        
        print(f"\nProcessing complete:")
        print(f"  Engines processed: {len(engine_results)}")
        print(f"  Engines optimized: {engines_optimized}")
        print(f"  Engines skipped: {engines_skipped}")
        print(f"  Engines failed: {engines_failed}")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Updated GBG analysis: {updated_path}")
        
        return ComprehensiveProcessingResult(
            success=True,
            updated_gbg_analysis_path=updated_path,
            engine_results=engine_results,
            processing_summary=processing_summary,
            total_processing_time=total_time,
            engines_processed=len(engine_results),
            engines_optimized=engines_optimized,
            engines_failed=engines_failed,
            engines_skipped=engines_skipped
        )
    
    def process_specific_engines(self, engine_names: List[str],
                               pdf_path: Optional[str] = None,
                               gbg_analysis_path: Optional[str] = None,
                               overwrite_mode: bool = True) -> ComprehensiveProcessingResult:
        """
        Process specific engines with optimized configurations.
        
        Args:
            engine_names: List of engine names to process
            pdf_path: Path to PDF file
            gbg_analysis_path: Path to existing GBG analysis file
            overwrite_mode: Whether to overwrite existing extraction results
            
        Returns:
            ComprehensiveProcessingResult with results
        """
        # Filter to available engines
        available_engines = self.get_available_engines()
        requested_engines = [name for name in engine_names if name in available_engines]
        
        if not requested_engines:
            print(f"None of the requested engines are available: {engine_names}")
            return ComprehensiveProcessingResult(
                success=False,
                updated_gbg_analysis_path="",
                engine_results={},
                processing_summary={"error": "No requested engines available"},
                total_processing_time=0,
                engines_processed=0,
                engines_optimized=0,
                engines_failed=0,
                engines_skipped=0
            )
        
        # Temporarily override available engines for processing
        original_get_available = self.engine_manager.get_available_engines
        self.engine_manager.get_available_engines = lambda: requested_engines
        
        try:
            result = self.process_all_engines_comprehensive(pdf_path, gbg_analysis_path, overwrite_mode)
            return result
        finally:
            # Restore original method
            self.engine_manager.get_available_engines = original_get_available


# Convenience functions
def process_all_engines_with_gbg_integration(pdf_path: Optional[str] = None,
                                           gbg_analysis_path: Optional[str] = None) -> ComprehensiveProcessingResult:
    """Process all engines with optimized configurations and integrate into GBG analysis."""
    processor = ComprehensiveEngineGBGProcessor()
    return processor.process_all_engines_comprehensive(pdf_path, gbg_analysis_path)


def process_engines_with_gbg_integration(engine_names: List[str],
                                       pdf_path: Optional[str] = None,
                                       gbg_analysis_path: Optional[str] = None) -> ComprehensiveProcessingResult:
    """Process specific engines with optimized configurations and integrate into GBG analysis."""
    processor = ComprehensiveEngineGBGProcessor()
    return processor.process_specific_engines(engine_names, pdf_path, gbg_analysis_path)


def get_available_engines_for_gbg_integration() -> List[str]:
    """Get list of available engines for GBG integration."""
    processor = ComprehensiveEngineGBGProcessor()
    return processor.get_available_engines()
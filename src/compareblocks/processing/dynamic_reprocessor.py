# src/compareblocks/processing/dynamic_reprocessor.py
"""
Dynamic Reprocessing Engine for BECR system.

Provides functions for rebuilding all comparisons vs. adding only new ones,
incremental processing when new associated files are added, reprocessing triggers
that update consistency percentages, and version tracking for processing different
configurations with the option to only store stats and config without supporting data.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

from ..engines.manager import ExtractionEngineManager
from ..config.engine_config import EngineConfigurationManager
from ..association.manager import AssociationManager
from ..features.consistency import CharacterConsistencyTracker, CharacterConsistency
from ..io.pdf_metadata import PDFMetadataExtractor
from ..config.file_manager import file_manager


class ProcessingMode(Enum):
    """Processing modes for dynamic reprocessing."""
    REBUILD_ALL = "rebuild_all"  # Rebuild all comparisons from scratch
    INCREMENTAL = "incremental"  # Add only new comparisons
    UPDATE_CONSISTENCY = "update_consistency"  # Update consistency percentages only
    STATS_ONLY = "stats_only"  # Store only stats and config, no supporting data


class VersionStorageMode(Enum):
    """Storage modes for version tracking."""
    FULL_DATA = "full_data"  # Store complete processing data
    STATS_ONLY = "stats_only"  # Store only statistics and configuration
    CONFIG_ONLY = "config_only"  # Store only configuration metadata


@dataclass
class ProcessingVersion:
    """Version information for a processing run."""
    version_id: str
    timestamp: str
    configuration_hash: str
    configuration: Dict[str, Any]
    processing_mode: ProcessingMode
    storage_mode: VersionStorageMode
    engines_used: List[str]
    file_count: int
    block_count: int
    consistency_stats: Dict[str, float]
    processing_time: float
    parent_version_id: Optional[str] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class ReprocessingTrigger:
    """Trigger for reprocessing based on changes."""
    trigger_type: str  # 'new_files', 'config_change', 'manual', 'consistency_update'
    trigger_data: Dict[str, Any]
    timestamp: str
    requires_full_rebuild: bool = False


@dataclass
class IncrementalUpdate:
    """Information about an incremental update."""
    update_id: str
    base_version_id: str
    new_files: List[str]
    updated_blocks: List[str]
    consistency_changes: Dict[str, float]
    processing_time: float
    timestamp: str


class DynamicReprocessor:
    """Dynamic reprocessing engine for BECR system."""
    
    def __init__(self, storage_directory: Optional[str] = None):
        """Initialize the dynamic reprocessor."""
        self.engine_manager = ExtractionEngineManager()
        self.config_manager = EngineConfigurationManager()
        self.association_manager = AssociationManager()
        self.consistency_tracker = CharacterConsistencyTracker()
        self.metadata_extractor = PDFMetadataExtractor()
        
        # Set up storage directory
        if storage_directory:
            self.storage_dir = Path(storage_directory)
        else:
            self.storage_dir = Path(file_manager.get_processing_directory()) / "dynamic_processing"
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Version tracking
        self.versions_file = self.storage_dir / "processing_versions.ndjson"
        self.triggers_file = self.storage_dir / "reprocessing_triggers.ndjson"
        self.incremental_updates_file = self.storage_dir / "incremental_updates.ndjson"
    
    def generate_configuration_hash(self, configuration: Dict[str, Any]) -> str:
        """Generate hash for configuration to detect changes."""
        try:
            # Sort keys for consistent hashing
            config_str = json.dumps(configuration, sort_keys=True, ensure_ascii=False)
            return hashlib.md5(config_str.encode()).hexdigest()
        except Exception as e:
            print(f"Warning: Could not generate configuration hash: {e}")
            return ""
    
    def get_current_configuration(self, pdf_path: str, include_timestamp: bool = False) -> Dict[str, Any]:
        """Get current effective configuration for all engines."""
        configuration = {
            "pdf_path": pdf_path,
            "engines": {},
            "global_settings": {}
        }
        
        # Only include timestamp if explicitly requested (for version creation)
        if include_timestamp:
            configuration["timestamp"] = datetime.now().isoformat()
        
        available_engines = self.engine_manager.get_available_engines()
        
        for engine_name in available_engines:
            engine_config = self.config_manager.get_effective_configuration(engine_name, pdf_path)
            configuration["engines"][engine_name] = engine_config
        
        return configuration
    
    def create_processing_version(self, pdf_path: str, processing_mode: ProcessingMode,
                                storage_mode: VersionStorageMode, 
                                engines_used: List[str],
                                parent_version_id: Optional[str] = None,
                                description: str = "") -> ProcessingVersion:
        """Create a new processing version."""
        configuration = self.get_current_configuration(pdf_path, include_timestamp=True)
        config_hash = self.generate_configuration_hash(configuration)
        
        version = ProcessingVersion(
            version_id=f"v_{int(time.time())}_{config_hash[:8]}",
            timestamp=datetime.now().isoformat(),
            configuration_hash=config_hash,
            configuration=configuration,
            processing_mode=processing_mode,
            storage_mode=storage_mode,
            engines_used=engines_used,
            file_count=0,  # Will be updated during processing
            block_count=0,  # Will be updated during processing
            consistency_stats={},  # Will be updated during processing
            processing_time=0.0,  # Will be updated during processing
            parent_version_id=parent_version_id,
            description=description,
            tags=["auto_generated"]
        )
        
        return version
    
    def save_processing_version(self, version: ProcessingVersion) -> None:
        """Save processing version to storage."""
        # Convert to dict and handle enum serialization
        version_dict = asdict(version)
        version_dict['processing_mode'] = version.processing_mode.value
        version_dict['storage_mode'] = version.storage_mode.value
        
        with open(self.versions_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(version_dict, ensure_ascii=False) + '\n')
    
    def load_processing_versions(self) -> List[ProcessingVersion]:
        """Load all processing versions."""
        versions = []
        
        if self.versions_file.exists():
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            # Convert enum strings back to enums
                            data['processing_mode'] = ProcessingMode(data['processing_mode'])
                            data['storage_mode'] = VersionStorageMode(data['storage_mode'])
                            versions.append(ProcessingVersion(**data))
                        except Exception as e:
                            print(f"Warning: Could not load version: {e}")
        
        return versions
    
    def get_latest_version(self, pdf_path: str) -> Optional[ProcessingVersion]:
        """Get the latest processing version for a PDF."""
        versions = self.load_processing_versions()
        pdf_versions = [v for v in versions if v.configuration.get("pdf_path") == pdf_path]
        
        if pdf_versions:
            # Sort by timestamp and return latest
            pdf_versions.sort(key=lambda x: x.timestamp, reverse=True)
            return pdf_versions[0]
        
        return None
    
    def detect_configuration_changes(self, pdf_path: str) -> Tuple[bool, Dict[str, Any]]:
        """Detect if configuration has changed since last processing."""
        latest_version = self.get_latest_version(pdf_path)
        
        if not latest_version:
            return True, {"reason": "no_previous_version"}
        
        # Get current config without timestamp for comparison
        current_config = self.get_current_configuration(pdf_path, include_timestamp=False)
        current_hash = self.generate_configuration_hash(current_config)
        
        # Compare with stored configuration hash (which was generated with timestamp)
        # We need to generate hash from stored config without timestamp for fair comparison
        stored_config = latest_version.configuration.copy()
        if "timestamp" in stored_config:
            del stored_config["timestamp"]
        stored_hash = self.generate_configuration_hash(stored_config)
        
        if current_hash != stored_hash:
            # Find specific changes
            changes = self._compare_configurations(stored_config, current_config)
            return True, {"reason": "configuration_changed", "changes": changes}
        
        return False, {"reason": "no_changes"}
    
    def _compare_configurations(self, old_config: Dict[str, Any], 
                              new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two configurations and identify changes."""
        changes = {
            "engines_added": [],
            "engines_removed": [],
            "engines_modified": {},
            "global_changes": {}
        }
        
        old_engines = set(old_config.get("engines", {}).keys())
        new_engines = set(new_config.get("engines", {}).keys())
        
        changes["engines_added"] = list(new_engines - old_engines)
        changes["engines_removed"] = list(old_engines - new_engines)
        
        # Check for modifications in common engines
        common_engines = old_engines & new_engines
        for engine in common_engines:
            old_engine_config = old_config["engines"][engine]
            new_engine_config = new_config["engines"][engine]
            
            if old_engine_config != new_engine_config:
                changes["engines_modified"][engine] = {
                    "old": old_engine_config,
                    "new": new_engine_config
                }
        
        return changes
    
    def detect_new_associated_files(self, pdf_path: str) -> Tuple[bool, List[str]]:
        """Detect if new associated files have been added."""
        latest_version = self.get_latest_version(pdf_path)
        
        # Get current associations
        current_associations = self.association_manager.load_associations_for_pdf(pdf_path)
        current_files = set(current_associations.associations.keys())
        
        if not latest_version:
            return bool(current_files), list(current_files)
        
        # Compare with previous file count (simplified approach)
        # In a full implementation, we'd store the actual file list
        if len(current_files) > latest_version.file_count:
            # Estimate new files (this is simplified)
            estimated_new_count = len(current_files) - latest_version.file_count
            new_files = list(current_files)[-estimated_new_count:]
            return True, new_files
        
        return False, []
    
    def create_reprocessing_trigger(self, trigger_type: str, trigger_data: Dict[str, Any],
                                  requires_full_rebuild: bool = False) -> ReprocessingTrigger:
        """Create a reprocessing trigger."""
        trigger = ReprocessingTrigger(
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            timestamp=datetime.now().isoformat(),
            requires_full_rebuild=requires_full_rebuild
        )
        
        # Save trigger
        with open(self.triggers_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(trigger), ensure_ascii=False) + '\n')
        
        return trigger
    
    def rebuild_all_comparisons(self, pdf_path: str, 
                              storage_mode: VersionStorageMode = VersionStorageMode.FULL_DATA,
                              description: str = "Full rebuild of all comparisons") -> ProcessingVersion:
        """
        Rebuild all comparisons from scratch.
        
        Args:
            pdf_path: Path to PDF file
            storage_mode: How to store the results
            description: Description of the rebuild
            
        Returns:
            ProcessingVersion with results
        """
        start_time = time.time()
        
        print(f"Starting full rebuild for: {pdf_path}")
        
        # Create processing version
        available_engines = self.engine_manager.get_available_engines()
        version = self.create_processing_version(
            pdf_path, ProcessingMode.REBUILD_ALL, storage_mode, 
            available_engines, description=description
        )
        
        # Load all associations
        associations = self.association_manager.load_associations_for_pdf(pdf_path)
        version.file_count = len(associations.associations)
        
        # Process all engines (simplified - in full implementation would run actual engines)
        consistency_results = {}
        block_count = 0
        
        # Simulate processing all blocks with all variations
        for file_path, parsed_content in associations.associations.items():
            # Extract blocks from content (simplified)
            blocks = self._extract_blocks_from_content(parsed_content.text_content)
            block_count += len(blocks)
            
            for block_id, block_text in blocks.items():
                # Get all variations for this block from all files
                variations = self._get_block_variations(block_id, associations)
                
                # Calculate consistency
                consistency = self.consistency_tracker.track_consistency_for_block(
                    block_id, variations
                )
                consistency_results[block_id] = consistency
        
        version.block_count = block_count
        version.processing_time = time.time() - start_time
        
        # Calculate overall consistency stats
        if consistency_results:
            char_scores = [c.character_consistency_score for c in consistency_results.values()]
            word_scores = [c.word_consistency_score for c in consistency_results.values()]
            spelling_scores = [c.spelling_accuracy_score for c in consistency_results.values()]
            
            version.consistency_stats = {
                "average_character_consistency": sum(char_scores) / len(char_scores),
                "average_word_consistency": sum(word_scores) / len(word_scores),
                "average_spelling_accuracy": sum(spelling_scores) / len(spelling_scores),
                "total_blocks": len(consistency_results)
            }
        
        # Save version and results based on storage mode
        if storage_mode == VersionStorageMode.FULL_DATA:
            self._save_full_processing_data(version, consistency_results, associations)
        elif storage_mode == VersionStorageMode.STATS_ONLY:
            self._save_stats_only(version)
        else:  # CONFIG_ONLY
            self._save_config_only(version)
        
        self.save_processing_version(version)
        
        print(f"Full rebuild completed in {version.processing_time:.1f}s")
        print(f"Processed {version.block_count} blocks from {version.file_count} files")
        
        return version
    
    def incremental_processing(self, pdf_path: str, new_files: List[str],
                             base_version_id: Optional[str] = None) -> IncrementalUpdate:
        """
        Process only new associated files incrementally.
        
        Args:
            pdf_path: Path to PDF file
            new_files: List of new files to process
            base_version_id: Base version to build upon
            
        Returns:
            IncrementalUpdate with results
        """
        start_time = time.time()
        
        print(f"Starting incremental processing for {len(new_files)} new files")
        
        if not base_version_id:
            latest_version = self.get_latest_version(pdf_path)
            base_version_id = latest_version.version_id if latest_version else None
        
        # Load new associations
        associations = self.association_manager.load_associations_for_pdf(pdf_path)
        
        # Process only new files
        updated_blocks = []
        consistency_changes = {}
        
        for file_path in new_files:
            if file_path in associations.associations:
                parsed_content = associations.associations[file_path]
                blocks = self._extract_blocks_from_content(parsed_content.text_content)
                
                for block_id, block_text in blocks.items():
                    # Get updated variations including new file
                    variations = self._get_block_variations(block_id, associations)
                    
                    # Recalculate consistency
                    new_consistency = self.consistency_tracker.track_consistency_for_block(
                        block_id, variations
                    )
                    
                    # Store change (simplified - would compare with previous)
                    consistency_changes[block_id] = new_consistency.character_consistency_score
                    updated_blocks.append(block_id)
        
        update = IncrementalUpdate(
            update_id=f"inc_{int(time.time())}",
            base_version_id=base_version_id or "none",
            new_files=new_files,
            updated_blocks=updated_blocks,
            consistency_changes=consistency_changes,
            processing_time=time.time() - start_time,
            timestamp=datetime.now().isoformat()
        )
        
        # Save incremental update
        with open(self.incremental_updates_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(update), ensure_ascii=False) + '\n')
        
        print(f"Incremental processing completed in {update.processing_time:.1f}s")
        print(f"Updated {len(updated_blocks)} blocks")
        
        return update
    
    def update_consistency_percentages(self, pdf_path: str) -> Dict[str, float]:
        """
        Update consistency percentages without full reprocessing.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Updated consistency statistics
        """
        print("Updating consistency percentages...")
        
        # Load current associations
        associations = self.association_manager.load_associations_for_pdf(pdf_path)
        
        # Recalculate consistency for all blocks
        consistency_results = {}
        
        # Get all unique blocks across all files
        all_blocks = set()
        for parsed_content in associations.associations.values():
            blocks = self._extract_blocks_from_content(parsed_content.text_content)
            all_blocks.update(blocks.keys())
        
        for block_id in all_blocks:
            variations = self._get_block_variations(block_id, associations)
            consistency = self.consistency_tracker.track_consistency_for_block(
                block_id, variations
            )
            consistency_results[block_id] = consistency
        
        # Calculate overall stats
        if consistency_results:
            char_scores = [c.character_consistency_score for c in consistency_results.values()]
            word_scores = [c.word_consistency_score for c in consistency_results.values()]
            spelling_scores = [c.spelling_accuracy_score for c in consistency_results.values()]
            
            updated_stats = {
                "average_character_consistency": sum(char_scores) / len(char_scores),
                "average_word_consistency": sum(word_scores) / len(word_scores),
                "average_spelling_accuracy": sum(spelling_scores) / len(spelling_scores),
                "total_blocks": len(consistency_results),
                "update_timestamp": datetime.now().isoformat()
            }
        else:
            updated_stats = {
                "average_character_consistency": 0.0,
                "average_word_consistency": 0.0,
                "average_spelling_accuracy": 0.0,
                "total_blocks": 0,
                "update_timestamp": datetime.now().isoformat()
            }
        
        print(f"Updated consistency for {len(consistency_results)} blocks")
        
        return updated_stats
    
    def _extract_blocks_from_content(self, text_content: str) -> Dict[str, str]:
        """Extract blocks from text content (simplified implementation)."""
        # This is a simplified implementation
        # In reality, this would use proper block detection
        lines = text_content.split('\n')
        blocks = {}
        
        block_index = 0
        for line in lines:
            if line.strip():  # Only non-empty lines
                block_id = f"block_{block_index}"
                blocks[block_id] = line.strip()
                block_index += 1
        
        return blocks
    
    def _get_block_variations(self, block_id: str, associations) -> List[str]:
        """Get all variations of a block from all associated files."""
        variations = []
        
        for file_path, parsed_content in associations.associations.items():
            blocks = self._extract_blocks_from_content(parsed_content.text_content)
            if block_id in blocks:
                variations.append(blocks[block_id])
        
        return variations
    
    def _save_full_processing_data(self, version: ProcessingVersion, 
                                 consistency_results: Dict[str, CharacterConsistency],
                                 associations) -> None:
        """Save full processing data."""
        data_file = self.storage_dir / f"{version.version_id}_full_data.json"
        
        # Convert version to dict with enum handling
        version_dict = asdict(version)
        version_dict['processing_mode'] = version.processing_mode.value
        version_dict['storage_mode'] = version.storage_mode.value
        
        data = {
            "version": version_dict,
            "consistency_results": {
                block_id: consistency.to_dict() 
                for block_id, consistency in consistency_results.items()
            },
            "associations_summary": {
                "total_files": len(associations.associations),
                "file_paths": list(associations.associations.keys())
            }
        }
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _save_stats_only(self, version: ProcessingVersion) -> None:
        """Save only statistics and configuration."""
        stats_file = self.storage_dir / f"{version.version_id}_stats_only.json"
        
        stats_data = {
            "version_id": version.version_id,
            "timestamp": version.timestamp,
            "configuration_hash": version.configuration_hash,
            "configuration": version.configuration,
            "consistency_stats": version.consistency_stats,
            "processing_time": version.processing_time,
            "file_count": version.file_count,
            "block_count": version.block_count,
            "storage_mode": "stats_only"
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, indent=2, ensure_ascii=False)
    
    def _save_config_only(self, version: ProcessingVersion) -> None:
        """Save only configuration metadata."""
        config_file = self.storage_dir / f"{version.version_id}_config_only.json"
        
        config_data = {
            "version_id": version.version_id,
            "timestamp": version.timestamp,
            "configuration_hash": version.configuration_hash,
            "configuration": version.configuration,
            "processing_mode": version.processing_mode.value,
            "storage_mode": "config_only"
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    def get_processing_history(self, pdf_path: str) -> List[ProcessingVersion]:
        """Get processing history for a PDF."""
        versions = self.load_processing_versions()
        return [v for v in versions if v.configuration.get("pdf_path") == pdf_path]
    
    def cleanup_old_versions(self, pdf_path: str, keep_count: int = 10) -> int:
        """Clean up old processing versions, keeping only the most recent."""
        history = self.get_processing_history(pdf_path)
        
        if len(history) <= keep_count:
            return 0
        
        # Sort by timestamp and keep only recent ones
        history.sort(key=lambda x: x.timestamp, reverse=True)
        to_remove = history[keep_count:]
        
        removed_count = 0
        for version in to_remove:
            # Remove associated data files
            for suffix in ["_full_data.json", "_stats_only.json", "_config_only.json"]:
                data_file = self.storage_dir / f"{version.version_id}{suffix}"
                if data_file.exists():
                    data_file.unlink()
                    removed_count += 1
        
        # Rewrite versions file without removed versions
        remaining_versions = [v for v in self.load_processing_versions() if v not in to_remove]
        
        with open(self.versions_file, 'w', encoding='utf-8') as f:
            for version in remaining_versions:
                # Convert to dict and handle enum serialization
                version_dict = asdict(version)
                version_dict['processing_mode'] = version.processing_mode.value
                version_dict['storage_mode'] = version.storage_mode.value
                f.write(json.dumps(version_dict, ensure_ascii=False) + '\n')
        
        return len(to_remove)


# Convenience functions
def rebuild_all_comparisons(pdf_path: str, 
                          storage_mode: VersionStorageMode = VersionStorageMode.FULL_DATA) -> ProcessingVersion:
    """Rebuild all comparisons for a PDF."""
    reprocessor = DynamicReprocessor()
    return reprocessor.rebuild_all_comparisons(pdf_path, storage_mode)


def incremental_processing_for_new_files(pdf_path: str, new_files: List[str]) -> IncrementalUpdate:
    """Process new files incrementally."""
    reprocessor = DynamicReprocessor()
    return reprocessor.incremental_processing(pdf_path, new_files)


def update_consistency_percentages(pdf_path: str) -> Dict[str, float]:
    """Update consistency percentages for a PDF."""
    reprocessor = DynamicReprocessor()
    return reprocessor.update_consistency_percentages(pdf_path)


def detect_reprocessing_needs(pdf_path: str) -> Dict[str, Any]:
    """Detect if reprocessing is needed for a PDF."""
    reprocessor = DynamicReprocessor()
    
    config_changed, config_info = reprocessor.detect_configuration_changes(pdf_path)
    new_files_detected, new_files = reprocessor.detect_new_associated_files(pdf_path)
    
    return {
        "needs_reprocessing": config_changed or new_files_detected,
        "configuration_changed": config_changed,
        "configuration_info": config_info,
        "new_files_detected": new_files_detected,
        "new_files": new_files,
        "recommended_action": "rebuild_all" if config_changed else "incremental" if new_files_detected else "none"
    }
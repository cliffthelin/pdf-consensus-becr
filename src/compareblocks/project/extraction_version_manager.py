# src/compareblocks/project/extraction_version_manager.py
"""
Enhanced version control for extraction JSON files.
Tracks multiple extractions from the same engine with different configurations,
manages extraction history, and provides smart version comparison.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class ExtractionFormat(Enum):
    """Supported extraction file formats."""
    NDJSON = "ndjson"
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    TXT = "txt"
    MD = "markdown"


@dataclass
class ExtractionMetadata:
    """Metadata for an extraction file."""
    file_path: str
    engine_name: str
    configuration_hash: str
    configuration: Dict[str, Any]
    extraction_timestamp: str
    file_format: ExtractionFormat
    file_size: int
    block_count: int
    checksum: str
    pdf_source: str
    version_number: int
    parent_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['file_format'] = self.file_format.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractionMetadata':
        """Create from dictionary."""
        data = data.copy()
        data['file_format'] = ExtractionFormat(data['file_format'])
        return cls(**data)


@dataclass
class ExtractionVersion:
    """Version information for an extraction."""
    version_id: str
    engine_name: str
    configuration_hash: str
    extraction_files: List[str]
    metadata: List[ExtractionMetadata]
    created_timestamp: str
    is_active: bool = True
    comparison_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineExtractionHistory:
    """Complete extraction history for an engine."""
    engine_name: str
    pdf_path: str
    versions: List[ExtractionVersion] = field(default_factory=list)
    active_version_id: Optional[str] = None
    total_extractions: int = 0


class ExtractionVersionManager:
    """Manages version control for extraction JSON files."""
    
    def __init__(self, storage_directory: Optional[str] = None):
        """Initialize the extraction version manager."""
        if storage_directory:
            self.storage_dir = Path(storage_directory)
        else:
            from ..config.file_manager import file_manager
            self.storage_dir = Path(file_manager.get_processing_directory()) / "extraction_versions"
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage files
        self.metadata_file = self.storage_dir / "extraction_metadata.ndjson"
        self.versions_file = self.storage_dir / "extraction_versions.ndjson"
        self.history_file = self.storage_dir / "engine_history.ndjson"
        
        # In-memory cache
        self._metadata_cache: Dict[str, ExtractionMetadata] = {}
        self._version_cache: Dict[str, ExtractionVersion] = {}
        self._history_cache: Dict[Tuple[str, str], EngineExtractionHistory] = {}
    
    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum for a file."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _calculate_configuration_hash(self, configuration: Dict[str, Any]) -> str:
        """Calculate hash for configuration."""
        try:
            config_str = json.dumps(configuration, sort_keys=True, ensure_ascii=False)
            return hashlib.md5(config_str.encode()).hexdigest()
        except Exception:
            return ""
    
    def _detect_file_format(self, file_path: str) -> ExtractionFormat:
        """Detect file format from extension."""
        suffix = Path(file_path).suffix.lower()
        format_map = {
            '.ndjson': ExtractionFormat.NDJSON,
            '.json': ExtractionFormat.JSON,
            '.csv': ExtractionFormat.CSV,
            '.html': ExtractionFormat.HTML,
            '.txt': ExtractionFormat.TXT,
            '.md': ExtractionFormat.MD
        }
        return format_map.get(suffix, ExtractionFormat.TXT)
    
    def _count_blocks_in_file(self, file_path: str, file_format: ExtractionFormat) -> int:
        """Count blocks in extraction file."""
        try:
            if file_format == ExtractionFormat.NDJSON:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return sum(1 for line in f if line.strip())
            elif file_format == ExtractionFormat.JSON:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return len(data)
                    elif isinstance(data, dict) and 'blocks' in data:
                        return len(data['blocks'])
            return 0
        except Exception:
            return 0
    
    def register_extraction(self, file_path: str, engine_name: str,
                          configuration: Dict[str, Any], pdf_source: str,
                          tags: List[str] = None, notes: str = "") -> ExtractionMetadata:
        """
        Register a new extraction file with version tracking.
        
        Args:
            file_path: Path to extraction file
            engine_name: Name of extraction engine
            configuration: Engine configuration used
            pdf_source: Source PDF path
            tags: Optional tags for categorization
            notes: Optional notes about this extraction
            
        Returns:
            ExtractionMetadata for the registered file
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Extraction file not found: {file_path}")
        
        # Calculate metadata
        config_hash = self._calculate_configuration_hash(configuration)
        file_format = self._detect_file_format(file_path)
        file_size = file_path_obj.stat().st_size
        block_count = self._count_blocks_in_file(file_path, file_format)
        checksum = self._calculate_file_checksum(file_path)
        
        # Get version number for this engine/config combination
        version_number = self._get_next_version_number(engine_name, pdf_source, config_hash)
        
        # Create metadata
        metadata = ExtractionMetadata(
            file_path=str(file_path),
            engine_name=engine_name,
            configuration_hash=config_hash,
            configuration=configuration,
            extraction_timestamp=datetime.now().isoformat(),
            file_format=file_format,
            file_size=file_size,
            block_count=block_count,
            checksum=checksum,
            pdf_source=pdf_source,
            version_number=version_number,
            tags=tags or [],
            notes=notes
        )
        
        # Save metadata
        self._save_metadata(metadata)
        
        # Update version tracking
        self._update_version_tracking(metadata)
        
        # Update history
        self._update_engine_history(metadata)
        
        return metadata
    
    def _get_next_version_number(self, engine_name: str, pdf_source: str, 
                                 config_hash: str) -> int:
        """Get next version number for engine/config combination."""
        # Load all metadata to find existing versions
        all_metadata = self.load_all_metadata()
        
        # Find versions with same engine, pdf, and config hash
        matching_versions = []
        for metadata in all_metadata.values():
            if (metadata.engine_name == engine_name and 
                metadata.pdf_source == pdf_source and
                metadata.configuration_hash == config_hash):
                matching_versions.append(metadata.version_number)
        
        if matching_versions:
            return max(matching_versions) + 1
        return 1
    
    def _save_metadata(self, metadata: ExtractionMetadata) -> None:
        """Save extraction metadata."""
        with open(self.metadata_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(metadata.to_dict(), ensure_ascii=False) + '\n')
        
        # Update cache
        self._metadata_cache[metadata.file_path] = metadata
    
    def _update_version_tracking(self, metadata: ExtractionMetadata) -> None:
        """Update version tracking for extraction."""
        # Find or create version
        version_id = f"{metadata.engine_name}_{metadata.configuration_hash[:8]}"
        
        if version_id in self._version_cache:
            version = self._version_cache[version_id]
            version.extraction_files.append(metadata.file_path)
            version.metadata.append(metadata)
        else:
            version = ExtractionVersion(
                version_id=version_id,
                engine_name=metadata.engine_name,
                configuration_hash=metadata.configuration_hash,
                extraction_files=[metadata.file_path],
                metadata=[metadata],
                created_timestamp=metadata.extraction_timestamp,
                is_active=True
            )
            self._version_cache[version_id] = version
        
        # Save version
        self._save_version(version)
    
    def _save_version(self, version: ExtractionVersion) -> None:
        """Save extraction version."""
        # Convert metadata list to dicts
        version_dict = asdict(version)
        version_dict['metadata'] = [m.to_dict() for m in version.metadata]
        
        # Rewrite versions file (simplified - in production would use better approach)
        all_versions = self.load_all_versions()
        all_versions[version.version_id] = version
        
        with open(self.versions_file, 'w', encoding='utf-8') as f:
            for v in all_versions.values():
                v_dict = asdict(v)
                v_dict['metadata'] = [m.to_dict() for m in v.metadata]
                f.write(json.dumps(v_dict, ensure_ascii=False) + '\n')
    
    def _update_engine_history(self, metadata: ExtractionMetadata) -> None:
        """Update engine extraction history."""
        cache_key = (metadata.engine_name, metadata.pdf_source)
        
        if cache_key in self._history_cache:
            history = self._history_cache[cache_key]
        else:
            history = self.get_engine_history(metadata.engine_name, metadata.pdf_source)
        
        history.total_extractions += 1
        
        # Update active version
        version_id = f"{metadata.engine_name}_{metadata.configuration_hash[:8]}"
        history.active_version_id = version_id
        
        # Save history
        self._save_history(history)
    
    def _save_history(self, history: EngineExtractionHistory) -> None:
        """Save engine history."""
        cache_key = (history.engine_name, history.pdf_path)
        self._history_cache[cache_key] = history
        
        # Rewrite history file
        all_histories = self.load_all_histories()
        all_histories[cache_key] = history
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            for h in all_histories.values():
                h_dict = asdict(h)
                h_dict['versions'] = [asdict(v) for v in h.versions]
                for v_dict in h_dict['versions']:
                    v_dict['metadata'] = [m.to_dict() for m in v_dict['metadata']]
                f.write(json.dumps(h_dict, ensure_ascii=False) + '\n')
    
    def load_all_metadata(self) -> Dict[str, ExtractionMetadata]:
        """Load all extraction metadata."""
        metadata_dict = {}
        
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            metadata = ExtractionMetadata.from_dict(data)
                            metadata_dict[metadata.file_path] = metadata
                        except Exception as e:
                            print(f"Warning: Could not load metadata: {e}")
        
        return metadata_dict
    
    def load_all_versions(self) -> Dict[str, ExtractionVersion]:
        """Load all extraction versions."""
        versions_dict = {}
        
        if self.versions_file.exists():
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            # Reconstruct metadata objects
                            data['metadata'] = [
                                ExtractionMetadata.from_dict(m) for m in data['metadata']
                            ]
                            version = ExtractionVersion(**data)
                            versions_dict[version.version_id] = version
                        except Exception as e:
                            print(f"Warning: Could not load version: {e}")
        
        return versions_dict
    
    def load_all_histories(self) -> Dict[Tuple[str, str], EngineExtractionHistory]:
        """Load all engine histories."""
        histories_dict = {}
        
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            # Reconstruct version objects
                            versions = []
                            for v_data in data.get('versions', []):
                                v_data['metadata'] = [
                                    ExtractionMetadata.from_dict(m) 
                                    for m in v_data['metadata']
                                ]
                                versions.append(ExtractionVersion(**v_data))
                            data['versions'] = versions
                            
                            history = EngineExtractionHistory(**data)
                            cache_key = (history.engine_name, history.pdf_path)
                            histories_dict[cache_key] = history
                        except Exception as e:
                            print(f"Warning: Could not load history: {e}")
        
        return histories_dict
    
    def get_extraction_metadata(self, file_path: str) -> Optional[ExtractionMetadata]:
        """Get metadata for an extraction file."""
        if file_path in self._metadata_cache:
            return self._metadata_cache[file_path]
        
        all_metadata = self.load_all_metadata()
        return all_metadata.get(file_path)
    
    def get_engine_history(self, engine_name: str, pdf_path: str) -> EngineExtractionHistory:
        """Get extraction history for an engine."""
        cache_key = (engine_name, pdf_path)
        
        if cache_key in self._history_cache:
            return self._history_cache[cache_key]
        
        all_histories = self.load_all_histories()
        
        if cache_key in all_histories:
            history = all_histories[cache_key]
            self._history_cache[cache_key] = history
            return history
        
        # Create new history
        history = EngineExtractionHistory(
            engine_name=engine_name,
            pdf_path=pdf_path
        )
        self._history_cache[cache_key] = history
        return history
    
    def get_extractions_by_engine(self, engine_name: str, pdf_path: str) -> List[ExtractionMetadata]:
        """Get all extractions for an engine."""
        all_metadata = self.load_all_metadata()
        
        return [
            metadata for metadata in all_metadata.values()
            if metadata.engine_name == engine_name and metadata.pdf_source == pdf_path
        ]
    
    def get_extractions_by_configuration(self, engine_name: str, pdf_path: str,
                                        config_hash: str) -> List[ExtractionMetadata]:
        """Get all extractions for a specific configuration."""
        all_metadata = self.load_all_metadata()
        
        return [
            metadata for metadata in all_metadata.values()
            if (metadata.engine_name == engine_name and 
                metadata.pdf_source == pdf_path and
                metadata.configuration_hash == config_hash)
        ]
    
    def compare_configurations(self, config_hash1: str, config_hash2: str) -> Dict[str, Any]:
        """Compare two configurations."""
        all_metadata = self.load_all_metadata()
        
        # Find metadata with these hashes
        metadata1 = None
        metadata2 = None
        
        for metadata in all_metadata.values():
            if metadata.configuration_hash == config_hash1:
                metadata1 = metadata
            if metadata.configuration_hash == config_hash2:
                metadata2 = metadata
        
        if not metadata1 or not metadata2:
            return {"error": "Configuration not found"}
        
        # Compare configurations
        config1 = metadata1.configuration
        config2 = metadata2.configuration
        
        differences = {}
        all_keys = set(config1.keys()) | set(config2.keys())
        
        for key in all_keys:
            val1 = config1.get(key)
            val2 = config2.get(key)
            
            if val1 != val2:
                differences[key] = {
                    "config1": val1,
                    "config2": val2
                }
        
        return {
            "config_hash1": config_hash1,
            "config_hash2": config_hash2,
            "differences": differences,
            "total_differences": len(differences)
        }
    
    def find_similar_extractions(self, file_path: str, 
                                similarity_threshold: float = 0.8) -> List[Tuple[str, float]]:
        """Find extractions with similar configurations."""
        metadata = self.get_extraction_metadata(file_path)
        if not metadata:
            return []
        
        all_metadata = self.load_all_metadata()
        similar = []
        
        for other_path, other_metadata in all_metadata.items():
            if (other_path != file_path and 
                other_metadata.engine_name == metadata.engine_name and
                other_metadata.pdf_source == metadata.pdf_source):
                
                # Calculate similarity based on configuration
                similarity = self._calculate_config_similarity(
                    metadata.configuration,
                    other_metadata.configuration
                )
                
                if similarity >= similarity_threshold:
                    similar.append((other_path, similarity))
        
        # Sort by similarity
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar
    
    def _calculate_config_similarity(self, config1: Dict[str, Any], 
                                    config2: Dict[str, Any]) -> float:
        """Calculate similarity between two configurations."""
        all_keys = set(config1.keys()) | set(config2.keys())
        if not all_keys:
            return 1.0
        
        matching_keys = sum(1 for key in all_keys if config1.get(key) == config2.get(key))
        return matching_keys / len(all_keys)
    
    def get_version_summary(self, engine_name: str, pdf_path: str) -> Dict[str, Any]:
        """Get summary of all versions for an engine."""
        history = self.get_engine_history(engine_name, pdf_path)
        extractions = self.get_extractions_by_engine(engine_name, pdf_path)
        
        # Group by configuration
        config_groups = {}
        for extraction in extractions:
            config_hash = extraction.configuration_hash
            if config_hash not in config_groups:
                config_groups[config_hash] = []
            config_groups[config_hash].append(extraction)
        
        return {
            "engine_name": engine_name,
            "pdf_path": pdf_path,
            "total_extractions": len(extractions),
            "unique_configurations": len(config_groups),
            "active_version_id": history.active_version_id,
            "configuration_groups": {
                config_hash: {
                    "count": len(group),
                    "latest_version": max(e.version_number for e in group),
                    "latest_timestamp": max(e.extraction_timestamp for e in group)
                }
                for config_hash, group in config_groups.items()
            }
        }
    
    def cleanup_old_extractions(self, engine_name: str, pdf_path: str,
                               keep_per_config: int = 3) -> int:
        """Clean up old extraction files, keeping only recent versions."""
        extractions = self.get_extractions_by_engine(engine_name, pdf_path)
        
        # Group by configuration
        config_groups = {}
        for extraction in extractions:
            config_hash = extraction.configuration_hash
            if config_hash not in config_groups:
                config_groups[config_hash] = []
            config_groups[config_hash].append(extraction)
        
        removed_count = 0
        
        # For each configuration, keep only recent versions
        for config_hash, group in config_groups.items():
            if len(group) > keep_per_config:
                # Sort by version number
                group.sort(key=lambda x: x.version_number, reverse=True)
                to_remove = group[keep_per_config:]
                
                for extraction in to_remove:
                    try:
                        file_path = Path(extraction.file_path)
                        if file_path.exists():
                            file_path.unlink()
                            removed_count += 1
                    except Exception as e:
                        print(f"Warning: Could not remove {extraction.file_path}: {e}")
        
        return removed_count


# Convenience functions
def register_extraction(file_path: str, engine_name: str, configuration: Dict[str, Any],
                       pdf_source: str, tags: List[str] = None, notes: str = "") -> ExtractionMetadata:
    """Register a new extraction file."""
    manager = ExtractionVersionManager()
    return manager.register_extraction(file_path, engine_name, configuration, 
                                      pdf_source, tags, notes)


def get_engine_extraction_history(engine_name: str, pdf_path: str) -> EngineExtractionHistory:
    """Get extraction history for an engine."""
    manager = ExtractionVersionManager()
    return manager.get_engine_history(engine_name, pdf_path)


def get_version_summary(engine_name: str, pdf_path: str) -> Dict[str, Any]:
    """Get version summary for an engine."""
    manager = ExtractionVersionManager()
    return manager.get_version_summary(engine_name, pdf_path)

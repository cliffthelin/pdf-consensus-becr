# src/compareblocks/tracking/change_tracker.py
"""
Block-level change tracking with source attribution.
Maintains immutable baseline and tracks all changes with source information.
"""

import json
from enum import Enum
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


class ChangeType(Enum):
    """Types of changes that can be tracked."""
    INITIAL_EXTRACT = "initial_extract"  # Initial positional extract (immutable baseline)
    CONSENSUS_SELECTION = "consensus_selection"  # Automatic consensus selection
    MANUAL_OVERRIDE = "manual_override"  # User manual override
    MERGE_RESULT = "merge_result"  # Result of merging multiple variations
    RECALCULATION = "recalculation"  # Recalculation due to surrounding block changes
    CORRECTION = "correction"  # Manual correction/edit


@dataclass
class SourceAttribution:
    """Source attribution information for a change."""
    engine_name: str
    configuration_hash: Optional[str] = None
    configuration_params: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    processing_timestamp: Optional[str] = None
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceAttribution':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class BlockChange:
    """Represents a single change to a block."""
    change_id: str
    block_id: str
    change_type: ChangeType
    timestamp: str
    previous_text: Optional[str]
    new_text: str
    source_attribution: SourceAttribution
    consensus_score: Optional[float] = None
    alternative_sources: List[SourceAttribution] = field(default_factory=list)
    user_id: Optional[str] = None
    change_reason: Optional[str] = None
    affected_neighbors: List[str] = field(default_factory=list)  # Block IDs of affected neighbors
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        data = asdict(self)
        data['change_type'] = self.change_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlockChange':
        """Create from dictionary."""
        data = data.copy()
        data['change_type'] = ChangeType(data['change_type'])
        data['source_attribution'] = SourceAttribution.from_dict(data['source_attribution'])
        data['alternative_sources'] = [
            SourceAttribution.from_dict(src) for src in data.get('alternative_sources', [])
        ]
        return cls(**data)


@dataclass
class ChangeHistory:
    """Complete change history for a block."""
    block_id: str
    initial_extract: BlockChange  # Immutable baseline
    changes: List[BlockChange] = field(default_factory=list)
    current_text: str = ""
    recalculation_count: int = 0
    manual_override_count: int = 0
    
    def get_current_source(self) -> SourceAttribution:
        """Get the source attribution for the current text."""
        if self.changes:
            return self.changes[-1].source_attribution
        return self.initial_extract.source_attribution
    
    def get_all_sources(self) -> List[SourceAttribution]:
        """Get all source attributions in chronological order."""
        sources = [self.initial_extract.source_attribution]
        sources.extend([change.source_attribution for change in self.changes])
        return sources
    
    def get_change_count_by_type(self, change_type: ChangeType) -> int:
        """Count changes of a specific type."""
        return sum(1 for change in self.changes if change.change_type == change_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'block_id': self.block_id,
            'initial_extract': self.initial_extract.to_dict(),
            'changes': [change.to_dict() for change in self.changes],
            'current_text': self.current_text,
            'recalculation_count': self.recalculation_count,
            'manual_override_count': self.manual_override_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChangeHistory':
        """Create from dictionary."""
        data = data.copy()
        data['initial_extract'] = BlockChange.from_dict(data['initial_extract'])
        data['changes'] = [BlockChange.from_dict(change) for change in data.get('changes', [])]
        return cls(**data)


class ChangeTracker:
    """Tracks block-level changes with source attribution."""
    
    def __init__(self):
        """Initialize the change tracker."""
        self.histories: Dict[str, ChangeHistory] = {}
        self._change_counter = 0
    
    def _generate_change_id(self) -> str:
        """Generate a unique change ID."""
        self._change_counter += 1
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        return f"change_{timestamp}_{self._change_counter}"
    
    def record_initial_extract(self, block_id: str, text: str, 
                              source: SourceAttribution) -> BlockChange:
        """
        Record the initial positional extract as immutable baseline.
        
        Args:
            block_id: Block identifier
            text: Extracted text
            source: Source attribution
            
        Returns:
            BlockChange representing the initial extract
        """
        if block_id in self.histories:
            raise ValueError(f"Block {block_id} already has an initial extract")
        
        change = BlockChange(
            change_id=self._generate_change_id(),
            block_id=block_id,
            change_type=ChangeType.INITIAL_EXTRACT,
            timestamp=datetime.now().isoformat(),
            previous_text=None,
            new_text=text,
            source_attribution=source
        )
        
        history = ChangeHistory(
            block_id=block_id,
            initial_extract=change,
            current_text=text
        )
        
        self.histories[block_id] = history
        return change
    
    def record_consensus_selection(self, block_id: str, new_text: str,
                                  source: SourceAttribution, consensus_score: float,
                                  alternative_sources: List[SourceAttribution] = None) -> BlockChange:
        """
        Record a consensus selection change.
        
        Args:
            block_id: Block identifier
            new_text: New text from consensus
            source: Source attribution for selected variation
            consensus_score: Consensus score
            alternative_sources: Other sources that were considered
            
        Returns:
            BlockChange representing the consensus selection
        """
        if block_id not in self.histories:
            raise ValueError(f"Block {block_id} has no initial extract")
        
        history = self.histories[block_id]
        
        change = BlockChange(
            change_id=self._generate_change_id(),
            block_id=block_id,
            change_type=ChangeType.CONSENSUS_SELECTION,
            timestamp=datetime.now().isoformat(),
            previous_text=history.current_text,
            new_text=new_text,
            source_attribution=source,
            consensus_score=consensus_score,
            alternative_sources=alternative_sources or []
        )
        
        history.changes.append(change)
        history.current_text = new_text
        
        return change
    
    def record_manual_override(self, block_id: str, new_text: str,
                              source: SourceAttribution, user_id: str,
                              reason: Optional[str] = None) -> BlockChange:
        """
        Record a manual override change.
        
        Args:
            block_id: Block identifier
            new_text: New text from manual override
            source: Source attribution (may be user or selected engine)
            user_id: User who made the override
            reason: Optional reason for override
            
        Returns:
            BlockChange representing the manual override
        """
        if block_id not in self.histories:
            raise ValueError(f"Block {block_id} has no initial extract")
        
        history = self.histories[block_id]
        
        change = BlockChange(
            change_id=self._generate_change_id(),
            block_id=block_id,
            change_type=ChangeType.MANUAL_OVERRIDE,
            timestamp=datetime.now().isoformat(),
            previous_text=history.current_text,
            new_text=new_text,
            source_attribution=source,
            user_id=user_id,
            change_reason=reason
        )
        
        history.changes.append(change)
        history.current_text = new_text
        history.manual_override_count += 1
        
        return change
    
    def record_recalculation(self, block_id: str, new_text: str,
                           source: SourceAttribution, affected_neighbors: List[str],
                           trigger_block_id: str) -> BlockChange:
        """
        Record a recalculation due to surrounding block changes.
        
        Args:
            block_id: Block identifier
            new_text: New text from recalculation
            source: Source attribution
            affected_neighbors: List of neighbor block IDs that were affected
            trigger_block_id: Block ID that triggered this recalculation
            
        Returns:
            BlockChange representing the recalculation
        """
        if block_id not in self.histories:
            raise ValueError(f"Block {block_id} has no initial extract")
        
        history = self.histories[block_id]
        
        change = BlockChange(
            change_id=self._generate_change_id(),
            block_id=block_id,
            change_type=ChangeType.RECALCULATION,
            timestamp=datetime.now().isoformat(),
            previous_text=history.current_text,
            new_text=new_text,
            source_attribution=source,
            affected_neighbors=affected_neighbors,
            metadata={'trigger_block_id': trigger_block_id}
        )
        
        history.changes.append(change)
        history.current_text = new_text
        history.recalculation_count += 1
        
        return change
    
    def get_history(self, block_id: str) -> Optional[ChangeHistory]:
        """Get the complete change history for a block."""
        return self.histories.get(block_id)
    
    def get_current_text(self, block_id: str) -> Optional[str]:
        """Get the current text for a block."""
        history = self.histories.get(block_id)
        return history.current_text if history else None
    
    def get_blocks_with_manual_overrides(self) -> List[str]:
        """Get list of block IDs that have manual overrides."""
        return [
            block_id for block_id, history in self.histories.items()
            if history.manual_override_count > 0
        ]
    
    def get_blocks_with_recalculations(self) -> List[str]:
        """Get list of block IDs that have been recalculated."""
        return [
            block_id for block_id, history in self.histories.items()
            if history.recalculation_count > 0
        ]
    
    def get_all_sources_used(self) -> Set[str]:
        """Get set of all engine names that have been used as sources."""
        sources = set()
        for history in self.histories.values():
            for source_attr in history.get_all_sources():
                sources.add(source_attr.engine_name)
        return sources
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics about tracked changes."""
        total_blocks = len(self.histories)
        total_changes = sum(len(h.changes) for h in self.histories.values())
        
        change_type_counts = {}
        for change_type in ChangeType:
            count = sum(
                h.get_change_count_by_type(change_type)
                for h in self.histories.values()
            )
            change_type_counts[change_type.value] = count
        
        return {
            'total_blocks': total_blocks,
            'total_changes': total_changes,
            'blocks_with_manual_overrides': len(self.get_blocks_with_manual_overrides()),
            'blocks_with_recalculations': len(self.get_blocks_with_recalculations()),
            'change_type_counts': change_type_counts,
            'unique_sources': len(self.get_all_sources_used()),
            'sources_used': list(self.get_all_sources_used())
        }
    
    def export_to_ndjson(self, file_path: Path) -> None:
        """
        Export all change histories to NDJSON format.
        
        Args:
            file_path: Output file path
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for history in self.histories.values():
                json_line = json.dumps(history.to_dict(), ensure_ascii=False)
                f.write(json_line + '\n')
    
    def import_from_ndjson(self, file_path: Path) -> None:
        """
        Import change histories from NDJSON format.
        
        Args:
            file_path: Input file path
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    history = ChangeHistory.from_dict(data)
                    self.histories[history.block_id] = history
    
    def clear(self) -> None:
        """Clear all tracked histories."""
        self.histories.clear()
        self._change_counter = 0

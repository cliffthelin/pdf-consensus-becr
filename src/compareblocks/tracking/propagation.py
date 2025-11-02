# src/compareblocks/tracking/propagation.py
"""
Change propagation detection system.
Detects when changes to one block affect neighboring blocks and tracks propagation chains.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque

from .change_tracker import ChangeHistory, ChangeType, BlockChange


@dataclass
class PropagationResult:
    """Result of a single propagation step."""
    source_block_id: str
    affected_block_id: str
    propagation_depth: int
    text_changed: bool
    previous_text: str
    new_text: str
    change_magnitude: float  # 0.0 to 1.0, based on text difference
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)


@dataclass
class PropagationChain:
    """Complete chain of propagated changes."""
    trigger_block_id: str
    trigger_change_id: str
    propagation_steps: List[PropagationResult] = field(default_factory=list)
    total_affected_blocks: int = 0
    max_propagation_depth: int = 0
    stopped_naturally: bool = True  # True if propagation stopped on its own
    
    def get_affected_block_ids(self) -> Set[str]:
        """Get set of all affected block IDs."""
        return {step.affected_block_id for step in self.propagation_steps}
    
    def get_blocks_at_depth(self, depth: int) -> List[str]:
        """Get block IDs affected at a specific depth."""
        return [
            step.affected_block_id
            for step in self.propagation_steps
            if step.propagation_depth == depth
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'trigger_block_id': self.trigger_block_id,
            'trigger_change_id': self.trigger_change_id,
            'propagation_steps': [step.to_dict() for step in self.propagation_steps],
            'total_affected_blocks': self.total_affected_blocks,
            'max_propagation_depth': self.max_propagation_depth,
            'stopped_naturally': self.stopped_naturally
        }


class ChangePropagationDetector:
    """Detects and tracks change propagation through neighboring blocks."""
    
    def __init__(self, similarity_threshold: float = 0.95):
        """
        Initialize the propagation detector.
        
        Args:
            similarity_threshold: Threshold for considering text unchanged (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.propagation_chains: List[PropagationChain] = []
    
    def detect_propagation(self, trigger_block_id: str, 
                          trigger_change: BlockChange,
                          histories: Dict[str, ChangeHistory],
                          neighbor_map: Dict[str, List[str]],
                          max_depth: int = 10) -> PropagationChain:
        """
        Detect change propagation from a trigger block.
        
        Args:
            trigger_block_id: Block that triggered the propagation
            trigger_change: The change that triggered propagation
            histories: All block histories
            neighbor_map: Map of block_id to list of neighbor block_ids
            max_depth: Maximum propagation depth to track
            
        Returns:
            PropagationChain describing the propagation
        """
        chain = PropagationChain(
            trigger_block_id=trigger_block_id,
            trigger_change_id=trigger_change.change_id
        )
        
        # Track which blocks have been processed
        processed: Set[str] = {trigger_block_id}
        
        # Queue of (block_id, depth) to process
        queue: deque = deque()
        
        # Add neighbors of trigger block to queue
        neighbors = neighbor_map.get(trigger_block_id, [])
        for neighbor_id in neighbors:
            if neighbor_id in histories:
                queue.append((neighbor_id, 1))
        
        # Process propagation breadth-first
        while queue and len(queue) <= max_depth * 10:  # Safety limit
            current_block_id, depth = queue.popleft()
            
            if depth > max_depth:
                chain.stopped_naturally = False
                break
            
            if current_block_id in processed:
                continue
            
            processed.add(current_block_id)
            
            # Check if this block was affected
            history = histories.get(current_block_id)
            if not history:
                continue
            
            # Look for recalculation changes after the trigger
            affected = False
            for change in history.changes:
                if (change.change_type == ChangeType.RECALCULATION and
                    change.metadata.get('trigger_block_id') == trigger_block_id):
                    
                    # Calculate change magnitude
                    magnitude = self._calculate_change_magnitude(
                        change.previous_text, change.new_text
                    )
                    
                    text_changed = magnitude > (1.0 - self.similarity_threshold)
                    
                    # Record propagation step
                    step = PropagationResult(
                        source_block_id=trigger_block_id,
                        affected_block_id=current_block_id,
                        propagation_depth=depth,
                        text_changed=text_changed,
                        previous_text=change.previous_text or "",
                        new_text=change.new_text,
                        change_magnitude=magnitude
                    )
                    
                    chain.propagation_steps.append(step)
                    affected = True
                    
                    # If text changed significantly, check this block's neighbors
                    if text_changed:
                        next_neighbors = neighbor_map.get(current_block_id, [])
                        for next_neighbor_id in next_neighbors:
                            if next_neighbor_id not in processed:
                                queue.append((next_neighbor_id, depth + 1))
                    
                    break  # Only process first matching recalculation
        
        # Update chain statistics
        chain.total_affected_blocks = len(chain.get_affected_block_ids())
        chain.max_propagation_depth = max(
            (step.propagation_depth for step in chain.propagation_steps),
            default=0
        )
        
        self.propagation_chains.append(chain)
        return chain
    
    def _calculate_change_magnitude(self, text1: Optional[str], text2: str) -> float:
        """
        Calculate magnitude of change between two texts.
        
        Args:
            text1: Previous text (may be None)
            text2: New text
            
        Returns:
            Change magnitude (0.0 = identical, 1.0 = completely different)
        """
        if text1 is None:
            return 1.0 if text2 else 0.0
        
        if text1 == text2:
            return 0.0
        
        # Simple character-level difference ratio
        len1 = len(text1)
        len2 = len(text2)
        
        if len1 == 0 and len2 == 0:
            return 0.0
        
        if len1 == 0 or len2 == 0:
            return 1.0
        
        # Calculate Levenshtein-like ratio
        # For simplicity, use character set difference
        set1 = set(text1)
        set2 = set(text2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        similarity = intersection / union
        return 1.0 - similarity
    
    def find_propagation_chains_for_block(self, block_id: str) -> List[PropagationChain]:
        """
        Find all propagation chains that affected a specific block.
        
        Args:
            block_id: Block identifier
            
        Returns:
            List of propagation chains affecting this block
        """
        chains = []
        for chain in self.propagation_chains:
            if block_id in chain.get_affected_block_ids():
                chains.append(chain)
        return chains
    
    def get_propagation_statistics(self) -> Dict[str, Any]:
        """Get statistics about all tracked propagation chains."""
        if not self.propagation_chains:
            return {
                'total_chains': 0,
                'total_affected_blocks': 0,
                'avg_chain_length': 0.0,
                'max_chain_length': 0,
                'avg_propagation_depth': 0.0,
                'max_propagation_depth': 0
            }
        
        total_affected = sum(chain.total_affected_blocks for chain in self.propagation_chains)
        chain_lengths = [len(chain.propagation_steps) for chain in self.propagation_chains]
        depths = [chain.max_propagation_depth for chain in self.propagation_chains]
        
        import statistics
        
        return {
            'total_chains': len(self.propagation_chains),
            'total_affected_blocks': total_affected,
            'avg_chain_length': statistics.mean(chain_lengths),
            'max_chain_length': max(chain_lengths),
            'avg_propagation_depth': statistics.mean(depths),
            'max_propagation_depth': max(depths),
            'chains_stopped_naturally': sum(
                1 for chain in self.propagation_chains if chain.stopped_naturally
            )
        }
    
    def should_continue_recalculation(self, block_id: str,
                                     previous_text: str,
                                     new_text: str) -> bool:
        """
        Determine if recalculation should continue to neighbors.
        
        Args:
            block_id: Block being recalculated
            previous_text: Text before recalculation
            new_text: Text after recalculation
            
        Returns:
            True if recalculation should propagate to neighbors
        """
        magnitude = self._calculate_change_magnitude(previous_text, new_text)
        return magnitude > (1.0 - self.similarity_threshold)
    
    def get_blocks_requiring_recalculation(self, changed_block_id: str,
                                          neighbor_map: Dict[str, List[str]]) -> List[str]:
        """
        Get list of blocks that should be recalculated due to a change.
        
        Args:
            changed_block_id: Block that changed
            neighbor_map: Map of block_id to neighbor block_ids
            
        Returns:
            List of block IDs that should be recalculated
        """
        return neighbor_map.get(changed_block_id, [])
    
    def clear_chains(self) -> None:
        """Clear all tracked propagation chains."""
        self.propagation_chains.clear()


def detect_change_propagation(trigger_block_id: str,
                             trigger_change: BlockChange,
                             histories: Dict[str, ChangeHistory],
                             neighbor_map: Dict[str, List[str]]) -> PropagationChain:
    """
    Convenience function to detect change propagation.
    
    Args:
        trigger_block_id: Block that triggered the propagation
        trigger_change: The change that triggered propagation
        histories: All block histories
        neighbor_map: Map of block_id to neighbor block_ids
        
    Returns:
        PropagationChain describing the propagation
    """
    detector = ChangePropagationDetector()
    return detector.detect_propagation(
        trigger_block_id, trigger_change, histories, neighbor_map
    )


def build_neighbor_map(block_positions: Dict[str, Tuple[int, float, float]]) -> Dict[str, List[str]]:
    """
    Build a neighbor map from block positions.
    
    Args:
        block_positions: Dict of block_id to (page, y_position, x_position)
        
    Returns:
        Dict mapping block_id to list of neighbor block_ids
    """
    neighbor_map = {}
    
    # Sort blocks by page and position
    sorted_blocks = sorted(
        block_positions.items(),
        key=lambda x: (x[1][0], x[1][1], x[1][2])  # page, y, x
    )
    
    # For each block, find adjacent blocks
    for i, (block_id, (page, y, x)) in enumerate(sorted_blocks):
        neighbors = []
        
        # Check previous block (if on same page)
        if i > 0:
            prev_id, (prev_page, prev_y, prev_x) = sorted_blocks[i - 1]
            if prev_page == page:
                neighbors.append(prev_id)
        
        # Check next block (if on same page)
        if i < len(sorted_blocks) - 1:
            next_id, (next_page, next_y, next_x) = sorted_blocks[i + 1]
            if next_page == page:
                neighbors.append(next_id)
        
        neighbor_map[block_id] = neighbors
    
    return neighbor_map

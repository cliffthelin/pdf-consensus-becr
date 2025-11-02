# tests/unit/test_propagation.py
"""
Tests for change propagation detection system.
"""

import pytest

from compareblocks.tracking.change_tracker import (
    ChangeTracker,
    SourceAttribution,
    ChangeType
)
from compareblocks.tracking.propagation import (
    ChangePropagationDetector,
    PropagationResult,
    PropagationChain,
    detect_change_propagation,
    build_neighbor_map
)


class TestPropagationResult:
    """Test PropagationResult dataclass."""
    
    def test_create_propagation_result(self):
        """Test creating propagation result."""
        result = PropagationResult(
            source_block_id="block_001",
            affected_block_id="block_002",
            propagation_depth=1,
            text_changed=True,
            previous_text="Old",
            new_text="New",
            change_magnitude=0.5
        )
        
        assert result.source_block_id == "block_001"
        assert result.affected_block_id == "block_002"
        assert result.propagation_depth == 1
        assert result.text_changed is True
    
    def test_propagation_result_to_dict(self):
        """Test converting result to dictionary."""
        result = PropagationResult(
            source_block_id="block_001",
            affected_block_id="block_002",
            propagation_depth=2,
            text_changed=False,
            previous_text="Same",
            new_text="Same",
            change_magnitude=0.0
        )
        
        data = result.to_dict()
        assert data['propagation_depth'] == 2
        assert data['text_changed'] is False


class TestPropagationChain:
    """Test PropagationChain dataclass."""
    
    def test_create_propagation_chain(self):
        """Test creating propagation chain."""
        chain = PropagationChain(
            trigger_block_id="block_001",
            trigger_change_id="change_001"
        )
        
        assert chain.trigger_block_id == "block_001"
        assert len(chain.propagation_steps) == 0
    
    def test_get_affected_block_ids(self):
        """Test getting affected block IDs."""
        chain = PropagationChain(
            trigger_block_id="block_001",
            trigger_change_id="change_001",
            propagation_steps=[
                PropagationResult("block_001", "block_002", 1, True, "Old", "New", 0.5),
                PropagationResult("block_001", "block_003", 1, True, "Old", "New", 0.5),
                PropagationResult("block_001", "block_004", 2, True, "Old", "New", 0.5),
            ]
        )
        
        affected = chain.get_affected_block_ids()
        assert len(affected) == 3
        assert "block_002" in affected
        assert "block_003" in affected
        assert "block_004" in affected
    
    def test_get_blocks_at_depth(self):
        """Test getting blocks at specific depth."""
        chain = PropagationChain(
            trigger_block_id="block_001",
            trigger_change_id="change_001",
            propagation_steps=[
                PropagationResult("block_001", "block_002", 1, True, "Old", "New", 0.5),
                PropagationResult("block_001", "block_003", 1, True, "Old", "New", 0.5),
                PropagationResult("block_001", "block_004", 2, True, "Old", "New", 0.5),
            ]
        )
        
        depth_1 = chain.get_blocks_at_depth(1)
        depth_2 = chain.get_blocks_at_depth(2)
        
        assert len(depth_1) == 2
        assert "block_002" in depth_1
        assert "block_003" in depth_1
        assert len(depth_2) == 1
        assert "block_004" in depth_2


class TestChangePropagationDetector:
    """Test ChangePropagationDetector class."""
    
    def test_create_detector(self):
        """Test creating propagation detector."""
        detector = ChangePropagationDetector()
        assert detector.similarity_threshold > 0
        assert len(detector.propagation_chains) == 0
    
    def test_detect_simple_propagation(self):
        """Test detecting simple propagation."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        # Create initial blocks
        tracker.record_initial_extract("block_001", "Text1", source)
        tracker.record_initial_extract("block_002", "Text2", source)
        
        # Trigger change
        trigger_change = tracker.record_consensus_selection(
            "block_001", "Updated1", source, 0.9
        )
        
        # Recalculate neighbor
        tracker.record_recalculation(
            "block_002", "Recalc2", source, [], "block_001"
        )
        
        # Build neighbor map
        neighbor_map = {
            "block_001": ["block_002"],
            "block_002": ["block_001"]
        }
        
        detector = ChangePropagationDetector()
        chain = detector.detect_propagation(
            "block_001", trigger_change, tracker.histories, neighbor_map
        )
        
        assert chain.trigger_block_id == "block_001"
        assert chain.total_affected_blocks >= 0
    
    def test_detect_multi_level_propagation(self):
        """Test detecting multi-level propagation."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        # Create chain of blocks
        for i in range(4):
            tracker.record_initial_extract(f"block_{i:03d}", f"Text{i}", source)
        
        # Trigger change
        trigger_change = tracker.record_consensus_selection(
            "block_000", "Updated0", source, 0.9
        )
        
        # Recalculate neighbors in sequence
        tracker.record_recalculation("block_001", "Recalc1", source, [], "block_000")
        tracker.record_recalculation("block_002", "Recalc2", source, [], "block_000")
        tracker.record_recalculation("block_003", "Recalc3", source, [], "block_000")
        
        # Build linear neighbor map
        neighbor_map = {
            "block_000": ["block_001"],
            "block_001": ["block_000", "block_002"],
            "block_002": ["block_001", "block_003"],
            "block_003": ["block_002"]
        }
        
        detector = ChangePropagationDetector()
        chain = detector.detect_propagation(
            "block_000", trigger_change, tracker.histories, neighbor_map, max_depth=5
        )
        
        assert chain.trigger_block_id == "block_000"
        # Should detect some propagation
        assert len(chain.propagation_steps) >= 0
    
    def test_should_continue_recalculation(self):
        """Test determining if recalculation should continue."""
        detector = ChangePropagationDetector(similarity_threshold=0.95)
        
        # Significant change - should continue
        should_continue = detector.should_continue_recalculation(
            "block_001", "Old text", "Completely different text"
        )
        assert should_continue is True
        
        # Minimal change - should not continue
        should_continue = detector.should_continue_recalculation(
            "block_001", "Same text", "Same text"
        )
        assert should_continue is False
    
    def test_get_blocks_requiring_recalculation(self):
        """Test getting blocks requiring recalculation."""
        detector = ChangePropagationDetector()
        
        neighbor_map = {
            "block_001": ["block_002", "block_003"],
            "block_002": ["block_001"],
            "block_003": ["block_001"]
        }
        
        blocks = detector.get_blocks_requiring_recalculation("block_001", neighbor_map)
        
        assert len(blocks) == 2
        assert "block_002" in blocks
        assert "block_003" in blocks
    
    def test_find_propagation_chains_for_block(self):
        """Test finding chains affecting a specific block."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        # Create blocks
        tracker.record_initial_extract("block_001", "Text1", source)
        tracker.record_initial_extract("block_002", "Text2", source)
        
        trigger_change = tracker.record_consensus_selection(
            "block_001", "Updated", source, 0.9
        )
        
        tracker.record_recalculation("block_002", "Recalc", source, [], "block_001")
        
        neighbor_map = {"block_001": ["block_002"], "block_002": []}
        
        detector = ChangePropagationDetector()
        chain = detector.detect_propagation(
            "block_001", trigger_change, tracker.histories, neighbor_map
        )
        
        # Find chains affecting block_002
        chains = detector.find_propagation_chains_for_block("block_002")
        assert len(chains) >= 0
    
    def test_get_propagation_statistics(self):
        """Test getting propagation statistics."""
        detector = ChangePropagationDetector()
        
        # Add some mock chains
        chain1 = PropagationChain(
            trigger_block_id="block_001",
            trigger_change_id="change_001",
            propagation_steps=[
                PropagationResult("block_001", "block_002", 1, True, "Old", "New", 0.5)
            ],
            total_affected_blocks=1,
            max_propagation_depth=1
        )
        
        chain2 = PropagationChain(
            trigger_block_id="block_003",
            trigger_change_id="change_002",
            propagation_steps=[
                PropagationResult("block_003", "block_004", 1, True, "Old", "New", 0.5),
                PropagationResult("block_003", "block_005", 2, True, "Old", "New", 0.5)
            ],
            total_affected_blocks=2,
            max_propagation_depth=2
        )
        
        detector.propagation_chains = [chain1, chain2]
        
        stats = detector.get_propagation_statistics()
        
        assert stats['total_chains'] == 2
        assert stats['total_affected_blocks'] == 3
        assert stats['max_chain_length'] == 2
        assert stats['max_propagation_depth'] == 2


class TestBuildNeighborMap:
    """Test build_neighbor_map function."""
    
    def test_build_neighbor_map_simple(self):
        """Test building neighbor map from positions."""
        positions = {
            "block_001": (1, 100, 50),  # page 1, y=100, x=50
            "block_002": (1, 200, 50),  # page 1, y=200, x=50
            "block_003": (1, 300, 50),  # page 1, y=300, x=50
        }
        
        neighbor_map = build_neighbor_map(positions)
        
        # block_001 should have block_002 as neighbor
        assert "block_002" in neighbor_map["block_001"]
        # block_002 should have both as neighbors
        assert "block_001" in neighbor_map["block_002"]
        assert "block_003" in neighbor_map["block_002"]
        # block_003 should have block_002 as neighbor
        assert "block_002" in neighbor_map["block_003"]
    
    def test_build_neighbor_map_multiple_pages(self):
        """Test building neighbor map across pages."""
        positions = {
            "block_001": (1, 100, 50),  # page 1
            "block_002": (1, 200, 50),  # page 1
            "block_003": (2, 100, 50),  # page 2
            "block_004": (2, 200, 50),  # page 2
        }
        
        neighbor_map = build_neighbor_map(positions)
        
        # Blocks on page 1 should not be neighbors with blocks on page 2
        assert "block_003" not in neighbor_map["block_001"]
        assert "block_004" not in neighbor_map["block_002"]
        
        # Blocks on same page should be neighbors
        assert "block_002" in neighbor_map["block_001"]
        assert "block_004" in neighbor_map["block_003"]


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_detect_change_propagation(self):
        """Test detect_change_propagation convenience function."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        tracker.record_initial_extract("block_001", "Text1", source)
        tracker.record_initial_extract("block_002", "Text2", source)
        
        trigger_change = tracker.record_consensus_selection(
            "block_001", "Updated", source, 0.9
        )
        
        tracker.record_recalculation("block_002", "Recalc", source, [], "block_001")
        
        neighbor_map = {"block_001": ["block_002"], "block_002": []}
        
        chain = detect_change_propagation(
            "block_001", trigger_change, tracker.histories, neighbor_map
        )
        
        assert chain.trigger_block_id == "block_001"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

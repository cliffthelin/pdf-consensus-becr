# tests/unit/test_change_tracker.py
"""
Tests for change tracking and source attribution system.
"""

import pytest
from pathlib import Path
import tempfile
import json

from compareblocks.tracking.change_tracker import (
    ChangeTracker,
    BlockChange,
    ChangeHistory,
    SourceAttribution,
    ChangeType
)


class TestSourceAttribution:
    """Test SourceAttribution dataclass."""
    
    def test_create_source_attribution(self):
        """Test creating source attribution."""
        source = SourceAttribution(
            engine_name="tesseract",
            configuration_hash="abc123",
            confidence_score=0.95
        )
        
        assert source.engine_name == "tesseract"
        assert source.configuration_hash == "abc123"
        assert source.confidence_score == 0.95
    
    def test_source_attribution_to_dict(self):
        """Test converting source attribution to dictionary."""
        source = SourceAttribution(
            engine_name="pymupdf",
            configuration_params={"dpi": 300}
        )
        
        data = source.to_dict()
        assert data['engine_name'] == "pymupdf"
        assert data['configuration_params'] == {"dpi": 300}
    
    def test_source_attribution_from_dict(self):
        """Test creating source attribution from dictionary."""
        data = {
            'engine_name': 'paddleocr',
            'configuration_hash': 'def456',
            'configuration_params': {'lang': 'en'},
            'confidence_score': 0.88,
            'processing_timestamp': '2024-01-01T12:00:00',
            'extraction_metadata': {'version': '2.0'}
        }
        
        source = SourceAttribution.from_dict(data)
        assert source.engine_name == 'paddleocr'
        assert source.configuration_hash == 'def456'
        assert source.confidence_score == 0.88


class TestBlockChange:
    """Test BlockChange dataclass."""
    
    def test_create_block_change(self):
        """Test creating block change."""
        source = SourceAttribution(engine_name="tesseract")
        
        change = BlockChange(
            change_id="change_001",
            block_id="block_123",
            change_type=ChangeType.INITIAL_EXTRACT,
            timestamp="2024-01-01T12:00:00",
            previous_text=None,
            new_text="Hello World",
            source_attribution=source
        )
        
        assert change.change_id == "change_001"
        assert change.block_id == "block_123"
        assert change.change_type == ChangeType.INITIAL_EXTRACT
        assert change.new_text == "Hello World"
    
    def test_block_change_to_dict(self):
        """Test converting block change to dictionary."""
        source = SourceAttribution(engine_name="pymupdf")
        change = BlockChange(
            change_id="change_002",
            block_id="block_456",
            change_type=ChangeType.CONSENSUS_SELECTION,
            timestamp="2024-01-01T13:00:00",
            previous_text="Old text",
            new_text="New text",
            source_attribution=source,
            consensus_score=0.92
        )
        
        data = change.to_dict()
        assert data['change_type'] == 'consensus_selection'
        assert data['consensus_score'] == 0.92
    
    def test_block_change_from_dict(self):
        """Test creating block change from dictionary."""
        data = {
            'change_id': 'change_003',
            'block_id': 'block_789',
            'change_type': 'manual_override',
            'timestamp': '2024-01-01T14:00:00',
            'previous_text': 'Before',
            'new_text': 'After',
            'source_attribution': {
                'engine_name': 'user',
                'configuration_hash': None,
                'configuration_params': {},
                'confidence_score': 1.0,
                'processing_timestamp': None,
                'extraction_metadata': {}
            },
            'consensus_score': None,
            'alternative_sources': [],
            'user_id': 'user123',
            'change_reason': 'Correction',
            'affected_neighbors': [],
            'metadata': {}
        }
        
        change = BlockChange.from_dict(data)
        assert change.change_type == ChangeType.MANUAL_OVERRIDE
        assert change.user_id == 'user123'


class TestChangeHistory:
    """Test ChangeHistory dataclass."""
    
    def test_create_change_history(self):
        """Test creating change history."""
        source = SourceAttribution(engine_name="tesseract")
        initial = BlockChange(
            change_id="init_001",
            block_id="block_001",
            change_type=ChangeType.INITIAL_EXTRACT,
            timestamp="2024-01-01T12:00:00",
            previous_text=None,
            new_text="Initial text",
            source_attribution=source
        )
        
        history = ChangeHistory(
            block_id="block_001",
            initial_extract=initial,
            current_text="Initial text"
        )
        
        assert history.block_id == "block_001"
        assert history.current_text == "Initial text"
        assert len(history.changes) == 0
    
    def test_get_current_source(self):
        """Test getting current source from history."""
        source1 = SourceAttribution(engine_name="tesseract")
        source2 = SourceAttribution(engine_name="pymupdf")
        
        initial = BlockChange(
            change_id="init_001",
            block_id="block_001",
            change_type=ChangeType.INITIAL_EXTRACT,
            timestamp="2024-01-01T12:00:00",
            previous_text=None,
            new_text="Initial",
            source_attribution=source1
        )
        
        change = BlockChange(
            change_id="change_001",
            block_id="block_001",
            change_type=ChangeType.CONSENSUS_SELECTION,
            timestamp="2024-01-01T13:00:00",
            previous_text="Initial",
            new_text="Updated",
            source_attribution=source2
        )
        
        history = ChangeHistory(
            block_id="block_001",
            initial_extract=initial,
            changes=[change],
            current_text="Updated"
        )
        
        current_source = history.get_current_source()
        assert current_source.engine_name == "pymupdf"
    
    def test_get_change_count_by_type(self):
        """Test counting changes by type."""
        source = SourceAttribution(engine_name="tesseract")
        initial = BlockChange(
            change_id="init_001",
            block_id="block_001",
            change_type=ChangeType.INITIAL_EXTRACT,
            timestamp="2024-01-01T12:00:00",
            previous_text=None,
            new_text="Initial",
            source_attribution=source
        )
        
        changes = [
            BlockChange(
                change_id=f"change_{i}",
                block_id="block_001",
                change_type=ChangeType.CONSENSUS_SELECTION if i % 2 == 0 else ChangeType.MANUAL_OVERRIDE,
                timestamp=f"2024-01-01T{13+i}:00:00",
                previous_text="Prev",
                new_text="New",
                source_attribution=source
            )
            for i in range(5)
        ]
        
        history = ChangeHistory(
            block_id="block_001",
            initial_extract=initial,
            changes=changes
        )
        
        consensus_count = history.get_change_count_by_type(ChangeType.CONSENSUS_SELECTION)
        override_count = history.get_change_count_by_type(ChangeType.MANUAL_OVERRIDE)
        
        assert consensus_count == 3  # indices 0, 2, 4
        assert override_count == 2  # indices 1, 3


class TestChangeTracker:
    """Test ChangeTracker class."""
    
    def test_create_change_tracker(self):
        """Test creating change tracker."""
        tracker = ChangeTracker()
        assert len(tracker.histories) == 0
    
    def test_record_initial_extract(self):
        """Test recording initial extract."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        change = tracker.record_initial_extract(
            block_id="block_001",
            text="Initial text",
            source=source
        )
        
        assert change.change_type == ChangeType.INITIAL_EXTRACT
        assert change.new_text == "Initial text"
        assert "block_001" in tracker.histories
        
        history = tracker.get_history("block_001")
        assert history.current_text == "Initial text"
    
    def test_record_initial_extract_duplicate_error(self):
        """Test that recording duplicate initial extract raises error."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        tracker.record_initial_extract("block_001", "Text", source)
        
        with pytest.raises(ValueError, match="already has an initial extract"):
            tracker.record_initial_extract("block_001", "Text2", source)
    
    def test_record_consensus_selection(self):
        """Test recording consensus selection."""
        tracker = ChangeTracker()
        source1 = SourceAttribution(engine_name="tesseract")
        source2 = SourceAttribution(engine_name="pymupdf")
        
        tracker.record_initial_extract("block_001", "Initial", source1)
        
        change = tracker.record_consensus_selection(
            block_id="block_001",
            new_text="Consensus text",
            source=source2,
            consensus_score=0.95
        )
        
        assert change.change_type == ChangeType.CONSENSUS_SELECTION
        assert change.consensus_score == 0.95
        assert change.previous_text == "Initial"
        
        history = tracker.get_history("block_001")
        assert history.current_text == "Consensus text"
    
    def test_record_manual_override(self):
        """Test recording manual override."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        tracker.record_initial_extract("block_001", "Initial", source)
        
        change = tracker.record_manual_override(
            block_id="block_001",
            new_text="Manual correction",
            source=SourceAttribution(engine_name="user"),
            user_id="user123",
            reason="Typo correction"
        )
        
        assert change.change_type == ChangeType.MANUAL_OVERRIDE
        assert change.user_id == "user123"
        assert change.change_reason == "Typo correction"
        
        history = tracker.get_history("block_001")
        assert history.manual_override_count == 1
    
    def test_record_recalculation(self):
        """Test recording recalculation."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        tracker.record_initial_extract("block_001", "Initial", source)
        tracker.record_initial_extract("block_002", "Neighbor", source)
        
        change = tracker.record_recalculation(
            block_id="block_002",
            new_text="Recalculated",
            source=source,
            affected_neighbors=["block_003"],
            trigger_block_id="block_001"
        )
        
        assert change.change_type == ChangeType.RECALCULATION
        assert change.metadata['trigger_block_id'] == "block_001"
        
        history = tracker.get_history("block_002")
        assert history.recalculation_count == 1
    
    def test_get_blocks_with_manual_overrides(self):
        """Test getting blocks with manual overrides."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        tracker.record_initial_extract("block_001", "Text1", source)
        tracker.record_initial_extract("block_002", "Text2", source)
        tracker.record_initial_extract("block_003", "Text3", source)
        
        tracker.record_manual_override("block_001", "Override1", source, "user1")
        tracker.record_manual_override("block_003", "Override3", source, "user1")
        
        overridden_blocks = tracker.get_blocks_with_manual_overrides()
        assert len(overridden_blocks) == 2
        assert "block_001" in overridden_blocks
        assert "block_003" in overridden_blocks
    
    def test_get_all_sources_used(self):
        """Test getting all sources used."""
        tracker = ChangeTracker()
        
        tracker.record_initial_extract(
            "block_001", "Text1", SourceAttribution(engine_name="tesseract")
        )
        tracker.record_initial_extract(
            "block_002", "Text2", SourceAttribution(engine_name="pymupdf")
        )
        tracker.record_consensus_selection(
            "block_001", "New", SourceAttribution(engine_name="paddleocr"), 0.9
        )
        
        sources = tracker.get_all_sources_used()
        assert len(sources) == 3
        assert "tesseract" in sources
        assert "pymupdf" in sources
        assert "paddleocr" in sources
    
    def test_get_statistics(self):
        """Test getting tracker statistics."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        tracker.record_initial_extract("block_001", "Text1", source)
        tracker.record_initial_extract("block_002", "Text2", source)
        tracker.record_consensus_selection("block_001", "New1", source, 0.9)
        tracker.record_manual_override("block_002", "Override", source, "user1")
        
        stats = tracker.get_statistics()
        
        assert stats['total_blocks'] == 2
        assert stats['total_changes'] == 2
        assert stats['blocks_with_manual_overrides'] == 1
        assert stats['change_type_counts']['consensus_selection'] == 1
        assert stats['change_type_counts']['manual_override'] == 1
    
    def test_export_import_ndjson(self):
        """Test exporting and importing change histories."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract", confidence_score=0.95)
        
        tracker.record_initial_extract("block_001", "Text1", source)
        tracker.record_consensus_selection("block_001", "Updated", source, 0.92)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "changes.ndjson"
            
            # Export
            tracker.export_to_ndjson(file_path)
            assert file_path.exists()
            
            # Import into new tracker
            new_tracker = ChangeTracker()
            new_tracker.import_from_ndjson(file_path)
            
            assert len(new_tracker.histories) == 1
            history = new_tracker.get_history("block_001")
            assert history.current_text == "Updated"
            assert len(history.changes) == 1
    
    def test_clear(self):
        """Test clearing tracker."""
        tracker = ChangeTracker()
        source = SourceAttribution(engine_name="tesseract")
        
        tracker.record_initial_extract("block_001", "Text", source)
        assert len(tracker.histories) == 1
        
        tracker.clear()
        assert len(tracker.histories) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

# tests/unit/test_source_ranker.py
"""
Tests for source ranking system.
"""

import pytest

from compareblocks.tracking.change_tracker import (
    ChangeTracker,
    SourceAttribution,
    ChangeType
)
from compareblocks.tracking.source_ranker import (
    SourceRanker,
    AccuracyMetrics,
    SourceRanking,
    rank_sources_by_accuracy,
    get_best_source
)


class TestAccuracyMetrics:
    """Test AccuracyMetrics dataclass."""
    
    def test_create_accuracy_metrics(self):
        """Test creating accuracy metrics."""
        metrics = AccuracyMetrics(
            source_identifier="tesseract",
            total_selections=10,
            consensus_selections=8,
            avg_consensus_score=0.85
        )
        
        assert metrics.source_identifier == "tesseract"
        assert metrics.total_selections == 10
        assert metrics.consensus_selections == 8
    
    def test_accuracy_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = AccuracyMetrics(
            source_identifier="pymupdf",
            accuracy_score=0.92
        )
        
        data = metrics.to_dict()
        assert data['source_identifier'] == "pymupdf"
        assert data['accuracy_score'] == 0.92


class TestSourceRanking:
    """Test SourceRanking dataclass."""
    
    def test_create_source_ranking(self):
        """Test creating source ranking."""
        metrics1 = AccuracyMetrics(source_identifier="engine1", accuracy_score=0.9)
        metrics2 = AccuracyMetrics(source_identifier="engine2", accuracy_score=0.8)
        
        ranking = SourceRanking(
            rankings=[("engine1", metrics1), ("engine2", metrics2)],
            total_blocks=100
        )
        
        assert len(ranking.rankings) == 2
        assert ranking.total_blocks == 100
    
    def test_get_top_sources(self):
        """Test getting top sources."""
        rankings = [
            ("engine1", AccuracyMetrics(source_identifier="engine1", accuracy_score=0.95)),
            ("engine2", AccuracyMetrics(source_identifier="engine2", accuracy_score=0.90)),
            ("engine3", AccuracyMetrics(source_identifier="engine3", accuracy_score=0.85)),
        ]
        
        ranking = SourceRanking(rankings=rankings)
        top_2 = ranking.get_top_sources(2)
        
        assert len(top_2) == 2
        assert top_2[0][0] == "engine1"
        assert top_2[1][0] == "engine2"
    
    def test_get_source_rank(self):
        """Test getting rank of specific source."""
        rankings = [
            ("engine1", AccuracyMetrics(source_identifier="engine1", accuracy_score=0.95)),
            ("engine2", AccuracyMetrics(source_identifier="engine2", accuracy_score=0.90)),
            ("engine3", AccuracyMetrics(source_identifier="engine3", accuracy_score=0.85)),
        ]
        
        ranking = SourceRanking(rankings=rankings)
        
        assert ranking.get_source_rank("engine1") == 1
        assert ranking.get_source_rank("engine2") == 2
        assert ranking.get_source_rank("engine3") == 3
        assert ranking.get_source_rank("engine4") is None


class TestSourceRanker:
    """Test SourceRanker class."""
    
    def test_create_source_ranker(self):
        """Test creating source ranker."""
        ranker = SourceRanker()
        assert ranker.consensus_weight > 0
        assert ranker.override_resistance_weight > 0
    
    def test_calculate_accuracy_metrics_simple(self):
        """Test calculating accuracy metrics with simple data."""
        tracker = ChangeTracker()
        
        # Create some test data
        source1 = SourceAttribution(engine_name="tesseract")
        source2 = SourceAttribution(engine_name="pymupdf")
        
        tracker.record_initial_extract("block_001", "Text1", source1)
        tracker.record_consensus_selection("block_001", "Updated1", source2, 0.95)
        
        tracker.record_initial_extract("block_002", "Text2", source1)
        tracker.record_consensus_selection("block_002", "Updated2", source1, 0.88)
        
        ranker = SourceRanker()
        metrics = ranker.calculate_accuracy_metrics(tracker.histories)
        
        assert "tesseract" in metrics
        assert "pymupdf" in metrics
        assert metrics["tesseract"].total_selections > 0
    
    def test_calculate_accuracy_metrics_with_overrides(self):
        """Test calculating metrics with manual overrides."""
        tracker = ChangeTracker()
        
        source1 = SourceAttribution(engine_name="tesseract")
        source2 = SourceAttribution(engine_name="user")
        
        tracker.record_initial_extract("block_001", "Text1", source1)
        tracker.record_consensus_selection("block_001", "Consensus", source1, 0.9)
        tracker.record_manual_override("block_001", "Manual", source2, "user123")
        
        ranker = SourceRanker()
        metrics = ranker.calculate_accuracy_metrics(tracker.histories)
        
        # Tesseract was overridden
        assert metrics["tesseract"].manual_overrides_from > 0
        # User selection
        assert metrics["user"].manual_overrides_to > 0
    
    def test_rank_sources(self):
        """Test ranking sources."""
        tracker = ChangeTracker()
        
        # Create test data with different engines
        engines = ["tesseract", "pymupdf", "paddleocr"]
        for i, engine in enumerate(engines):
            source = SourceAttribution(engine_name=engine)
            block_id = f"block_{i:03d}"
            tracker.record_initial_extract(block_id, f"Text{i}", source)
            tracker.record_consensus_selection(block_id, f"Updated{i}", source, 0.8 + i * 0.05)
        
        ranker = SourceRanker()
        ranking = ranker.rank_sources(tracker.histories)
        
        assert len(ranking.rankings) == 3
        assert ranking.total_blocks == 3
        # Rankings should be sorted by accuracy score
        scores = [metrics.accuracy_score for _, metrics in ranking.rankings]
        assert scores == sorted(scores, reverse=True)
    
    def test_rank_sources_with_config(self):
        """Test ranking sources with configuration hash."""
        tracker = ChangeTracker()
        
        source1 = SourceAttribution(engine_name="tesseract", configuration_hash="config1")
        source2 = SourceAttribution(engine_name="tesseract", configuration_hash="config2")
        
        tracker.record_initial_extract("block_001", "Text1", source1)
        tracker.record_initial_extract("block_002", "Text2", source2)
        
        ranker = SourceRanker()
        ranking = ranker.rank_sources(tracker.histories, include_config=True)
        
        # Should have separate entries for different configs
        assert len(ranking.rankings) == 2
        source_ids = [src_id for src_id, _ in ranking.rankings]
        assert "tesseract:config1" in source_ids
        assert "tesseract:config2" in source_ids
    
    def test_get_best_source_for_block_type(self):
        """Test getting best source for filtered blocks."""
        tracker = ChangeTracker()
        
        source1 = SourceAttribution(engine_name="tesseract")
        source2 = SourceAttribution(engine_name="pymupdf")
        
        # Create blocks with different patterns
        for i in range(5):
            block_id = f"block_{i:03d}"
            source = source1 if i % 2 == 0 else source2
            tracker.record_initial_extract(block_id, f"Text{i}", source)
            tracker.record_consensus_selection(block_id, f"Final{i}", source, 0.9)
        
        ranker = SourceRanker()
        
        # Filter for even blocks (should prefer tesseract)
        def even_filter(block_id, history):
            return int(block_id.split('_')[1]) % 2 == 0
        
        best = ranker.get_best_source_for_block_type(tracker.histories, even_filter)
        assert best is not None
    
    def test_compare_sources(self):
        """Test comparing two sources."""
        tracker = ChangeTracker()
        
        source1 = SourceAttribution(engine_name="tesseract")
        source2 = SourceAttribution(engine_name="pymupdf")
        
        # Give tesseract more selections
        for i in range(3):
            tracker.record_initial_extract(f"block_{i}", f"Text{i}", source1)
            tracker.record_consensus_selection(f"block_{i}", f"Final{i}", source1, 0.9)
        
        # Give pymupdf fewer selections
        tracker.record_initial_extract("block_3", "Text3", source2)
        tracker.record_consensus_selection("block_3", "Final3", source2, 0.85)
        
        ranker = SourceRanker()
        comparison = ranker.compare_sources("tesseract", "pymupdf", tracker.histories)
        
        assert 'winner' in comparison
        assert 'accuracy_score_diff' in comparison
        assert comparison['source1'] == "tesseract"
        assert comparison['source2'] == "pymupdf"
    
    def test_get_ranking_summary(self):
        """Test getting ranking summary."""
        tracker = ChangeTracker()
        
        for i in range(3):
            source = SourceAttribution(engine_name=f"engine{i}")
            tracker.record_initial_extract(f"block_{i}", f"Text{i}", source)
            tracker.record_consensus_selection(f"block_{i}", f"Final{i}", source, 0.8 + i * 0.05)
        
        ranker = SourceRanker()
        ranking = ranker.rank_sources(tracker.histories)
        summary = ranker.get_ranking_summary(ranking)
        
        assert summary['total_sources'] == 3
        assert summary['total_blocks'] == 3
        assert 'best_source' in summary
        assert 'worst_source' in summary
        assert 'avg_accuracy_score' in summary


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_rank_sources_by_accuracy(self):
        """Test rank_sources_by_accuracy convenience function."""
        tracker = ChangeTracker()
        
        source = SourceAttribution(engine_name="tesseract")
        tracker.record_initial_extract("block_001", "Text", source)
        tracker.record_consensus_selection("block_001", "Final", source, 0.9)
        
        ranking = rank_sources_by_accuracy(tracker.histories)
        
        assert len(ranking.rankings) > 0
        assert ranking.total_blocks == 1
    
    def test_get_best_source(self):
        """Test get_best_source convenience function."""
        tracker = ChangeTracker()
        
        source1 = SourceAttribution(engine_name="tesseract")
        source2 = SourceAttribution(engine_name="pymupdf")
        
        # Give tesseract better scores
        tracker.record_initial_extract("block_001", "Text1", source1)
        tracker.record_consensus_selection("block_001", "Final1", source1, 0.95)
        
        tracker.record_initial_extract("block_002", "Text2", source2)
        tracker.record_consensus_selection("block_002", "Final2", source2, 0.80)
        
        best = get_best_source(tracker.histories)
        assert best is not None
        # Should be one of the engines
        assert best in ["tesseract", "pymupdf"]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

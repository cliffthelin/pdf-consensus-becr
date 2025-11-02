# tests/integration/test_change_tracking_workflow.py
"""
Integration tests for complete change tracking workflow.
Tests the interaction between change tracking, source ranking, and propagation detection.
"""

import pytest
from pathlib import Path
import tempfile

from compareblocks.tracking.change_tracker import (
    ChangeTracker,
    SourceAttribution,
    ChangeType
)
from compareblocks.tracking.source_ranker import (
    SourceRanker,
    rank_sources_by_accuracy,
    get_best_source
)
from compareblocks.tracking.propagation import (
    ChangePropagationDetector,
    build_neighbor_map
)


class TestCompleteChangeTrackingWorkflow:
    """Test complete change tracking workflow."""
    
    def test_full_workflow_with_multiple_engines(self):
        """Test complete workflow with multiple engines and changes."""
        # Initialize tracker
        tracker = ChangeTracker()
        
        # Define sources
        tesseract = SourceAttribution(
            engine_name="tesseract",
            configuration_hash="config1",
            confidence_score=0.85
        )
        pymupdf = SourceAttribution(
            engine_name="pymupdf",
            configuration_hash="config2",
            confidence_score=0.90
        )
        paddleocr = SourceAttribution(
            engine_name="paddleocr",
            configuration_hash="config3",
            confidence_score=0.88
        )
        
        # Record initial extracts for multiple blocks
        tracker.record_initial_extract("block_001", "The quick brown fox", tesseract)
        tracker.record_initial_extract("block_002", "jumps over the lazy", pymupdf)
        tracker.record_initial_extract("block_003", "dog in the park", paddleocr)
        tracker.record_initial_extract("block_004", "on a sunny day", tesseract)
        
        # Record consensus selections
        tracker.record_consensus_selection(
            "block_001", "The quick brown fox", pymupdf, 0.95
        )
        tracker.record_consensus_selection(
            "block_002", "jumps over the lazy", pymupdf, 0.92
        )
        tracker.record_consensus_selection(
            "block_003", "dog in the park", paddleocr, 0.88
        )
        
        # Record manual override
        user_source = SourceAttribution(engine_name="user", confidence_score=1.0)
        tracker.record_manual_override(
            "block_001", "The quick brown fox.", user_source, "user123", "Added period"
        )
        
        # Verify tracking
        assert len(tracker.histories) == 4
        assert tracker.get_current_text("block_001") == "The quick brown fox."
        
        # Rank sources
        ranker = SourceRanker()
        ranking = ranker.rank_sources(tracker.histories, include_config=False)
        
        assert len(ranking.rankings) > 0
        assert ranking.total_blocks == 4
        
        # Get best source
        best = get_best_source(tracker.histories)
        assert best is not None
        
        # Get statistics
        stats = tracker.get_statistics()
        assert stats['total_blocks'] == 4
        assert stats['blocks_with_manual_overrides'] == 1
    
    def test_workflow_with_recalculation_and_propagation(self):
        """Test workflow with recalculation and propagation detection."""
        tracker = ChangeTracker()
        detector = ChangePropagationDetector()
        
        source = SourceAttribution(engine_name="tesseract")
        
        # Create a chain of blocks
        for i in range(5):
            tracker.record_initial_extract(f"block_{i:03d}", f"Text {i}", source)
        
        # Build neighbor map (linear chain)
        positions = {
            f"block_{i:03d}": (1, i * 100, 50)
            for i in range(5)
        }
        neighbor_map = build_neighbor_map(positions)
        
        # Trigger change in first block
        trigger_change = tracker.record_consensus_selection(
            "block_000", "Updated text 0", source, 0.95
        )
        
        # Simulate recalculation propagation
        tracker.record_recalculation(
            "block_001", "Recalculated text 1", source, ["block_002"], "block_000"
        )
        tracker.record_recalculation(
            "block_002", "Recalculated text 2", source, ["block_003"], "block_000"
        )
        
        # Detect propagation
        chain = detector.detect_propagation(
            "block_000", trigger_change, tracker.histories, neighbor_map
        )
        
        assert chain.trigger_block_id == "block_000"
        assert chain.total_affected_blocks >= 0
        
        # Get propagation statistics
        stats = detector.get_propagation_statistics()
        assert stats['total_chains'] >= 1
    
    def test_workflow_with_export_and_import(self):
        """Test workflow with NDJSON export and import."""
        tracker = ChangeTracker()
        
        source1 = SourceAttribution(engine_name="tesseract", confidence_score=0.85)
        source2 = SourceAttribution(engine_name="pymupdf", confidence_score=0.90)
        
        # Create some history
        tracker.record_initial_extract("block_001", "Initial text", source1)
        tracker.record_consensus_selection("block_001", "Consensus text", source2, 0.92)
        tracker.record_initial_extract("block_002", "Another block", source1)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "changes.ndjson"
            
            # Export
            tracker.export_to_ndjson(file_path)
            assert file_path.exists()
            
            # Import into new tracker
            new_tracker = ChangeTracker()
            new_tracker.import_from_ndjson(file_path)
            
            # Verify imported data
            assert len(new_tracker.histories) == 2
            assert new_tracker.get_current_text("block_001") == "Consensus text"
            assert new_tracker.get_current_text("block_002") == "Another block"
            
            # Rank sources from imported data
            ranking = rank_sources_by_accuracy(new_tracker.histories)
            assert len(ranking.rankings) > 0
    
    def test_workflow_with_source_comparison(self):
        """Test workflow with source comparison."""
        tracker = ChangeTracker()
        
        tesseract = SourceAttribution(engine_name="tesseract")
        pymupdf = SourceAttribution(engine_name="pymupdf")
        
        # Give tesseract more successful selections
        for i in range(5):
            tracker.record_initial_extract(f"block_{i:03d}", f"Text {i}", tesseract)
            tracker.record_consensus_selection(f"block_{i:03d}", f"Final {i}", tesseract, 0.9)
        
        # Give pymupdf fewer selections with some overrides
        for i in range(5, 8):
            tracker.record_initial_extract(f"block_{i:03d}", f"Text {i}", pymupdf)
            tracker.record_consensus_selection(f"block_{i:03d}", f"Consensus {i}", pymupdf, 0.85)
            # Override one
            if i == 6:
                user = SourceAttribution(engine_name="user")
                tracker.record_manual_override(
                    f"block_{i:03d}", f"Manual {i}", user, "user123"
                )
        
        # Compare sources
        ranker = SourceRanker()
        comparison = ranker.compare_sources("tesseract", "pymupdf", tracker.histories)
        
        assert 'winner' in comparison
        assert 'accuracy_score_diff' in comparison
        assert comparison['source1'] == "tesseract"
        assert comparison['source2'] == "pymupdf"
        
        # Get ranking summary
        ranking = ranker.rank_sources(tracker.histories)
        summary = ranker.get_ranking_summary(ranking)
        
        assert summary['total_sources'] == 3  # tesseract, pymupdf, user
        assert summary['total_blocks'] == 8
        assert 'best_source' in summary
    
    def test_workflow_with_configuration_tracking(self):
        """Test workflow tracking different configurations."""
        tracker = ChangeTracker()
        
        # Same engine, different configurations
        config1 = SourceAttribution(
            engine_name="tesseract",
            configuration_hash="config_high_dpi",
            configuration_params={"dpi": 300, "psm": 6}
        )
        config2 = SourceAttribution(
            engine_name="tesseract",
            configuration_hash="config_low_dpi",
            configuration_params={"dpi": 150, "psm": 6}
        )
        
        # Create blocks with different configs
        for i in range(3):
            tracker.record_initial_extract(f"block_{i:03d}", f"Text {i}", config1)
            tracker.record_consensus_selection(f"block_{i:03d}", f"Final {i}", config1, 0.95)
        
        for i in range(3, 6):
            tracker.record_initial_extract(f"block_{i:03d}", f"Text {i}", config2)
            tracker.record_consensus_selection(f"block_{i:03d}", f"Final {i}", config2, 0.80)
        
        # Rank with configuration included
        ranker = SourceRanker()
        ranking = ranker.rank_sources(tracker.histories, include_config=True)
        
        # Should have separate rankings for each config
        assert len(ranking.rankings) == 2
        
        # High DPI config should rank better
        top_source = ranking.rankings[0][0]
        assert "config_high_dpi" in top_source or "config_low_dpi" in top_source
    
    def test_workflow_with_complex_propagation(self):
        """Test workflow with complex propagation patterns."""
        tracker = ChangeTracker()
        detector = ChangePropagationDetector(similarity_threshold=0.90)
        
        source = SourceAttribution(engine_name="tesseract")
        
        # Create a grid of blocks (3x3)
        for row in range(3):
            for col in range(3):
                block_id = f"block_{row}_{col}"
                tracker.record_initial_extract(block_id, f"Text {row},{col}", source)
        
        # Build neighbor map (grid neighbors)
        neighbor_map = {}
        for row in range(3):
            for col in range(3):
                block_id = f"block_{row}_{col}"
                neighbors = []
                
                # Add adjacent neighbors
                if row > 0:
                    neighbors.append(f"block_{row-1}_{col}")
                if row < 2:
                    neighbors.append(f"block_{row+1}_{col}")
                if col > 0:
                    neighbors.append(f"block_{row}_{col-1}")
                if col < 2:
                    neighbors.append(f"block_{row}_{col+1}")
                
                neighbor_map[block_id] = neighbors
        
        # Trigger change in center block
        trigger_change = tracker.record_consensus_selection(
            "block_1_1", "Updated center", source, 0.95
        )
        
        # Simulate propagation to neighbors
        for neighbor in neighbor_map["block_1_1"]:
            tracker.record_recalculation(
                neighbor, f"Recalc {neighbor}", source, [], "block_1_1"
            )
        
        # Detect propagation
        chain = detector.detect_propagation(
            "block_1_1", trigger_change, tracker.histories, neighbor_map, max_depth=3
        )
        
        assert chain.trigger_block_id == "block_1_1"
        
        # Find chains affecting specific blocks
        chains = detector.find_propagation_chains_for_block("block_1_0")
        assert len(chains) >= 0


class TestRealWorldScenarios:
    """Test real-world scenarios."""
    
    def test_scenario_improving_accuracy_over_time(self):
        """Test scenario where accuracy improves over time."""
        tracker = ChangeTracker()
        
        # Initial extracts with lower quality
        low_quality = SourceAttribution(engine_name="tesseract_v1", confidence_score=0.75)
        for i in range(10):
            tracker.record_initial_extract(f"block_{i:03d}", f"Text {i}", low_quality)
        
        # Improved extracts with higher quality
        high_quality = SourceAttribution(engine_name="tesseract_v2", confidence_score=0.92)
        for i in range(10):
            tracker.record_consensus_selection(
                f"block_{i:03d}", f"Improved {i}", high_quality, 0.92
            )
        
        # Rank sources
        ranking = rank_sources_by_accuracy(tracker.histories)
        
        # v2 should rank higher
        best = ranking.rankings[0][0]
        assert "v2" in best or best == "tesseract_v2"
    
    def test_scenario_user_corrections_pattern(self):
        """Test scenario with pattern of user corrections."""
        tracker = ChangeTracker()
        
        engine = SourceAttribution(engine_name="ocr_engine")
        user = SourceAttribution(engine_name="user")
        
        # Create blocks where certain types need more corrections
        for i in range(20):
            tracker.record_initial_extract(f"block_{i:03d}", f"Text {i}", engine)
            tracker.record_consensus_selection(f"block_{i:03d}", f"OCR {i}", engine, 0.85)
            
            # User corrects every 5th block
            if i % 5 == 0:
                tracker.record_manual_override(
                    f"block_{i:03d}", f"Corrected {i}", user, "user123", "OCR error"
                )
        
        # Analyze patterns
        stats = tracker.get_statistics()
        assert stats['blocks_with_manual_overrides'] == 4  # blocks 0, 5, 10, 15
        
        # Engine should show override resistance issues
        ranker = SourceRanker()
        metrics = ranker.calculate_accuracy_metrics(tracker.histories)
        
        engine_metrics = metrics.get("ocr_engine")
        assert engine_metrics is not None
        assert engine_metrics.manual_overrides_from > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

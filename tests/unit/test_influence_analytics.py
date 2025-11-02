# tests/unit/test_influence_analytics.py
"""
Unit tests for influence percentage and analytics integration.

Tests the calculation of influence percentages, consensus output tracking,
and analytics integration through MCP communication.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from compareblocks.analytics.influence import (
    InfluenceCalculator,
    InfluenceMetrics,
    calculate_influence_percentages,
    track_consensus_contribution
)
from compareblocks.analytics.engine_analytics import EngineAnalytics, EnginePerformanceMetrics
from compareblocks.consensus.policy import ConsensusDecision, DecisionAction
from compareblocks.consensus.score import VariationScore
from compareblocks.config.file_manager import file_manager


class TestInfluenceCalculator:
    """Test influence percentage calculation."""
    
    def test_calculate_basic_influence(self):
        """Test basic influence percentage calculation."""
        calculator = InfluenceCalculator()
        
        # Create sample consensus decisions
        decisions = [
            ConsensusDecision(
                action=DecisionAction.PICK,
                selected_text="Sample text",
                selected_engine="tesseract",
                decision_reason="clear_winner",
                confidence_score=0.85,
                engine_scores={"tesseract": 0.85, "pymupdf": 0.75, "paddleocr": 0.65},
                anomaly_score=0.1,
                flags=[],
                merge_candidates=[],
                metadata={}
            ),
            ConsensusDecision(
                action=DecisionAction.PICK,
                selected_text="Another text",
                selected_engine="pymupdf",
                decision_reason="clear_winner",
                confidence_score=0.90,
                engine_scores={"tesseract": 0.70, "pymupdf": 0.90, "paddleocr": 0.60},
                anomaly_score=0.05,
                flags=[],
                merge_candidates=[],
                metadata={}
            ),
            ConsensusDecision(
                action=DecisionAction.PICK,
                selected_text="Third text",
                selected_engine="tesseract",
                decision_reason="clear_winner",
                confidence_score=0.80,
                engine_scores={"tesseract": 0.80, "pymupdf": 0.70, "paddleocr": 0.75},
                anomaly_score=0.15,
                flags=[],
                merge_candidates=[],
                metadata={}
            )
        ]
        
        # Calculate influence
        influence = calculator.calculate_influence(decisions)
        
        # Verify results
        assert isinstance(influence, InfluenceMetrics)
        assert "tesseract" in influence.engine_percentages
        assert "pymupdf" in influence.engine_percentages
        
        # Tesseract should have highest influence (2 out of 3 selections)
        assert influence.engine_percentages["tesseract"] > influence.engine_percentages["pymupdf"]
        
        # Total should be approximately 100%
        total = sum(influence.engine_percentages.values())
        assert 99.0 <= total <= 101.0
    
    def test_calculate_influence_with_weights(self):
        """Test influence calculation with score weights."""
        calculator = InfluenceCalculator(use_score_weights=True)
        
        decisions = [
            ConsensusDecision(
                block_id="block_1",
                selected_engine="tesseract",
                final_text="Text",
                consensus_score=0.95,  # High score
                decision_action=DecisionAction.AUTO_SELECT,
                engine_scores={"tesseract": 0.95, "pymupdf": 0.50},
                anomaly_score=0.05,
                flags=[],
                merge_candidates=[]
            ),
            ConsensusDecision(
                block_id="block_2",
                selected_engine="pymupdf",
                final_text="Text",
                consensus_score=0.60,  # Low score
                decision_action=DecisionAction.AUTO_SELECT,
                engine_scores={"tesseract": 0.55, "pymupdf": 0.60},
                anomaly_score=0.20,
                flags=[],
                merge_candidates=[]
            )
        ]
        
        influence = calculator.calculate_influence(decisions)
        
        # Tesseract should have higher influence due to higher score weight
        assert influence.engine_percentages["tesseract"] > influence.engine_percentages["pymupdf"]
    
    def test_calculate_influence_empty_decisions(self):
        """Test influence calculation with empty decisions."""
        calculator = InfluenceCalculator()
        
        influence = calculator.calculate_influence([])
        
        assert isinstance(influence, InfluenceMetrics)
        assert len(influence.engine_percentages) == 0
        assert influence.total_blocks == 0
        assert influence.consensus_blocks == 0
    
    def test_calculate_influence_with_manual_overrides(self):
        """Test influence calculation excluding manual overrides."""
        calculator = InfluenceCalculator(include_manual_overrides=False)
        
        decisions = [
            ConsensusDecision(
                block_id="block_1",
                selected_engine="tesseract",
                final_text="Text",
                consensus_score=0.85,
                decision_action=DecisionAction.AUTO_SELECT,
                engine_scores={"tesseract": 0.85},
                anomaly_score=0.1,
                flags=[],
                merge_candidates=[]
            ),
            ConsensusDecision(
                block_id="block_2",
                selected_engine="pymupdf",
                final_text="Text",
                consensus_score=0.90,
                decision_action=DecisionAction.MANUAL_OVERRIDE,
                engine_scores={"pymupdf": 0.90},
                anomaly_score=0.05,
                flags=["manual_override"],
                merge_candidates=[]
            )
        ]
        
        influence = calculator.calculate_influence(decisions)
        
        # Only tesseract should be counted (manual override excluded)
        assert influence.engine_percentages.get("tesseract", 0) == 100.0
        assert influence.engine_percentages.get("pymupdf", 0) == 0.0
    
    def test_track_consensus_contribution(self):
        """Test tracking consensus contribution over time."""
        pdf_path = file_manager.get_target_pdf_path()
        
        decisions = [
            ConsensusDecision(
                block_id="block_1",
                selected_engine="tesseract",
                final_text="Text",
                consensus_score=0.85,
                decision_action=DecisionAction.AUTO_SELECT,
                engine_scores={"tesseract": 0.85, "pymupdf": 0.75},
                anomaly_score=0.1,
                flags=[],
                merge_candidates=[]
            )
        ]
        
        # Track contribution
        result = track_consensus_contribution(pdf_path, decisions)
        
        assert "influence_metrics" in result
        assert "timestamp" in result
        assert "pdf_path" in result
        assert result["pdf_path"] == pdf_path


class TestInfluenceMetrics:
    """Test InfluenceMetrics data class."""
    
    def test_influence_metrics_creation(self):
        """Test creating influence metrics."""
        metrics = InfluenceMetrics(
            engine_percentages={"tesseract": 60.0, "pymupdf": 40.0},
            total_blocks=100,
            consensus_blocks=95,
            manual_override_blocks=5,
            flagged_blocks=10,
            engine_selection_counts={"tesseract": 60, "pymupdf": 40},
            weighted_scores={"tesseract": 0.85, "pymupdf": 0.80}
        )
        
        assert metrics.engine_percentages["tesseract"] == 60.0
        assert metrics.total_blocks == 100
        assert metrics.consensus_blocks == 95
    
    def test_influence_metrics_to_dict(self):
        """Test converting influence metrics to dictionary."""
        metrics = InfluenceMetrics(
            engine_percentages={"tesseract": 60.0},
            total_blocks=100,
            consensus_blocks=95,
            manual_override_blocks=5,
            flagged_blocks=10,
            engine_selection_counts={"tesseract": 60},
            weighted_scores={"tesseract": 0.85}
        )
        
        data = metrics.to_dict()
        
        assert isinstance(data, dict)
        assert data["engine_percentages"]["tesseract"] == 60.0
        assert data["total_blocks"] == 100


class TestAnalyticsIntegration:
    """Test analytics integration with influence calculation."""
    
    def test_integrate_influence_with_engine_analytics(self):
        """Test integrating influence metrics with engine analytics."""
        # Create engine analytics
        analytics = EngineAnalytics()
        
        # Create sample decisions
        decisions = [
            ConsensusDecision(
                block_id="block_1",
                selected_engine="tesseract",
                final_text="Text",
                consensus_score=0.85,
                decision_action=DecisionAction.AUTO_SELECT,
                engine_scores={"tesseract": 0.85, "pymupdf": 0.75},
                anomaly_score=0.1,
                flags=[],
                merge_candidates=[]
            )
        ]
        
        # Get engine metrics
        engine_metrics = analytics.analyze_consensus_decisions(decisions)
        
        # Calculate influence
        calculator = InfluenceCalculator()
        influence = calculator.calculate_influence(decisions)
        
        # Verify integration
        assert len(engine_metrics) > 0
        assert len(influence.engine_percentages) > 0
        
        # Engines in metrics should match engines in influence
        for engine in engine_metrics.keys():
            assert engine in influence.engine_percentages
    
    def test_calculate_influence_percentages_convenience_function(self):
        """Test convenience function for calculating influence."""
        decisions = [
            ConsensusDecision(
                block_id="block_1",
                selected_engine="tesseract",
                final_text="Text",
                consensus_score=0.85,
                decision_action=DecisionAction.AUTO_SELECT,
                engine_scores={"tesseract": 0.85},
                anomaly_score=0.1,
                flags=[],
                merge_candidates=[]
            )
        ]
        
        influence = calculate_influence_percentages(decisions)
        
        assert isinstance(influence, InfluenceMetrics)
        assert "tesseract" in influence.engine_percentages


class TestConsensusOutputTracking:
    """Test consensus output tracking functionality."""
    
    def test_track_consensus_output_file(self):
        """Test tracking consensus output file."""
        from compareblocks.analytics.influence import ConsensusOutputTracker
        
        tracker = ConsensusOutputTracker()
        pdf_path = file_manager.get_target_pdf_path()
        consensus_file = Path(file_manager.get_processing_directory()) / "consensus_output.json"
        
        # Track consensus output
        tracker.track_output(pdf_path, consensus_file)
        
        # Verify tracking
        tracked = tracker.get_tracked_output(pdf_path)
        assert tracked is not None
        assert tracked["consensus_file"] == str(consensus_file)
    
    def test_track_consensus_exports(self):
        """Test tracking consensus export files."""
        from compareblocks.analytics.influence import ConsensusOutputTracker
        
        tracker = ConsensusOutputTracker()
        pdf_path = file_manager.get_target_pdf_path()
        
        export_files = [
            Path(file_manager.get_processing_directory()) / "output.txt",
            Path(file_manager.get_processing_directory()) / "output.csv"
        ]
        
        # Track exports
        tracker.track_exports(pdf_path, export_files)
        
        # Verify tracking
        tracked = tracker.get_tracked_output(pdf_path)
        assert tracked is not None
        assert len(tracked["export_files"]) == 2


class TestRealTimeAnalyticsUpdates:
    """Test real-time analytics updates during reprocessing."""
    
    def test_analytics_update_on_reprocessing(self):
        """Test that analytics update when reprocessing occurs."""
        from compareblocks.analytics.influence import InfluenceAnalyticsManager
        
        manager = InfluenceAnalyticsManager()
        pdf_path = file_manager.get_target_pdf_path()
        
        # Initial processing
        decisions_v1 = [
            ConsensusDecision(
                block_id="block_1",
                selected_engine="tesseract",
                final_text="Text",
                consensus_score=0.85,
                decision_action=DecisionAction.AUTO_SELECT,
                engine_scores={"tesseract": 0.85},
                anomaly_score=0.1,
                flags=[],
                merge_candidates=[]
            )
        ]
        
        result_v1 = manager.update_analytics(pdf_path, decisions_v1)
        influence_v1 = result_v1["influence_metrics"]
        
        # Reprocessing with different results
        decisions_v2 = [
            ConsensusDecision(
                block_id="block_1",
                selected_engine="pymupdf",
                final_text="Text",
                consensus_score=0.90,
                decision_action=DecisionAction.AUTO_SELECT,
                engine_scores={"pymupdf": 0.90},
                anomaly_score=0.05,
                flags=[],
                merge_candidates=[]
            )
        ]
        
        result_v2 = manager.update_analytics(pdf_path, decisions_v2)
        influence_v2 = result_v2["influence_metrics"]
        
        # Verify analytics updated
        assert influence_v1.engine_percentages != influence_v2.engine_percentages
        assert result_v2["version"] > result_v1["version"]


@pytest.mark.integration
class TestInfluenceAnalyticsIntegration:
    """Integration tests for influence analytics with real data."""
    
    def test_end_to_end_influence_calculation(self):
        """Test end-to-end influence calculation with real PDF."""
        from compareblocks.gbg.processor import GBGProcessor
        from compareblocks.engines.manager import EngineManager
        from compareblocks.consensus.score import ConsensusScorer
        from compareblocks.analytics.influence import calculate_influence_percentages
        
        pdf_path = file_manager.get_target_pdf_path()
        
        # Process PDF through GBG
        gbg_processor = GBGProcessor()
        seed_blocks = gbg_processor.process_pdf(pdf_path)
        
        # Skip if no blocks (PDF not available)
        if not seed_blocks:
            pytest.skip("No seed blocks generated - PDF may not be available")
        
        # Create mock consensus decisions
        decisions = []
        for i, block in enumerate(seed_blocks[:5]):  # Use first 5 blocks
            decisions.append(
                ConsensusDecision(
                    block_id=block.block_id,
                    selected_engine="tesseract" if i % 2 == 0 else "pymupdf",
                    final_text=f"Block {i} text",
                    consensus_score=0.85,
                    decision_action=DecisionAction.AUTO_SELECT,
                    engine_scores={"tesseract": 0.85, "pymupdf": 0.75},
                    anomaly_score=0.1,
                    flags=[],
                    merge_candidates=[]
                )
            )
        
        # Calculate influence
        influence = calculate_influence_percentages(decisions)
        
        # Verify results
        assert influence.total_blocks == len(decisions)
        assert sum(influence.engine_percentages.values()) > 99.0
        assert "tesseract" in influence.engine_percentages
        assert "pymupdf" in influence.engine_percentages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

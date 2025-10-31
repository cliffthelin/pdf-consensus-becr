# tests/unit/test_analytics_dashboard.py
"""
Tests for analytics dashboard functionality.
Tests engine performance dashboards and optimization insights using real data.
"""

import pytest
import statistics
from datetime import datetime

from src.compareblocks.analytics.dashboard import (
    AnalyticsDashboard, create_performance_dashboard, create_quality_dashboard
)
from src.compareblocks.analytics.engine_analytics import EnginePerformanceMetrics
from src.compareblocks.analytics.report_generator import AnalyticsReport
from src.compareblocks.consensus.score import VariationScore, ConsensusScorer
from src.compareblocks.consensus.policy import ConsensusDecision, DecisionAction
from src.compareblocks.engines.manager import ExtractionEngineManager
from src.compareblocks.config.file_manager import file_manager
from compareblocks.consensus.score import ConsensusScorer


class TestAnalyticsDashboard:
    """Test analytics dashboard functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dashboard = AnalyticsDashboard()
        self.pdf_path = file_manager.get_target_pdf_path()
    
    def test_create_performance_dashboard_real_metrics(self):
        """Test performance dashboard creation with real metrics."""
        # Create realistic performance metrics
        metrics = {
            'high_performer': EnginePerformanceMetrics(
                engine_name='high_performer',
                total_extractions=20,
                successful_extractions=20,
                failed_extractions=0,
                success_rate=100.0,
                avg_extraction_time=1.2,
                min_extraction_time=0.8,
                max_extraction_time=1.5,
                total_extraction_time=24.0,
                avg_score=0.92,
                min_score=0.85,
                max_score=0.98,
                score_variance=0.002,
                selections_count=18,
                selection_rate=90.0,
                manual_override_count=1,
                manual_override_rate=5.0,
                anomaly_detection_count=0,
                anomaly_detection_rate=0.0,
                common_flags={},
                accuracy_metrics={'total_variations': 20}
            ),
            'medium_performer': EnginePerformanceMetrics(
                engine_name='medium_performer',
                total_extractions=20,
                successful_extractions=18,
                failed_extractions=2,
                success_rate=90.0,
                avg_extraction_time=2.5,
                min_extraction_time=1.8,
                max_extraction_time=3.2,
                total_extraction_time=50.0,
                avg_score=0.75,
                min_score=0.60,
                max_score=0.88,
                score_variance=0.015,
                selections_count=10,
                selection_rate=50.0,
                manual_override_count=3,
                manual_override_rate=15.0,
                anomaly_detection_count=2,
                anomaly_detection_rate=10.0,
                common_flags={'low_language_fitness': 1},
                accuracy_metrics={'total_variations': 18}
            ),
            'low_performer': EnginePerformanceMetrics(
                engine_name='low_performer',
                total_extractions=20,
                successful_extractions=14,
                failed_extractions=6,
                success_rate=70.0,
                avg_extraction_time=8.0,
                min_extraction_time=5.0,
                max_extraction_time=12.0,
                total_extraction_time=160.0,
                avg_score=0.45,
                min_score=0.20,
                max_score=0.70,
                score_variance=0.08,
                selections_count=3,
                selection_rate=15.0,
                manual_override_count=8,
                manual_override_rate=40.0,
                anomaly_detection_count=6,
                anomaly_detection_rate=30.0,
                common_flags={'high_anomaly_score': 4, 'low_language_fitness': 2},
                accuracy_metrics={'total_variations': 14}
            )
        }
        
        # Create performance dashboard
        dashboard = self.dashboard.create_performance_dashboard(metrics)
        
        # Verify dashboard structure
        assert dashboard is not None and isinstance(dashboard, dict)
        assert dashboard['title'] == 'Engine Performance Dashboard'
        assert dashboard['status'] == 'active'
        assert 'timestamp' in dashboard
        
        # Verify summary
        assert 'summary' in dashboard
        summary = dashboard['summary']
        assert abs(summary['total_engines'] - 3) < 0.01, f"Expected summary['total_engines'] to be close to 3"
        assert 0.0 <= summary['avg_score'] <= 1.0
        assert 0.0 <= summary['avg_success_rate'] <= 100.0
        assert 0.0 <= summary['avg_selection_rate'] <= 100.0
        assert summary['best_engine'] == 'high_performer'
        assert summary['worst_engine'] == 'low_performer'
        
        # Verify engine rankings
        assert 'engine_rankings' in dashboard
        rankings = dashboard['engine_rankings']
        assert abs(len(rankings) - 3) < 0.01, f"Expected len(rankings) to be close to 3"
        assert rankings[0]['engine'] == 'high_performer'
        assert abs(rankings[0]['rank'] - 1) < 0.01, f"Expected rankings[0]['rank'] to be close to 1"
        assert rankings[0]['performance_level'] == 'excellent'
        assert rankings[2]['engine'] == 'low_performer'
        assert abs(rankings[2]['rank'] - 3) < 0.01, f"Expected rankings[2]['rank'] to be close to 3"
        assert rankings[2]['performance_level'] in ['poor', 'fair']  # Depends on calculated score
        
        # Verify performance matrix
        assert 'performance_matrix' in dashboard
        matrix = dashboard['performance_matrix']
        assert abs(len(matrix) - 3) < 0.01, f"Expected len(matrix) to be close to 3"
        
        for engine_data in matrix:
            assert 'engine' in engine_data
            assert 'success_rate' in engine_data
            assert 'avg_score' in engine_data
            assert 'selection_rate' in engine_data
            assert 'performance_indicators' in engine_data
            
            indicators = engine_data['performance_indicators']
            assert 'speed' in indicators
            assert 'quality' in indicators
            assert 'reliability' in indicators
            assert 'selection' in indicators
        
        # Verify alerts
        assert 'alerts' in dashboard
        alerts = dashboard['alerts']
        assert alerts is not None and isinstance(alerts, list)
        
        # Should have alerts for low performer
        low_performer_alerts = [a for a in alerts if a.get('engine') == 'low_performer']
        assert len(low_performer_alerts) > 0
        
        # Verify recommendations
        assert 'recommendations' in dashboard
        recommendations = dashboard['recommendations']
        assert recommendations is not None and isinstance(recommendations, list)
        assert len(recommendations) > 0


class TestAnalyticsDashboardEdgeCases:
    """Test edge cases and error conditions for analytics dashboard."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dashboard = AnalyticsDashboard()
    
    def test_create_performance_dashboard_no_data(self):
        """Test performance dashboard with no data."""
        dashboard = self.dashboard.create_performance_dashboard({})
        
        assert dashboard is not None and isinstance(dashboard, dict)
        assert dashboard['title'] == 'Engine Performance Dashboard'
        assert dashboard['status'] == 'no_data'
        assert 'message' in dashboard
        assert dashboard['message'] == 'No performance data available'
    
    def test_create_quality_dashboard_real_data(self):
        """Test quality dashboard creation with real data."""
        # Create real variation scores
        scorer = ConsensusScorer()
        variations = [
            {'text': 'High quality text with excellent language fitness.', 'engine': 'engine1'},
            {'text': 'Medium quality text with some issues.', 'engine': 'engine2'},
            {'text': 'L0w qu4l1ty t3xt w1th m4ny 0CR 3rr0rs.', 'engine': 'engine3'},  # OCR errors
            {'text': 'Repetitive text text text text text.', 'engine': 'engine4'}  # Repetitive
        ]
        
        variation_scores = scorer.score_variations(variations)
        
        # Create consensus decisions
        decisions = []
        for i, scores in enumerate([variation_scores]):
            best_score = max(scores, key=lambda x: x.final_score)
            
            # Add manual override for some decisions
            flags = ['manual_override'] if i % 2 == 0 else []
            
            decision = ConsensusDecision(action=DecisionAction.PICK,
                selected_text=best_score.raw_text,
                selected_engine=best_score.engine_name,
                decision_reason="test_quality",
                confidence_score=best_score.final_score,
                engine_scores={s.engine_name: s.final_score for s in scores},
                anomaly_score=best_score.anomaly_score,
                merge_candidates=[],
                flags=flags,
                metadata={})
            decisions.append(decision)
        
        # Create quality dashboard
        dashboard = self.dashboard.create_quality_dashboard(variation_scores, decisions)
        
        # Verify dashboard structure
        assert dashboard is not None and isinstance(dashboard, dict)
        assert dashboard['title'] == 'Quality Metrics Dashboard'
        assert dashboard['status'] == 'active'
        assert 'timestamp' in dashboard
        
        # Verify quality metrics
        assert 'quality_metrics' in dashboard
        quality_metrics = dashboard['quality_metrics']
        assert 'total_variations' in quality_metrics
        assert 'avg_final_score' in quality_metrics
        assert 'score_distribution' in quality_metrics
        assert 'avg_language_score' in quality_metrics
        assert 'avg_anomaly_score' in quality_metrics
        
        assert quality_metrics['total_variations'] == len(variation_scores)
        assert 0.0 <= quality_metrics['avg_final_score'] <= 1.0
        
        # Verify score distribution
        distribution = quality_metrics['score_distribution']
        assert 'excellent' in distribution
        assert 'good' in distribution
        assert 'fair' in distribution
        assert 'poor' in distribution
        assert sum(distribution.values()) == len(variation_scores)
        
        # Verify decision metrics
        assert 'decision_metrics' in dashboard
        decision_metrics = dashboard['decision_metrics']
        assert 'total_decisions' in decision_metrics
        assert 'avg_confidence' in decision_metrics
        assert 'confidence_distribution' in decision_metrics
        assert 'manual_override_count' in decision_metrics
        assert 'manual_override_rate' in decision_metrics
        
        assert decision_metrics['total_decisions'] == len(decisions)
        assert 0.0 <= decision_metrics['avg_confidence'] <= 1.0
        assert 0.0 <= decision_metrics['manual_override_rate'] <= 100.0
        
        # Verify alerts
        assert 'quality_alerts' in dashboard
        alerts = dashboard['quality_alerts']
        assert alerts is not None and isinstance(alerts, list)
        
        # Verify quality trends
        assert 'quality_trends' in dashboard
        trends = dashboard['quality_trends']
        assert trends is not None and isinstance(trends, dict)
    
    def test_create_optimization_dashboard_real_data(self):
        """Test optimization dashboard creation with real data."""
        # Create realistic performance metrics
        metrics = {
            'underutilized_engine': EnginePerformanceMetrics(
                engine_name='underutilized_engine',
                total_extractions=10,
                successful_extractions=10,
                failed_extractions=0,
                success_rate=100.0,
                avg_extraction_time=2.0,
                min_extraction_time=1.5,
                max_extraction_time=2.5,
                total_extraction_time=20.0,
                avg_score=0.85,  # Good quality
                min_score=0.75,
                max_score=0.95,
                score_variance=0.01,
                selections_count=2,  # Low selection rate
                selection_rate=20.0,  # Underutilized despite good quality
                manual_override_count=1,
                manual_override_rate=10.0,
                anomaly_detection_count=0,
                anomaly_detection_rate=0.0,
                common_flags={},
                accuracy_metrics={}
            ),
            'high_anomaly_engine': EnginePerformanceMetrics(
                engine_name='high_anomaly_engine',
                total_extractions=10,
                successful_extractions=9,
                failed_extractions=1,
                success_rate=90.0,
                avg_extraction_time=3.0,
                min_extraction_time=2.0,
                max_extraction_time=4.0,
                total_extraction_time=30.0,
                avg_score=0.65,
                min_score=0.40,
                max_score=0.80,
                score_variance=0.05,
                selections_count=5,
                selection_rate=50.0,
                manual_override_count=2,
                manual_override_rate=20.0,
                anomaly_detection_count=4,  # High anomaly rate
                anomaly_detection_rate=40.0,
                common_flags={'high_anomaly_score': 3, 'low_language_fitness': 1},
                accuracy_metrics={}
            ),
            'slow_reliable_engine': EnginePerformanceMetrics(
                engine_name='slow_reliable_engine',
                total_extractions=10,
                successful_extractions=10,
                failed_extractions=0,
                success_rate=100.0,  # Very reliable
                avg_extraction_time=15.0,  # Very slow
                min_extraction_time=12.0,
                max_extraction_time=18.0,
                total_extraction_time=150.0,
                avg_score=0.80,
                min_score=0.70,
                max_score=0.90,
                score_variance=0.02,
                selections_count=6,
                selection_rate=60.0,
                manual_override_count=1,
                manual_override_rate=10.0,
                anomaly_detection_count=0,
                anomaly_detection_rate=0.0,
                common_flags={},
                accuracy_metrics={}
            )
        }
        
        # Create some sample recent reports
        recent_reports = []  # Empty for this test
        
        # Create optimization dashboard
        dashboard = self.dashboard.create_optimization_dashboard(metrics, recent_reports)
        
        # Verify dashboard structure
        assert dashboard is not None and isinstance(dashboard, dict)
        assert dashboard['title'] == 'Optimization Insights Dashboard'
        assert dashboard['status'] == 'active'
        assert 'timestamp' in dashboard
        
        # Verify optimization opportunities
        assert 'optimization_opportunities' in dashboard
        opportunities = dashboard['optimization_opportunities']
        assert opportunities is not None and isinstance(opportunities, list)
        assert len(opportunities) > 0
        
        # Should identify underutilized engine
        underutilized_ops = [op for op in opportunities if op.get('type') == 'underutilized_engine']
        assert len(underutilized_ops) > 0
        assert underutilized_ops[0]['engine'] == 'underutilized_engine'
        
        # Should identify anomaly reduction opportunity
        anomaly_ops = [op for op in opportunities if op.get('type') == 'anomaly_reduction']
        assert len(anomaly_ops) > 0
        assert anomaly_ops[0]['engine'] == 'high_anomaly_engine'
        
        # Should identify speed optimization opportunity
        speed_ops = [op for op in opportunities if op.get('type') == 'speed_optimization']
        assert len(speed_ops) > 0
        assert speed_ops[0]['engine'] == 'slow_reliable_engine'
        
        # Verify trend analysis
        assert 'trend_analysis' in dashboard
        trend_analysis = dashboard['trend_analysis']
        assert trend_analysis is not None and isinstance(trend_analysis, dict)
        assert trend_analysis['status'] == 'insufficient_data'  # No reports provided
        
        # Verify optimization recommendations
        assert 'optimization_recommendations' in dashboard
        recommendations = dashboard['optimization_recommendations']
        assert recommendations is not None and isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Verify performance gaps
        assert 'performance_gaps' in dashboard
        gaps = dashboard['performance_gaps']
        assert gaps is not None and isinstance(gaps, list)
        
        # Verify improvement potential
        assert 'improvement_potential' in dashboard
        potential = dashboard['improvement_potential']
        assert potential is not None and isinstance(potential, dict)
        assert 'potential' in potential
        assert 'status' in potential
        assert potential['status'] == 'calculated'


class TestAnalyticsDashboardConvenienceFunctions:
    """Test convenience functions for analytics dashboard."""
    
    def setup_method(self):
        """Set up test fixtures."""
        pass
    
    def test_create_performance_dashboard_convenience_function(self):
        """Test convenience function for creating performance dashboard."""
        # Create sample metrics
        metrics = {
            'engine1': EnginePerformanceMetrics(
                engine_name='engine1',
                total_extractions=5,
                successful_extractions=5,
                failed_extractions=0,
                success_rate=100.0,
                avg_extraction_time=1.0,
                min_extraction_time=0.8,
                max_extraction_time=1.2,
                total_extraction_time=5.0,
                avg_score=0.9,
                min_score=0.8,
                max_score=1.0,
                score_variance=0.01,
                selections_count=4,
                selection_rate=80.0,
                manual_override_count=0,
                manual_override_rate=0.0,
                anomaly_detection_count=0,
                anomaly_detection_rate=0.0,
                common_flags={},
                accuracy_metrics={}
            )
        }
        
        # Use convenience function
        dashboard = create_performance_dashboard(metrics)
        
        # Verify results
        assert dashboard is not None and isinstance(dashboard, dict)
        assert dashboard['title'] == 'Engine Performance Dashboard'
        assert dashboard['status'] == 'active'
        assert abs(len(dashboard['engine_rankings']) - 1) < 0.01, f"Expected len(dashboard['engine_rankings']) to be close to 1"
    
    def test_create_quality_dashboard_convenience_function(self):
        """Test convenience function for creating quality dashboard."""
        # Create real variation scores
        scorer = ConsensusScorer()
        variations = [
            {'text': 'Sample text for quality testing.', 'engine': 'engine1'},
            {'text': 'Another sample text for testing.', 'engine': 'engine2'}
        ]
        variation_scores = scorer.score_variations(variations)
        
        # Create sample consensus decisions
        best_score = max(variation_scores, key=lambda x: x.final_score)
        decisions = [
            ConsensusDecision(action=DecisionAction.PICK,
                selected_text=best_score.raw_text,
                selected_engine=best_score.engine_name,
                decision_reason="test",
                confidence_score=best_score.final_score,
                engine_scores={s.engine_name: s.final_score for s in variation_scores},
                anomaly_score=best_score.anomaly_score,
                merge_candidates=[],
                flags=[],
                metadata={})
        ]
        
        # Use convenience function
        dashboard = create_quality_dashboard(variation_scores, decisions)
        
        # Verify results
        assert dashboard is not None and isinstance(dashboard, dict)
        assert dashboard['title'] == 'Quality Metrics Dashboard'
        assert dashboard['status'] == 'active'
        assert 'quality_metrics' in dashboard
        assert 'decision_metrics' in dashboard


class TestAnalyticsDashboardEdgeCases:
    """Test edge cases and error conditions for analytics dashboard."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dashboard = AnalyticsDashboard()
    
    def test_create_performance_dashboard_no_data(self):
        """Test performance dashboard with no data."""
        dashboard = self.dashboard.create_performance_dashboard({})
        
        assert dashboard is not None and isinstance(dashboard, dict)
        assert dashboard['title'] == 'Engine Performance Dashboard'
        assert dashboard['status'] == 'no_data'
        assert 'message' in dashboard
        assert dashboard['message'] == 'No performance data available'
    
    def test_create_quality_dashboard_no_data(self):
        """Test quality dashboard with no data."""
        dashboard = self.dashboard.create_quality_dashboard([], [])
        
        assert dashboard is not None and isinstance(dashboard, dict)
        assert dashboard['title'] == 'Quality Metrics Dashboard'
        assert dashboard['status'] == 'no_data'
        assert 'message' in dashboard
        assert dashboard['message'] == 'No quality data available'
    
    def test_create_optimization_dashboard_no_data(self):
        """Test optimization dashboard with no data."""
        dashboard = self.dashboard.create_optimization_dashboard({}, [])
        
        assert dashboard is not None and isinstance(dashboard, dict)
        assert dashboard['title'] == 'Optimization Insights Dashboard'
        assert dashboard['status'] == 'no_data'
        assert 'message' in dashboard
        assert dashboard['message'] == 'No optimization data available'
    
    def test_performance_level_ratings(self):
        """Test performance level rating function."""
        # Test excellent performance
        assert self.dashboard._get_performance_level(85) == 'excellent'
        
        # Test good performance
        assert self.dashboard._get_performance_level(65) == 'good'
        
        # Test fair performance
        assert self.dashboard._get_performance_level(45) == 'fair'
        
        # Test poor performance
        assert self.dashboard._get_performance_level(25) == 'poor'
    
    def test_rate_performance_different_metrics(self):
        """Test performance rating for different metric types."""
        # Test time metrics (lower is better)
        assert self.dashboard._rate_performance(0.5, 'time') == 'excellent'
        assert self.dashboard._rate_performance(2.0, 'time') == 'good'
        assert self.dashboard._rate_performance(5.0, 'time') == 'fair'
        assert self.dashboard._rate_performance(15.0, 'time') == 'poor'
        
        # Test score metrics (higher is better)
        assert self.dashboard._rate_performance(0.9, 'score') == 'excellent'
        assert self.dashboard._rate_performance(0.7, 'score') == 'good'
        assert self.dashboard._rate_performance(0.5, 'score') == 'fair'
        assert self.dashboard._rate_performance(0.2, 'score') == 'poor'
        
        # Test percentage metrics (higher is better)
        assert self.dashboard._rate_performance(90, 'percentage') == 'excellent'
        assert self.dashboard._rate_performance(70, 'percentage') == 'good'
        assert self.dashboard._rate_performance(50, 'percentage') == 'fair'
        assert self.dashboard._rate_performance(20, 'percentage') == 'poor'
    
    def test_improvement_potential_descriptions(self):
        """Test improvement potential description function."""
        assert 'Low' in self.dashboard._describe_improvement_potential(3)
        assert 'Medium' in self.dashboard._describe_improvement_potential(10)
        assert 'High' in self.dashboard._describe_improvement_potential(20)
        assert 'Very High' in self.dashboard._describe_improvement_potential(35)
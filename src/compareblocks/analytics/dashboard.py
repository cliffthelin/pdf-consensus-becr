# src/compareblocks/analytics/dashboard.py
"""
Analytics dashboard for engine performance optimization insights.
Provides visual and textual dashboards for monitoring engine performance.
"""

import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from .engine_analytics import EnginePerformanceMetrics, EngineAnalytics
from .report_generator import AnalyticsReport, ReportGenerator
from ..consensus.policy import ConsensusDecision
from ..consensus.score import VariationScore
from ..engines.manager import EngineResult


class AnalyticsDashboard:
    """Provides dashboard views for analytics data."""
    
    def __init__(self):
        """Initialize analytics dashboard."""
        self.engine_analytics = EngineAnalytics()
        self.report_generator = ReportGenerator()
    
    def create_performance_dashboard(self, metrics: Dict[str, EnginePerformanceMetrics]) -> Dict[str, Any]:
        """
        Create a performance dashboard view.
        
        Args:
            metrics: Dictionary of engine performance metrics
            
        Returns:
            Dashboard data dictionary
        """
        if not metrics:
            return {
                'title': 'Engine Performance Dashboard',
                'timestamp': datetime.now().isoformat(),
                'status': 'no_data',
                'message': 'No performance data available'
            }
        
        # Get engine rankings
        rankings = self.engine_analytics.get_engine_rankings(metrics)
        
        # Calculate summary statistics
        all_scores = [m.avg_score for m in metrics.values()]
        all_success_rates = [m.success_rate for m in metrics.values()]
        all_selection_rates = [m.selection_rate for m in metrics.values()]
        
        dashboard = {
            'title': 'Engine Performance Dashboard',
            'timestamp': datetime.now().isoformat(),
            'status': 'active',
            'summary': {
                'total_engines': len(metrics),
                'avg_score': statistics.mean(all_scores) if all_scores else 0.0,
                'avg_success_rate': statistics.mean(all_success_rates) if all_success_rates else 0.0,
                'avg_selection_rate': statistics.mean(all_selection_rates) if all_selection_rates else 0.0,
                'best_engine': rankings[0][0] if rankings else None,
                'worst_engine': rankings[-1][0] if rankings else None
            },
            'engine_rankings': [
                {
                    'rank': i + 1,
                    'engine': engine,
                    'overall_score': score,
                    'performance_level': self._get_performance_level(score)
                }
                for i, (engine, score) in enumerate(rankings)
            ],
            'performance_matrix': self._create_performance_matrix(metrics),
            'alerts': self._generate_performance_alerts(metrics),
            'recommendations': self._generate_dashboard_recommendations(metrics)
        }
        
        return dashboard
    
    def create_quality_dashboard(self, variation_scores: List[VariationScore],
                               consensus_decisions: List[ConsensusDecision]) -> Dict[str, Any]:
        """
        Create a quality metrics dashboard view.
        
        Args:
            variation_scores: List of variation scores
            consensus_decisions: List of consensus decisions
            
        Returns:
            Quality dashboard data dictionary
        """
        dashboard = {
            'title': 'Quality Metrics Dashboard',
            'timestamp': datetime.now().isoformat(),
            'status': 'active' if variation_scores or consensus_decisions else 'no_data'
        }
        
        if not variation_scores and not consensus_decisions:
            dashboard['message'] = 'No quality data available'
            return dashboard
        
        # Analyze variation scores
        quality_metrics = {}
        if variation_scores:
            final_scores = [s.final_score for s in variation_scores]
            language_scores = [s.language_score for s in variation_scores]
            anomaly_scores = [s.anomaly_score for s in variation_scores]
            
            quality_metrics.update({
                'total_variations': len(variation_scores),
                'avg_final_score': statistics.mean(final_scores),
                'score_distribution': {
                    'excellent': sum(1 for s in final_scores if s >= 0.8),
                    'good': sum(1 for s in final_scores if 0.6 <= s < 0.8),
                    'fair': sum(1 for s in final_scores if 0.4 <= s < 0.6),
                    'poor': sum(1 for s in final_scores if s < 0.4)
                },
                'avg_language_score': statistics.mean(language_scores),
                'avg_anomaly_score': statistics.mean(anomaly_scores),
                'high_anomaly_count': sum(1 for s in anomaly_scores if s > 0.7)
            })
        
        # Analyze consensus decisions
        decision_metrics = {}
        if consensus_decisions:
            confidences = [d.confidence_score for d in consensus_decisions]
            manual_overrides = sum(1 for d in consensus_decisions if 'manual_override' in d.flags)
            
            decision_metrics.update({
                'total_decisions': len(consensus_decisions),
                'avg_confidence': statistics.mean(confidences),
                'confidence_distribution': {
                    'high': sum(1 for c in confidences if c >= 0.7),
                    'medium': sum(1 for c in confidences if 0.3 <= c < 0.7),
                    'low': sum(1 for c in confidences if c < 0.3)
                },
                'manual_override_count': manual_overrides,
                'manual_override_rate': (manual_overrides / len(consensus_decisions)) * 100.0,
                'action_distribution': self._count_decision_actions(consensus_decisions)
            })
        
        dashboard.update({
            'quality_metrics': quality_metrics,
            'decision_metrics': decision_metrics,
            'quality_alerts': self._generate_quality_alerts(quality_metrics, decision_metrics),
            'quality_trends': self._analyze_quality_trends(variation_scores, consensus_decisions)
        })
        
        return dashboard
    
    def create_optimization_dashboard(self, metrics: Dict[str, EnginePerformanceMetrics],
                                    recent_reports: List[AnalyticsReport]) -> Dict[str, Any]:
        """
        Create an optimization insights dashboard.
        
        Args:
            metrics: Dictionary of engine performance metrics
            recent_reports: List of recent analytics reports
            
        Returns:
            Optimization dashboard data dictionary
        """
        dashboard = {
            'title': 'Optimization Insights Dashboard',
            'timestamp': datetime.now().isoformat(),
            'status': 'active' if metrics else 'no_data'
        }
        
        if not metrics:
            dashboard['message'] = 'No optimization data available'
            return dashboard
        
        # Identify optimization opportunities
        optimization_opportunities = self._identify_optimization_opportunities(metrics)
        
        # Analyze trends from recent reports
        trend_analysis = self._analyze_optimization_trends(recent_reports)
        
        # Generate optimization recommendations
        optimization_recommendations = self._generate_optimization_recommendations(metrics, trend_analysis)
        
        dashboard.update({
            'optimization_opportunities': optimization_opportunities,
            'trend_analysis': trend_analysis,
            'optimization_recommendations': optimization_recommendations,
            'performance_gaps': self._identify_performance_gaps(metrics),
            'improvement_potential': self._calculate_improvement_potential(metrics)
        })
        
        return dashboard
    
    def _create_performance_matrix(self, metrics: Dict[str, EnginePerformanceMetrics]) -> List[Dict[str, Any]]:
        """Create a performance matrix for dashboard display."""
        matrix = []
        
        for engine_name, metric in metrics.items():
            matrix.append({
                'engine': engine_name,
                'success_rate': metric.success_rate,
                'avg_score': metric.avg_score,
                'selection_rate': metric.selection_rate,
                'avg_extraction_time': metric.avg_extraction_time,
                'anomaly_rate': metric.anomaly_detection_rate,
                'manual_override_rate': metric.manual_override_rate,
                'performance_indicators': {
                    'speed': self._rate_performance(metric.avg_extraction_time, 'time', reverse=True),
                    'quality': self._rate_performance(metric.avg_score, 'score'),
                    'reliability': self._rate_performance(metric.success_rate, 'percentage'),
                    'selection': self._rate_performance(metric.selection_rate, 'percentage')
                }
            })
        
        return matrix
    
    def _get_performance_level(self, score: float) -> str:
        """Get performance level description for a score."""
        if score >= 80:
            return 'excellent'
        elif score >= 60:
            return 'good'
        elif score >= 40:
            return 'fair'
        else:
            return 'poor'
    
    def _rate_performance(self, value: float, metric_type: str, reverse: bool = False) -> str:
        """Rate performance value as excellent/good/fair/poor."""
        if metric_type == 'time':
            # Lower is better for time
            if value <= 1.0:
                return 'excellent'
            elif value <= 3.0:
                return 'good'
            elif value <= 10.0:
                return 'fair'
            else:
                return 'poor'
        elif metric_type == 'score':
            # Higher is better for scores (0-1 range)
            if value >= 0.8:
                return 'excellent'
            elif value >= 0.6:
                return 'good'
            elif value >= 0.4:
                return 'fair'
            else:
                return 'poor'
        elif metric_type == 'percentage':
            # Higher is better for percentages
            if value >= 80:
                return 'excellent'
            elif value >= 60:
                return 'good'
            elif value >= 40:
                return 'fair'
            else:
                return 'poor'
        
        return 'unknown'
    
    def _generate_performance_alerts(self, metrics: Dict[str, EnginePerformanceMetrics]) -> List[Dict[str, Any]]:
        """Generate performance alerts for dashboard."""
        alerts = []
        
        for engine_name, metric in metrics.items():
            # Low success rate alert
            if metric.success_rate < 90:
                alerts.append({
                    'type': 'warning',
                    'engine': engine_name,
                    'message': f'Low success rate: {metric.success_rate:.1f}%',
                    'severity': 'high' if metric.success_rate < 70 else 'medium'
                })
            
            # High anomaly rate alert
            if metric.anomaly_detection_rate > 20:
                alerts.append({
                    'type': 'warning',
                    'engine': engine_name,
                    'message': f'High anomaly rate: {metric.anomaly_detection_rate:.1f}%',
                    'severity': 'high' if metric.anomaly_detection_rate > 40 else 'medium'
                })
            
            # High manual override rate alert
            if metric.manual_override_rate > 30:
                alerts.append({
                    'type': 'info',
                    'engine': engine_name,
                    'message': f'High manual override rate: {metric.manual_override_rate:.1f}%',
                    'severity': 'medium'
                })
            
            # Slow extraction time alert
            if metric.avg_extraction_time > 10:
                alerts.append({
                    'type': 'info',
                    'engine': engine_name,
                    'message': f'Slow extraction time: {metric.avg_extraction_time:.1f}s',
                    'severity': 'low'
                })
        
        return alerts
    
    def _generate_dashboard_recommendations(self, metrics: Dict[str, EnginePerformanceMetrics]) -> List[str]:
        """Generate recommendations for dashboard display."""
        recommendations = []
        
        if not metrics:
            return recommendations
        
        # Find best and worst performing engines
        rankings = self.engine_analytics.get_engine_rankings(metrics)
        if len(rankings) > 1:
            best_engine = rankings[0][0]
            worst_engine = rankings[-1][0]
            
            best_score = rankings[0][1]
            worst_score = rankings[-1][1]
            
            if best_score > worst_score * 1.5:
                recommendations.append(f"Consider prioritizing {best_engine} for better overall performance")
        
        # Check for engines needing attention
        for engine_name, metric in metrics.items():
            if metric.success_rate < 80:
                recommendations.append(f"Investigate {engine_name} reliability issues")
            
            if metric.anomaly_detection_rate > 25:
                recommendations.append(f"Review {engine_name} configuration to reduce anomalies")
        
        return recommendations
    
    def _generate_quality_alerts(self, quality_metrics: Dict[str, Any],
                               decision_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate quality-related alerts."""
        alerts = []
        
        if quality_metrics:
            avg_score = quality_metrics.get('avg_final_score', 0)
            if avg_score < 0.5:
                alerts.append({
                    'type': 'warning',
                    'message': f'Low average quality score: {avg_score:.2f}',
                    'severity': 'high'
                })
            
            high_anomaly_count = quality_metrics.get('high_anomaly_count', 0)
            total_variations = quality_metrics.get('total_variations', 1)
            if high_anomaly_count / total_variations > 0.2:
                alerts.append({
                    'type': 'warning',
                    'message': f'High anomaly detection rate: {(high_anomaly_count/total_variations)*100:.1f}%',
                    'severity': 'medium'
                })
        
        if decision_metrics:
            manual_override_rate = decision_metrics.get('manual_override_rate', 0)
            if manual_override_rate > 25:
                alerts.append({
                    'type': 'info',
                    'message': f'High manual override rate: {manual_override_rate:.1f}%',
                    'severity': 'medium'
                })
            
            avg_confidence = decision_metrics.get('avg_confidence', 0)
            if avg_confidence < 0.6:
                alerts.append({
                    'type': 'warning',
                    'message': f'Low average confidence: {avg_confidence:.2f}',
                    'severity': 'medium'
                })
        
        return alerts
    
    def _count_decision_actions(self, decisions: List[ConsensusDecision]) -> Dict[str, int]:
        """Count decision actions for dashboard display."""
        action_counts = defaultdict(int)
        for decision in decisions:
            action_counts[decision.action.value] += 1
        return dict(action_counts)
    
    def _analyze_quality_trends(self, variation_scores: List[VariationScore],
                              consensus_decisions: List[ConsensusDecision]) -> Dict[str, Any]:
        """Analyze quality trends for dashboard."""
        trends = {}
        
        if variation_scores:
            # Simple trend analysis - could be enhanced with time series data
            scores = [s.final_score for s in variation_scores]
            trends['score_trend'] = {
                'current_avg': statistics.mean(scores),
                'trend_direction': 'stable',  # Would need historical data for real trend
                'quality_consistency': 1.0 - (statistics.variance(scores) if len(scores) > 1 else 0.0)
            }
        
        if consensus_decisions:
            confidences = [d.confidence_score for d in consensus_decisions]
            trends['confidence_trend'] = {
                'current_avg': statistics.mean(confidences),
                'trend_direction': 'stable',  # Would need historical data for real trend
                'confidence_consistency': 1.0 - (statistics.variance(confidences) if len(confidences) > 1 else 0.0)
            }
        
        return trends
    
    def _identify_optimization_opportunities(self, metrics: Dict[str, EnginePerformanceMetrics]) -> List[Dict[str, Any]]:
        """Identify optimization opportunities from metrics."""
        opportunities = []
        
        for engine_name, metric in metrics.items():
            # Low selection rate opportunity
            if metric.selection_rate < 20 and metric.avg_score > 0.5:
                opportunities.append({
                    'type': 'underutilized_engine',
                    'engine': engine_name,
                    'description': f'{engine_name} has good quality but low selection rate',
                    'potential_impact': 'medium',
                    'recommendation': 'Review consensus thresholds or engine weighting'
                })
            
            # High anomaly rate opportunity
            if metric.anomaly_detection_rate > 15:
                opportunities.append({
                    'type': 'anomaly_reduction',
                    'engine': engine_name,
                    'description': f'{engine_name} has high anomaly detection rate',
                    'potential_impact': 'high',
                    'recommendation': 'Optimize engine parameters or preprocessing'
                })
            
            # Performance improvement opportunity
            if metric.avg_extraction_time > 5 and metric.success_rate > 90:
                opportunities.append({
                    'type': 'speed_optimization',
                    'engine': engine_name,
                    'description': f'{engine_name} is reliable but slow',
                    'potential_impact': 'medium',
                    'recommendation': 'Optimize processing parameters for speed'
                })
        
        return opportunities
    
    def _analyze_optimization_trends(self, recent_reports: List[AnalyticsReport]) -> Dict[str, Any]:
        """Analyze optimization trends from recent reports."""
        if not recent_reports:
            return {'status': 'insufficient_data'}
        
        # Simple trend analysis - would be enhanced with proper time series analysis
        return {
            'status': 'analyzed',
            'report_count': len(recent_reports),
            'date_range': {
                'earliest': min(r.timestamp for r in recent_reports),
                'latest': max(r.timestamp for r in recent_reports)
            },
            'trend_summary': 'Stable performance across recent reports'
        }
    
    def _generate_optimization_recommendations(self, metrics: Dict[str, EnginePerformanceMetrics],
                                             trend_analysis: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        if not metrics:
            return recommendations
        
        # Performance-based recommendations
        rankings = self.engine_analytics.get_engine_rankings(metrics)
        if len(rankings) > 1:
            best_engine = rankings[0][0]
            recommendations.append(f"Focus optimization efforts on {best_engine} as the top performer")
        
        # Identify engines needing optimization
        for engine_name, metric in metrics.items():
            if metric.anomaly_detection_rate > 20:
                recommendations.append(f"Optimize {engine_name} to reduce anomaly detection rate")
            
            if metric.avg_extraction_time > 10:
                recommendations.append(f"Improve {engine_name} processing speed")
        
        return recommendations
    
    def _identify_performance_gaps(self, metrics: Dict[str, EnginePerformanceMetrics]) -> List[Dict[str, Any]]:
        """Identify performance gaps between engines."""
        gaps = []
        
        if len(metrics) < 2:
            return gaps
        
        # Find performance gaps
        rankings = self.engine_analytics.get_engine_rankings(metrics)
        best_score = rankings[0][1]
        
        for engine, score in rankings[1:]:
            gap = best_score - score
            if gap > 20:  # Significant gap
                gaps.append({
                    'engine': engine,
                    'gap_score': gap,
                    'current_score': score,
                    'target_score': best_score,
                    'improvement_needed': gap
                })
        
        return gaps
    
    def _calculate_improvement_potential(self, metrics: Dict[str, EnginePerformanceMetrics]) -> Dict[str, Any]:
        """Calculate overall improvement potential."""
        if not metrics:
            return {'potential': 0, 'status': 'no_data'}
        
        # Calculate potential improvement based on gaps
        rankings = self.engine_analytics.get_engine_rankings(metrics)
        if len(rankings) < 2:
            return {'potential': 0, 'status': 'single_engine'}
        
        best_score = rankings[0][1]
        avg_score = statistics.mean([score for _, score in rankings])
        
        improvement_potential = best_score - avg_score
        
        return {
            'potential': improvement_potential,
            'status': 'calculated',
            'best_engine_score': best_score,
            'average_score': avg_score,
            'improvement_description': self._describe_improvement_potential(improvement_potential)
        }
    
    def _describe_improvement_potential(self, potential: float) -> str:
        """Describe improvement potential in human terms."""
        if potential < 5:
            return 'Low - engines are performing similarly'
        elif potential < 15:
            return 'Medium - some optimization opportunities exist'
        elif potential < 30:
            return 'High - significant optimization opportunities available'
        else:
            return 'Very High - major performance gaps need attention'


def create_performance_dashboard(metrics: Dict[str, EnginePerformanceMetrics]) -> Dict[str, Any]:
    """
    Convenience function to create a performance dashboard.
    
    Args:
        metrics: Dictionary of engine performance metrics
        
    Returns:
        Performance dashboard data
    """
    dashboard = AnalyticsDashboard()
    return dashboard.create_performance_dashboard(metrics)


def create_quality_dashboard(variation_scores: List[VariationScore],
                           consensus_decisions: List[ConsensusDecision]) -> Dict[str, Any]:
    """
    Convenience function to create a quality dashboard.
    
    Args:
        variation_scores: List of variation scores
        consensus_decisions: List of consensus decisions
        
    Returns:
        Quality dashboard data
    """
    dashboard = AnalyticsDashboard()
    return dashboard.create_quality_dashboard(variation_scores, consensus_decisions)
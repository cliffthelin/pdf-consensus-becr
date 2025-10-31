# src/compareblocks/analytics/report_generator.py
"""
Analytics report generation with summary reports and manual override tracking.
Generates comprehensive reports for downstream analysis and optimization insights.
"""

import json
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from .engine_analytics import EnginePerformanceMetrics, EngineAnalytics
from ..consensus.policy import ConsensusDecision, DecisionAction
from ..consensus.score import VariationScore
from ..engines.manager import EngineResult
from ..config.file_manager import file_manager


@dataclass
class AnalyticsReport:
    """Comprehensive analytics report."""
    report_id: str
    timestamp: str
    report_type: str
    pdf_path: str
    pdf_name: str
    summary: Dict[str, Any]
    engine_performance: Dict[str, EnginePerformanceMetrics]
    decision_analysis: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    recommendations: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        data = asdict(self)
        # Convert EnginePerformanceMetrics to dict
        data['engine_performance'] = {
            engine: metrics.to_dict() if hasattr(metrics, 'to_dict') else metrics
            for engine, metrics in self.engine_performance.items()
        }
        return data


class ReportGenerator:
    """Generates comprehensive analytics reports."""
    
    def __init__(self):
        """Initialize report generator."""
        self.engine_analytics = EngineAnalytics()
    
    def generate_comprehensive_report(self, 
                                    engine_results: Optional[Dict[str, EngineResult]] = None,
                                    consensus_decisions: Optional[List[ConsensusDecision]] = None,
                                    variation_scores: Optional[List[VariationScore]] = None,
                                    pdf_path: Optional[str] = None) -> AnalyticsReport:
        """
        Generate a comprehensive analytics report.
        
        Args:
            engine_results: Optional engine extraction results
            consensus_decisions: Optional consensus decisions
            variation_scores: Optional variation scores
            pdf_path: Optional PDF file path
            
        Returns:
            Comprehensive analytics report
        """
        # Use default PDF if none provided
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        pdf_name = Path(pdf_path).name
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Analyze engine performance
        engine_performance = {}
        if engine_results:
            engine_performance.update(self.engine_analytics.analyze_engine_results(engine_results))
        if consensus_decisions:
            engine_performance.update(self.engine_analytics.analyze_consensus_decisions(consensus_decisions))
        if variation_scores:
            engine_performance.update(self.engine_analytics.analyze_variation_scores(variation_scores))
        
        # Generate summary
        summary = self._generate_summary(engine_performance, consensus_decisions, engine_results)
        
        # Analyze decisions
        decision_analysis = self._analyze_decisions(consensus_decisions) if consensus_decisions else {}
        
        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(variation_scores, consensus_decisions)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(engine_performance, decision_analysis, quality_metrics)
        
        return AnalyticsReport(
            report_id=report_id,
            timestamp=datetime.now().isoformat(),
            report_type="comprehensive",
            pdf_path=pdf_path,
            pdf_name=pdf_name,
            summary=summary,
            engine_performance=engine_performance,
            decision_analysis=decision_analysis,
            quality_metrics=quality_metrics,
            recommendations=recommendations,
            metadata={
                'has_engine_results': engine_results is not None,
                'has_consensus_decisions': consensus_decisions is not None,
                'has_variation_scores': variation_scores is not None,
                'total_engines': len(engine_performance),
                'generation_time': datetime.now().isoformat()
            }
        )
    
    def generate_engine_performance_report(self, engine_results: Dict[str, EngineResult]) -> AnalyticsReport:
        """
        Generate a report focused on engine performance.
        
        Args:
            engine_results: Engine extraction results
            
        Returns:
            Engine performance report
        """
        pdf_path = file_manager.get_target_pdf_path()
        pdf_name = Path(pdf_path).name
        report_id = f"engine_perf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Analyze engine performance
        engine_performance = self.engine_analytics.analyze_engine_results(engine_results)
        
        # Generate performance summary
        summary = {
            'total_engines': len(engine_results),
            'successful_engines': sum(1 for r in engine_results.values() if r.success),
            'failed_engines': sum(1 for r in engine_results.values() if not r.success),
            'total_extraction_time': sum(r.extraction_time for r in engine_results.values()),
            'avg_extraction_time': statistics.mean([r.extraction_time for r in engine_results.values()]),
            'fastest_engine': min(engine_results.items(), key=lambda x: x[1].extraction_time)[0],
            'slowest_engine': max(engine_results.items(), key=lambda x: x[1].extraction_time)[0],
            'engine_rankings': self.engine_analytics.get_engine_rankings(engine_performance)
        }
        
        # Performance recommendations
        recommendations = []
        if summary['failed_engines'] > 0:
            recommendations.append("Some engines failed - check engine availability and configuration")
        
        fastest_time = min(r.extraction_time for r in engine_results.values())
        slowest_time = max(r.extraction_time for r in engine_results.values())
        if slowest_time > fastest_time * 3:
            recommendations.append("Significant performance variation between engines - consider optimization")
        
        return AnalyticsReport(
            report_id=report_id,
            timestamp=datetime.now().isoformat(),
            report_type="engine_performance",
            pdf_path=pdf_path,
            pdf_name=pdf_name,
            summary=summary,
            engine_performance=engine_performance,
            decision_analysis={},
            quality_metrics={},
            recommendations=recommendations,
            metadata={
                'focus': 'engine_performance',
                'total_engines_tested': len(engine_results)
            }
        )
    
    def generate_decision_analysis_report(self, consensus_decisions: List[ConsensusDecision]) -> AnalyticsReport:
        """
        Generate a report focused on consensus decision analysis.
        
        Args:
            consensus_decisions: List of consensus decisions
            
        Returns:
            Decision analysis report
        """
        pdf_path = file_manager.get_target_pdf_path()
        pdf_name = Path(pdf_path).name
        report_id = f"decision_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Analyze decisions
        decision_analysis = self._analyze_decisions(consensus_decisions)
        
        # Generate engine performance from decisions
        engine_performance = self.engine_analytics.analyze_consensus_decisions(consensus_decisions)
        
        # Generate summary
        summary = {
            'total_decisions': len(consensus_decisions),
            'auto_selections': decision_analysis.get('action_counts', {}).get('pick', 0),
            'manual_reviews': decision_analysis.get('action_counts', {}).get('review', 0),
            'merges': decision_analysis.get('action_counts', {}).get('merge', 0),
            'rejections': decision_analysis.get('action_counts', {}).get('reject', 0),
            'manual_override_rate': decision_analysis.get('manual_override_rate', 0.0),
            'avg_confidence': decision_analysis.get('avg_confidence', 0.0),
            'most_selected_engine': decision_analysis.get('most_selected_engine', 'unknown')
        }
        
        # Decision recommendations
        recommendations = []
        if summary['manual_override_rate'] > 30:
            recommendations.append("High manual override rate - consider adjusting consensus thresholds")
        if summary['avg_confidence'] < 0.6:
            recommendations.append("Low average confidence - review engine quality and scoring parameters")
        if summary['rejections'] > summary['total_decisions'] * 0.1:
            recommendations.append("High rejection rate - check for data quality issues")
        
        return AnalyticsReport(
            report_id=report_id,
            timestamp=datetime.now().isoformat(),
            report_type="decision_analysis",
            pdf_path=pdf_path,
            pdf_name=pdf_name,
            summary=summary,
            engine_performance=engine_performance,
            decision_analysis=decision_analysis,
            quality_metrics={},
            recommendations=recommendations,
            metadata={
                'focus': 'decision_analysis',
                'total_decisions_analyzed': len(consensus_decisions)
            }
        )
    
    def _generate_summary(self, engine_performance: Dict[str, EnginePerformanceMetrics],
                         consensus_decisions: Optional[List[ConsensusDecision]],
                         engine_results: Optional[Dict[str, EngineResult]]) -> Dict[str, Any]:
        """Generate overall summary statistics."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_engines': len(engine_performance),
            'engine_rankings': self.engine_analytics.get_engine_rankings(engine_performance)
        }
        
        if engine_results:
            summary.update({
                'total_extraction_time': sum(r.extraction_time for r in engine_results.values()),
                'successful_extractions': sum(1 for r in engine_results.values() if r.success),
                'failed_extractions': sum(1 for r in engine_results.values() if not r.success)
            })
        
        if consensus_decisions:
            summary.update({
                'total_decisions': len(consensus_decisions),
                'manual_override_rate': self._calculate_manual_override_rate(consensus_decisions),
                'avg_confidence': statistics.mean([d.confidence_score for d in consensus_decisions])
            })
        
        return summary
    
    def _analyze_decisions(self, decisions: List[ConsensusDecision]) -> Dict[str, Any]:
        """Analyze consensus decisions for patterns and statistics."""
        if not decisions:
            return {}
        
        # Count actions
        action_counts = Counter(d.action.value for d in decisions)
        
        # Count manual overrides
        manual_overrides = sum(1 for d in decisions if 'manual_override' in d.flags)
        manual_override_rate = (manual_overrides / len(decisions)) * 100.0
        
        # Calculate confidence statistics
        confidences = [d.confidence_score for d in decisions]
        avg_confidence = statistics.mean(confidences)
        confidence_variance = statistics.variance(confidences) if len(confidences) > 1 else 0.0
        
        # Count engine selections
        engine_selections = Counter(d.selected_engine for d in decisions if d.selected_engine)
        most_selected_engine = engine_selections.most_common(1)[0][0] if engine_selections else None
        
        # Analyze anomaly scores
        anomaly_scores = [d.anomaly_score for d in decisions]
        avg_anomaly_score = statistics.mean(anomaly_scores)
        high_anomaly_count = sum(1 for score in anomaly_scores if score > 0.7)
        
        # Analyze flags
        all_flags = []
        for d in decisions:
            all_flags.extend(d.flags)
        common_flags = dict(Counter(all_flags).most_common(10))
        
        return {
            'action_counts': dict(action_counts),
            'manual_override_count': manual_overrides,
            'manual_override_rate': manual_override_rate,
            'avg_confidence': avg_confidence,
            'confidence_variance': confidence_variance,
            'confidence_distribution': {
                'high_confidence': sum(1 for c in confidences if c >= 0.7),
                'medium_confidence': sum(1 for c in confidences if 0.3 <= c < 0.7),
                'low_confidence': sum(1 for c in confidences if c < 0.3)
            },
            'engine_selections': dict(engine_selections),
            'most_selected_engine': most_selected_engine,
            'avg_anomaly_score': avg_anomaly_score,
            'high_anomaly_count': high_anomaly_count,
            'high_anomaly_rate': (high_anomaly_count / len(decisions)) * 100.0,
            'common_flags': common_flags
        }
    
    def _calculate_quality_metrics(self, variation_scores: Optional[List[VariationScore]],
                                 consensus_decisions: Optional[List[ConsensusDecision]]) -> Dict[str, Any]:
        """Calculate overall quality metrics."""
        metrics = {}
        
        if variation_scores:
            final_scores = [s.final_score for s in variation_scores]
            length_scores = [s.length_score for s in variation_scores]
            language_scores = [s.language_score for s in variation_scores]
            anomaly_scores = [s.anomaly_score for s in variation_scores]
            
            metrics.update({
                'avg_final_score': statistics.mean(final_scores),
                'avg_length_score': statistics.mean(length_scores),
                'avg_language_score': statistics.mean(language_scores),
                'avg_anomaly_score': statistics.mean(anomaly_scores),
                'score_variance': statistics.variance(final_scores) if len(final_scores) > 1 else 0.0,
                'high_quality_variations': sum(1 for s in final_scores if s >= 0.7),
                'low_quality_variations': sum(1 for s in final_scores if s < 0.3),
                'total_variations': len(variation_scores)
            })
        
        if consensus_decisions:
            confidence_scores = [d.confidence_score for d in consensus_decisions]
            anomaly_scores = [d.anomaly_score for d in consensus_decisions]
            
            metrics.update({
                'avg_decision_confidence': statistics.mean(confidence_scores),
                'avg_decision_anomaly': statistics.mean(anomaly_scores),
                'high_confidence_decisions': sum(1 for c in confidence_scores if c >= 0.7),
                'low_confidence_decisions': sum(1 for c in confidence_scores if c < 0.3)
            })
        
        return metrics
    
    def _generate_recommendations(self, engine_performance: Dict[str, EnginePerformanceMetrics],
                                decision_analysis: Dict[str, Any],
                                quality_metrics: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []
        
        # Engine performance recommendations
        if engine_performance:
            rankings = self.engine_analytics.get_engine_rankings(engine_performance)
            if len(rankings) > 1:
                best_engine = rankings[0][0]
                worst_engine = rankings[-1][0]
                
                best_score = rankings[0][1]
                worst_score = rankings[-1][1]
                
                if best_score > worst_score * 1.5:
                    recommendations.append(f"Consider prioritizing {best_engine} engine for better performance")
                
                # Check for engines with high anomaly rates
                for engine, metrics in engine_performance.items():
                    if metrics.anomaly_detection_rate > 20:
                        recommendations.append(f"Engine {engine} has high anomaly rate ({metrics.anomaly_detection_rate:.1f}%) - review configuration")
                    
                    if metrics.success_rate < 90:
                        recommendations.append(f"Engine {engine} has low success rate ({metrics.success_rate:.1f}%) - check availability")
        
        # Decision analysis recommendations
        if decision_analysis:
            manual_override_rate = decision_analysis.get('manual_override_rate', 0)
            if manual_override_rate > 25:
                recommendations.append(f"High manual override rate ({manual_override_rate:.1f}%) - consider adjusting consensus thresholds")
            
            avg_confidence = decision_analysis.get('avg_confidence', 0)
            if avg_confidence < 0.6:
                recommendations.append(f"Low average confidence ({avg_confidence:.2f}) - review scoring parameters")
            
            high_anomaly_rate = decision_analysis.get('high_anomaly_rate', 0)
            if high_anomaly_rate > 15:
                recommendations.append(f"High anomaly detection rate ({high_anomaly_rate:.1f}%) - check input data quality")
        
        # Quality metrics recommendations
        if quality_metrics:
            avg_final_score = quality_metrics.get('avg_final_score', 0)
            if avg_final_score < 0.5:
                recommendations.append(f"Low average quality score ({avg_final_score:.2f}) - consider engine optimization")
            
            low_quality_count = quality_metrics.get('low_quality_variations', 0)
            total_variations = quality_metrics.get('total_variations', 1)
            if low_quality_count / total_variations > 0.3:
                recommendations.append("High proportion of low-quality variations - review extraction parameters")
        
        # General recommendations
        if not recommendations:
            recommendations.append("System performance appears optimal - continue monitoring")
        
        return recommendations
    
    def _calculate_manual_override_rate(self, decisions: List[ConsensusDecision]) -> float:
        """Calculate the manual override rate from decisions."""
        if not decisions:
            return 0.0
        
        manual_overrides = sum(1 for d in decisions if 'manual_override' in d.flags)
        return (manual_overrides / len(decisions)) * 100.0
    
    def save_report(self, report: AnalyticsReport, output_path: Optional[Path] = None) -> Path:
        """
        Save analytics report to file.
        
        Args:
            report: Analytics report to save
            output_path: Optional output file path
            
        Returns:
            Path to saved report file
        """
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            filename = f"{report.report_type}_{report.report_id}.json"
            output_path = output_dir / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save report
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def load_report(self, file_path: Path) -> AnalyticsReport:
        """
        Load analytics report from file.
        
        Args:
            file_path: Path to report file
            
        Returns:
            Analytics report
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert engine performance back to objects
        engine_performance = {}
        for engine, metrics_data in data.get('engine_performance', {}).items():
            engine_performance[engine] = EnginePerformanceMetrics(**metrics_data)
        
        data['engine_performance'] = engine_performance
        
        return AnalyticsReport(**data)
    
    def generate_comparison_report(self, reports: List[AnalyticsReport]) -> Dict[str, Any]:
        """
        Generate a comparison report from multiple analytics reports.
        
        Args:
            reports: List of analytics reports to compare
            
        Returns:
            Comparison report dictionary
        """
        if not reports:
            return {'error': 'No reports provided for comparison'}
        
        comparison = {
            'comparison_id': f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'total_reports': len(reports),
            'report_ids': [r.report_id for r in reports],
            'date_range': {
                'earliest': min(r.timestamp for r in reports),
                'latest': max(r.timestamp for r in reports)
            },
            'engine_performance_trends': {},
            'quality_trends': {},
            'recommendations': []
        }
        
        # Analyze engine performance trends
        all_engines = set()
        for report in reports:
            all_engines.update(report.engine_performance.keys())
        
        for engine in all_engines:
            engine_data = []
            for report in reports:
                if engine in report.engine_performance:
                    metrics = report.engine_performance[engine]
                    engine_data.append({
                        'timestamp': report.timestamp,
                        'avg_score': metrics.avg_score,
                        'success_rate': metrics.success_rate,
                        'selection_rate': metrics.selection_rate,
                        'anomaly_rate': metrics.anomaly_detection_rate
                    })
            
            if engine_data:
                comparison['engine_performance_trends'][engine] = engine_data
        
        # Analyze quality trends
        quality_data = []
        for report in reports:
            if report.quality_metrics:
                quality_data.append({
                    'timestamp': report.timestamp,
                    'avg_final_score': report.quality_metrics.get('avg_final_score', 0),
                    'avg_confidence': report.summary.get('avg_confidence', 0),
                    'manual_override_rate': report.summary.get('manual_override_rate', 0)
                })
        
        comparison['quality_trends'] = quality_data
        
        # Generate trend-based recommendations
        if len(reports) > 1:
            # Check for declining performance
            recent_report = max(reports, key=lambda r: r.timestamp)
            oldest_report = min(reports, key=lambda r: r.timestamp)
            
            recent_confidence = recent_report.summary.get('avg_confidence', 0)
            oldest_confidence = oldest_report.summary.get('avg_confidence', 0)
            
            if recent_confidence < oldest_confidence:
                comparison['recommendations'].append("Confidence scores are declining over time - investigate causes")
            
            recent_override_rate = recent_report.summary.get('manual_override_rate', 0)
            oldest_override_rate = oldest_report.summary.get('manual_override_rate', 0)
            
            if recent_override_rate > oldest_override_rate * 1.2:
                comparison['recommendations'].append("Manual override rate is increasing - review system performance")
            
            # Always provide at least one recommendation for comparison reports
            if not comparison['recommendations']:
                if len(reports) >= 3:
                    comparison['recommendations'].append("Performance appears stable across multiple reports - continue monitoring")
                else:
                    comparison['recommendations'].append("Collect more data points for meaningful trend analysis")
        
        return comparison


def generate_analytics_report(engine_results: Optional[Dict[str, EngineResult]] = None,
                            consensus_decisions: Optional[List[ConsensusDecision]] = None,
                            variation_scores: Optional[List[VariationScore]] = None,
                            pdf_path: Optional[str] = None) -> AnalyticsReport:
    """
    Convenience function to generate a comprehensive analytics report.
    
    Args:
        engine_results: Optional engine extraction results
        consensus_decisions: Optional consensus decisions
        variation_scores: Optional variation scores
        pdf_path: Optional PDF file path
        
    Returns:
        Comprehensive analytics report
    """
    generator = ReportGenerator()
    return generator.generate_comprehensive_report(
        engine_results=engine_results,
        consensus_decisions=consensus_decisions,
        variation_scores=variation_scores,
        pdf_path=pdf_path
    )


def save_analytics_report(report: AnalyticsReport, output_path: Optional[Path] = None) -> Path:
    """
    Convenience function to save an analytics report.
    
    Args:
        report: Analytics report to save
        output_path: Optional output file path
        
    Returns:
        Path to saved report file
    """
    generator = ReportGenerator()
    return generator.save_report(report, output_path)
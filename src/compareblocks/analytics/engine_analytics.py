# src/compareblocks/analytics/engine_analytics.py
"""
Per-engine performance analytics and accuracy metrics.
Tracks engine performance, accuracy, and usage patterns.
"""

import json
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from ..consensus.score import VariationScore, ConsensusScorer
from ..consensus.policy import ConsensusDecision, DecisionAction
from ..engines.manager import EngineResult
from ..config.file_manager import file_manager


@dataclass
class EnginePerformanceMetrics:
    """Performance metrics for a single engine."""
    engine_name: str
    total_extractions: int
    successful_extractions: int
    failed_extractions: int
    success_rate: float
    avg_extraction_time: float
    min_extraction_time: float
    max_extraction_time: float
    total_extraction_time: float
    avg_score: float
    min_score: float
    max_score: float
    score_variance: float
    selections_count: int  # How many times this engine was selected as best
    selection_rate: float  # Percentage of times selected when available
    manual_override_count: int  # Times manually overridden
    manual_override_rate: float
    anomaly_detection_count: int  # Times flagged for anomalies
    anomaly_detection_rate: float
    common_flags: Dict[str, int]  # Most common quality flags
    accuracy_metrics: Dict[str, float]  # Additional accuracy metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)


class EngineAnalytics:
    """Analyzes engine performance and generates metrics."""
    
    def __init__(self):
        """Initialize engine analytics."""
        self.scorer = ConsensusScorer()
        self.performance_cache = {}
        self.last_cache_update = None
        self.cache_duration = timedelta(minutes=5)  # Cache for 5 minutes
    
    def analyze_engine_results(self, engine_results: Dict[str, EngineResult]) -> Dict[str, EnginePerformanceMetrics]:
        """
        Analyze engine extraction results and generate performance metrics.
        
        Args:
            engine_results: Dictionary of engine results from extraction
            
        Returns:
            Dictionary of engine performance metrics
        """
        metrics = {}
        
        for engine_name, result in engine_results.items():
            # Basic performance metrics
            total_extractions = 1
            successful_extractions = 1 if result.success else 0
            failed_extractions = 1 if not result.success else 0
            success_rate = (successful_extractions / total_extractions) * 100.0
            
            # Timing metrics
            extraction_time = result.extraction_time
            
            # Initialize metrics with basic data
            metrics[engine_name] = EnginePerformanceMetrics(
                engine_name=engine_name,
                total_extractions=total_extractions,
                successful_extractions=successful_extractions,
                failed_extractions=failed_extractions,
                success_rate=success_rate,
                avg_extraction_time=extraction_time,
                min_extraction_time=extraction_time,
                max_extraction_time=extraction_time,
                total_extraction_time=extraction_time,
                avg_score=0.0,  # Will be updated with scoring data
                min_score=0.0,
                max_score=0.0,
                score_variance=0.0,
                selections_count=0,
                selection_rate=0.0,
                manual_override_count=0,
                manual_override_rate=0.0,
                anomaly_detection_count=0,
                anomaly_detection_rate=0.0,
                common_flags={},
                accuracy_metrics={}
            )
            
            # Add metadata-based metrics if available
            if result.metadata:
                metrics[engine_name].accuracy_metrics.update(result.metadata)
        
        return metrics
    
    def analyze_consensus_decisions(self, decisions: List[ConsensusDecision]) -> Dict[str, EnginePerformanceMetrics]:
        """
        Analyze consensus decisions to generate engine performance metrics.
        
        Args:
            decisions: List of consensus decisions
            
        Returns:
            Dictionary of engine performance metrics
        """
        if not decisions:
            return {}
        
        # Collect data by engine
        engine_data = defaultdict(lambda: {
            'scores': [],
            'selections': 0,
            'manual_overrides': 0,
            'anomaly_flags': 0,
            'flags': [],
            'total_appearances': 0
        })
        
        # Process each decision
        for decision in decisions:
            # Count engine appearances and selections
            for engine, score in decision.engine_scores.items():
                engine_data[engine]['scores'].append(score)
                engine_data[engine]['total_appearances'] += 1
                
                # Check if this engine was selected
                if decision.selected_engine == engine:
                    engine_data[engine]['selections'] += 1
                
                # Check for manual overrides
                if 'manual_override' in decision.flags:
                    engine_data[engine]['manual_overrides'] += 1
                
                # Check for anomaly flags
                if decision.anomaly_score > 0.7:  # High anomaly threshold
                    engine_data[engine]['anomaly_flags'] += 1
            
            # Collect flags from merge candidates
            for candidate in decision.merge_candidates:
                if hasattr(candidate, 'engine_name') and hasattr(candidate, 'flags'):
                    engine_data[candidate.engine_name]['flags'].extend(candidate.flags)
        
        # Generate metrics for each engine
        metrics = {}
        for engine_name, data in engine_data.items():
            scores = data['scores']
            total_appearances = data['total_appearances']
            
            if not scores or total_appearances == 0:
                continue
            
            # Calculate score statistics
            avg_score = statistics.mean(scores)
            min_score = min(scores)
            max_score = max(scores)
            score_variance = statistics.variance(scores) if len(scores) > 1 else 0.0
            
            # Calculate rates
            selection_rate = (data['selections'] / total_appearances) * 100.0
            manual_override_rate = (data['manual_overrides'] / total_appearances) * 100.0
            anomaly_detection_rate = (data['anomaly_flags'] / total_appearances) * 100.0
            
            # Count common flags
            flag_counts = Counter(data['flags'])
            common_flags = dict(flag_counts.most_common(5))
            
            metrics[engine_name] = EnginePerformanceMetrics(
                engine_name=engine_name,
                total_extractions=total_appearances,
                successful_extractions=total_appearances,  # Assume all successful if in decisions
                failed_extractions=0,
                success_rate=100.0,
                avg_extraction_time=0.0,  # Not available from decisions
                min_extraction_time=0.0,
                max_extraction_time=0.0,
                total_extraction_time=0.0,
                avg_score=avg_score,
                min_score=min_score,
                max_score=max_score,
                score_variance=score_variance,
                selections_count=data['selections'],
                selection_rate=selection_rate,
                manual_override_count=data['manual_overrides'],
                manual_override_rate=manual_override_rate,
                anomaly_detection_count=data['anomaly_flags'],
                anomaly_detection_rate=anomaly_detection_rate,
                common_flags=common_flags,
                accuracy_metrics={
                    'total_decisions': len(decisions),
                    'engine_appearances': total_appearances
                }
            )
        
        return metrics
    
    def analyze_variation_scores(self, variation_scores: List[VariationScore]) -> Dict[str, EnginePerformanceMetrics]:
        """
        Analyze variation scores to generate engine performance metrics.
        
        Args:
            variation_scores: List of variation scores
            
        Returns:
            Dictionary of engine performance metrics
        """
        if not variation_scores:
            return {}
        
        # Group scores by engine
        engine_scores = defaultdict(list)
        engine_flags = defaultdict(list)
        
        for score in variation_scores:
            engine_scores[score.engine_name].append(score)
            engine_flags[score.engine_name].extend(score.flags)
        
        # Generate metrics for each engine
        metrics = {}
        for engine_name, scores in engine_scores.items():
            final_scores = [s.final_score for s in scores]
            
            # Calculate score statistics
            avg_score = statistics.mean(final_scores)
            min_score = min(final_scores)
            max_score = max(final_scores)
            score_variance = statistics.variance(final_scores) if len(final_scores) > 1 else 0.0
            
            # Count flags
            flag_counts = Counter(engine_flags[engine_name])
            common_flags = dict(flag_counts.most_common(5))
            
            # Count anomalies
            anomaly_count = sum(1 for s in scores if 'high_anomaly_score' in s.flags)
            anomaly_rate = (anomaly_count / len(scores)) * 100.0
            
            metrics[engine_name] = EnginePerformanceMetrics(
                engine_name=engine_name,
                total_extractions=len(scores),
                successful_extractions=len(scores),
                failed_extractions=0,
                success_rate=100.0,
                avg_extraction_time=0.0,
                min_extraction_time=0.0,
                max_extraction_time=0.0,
                total_extraction_time=0.0,
                avg_score=avg_score,
                min_score=min_score,
                max_score=max_score,
                score_variance=score_variance,
                selections_count=0,  # Not available from scores alone
                selection_rate=0.0,
                manual_override_count=0,
                manual_override_rate=0.0,
                anomaly_detection_count=anomaly_count,
                anomaly_detection_rate=anomaly_rate,
                common_flags=common_flags,
                accuracy_metrics={
                    'total_variations': len(scores),
                    'avg_length_score': statistics.mean([s.length_score for s in scores]),
                    'avg_language_score': statistics.mean([s.language_score for s in scores]),
                    'avg_context_score': statistics.mean([s.context_score for s in scores])
                }
            )
        
        return metrics
    
    def combine_metrics(self, *metric_dicts: Dict[str, EnginePerformanceMetrics]) -> Dict[str, EnginePerformanceMetrics]:
        """
        Combine multiple engine performance metrics dictionaries.
        
        Args:
            metric_dicts: Variable number of metrics dictionaries to combine
            
        Returns:
            Combined metrics dictionary
        """
        combined = {}
        all_engines = set()
        
        # Collect all engine names
        for metrics_dict in metric_dicts:
            all_engines.update(metrics_dict.keys())
        
        # Combine metrics for each engine
        for engine_name in all_engines:
            engine_metrics = [metrics_dict.get(engine_name) for metrics_dict in metric_dicts if engine_name in metrics_dict]
            
            if not engine_metrics:
                continue
            
            # Combine the metrics
            combined[engine_name] = self._combine_engine_metrics(engine_metrics)
        
        return combined
    
    def _combine_engine_metrics(self, metrics_list: List[EnginePerformanceMetrics]) -> EnginePerformanceMetrics:
        """
        Combine multiple metrics for the same engine.
        
        Args:
            metrics_list: List of metrics for the same engine
            
        Returns:
            Combined engine metrics
        """
        if not metrics_list:
            raise ValueError("Cannot combine empty metrics list")
        
        if len(metrics_list) == 1:
            return metrics_list[0]
        
        # Use first metrics as base
        base = metrics_list[0]
        
        # Combine numerical values
        total_extractions = sum(m.total_extractions for m in metrics_list)
        successful_extractions = sum(m.successful_extractions for m in metrics_list)
        failed_extractions = sum(m.failed_extractions for m in metrics_list)
        total_extraction_time = sum(m.total_extraction_time for m in metrics_list)
        selections_count = sum(m.selections_count for m in metrics_list)
        manual_override_count = sum(m.manual_override_count for m in metrics_list)
        anomaly_detection_count = sum(m.anomaly_detection_count for m in metrics_list)
        
        # Calculate averages and rates
        success_rate = (successful_extractions / total_extractions * 100.0) if total_extractions > 0 else 0.0
        avg_extraction_time = (total_extraction_time / successful_extractions) if successful_extractions > 0 else 0.0
        selection_rate = (selections_count / total_extractions * 100.0) if total_extractions > 0 else 0.0
        manual_override_rate = (manual_override_count / total_extractions * 100.0) if total_extractions > 0 else 0.0
        anomaly_detection_rate = (anomaly_detection_count / total_extractions * 100.0) if total_extractions > 0 else 0.0
        
        # Combine scores (weighted average by number of extractions)
        weighted_scores = []
        for m in metrics_list:
            if m.total_extractions > 0:
                weighted_scores.extend([m.avg_score] * m.total_extractions)
        
        avg_score = statistics.mean(weighted_scores) if weighted_scores else 0.0
        min_score = min(m.min_score for m in metrics_list if m.total_extractions > 0)
        max_score = max(m.max_score for m in metrics_list if m.total_extractions > 0)
        score_variance = statistics.variance(weighted_scores) if len(weighted_scores) > 1 else 0.0
        
        # Combine flags
        combined_flags = Counter()
        for m in metrics_list:
            for flag, count in m.common_flags.items():
                combined_flags[flag] += count
        common_flags = dict(combined_flags.most_common(5))
        
        # Combine accuracy metrics
        combined_accuracy = {}
        for m in metrics_list:
            for key, value in m.accuracy_metrics.items():
                if key not in combined_accuracy:
                    combined_accuracy[key] = []
                combined_accuracy[key].append(value)
        
        # Average the accuracy metrics
        accuracy_metrics = {}
        for key, values in combined_accuracy.items():
            if all(isinstance(v, (int, float)) for v in values):
                accuracy_metrics[key] = statistics.mean(values)
            else:
                accuracy_metrics[key] = values[-1]  # Use most recent value
        
        return EnginePerformanceMetrics(
            engine_name=base.engine_name,
            total_extractions=total_extractions,
            successful_extractions=successful_extractions,
            failed_extractions=failed_extractions,
            success_rate=success_rate,
            avg_extraction_time=avg_extraction_time,
            min_extraction_time=min(m.min_extraction_time for m in metrics_list if m.total_extractions > 0),
            max_extraction_time=max(m.max_extraction_time for m in metrics_list if m.total_extractions > 0),
            total_extraction_time=total_extraction_time,
            avg_score=avg_score,
            min_score=min_score,
            max_score=max_score,
            score_variance=score_variance,
            selections_count=selections_count,
            selection_rate=selection_rate,
            manual_override_count=manual_override_count,
            manual_override_rate=manual_override_rate,
            anomaly_detection_count=anomaly_detection_count,
            anomaly_detection_rate=anomaly_detection_rate,
            common_flags=common_flags,
            accuracy_metrics=accuracy_metrics
        )
    
    def get_engine_rankings(self, metrics: Dict[str, EnginePerformanceMetrics]) -> List[Tuple[str, float]]:
        """
        Rank engines by overall performance score.
        
        Args:
            metrics: Dictionary of engine performance metrics
            
        Returns:
            List of (engine_name, overall_score) tuples, sorted by score descending
        """
        rankings = []
        
        for engine_name, metric in metrics.items():
            # Calculate overall performance score
            # Weighted combination of success rate, average score, and selection rate
            overall_score = (
                metric.success_rate * 0.3 +  # 30% weight on success rate
                metric.avg_score * 100 * 0.4 +  # 40% weight on average quality score
                metric.selection_rate * 0.2 +  # 20% weight on selection rate
                (100 - metric.anomaly_detection_rate) * 0.1  # 10% weight on low anomaly rate
            )
            
            rankings.append((engine_name, overall_score))
        
        # Sort by score descending
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings
    
    def get_performance_summary(self, metrics: Dict[str, EnginePerformanceMetrics]) -> Dict[str, Any]:
        """
        Generate a performance summary across all engines.
        
        Args:
            metrics: Dictionary of engine performance metrics
            
        Returns:
            Performance summary dictionary
        """
        if not metrics:
            return {
                'total_engines': 0,
                'total_extractions': 0,
                'overall_success_rate': 0.0,
                'avg_extraction_time': 0.0,
                'best_engine': None,
                'engine_rankings': []
            }
        
        # Calculate totals
        total_engines = len(metrics)
        total_extractions = sum(m.total_extractions for m in metrics.values())
        total_successful = sum(m.successful_extractions for m in metrics.values())
        total_time = sum(m.total_extraction_time for m in metrics.values())
        
        # Calculate averages
        overall_success_rate = (total_successful / total_extractions * 100.0) if total_extractions > 0 else 0.0
        avg_extraction_time = (total_time / total_successful) if total_successful > 0 else 0.0
        
        # Get rankings
        rankings = self.get_engine_rankings(metrics)
        best_engine = rankings[0][0] if rankings else None
        
        return {
            'total_engines': total_engines,
            'total_extractions': total_extractions,
            'successful_extractions': total_successful,
            'overall_success_rate': overall_success_rate,
            'avg_extraction_time': avg_extraction_time,
            'best_engine': best_engine,
            'engine_rankings': rankings,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_metrics(self, metrics: Dict[str, EnginePerformanceMetrics], output_path: Optional[Path] = None) -> Path:
        """
        Save engine performance metrics to file.
        
        Args:
            metrics: Dictionary of engine performance metrics
            output_path: Optional output file path
            
        Returns:
            Path to saved metrics file
        """
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            output_path = output_dir / f"engine_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert metrics to serializable format
        serializable_metrics = {
            engine_name: metric.to_dict()
            for engine_name, metric in metrics.items()
        }
        
        # Add summary information
        data = {
            'timestamp': datetime.now().isoformat(),
            'summary': self.get_performance_summary(metrics),
            'engine_metrics': serializable_metrics
        }
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def load_metrics(self, file_path: Path) -> Dict[str, EnginePerformanceMetrics]:
        """
        Load engine performance metrics from file.
        
        Args:
            file_path: Path to metrics file
            
        Returns:
            Dictionary of engine performance metrics
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert back to EnginePerformanceMetrics objects
        metrics = {}
        for engine_name, metric_data in data.get('engine_metrics', {}).items():
            metrics[engine_name] = EnginePerformanceMetrics(**metric_data)
        
        return metrics


def analyze_engine_performance(engine_results: Dict[str, EngineResult] = None,
                             consensus_decisions: List[ConsensusDecision] = None,
                             variation_scores: List[VariationScore] = None) -> Dict[str, EnginePerformanceMetrics]:
    """
    Convenience function to analyze engine performance from various data sources.
    
    Args:
        engine_results: Optional engine extraction results
        consensus_decisions: Optional consensus decisions
        variation_scores: Optional variation scores
        
    Returns:
        Combined engine performance metrics
    """
    analytics = EngineAnalytics()
    metrics_list = []
    
    if engine_results:
        metrics_list.append(analytics.analyze_engine_results(engine_results))
    
    if consensus_decisions:
        metrics_list.append(analytics.analyze_consensus_decisions(consensus_decisions))
    
    if variation_scores:
        metrics_list.append(analytics.analyze_variation_scores(variation_scores))
    
    if not metrics_list:
        return {}
    
    return analytics.combine_metrics(*metrics_list)


def get_engine_rankings(metrics: Dict[str, EnginePerformanceMetrics]) -> List[Tuple[str, float]]:
    """
    Convenience function to get engine rankings.
    
    Args:
        metrics: Dictionary of engine performance metrics
        
    Returns:
        List of (engine_name, overall_score) tuples, sorted by score descending
    """
    analytics = EngineAnalytics()
    return analytics.get_engine_rankings(metrics)
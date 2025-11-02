# src/compareblocks/tracking/source_ranker.py
"""
Source ranking system based on accuracy metrics.
Provides quick ranking of sources, engines, and configurations for final output accuracy.
"""

import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter

from .change_tracker import ChangeHistory, ChangeType, SourceAttribution


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for a source."""
    source_identifier: str  # engine_name or engine_name:config_hash
    total_selections: int = 0
    consensus_selections: int = 0
    manual_overrides_from: int = 0  # Times overridden by user
    manual_overrides_to: int = 0  # Times selected by user override
    recalculation_stability: float = 0.0  # How often text stays same after recalc
    avg_consensus_score: float = 0.0
    selection_rate: float = 0.0  # Percentage of times selected when available
    override_resistance: float = 0.0  # 1 - (overrides_from / total_selections)
    final_output_contribution: int = 0  # Times in final output
    accuracy_score: float = 0.0  # Overall accuracy score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccuracyMetrics':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SourceRanking:
    """Ranking information for sources."""
    rankings: List[Tuple[str, AccuracyMetrics]] = field(default_factory=list)
    total_blocks: int = 0
    ranking_timestamp: Optional[str] = None
    ranking_criteria: Dict[str, float] = field(default_factory=dict)
    
    def get_top_sources(self, n: int = 5) -> List[Tuple[str, AccuracyMetrics]]:
        """Get top N sources by accuracy score."""
        return self.rankings[:n]
    
    def get_source_rank(self, source_identifier: str) -> Optional[int]:
        """Get the rank of a specific source (1-indexed)."""
        for i, (src_id, _) in enumerate(self.rankings, 1):
            if src_id == source_identifier:
                return i
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'rankings': [
                {'source': src_id, 'metrics': metrics.to_dict()}
                for src_id, metrics in self.rankings
            ],
            'total_blocks': self.total_blocks,
            'ranking_timestamp': self.ranking_timestamp,
            'ranking_criteria': self.ranking_criteria
        }


class SourceRanker:
    """Ranks sources based on accuracy and performance metrics."""
    
    def __init__(self, 
                 consensus_weight: float = 0.3,
                 override_resistance_weight: float = 0.25,
                 final_output_weight: float = 0.35,
                 score_weight: float = 0.1):
        """
        Initialize the source ranker.
        
        Args:
            consensus_weight: Weight for consensus selection rate
            override_resistance_weight: Weight for override resistance
            final_output_weight: Weight for final output contribution
            score_weight: Weight for average consensus score
        """
        self.consensus_weight = consensus_weight
        self.override_resistance_weight = override_resistance_weight
        self.final_output_weight = final_output_weight
        self.score_weight = score_weight
        
        # Normalize weights
        total = (consensus_weight + override_resistance_weight + 
                final_output_weight + score_weight)
        if total > 0:
            self.consensus_weight /= total
            self.override_resistance_weight /= total
            self.final_output_weight /= total
            self.score_weight /= total
    
    def calculate_accuracy_metrics(self, histories: Dict[str, ChangeHistory],
                                  include_config: bool = False) -> Dict[str, AccuracyMetrics]:
        """
        Calculate accuracy metrics for all sources from change histories.
        
        Args:
            histories: Dictionary of block change histories
            include_config: Whether to include configuration hash in source identifier
            
        Returns:
            Dictionary of accuracy metrics by source identifier
        """
        # Collect data by source
        source_data = defaultdict(lambda: {
            'total_selections': 0,
            'consensus_selections': 0,
            'manual_overrides_from': 0,
            'manual_overrides_to': 0,
            'consensus_scores': [],
            'final_output_count': 0,
            'recalc_stability_checks': [],
            'total_appearances': 0
        })
        
        # Process each block's history
        for block_id, history in histories.items():
            # Track initial extract
            initial_source = self._get_source_identifier(
                history.initial_extract.source_attribution, include_config
            )
            source_data[initial_source]['total_appearances'] += 1
            
            # Track all changes
            previous_text = history.initial_extract.new_text
            previous_source = initial_source
            
            for change in history.changes:
                current_source = self._get_source_identifier(
                    change.source_attribution, include_config
                )
                source_data[current_source]['total_appearances'] += 1
                
                if change.change_type == ChangeType.CONSENSUS_SELECTION:
                    source_data[current_source]['consensus_selections'] += 1
                    source_data[current_source]['total_selections'] += 1
                    if change.consensus_score is not None:
                        source_data[current_source]['consensus_scores'].append(
                            change.consensus_score
                        )
                
                elif change.change_type == ChangeType.MANUAL_OVERRIDE:
                    # Previous source was overridden
                    source_data[previous_source]['manual_overrides_from'] += 1
                    # Current source was selected by user
                    source_data[current_source]['manual_overrides_to'] += 1
                    source_data[current_source]['total_selections'] += 1
                
                elif change.change_type == ChangeType.RECALCULATION:
                    # Check if text stayed the same (stability)
                    stability = 1.0 if change.new_text == previous_text else 0.0
                    source_data[current_source]['recalc_stability_checks'].append(stability)
                
                previous_text = change.new_text
                previous_source = current_source
            
            # Track final output contribution
            final_source = self._get_source_identifier(
                history.get_current_source(), include_config
            )
            source_data[final_source]['final_output_count'] += 1
        
        # Calculate metrics for each source
        metrics = {}
        total_blocks = len(histories)
        
        for source_id, data in source_data.items():
            total_selections = data['total_selections']
            
            # Calculate rates
            selection_rate = (
                (total_selections / data['total_appearances'] * 100.0)
                if data['total_appearances'] > 0 else 0.0
            )
            
            override_resistance = (
                1.0 - (data['manual_overrides_from'] / total_selections)
                if total_selections > 0 else 1.0
            )
            
            recalc_stability = (
                statistics.mean(data['recalc_stability_checks'])
                if data['recalc_stability_checks'] else 1.0
            )
            
            avg_consensus_score = (
                statistics.mean(data['consensus_scores'])
                if data['consensus_scores'] else 0.0
            )
            
            # Calculate overall accuracy score
            accuracy_score = self._calculate_accuracy_score(
                selection_rate=selection_rate / 100.0,  # Normalize to 0-1
                override_resistance=override_resistance,
                final_output_rate=data['final_output_count'] / total_blocks,
                avg_consensus_score=avg_consensus_score
            )
            
            metrics[source_id] = AccuracyMetrics(
                source_identifier=source_id,
                total_selections=total_selections,
                consensus_selections=data['consensus_selections'],
                manual_overrides_from=data['manual_overrides_from'],
                manual_overrides_to=data['manual_overrides_to'],
                recalculation_stability=recalc_stability,
                avg_consensus_score=avg_consensus_score,
                selection_rate=selection_rate,
                override_resistance=override_resistance,
                final_output_contribution=data['final_output_count'],
                accuracy_score=accuracy_score
            )
        
        return metrics
    
    def _get_source_identifier(self, source: SourceAttribution, 
                              include_config: bool) -> str:
        """Get source identifier string."""
        if include_config and source.configuration_hash:
            return f"{source.engine_name}:{source.configuration_hash}"
        return source.engine_name
    
    def _calculate_accuracy_score(self, selection_rate: float,
                                 override_resistance: float,
                                 final_output_rate: float,
                                 avg_consensus_score: float) -> float:
        """
        Calculate overall accuracy score using weighted components.
        
        Args:
            selection_rate: Rate of selection (0-1)
            override_resistance: Resistance to manual override (0-1)
            final_output_rate: Rate of appearance in final output (0-1)
            avg_consensus_score: Average consensus score (0-1)
            
        Returns:
            Overall accuracy score (0-1)
        """
        score = (
            self.consensus_weight * selection_rate +
            self.override_resistance_weight * override_resistance +
            self.final_output_weight * final_output_rate +
            self.score_weight * avg_consensus_score
        )
        return max(0.0, min(1.0, score))
    
    def rank_sources(self, histories: Dict[str, ChangeHistory],
                    include_config: bool = False) -> SourceRanking:
        """
        Rank all sources by accuracy metrics.
        
        Args:
            histories: Dictionary of block change histories
            include_config: Whether to include configuration hash in ranking
            
        Returns:
            SourceRanking with ranked sources
        """
        from datetime import datetime
        
        # Calculate metrics
        metrics = self.calculate_accuracy_metrics(histories, include_config)
        
        # Sort by accuracy score (descending)
        ranked = sorted(
            metrics.items(),
            key=lambda x: x[1].accuracy_score,
            reverse=True
        )
        
        return SourceRanking(
            rankings=ranked,
            total_blocks=len(histories),
            ranking_timestamp=datetime.now().isoformat(),
            ranking_criteria={
                'consensus_weight': self.consensus_weight,
                'override_resistance_weight': self.override_resistance_weight,
                'final_output_weight': self.final_output_weight,
                'score_weight': self.score_weight
            }
        )
    
    def get_best_source_for_block_type(self, histories: Dict[str, ChangeHistory],
                                      block_filter: callable = None) -> Optional[str]:
        """
        Get the best source for a specific type of block.
        
        Args:
            histories: Dictionary of block change histories
            block_filter: Optional filter function to select specific blocks
            
        Returns:
            Best source identifier or None
        """
        # Filter histories if filter provided
        if block_filter:
            filtered_histories = {
                block_id: history
                for block_id, history in histories.items()
                if block_filter(block_id, history)
            }
        else:
            filtered_histories = histories
        
        if not filtered_histories:
            return None
        
        # Rank sources for filtered blocks
        ranking = self.rank_sources(filtered_histories)
        
        if ranking.rankings:
            return ranking.rankings[0][0]  # Return top source
        
        return None
    
    def compare_sources(self, source1: str, source2: str,
                       histories: Dict[str, ChangeHistory]) -> Dict[str, Any]:
        """
        Compare two sources head-to-head.
        
        Args:
            source1: First source identifier
            source2: Second source identifier
            histories: Dictionary of block change histories
            
        Returns:
            Comparison results
        """
        metrics = self.calculate_accuracy_metrics(histories, include_config=True)
        
        metrics1 = metrics.get(source1)
        metrics2 = metrics.get(source2)
        
        if not metrics1 or not metrics2:
            return {
                'error': 'One or both sources not found',
                'source1_found': metrics1 is not None,
                'source2_found': metrics2 is not None
            }
        
        return {
            'source1': source1,
            'source2': source2,
            'accuracy_score_diff': metrics1.accuracy_score - metrics2.accuracy_score,
            'winner': source1 if metrics1.accuracy_score > metrics2.accuracy_score else source2,
            'metrics1': metrics1.to_dict(),
            'metrics2': metrics2.to_dict(),
            'comparison': {
                'selection_rate': {
                    'source1': metrics1.selection_rate,
                    'source2': metrics2.selection_rate,
                    'diff': metrics1.selection_rate - metrics2.selection_rate
                },
                'override_resistance': {
                    'source1': metrics1.override_resistance,
                    'source2': metrics2.override_resistance,
                    'diff': metrics1.override_resistance - metrics2.override_resistance
                },
                'final_output_contribution': {
                    'source1': metrics1.final_output_contribution,
                    'source2': metrics2.final_output_contribution,
                    'diff': metrics1.final_output_contribution - metrics2.final_output_contribution
                }
            }
        }
    
    def get_ranking_summary(self, ranking: SourceRanking) -> Dict[str, Any]:
        """
        Get a summary of the ranking results.
        
        Args:
            ranking: Source ranking
            
        Returns:
            Summary dictionary
        """
        if not ranking.rankings:
            return {
                'total_sources': 0,
                'best_source': None,
                'worst_source': None,
                'avg_accuracy_score': 0.0
            }
        
        accuracy_scores = [metrics.accuracy_score for _, metrics in ranking.rankings]
        
        return {
            'total_sources': len(ranking.rankings),
            'total_blocks': ranking.total_blocks,
            'best_source': ranking.rankings[0][0],
            'best_accuracy_score': ranking.rankings[0][1].accuracy_score,
            'worst_source': ranking.rankings[-1][0],
            'worst_accuracy_score': ranking.rankings[-1][1].accuracy_score,
            'avg_accuracy_score': statistics.mean(accuracy_scores),
            'score_variance': statistics.variance(accuracy_scores) if len(accuracy_scores) > 1 else 0.0,
            'ranking_criteria': ranking.ranking_criteria,
            'timestamp': ranking.ranking_timestamp
        }


def rank_sources_by_accuracy(histories: Dict[str, ChangeHistory],
                            include_config: bool = False) -> SourceRanking:
    """
    Convenience function to rank sources by accuracy.
    
    Args:
        histories: Dictionary of block change histories
        include_config: Whether to include configuration in ranking
        
    Returns:
        SourceRanking with ranked sources
    """
    ranker = SourceRanker()
    return ranker.rank_sources(histories, include_config)


def get_best_source(histories: Dict[str, ChangeHistory]) -> Optional[str]:
    """
    Convenience function to get the best performing source.
    
    Args:
        histories: Dictionary of block change histories
        
    Returns:
        Best source identifier or None
    """
    ranking = rank_sources_by_accuracy(histories)
    if ranking.rankings:
        return ranking.rankings[0][0]
    return None

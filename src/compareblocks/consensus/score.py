# src/compareblocks/consensus/score.py
"""
Consensus scoring algorithms for text variations.
Implements weighted scoring with configurable thresholds and caps.
"""

import statistics
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..features.core import CoreFeatureExtractor, LengthFeatures
from ..features.language import LanguageFeatureExtractor, LanguageFeatures
from ..features.anomaly import AnomalyDetector, AnomalyFeatures
from ..features.context import ContextSimilarityExtractor, ContextFeatures
from ..features.consistency import CharacterConsistencyTracker, CharacterConsistency


@dataclass
class ScoringWeights:
    """Configurable weights for consensus scoring."""
    length_consistency: float = 0.25
    character_consistency: float = 0.15
    language_fitness: float = 0.30
    anomaly_penalty: float = 0.20
    context_relevance: float = 0.15
    orientation_penalty: float = 0.10
    
    def normalize(self) -> 'ScoringWeights':
        """Normalize weights to sum to 1.0."""
        total = (self.length_consistency + self.character_consistency + 
                self.language_fitness + self.anomaly_penalty + 
                self.context_relevance + self.orientation_penalty)
        
        if total == 0:
            return ScoringWeights()
        
        return ScoringWeights(
            length_consistency=self.length_consistency / total,
            character_consistency=self.character_consistency / total,
            language_fitness=self.language_fitness / total,
            anomaly_penalty=self.anomaly_penalty / total,
            context_relevance=self.context_relevance / total,
            orientation_penalty=self.orientation_penalty / total
        )


@dataclass
class ScoringThresholds:
    """Configurable thresholds for consensus scoring."""
    min_language_fitness: float = 0.15
    max_anomaly_score: float = 0.7
    max_orientation_mismatch: float = 45.0  # degrees
    min_overall_score: float = 0.1
    
    
@dataclass
class VariationScore:
    """Complete scoring information for a text variation."""
    variation_index: int
    engine_name: str
    raw_text: str
    length_score: float
    character_consistency_score: float
    language_score: float
    anomaly_score: float
    context_score: float
    orientation_penalty: float
    weighted_score: float
    final_score: float
    score_components: Dict[str, float]
    flags: List[str]
    character_consistency: Optional[CharacterConsistency] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            'variation_index': self.variation_index,
            'engine_name': self.engine_name,
            'raw_text': self.raw_text,
            'length_score': self.length_score,
            'character_consistency_score': self.character_consistency_score,
            'language_score': self.language_score,
            'anomaly_score': self.anomaly_score,
            'context_score': self.context_score,
            'orientation_penalty': self.orientation_penalty,
            'weighted_score': self.weighted_score,
            'final_score': self.final_score,
            'score_components': self.score_components,
            'flags': self.flags
        }
        
        if self.character_consistency:
            result['character_consistency'] = self.character_consistency.to_dict()
        
        return result


class ConsensusScorer:
    """Implements consensus scoring algorithms for text variations."""
    
    def __init__(self, weights: Optional[ScoringWeights] = None, 
                 thresholds: Optional[ScoringThresholds] = None):
        """
        Initialize the consensus scorer.
        
        Args:
            weights: Scoring weights configuration
            thresholds: Scoring thresholds configuration
        """
        self.weights = weights.normalize() if weights else ScoringWeights().normalize()
        self.thresholds = thresholds if thresholds else ScoringThresholds()
        
        # Initialize feature extractors
        self.core_extractor = CoreFeatureExtractor()
        self.language_extractor = LanguageFeatureExtractor()
        self.anomaly_detector = AnomalyDetector()
        self.context_extractor = ContextSimilarityExtractor()
        self.consistency_tracker = CharacterConsistencyTracker()
    
    def _calculate_orientation_penalty(self, expected_orientation: float, 
                                     actual_orientation: float) -> float:
        """
        Calculate penalty for orientation mismatch.
        
        Args:
            expected_orientation: Expected text orientation in degrees
            actual_orientation: Actual text orientation in degrees
            
        Returns:
            Penalty score (0.0 = no penalty, 1.0 = maximum penalty)
        """
        if expected_orientation is None or actual_orientation is None:
            return 0.0  # No penalty if orientation data unavailable
        
        # Calculate angular difference
        diff = abs(expected_orientation - actual_orientation)
        # Handle wraparound (e.g., 359° vs 1°)
        diff = min(diff, 360 - diff)
        
        # Apply penalty based on threshold
        if diff <= self.thresholds.max_orientation_mismatch:
            return 0.0
        
        # Linear penalty beyond threshold
        max_diff = 180.0  # Maximum possible meaningful difference
        penalty_range = max_diff - self.thresholds.max_orientation_mismatch
        excess_diff = diff - self.thresholds.max_orientation_mismatch
        
        penalty = min(1.0, excess_diff / penalty_range)
        return penalty
    
    def _apply_language_fitness_cap(self, score: float, language_fitness: float) -> float:
        """
        Apply language fitness cap to score.
        
        Args:
            score: Current score
            language_fitness: Language fitness score (0.0 to 1.0)
            
        Returns:
            Capped score
        """
        if language_fitness < self.thresholds.min_language_fitness:
            # Cap score based on how far below threshold
            fitness_ratio = language_fitness / self.thresholds.min_language_fitness
            max_allowed_score = 0.5 * fitness_ratio  # Maximum 50% of normal score
            return min(score, max_allowed_score)
        
        return score
    
    def _apply_anomaly_score_cap(self, score: float, anomaly_score: float) -> float:
        """
        Apply anomaly score cap to score.
        
        Args:
            score: Current score
            anomaly_score: Anomaly score (0.0 to 1.0, higher is more anomalous)
            
        Returns:
            Capped score
        """
        if anomaly_score > self.thresholds.max_anomaly_score:
            # Severely cap score for highly anomalous text
            anomaly_excess = anomaly_score - self.thresholds.max_anomaly_score
            anomaly_penalty = min(0.8, anomaly_excess * 2.0)  # Up to 80% penalty
            return score * (1.0 - anomaly_penalty)
        
        return score
    
    def score_variation(self, variation_text: str, engine_name: str, 
                       variation_index: int, all_variations: List[str],
                       expected_orientation: Optional[float] = None,
                       actual_orientation: Optional[float] = None,
                       context_texts: Optional[List[str]] = None,
                       block_id: Optional[str] = None) -> VariationScore:
        """
        Score a single text variation.
        
        Args:
            variation_text: The text variation to score
            engine_name: Name of the engine that produced this variation
            variation_index: Index of this variation in the list
            all_variations: All variations for consistency scoring
            expected_orientation: Expected text orientation in degrees
            actual_orientation: Actual text orientation in degrees
            context_texts: Optional context texts for similarity scoring
            
        Returns:
            VariationScore object with complete scoring information
        """
        flags = []
        
        # Extract features
        length_features = self.core_extractor.extract_length_features(variation_text)
        language_features = self.language_extractor.extract_language_features(variation_text)
        anomaly_features = self.anomaly_detector.extract_anomaly_features(variation_text)
        context_features = self.context_extractor.extract_context_features(
            variation_text, context_texts)
        
        # Calculate consistency score with all variations
        consistency_scores = self.core_extractor.compute_consistency_score(all_variations)
        length_consistency = consistency_scores.get(str(variation_index), 0.0)
        
        # Calculate character-level consistency
        character_consistency = None
        character_consistency_score = 0.0
        if block_id:
            character_consistency = self.consistency_tracker.track_consistency_for_block(
                block_id, all_variations
            )
            character_consistency_score = character_consistency.character_consistency_score
        else:
            # Fallback to simple character consistency calculation
            char_score, _ = self.consistency_tracker.calculate_character_consistency(all_variations)
            character_consistency_score = char_score
        
        # Calculate individual component scores
        length_score = length_consistency
        language_score = language_features.fitness_score
        anomaly_score = 1.0 - anomaly_features.overall_anomaly_score  # Invert (higher is better)
        context_score = context_features.context_relevance_score
        
        # Calculate orientation penalty
        orientation_penalty = self._calculate_orientation_penalty(
            expected_orientation, actual_orientation)
        
        # Calculate weighted score
        weighted_score = (
            self.weights.length_consistency * length_score +
            self.weights.character_consistency * character_consistency_score +
            self.weights.language_fitness * language_score +
            self.weights.anomaly_penalty * anomaly_score +
            self.weights.context_relevance * context_score -
            self.weights.orientation_penalty * orientation_penalty
        )
        
        # Ensure weighted score is in valid range
        weighted_score = max(0.0, min(1.0, weighted_score))
        
        # Apply caps based on language fitness and anomaly scores
        final_score = weighted_score
        final_score = self._apply_language_fitness_cap(final_score, language_features.fitness_score)
        final_score = self._apply_anomaly_score_cap(final_score, anomaly_features.overall_anomaly_score)
        
        # Add flags based on thresholds
        if language_features.fitness_score < self.thresholds.min_language_fitness:
            flags.append('low_language_fitness')
        
        if anomaly_features.overall_anomaly_score > self.thresholds.max_anomaly_score:
            flags.append('high_anomaly_score')
        
        if orientation_penalty > 0:
            flags.append('orientation_mismatch')
        
        if final_score < self.thresholds.min_overall_score:
            flags.append('low_overall_score')
        
        # Add specific anomaly flags
        flags.extend(anomaly_features.anomaly_flags)
        
        # Create score components dictionary
        score_components = {
            'length_consistency': length_score,
            'character_consistency': character_consistency_score,
            'language_fitness': language_features.fitness_score,
            'anomaly_score': anomaly_features.overall_anomaly_score,
            'context_relevance': context_features.context_relevance_score,
            'orientation_penalty': orientation_penalty,
            'weighted_score': weighted_score,
            'language_fitness_cap_applied': final_score != weighted_score,
            'anomaly_cap_applied': final_score != self._apply_language_fitness_cap(weighted_score, language_features.fitness_score)
        }
        
        return VariationScore(
            variation_index=variation_index,
            engine_name=engine_name,
            raw_text=variation_text,
            length_score=length_score,
            character_consistency_score=character_consistency_score,
            language_score=language_score,
            anomaly_score=anomaly_score,
            context_score=context_score,
            orientation_penalty=orientation_penalty,
            weighted_score=weighted_score,
            final_score=final_score,
            score_components=score_components,
            flags=flags,
            character_consistency=character_consistency
        )
    
    def score_variations(self, variations: List[Dict[str, Any]], 
                        context_texts: Optional[List[str]] = None,
                        block_id: Optional[str] = None) -> List[VariationScore]:
        """
        Score multiple text variations.
        
        Args:
            variations: List of variation dictionaries with keys:
                       'text', 'engine', 'orientation' (optional)
            context_texts: Optional context texts for similarity scoring
            
        Returns:
            List of VariationScore objects
        """
        if not variations:
            return []
        
        # Extract text variations for consistency scoring
        variation_texts = [var.get('text', '') for var in variations]
        
        # Determine expected orientation (use most common orientation)
        orientations = [var.get('orientation') for var in variations if var.get('orientation') is not None]
        expected_orientation = None
        if orientations:
            expected_orientation = statistics.mode(orientations) if len(set(orientations)) > 1 else orientations[0]
        
        # Score each variation
        scores = []
        for i, variation in enumerate(variations):
            text = variation.get('text', '')
            engine = variation.get('engine', f'engine_{i}')
            actual_orientation = variation.get('orientation')
            
            score = self.score_variation(
                variation_text=text,
                engine_name=engine,
                variation_index=i,
                all_variations=variation_texts,
                expected_orientation=expected_orientation,
                actual_orientation=actual_orientation,
                context_texts=context_texts,
                block_id=block_id
            )
            scores.append(score)
        
        return scores
    
    def get_best_variation(self, variations: List[Dict[str, Any]], 
                          context_texts: Optional[List[str]] = None,
                          block_id: Optional[str] = None) -> Optional[VariationScore]:
        """
        Get the best scoring variation.
        
        Args:
            variations: List of variation dictionaries
            context_texts: Optional context texts for similarity scoring
            block_id: Optional block identifier for character consistency tracking
            
        Returns:
            Best VariationScore or None if no variations
        """
        scores = self.score_variations(variations, context_texts, block_id)
        if not scores:
            return None
        
        # Return variation with highest final score
        return max(scores, key=lambda x: x.final_score)
    
    def rank_variations(self, variations: List[Dict[str, Any]], 
                       context_texts: Optional[List[str]] = None,
                       block_id: Optional[str] = None) -> List[VariationScore]:
        """
        Rank variations by score (best first).
        
        Args:
            variations: List of variation dictionaries
            context_texts: Optional context texts for similarity scoring
            block_id: Optional block identifier for character consistency tracking
            
        Returns:
            List of VariationScore objects sorted by final_score (descending)
        """
        scores = self.score_variations(variations, context_texts, block_id)
        return sorted(scores, key=lambda x: x.final_score, reverse=True)
    
    def get_scoring_statistics(self, variations: List[Dict[str, Any]], 
                             context_texts: Optional[List[str]] = None,
                             block_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get scoring statistics for a set of variations.
        
        Args:
            variations: List of variation dictionaries
            context_texts: Optional context texts for similarity scoring
            block_id: Optional block identifier for character consistency tracking
            
        Returns:
            Dictionary with scoring statistics
        """
        scores = self.score_variations(variations, context_texts, block_id)
        
        if not scores:
            return {
                'total_variations': 0,
                'avg_score': 0.0,
                'max_score': 0.0,
                'min_score': 0.0,
                'score_variance': 0.0,
                'flagged_variations': 0,
                'common_flags': {}
            }
        
        final_scores = [s.final_score for s in scores]
        all_flags = []
        for score in scores:
            all_flags.extend(score.flags)
        
        from collections import Counter
        flag_counts = Counter(all_flags)
        flagged_count = sum(1 for s in scores if s.flags)
        
        return {
            'total_variations': len(scores),
            'avg_score': statistics.mean(final_scores),
            'max_score': max(final_scores),
            'min_score': min(final_scores),
            'score_variance': statistics.variance(final_scores) if len(final_scores) > 1 else 0.0,
            'flagged_variations': flagged_count,
            'common_flags': dict(flag_counts.most_common(5)),
            'score_distribution': {
                'high_scores': sum(1 for s in final_scores if s >= 0.7),
                'medium_scores': sum(1 for s in final_scores if 0.3 <= s < 0.7),
                'low_scores': sum(1 for s in final_scores if s < 0.3)
            }
        }
    
    def update_weights(self, new_weights: ScoringWeights) -> None:
        """Update scoring weights."""
        self.weights = new_weights.normalize()
    
    def update_thresholds(self, new_thresholds: ScoringThresholds) -> None:
        """Update scoring thresholds."""
        self.thresholds = new_thresholds
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current scorer configuration."""
        return {
            'weights': {
                'length_consistency': self.weights.length_consistency,
                'character_consistency': self.weights.character_consistency,
                'language_fitness': self.weights.language_fitness,
                'anomaly_penalty': self.weights.anomaly_penalty,
                'context_relevance': self.weights.context_relevance,
                'orientation_penalty': self.weights.orientation_penalty
            },
            'thresholds': {
                'min_language_fitness': self.thresholds.min_language_fitness,
                'max_anomaly_score': self.thresholds.max_anomaly_score,
                'max_orientation_mismatch': self.thresholds.max_orientation_mismatch,
                'min_overall_score': self.thresholds.min_overall_score
            }
        }

def create_default_scoring_weights() -> ScoringWeights:
    """
    Create default scoring weights for consensus evaluation.
    
    Returns:
        ScoringWeights: Default weight configuration
    """
    return ScoringWeights()


def create_conservative_scoring_weights() -> ScoringWeights:
    """
    Create conservative scoring weights that prioritize quality over speed.
    
    Returns:
        ScoringWeights: Conservative weight configuration with higher anomaly penalty
    """
    return ScoringWeights(
        length_consistency=0.15,
        character_consistency=0.20,
        language_fitness=0.35,
        anomaly_penalty=0.30,
        context_relevance=0.05,
        orientation_penalty=0.05
    )


def create_default_scoring_thresholds() -> ScoringThresholds:
    """
    Create default scoring thresholds for consensus evaluation.
    
    Returns:
        ScoringThresholds: Default threshold configuration
    """
    return ScoringThresholds()


def create_strict_scoring_thresholds() -> ScoringThresholds:
    """
    Create strict scoring thresholds for high-quality requirements.
    
    Returns:
        ScoringThresholds: Strict threshold configuration
    """
    return ScoringThresholds(
        min_language_fitness=0.25,
        max_anomaly_score=0.5,
        max_orientation_mismatch=30.0,
        min_overall_score=0.2
    )


def calculate_median_length_consistency(variations: List[Dict[str, Any]]) -> float:
    """
    Calculate length consistency score based on median variation length.
    
    Args:
        variations: List of text variations with 'text' field
        
    Returns:
        float: Length consistency score (0.0 to 1.0)
    """
    if not variations:
        return 0.0
    
    lengths = [len(var.get('text', '')) for var in variations]
    if not lengths:
        return 0.0
    
    median_length = statistics.median(lengths)
    if median_length == 0:
        return 1.0 if all(l == 0 for l in lengths) else 0.0
    
    # Calculate consistency as inverse of coefficient of variation from median
    deviations = [abs(length - median_length) for length in lengths]
    avg_deviation = sum(deviations) / len(deviations)
    
    consistency = 1.0 - min(1.0, avg_deviation / median_length)
    return max(0.0, consistency)


def calculate_orientation_penalty(variation: Dict[str, Any], expected_orientation: float = 0.0) -> float:
    """
    Calculate orientation penalty for a variation.
    
    Args:
        variation: Text variation with optional 'orientation' field
        expected_orientation: Expected orientation in degrees
        
    Returns:
        float: Orientation penalty (0.0 to 1.0, where 0.0 is no penalty)
    """
    orientation = variation.get('orientation', 0.0)
    if orientation is None:
        return 0.0
    
    angle_diff = abs(orientation - expected_orientation)
    # Normalize to 0-180 degree range
    angle_diff = min(angle_diff, 360 - angle_diff)
    
    # Convert to penalty (0.0 for perfect alignment, 1.0 for 180 degree difference)
    penalty = angle_diff / 180.0
    return min(1.0, penalty)


def score_single_variation(variation: Dict[str, Any], 
                          context_variations: List[Dict[str, Any]] = None,
                          weights: ScoringWeights = None,
                          thresholds: ScoringThresholds = None) -> VariationScore:
    """
    Score a single text variation using all available features.
    
    Args:
        variation: Text variation to score
        context_variations: Other variations for context (optional)
        weights: Scoring weights (uses defaults if None)
        thresholds: Scoring thresholds (uses defaults if None)
        
    Returns:
        VariationScore: Complete scoring results
    """
    if weights is None:
        weights = create_default_scoring_weights()
    if thresholds is None:
        thresholds = create_default_scoring_thresholds()
    
    text = variation.get('text', '')
    engine = variation.get('engine', 'unknown')
    
    # Extract features
    core_extractor = CoreFeatureExtractor()
    language_extractor = LanguageFeatureExtractor()
    anomaly_detector = AnomalyDetector()
    context_extractor = ContextSimilarityExtractor()
    
    length_features = core_extractor.extract_length_features(text)
    language_features = language_extractor.extract_language_features(text)
    anomaly_features = anomaly_detector.extract_anomaly_features(text)
    
    # Context features (if other variations available)
    context_features = None
    if context_variations:
        context_texts = [v.get('text', '') for v in context_variations]
        context_features = context_extractor.extract_context_features(text, context_texts)
    
    # Calculate component scores
    length_score = calculate_median_length_consistency([variation] + (context_variations or []))
    language_score = language_features.word_in_language_rate
    anomaly_score = 1.0 - anomaly_features.overall_anomaly_score  # Invert for scoring
    context_score = context_features.semantic_coherence_score if context_features else 0.0
    orientation_penalty = calculate_orientation_penalty(variation)
    
    # Apply caps
    language_fitness_cap_applied = False
    if language_score < thresholds.min_language_fitness:
        language_score = 0.0
        language_fitness_cap_applied = True
    
    anomaly_cap_applied = False
    if (1.0 - anomaly_score) > thresholds.max_anomaly_score:
        anomaly_score = 0.0
        anomaly_cap_applied = True
    
    # Calculate weighted score
    weighted_score = (
        weights.length_consistency * length_score +
        weights.language_fitness * language_score +
        weights.anomaly_penalty * anomaly_score +
        weights.context_relevance * context_score -
        weights.orientation_penalty * orientation_penalty
    )
    
    final_score = max(0.0, weighted_score)
    
    # Apply minimum threshold
    if final_score < thresholds.min_overall_score:
        final_score = 0.0
    
    # Determine flags
    flags = []
    if language_fitness_cap_applied:
        flags.append('low_language_fitness')
    if anomaly_cap_applied:
        flags.append('high_anomaly_score')
    if final_score < thresholds.min_overall_score:
        flags.append('low_overall_score')
    if orientation_penalty > 0.5:
        flags.append('orientation_mismatch')
    # Check for unusual patterns based on anomaly score
    if anomaly_features.overall_anomaly_score > 0.7:
        flags.append('unusual_char_patterns')
    
    return VariationScore(
        variation_index=0,  # Will be set by caller
        engine_name=engine,
        raw_text=text,
        length_score=length_score,
        character_consistency_score=0.0,  # Default value, will be updated by consistency tracker
        language_score=language_score,
        anomaly_score=1.0 - anomaly_score,  # Return original anomaly score
        context_score=context_score,
        orientation_penalty=orientation_penalty,
        weighted_score=weighted_score,
        final_score=final_score,
        score_components={
            'length_consistency': length_score,
            'language_fitness': language_score,
            'anomaly_score': 1.0 - anomaly_score,
            'context_relevance': context_score,
            'orientation_penalty': orientation_penalty,
            'weighted_score': weighted_score,
            'language_fitness_cap_applied': language_fitness_cap_applied,
            'anomaly_cap_applied': anomaly_cap_applied
        },
        flags=flags
    )


def rank_variations_by_score(scores: List[VariationScore]) -> List[VariationScore]:
    """
    Rank variations by their final scores in descending order.
    
    Args:
        scores: List of variation scores
        
    Returns:
        List[VariationScore]: Sorted list with highest scores first
    """
    return sorted(scores, key=lambda x: x.final_score, reverse=True)


def get_scoring_statistics(scores: List[VariationScore]) -> Dict[str, Any]:
    """
    Calculate statistics for a set of variation scores.
    
    Args:
        scores: List of variation scores
        
    Returns:
        Dict: Statistics including mean, median, std dev, etc.
    """
    if not scores:
        return {
            'count': 0,
            'mean_score': 0.0,
            'median_score': 0.0,
            'std_dev': 0.0,
            'min_score': 0.0,
            'max_score': 0.0,
            'flagged_count': 0
        }
    
    final_scores = [s.final_score for s in scores]
    flagged_count = sum(1 for s in scores if s.flags)
    
    return {
        'count': len(scores),
        'mean_score': statistics.mean(final_scores),
        'median_score': statistics.median(final_scores),
        'std_dev': statistics.stdev(final_scores) if len(final_scores) > 1 else 0.0,
        'min_score': min(final_scores),
        'max_score': max(final_scores),
        'flagged_count': flagged_count,
        'flagged_percentage': (flagged_count / len(scores)) * 100.0
    }
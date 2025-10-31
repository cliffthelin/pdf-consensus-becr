# src/compareblocks/consensus/guard.py
"""
Hallucination guard system for preventing selection of obviously incorrect text.
Integrates anomaly detection into scoring to flag variations for manual review.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .score import ConsensusScorer, VariationScore, ScoringThresholds
from ..features.anomaly import AnomalyDetector


@dataclass
class GuardThresholds:
    """Configurable thresholds for hallucination guard."""
    max_auto_select_anomaly: float = 0.5  # Maximum anomaly score for auto-selection
    min_auto_select_score: float = 0.2    # Minimum overall score for auto-selection
    min_quality_threshold: float = 0.1    # Minimum quality for any variation
    max_orientation_deviation: float = 45.0  # Maximum orientation deviation in degrees
    min_language_fitness: float = 0.15    # Minimum language fitness for auto-selection
    
    
@dataclass
class GuardDecision:
    """Decision made by the hallucination guard."""
    action: str  # 'auto_select', 'flag_for_review', 'reject_all'
    selected_variation: Optional[VariationScore]
    reason: str
    confidence: float
    flags: List[str]
    all_scores: List[VariationScore]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'action': self.action,
            'selected_variation': self.selected_variation.to_dict() if self.selected_variation else None,
            'reason': self.reason,
            'confidence': self.confidence,
            'flags': self.flags,
            'all_scores': [score.to_dict() for score in self.all_scores]
        }


class HallucinationGuard:
    """Prevents auto-selection of obviously incorrect text variations."""
    
    def __init__(self, scorer: Optional[ConsensusScorer] = None,
                 guard_thresholds: Optional[GuardThresholds] = None):
        """
        Initialize the hallucination guard.
        
        Args:
            scorer: ConsensusScorer instance (creates default if None)
            guard_thresholds: Guard thresholds configuration
        """
        self.scorer = scorer if scorer else ConsensusScorer()
        self.guard_thresholds = guard_thresholds if guard_thresholds else GuardThresholds()
        self.anomaly_detector = AnomalyDetector()
    
    def _check_individual_variation_quality(self, score: VariationScore) -> Tuple[bool, List[str]]:
        """
        Check if an individual variation meets quality standards.
        
        Args:
            score: VariationScore to check
            
        Returns:
            Tuple of (passes_quality_check, list_of_issues)
        """
        issues = []
        
        # Check anomaly score
        if score.anomaly_score < (1.0 - self.guard_thresholds.max_auto_select_anomaly):
            issues.append('high_anomaly_score')
        
        # Check overall score
        if score.final_score < self.guard_thresholds.min_auto_select_score:
            issues.append('low_overall_score')
        
        # Check language fitness
        if score.language_score < self.guard_thresholds.min_language_fitness:
            issues.append('poor_language_fitness')
        
        # Check orientation penalty
        if score.orientation_penalty > 0:
            issues.append('orientation_mismatch')
        
        # Check for specific anomaly flags that should prevent auto-selection
        dangerous_flags = {
            'one_char_per_line', 'excessive_punctuation', 'repeated_characters',
            'unusual_char_patterns', 'excessive_single_char_words'
        }
        
        for flag in score.flags:
            if flag in dangerous_flags:
                issues.append(f'anomaly_flag_{flag}')
        
        return len(issues) == 0, issues
    
    def _check_overall_quality(self, scores: List[VariationScore]) -> Tuple[bool, str]:
        """
        Check if any variations meet minimum quality standards.
        
        Args:
            scores: List of VariationScore objects
            
        Returns:
            Tuple of (has_acceptable_quality, reason)
        """
        if not scores:
            return False, 'no_variations_provided'
        
        # Check if any variation meets minimum quality threshold
        acceptable_variations = [
            score for score in scores 
            if score.final_score >= self.guard_thresholds.min_quality_threshold
        ]
        
        if not acceptable_variations:
            return False, 'all_variations_below_quality_threshold'
        
        # Check if best variation is significantly better than others
        best_score = max(score.final_score for score in scores)
        if best_score < self.guard_thresholds.min_auto_select_score:
            return False, 'best_variation_insufficient_quality'
        
        return True, 'acceptable_quality_found'
    
    def _calculate_confidence(self, selected_score: VariationScore, 
                            all_scores: List[VariationScore]) -> float:
        """
        Calculate confidence in the guard decision.
        
        Args:
            selected_score: The selected variation score
            all_scores: All variation scores
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not all_scores or not selected_score:
            return 0.0
        
        # Base confidence on the selected score
        base_confidence = selected_score.final_score
        
        # Adjust based on score separation from other variations
        other_scores = [s.final_score for s in all_scores if s != selected_score]
        if other_scores:
            max_other_score = max(other_scores)
            score_separation = selected_score.final_score - max_other_score
            
            # Higher separation increases confidence
            separation_bonus = min(0.3, score_separation * 2.0)
            base_confidence += separation_bonus
        
        # Penalize if selected variation has concerning flags
        flag_penalty = len(selected_score.flags) * 0.05
        base_confidence -= flag_penalty
        
        return max(0.0, min(1.0, base_confidence))
    
    def evaluate_variations(self, variations: List[Dict[str, Any]], 
                          context_texts: Optional[List[str]] = None) -> GuardDecision:
        """
        Evaluate variations and make a guard decision.
        
        Args:
            variations: List of variation dictionaries
            context_texts: Optional context texts for similarity scoring
            
        Returns:
            GuardDecision with action and reasoning
        """
        # Score all variations
        scores = self.scorer.score_variations(variations, context_texts)
        
        if not scores:
            return GuardDecision(
                action='reject_all',
                selected_variation=None,
                reason='no_variations_to_evaluate',
                confidence=1.0,
                flags=['no_input'],
                all_scores=[]
            )
        
        # Check overall quality
        has_quality, quality_reason = self._check_overall_quality(scores)
        
        if not has_quality:
            return GuardDecision(
                action='flag_for_review',
                selected_variation=None,
                reason=quality_reason,
                confidence=0.9,
                flags=['poor_overall_quality'],
                all_scores=scores
            )
        
        # Find best variation
        best_score = max(scores, key=lambda x: x.final_score)
        
        # Check if best variation passes individual quality checks
        passes_quality, quality_issues = self._check_individual_variation_quality(best_score)
        
        if not passes_quality:
            return GuardDecision(
                action='flag_for_review',
                selected_variation=best_score,
                reason=f'best_variation_has_issues: {", ".join(quality_issues)}',
                confidence=0.7,
                flags=['quality_issues'] + quality_issues,
                all_scores=scores
            )
        
        # Check for close competition (multiple high-scoring variations)
        high_scoring_variations = [
            s for s in scores 
            if s.final_score >= self.guard_thresholds.min_auto_select_score
        ]
        
        if len(high_scoring_variations) > 1:
            # Check if scores are very close
            score_range = max(s.final_score for s in high_scoring_variations) - \
                         min(s.final_score for s in high_scoring_variations)
            
            if score_range < 0.1:  # Very close scores
                return GuardDecision(
                    action='flag_for_review',
                    selected_variation=best_score,
                    reason='multiple_high_quality_variations_with_close_scores',
                    confidence=0.6,
                    flags=['close_competition'],
                    all_scores=scores
                )
        
        # Auto-select the best variation
        confidence = self._calculate_confidence(best_score, scores)
        
        return GuardDecision(
            action='auto_select',
            selected_variation=best_score,
            reason='best_variation_passes_quality_checks',
            confidence=confidence,
            flags=[],
            all_scores=scores
        )
    
    def is_variation_safe_for_auto_selection(self, variation_text: str, 
                                           engine_name: str = 'unknown') -> bool:
        """
        Quick check if a single variation is safe for auto-selection.
        
        Args:
            variation_text: Text variation to check
            engine_name: Name of the engine
            
        Returns:
            True if variation is safe for auto-selection
        """
        # Create a single variation for scoring
        variations = [{'text': variation_text, 'engine': engine_name}]
        decision = self.evaluate_variations(variations)
        
        return decision.action == 'auto_select'
    
    def get_anomaly_summary(self, variations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary of anomalies detected in variations.
        
        Args:
            variations: List of variation dictionaries
            
        Returns:
            Dictionary with anomaly summary
        """
        anomaly_summaries = []
        
        for i, variation in enumerate(variations):
            text = variation.get('text', '')
            engine = variation.get('engine', f'engine_{i}')
            
            anomaly_features = self.anomaly_detector.extract_anomaly_features(text)
            
            anomaly_summaries.append({
                'engine': engine,
                'anomaly_score': anomaly_features.overall_anomaly_score,
                'flags': anomaly_features.anomaly_flags,
                'entropy': anomaly_features.entropy_score,
                'repetition': anomaly_features.repetition_score,
                'space_ratio': anomaly_features.space_ratio
            })
        
        # Calculate overall statistics
        anomaly_scores = [s['anomaly_score'] for s in anomaly_summaries]
        all_flags = []
        for s in anomaly_summaries:
            all_flags.extend(s['flags'])
        
        from collections import Counter
        flag_counts = Counter(all_flags)
        
        return {
            'total_variations': len(variations),
            'avg_anomaly_score': sum(anomaly_scores) / len(anomaly_scores) if anomaly_scores else 0.0,
            'max_anomaly_score': max(anomaly_scores) if anomaly_scores else 0.0,
            'highly_anomalous_count': sum(1 for s in anomaly_scores if s > self.guard_thresholds.max_auto_select_anomaly),
            'common_anomaly_flags': dict(flag_counts.most_common(5)),
            'variation_details': anomaly_summaries
        }
    
    def update_guard_thresholds(self, new_thresholds: GuardThresholds) -> None:
        """Update guard thresholds."""
        self.guard_thresholds = new_thresholds
    
    def get_guard_configuration(self) -> Dict[str, Any]:
        """Get current guard configuration."""
        return {
            'guard_thresholds': {
                'max_auto_select_anomaly': self.guard_thresholds.max_auto_select_anomaly,
                'min_auto_select_score': self.guard_thresholds.min_auto_select_score,
                'min_quality_threshold': self.guard_thresholds.min_quality_threshold,
                'max_orientation_deviation': self.guard_thresholds.max_orientation_deviation,
                'min_language_fitness': self.guard_thresholds.min_language_fitness
            },
            'scorer_configuration': self.scorer.get_configuration()
        }

def create_default_guard_thresholds() -> GuardThresholds:
    """
    Create default guard thresholds for hallucination detection.
    
    Returns:
        GuardThresholds: Default threshold configuration
    """
    return GuardThresholds()


def create_strict_guard_thresholds() -> GuardThresholds:
    """
    Create strict guard thresholds for conservative hallucination detection.
    
    Returns:
        GuardThresholds: Strict threshold configuration
    """
    return GuardThresholds(
        min_quality_score=0.7,
        max_anomaly_tolerance=0.3,
        min_confidence_gap=0.2,
        max_close_competition_threshold=0.1
    )


def detect_hallucination_patterns(variation: Dict[str, Any]) -> List[str]:
    """
    Detect potential hallucination patterns in a text variation.
    
    Args:
        variation: Text variation to analyze
        
    Returns:
        List[str]: List of detected hallucination patterns
    """
    text = variation.get('text', '')
    patterns = []
    
    if not text:
        patterns.append('empty_text')
        return patterns
    
    # Check for excessive repetition
    if len(set(text.replace(' ', ''))) < len(text) * 0.3:
        patterns.append('excessive_repetition')
    
    # Check for unusual character patterns
    non_alpha_ratio = sum(1 for c in text if not c.isalpha()) / len(text)
    if non_alpha_ratio > 0.5:
        patterns.append('high_non_alpha_ratio')
    
    # Check for very short or very long text
    if len(text) < 3:
        patterns.append('too_short')
    elif len(text) > 1000:
        patterns.append('unusually_long')
    
    # Check for digit-heavy content (potential OCR errors)
    digit_ratio = sum(1 for c in text if c.isdigit()) / len(text)
    if digit_ratio > 0.3:
        patterns.append('digit_heavy')
    
    return patterns


def evaluate_variation_quality(variation: Dict[str, Any], 
                             thresholds: GuardThresholds = None) -> Dict[str, Any]:
    """
    Evaluate the quality of a single variation for hallucination detection.
    
    Args:
        variation: Text variation to evaluate
        thresholds: Guard thresholds (uses defaults if None)
        
    Returns:
        Dict: Quality evaluation results
    """
    if thresholds is None:
        thresholds = create_default_guard_thresholds()
    
    text = variation.get('text', '')
    confidence = variation.get('confidence', 0.0)
    
    # Detect hallucination patterns
    patterns = detect_hallucination_patterns(variation)
    
    # Calculate quality score (simple heuristic)
    quality_score = confidence
    
    # Penalize for patterns
    pattern_penalty = len(patterns) * 0.1
    quality_score = max(0.0, quality_score - pattern_penalty)
    
    # Determine if variation passes quality check
    passes_quality = (
        quality_score >= thresholds.min_quality_score and
        len(patterns) == 0
    )
    
    return {
        'quality_score': quality_score,
        'passes_quality': passes_quality,
        'hallucination_patterns': patterns,
        'confidence': confidence,
        'flags': patterns
    }


def check_close_competition(scores: List[Any], 
                          threshold: float = 0.05) -> bool:
    """
    Check if multiple variations have very close scores (close competition).
    
    Args:
        scores: List of variation scores
        threshold: Maximum difference for close competition
        
    Returns:
        bool: True if close competition detected
    """
    if len(scores) < 2:
        return False
    
    # Extract final scores
    final_scores = []
    for score in scores:
        if hasattr(score, 'final_score'):
            final_scores.append(score.final_score)
        elif isinstance(score, dict):
            final_scores.append(score.get('final_score', 0.0))
        else:
            final_scores.append(float(score))
    
    if not final_scores:
        return False
    
    # Sort scores in descending order
    sorted_scores = sorted(final_scores, reverse=True)
    
    # Check if top scores are very close
    if len(sorted_scores) >= 2:
        top_diff = sorted_scores[0] - sorted_scores[1]
        return top_diff <= threshold
    
    return False


def flag_for_manual_review(variations: List[Dict[str, Any]], 
                         scores: List[Any] = None,
                         reason: str = 'quality_concern') -> Dict[str, Any]:
    """
    Flag variations for manual review with detailed reasoning.
    
    Args:
        variations: List of text variations
        scores: Optional variation scores
        reason: Reason for flagging
        
    Returns:
        Dict: Review flag information
    """
    return {
        'action': 'flag_for_review',
        'reason': reason,
        'variation_count': len(variations),
        'requires_human_review': True,
        'confidence_level': 'low',
        'recommended_action': 'manual_inspection',
        'metadata': {
            'flagged_variations': len(variations),
            'primary_concern': reason,
            'review_priority': 'high' if reason in ['hallucination_detected', 'quality_failure'] else 'medium'
        }
    }
# src/compareblocks/consensus/policy.py
"""
Decision policy engine for consensus decisions.
Implements pick/merge/review threshold logic with decision tree.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .score import VariationScore
from .guard import HallucinationGuard, GuardDecision


class DecisionAction(Enum):
    """Possible decision actions."""
    PICK = "pick"
    MERGE = "merge"  
    REVIEW = "review"
    REJECT = "reject"


@dataclass
class PolicyThresholds:
    """Configurable thresholds for decision policy."""
    clear_winner_threshold: float = 0.15  # Score difference for clear winner
    merge_candidate_threshold: float = 0.05  # Score difference for merge candidates
    min_acceptable_score: float = 0.2  # Minimum score to consider
    high_confidence_threshold: float = 0.7  # High confidence threshold
    merge_similarity_threshold: float = 0.8  # Text similarity for merging


@dataclass
class ConsensusDecision:
    """Complete consensus decision with reasoning."""
    action: DecisionAction
    selected_text: Optional[str]
    selected_engine: Optional[str]
    decision_reason: str
    confidence_score: float
    engine_scores: Dict[str, float]
    anomaly_score: float
    merge_candidates: List[VariationScore]
    flags: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'action': self.action.value,
            'selected_text': self.selected_text,
            'selected_engine': self.selected_engine,
            'decision_reason': self.decision_reason,
            'confidence_score': self.confidence_score,
            'engine_scores': self.engine_scores,
            'anomaly_score': self.anomaly_score,
            'merge_candidates': [candidate.to_dict() for candidate in self.merge_candidates],
            'flags': self.flags,
            'metadata': self.metadata
        }


class DecisionPolicyEngine:
    """Implements decision policy for consensus selection."""
    
    def __init__(self, guard: Optional[HallucinationGuard] = None,
                 policy_thresholds: Optional[PolicyThresholds] = None):
        """
        Initialize the decision policy engine.
        
        Args:
            guard: HallucinationGuard instance (creates default if None)
            policy_thresholds: Policy thresholds configuration
        """
        self.guard = guard if guard else HallucinationGuard()
        self.policy_thresholds = policy_thresholds if policy_thresholds else PolicyThresholds()
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        # Simple character-level similarity
        if text1 == text2:
            return 1.0
        
        # Use difflib for sequence matching
        import difflib
        matcher = difflib.SequenceMatcher(None, text1, text2)
        return matcher.ratio()
    
    def _identify_merge_candidates(self, scores: List[VariationScore]) -> List[VariationScore]:
        """
        Identify variations that are candidates for merging.
        
        Args:
            scores: List of VariationScore objects
            
        Returns:
            List of merge candidate scores
        """
        if len(scores) < 2:
            return []
        
        # Filter variations that meet minimum score threshold
        acceptable_scores = [
            score for score in scores 
            if score.final_score >= self.policy_thresholds.min_acceptable_score
        ]
        
        if len(acceptable_scores) < 2:
            return []
        
        # Sort by score (best first)
        sorted_scores = sorted(acceptable_scores, key=lambda x: x.final_score, reverse=True)
        
        # Check if top variations have similar scores
        best_score = sorted_scores[0].final_score
        merge_candidates = []
        
        for score in sorted_scores:
            score_diff = best_score - score.final_score
            if score_diff <= self.policy_thresholds.merge_candidate_threshold:
                merge_candidates.append(score)
            else:
                break  # Scores are sorted, so we can stop here
        
        # Only return candidates if we have multiple similar scores
        return merge_candidates if len(merge_candidates) > 1 else []
    
    def _check_for_clear_winner(self, scores: List[VariationScore]) -> Optional[VariationScore]:
        """
        Check if there's a clear winner among variations.
        
        Args:
            scores: List of VariationScore objects
            
        Returns:
            Clear winner VariationScore or None
        """
        if len(scores) < 2:
            return scores[0] if scores else None
        
        # Sort by score (best first)
        sorted_scores = sorted(scores, key=lambda x: x.final_score, reverse=True)
        
        best_score = sorted_scores[0]
        second_best_score = sorted_scores[1]
        
        # Check if best score is significantly higher
        score_difference = best_score.final_score - second_best_score.final_score
        
        if (score_difference >= self.policy_thresholds.clear_winner_threshold and
            best_score.final_score >= self.policy_thresholds.min_acceptable_score):
            return best_score
        
        return None
    
    def _should_merge_variations(self, candidates: List[VariationScore]) -> bool:
        """
        Determine if variations should be merged.
        
        Args:
            candidates: List of merge candidate scores
            
        Returns:
            True if variations should be merged
        """
        if len(candidates) < 2:
            return False
        
        # Check text similarity between candidates
        texts = [candidate.raw_text for candidate in candidates]
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                similarity = self._calculate_text_similarity(texts[i], texts[j])
                similarities.append(similarity)
        
        if not similarities:
            return False
        
        # Check if average similarity is above threshold
        avg_similarity = sum(similarities) / len(similarities)
        return avg_similarity >= self.policy_thresholds.merge_similarity_threshold
    
    def make_decision(self, variations: List[Dict[str, Any]], 
                     context_texts: Optional[List[str]] = None) -> ConsensusDecision:
        """
        Make a consensus decision for the given variations.
        
        Args:
            variations: List of variation dictionaries
            context_texts: Optional context texts for similarity scoring
            
        Returns:
            ConsensusDecision with action and reasoning
        """
        # First, let the hallucination guard evaluate
        guard_decision = self.guard.evaluate_variations(variations, context_texts)
        
        # Extract basic information
        scores = guard_decision.all_scores
        engine_scores = {score.engine_name: score.final_score for score in scores}
        
        # Calculate overall anomaly score (average of all variations)
        avg_anomaly_score = sum(score.anomaly_score for score in scores) / len(scores) if scores else 1.0
        
        # Handle guard decisions that prevent auto-selection
        if guard_decision.action in ['flag_for_review', 'reject_all']:
            return ConsensusDecision(
                action=DecisionAction.REVIEW if guard_decision.action == 'flag_for_review' else DecisionAction.REJECT,
                selected_text=None,
                selected_engine=None,
                decision_reason=f"hallucination_guard_{guard_decision.reason}",
                confidence_score=guard_decision.confidence,
                engine_scores=engine_scores,
                anomaly_score=avg_anomaly_score,
                merge_candidates=[],
                flags=guard_decision.flags,
                metadata={
                    'guard_decision': guard_decision.to_dict(),
                    'total_variations': len(variations)
                }
            )
        
        # Guard approved auto-selection, now apply policy logic
        
        # Check for clear winner
        clear_winner = self._check_for_clear_winner(scores)
        
        if clear_winner:
            return ConsensusDecision(
                action=DecisionAction.PICK,
                selected_text=clear_winner.raw_text,
                selected_engine=clear_winner.engine_name,
                decision_reason="highest_score",
                confidence_score=guard_decision.confidence,
                engine_scores=engine_scores,
                anomaly_score=avg_anomaly_score,
                merge_candidates=[],
                flags=clear_winner.flags,
                metadata={
                    'score_difference': clear_winner.final_score - (sorted(scores, key=lambda x: x.final_score, reverse=True)[1].final_score if len(scores) > 1 else 0),
                    'winner_score': clear_winner.final_score
                }
            )
        
        # Check for merge candidates
        merge_candidates = self._identify_merge_candidates(scores)
        
        if merge_candidates and self._should_merge_variations(merge_candidates):
            # Select the best candidate as the base for merging
            best_candidate = max(merge_candidates, key=lambda x: x.final_score)
            
            return ConsensusDecision(
                action=DecisionAction.MERGE,
                selected_text=best_candidate.raw_text,  # Base text for merging
                selected_engine=best_candidate.engine_name,
                decision_reason="merged_result",
                confidence_score=guard_decision.confidence * 0.8,  # Slightly lower confidence for merges
                engine_scores=engine_scores,
                anomaly_score=avg_anomaly_score,
                merge_candidates=merge_candidates,
                flags=['merge_required'],
                metadata={
                    'merge_candidate_count': len(merge_candidates),
                    'avg_candidate_score': sum(c.final_score for c in merge_candidates) / len(merge_candidates),
                    'text_similarity': self._calculate_text_similarity(
                        merge_candidates[0].raw_text, 
                        merge_candidates[1].raw_text
                    ) if len(merge_candidates) >= 2 else 0.0
                }
            )
        
        # No clear winner and no good merge candidates - flag for review
        best_available = max(scores, key=lambda x: x.final_score) if scores else None
        
        return ConsensusDecision(
            action=DecisionAction.REVIEW,
            selected_text=best_available.raw_text if best_available else None,
            selected_engine=best_available.engine_name if best_available else None,
            decision_reason="flagged_review",
            confidence_score=0.5,  # Low confidence when flagging for review
            engine_scores=engine_scores,
            anomaly_score=avg_anomaly_score,
            merge_candidates=merge_candidates,
            flags=['requires_manual_review'],
            metadata={
                'reason_details': 'no_clear_winner_and_no_merge_candidates',
                'best_available_score': best_available.final_score if best_available else 0.0,
                'score_variance': max(engine_scores.values()) - min(engine_scores.values()) if engine_scores else 0.0
            }
        )
    
    def batch_decisions(self, variation_batches: List[List[Dict[str, Any]]], 
                       context_texts: Optional[List[str]] = None) -> List[ConsensusDecision]:
        """
        Make decisions for multiple batches of variations.
        
        Args:
            variation_batches: List of variation lists (one per block)
            context_texts: Optional context texts for similarity scoring
            
        Returns:
            List of ConsensusDecision objects
        """
        decisions = []
        
        for variations in variation_batches:
            decision = self.make_decision(variations, context_texts)
            decisions.append(decision)
        
        return decisions
    
    def get_decision_statistics(self, decisions: List[ConsensusDecision]) -> Dict[str, Any]:
        """
        Get statistics for a set of decisions.
        
        Args:
            decisions: List of ConsensusDecision objects
            
        Returns:
            Dictionary with decision statistics
        """
        if not decisions:
            return {
                'total_decisions': 0,
                'action_counts': {},
                'avg_confidence': 0.0,
                'manual_review_rate': 0.0,
                'auto_selection_rate': 0.0,
                'merge_rate': 0.0
            }
        
        # Count actions
        action_counts = {}
        for decision in decisions:
            action = decision.action.value
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Calculate rates
        total = len(decisions)
        manual_review_rate = action_counts.get('review', 0) / total
        auto_selection_rate = action_counts.get('pick', 0) / total
        merge_rate = action_counts.get('merge', 0) / total
        
        # Calculate average confidence
        confidences = [d.confidence_score for d in decisions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'total_decisions': total,
            'action_counts': action_counts,
            'avg_confidence': avg_confidence,
            'manual_review_rate': manual_review_rate,
            'auto_selection_rate': auto_selection_rate,
            'merge_rate': merge_rate,
            'confidence_distribution': {
                'high_confidence': sum(1 for c in confidences if c >= 0.7),
                'medium_confidence': sum(1 for c in confidences if 0.3 <= c < 0.7),
                'low_confidence': sum(1 for c in confidences if c < 0.3)
            }
        }
    
    def update_policy_thresholds(self, new_thresholds: PolicyThresholds) -> None:
        """Update policy thresholds."""
        self.policy_thresholds = new_thresholds
    
    def get_policy_configuration(self) -> Dict[str, Any]:
        """Get current policy configuration."""
        return {
            'policy_thresholds': {
                'clear_winner_threshold': self.policy_thresholds.clear_winner_threshold,
                'merge_candidate_threshold': self.policy_thresholds.merge_candidate_threshold,
                'min_acceptable_score': self.policy_thresholds.min_acceptable_score,
                'high_confidence_threshold': self.policy_thresholds.high_confidence_threshold,
                'merge_similarity_threshold': self.policy_thresholds.merge_similarity_threshold
            },
            'guard_configuration': self.guard.get_guard_configuration()
        }
def create_default_policy_thresholds() -> PolicyThresholds:
    """
    Create default policy thresholds for decision making.
    
    Returns:
        PolicyThresholds: Default threshold configuration
    """
    return PolicyThresholds()


def create_conservative_policy_thresholds() -> PolicyThresholds:
    """
    Create conservative policy thresholds that favor manual review.
    
    Returns:
        PolicyThresholds: Conservative threshold configuration
    """
    return PolicyThresholds(
        auto_pick_threshold=0.8,
        merge_similarity_threshold=0.95,
        review_threshold=0.6,
        min_confidence_gap=0.15
    )


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two text strings.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        float: Similarity score (0.0 to 1.0)
    """
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    
    # Simple character-based similarity
    if text1 == text2:
        return 1.0
    
    # Calculate Jaccard similarity on character level
    set1 = set(text1.lower())
    set2 = set(text2.lower())
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0


def identify_merge_candidates(variations: List[Dict[str, Any]], 
                            similarity_threshold: float = 0.85) -> List[Tuple[int, int]]:
    """
    Identify pairs of variations that are candidates for merging.
    
    Args:
        variations: List of text variations
        similarity_threshold: Minimum similarity for merge candidacy
        
    Returns:
        List[Tuple[int, int]]: Pairs of variation indices that could be merged
    """
    candidates = []
    
    for i in range(len(variations)):
        for j in range(i + 1, len(variations)):
            text1 = variations[i].get('text', '')
            text2 = variations[j].get('text', '')
            
            similarity = calculate_text_similarity(text1, text2)
            if similarity >= similarity_threshold:
                candidates.append((i, j))
    
    return candidates


def should_merge_variations(variations: List[Dict[str, Any]], 
                          scores: List[Any] = None,
                          threshold: float = 0.85) -> bool:
    """
    Determine if variations should be merged based on similarity.
    
    Args:
        variations: List of text variations
        scores: Optional variation scores
        threshold: Similarity threshold for merging
        
    Returns:
        bool: True if variations should be merged
    """
    if len(variations) < 2:
        return False
    
    merge_candidates = identify_merge_candidates(variations, threshold)
    return len(merge_candidates) > 0


def make_consensus_decision(variations: List[Dict[str, Any]], 
                          scores: List[Any] = None,
                          thresholds: PolicyThresholds = None) -> ConsensusDecision:
    """
    Make a consensus decision for a set of variations.
    
    Args:
        variations: List of text variations
        scores: Optional variation scores
        thresholds: Policy thresholds (uses defaults if None)
        
    Returns:
        ConsensusDecision: Decision result
    """
    if thresholds is None:
        thresholds = create_default_policy_thresholds()
    
    if not variations:
        return ConsensusDecision(
            action=DecisionAction.REJECT,
            selected_text=None,
            selected_engine=None,
            decision_reason='no_variations_provided',
            confidence_score=0.0,
            engine_scores={},
            anomaly_score=1.0,
            merge_candidates=[],
            flags=['no_input'],
            metadata={}
        )
    
    if len(variations) == 1:
        variation = variations[0]
        return ConsensusDecision(
            action=DecisionAction.PICK,
            selected_text=variation.get('text', ''),
            selected_engine=variation.get('engine', 'unknown'),
            decision_reason='single_variation_auto_pick',
            confidence_score=1.0,
            engine_scores={variation.get('engine', 'unknown'): 1.0},
            anomaly_score=0.0,
            merge_candidates=[],
            flags=[],
            metadata={'total_variations': 1}
        )
    
    # Check for merge candidates
    merge_candidates = identify_merge_candidates(variations, thresholds.merge_similarity_threshold)
    
    if merge_candidates:
        return ConsensusDecision(
            action=DecisionAction.MERGE,
            selected_text=None,
            selected_engine=None,
            decision_reason='merge_candidates_identified',
            confidence_score=0.8,
            engine_scores={v.get('engine', f'engine_{i}'): 0.8 for i, v in enumerate(variations)},
            anomaly_score=0.2,
            merge_candidates=merge_candidates,
            flags=['merge_recommended'],
            metadata={'total_variations': len(variations)}
        )
    
    # Default to review for multiple variations without clear winner
    return ConsensusDecision(
        action=DecisionAction.REVIEW,
        selected_text=None,
        selected_engine=None,
        decision_reason='multiple_variations_require_review',
        confidence_score=0.5,
        engine_scores={v.get('engine', f'engine_{i}'): 0.5 for i, v in enumerate(variations)},
        anomaly_score=0.5,
        merge_candidates=[],
        flags=['manual_review_required'],
        metadata={'total_variations': len(variations)}
    )


def batch_consensus_decisions(variation_batches: List[List[Dict[str, Any]]], 
                            thresholds: PolicyThresholds = None) -> List[ConsensusDecision]:
    """
    Make consensus decisions for multiple batches of variations.
    
    Args:
        variation_batches: List of variation lists
        thresholds: Policy thresholds (uses defaults if None)
        
    Returns:
        List[ConsensusDecision]: Decision results for each batch
    """
    decisions = []
    for batch in variation_batches:
        decision = make_consensus_decision(batch, thresholds=thresholds)
        decisions.append(decision)
    return decisions


def get_decision_statistics(decisions: List[ConsensusDecision]) -> Dict[str, Any]:
    """
    Calculate statistics for a set of consensus decisions.
    
    Args:
        decisions: List of consensus decisions
        
    Returns:
        Dict: Statistics about decision patterns
    """
    if not decisions:
        return {
            'total_decisions': 0,
            'pick_count': 0,
            'merge_count': 0,
            'review_count': 0,
            'reject_count': 0,
            'average_confidence': 0.0
        }
    
    action_counts = {}
    for decision in decisions:
        action = decision.action.value
        action_counts[action] = action_counts.get(action, 0) + 1
    
    confidences = [d.confidence_score for d in decisions]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    return {
        'total_decisions': len(decisions),
        'pick_count': action_counts.get('pick', 0),
        'merge_count': action_counts.get('merge', 0),
        'review_count': action_counts.get('review', 0),
        'reject_count': action_counts.get('reject', 0),
        'average_confidence': avg_confidence,
        'action_percentages': {
            action: (count / len(decisions)) * 100.0 
            for action, count in action_counts.items()
        }
    }
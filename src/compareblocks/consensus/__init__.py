# src/compareblocks/consensus/__init__.py
"""
Consensus scoring and decision making module.
Provides weighted scoring, hallucination guards, and decision policies.
"""

from .score import (
    ConsensusScorer,
    ScoringWeights,
    ScoringThresholds,
    VariationScore
)

from .guard import (
    HallucinationGuard,
    GuardThresholds,
    GuardDecision
)

from .policy import (
    DecisionPolicyEngine,
    PolicyThresholds,
    ConsensusDecision,
    DecisionAction
)

from .merge import (
    TokenLevelMerger,
    MergeStrategy,
    MergeResult,
    TokenAlignment
)

__all__ = [
    'ConsensusScorer',
    'ScoringWeights', 
    'ScoringThresholds',
    'VariationScore',
    'HallucinationGuard',
    'GuardThresholds',
    'GuardDecision',
    'DecisionPolicyEngine',
    'PolicyThresholds',
    'ConsensusDecision',
    'DecisionAction',
    'TokenLevelMerger',
    'MergeStrategy',
    'MergeResult',
    'TokenAlignment'
]
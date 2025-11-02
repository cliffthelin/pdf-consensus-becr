# src/compareblocks/tracking/__init__.py
"""
Change tracking and source attribution system.
Tracks block-level changes, maintains source attribution, and provides ranking capabilities.
"""

from .change_tracker import (
    ChangeTracker,
    BlockChange,
    ChangeHistory,
    SourceAttribution,
    ChangeType
)
from .source_ranker import (
    SourceRanker,
    SourceRanking,
    AccuracyMetrics,
    rank_sources_by_accuracy,
    get_best_source
)
from .propagation import (
    ChangePropagationDetector,
    PropagationResult,
    PropagationChain,
    detect_change_propagation,
    build_neighbor_map
)

__all__ = [
    'ChangeTracker',
    'BlockChange',
    'ChangeHistory',
    'SourceAttribution',
    'ChangeType',
    'SourceRanker',
    'SourceRanking',
    'AccuracyMetrics',
    'rank_sources_by_accuracy',
    'get_best_source',
    'ChangePropagationDetector',
    'PropagationResult',
    'PropagationChain',
    'detect_change_propagation',
    'build_neighbor_map'
]

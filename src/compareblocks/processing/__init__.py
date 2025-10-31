# src/compareblocks/processing/__init__.py
"""
Processing module for BECR system.

Provides dynamic reprocessing capabilities including:
- Rebuilding all comparisons vs. adding only new ones
- Incremental processing when new associated files are added
- Reprocessing triggers that update consistency percentages
- Version tracking for processing different configurations
"""

from .dynamic_reprocessor import (
    DynamicReprocessor,
    ProcessingMode,
    VersionStorageMode,
    ProcessingVersion,
    ReprocessingTrigger,
    IncrementalUpdate,
    rebuild_all_comparisons,
    incremental_processing_for_new_files,
    update_consistency_percentages,
    detect_reprocessing_needs
)

__all__ = [
    'DynamicReprocessor',
    'ProcessingMode',
    'VersionStorageMode',
    'ProcessingVersion',
    'ReprocessingTrigger',
    'IncrementalUpdate',
    'rebuild_all_comparisons',
    'incremental_processing_for_new_files',
    'update_consistency_percentages',
    'detect_reprocessing_needs'
]
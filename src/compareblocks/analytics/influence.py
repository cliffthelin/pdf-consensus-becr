# src/compareblocks/analytics/influence.py
"""
Influence percentage calculation and analytics integration.

Calculates how much each extraction engine contributes to the final consensus output,
tracks consensus outputs and exports, and provides real-time analytics updates.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from collections import Counter, defaultdict

from ..consensus.policy import ConsensusDecision, DecisionAction
from ..config.file_manager import file_manager


@dataclass
class InfluenceMetrics:
    """Metrics showing engine influence on consensus decisions."""
    
    engine_percentages: Dict[str, float]  # Percentage contribution per engine
    total_blocks: int  # Total number of blocks processed
    consensus_blocks: int  # Blocks with consensus decisions
    manual_override_blocks: int  # Blocks with manual overrides
    flagged_blocks: int  # Blocks flagged for review
    engine_selection_counts: Dict[str, int]  # Raw selection counts per engine
    weighted_scores: Dict[str, float]  # Average weighted scores per engine
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)
    
    def get_top_engine(self) -> Optional[str]:
        """Get the engine with highest influence."""
        if not self.engine_percentages:
            return None
        return max(self.engine_percentages.items(), key=lambda x: x[1])[0]
    
    def get_engine_rank(self, engine_name: str) -> int:
        """Get the rank of an engine (1-based)."""
        sorted_engines = sorted(
            self.engine_percentages.items(),
            key=lambda x: x[1],
            reverse=True
        )
        for rank, (name, _) in enumerate(sorted_engines, 1):
            if name == engine_name:
                return rank
        return -1


class InfluenceCalculator:
    """Calculates influence percentages for extraction engines."""
    
    def __init__(self, use_score_weights: bool = True, 
                 include_manual_overrides: bool = True):
        """
        Initialize influence calculator.
        
        Args:
            use_score_weights: Whether to weight influence by consensus scores
            include_manual_overrides: Whether to include manual overrides in calculation
        """
        self.use_score_weights = use_score_weights
        self.include_manual_overrides = include_manual_overrides
    
    def calculate_influence(self, decisions: List[ConsensusDecision]) -> InfluenceMetrics:
        """
        Calculate influence percentages from consensus decisions.
        
        Args:
            decisions: List of consensus decisions
            
        Returns:
            InfluenceMetrics with calculated percentages
        """
        if not decisions:
            return InfluenceMetrics(
                engine_percentages={},
                total_blocks=0,
                consensus_blocks=0,
                manual_override_blocks=0,
                flagged_blocks=0,
                engine_selection_counts={},
                weighted_scores={}
            )
        
        # Filter decisions if needed
        filtered_decisions = self._filter_decisions(decisions)
        
        # Count selections and calculate weights
        engine_data = defaultdict(lambda: {
            'count': 0,
            'weighted_score': 0.0,
            'total_weight': 0.0
        })
        
        for decision in filtered_decisions:
            engine = decision.selected_engine
            score = decision.confidence_score if self.use_score_weights else 1.0
            
            engine_data[engine]['count'] += 1
            engine_data[engine]['weighted_score'] += score
            engine_data[engine]['total_weight'] += score
        
        # Calculate percentages
        if self.use_score_weights:
            total_weight = sum(data['total_weight'] for data in engine_data.values())
            engine_percentages = {
                engine: (data['total_weight'] / total_weight * 100.0) if total_weight > 0 else 0.0
                for engine, data in engine_data.items()
            }
        else:
            total_count = sum(data['count'] for data in engine_data.values())
            engine_percentages = {
                engine: (data['count'] / total_count * 100.0) if total_count > 0 else 0.0
                for engine, data in engine_data.items()
            }
        
        # Calculate average weighted scores
        weighted_scores = {
            engine: (data['weighted_score'] / data['count']) if data['count'] > 0 else 0.0
            for engine, data in engine_data.items()
        }
        
        # Count selection counts
        selection_counts = {
            engine: data['count']
            for engine, data in engine_data.items()
        }
        
        # Count special blocks
        manual_override_blocks = sum(
            1 for d in decisions
            if 'manual_override' in d.flags
        )
        
        flagged_blocks = sum(
            1 for d in decisions
            if d.action == DecisionAction.REVIEW or len(d.flags) > 0
        )
        
        return InfluenceMetrics(
            engine_percentages=engine_percentages,
            total_blocks=len(decisions),
            consensus_blocks=len(filtered_decisions),
            manual_override_blocks=manual_override_blocks,
            flagged_blocks=flagged_blocks,
            engine_selection_counts=selection_counts,
            weighted_scores=weighted_scores
        )
    
    def _filter_decisions(self, decisions: List[ConsensusDecision]) -> List[ConsensusDecision]:
        """Filter decisions based on calculator settings."""
        if self.include_manual_overrides:
            return decisions
        
        # Exclude manual overrides
        return [
            d for d in decisions
            if 'manual_override' not in d.flags
        ]


class ConsensusOutputTracker:
    """Tracks consensus output files and exports."""
    
    def __init__(self):
        """Initialize consensus output tracker."""
        self.tracked_outputs: Dict[str, Dict[str, Any]] = {}
        self.tracking_file = Path(file_manager.get_processing_directory()) / "consensus_tracking.json"
        self._load_tracking()
    
    def track_output(self, pdf_path: str, consensus_file: Path):
        """
        Track a consensus output file.
        
        Args:
            pdf_path: Path to root PDF
            consensus_file: Path to consensus output file
        """
        if pdf_path not in self.tracked_outputs:
            self.tracked_outputs[pdf_path] = {
                "consensus_file": None,
                "export_files": [],
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        
        self.tracked_outputs[pdf_path]["consensus_file"] = str(consensus_file)
        self.tracked_outputs[pdf_path]["last_updated"] = datetime.now().isoformat()
        self._save_tracking()
    
    def track_exports(self, pdf_path: str, export_files: List[Path]):
        """
        Track consensus export files.
        
        Args:
            pdf_path: Path to root PDF
            export_files: List of export file paths
        """
        if pdf_path not in self.tracked_outputs:
            self.tracked_outputs[pdf_path] = {
                "consensus_file": None,
                "export_files": [],
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        
        self.tracked_outputs[pdf_path]["export_files"] = [str(f) for f in export_files]
        self.tracked_outputs[pdf_path]["last_updated"] = datetime.now().isoformat()
        self._save_tracking()
    
    def get_tracked_output(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """
        Get tracked output for a PDF.
        
        Args:
            pdf_path: Path to root PDF
            
        Returns:
            Tracked output data or None
        """
        return self.tracked_outputs.get(pdf_path)
    
    def get_all_tracked_outputs(self) -> Dict[str, Dict[str, Any]]:
        """Get all tracked outputs."""
        return self.tracked_outputs.copy()
    
    def _load_tracking(self):
        """Load tracking data from file."""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    self.tracked_outputs = json.load(f)
            except Exception:
                self.tracked_outputs = {}
    
    def _save_tracking(self):
        """Save tracking data to file."""
        try:
            self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(self.tracked_outputs, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # Fail silently for tracking


class InfluenceAnalyticsManager:
    """Manages influence analytics with versioning and real-time updates."""
    
    def __init__(self):
        """Initialize influence analytics manager."""
        self.calculator = InfluenceCalculator()
        self.output_tracker = ConsensusOutputTracker()
        self.analytics_history: Dict[str, List[Dict[str, Any]]] = {}
        self.history_file = Path(file_manager.get_processing_directory()) / "influence_history.json"
        self._load_history()
    
    def update_analytics(self, pdf_path: str, decisions: List[ConsensusDecision]) -> Dict[str, Any]:
        """
        Update analytics for a PDF with new consensus decisions.
        
        Args:
            pdf_path: Path to root PDF
            decisions: List of consensus decisions
            
        Returns:
            Updated analytics data with version
        """
        # Calculate influence
        influence = self.calculator.calculate_influence(decisions)
        
        # Create analytics record
        analytics_record = {
            "pdf_path": pdf_path,
            "influence_metrics": influence.to_dict(),
            "timestamp": datetime.now().isoformat(),
            "version": self._get_next_version(pdf_path),
            "decision_count": len(decisions)
        }
        
        # Add to history
        if pdf_path not in self.analytics_history:
            self.analytics_history[pdf_path] = []
        self.analytics_history[pdf_path].append(analytics_record)
        
        # Save history
        self._save_history()
        
        return analytics_record
    
    def get_latest_analytics(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """
        Get latest analytics for a PDF.
        
        Args:
            pdf_path: Path to root PDF
            
        Returns:
            Latest analytics record or None
        """
        history = self.analytics_history.get(pdf_path, [])
        return history[-1] if history else None
    
    def get_analytics_history(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Get full analytics history for a PDF.
        
        Args:
            pdf_path: Path to root PDF
            
        Returns:
            List of analytics records
        """
        return self.analytics_history.get(pdf_path, []).copy()
    
    def compare_versions(self, pdf_path: str, version1: int, version2: int) -> Dict[str, Any]:
        """
        Compare two versions of analytics.
        
        Args:
            pdf_path: Path to root PDF
            version1: First version number
            version2: Second version number
            
        Returns:
            Comparison data
        """
        history = self.analytics_history.get(pdf_path, [])
        
        if version1 < 1 or version2 < 1 or version1 > len(history) or version2 > len(history):
            return {"error": "Invalid version numbers"}
        
        record1 = history[version1 - 1]
        record2 = history[version2 - 1]
        
        metrics1 = InfluenceMetrics(**record1["influence_metrics"])
        metrics2 = InfluenceMetrics(**record2["influence_metrics"])
        
        # Calculate differences
        percentage_changes = {}
        for engine in set(list(metrics1.engine_percentages.keys()) + list(metrics2.engine_percentages.keys())):
            old_pct = metrics1.engine_percentages.get(engine, 0.0)
            new_pct = metrics2.engine_percentages.get(engine, 0.0)
            percentage_changes[engine] = new_pct - old_pct
        
        return {
            "pdf_path": pdf_path,
            "version1": version1,
            "version2": version2,
            "timestamp1": record1["timestamp"],
            "timestamp2": record2["timestamp"],
            "percentage_changes": percentage_changes,
            "block_count_change": metrics2.total_blocks - metrics1.total_blocks,
            "consensus_block_change": metrics2.consensus_blocks - metrics1.consensus_blocks
        }
    
    def _get_next_version(self, pdf_path: str) -> int:
        """Get next version number for a PDF."""
        history = self.analytics_history.get(pdf_path, [])
        return len(history) + 1
    
    def _load_history(self):
        """Load analytics history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.analytics_history = json.load(f)
            except Exception:
                self.analytics_history = {}
    
    def _save_history(self):
        """Save analytics history to file."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.analytics_history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # Fail silently for history


# Convenience functions

def calculate_influence_percentages(decisions: List[ConsensusDecision],
                                   use_score_weights: bool = True,
                                   include_manual_overrides: bool = True) -> InfluenceMetrics:
    """
    Convenience function to calculate influence percentages.
    
    Args:
        decisions: List of consensus decisions
        use_score_weights: Whether to weight by consensus scores
        include_manual_overrides: Whether to include manual overrides
        
    Returns:
        InfluenceMetrics with calculated percentages
    """
    calculator = InfluenceCalculator(use_score_weights, include_manual_overrides)
    return calculator.calculate_influence(decisions)


def track_consensus_contribution(pdf_path: str, decisions: List[ConsensusDecision]) -> Dict[str, Any]:
    """
    Convenience function to track consensus contribution.
    
    Args:
        pdf_path: Path to root PDF
        decisions: List of consensus decisions
        
    Returns:
        Tracking result with influence metrics
    """
    manager = InfluenceAnalyticsManager()
    return manager.update_analytics(pdf_path, decisions)


def get_consensus_outputs(pdf_path: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get consensus outputs for a PDF.
    
    Args:
        pdf_path: Path to root PDF
        
    Returns:
        Consensus output data or None
    """
    tracker = ConsensusOutputTracker()
    return tracker.get_tracked_output(pdf_path)

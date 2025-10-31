# src/compareblocks/features/core.py
"""
Core feature extraction for text variations including length and line statistics.
Provides fundamental metrics for consensus scoring and quality assessment.
"""

import statistics
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class LengthFeatures:
    """Core length and line statistics for text variations."""
    len_no_spaces: int
    len_with_spaces: int
    line_count: int
    avg_line_len: float
    line_len_std: float
    consistency_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert features to dictionary format."""
        return {
            'len_no_spaces': self.len_no_spaces,
            'len_with_spaces': self.len_with_spaces,
            'line_count': self.line_count,
            'avg_line_len': self.avg_line_len,
            'line_len_std': self.line_len_std,
            'consistency_score': self.consistency_score
        }


class CoreFeatureExtractor:
    """Extracts core length and line features from text variations."""
    
    def __init__(self):
        """Initialize the core feature extractor."""
        pass
    
    def extract_length_features(self, text: str) -> LengthFeatures:
        """
        Extract length and line features from a single text variation.
        
        Args:
            text: The text to analyze
            
        Returns:
            LengthFeatures object with computed metrics
        """
        if not text:
            return LengthFeatures(
                len_no_spaces=0,
                len_with_spaces=0,
                line_count=0,
                avg_line_len=0.0,
                line_len_std=0.0,
                consistency_score=0.0
            )
        
        # Basic length metrics
        len_with_spaces = len(text)
        len_no_spaces = len(text.replace(' ', '').replace('\t', '').replace('\n', ''))
        
        # Line statistics
        lines = text.split('\n')
        line_count = len(lines)
        
        # Calculate line lengths (excluding empty lines for statistics)
        line_lengths = [len(line.strip()) for line in lines if line.strip()]
        
        if line_lengths:
            avg_line_len = statistics.mean(line_lengths)
            line_len_std = statistics.stdev(line_lengths) if len(line_lengths) > 1 else 0.0
        else:
            avg_line_len = 0.0
            line_len_std = 0.0
        
        # Initial consistency score (will be updated by compute_consistency_score)
        consistency_score = 1.0
        
        return LengthFeatures(
            len_no_spaces=len_no_spaces,
            len_with_spaces=len_with_spaces,
            line_count=line_count,
            avg_line_len=avg_line_len,
            line_len_std=line_len_std,
            consistency_score=consistency_score
        )
    
    def compute_consistency_score(self, variations: List[str]) -> Dict[str, float]:
        """
        Compute length consistency scores for variations based on median length.
        
        Args:
            variations: List of text variations to compare
            
        Returns:
            Dictionary mapping variation index to consistency score
        """
        if not variations:
            return {}
        
        # Extract lengths for all variations
        lengths = []
        for text in variations:
            if text:
                lengths.append(len(text.replace(' ', '').replace('\t', '').replace('\n', '')))
            else:
                lengths.append(0)
        
        if not lengths:
            return {str(i): 0.0 for i in range(len(variations))}
        
        # Calculate median length
        median_length = statistics.median(lengths)
        
        # Compute consistency scores
        consistency_scores = {}
        for i, length in enumerate(lengths):
            if median_length == 0:
                score = 1.0 if length == 0 else 0.0
            else:
                # Score based on deviation from median (closer to median = higher score)
                deviation = abs(length - median_length) / median_length
                score = max(0.0, 1.0 - deviation)
            
            consistency_scores[str(i)] = score
        
        return consistency_scores
    
    def extract_features_for_variations(self, variations: List[str]) -> List[LengthFeatures]:
        """
        Extract features for multiple variations and compute consistency scores.
        
        Args:
            variations: List of text variations
            
        Returns:
            List of LengthFeatures with updated consistency scores
        """
        # Extract basic features for each variation
        features_list = []
        for text in variations:
            features = self.extract_length_features(text)
            features_list.append(features)
        
        # Compute consistency scores
        consistency_scores = self.compute_consistency_score(variations)
        
        # Update features with consistency scores
        for i, features in enumerate(features_list):
            features.consistency_score = consistency_scores.get(str(i), 0.0)
        
        return features_list
    
    def get_variation_statistics(self, variations: List[str]) -> Dict[str, Any]:
        """
        Get summary statistics for a set of variations.
        
        Args:
            variations: List of text variations
            
        Returns:
            Dictionary with summary statistics
        """
        if not variations:
            return {
                'total_variations': 0,
                'median_length': 0,
                'length_range': (0, 0),
                'avg_line_count': 0.0,
                'consistency_variance': 0.0
            }
        
        features_list = self.extract_features_for_variations(variations)
        
        lengths = [f.len_no_spaces for f in features_list]
        line_counts = [f.line_count for f in features_list]
        consistency_scores = [f.consistency_score for f in features_list]
        
        return {
            'total_variations': len(variations),
            'median_length': statistics.median(lengths) if lengths else 0,
            'length_range': (min(lengths), max(lengths)) if lengths else (0, 0),
            'avg_line_count': statistics.mean(line_counts) if line_counts else 0.0,
            'consistency_variance': statistics.variance(consistency_scores) if len(consistency_scores) > 1 else 0.0
        }
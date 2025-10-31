# src/compareblocks/features/anomaly.py
"""
Anomaly detection for text variations.
Identifies patterns that indicate poor OCR quality or extraction errors.
"""

import math
import re
from typing import List, Dict, Any, Counter
from dataclasses import dataclass
from collections import Counter


@dataclass
class AnomalyFeatures:
    """Anomaly detection features for text variations."""
    entropy_score: float
    repetition_score: float
    space_ratio: float
    char_per_line_ratio: float
    special_char_ratio: float
    digit_ratio: float
    anomaly_flags: List[str]
    overall_anomaly_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert features to dictionary format."""
        return {
            'entropy_score': self.entropy_score,
            'repetition_score': self.repetition_score,
            'space_ratio': self.space_ratio,
            'char_per_line_ratio': self.char_per_line_ratio,
            'special_char_ratio': self.special_char_ratio,
            'digit_ratio': self.digit_ratio,
            'anomaly_flags': self.anomaly_flags,
            'overall_anomaly_score': self.overall_anomaly_score
        }


class AnomalyDetector:
    """Detects anomalies in text that indicate poor extraction quality."""
    
    def __init__(self):
        """Initialize the anomaly detector."""
        # Thresholds for anomaly detection
        self.low_entropy_threshold = 2.0  # bits
        self.high_repetition_threshold = 0.7  # 70% repetitive
        self.extreme_space_ratio_threshold = 0.8  # 80% spaces
        self.one_char_per_line_threshold = 2.0  # average chars per line
        self.high_special_char_threshold = 0.5  # 50% special characters
        self.high_digit_ratio_threshold = 0.8  # 80% digits
    
    def calculate_entropy(self, text: str) -> float:
        """
        Calculate Shannon entropy of text.
        
        Args:
            text: Input text
            
        Returns:
            Entropy in bits
        """
        if not text:
            return 0.0
        
        # Count character frequencies
        char_counts = Counter(text)
        text_length = len(text)
        
        # Calculate entropy
        entropy = 0.0
        for count in char_counts.values():
            probability = count / text_length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def calculate_repetition_score(self, text: str) -> float:
        """
        Calculate repetition score based on repeated patterns.
        
        Args:
            text: Input text
            
        Returns:
            Repetition score (0.0 = no repetition, 1.0 = highly repetitive)
        """
        if not text or len(text) < 4:
            return 0.0
        
        # Look for repeated substrings of different lengths
        repetition_scores = []
        
        # Check for repeated 2-grams, 3-grams, and 4-grams
        for n in [2, 3, 4]:
            if len(text) < n:
                continue
                
            ngrams = []
            for i in range(len(text) - n + 1):
                ngrams.append(text[i:i+n])
            
            if not ngrams:
                continue
            
            ngram_counts = Counter(ngrams)
            total_ngrams = len(ngrams)
            unique_ngrams = len(ngram_counts)
            
            # Calculate repetition ratio for this n-gram size
            if unique_ngrams > 0:
                repetition_ratio = 1.0 - (unique_ngrams / total_ngrams)
                repetition_scores.append(repetition_ratio)
        
        # Return the maximum repetition score found
        return max(repetition_scores) if repetition_scores else 0.0
    
    def calculate_space_ratio(self, text: str) -> float:
        """
        Calculate ratio of whitespace characters to total characters.
        
        Args:
            text: Input text
            
        Returns:
            Space ratio (0.0 to 1.0)
        """
        if not text:
            return 0.0
        
        whitespace_count = sum(1 for char in text if char.isspace())
        return whitespace_count / len(text)
    
    def calculate_char_per_line_ratio(self, text: str) -> float:
        """
        Calculate average characters per line.
        
        Args:
            text: Input text
            
        Returns:
            Average characters per line
        """
        if not text:
            return 0.0
        
        lines = text.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        if not non_empty_lines:
            return 0.0
        
        total_chars = sum(len(line.strip()) for line in non_empty_lines)
        return total_chars / len(non_empty_lines)
    
    def calculate_special_char_ratio(self, text: str) -> float:
        """
        Calculate ratio of special characters (non-alphanumeric, non-space).
        
        Args:
            text: Input text
            
        Returns:
            Special character ratio (0.0 to 1.0)
        """
        if not text:
            return 0.0
        
        special_char_count = sum(1 for char in text 
                               if not char.isalnum() and not char.isspace())
        return special_char_count / len(text)
    
    def calculate_digit_ratio(self, text: str) -> float:
        """
        Calculate ratio of digit characters to total characters.
        
        Args:
            text: Input text
            
        Returns:
            Digit ratio (0.0 to 1.0)
        """
        if not text:
            return 0.0
        
        digit_count = sum(1 for char in text if char.isdigit())
        return digit_count / len(text)
    
    def detect_specific_patterns(self, text: str) -> List[str]:
        """
        Detect specific anomaly patterns in text.
        
        Args:
            text: Input text
            
        Returns:
            List of detected anomaly pattern names
        """
        flags = []
        
        if not text:
            return flags
        
        # One character per line pattern
        lines = text.split('\n')
        single_char_lines = sum(1 for line in lines if len(line.strip()) == 1)
        if len(lines) > 1 and single_char_lines / len(lines) > 0.5:
            flags.append('one_char_per_line')
        
        # Excessive punctuation
        punct_pattern = re.compile(r'[^\w\s]')
        punct_matches = len(punct_pattern.findall(text))
        if len(text) > 0 and punct_matches / len(text) > 0.3:
            flags.append('excessive_punctuation')
        
        # Repeated characters (like "aaaaaaa" or "111111")
        repeated_char_pattern = re.compile(r'(.)\1{4,}')  # 5 or more same chars
        if repeated_char_pattern.search(text):
            flags.append('repeated_characters')
        
        # All caps (might indicate OCR issues)
        alpha_chars = [c for c in text if c.isalpha()]
        if len(alpha_chars) > 10:  # Only check if substantial text
            caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if caps_ratio > 0.8:
                flags.append('excessive_caps')
        
        # Mixed scripts or unusual character combinations
        # Check for unusual character combinations that might indicate OCR errors
        unusual_patterns = [
            r'[0-9][A-Za-z][0-9]',  # digit-letter-digit
            r'[A-Za-z][0-9][A-Za-z]',  # letter-digit-letter
            r'[Il1|]{3,}',  # Common OCR confusion characters
        ]
        
        for pattern in unusual_patterns:
            if re.search(pattern, text):
                flags.append('unusual_char_patterns')
                break
        
        # Very short words (might indicate character-level OCR errors)
        words = re.findall(r'\b\w+\b', text)
        if words:
            single_char_words = sum(1 for word in words if len(word) == 1)
            if single_char_words / len(words) > 0.4:  # More than 40% single-char words
                flags.append('excessive_single_char_words')
        
        return flags
    
    def extract_anomaly_features(self, text: str) -> AnomalyFeatures:
        """
        Extract anomaly detection features from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            AnomalyFeatures object with computed metrics
        """
        if not text:
            return AnomalyFeatures(
                entropy_score=0.0,
                repetition_score=0.0,
                space_ratio=0.0,
                char_per_line_ratio=0.0,
                special_char_ratio=0.0,
                digit_ratio=0.0,
                anomaly_flags=[],
                overall_anomaly_score=1.0  # Empty text is anomalous
            )
        
        # Calculate individual metrics
        entropy_score = self.calculate_entropy(text)
        repetition_score = self.calculate_repetition_score(text)
        space_ratio = self.calculate_space_ratio(text)
        char_per_line_ratio = self.calculate_char_per_line_ratio(text)
        special_char_ratio = self.calculate_special_char_ratio(text)
        digit_ratio = self.calculate_digit_ratio(text)
        
        # Detect specific patterns
        anomaly_flags = self.detect_specific_patterns(text)
        
        # Calculate overall anomaly score
        anomaly_score = 0.0
        
        # Low entropy indicates repetitive or simple text
        if entropy_score < self.low_entropy_threshold:
            anomaly_score += 0.3
        
        # High repetition is anomalous
        if repetition_score > self.high_repetition_threshold:
            anomaly_score += 0.3
        
        # Extreme space ratios are anomalous
        if space_ratio > self.extreme_space_ratio_threshold:
            anomaly_score += 0.2
        
        # Very few characters per line (one-char-per-line pattern)
        if char_per_line_ratio < self.one_char_per_line_threshold:
            anomaly_score += 0.2
        
        # Too many special characters
        if special_char_ratio > self.high_special_char_threshold:
            anomaly_score += 0.2
        
        # Too many digits (might be OCR artifacts)
        if digit_ratio > self.high_digit_ratio_threshold:
            anomaly_score += 0.2
        
        # Add penalty for specific anomaly patterns
        anomaly_score += len(anomaly_flags) * 0.1
        
        # Normalize to 0-1 range
        overall_anomaly_score = min(1.0, anomaly_score)
        
        return AnomalyFeatures(
            entropy_score=entropy_score,
            repetition_score=repetition_score,
            space_ratio=space_ratio,
            char_per_line_ratio=char_per_line_ratio,
            special_char_ratio=special_char_ratio,
            digit_ratio=digit_ratio,
            anomaly_flags=anomaly_flags,
            overall_anomaly_score=overall_anomaly_score
        )
    
    def extract_features_for_variations(self, variations: List[str]) -> List[AnomalyFeatures]:
        """
        Extract anomaly features for multiple variations.
        
        Args:
            variations: List of text variations
            
        Returns:
            List of AnomalyFeatures
        """
        return [self.extract_anomaly_features(text) for text in variations]
    
    def get_anomaly_statistics(self, variations: List[str]) -> Dict[str, Any]:
        """
        Get anomaly statistics for a set of variations.
        
        Args:
            variations: List of text variations
            
        Returns:
            Dictionary with anomaly statistics
        """
        if not variations:
            return {
                'total_variations': 0,
                'avg_anomaly_score': 0.0,
                'max_anomaly_score': 0.0,
                'anomalous_variations': 0,
                'common_flags': {},
                'entropy_stats': {'min': 0.0, 'max': 0.0, 'avg': 0.0}
            }
        
        features_list = self.extract_features_for_variations(variations)
        
        anomaly_scores = [f.overall_anomaly_score for f in features_list]
        entropy_scores = [f.entropy_score for f in features_list]
        
        # Count anomaly flags
        all_flags = []
        for features in features_list:
            all_flags.extend(features.anomaly_flags)
        
        flag_counts = Counter(all_flags)
        
        # Count anomalous variations (score > 0.5)
        anomalous_count = sum(1 for score in anomaly_scores if score > 0.5)
        
        import statistics
        
        return {
            'total_variations': len(variations),
            'avg_anomaly_score': statistics.mean(anomaly_scores) if anomaly_scores else 0.0,
            'max_anomaly_score': max(anomaly_scores) if anomaly_scores else 0.0,
            'anomalous_variations': anomalous_count,
            'common_flags': dict(flag_counts.most_common(5)),
            'entropy_stats': {
                'min': min(entropy_scores) if entropy_scores else 0.0,
                'max': max(entropy_scores) if entropy_scores else 0.0,
                'avg': statistics.mean(entropy_scores) if entropy_scores else 0.0
            }
        }
    
    def rank_by_anomaly_score(self, variations: List[str]) -> List[tuple[int, float]]:
        """
        Rank variations by anomaly score (lower is better).
        
        Args:
            variations: List of text variations
            
        Returns:
            List of (index, anomaly_score) tuples sorted by anomaly score
        """
        if not variations:
            return []
        
        features_list = self.extract_features_for_variations(variations)
        
        # Create list of (index, anomaly_score) tuples
        indexed_scores = [(i, features.overall_anomaly_score) 
                         for i, features in enumerate(features_list)]
        
        # Sort by anomaly score (ascending - lower is better)
        return sorted(indexed_scores, key=lambda x: x[1])
    
    def is_anomalous(self, text: str, threshold: float = 0.5) -> bool:
        """
        Check if text is anomalous based on threshold.
        
        Args:
            text: Input text
            threshold: Anomaly score threshold (default 0.5)
            
        Returns:
            True if text is considered anomalous
        """
        features = self.extract_anomaly_features(text)
        return features.overall_anomaly_score > threshold
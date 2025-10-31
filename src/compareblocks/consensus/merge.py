# src/compareblocks/consensus/merge.py
"""
Token-level merging capability for text variations.
Uses dynamic programming alignment for optimal merging of close variations.
"""

import difflib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MergeStrategy(Enum):
    """Different strategies for merging text variations."""
    LONGEST_COMMON = "longest_common"
    BEST_QUALITY = "best_quality"
    CONSENSUS_VOTING = "consensus_voting"
    DYNAMIC_PROGRAMMING = "dynamic_programming"


@dataclass
class TokenAlignment:
    """Alignment information for tokens during merging."""
    token: str
    sources: List[str]  # Which variations contributed this token
    confidence: float
    position: int
    alternatives: List[str]  # Alternative tokens from other variations


@dataclass
class MergeResult:
    """Result of merging multiple text variations."""
    merged_text: str
    merge_strategy: MergeStrategy
    source_variations: List[str]
    confidence_score: float
    token_alignments: List[TokenAlignment]
    merge_statistics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'merged_text': self.merged_text,
            'merge_strategy': self.merge_strategy.value,
            'source_variations': self.source_variations,
            'confidence_score': self.confidence_score,
            'token_alignments': [
                {
                    'token': ta.token,
                    'sources': ta.sources,
                    'confidence': ta.confidence,
                    'position': ta.position,
                    'alternatives': ta.alternatives
                }
                for ta in self.token_alignments
            ],
            'merge_statistics': self.merge_statistics
        }


class TokenLevelMerger:
    """Implements token-level merging of text variations using dynamic programming."""
    
    def __init__(self):
        """Initialize the token-level merger."""
        self.word_separators = {' ', '\t', '\n'}
        self.punctuation = {'.', ',', '!', '?', ';', ':', '"', "'", '(', ')', '[', ']', '{', '}'}
    
    def _tokenize_text(self, text: str) -> List[str]:
        """
        Tokenize text into words and punctuation.
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        if not text:
            return []
        
        # Use a simple tokenization that preserves whitespace information
        import re
        
        # Split on whitespace but keep the whitespace
        tokens = re.split(r'(\s+)', text)
        
        # Further split words from punctuation
        result_tokens = []
        for token in tokens:
            if not token:
                continue
            
            if token.isspace():
                result_tokens.append(token)
            else:
                # Split punctuation from words
                current_token = ""
                for char in token:
                    if char in self.punctuation:
                        if current_token:
                            result_tokens.append(current_token)
                            current_token = ""
                        result_tokens.append(char)
                    else:
                        current_token += char
                
                if current_token:
                    result_tokens.append(current_token)
        
        return [token for token in result_tokens if token]
    
    def _calculate_token_similarity(self, token1: str, token2: str) -> float:
        """
        Calculate similarity between two tokens.
        
        Args:
            token1: First token
            token2: Second token
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if token1 == token2:
            return 1.0
        
        if not token1 or not token2:
            return 0.0
        
        # Use difflib for character-level similarity
        matcher = difflib.SequenceMatcher(None, token1.lower(), token2.lower())
        return matcher.ratio()
    
    def _align_token_sequences(self, sequences: List[List[str]]) -> List[List[Optional[str]]]:
        """
        Align multiple token sequences using dynamic programming.
        
        Args:
            sequences: List of token sequences to align
            
        Returns:
            List of aligned sequences (with None for gaps)
        """
        if not sequences:
            return []
        
        if len(sequences) == 1:
            return [sequences[0]]
        
        # Start with pairwise alignment of first two sequences
        aligned = self._pairwise_align(sequences[0], sequences[1])
        
        # Progressively align additional sequences
        for i in range(2, len(sequences)):
            aligned = self._align_with_existing(aligned, sequences[i])
        
        return aligned
    
    def _pairwise_align(self, seq1: List[str], seq2: List[str]) -> List[List[Optional[str]]]:
        """
        Align two token sequences using dynamic programming.
        
        Args:
            seq1: First token sequence
            seq2: Second token sequence
            
        Returns:
            Two aligned sequences
        """
        # Use difflib for sequence alignment
        matcher = difflib.SequenceMatcher(None, seq1, seq2)
        
        aligned_seq1 = []
        aligned_seq2 = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Tokens match
                for k in range(i2 - i1):
                    aligned_seq1.append(seq1[i1 + k])
                    aligned_seq2.append(seq2[j1 + k])
            elif tag == 'replace':
                # Tokens differ - align them anyway
                max_len = max(i2 - i1, j2 - j1)
                for k in range(max_len):
                    token1 = seq1[i1 + k] if i1 + k < i2 else None
                    token2 = seq2[j1 + k] if j1 + k < j2 else None
                    aligned_seq1.append(token1)
                    aligned_seq2.append(token2)
            elif tag == 'delete':
                # Tokens only in seq1
                for k in range(i2 - i1):
                    aligned_seq1.append(seq1[i1 + k])
                    aligned_seq2.append(None)
            elif tag == 'insert':
                # Tokens only in seq2
                for k in range(j2 - j1):
                    aligned_seq1.append(None)
                    aligned_seq2.append(seq2[j1 + k])
        
        return [aligned_seq1, aligned_seq2]
    
    def _align_with_existing(self, existing_alignment: List[List[Optional[str]]], 
                           new_sequence: List[str]) -> List[List[Optional[str]]]:
        """
        Align a new sequence with existing alignment.
        
        Args:
            existing_alignment: Current alignment of sequences
            new_sequence: New sequence to align
            
        Returns:
            Updated alignment including new sequence
        """
        # Create consensus sequence from existing alignment for comparison
        consensus_tokens = []
        for i in range(len(existing_alignment[0])):
            # Use the first non-None token at each position
            token = None
            for seq in existing_alignment:
                if seq[i] is not None:
                    token = seq[i]
                    break
            consensus_tokens.append(token if token is not None else "")
        
        # Align new sequence with consensus
        aligned_consensus, aligned_new = self._pairwise_align(
            [t for t in consensus_tokens if t], new_sequence
        )
        
        # Expand existing alignment to match new alignment length
        result_alignment = []
        
        # Add existing sequences with gaps inserted
        consensus_idx = 0
        for seq in existing_alignment:
            new_seq = []
            for token in aligned_consensus:
                if token and consensus_idx < len(seq):
                    new_seq.append(seq[consensus_idx])
                    consensus_idx += 1
                else:
                    new_seq.append(None)
            result_alignment.append(new_seq)
            consensus_idx = 0  # Reset for next sequence
        
        # Add the new sequence
        result_alignment.append(aligned_new)
        
        return result_alignment
    
    def _select_best_token(self, aligned_tokens: List[Optional[str]], 
                          variation_qualities: Optional[List[float]] = None) -> TokenAlignment:
        """
        Select the best token from aligned alternatives.
        
        Args:
            aligned_tokens: List of aligned tokens (with None for gaps)
            variation_qualities: Optional quality scores for each variation
            
        Returns:
            TokenAlignment with selected token and metadata
        """
        # Filter out None values
        valid_tokens = [(i, token) for i, token in enumerate(aligned_tokens) if token is not None]
        
        if not valid_tokens:
            return TokenAlignment(
                token="",
                sources=[],
                confidence=0.0,
                position=0,
                alternatives=[]
            )
        
        # If all tokens are the same, use that token
        unique_tokens = list(set(token for _, token in valid_tokens))
        if len(unique_tokens) == 1:
            sources = [f"var_{i}" for i, _ in valid_tokens]
            return TokenAlignment(
                token=unique_tokens[0],
                sources=sources,
                confidence=1.0,
                position=0,
                alternatives=[]
            )
        
        # Select based on quality scores if available
        if variation_qualities:
            best_idx = 0
            best_quality = -1.0
            
            for i, token in valid_tokens:
                if i < len(variation_qualities) and variation_qualities[i] > best_quality:
                    best_quality = variation_qualities[i]
                    best_idx = i
            
            selected_token = aligned_tokens[best_idx]
            confidence = best_quality
        else:
            # Use majority voting or first occurrence
            token_counts = {}
            for _, token in valid_tokens:
                token_counts[token] = token_counts.get(token, 0) + 1
            
            # Select most frequent token
            selected_token = max(token_counts.keys(), key=lambda x: token_counts[x])
            confidence = token_counts[selected_token] / len(valid_tokens)
        
        # Collect sources and alternatives
        sources = []
        alternatives = []
        
        for i, token in enumerate(aligned_tokens):
            if token is not None:
                if token == selected_token:
                    sources.append(f"var_{i}")
                else:
                    alternatives.append(token)
        
        return TokenAlignment(
            token=selected_token,
            sources=sources,
            confidence=confidence,
            position=0,
            alternatives=list(set(alternatives))
        )
    
    def merge_variations(self, variations: List[str], 
                        variation_qualities: Optional[List[float]] = None,
                        strategy: MergeStrategy = MergeStrategy.DYNAMIC_PROGRAMMING) -> MergeResult:
        """
        Merge multiple text variations using specified strategy.
        
        Args:
            variations: List of text variations to merge
            variation_qualities: Optional quality scores for each variation
            strategy: Merging strategy to use
            
        Returns:
            MergeResult with merged text and metadata
        """
        if not variations:
            return MergeResult(
                merged_text="",
                merge_strategy=strategy,
                source_variations=[],
                confidence_score=0.0,
                token_alignments=[],
                merge_statistics={'total_variations': 0}
            )
        
        if len(variations) == 1:
            tokens = self._tokenize_text(variations[0])
            alignments = [
                TokenAlignment(
                    token=token,
                    sources=['var_0'],
                    confidence=1.0,
                    position=i,
                    alternatives=[]
                )
                for i, token in enumerate(tokens)
            ]
            
            return MergeResult(
                merged_text=variations[0],
                merge_strategy=strategy,
                source_variations=variations,
                confidence_score=1.0,
                token_alignments=alignments,
                merge_statistics={'total_variations': 1, 'alignment_length': len(tokens)}
            )
        
        # Tokenize all variations
        tokenized_variations = [self._tokenize_text(var) for var in variations]
        
        # Align token sequences
        aligned_sequences = self._align_token_sequences(tokenized_variations)
        
        # Select best token at each position
        token_alignments = []
        merged_tokens = []
        
        alignment_length = len(aligned_sequences[0]) if aligned_sequences else 0
        
        for pos in range(alignment_length):
            aligned_tokens = [seq[pos] for seq in aligned_sequences]
            
            token_alignment = self._select_best_token(aligned_tokens, variation_qualities)
            token_alignment.position = pos
            
            token_alignments.append(token_alignment)
            merged_tokens.append(token_alignment.token)
        
        # Reconstruct merged text
        merged_text = ''.join(merged_tokens)
        
        # Calculate overall confidence
        confidences = [ta.confidence for ta in token_alignments if ta.confidence > 0]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Calculate merge statistics
        merge_statistics = {
            'total_variations': len(variations),
            'alignment_length': alignment_length,
            'avg_token_confidence': overall_confidence,
            'tokens_with_alternatives': sum(1 for ta in token_alignments if ta.alternatives),
            'unanimous_tokens': sum(1 for ta in token_alignments if ta.confidence == 1.0),
            'original_lengths': [len(self._tokenize_text(var)) for var in variations],
            'merged_length': len(merged_tokens)
        }
        
        return MergeResult(
            merged_text=merged_text,
            merge_strategy=strategy,
            source_variations=variations,
            confidence_score=overall_confidence,
            token_alignments=token_alignments,
            merge_statistics=merge_statistics
        )
    
    def merge_with_quality_weights(self, variations: List[Dict[str, Any]]) -> MergeResult:
        """
        Merge variations using their quality scores as weights.
        
        Args:
            variations: List of variation dictionaries with 'text' and 'quality' keys
            
        Returns:
            MergeResult with merged text and metadata
        """
        if not variations:
            return self.merge_variations([])
        
        texts = [var.get('text', '') for var in variations]
        qualities = [var.get('quality', 0.0) for var in variations]
        
        return self.merge_variations(texts, qualities, MergeStrategy.BEST_QUALITY)
    
    def get_merge_preview(self, variations: List[str], 
                         max_differences: int = 10) -> Dict[str, Any]:
        """
        Get a preview of what merging would produce without full processing.
        
        Args:
            variations: List of text variations
            max_differences: Maximum number of differences to show
            
        Returns:
            Dictionary with merge preview information
        """
        if len(variations) < 2:
            return {
                'can_merge': False,
                'reason': 'insufficient_variations',
                'differences': [],
                'similarity_score': 1.0 if variations else 0.0
            }
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(variations)):
            for j in range(i + 1, len(variations)):
                matcher = difflib.SequenceMatcher(None, variations[i], variations[j])
                similarities.append(matcher.ratio())
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        
        # Find differences using difflib
        differences = []
        if len(variations) >= 2:
            differ = difflib.unified_diff(
                variations[0].splitlines(keepends=True),
                variations[1].splitlines(keepends=True),
                fromfile='variation_0',
                tofile='variation_1',
                n=1
            )
            
            diff_lines = list(differ)
            differences = diff_lines[:max_differences]
        
        can_merge = avg_similarity >= 0.7  # Threshold for mergeable variations
        
        return {
            'can_merge': can_merge,
            'reason': 'sufficient_similarity' if can_merge else 'low_similarity',
            'avg_similarity': avg_similarity,
            'differences': differences,
            'variation_count': len(variations),
            'estimated_confidence': avg_similarity
        }

def calculate_character_alignment_score(text1: str, text2: str) -> float:
    """
    Calculate character-level alignment score between two texts.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        float: Alignment score (0.0 to 1.0)
    """
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    
    # Simple character overlap calculation
    chars1 = set(text1.lower())
    chars2 = set(text2.lower())
    
    intersection = len(chars1.intersection(chars2))
    union = len(chars1.union(chars2))
    
    return intersection / union if union > 0 else 0.0


def find_common_subsequence(text1: str, text2: str) -> str:
    """
    Find the longest common subsequence between two texts.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        str: Longest common subsequence
    """
    if not text1 or not text2:
        return ""
    
    # Dynamic programming approach for LCS
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    # Fill the DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i-1] == text2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    # Reconstruct the LCS
    lcs = []
    i, j = m, n
    while i > 0 and j > 0:
        if text1[i-1] == text2[j-1]:
            lcs.append(text1[i-1])
            i -= 1
            j -= 1
        elif dp[i-1][j] > dp[i][j-1]:
            i -= 1
        else:
            j -= 1
    
    return ''.join(reversed(lcs))


def merge_by_confidence(texts: List[str], confidences: List[float] = None) -> str:
    """
    Merge texts by selecting characters based on confidence scores.
    
    Args:
        texts: List of text strings to merge
        confidences: Optional confidence scores for each text
        
    Returns:
        str: Merged text result
    """
    if not texts:
        return ""
    
    if len(texts) == 1:
        return texts[0]
    
    if confidences is None:
        confidences = [1.0] * len(texts)
    
    # Simple merge: select text with highest confidence
    max_confidence_idx = confidences.index(max(confidences))
    return texts[max_confidence_idx]


def merge_by_majority_vote(texts: List[str]) -> str:
    """
    Merge texts by character-level majority voting.
    
    Args:
        texts: List of text strings to merge
        
    Returns:
        str: Merged text result
    """
    if not texts:
        return ""
    
    if len(texts) == 1:
        return texts[0]
    
    # Find the longest text as base
    max_length = max(len(text) for text in texts)
    
    result = []
    for pos in range(max_length):
        char_votes = {}
        
        # Collect character votes at this position
        for text in texts:
            if pos < len(text):
                char = text[pos]
                char_votes[char] = char_votes.get(char, 0) + 1
        
        if char_votes:
            # Select character with most votes
            winning_char = max(char_votes.items(), key=lambda x: x[1])[0]
            result.append(winning_char)
    
    return ''.join(result)


def create_merge_alignment(texts: List[str]) -> List[List[str]]:
    """
    Create character-level alignment for multiple texts.
    
    Args:
        texts: List of text strings to align
        
    Returns:
        List[List[str]]: Aligned character matrix
    """
    if not texts:
        return []
    
    max_length = max(len(text) for text in texts)
    alignment = []
    
    for text in texts:
        aligned_chars = list(text) + [''] * (max_length - len(text))
        alignment.append(aligned_chars)
    
    return alignment


def calculate_merge_confidence(texts: List[str], merged_text: str) -> float:
    """
    Calculate confidence score for a merge result.
    
    Args:
        texts: Original texts that were merged
        merged_text: Result of merging
        
    Returns:
        float: Confidence score (0.0 to 1.0)
    """
    if not texts or not merged_text:
        return 0.0
    
    # Calculate similarity between merged result and each input
    similarities = []
    for text in texts:
        if text:
            similarity = calculate_character_alignment_score(merged_text, text)
            similarities.append(similarity)
    
    if not similarities:
        return 0.0
    
    # Return average similarity as confidence
    return sum(similarities) / len(similarities)


def validate_merge_result(original_texts: List[str], merged_text: str) -> Dict[str, Any]:
    """
    Validate the quality of a merge result.
    
    Args:
        original_texts: Original texts that were merged
        merged_text: Result of merging
        
    Returns:
        Dict: Validation results
    """
    if not original_texts:
        return {
            'is_valid': False,
            'confidence': 0.0,
            'issues': ['no_input_texts'],
            'length_ratio': 0.0
        }
    
    issues = []
    
    # Check if merged text is empty
    if not merged_text:
        issues.append('empty_result')
    
    # Check length ratio
    avg_input_length = sum(len(text) for text in original_texts) / len(original_texts)
    length_ratio = len(merged_text) / avg_input_length if avg_input_length > 0 else 0.0
    
    if length_ratio < 0.5:
        issues.append('result_too_short')
    elif length_ratio > 2.0:
        issues.append('result_too_long')
    
    # Calculate confidence
    confidence = calculate_merge_confidence(original_texts, merged_text)
    
    if confidence < 0.3:
        issues.append('low_confidence')
    
    return {
        'is_valid': len(issues) == 0,
        'confidence': confidence,
        'issues': issues,
        'length_ratio': length_ratio,
        'input_count': len(original_texts),
        'result_length': len(merged_text)
    }
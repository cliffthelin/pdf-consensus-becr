# src/compareblocks/association/alignment.py
"""
Content-based alignment for non-positional extracts.
Implements fuzzy matching for finding content in non-positional extracts.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import difflib
from rapidfuzz import fuzz


@dataclass
class AlignmentResult:
    """Result of content alignment."""
    block_id: str
    content_match: str
    confidence: float
    alignment_type: str
    context_before: str = ""
    context_after: str = ""


class ContentAligner:
    """Aligns content to blocks using fuzzy matching."""
    
    def __init__(self, similarity_threshold: float = 0.8):
        """Initialize content aligner."""
        self.similarity_threshold = similarity_threshold
    
    def align_to_blocks(self, content: str, blocks: List[Dict[str, Any]]) -> List[AlignmentResult]:
        """Align content to blocks using fuzzy matching."""
        results = []
        
        for block in blocks:
            block_id = block.get('block_id', '')
            block_text = block.get('text_content', '')
            
            if not block_text:
                continue
            
            # Calculate similarity using improved fuzzy matching
            similarity = fuzzy_match_content(content, block_text)
            
            if similarity >= self.similarity_threshold:
                results.append(AlignmentResult(
                    block_id=block_id,
                    content_match=content,
                    confidence=similarity,
                    alignment_type="fuzzy_match"
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)


def align_content_to_blocks(content: str, blocks: List[Dict[str, Any]], 
                          threshold: float = 0.8) -> List[AlignmentResult]:
    """Convenience function for content alignment."""
    aligner = ContentAligner(threshold)
    return aligner.align_to_blocks(content, blocks)


def fuzzy_match_content(text1: str, text2: str) -> float:
    """Calculate fuzzy match score between two texts."""
    # Normalize texts for better matching
    norm_text1 = text1.lower().strip()
    norm_text2 = text2.lower().strip()
    
    # Use multiple fuzzy matching approaches
    ratio_score = fuzz.ratio(norm_text1, norm_text2) / 100.0
    partial_score = fuzz.partial_ratio(norm_text1, norm_text2) / 100.0
    token_sort_score = fuzz.token_sort_ratio(norm_text1, norm_text2) / 100.0
    
    # Return the best score
    return max(ratio_score, partial_score, token_sort_score)
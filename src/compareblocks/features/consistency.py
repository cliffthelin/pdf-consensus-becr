# src/compareblocks/features/consistency.py
"""
Character-level consistency tracking across all associated files.
Implements dynamic consistency percentages and word-level accuracy scoring.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import re
import statistics
from difflib import SequenceMatcher


@dataclass
class CharacterConsistency:
    """Character-level consistency metrics for a text block."""
    block_id: str
    character_consistency_score: float
    word_consistency_score: float
    spelling_accuracy_score: float
    total_variations: int
    consistent_characters: int
    total_characters: int
    consistent_words: int
    total_words: int
    override_terms: Set[str] = field(default_factory=set)
    consistency_details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'block_id': self.block_id,
            'character_consistency_score': self.character_consistency_score,
            'word_consistency_score': self.word_consistency_score,
            'spelling_accuracy_score': self.spelling_accuracy_score,
            'total_variations': self.total_variations,
            'consistent_characters': self.consistent_characters,
            'total_characters': self.total_characters,
            'consistent_words': self.consistent_words,
            'total_words': self.total_words,
            'override_terms': list(self.override_terms),
            'consistency_details': self.consistency_details
        }


@dataclass
class WordConsistency:
    """Word-level consistency tracking."""
    word: str
    variations: List[str]
    frequency: int
    consistency_score: float
    is_override_term: bool = False
    spelling_variants: Set[str] = field(default_factory=set)


class CharacterConsistencyTracker:
    """Tracks character-level consistency across all associated files."""
    
    def __init__(self):
        """Initialize consistency tracker."""
        self.override_terms: Set[str] = set()
        self.acronym_patterns = [
            r'\b[A-Z]{2,}\b',  # All caps words (acronyms)
            r'\b[A-Z]+\d+\b',  # Alphanumeric codes
            r'\b\d+[A-Z]+\b',  # Numeric codes with letters
        ]
    
    def add_override_terms(self, terms: List[str]) -> None:
        """Add terms where consistency trumps spelling."""
        self.override_terms.update(term.lower() for term in terms)
    
    def is_override_term(self, word: str) -> bool:
        """Check if word is an override term (acronym/domain term)."""
        word_lower = word.lower()
        
        # Check explicit override terms
        if word_lower in self.override_terms:
            return True
        
        # Check acronym patterns
        for pattern in self.acronym_patterns:
            if re.match(pattern, word):
                return True
        
        return False
    
    def _normalize_variations_for_comparison(self, variations: List[str]) -> List[str]:
        """
        Normalize text variations for consistent character-level comparison.
        Handles whitespace, newlines, and special characters that shouldn't affect consistency.
        
        Args:
            variations: List of text variations to normalize
            
        Returns:
            List of normalized text variations
        """
        from ..normalize.textnorm import normalize_text, NormalizationConfig
        
        # Create configuration for consistency comparison
        # Focus on normalizing formatting differences that shouldn't affect consistency
        config = NormalizationConfig(
            unicode_form="NFC",                    # Normalize Unicode characters
            normalize_whitespace=True,             # Collapse multiple spaces
            preserve_line_breaks=False,            # Convert line breaks to spaces
            preserve_paragraph_breaks=False,       # Convert paragraph breaks to spaces
            enable_hyphen_joining=True,            # Join hyphenated words
            normalize_fancy_spaces=True,           # Normalize special space characters
            normalize_quotes=True,                 # Normalize quote characters
            normalize_dashes=True                  # Normalize dash characters
        )
        
        normalized_variations = []
        for variation in variations:
            if variation:
                # Apply normalization
                normalized = normalize_text(variation, config)
                # Additional cleanup for consistency comparison
                normalized = self._additional_consistency_cleanup(normalized)
                normalized_variations.append(normalized)
            else:
                normalized_variations.append(variation)
        
        return normalized_variations
    
    def _additional_consistency_cleanup(self, text: str) -> str:
        """
        Additional text cleanup specifically for consistency comparison.
        
        Args:
            text: Text to clean up
            
        Returns:
            Cleaned text
        """
        import re
        
        # Remove extra whitespace that might remain
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Normalize common OCR artifacts
        text = re.sub(r'[''`]', "'", text)  # Normalize apostrophes
        text = re.sub(r'["""]', '"', text)  # Normalize quotes
        text = re.sub(r'…', '...', text)    # Normalize ellipsis
        
        return text
    
    def _calculate_multiple_scoring_methods(self, variations: List[str], reference_text: str) -> Dict[str, float]:
        """
        Calculate multiple scoring methods to determine accuracy from different perspectives.
        
        Args:
            variations: Normalized text variations
            reference_text: Reference text for comparison
            
        Returns:
            Dictionary with different scoring method results
        """
        methods = {}
        
        # Method 1: Average Similarity Ratio (using difflib ratio)
        total_similarity = 0.0
        for variation in variations:
            matcher = SequenceMatcher(None, reference_text, variation)
            total_similarity += matcher.ratio()
        methods['average_similarity_ratio'] = total_similarity / len(variations) if variations else 0.0
        
        # Method 2: Longest Common Subsequence (LCS) based
        total_lcs_ratio = 0.0
        for variation in variations:
            lcs_length = self._longest_common_subsequence_length(reference_text, variation)
            max_length = max(len(reference_text), len(variation))
            lcs_ratio = lcs_length / max_length if max_length > 0 else 1.0
            total_lcs_ratio += lcs_ratio
        methods['lcs_ratio'] = total_lcs_ratio / len(variations) if variations else 0.0
        
        # Method 3: Edit Distance (Levenshtein) based
        total_edit_similarity = 0.0
        for variation in variations:
            edit_distance = self._levenshtein_distance(reference_text, variation)
            max_length = max(len(reference_text), len(variation))
            edit_similarity = 1.0 - (edit_distance / max_length) if max_length > 0 else 1.0
            total_edit_similarity += max(0.0, edit_similarity)
        methods['edit_distance_similarity'] = total_edit_similarity / len(variations) if variations else 0.0
        
        # Method 4: Jaccard Similarity (character n-grams)
        total_jaccard = 0.0
        for variation in variations:
            jaccard_sim = self._jaccard_similarity_chars(reference_text, variation)
            total_jaccard += jaccard_sim
        methods['jaccard_character_similarity'] = total_jaccard / len(variations) if variations else 0.0
        
        # Method 5: Weighted Average (combining multiple methods)
        methods['weighted_average'] = (
            methods['average_similarity_ratio'] * 0.3 +
            methods['lcs_ratio'] * 0.25 +
            methods['edit_distance_similarity'] * 0.25 +
            methods['jaccard_character_similarity'] * 0.2
        )
        
        return methods
    
    def _longest_common_subsequence_length(self, text1: str, text2: str) -> int:
        """Calculate the length of the longest common subsequence."""
        m, n = len(text1), len(text2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if text1[i-1] == text2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    def _levenshtein_distance(self, text1: str, text2: str) -> int:
        """Calculate the Levenshtein (edit) distance between two strings."""
        m, n = len(text1), len(text2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # Initialize base cases
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        # Fill the DP table
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if text1[i-1] == text2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        return dp[m][n]
    
    def _jaccard_similarity_chars(self, text1: str, text2: str, n: int = 2) -> float:
        """Calculate Jaccard similarity using character n-grams."""
        def get_ngrams(text: str, n: int) -> Set[str]:
            return set(text[i:i+n] for i in range(len(text) - n + 1))
        
        if len(text1) < n and len(text2) < n:
            return 1.0 if text1 == text2 else 0.0
        
        ngrams1 = get_ngrams(text1, n)
        ngrams2 = get_ngrams(text2, n)
        
        if not ngrams1 and not ngrams2:
            return 1.0
        
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_character_consistency(self, variations: List[str], 
                                      normalize_for_comparison: bool = True,
                                      include_multiple_methods: bool = True) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate character-by-character consistency across variations for a single block.
        Uses multiple scoring methods to determine accuracy from different perspectives.
        
        Args:
            variations: List of text variations for the same block to compare
            normalize_for_comparison: Whether to apply normalization before comparison
                                    (handles whitespace, newlines, special characters)
            include_multiple_methods: Whether to calculate multiple scoring methods
            
        Returns:
            Tuple of (primary_consistency_score, details_dict_with_multiple_methods)
        """
        if not variations or len(variations) < 2:
            return 1.0, {'total_characters': 0, 'consistent_characters': 0}
        
        # Apply normalization for comparison if enabled
        if normalize_for_comparison:
            normalized_variations = self._normalize_variations_for_comparison(variations)
        else:
            normalized_variations = variations
        
        # Handle identical variations (after normalization)
        unique_variations = list(set(normalized_variations))
        if len(unique_variations) == 1:
            return 1.0, {
                'total_characters': len(unique_variations[0]),
                'consistent_characters': len(unique_variations[0]),
                'reference_text': unique_variations[0],
                'variation_count': len(variations),
                'unique_variations': 1,
                'normalized_for_comparison': normalize_for_comparison
            }
        
        # Use the most frequent variation as reference for block-level comparison
        variation_counts = Counter(normalized_variations)
        reference_text = variation_counts.most_common(1)[0][0]
        
        total_chars = len(reference_text)
        if total_chars == 0:
            return 1.0, {'total_characters': 0, 'consistent_characters': 0}
        
        # Calculate consistency by comparing each variation to reference (original algorithm)
        consistent_positions = 0
        total_positions = 0
        
        for variation in normalized_variations:
            matcher = SequenceMatcher(None, reference_text, variation)
            matching_blocks = matcher.get_matching_blocks()
            
            # Count matching characters
            for match in matching_blocks:
                consistent_positions += match.size
                total_positions += max(len(reference_text), len(variation))
        
        # Average consistency across all variations (original calculation)
        if total_positions == 0:
            consistency_score = 1.0
        else:
            consistency_score = consistent_positions / total_positions
        
        # Calculate additional scoring methods if requested
        additional_scores = {}
        if include_multiple_methods:
            additional_scores = self._calculate_multiple_scoring_methods(normalized_variations, reference_text)
        
        details = {
            'total_characters': total_chars,
            'consistent_characters': consistent_positions,
            'reference_text': reference_text,
            'variation_count': len(variations),
            'unique_variations': len(unique_variations),
            'normalized_for_comparison': normalize_for_comparison,
            'total_positions': total_positions,
            'primary_method': 'original_algorithm',
            'additional_scoring_methods': additional_scores
        }
        
        return min(1.0, consistency_score), details
    
    def calculate_word_consistency(self, variations: List[str]) -> Tuple[float, Dict[str, WordConsistency]]:
        """
        Calculate word-level consistency with spelling accuracy.
        
        Args:
            variations: List of text variations to compare
            
        Returns:
            Tuple of (consistency_score, word_details)
        """
        if not variations:
            return 1.0, {}
        
        # Extract words from all variations
        all_words = defaultdict(list)
        word_details = {}
        
        for variation in variations:
            words = re.findall(r'\b\w+\b', variation.lower())
            for word in words:
                all_words[word].append(variation)
        
        if not all_words:
            return 1.0, {}
        
        consistent_words = 0
        total_words = len(all_words)
        
        for word, sources in all_words.items():
            frequency = len(sources)
            
            # Calculate consistency score for this word
            # Higher frequency = higher consistency
            word_consistency = frequency / len(variations)
            
            # Check if it's an override term
            is_override = self.is_override_term(word)
            
            # Find spelling variants
            spelling_variants = set()
            for other_word in all_words.keys():
                if other_word != word and self._are_spelling_variants(word, other_word):
                    spelling_variants.add(other_word)
            
            word_details[word] = WordConsistency(
                word=word,
                variations=list(set(sources)),
                frequency=frequency,
                consistency_score=word_consistency,
                is_override_term=is_override,
                spelling_variants=spelling_variants
            )
            
            # Count as consistent if frequency is high or it's an override term
            if word_consistency >= 0.5 or is_override:
                consistent_words += 1
        
        overall_consistency = consistent_words / total_words if total_words > 0 else 1.0
        return overall_consistency, word_details
    
    def _are_spelling_variants(self, word1: str, word2: str) -> bool:
        """Check if two words are likely spelling variants."""
        if abs(len(word1) - len(word2)) > 2:
            return False
        
        # Use sequence matcher to find similarity
        similarity = SequenceMatcher(None, word1, word2).ratio()
        return similarity >= 0.8
    
    def calculate_spelling_accuracy(self, word_details: Dict[str, WordConsistency]) -> float:
        """
        Calculate spelling accuracy score based on word consistency.
        
        Args:
            word_details: Dictionary of word consistency details
            
        Returns:
            Spelling accuracy score (0.0 to 1.0)
        """
        if not word_details:
            return 1.0
        
        total_score = 0.0
        total_words = len(word_details)
        
        for word, details in word_details.items():
            if details.is_override_term:
                # Override terms get full score regardless of spelling variants
                word_score = 1.0
            else:
                # Regular words penalized for having spelling variants
                variant_penalty = len(details.spelling_variants) * 0.1
                word_score = max(0.0, details.consistency_score - variant_penalty)
            
            total_score += word_score
        
        return total_score / total_words if total_words > 0 else 1.0
    
    def track_consistency_for_block_with_context(self, block_id: str, variations: List[str], 
                                               surrounding_blocks: Optional[Dict[str, List[str]]] = None) -> CharacterConsistency:
        """
        Track consistency for a block with optional surrounding block context.
        
        Args:
            block_id: Unique identifier for the block
            variations: List of text variations for this block
            surrounding_blocks: Optional dict of {position: [variations]} for context
                               where position can be 'before' or 'after'
            
        Returns:
            CharacterConsistency object with all metrics
        """
        if surrounding_blocks:
            # Combine current block with surrounding context when needed
            enhanced_variations = []
            for variation in variations:
                enhanced_variation = variation
                
                # Add before context if available
                if 'before' in surrounding_blocks and surrounding_blocks['before']:
                    before_text = surrounding_blocks['before'][0] if surrounding_blocks['before'] else ""
                    enhanced_variation = f"{before_text} {enhanced_variation}"
                
                # Add after context if available
                if 'after' in surrounding_blocks and surrounding_blocks['after']:
                    after_text = surrounding_blocks['after'][0] if surrounding_blocks['after'] else ""
                    enhanced_variation = f"{enhanced_variation} {after_text}"
                
                enhanced_variations.append(enhanced_variation.strip())
            
            return self.track_consistency_for_block(block_id, enhanced_variations)
        else:
            return self.track_consistency_for_block(block_id, variations)
    
    def track_consistency_for_block(self, block_id: str, variations: List[str]) -> CharacterConsistency:
        """
        Track comprehensive consistency metrics for a block.
        
        Args:
            block_id: Unique identifier for the block
            variations: List of text variations for this block
            
        Returns:
            CharacterConsistency object with all metrics
        """
        if not variations:
            return CharacterConsistency(
                block_id=block_id,
                character_consistency_score=1.0,
                word_consistency_score=1.0,
                spelling_accuracy_score=1.0,
                total_variations=0,
                consistent_characters=0,
                total_characters=0,
                consistent_words=0,
                total_words=0
            )
        
        # Calculate character-level consistency (with normalization by default)
        char_score, char_details = self.calculate_character_consistency(variations, normalize_for_comparison=True)
        
        # Calculate word-level consistency
        word_score, word_details = self.calculate_word_consistency(variations)
        
        # Calculate spelling accuracy
        spelling_score = self.calculate_spelling_accuracy(word_details)
        
        # Count override terms found
        override_terms_found = set()
        for word, details in word_details.items():
            if details.is_override_term:
                override_terms_found.add(word)
        
        return CharacterConsistency(
            block_id=block_id,
            character_consistency_score=char_score,
            word_consistency_score=word_score,
            spelling_accuracy_score=spelling_score,
            total_variations=len(variations),
            consistent_characters=char_details.get('consistent_characters', 0),
            total_characters=char_details.get('total_characters', 0),
            consistent_words=sum(1 for w in word_details.values() if w.consistency_score >= 0.5),
            total_words=len(word_details),
            override_terms=override_terms_found,
            consistency_details={
                'character_details': char_details,
                'word_details': {k: v.__dict__ for k, v in word_details.items()}
            }
        )
    
    def update_consistency_with_new_files(self, existing_consistency: CharacterConsistency, 
                                        new_variations: List[str]) -> CharacterConsistency:
        """
        Update consistency metrics when new associated files are added.
        
        Args:
            existing_consistency: Current consistency metrics
            new_variations: New variations to include
            
        Returns:
            Updated CharacterConsistency object
        """
        # Reconstruct all variations (this is a simplified approach)
        # In a real implementation, we'd store the original variations
        all_variations = new_variations
        
        # Recalculate with all variations
        return self.track_consistency_for_block(
            existing_consistency.block_id, 
            all_variations
        )


class ConsistencyOverrideManager:
    """Manages consistency override system for acronyms and domain terms."""
    
    def __init__(self):
        """Initialize override manager."""
        self.domain_terms: Set[str] = set()
        self.acronyms: Set[str] = set()
        self.custom_overrides: Set[str] = set()
    
    def add_domain_terms(self, terms: List[str]) -> None:
        """Add domain-specific terms."""
        self.domain_terms.update(term.lower() for term in terms)
    
    def add_acronyms(self, acronyms: List[str]) -> None:
        """Add known acronyms."""
        self.acronyms.update(acronym.upper() for acronym in acronyms)
    
    def add_custom_overrides(self, terms: List[str]) -> None:
        """Add custom override terms."""
        self.custom_overrides.update(term.lower() for term in terms)
    
    def should_override_spelling(self, word: str, consistency_score: float, 
                               spelling_score: float) -> bool:
        """
        Determine if consistency should trump spelling for a word.
        
        Args:
            word: The word to check
            consistency_score: Consistency score for the word
            spelling_score: Spelling accuracy score for the word
            
        Returns:
            True if consistency should override spelling concerns
        """
        word_lower = word.lower()
        word_upper = word.upper()
        
        # Check if it's a known override term
        if (word_lower in self.domain_terms or 
            word_upper in self.acronyms or 
            word_lower in self.custom_overrides):
            return True
        
        # Check if consistency is significantly higher than spelling
        if consistency_score > 0.8 and consistency_score > spelling_score + 0.2:
            return True
        
        return False
    
    def get_all_override_terms(self) -> Set[str]:
        """Get all override terms."""
        return self.domain_terms.union(
            {a.lower() for a in self.acronyms}
        ).union(self.custom_overrides)


def track_character_consistency(block_id: str, variations: List[str], 
                              override_terms: Optional[List[str]] = None) -> CharacterConsistency:
    """
    Convenience function to track character consistency for a block.
    
    Args:
        block_id: Unique identifier for the block
        variations: List of text variations
        override_terms: Optional list of override terms
        
    Returns:
        CharacterConsistency object
    """
    tracker = CharacterConsistencyTracker()
    if override_terms:
        tracker.add_override_terms(override_terms)
    
    return tracker.track_consistency_for_block(block_id, variations)


def calculate_block_consistency_for_json(block_id: str, variations: List[str], 
                                       override_terms: Optional[List[str]] = None,
                                       normalize_for_comparison: bool = True) -> Dict[str, Any]:
    """
    Calculate consistency metrics for a block formatted for JSON output.
    
    Args:
        block_id: Unique identifier for the block
        variations: List of text variations for this block
        override_terms: Optional list of override terms
        normalize_for_comparison: Whether to normalize text before comparison
        
    Returns:
        Dictionary with consistency metrics formatted for JSON inclusion
    """
    tracker = CharacterConsistencyTracker()
    if override_terms:
        tracker.add_override_terms(override_terms)
    
    # Calculate character consistency with normalization and multiple methods
    char_score, char_details = tracker.calculate_character_consistency(
        variations, normalize_for_comparison=normalize_for_comparison, include_multiple_methods=True
    )
    
    # Calculate full consistency metrics
    consistency = tracker.track_consistency_for_block(block_id, variations)
    
    # Format for JSON output
    return {
        'block_id': block_id,
        'character_consistency_score': char_score,
        'word_consistency_score': consistency.word_consistency_score,
        'spelling_accuracy_score': consistency.spelling_accuracy_score,
        'total_variations': len(variations),
        'unique_variations': char_details.get('unique_variations', 0),
        'normalized_for_comparison': normalize_for_comparison,
        'override_terms_count': len(consistency.override_terms),
        'consistency_details': {
            'total_characters': char_details.get('total_characters', 0),
            'consistent_characters': char_details.get('consistent_characters', 0),
            'reference_text_length': len(char_details.get('reference_text', '')),
            'primary_method': char_details.get('primary_method', 'original_algorithm'),
            'additional_scoring_methods': char_details.get('additional_scoring_methods', {})
        }
    }


def calculate_dynamic_consistency_percentage(consistencies: List[CharacterConsistency]) -> Dict[str, float]:
    """
    Calculate dynamic consistency percentages across multiple blocks.
    
    Args:
        consistencies: List of consistency objects
        
    Returns:
        Dictionary with overall consistency metrics
    """
    if not consistencies:
        return {
            'overall_character_consistency': 1.0,
            'overall_word_consistency': 1.0,
            'overall_spelling_accuracy': 1.0,
            'total_blocks': 0
        }
    
    char_scores = [c.character_consistency_score for c in consistencies]
    word_scores = [c.word_consistency_score for c in consistencies]
    spelling_scores = [c.spelling_accuracy_score for c in consistencies]
    
    return {
        'overall_character_consistency': statistics.mean(char_scores),
        'overall_word_consistency': statistics.mean(word_scores),
        'overall_spelling_accuracy': statistics.mean(spelling_scores),
        'total_blocks': len(consistencies),
        'character_consistency_std': statistics.stdev(char_scores) if len(char_scores) > 1 else 0.0,
        'word_consistency_std': statistics.stdev(word_scores) if len(word_scores) > 1 else 0.0,
        'spelling_accuracy_std': statistics.stdev(spelling_scores) if len(spelling_scores) > 1 else 0.0
    }
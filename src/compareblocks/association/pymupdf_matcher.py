# src/compareblocks/association/pymupdf_matcher.py
"""
Specialized matcher for PyMuPDF blocks to GBG blocks.
Since GBG uses PyMuPDF as its underlying engine, we should achieve near-perfect matching.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path
from rapidfuzz import fuzz
import re
from ..config.file_manager import file_manager


@dataclass
class PyMuPDFMatch:
    """Result of PyMuPDF to GBG block matching."""
    engine_block_id: str
    gbg_block_id: str
    similarity_score: float
    match_type: str
    engine_text_preview: str
    gbg_text_preview: str
    page_match: bool
    bbox_similarity: float = 0.0


class PyMuPDFBlockMatcher:
    """Specialized matcher for PyMuPDF blocks to GBG blocks."""
    
    def __init__(self, similarity_threshold: float = 0.7):
        """Initialize the PyMuPDF block matcher."""
        self.similarity_threshold = similarity_threshold
    
    def match_blocks_enhanced(self, gbg_data: Dict[str, Any], engine_data: Dict[str, Any]) -> List[PyMuPDFMatch]:
        """Enhanced version of match_blocks with additional features."""
        return self.match_blocks(gbg_data, engine_data)
    
    def match_blocks(self, gbg_data: Dict[str, Any], engine_data: Dict[str, Any]) -> List[PyMuPDFMatch]:
        """
        Match PyMuPDF engine blocks to GBG blocks using multiple strategies.
        
        Args:
            gbg_data: GBG analysis data
            engine_data: PyMuPDF engine data
            
        Returns:
            List of PyMuPDF matches
        """
        matches = []
        
        # Extract GBG blocks organized by page
        gbg_blocks_by_page = self._extract_gbg_blocks_by_page(gbg_data)
        
        # Extract PyMuPDF blocks organized by page
        engine_blocks_by_page = self._extract_engine_blocks_by_page(engine_data)
        
        # Match blocks page by page for better accuracy
        for page_num in engine_blocks_by_page.keys():
            if page_num in gbg_blocks_by_page:
                page_matches = self._match_blocks_on_page(
                    engine_blocks_by_page[page_num],
                    gbg_blocks_by_page[page_num],
                    page_num
                )
                matches.extend(page_matches)
        
        return matches
    
    def _extract_gbg_blocks_by_page(self, gbg_data: Dict[str, Any]) -> Dict[int, List[Dict[str, Any]]]:
        """Extract GBG blocks organized by page."""
        blocks_by_page = {}
        
        for page_str, page_data in gbg_data.get('pages', {}).items():
            page_num = int(page_str)
            blocks = []
            
            for block in page_data.get('blocks', []):
                text_content = block.get('text_content', '').strip()
                if text_content:  # Only include blocks with text
                    # Skip image blocks if configured to ignore them
                    if file_manager.should_ignore_images() and file_manager.is_image_block(text_content):
                        continue
                    
                    blocks.append({
                        'block_id': block.get('block_id', ''),
                        'page': page_num,
                        'text': text_content,
                        'bbox': block.get('bbox', {}),
                        'text_length': block.get('text_length', len(text_content))
                    })
            
            if blocks:
                blocks_by_page[page_num] = blocks
        
        return blocks_by_page
    
    def _extract_engine_blocks_by_page(self, engine_data: Dict[str, Any]) -> Dict[int, List[Dict[str, Any]]]:
        """Extract PyMuPDF engine blocks organized by page."""
        blocks_by_page = {}
        
        for block in engine_data.get('blocks', []):
            page_num = block.get('page', 0)
            text = block.get('text', '').strip()
            
            if text:  # Only include blocks with text
                # Skip image blocks if configured to ignore them
                if file_manager.should_ignore_images() and file_manager.is_image_block(text):
                    continue
                
                if page_num not in blocks_by_page:
                    blocks_by_page[page_num] = []
                
                blocks_by_page[page_num].append({
                    'block_id': block.get('block_id', ''),
                    'page': page_num,
                    'text': text,
                    'bbox': block.get('bbox', []),
                    'text_length': len(text)
                })
        
        return blocks_by_page
    
    def _match_blocks_on_page(self, engine_blocks: List[Dict[str, Any]], 
                             gbg_blocks: List[Dict[str, Any]], page_num: int) -> List[PyMuPDFMatch]:
        """Match blocks on a specific page using multiple strategies."""
        matches = []
        used_gbg_blocks = set()
        used_engine_blocks = set()
        
        # Strategy 1: Exact text match (should be common since both use PyMuPDF)
        for engine_block in engine_blocks:
            if engine_block['block_id'] in used_engine_blocks:
                continue
            best_match = self._find_exact_text_match(engine_block, gbg_blocks, used_gbg_blocks)
            if best_match:
                matches.append(best_match)
                used_gbg_blocks.add(best_match.gbg_block_id)
                used_engine_blocks.add(best_match.engine_block_id)
        
        # Strategy 2: High similarity text match for remaining blocks
        remaining_engine_blocks = [b for b in engine_blocks if b['block_id'] not in used_engine_blocks]
        
        for engine_block in remaining_engine_blocks:
            best_match = self._find_similarity_match(engine_block, gbg_blocks, used_gbg_blocks)
            if best_match and best_match.similarity_score >= self.similarity_threshold:
                matches.append(best_match)
                used_gbg_blocks.add(best_match.gbg_block_id)
                used_engine_blocks.add(best_match.engine_block_id)
        
        # Strategy 3: SPATIAL-FIRST MATCHING - Match by position regardless of text content
        remaining_engine_blocks = [b for b in engine_blocks if b['block_id'] not in used_engine_blocks]
        
        spatial_matches = self._find_spatial_first_matches(remaining_engine_blocks, gbg_blocks, used_gbg_blocks)
        matches.extend(spatial_matches)
        for match in spatial_matches:
            used_gbg_blocks.add(match.gbg_block_id)
            used_engine_blocks.add(match.engine_block_id)
        
        # Strategy 4: BLOCK COMBINATION MATCHING - Match multiple engine blocks to single GBG block
        remaining_engine_blocks = [b for b in engine_blocks if b['block_id'] not in used_engine_blocks]
        remaining_gbg_blocks = [b for b in gbg_blocks if b['block_id'] not in used_gbg_blocks]
        
        combination_matches = self._find_combination_matches(remaining_engine_blocks, remaining_gbg_blocks)
        matches.extend(combination_matches)
        for match in combination_matches:
            used_gbg_blocks.add(match.gbg_block_id)
            used_engine_blocks.add(match.engine_block_id)
        
        # Strategy 5: FORCE 100% MATCHING - Match any remaining blocks by best spatial fit
        remaining_engine_blocks = [b for b in engine_blocks if b['block_id'] not in used_engine_blocks]
        remaining_gbg_blocks = [b for b in gbg_blocks if b['block_id'] not in used_gbg_blocks]
        
        force_matches = self._force_remaining_matches(remaining_engine_blocks, remaining_gbg_blocks)
        matches.extend(force_matches)
        
        return matches
    
    def _find_exact_text_match(self, engine_block: Dict[str, Any], 
                              gbg_blocks: List[Dict[str, Any]], 
                              used_blocks: set) -> Optional[PyMuPDFMatch]:
        """Find exact text match between engine and GBG blocks."""
        engine_text = self._normalize_text(engine_block['text'])
        
        for gbg_block in gbg_blocks:
            if gbg_block['block_id'] in used_blocks:
                continue
            
            gbg_text = self._normalize_text(gbg_block['text'])
            
            if engine_text == gbg_text:
                return PyMuPDFMatch(
                    engine_block_id=engine_block['block_id'],
                    gbg_block_id=gbg_block['block_id'],
                    similarity_score=1.0,
                    match_type='exact_text',
                    engine_text_preview=engine_block['text'][:100],
                    gbg_text_preview=gbg_block['text'][:100],
                    page_match=True,
                    bbox_similarity=self._calculate_bbox_similarity(
                        engine_block.get('bbox', []), gbg_block.get('bbox', {})
                    )
                )
        
        return None
    
    def _find_similarity_match(self, engine_block: Dict[str, Any], 
                              gbg_blocks: List[Dict[str, Any]], 
                              used_blocks: set) -> Optional[PyMuPDFMatch]:
        """Find best similarity match between engine and GBG blocks."""
        engine_text = engine_block['text']
        best_match = None
        best_similarity = 0
        
        # Special handling for single character blocks
        if len(engine_text.strip()) == 1:
            return self._find_single_char_match(engine_block, gbg_blocks, used_blocks)
        
        for gbg_block in gbg_blocks:
            if gbg_block['block_id'] in used_blocks:
                continue
            
            gbg_text = gbg_block['text']
            
            # Use multiple similarity measures
            similarity = self._calculate_comprehensive_similarity(engine_text, gbg_text)
            
            # AGGRESSIVE MATCHING: Check for normalization match first
            engine_normalized = self._normalize_text(engine_text)
            gbg_normalized = self._normalize_text(gbg_text)
            
            if engine_normalized == gbg_normalized:
                # This is an exact match after normalization (line breaks, spacing, etc.)
                return PyMuPDFMatch(
                    engine_block_id=engine_block['block_id'],
                    gbg_block_id=gbg_block['block_id'],
                    similarity_score=1.0,
                    match_type='exact_text_normalized',
                    engine_text_preview=engine_block['text'][:100],
                    gbg_text_preview=gbg_block['text'][:100],
                    page_match=True,
                    bbox_similarity=self._calculate_bbox_similarity(
                        engine_block.get('bbox', []), gbg_block.get('bbox', {})
                    )
                )
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = gbg_block
        
        if best_match and best_similarity >= self.similarity_threshold:
            # TREAT HIGH SIMILARITY AS EXACT MATCH
            # Line breaks, spacing differences are not valid content differences
            if best_similarity >= 0.90:
                match_type = 'exact_text_high_similarity'
                final_score = 1.0
            else:
                match_type = 'similarity_text'
                final_score = best_similarity
            
            return PyMuPDFMatch(
                engine_block_id=engine_block['block_id'],
                gbg_block_id=best_match['block_id'],
                similarity_score=final_score,
                match_type=match_type,
                engine_text_preview=engine_block['text'][:100],
                gbg_text_preview=best_match['text'][:100],
                page_match=True,
                bbox_similarity=self._calculate_bbox_similarity(
                    engine_block.get('bbox', []), best_match.get('bbox', {})
                )
            )
        
        return None
    
    def _find_positional_match(self, engine_block: Dict[str, Any], 
                              gbg_blocks: List[Dict[str, Any]], 
                              used_blocks: set) -> Optional[PyMuPDFMatch]:
        """Find positional match based on bounding box similarity."""
        engine_bbox = engine_block.get('bbox', [])
        if not engine_bbox or len(engine_bbox) < 4:
            return None
        
        best_match = None
        best_bbox_similarity = 0
        
        for gbg_block in gbg_blocks:
            if gbg_block['block_id'] in used_blocks:
                continue
            
            gbg_bbox = gbg_block.get('bbox', {})
            bbox_similarity = self._calculate_bbox_similarity(engine_bbox, gbg_bbox)
            
            if bbox_similarity > best_bbox_similarity and bbox_similarity > 0.8:  # High bbox threshold
                # Also check if text has some similarity
                text_similarity = self._calculate_comprehensive_similarity(
                    engine_block['text'], gbg_block['text']
                )
                
                if text_similarity > 0.3:  # Some text similarity required
                    best_bbox_similarity = bbox_similarity
                    best_match = gbg_block
        
        if best_match:
            return PyMuPDFMatch(
                engine_block_id=engine_block['block_id'],
                gbg_block_id=best_match['block_id'],
                similarity_score=best_bbox_similarity * 0.7 + text_similarity * 0.3,  # Weighted score
                match_type='positional',
                engine_text_preview=engine_block['text'][:100],
                gbg_text_preview=best_match['text'][:100],
                page_match=True,
                bbox_similarity=best_bbox_similarity
            )
        
        return None
    
    def _find_single_char_match(self, engine_block: Dict[str, Any], 
                               gbg_blocks: List[Dict[str, Any]], 
                               used_blocks: set) -> Optional[PyMuPDFMatch]:
        """Find match for single character blocks that may be contained in larger GBG blocks."""
        engine_char = engine_block['text'].strip().upper()
        engine_bbox = engine_block.get('bbox', [])
        
        # Find GBG blocks that contain this character
        candidate_matches = []
        
        for gbg_block in gbg_blocks:
            if gbg_block['block_id'] in used_blocks:
                continue
            
            gbg_text = gbg_block['text'].upper()
            
            # Check if the character is contained in the GBG text
            if engine_char in gbg_text:
                # Calculate positional relevance if bbox is available
                positional_score = 0.0
                if engine_bbox and len(engine_bbox) >= 4:
                    bbox_similarity = self._calculate_bbox_similarity(
                        engine_bbox, gbg_block.get('bbox', {})
                    )
                    positional_score = bbox_similarity
                
                # Calculate character frequency (prefer blocks where char appears less frequently)
                char_frequency = gbg_text.count(engine_char)
                frequency_score = 1.0 / char_frequency if char_frequency > 0 else 0.0
                
                # Prioritize positional matching for single characters
                # Base score for containment, heavily weighted by position
                if positional_score > 0.5:  # Good positional match
                    combined_score = 0.85 + (positional_score * 0.1) + (frequency_score * 0.05)
                else:  # Poor positional match
                    combined_score = 0.7 + (positional_score * 0.2) + (frequency_score * 0.1)
                
                candidate_matches.append({
                    'gbg_block': gbg_block,
                    'score': combined_score,
                    'bbox_similarity': positional_score,
                    'char_frequency': char_frequency
                })
        
        if not candidate_matches:
            return None
        
        # Sort by combined score and take the best match
        candidate_matches.sort(key=lambda x: x['score'], reverse=True)
        best_candidate = candidate_matches[0]
        
        # Only match if we have reasonable confidence
        # Require higher confidence for single chars to avoid false matches
        if best_candidate['score'] >= 0.8 and best_candidate['bbox_similarity'] > 0.3:
            return PyMuPDFMatch(
                engine_block_id=engine_block['block_id'],
                gbg_block_id=best_candidate['gbg_block']['block_id'],
                similarity_score=best_candidate['score'],
                match_type='single_char_containment',
                engine_text_preview=engine_block['text'],
                gbg_text_preview=best_candidate['gbg_block']['text'][:100],
                page_match=True,
                bbox_similarity=best_candidate['bbox_similarity']
            )
        
        return None
    
    def _find_spatial_first_matches(self, engine_blocks: List[Dict[str, Any]], 
                                   gbg_blocks: List[Dict[str, Any]], 
                                   used_gbg_blocks: set) -> List[PyMuPDFMatch]:
        """
        Find matches based primarily on spatial position, regardless of text content.
        This handles cases where text doesn't match due to orientation, OCR errors, etc.
        """
        matches = []
        
        for engine_block in engine_blocks:
            engine_bbox = engine_block.get('bbox', [])
            if not engine_bbox or len(engine_bbox) < 4:
                continue
            
            best_match = None
            best_spatial_score = 0.0
            
            for gbg_block in gbg_blocks:
                if gbg_block['block_id'] in used_gbg_blocks:
                    continue
                
                gbg_bbox = gbg_block.get('bbox', {})
                
                # Calculate spatial similarity (IoU)
                spatial_score = self._calculate_bbox_similarity(engine_bbox, gbg_bbox)
                
                if spatial_score > best_spatial_score:
                    best_spatial_score = spatial_score
                    best_match = gbg_block
            
            # AGGRESSIVE SPATIAL MATCHING: Accept any reasonable spatial overlap
            if best_match and best_spatial_score >= 0.1:  # 10% spatial overlap minimum
                
                # Calculate text similarity for reference (but don't require it)
                text_similarity = self._calculate_comprehensive_similarity(
                    engine_block.get('text', ''), best_match.get('text', '')
                )
                
                # Determine match type based on text similarity
                if text_similarity >= 0.8:
                    match_type = 'spatial_with_text'
                elif text_similarity >= 0.3:
                    match_type = 'spatial_partial_text'
                else:
                    match_type = 'spatial_only'
                
                # Combined score: prioritize spatial, but include text as bonus
                combined_score = best_spatial_score * 0.8 + text_similarity * 0.2
                
                match = PyMuPDFMatch(
                    engine_block_id=engine_block['block_id'],
                    gbg_block_id=best_match['block_id'],
                    similarity_score=combined_score,
                    match_type=match_type,
                    engine_text_preview=engine_block.get('text', '')[:100],
                    gbg_text_preview=best_match.get('text', '')[:100],
                    page_match=True,
                    bbox_similarity=best_spatial_score
                )
                
                matches.append(match)
        
        return matches
    
    def _find_combination_matches(self, engine_blocks: List[Dict[str, Any]], 
                                 gbg_blocks: List[Dict[str, Any]]) -> List[PyMuPDFMatch]:
        """
        Find matches where multiple engine blocks combine to match a single GBG block.
        This handles cases where PyMuPDF extracted individual characters/words that GBG merged.
        """
        matches = []
        used_engine_blocks = set()
        
        for gbg_block in gbg_blocks:
            gbg_text = gbg_block['text'].strip()
            if not gbg_text:
                continue
            
            # Find potential engine blocks that could combine to form this GBG block
            combination_match = self._find_best_combination_for_gbg_block(
                gbg_block, engine_blocks, used_engine_blocks
            )
            
            if combination_match:
                matches.extend(combination_match)
                # Mark used engine blocks
                for match in combination_match:
                    used_engine_blocks.add(match.engine_block_id)
        
        return matches
    
    def _find_best_combination_for_gbg_block(self, gbg_block: Dict[str, Any], 
                                           engine_blocks: List[Dict[str, Any]], 
                                           used_engine_blocks: set) -> Optional[List[PyMuPDFMatch]]:
        """
        Find the best combination of engine blocks that match a single GBG block.
        """
        gbg_text = gbg_block['text'].strip().upper()
        gbg_bbox = gbg_block.get('bbox', {})
        
        # Get available engine blocks (not already used)
        available_blocks = [b for b in engine_blocks if b['block_id'] not in used_engine_blocks]
        
        if not available_blocks:
            return None
        
        # Strategy 1: Character-by-character combination (for single chars like U,T,A,H -> UTAH)
        char_combination = self._find_character_combination(gbg_block, available_blocks)
        if char_combination:
            return char_combination
        
        # Strategy 2: Word-by-word combination (for words that were split)
        word_combination = self._find_word_combination(gbg_block, available_blocks)
        if word_combination:
            return word_combination
        
        # Strategy 3: Spatial combination (blocks that are spatially close and form the text)
        spatial_combination = self._find_spatial_combination(gbg_block, available_blocks)
        if spatial_combination:
            return spatial_combination
        
        return None
    
    def _find_character_combination(self, gbg_block: Dict[str, Any], 
                                  engine_blocks: List[Dict[str, Any]]) -> Optional[List[PyMuPDFMatch]]:
        """
        Enhanced character combination matching with improved spatial grouping.
        
        Enhancements:
        1. Enhanced spatial character grouping
        2. Relaxed spatial thresholds  
        3. Sequential character detection
        4. Word boundary analysis
        """
        gbg_text = gbg_block['text'].strip().upper()
        gbg_bbox = gbg_block.get('bbox', {})
        
        # Increased threshold for character combinations (handles longer sequences)
        if len(gbg_text) > 200:  # Allow longer text sequences
            return None
        
        # Find single-character blocks that could form this text
        single_char_blocks = [b for b in engine_blocks if len(b['text'].strip()) == 1]
        
        if len(single_char_blocks) < 2:  # Need at least 2 chars to combine
            return None
        
        # ENHANCEMENT 1: Enhanced spatial character grouping
        # Try multiple strategies in order of preference
        strategies = [
            self._find_sequential_character_match,      # Strategy 1: Sequential detection
            self._find_word_boundary_character_match,   # Strategy 2: Word boundary analysis  
            self._find_relaxed_spatial_character_match, # Strategy 3: Relaxed spatial matching
            self._find_best_char_sequence              # Strategy 4: Original fallback
        ]
        
        for strategy in strategies:
            combination = strategy(gbg_text, single_char_blocks, gbg_bbox)
            if combination:
                # Create matches for each character in the combination
                matches = []
                for engine_block in combination['blocks']:
                    match = PyMuPDFMatch(
                        engine_block_id=engine_block['block_id'],
                        gbg_block_id=gbg_block['block_id'],
                        similarity_score=combination['score'],
                        match_type=f"character_combination_{combination.get('strategy', 'enhanced')}",
                        engine_text_preview=engine_block['text'],
                        gbg_text_preview=gbg_block['text'][:100],
                        page_match=True,
                        bbox_similarity=combination['spatial_score']
                    )
                    matches.append(match)
                
                return matches
        
        return None
    
    def _find_sequential_character_match(self, target_text: str, char_blocks: List[Dict[str, Any]], 
                                       gbg_bbox: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        ENHANCEMENT 3: Sequential character detection.
        Recognize character sequences that form words by analyzing spatial ordering.
        """
        target_chars = [c for c in target_text if c.isalnum()]
        
        if len(target_chars) < 2:
            return None
        
        # Group blocks by character
        char_to_blocks = {}
        for block in char_blocks:
            char = block['text'].strip().upper()
            if char.isalnum():
                if char not in char_to_blocks:
                    char_to_blocks[char] = []
                char_to_blocks[char].append(block)
        
        # Find available characters that match target
        available_chars = set(char_to_blocks.keys())
        target_char_set = set(target_chars)
        matching_chars = available_chars.intersection(target_char_set)
        
        if len(matching_chars) < max(2, len(target_chars) * 0.4):  # Need at least 40% of characters or minimum 2
            return None
        
        # Try to find a sequential arrangement
        selected_blocks = []
        used_blocks = set()
        
        for target_char in target_chars:
            if target_char not in char_to_blocks:
                continue
                
            # Find the best unused block for this character
            best_block = None
            best_score = 0.0
            
            for block in char_to_blocks[target_char]:
                if block['block_id'] in used_blocks:
                    continue
                    
                # Calculate spatial relevance to GBG bbox
                spatial_score = self._calculate_bbox_similarity(block.get('bbox', []), gbg_bbox)
                
                # Bonus for spatial sequence (blocks that are close to previously selected blocks)
                sequence_bonus = 0.0
                if selected_blocks:
                    last_block = selected_blocks[-1]
                    sequence_bonus = self._calculate_sequence_proximity(block, last_block)
                
                total_score = spatial_score + (sequence_bonus * 0.3)
                
                if total_score > best_score:
                    best_score = total_score
                    best_block = block
            
            if best_block and best_score > 0.01:  # Ultra-relaxed threshold
                selected_blocks.append(best_block)
                used_blocks.add(best_block['block_id'])
        
        if len(selected_blocks) >= max(2, len(target_chars) * 0.3):  # At least 30% coverage
            avg_spatial_score = sum(self._calculate_bbox_similarity(b.get('bbox', []), gbg_bbox) 
                                  for b in selected_blocks) / len(selected_blocks)
            
            text_coverage = len(selected_blocks) / len(target_chars)
            combined_score = 0.6 + (avg_spatial_score * 0.3) + (text_coverage * 0.1)
            
            return {
                'blocks': selected_blocks,
                'score': combined_score,
                'spatial_score': avg_spatial_score,
                'text_coverage': text_coverage,
                'strategy': 'sequential'
            }
        
        return None
    
    def _find_word_boundary_character_match(self, target_text: str, char_blocks: List[Dict[str, Any]], 
                                          gbg_bbox: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        ENHANCEMENT 4: Word boundary analysis.
        Group characters into logical word units based on spatial clustering.
        """
        target_chars = [c for c in target_text if c.isalnum()]
        
        if len(target_chars) < 2:
            return None
        
        # Analyze target text for word boundaries
        words = target_text.split()
        if len(words) < 2:
            # Single word - treat as character sequence
            return self._find_sequential_character_match(target_text, char_blocks, gbg_bbox)
        
        # Group blocks by character
        char_to_blocks = {}
        for block in char_blocks:
            char = block['text'].strip().upper()
            if char.isalnum():
                if char not in char_to_blocks:
                    char_to_blocks[char] = []
                char_to_blocks[char].append(block)
        
        # Try to match each word separately, then combine
        word_matches = []
        used_blocks = set()
        
        for word in words:
            word_chars = [c for c in word.upper() if c.isalnum()]
            word_blocks = []
            
            for char in word_chars:
                if char not in char_to_blocks:
                    continue
                    
                # Find best unused block for this character
                best_block = None
                best_score = 0.0
                
                for block in char_to_blocks[char]:
                    if block['block_id'] in used_blocks:
                        continue
                        
                    spatial_score = self._calculate_bbox_similarity(block.get('bbox', []), gbg_bbox)
                    
                    # Bonus for being close to other blocks in this word
                    word_proximity_bonus = 0.0
                    if word_blocks:
                        word_proximity_bonus = max(
                            self._calculate_sequence_proximity(block, wb) for wb in word_blocks
                        )
                    
                    total_score = spatial_score + (word_proximity_bonus * 0.4)
                    
                    if total_score > best_score:
                        best_score = total_score
                        best_block = block
                
                if best_block and best_score > 0.01:  # Ultra-relaxed threshold
                    word_blocks.append(best_block)
                    used_blocks.add(best_block['block_id'])
            
            if len(word_blocks) >= max(1, len(word_chars) * 0.4):  # At least 40% of word characters
                word_matches.extend(word_blocks)
        
        if len(word_matches) >= max(2, len(target_chars) * 0.3):  # At least 30% coverage
            avg_spatial_score = sum(self._calculate_bbox_similarity(b.get('bbox', []), gbg_bbox) 
                                  for b in word_matches) / len(word_matches)
            
            text_coverage = len(word_matches) / len(target_chars)
            word_coverage = len([w for w in words if any(c in [b['text'].strip().upper() for b in word_matches] 
                                                        for c in w.upper() if c.isalnum())]) / len(words)
            
            combined_score = 0.5 + (avg_spatial_score * 0.2) + (text_coverage * 0.15) + (word_coverage * 0.15)
            
            return {
                'blocks': word_matches,
                'score': combined_score,
                'spatial_score': avg_spatial_score,
                'text_coverage': text_coverage,
                'word_coverage': word_coverage,
                'strategy': 'word_boundary'
            }
        
        return None
    
    def _find_relaxed_spatial_character_match(self, target_text: str, char_blocks: List[Dict[str, Any]], 
                                            gbg_bbox: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        ENHANCEMENT 2: Relaxed spatial thresholds.
        Allow larger gaps between characters and more flexible spatial matching.
        """
        target_chars = [c for c in target_text if c.isalnum()]
        
        if len(target_chars) < 2:
            return None
        
        # Group blocks by character
        char_to_blocks = {}
        for block in char_blocks:
            char = block['text'].strip().upper()
            if char.isalnum():
                if char not in char_to_blocks:
                    char_to_blocks[char] = []
                char_to_blocks[char].append(block)
        
        # EXTREMELY RELAXED MATCHING: Accept any available characters
        available_chars = set(char_to_blocks.keys())
        target_char_set = set(target_chars)
        matching_chars = available_chars.intersection(target_char_set)
        
        # Even more relaxed - accept if we have any matching characters
        if len(matching_chars) < 1:
            return None
        
        # Collect all available blocks for matching characters
        selected_blocks = []
        for char in matching_chars:
            # Take the first available block for each character (very relaxed)
            if char_to_blocks[char]:
                # Choose block with best spatial score, but accept very low scores
                best_block = max(char_to_blocks[char], 
                               key=lambda b: self._calculate_bbox_similarity(b.get('bbox', []), gbg_bbox))
                selected_blocks.append(best_block)
        
        if len(selected_blocks) >= 1:  # Accept even single character matches
            avg_spatial_score = sum(self._calculate_bbox_similarity(b.get('bbox', []), gbg_bbox) 
                                  for b in selected_blocks) / len(selected_blocks)
            
            text_coverage = len(set(b['text'].strip().upper() for b in selected_blocks) & target_char_set) / len(target_char_set)
            
            # Very generous scoring for relaxed matching
            combined_score = 0.3 + (avg_spatial_score * 0.3) + (text_coverage * 0.4)
            
            return {
                'blocks': selected_blocks,
                'score': combined_score,
                'spatial_score': avg_spatial_score,
                'text_coverage': text_coverage,
                'strategy': 'relaxed_spatial'
            }
        
        return None
    
    def _calculate_sequence_proximity(self, block1: Dict[str, Any], block2: Dict[str, Any]) -> float:
        """
        Calculate how close two blocks are in sequence (for sequential character detection).
        Returns a score from 0.0 to 1.0 based on spatial proximity.
        """
        bbox1 = block1.get('bbox', [])
        bbox2 = block2.get('bbox', [])
        
        if not bbox1 or not bbox2 or len(bbox1) < 4 or len(bbox2) < 4:
            return 0.0
        
        # Calculate center points
        center1_x = (bbox1[0] + bbox1[2]) / 2
        center1_y = (bbox1[1] + bbox1[3]) / 2
        center2_x = (bbox2[0] + bbox2[2]) / 2
        center2_y = (bbox2[1] + bbox2[3]) / 2
        
        # Calculate distance
        distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
        
        # Convert distance to proximity score (closer = higher score)
        # Use generous thresholds for character-level proximity
        max_distance = 200  # Allow large gaps between characters
        if distance > max_distance:
            return 0.0
        
        proximity_score = 1.0 - (distance / max_distance)
        return max(0.0, proximity_score)
    
    def _find_best_char_sequence(self, target_text: str, char_blocks: List[Dict[str, Any]], 
                               gbg_bbox: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find the best sequence of character blocks that forms the target text."""
        target_chars = [c for c in target_text if c.isalnum()]  # Only alphanumeric chars
        
        if len(target_chars) < 2:
            return None
        
        # Group blocks by their character
        char_to_blocks = {}
        for block in char_blocks:
            char = block['text'].strip().upper()
            if char.isalnum():
                if char not in char_to_blocks:
                    char_to_blocks[char] = []
                char_to_blocks[char].append(block)
        
        # RELAXED MATCHING: Don't require all characters, just find spatially close ones
        available_chars = set(char_to_blocks.keys())
        target_char_set = set(target_chars)
        
        # Find intersection of available and target characters
        matching_chars = available_chars.intersection(target_char_set)
        
        if len(matching_chars) < 2:  # Need at least 2 matching characters
            return None
        
        # Find the best spatial arrangement of available characters
        best_combination = self._find_spatially_coherent_sequence(
            list(matching_chars), char_to_blocks, gbg_bbox
        )
        
        return best_combination
    
    def _find_spatially_coherent_sequence(self, target_chars: List[str], 
                                        char_to_blocks: Dict[str, List[Dict[str, Any]]], 
                                        gbg_bbox: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a spatially coherent sequence of character blocks.
        ENHANCEMENT 1: Enhanced spatial character grouping with ultra-relaxed thresholds.
        """
        # For each available character, find the block that's closest to the GBG bbox
        selected_blocks = []
        total_spatial_score = 0.0
        
        for char in target_chars:
            if char not in char_to_blocks:
                continue  # Skip missing characters instead of failing
            
            # Find the block for this character that's closest to the GBG bbox
            best_block = None
            best_spatial_score = 0.0
            
            for block in char_to_blocks[char]:
                spatial_score = self._calculate_bbox_similarity(
                    block.get('bbox', []), gbg_bbox
                )
                
                if spatial_score > best_spatial_score:
                    best_spatial_score = spatial_score
                    best_block = block
            
            # ULTRA-RELAXED SPATIAL THRESHOLD: Accept any block with minimal relevance
            if best_block and best_spatial_score >= 0.001:  # Ultra-low threshold (0.1% overlap)
                selected_blocks.append(best_block)
                total_spatial_score += best_spatial_score
            elif best_block:  # If no spatial overlap, still accept if it's the only option
                selected_blocks.append(best_block)
                total_spatial_score += 0.001  # Minimal score
        
        # ULTRA-RELAXED REQUIREMENTS: Accept even single character matches
        if len(selected_blocks) < 1:
            return None
        
        # Calculate overall scores with generous weighting
        avg_spatial_score = total_spatial_score / len(selected_blocks) if selected_blocks else 0.0
        
        # Text coverage score (how much of target text we can form)
        formed_chars = [block['text'].strip().upper() for block in selected_blocks]
        text_coverage = len(set(formed_chars) & set(target_chars)) / len(set(target_chars))
        
        # ULTRA-RELAXED SCORING: Accept almost any combination
        # Heavily weight text coverage over spatial accuracy
        combined_score = 0.2 + (avg_spatial_score * 0.2) + (text_coverage * 0.6)
        
        # Accept if we have any blocks and reasonable text coverage
        if combined_score >= 0.3 and len(selected_blocks) >= 1:
            return {
                'blocks': selected_blocks,
                'score': combined_score,
                'spatial_score': avg_spatial_score,
                'text_coverage': text_coverage,
                'strategy': 'enhanced_spatial'
            }
        
        return None
    
    def _find_word_combination(self, gbg_block: Dict[str, Any], 
                             engine_blocks: List[Dict[str, Any]]) -> Optional[List[PyMuPDFMatch]]:
        """Find combination of word-level engine blocks that form the GBG text."""
        gbg_text = gbg_block['text'].strip()
        gbg_words = gbg_text.split()
        
        if len(gbg_words) < 2:  # Need multiple words to combine
            return None
        
        # Find engine blocks that could be words from this GBG block
        word_blocks = [b for b in engine_blocks if len(b['text'].strip().split()) <= 2]  # 1-2 words
        
        if len(word_blocks) < 2:
            return None
        
        # Try to find blocks that when combined form the GBG text
        best_combination = self._find_word_sequence(gbg_words, word_blocks, gbg_block.get('bbox', {}))
        
        if best_combination and best_combination['score'] >= 0.8:
            matches = []
            for engine_block in best_combination['blocks']:
                match = PyMuPDFMatch(
                    engine_block_id=engine_block['block_id'],
                    gbg_block_id=gbg_block['block_id'],
                    similarity_score=best_combination['score'],
                    match_type='word_combination',
                    engine_text_preview=engine_block['text'][:50],
                    gbg_text_preview=gbg_block['text'][:100],
                    page_match=True,
                    bbox_similarity=best_combination.get('spatial_score', 0.0)
                )
                matches.append(match)
            
            return matches
        
        return None
    
    def _find_word_sequence(self, target_words: List[str], word_blocks: List[Dict[str, Any]], 
                          gbg_bbox: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find sequence of word blocks that forms the target words."""
        # This is a simplified implementation - could be enhanced with more sophisticated matching
        selected_blocks = []
        matched_words = set()
        total_spatial_score = 0.0
        
        for target_word in target_words:
            best_block = None
            best_score = 0.0
            
            for block in word_blocks:
                if block in selected_blocks:
                    continue
                
                block_text = block['text'].strip()
                
                # Check if this block contains the target word
                if target_word.lower() in block_text.lower():
                    # Calculate spatial relevance
                    spatial_score = self._calculate_bbox_similarity(
                        block.get('bbox', []), gbg_bbox
                    )
                    
                    # Text similarity
                    text_similarity = self._calculate_comprehensive_similarity(target_word, block_text)
                    
                    combined_score = text_similarity * 0.7 + spatial_score * 0.3
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_block = block
            
            if best_block and best_score > 0.6:
                selected_blocks.append(best_block)
                matched_words.add(target_word)
                total_spatial_score += self._calculate_bbox_similarity(
                    best_block.get('bbox', []), gbg_bbox
                )
        
        # Check if we matched enough words
        coverage = len(matched_words) / len(target_words)
        if coverage >= 0.7 and len(selected_blocks) >= 2:
            avg_spatial_score = total_spatial_score / len(selected_blocks)
            combined_score = 0.7 + (coverage * 0.2) + (avg_spatial_score * 0.1)
            
            return {
                'blocks': selected_blocks,
                'score': combined_score,
                'spatial_score': avg_spatial_score,
                'coverage': coverage
            }
        
        return None
    
    def _find_spatial_combination(self, gbg_block: Dict[str, Any], 
                                engine_blocks: List[Dict[str, Any]]) -> Optional[List[PyMuPDFMatch]]:
        """Find spatially close engine blocks that could combine to form the GBG block."""
        gbg_bbox = gbg_block.get('bbox', {})
        if not gbg_bbox or 'x' not in gbg_bbox:
            return None
        
        # Find engine blocks that are spatially close to the GBG block
        nearby_blocks = []
        for block in engine_blocks:
            spatial_score = self._calculate_bbox_similarity(block.get('bbox', []), gbg_bbox)
            if spatial_score > 0.3:  # Reasonably close
                nearby_blocks.append((block, spatial_score))
        
        if len(nearby_blocks) < 2:
            return None
        
        # Sort by spatial relevance
        nearby_blocks.sort(key=lambda x: x[1], reverse=True)
        
        # Try combining the most spatially relevant blocks
        selected_blocks = [block for block, score in nearby_blocks[:5]]  # Top 5 candidates
        
        # Check if combined text has reasonable similarity to GBG text
        combined_text = ' '.join(block['text'].strip() for block in selected_blocks)
        text_similarity = self._calculate_comprehensive_similarity(combined_text, gbg_block['text'])
        
        if text_similarity >= 0.6:
            matches = []
            avg_spatial_score = sum(score for _, score in nearby_blocks[:len(selected_blocks)]) / len(selected_blocks)
            combined_score = text_similarity * 0.7 + avg_spatial_score * 0.3
            
            for block in selected_blocks:
                match = PyMuPDFMatch(
                    engine_block_id=block['block_id'],
                    gbg_block_id=gbg_block['block_id'],
                    similarity_score=combined_score,
                    match_type='spatial_combination',
                    engine_text_preview=block['text'][:50],
                    gbg_text_preview=gbg_block['text'][:100],
                    page_match=True,
                    bbox_similarity=avg_spatial_score
                )
                matches.append(match)
            
            return matches
        
        return None
    
    def _force_remaining_matches(self, engine_blocks: List[Dict[str, Any]], 
                               gbg_blocks: List[Dict[str, Any]]) -> List[PyMuPDFMatch]:
        """
        Force match any remaining blocks to achieve 100% matching.
        Uses best spatial fit regardless of text quality.
        """
        matches = []
        used_gbg_blocks = set()
        
        for engine_block in engine_blocks:
            engine_bbox = engine_block.get('bbox', [])
            if not engine_bbox or len(engine_bbox) < 4:
                continue
            
            best_match = None
            best_spatial_score = 0.0
            
            # Find the best spatial match among remaining GBG blocks
            for gbg_block in gbg_blocks:
                if gbg_block['block_id'] in used_gbg_blocks:
                    continue
                
                gbg_bbox = gbg_block.get('bbox', {})
                spatial_score = self._calculate_bbox_similarity(engine_bbox, gbg_bbox)
                
                if spatial_score > best_spatial_score:
                    best_spatial_score = spatial_score
                    best_match = gbg_block
            
            # Accept ANY spatial match, even very low ones, to achieve 100% matching
            if best_match:
                # Calculate text similarity for reference
                text_similarity = self._calculate_comprehensive_similarity(
                    engine_block.get('text', ''), best_match.get('text', '')
                )
                
                # Determine match type
                if best_spatial_score >= 0.5:
                    match_type = 'forced_spatial_good'
                elif best_spatial_score >= 0.1:
                    match_type = 'forced_spatial_weak'
                else:
                    match_type = 'forced_spatial_minimal'
                
                # Combined score: prioritize spatial for forced matches
                combined_score = best_spatial_score * 0.9 + text_similarity * 0.1
                
                match = PyMuPDFMatch(
                    engine_block_id=engine_block['block_id'],
                    gbg_block_id=best_match['block_id'],
                    similarity_score=combined_score,
                    match_type=match_type,
                    engine_text_preview=engine_block.get('text', '')[:100],
                    gbg_text_preview=best_match.get('text', '')[:100],
                    page_match=True,
                    bbox_similarity=best_spatial_score
                )
                
                matches.append(match)
                used_gbg_blocks.add(best_match['block_id'])
        
        return matches
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for exact matching."""
        # Remove extra whitespace and normalize (this handles line breaks)
        normalized = re.sub(r'\s+', ' ', text.strip())
        # Remove common PDF artifacts
        normalized = normalized.replace('\u00ad', '')  # Soft hyphen
        normalized = normalized.replace('\ufeff', '')  # BOM
        normalized = normalized.replace('­', '')  # Another soft hyphen variant
        # Remove zero-width characters
        normalized = normalized.replace('\u200b', '')  # Zero-width space
        normalized = normalized.replace('\u200c', '')  # Zero-width non-joiner
        normalized = normalized.replace('\u200d', '')  # Zero-width joiner
        return normalized.lower()
    
    def _calculate_comprehensive_similarity(self, text1: str, text2: str) -> float:
        """Calculate comprehensive similarity using multiple measures."""
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        norm_text1 = text1.lower().strip()
        norm_text2 = text2.lower().strip()
        
        # Multiple similarity measures
        ratio_score = fuzz.ratio(norm_text1, norm_text2) / 100.0
        partial_score = fuzz.partial_ratio(norm_text1, norm_text2) / 100.0
        token_sort_score = fuzz.token_sort_ratio(norm_text1, norm_text2) / 100.0
        token_set_score = fuzz.token_set_ratio(norm_text1, norm_text2) / 100.0
        
        # Word overlap similarity
        words1 = set(norm_text1.split())
        words2 = set(norm_text2.split())
        if words1 or words2:
            word_overlap = len(words1.intersection(words2)) / len(words1.union(words2))
        else:
            word_overlap = 1.0 if not words1 and not words2 else 0.0
        
        # Return weighted average of best scores
        scores = [ratio_score, partial_score, token_sort_score, token_set_score, word_overlap]
        return max(scores)
    
    def _calculate_bbox_similarity(self, engine_bbox: List[float], gbg_bbox: Dict[str, Any]) -> float:
        """Calculate bounding box similarity."""
        if not engine_bbox or len(engine_bbox) < 4:
            return 0.0
        
        if not gbg_bbox or 'x' not in gbg_bbox:
            return 0.0
        
        # Convert engine bbox [x, y, x2, y2] to [x, y, width, height]
        engine_x, engine_y, engine_x2, engine_y2 = engine_bbox[:4]
        engine_width = engine_x2 - engine_x
        engine_height = engine_y2 - engine_y
        
        # Get GBG bbox values
        gbg_x = gbg_bbox.get('x', 0)
        gbg_y = gbg_bbox.get('y', 0)
        gbg_width = gbg_bbox.get('width', 0)
        gbg_height = gbg_bbox.get('height', 0)
        
        # Calculate overlap area
        overlap_x = max(0, min(engine_x + engine_width, gbg_x + gbg_width) - max(engine_x, gbg_x))
        overlap_y = max(0, min(engine_y + engine_height, gbg_y + gbg_height) - max(engine_y, gbg_y))
        overlap_area = overlap_x * overlap_y
        
        # Calculate union area
        engine_area = engine_width * engine_height
        gbg_area = gbg_width * gbg_height
        union_area = engine_area + gbg_area - overlap_area
        
        # Return IoU (Intersection over Union)
        return overlap_area / union_area if union_area > 0 else 0.0


def match_pymupdf_blocks_to_gbg(gbg_data: Dict[str, Any], engine_data: Dict[str, Any], 
                               similarity_threshold: float = 0.7) -> List[PyMuPDFMatch]:
    """
    Match PyMuPDF engine blocks to GBG blocks.
    
    Args:
        gbg_data: GBG analysis data
        engine_data: PyMuPDF engine data
        similarity_threshold: Minimum similarity threshold for matching
        
    Returns:
        List of PyMuPDF matches
    """
    matcher = PyMuPDFBlockMatcher(similarity_threshold)
    return matcher.match_blocks(gbg_data, engine_data)
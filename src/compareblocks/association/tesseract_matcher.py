# src/compareblocks/association/tesseract_matcher.py
"""
Specialized matcher for Tesseract OCR blocks to GBG blocks.
Handles OCR-specific issues like character corruption, mixed case, and artifacts.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re
from rapidfuzz import fuzz
from ..config.file_manager import file_manager


@dataclass
class TesseractMatch:
    """Result of Tesseract to GBG block matching."""
    engine_block_id: str
    gbg_block_id: str
    similarity_score: float
    match_type: str
    engine_text_preview: str
    gbg_text_preview: str
    page_match: bool
    bbox_similarity: float
    ocr_confidence: float = 0.0
    normalization_applied: str = ""


class TesseractBlockMatcher:
    """Specialized matcher for Tesseract OCR blocks with OCR-aware matching strategies."""
    
    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize Tesseract matcher with OCR-specific settings.
        
        Args:
            similarity_threshold: Minimum similarity score for matches (lower for OCR)
        """
        self.similarity_threshold = similarity_threshold
        self.ocr_artifacts = self._build_ocr_artifact_patterns()
    
    def _build_ocr_artifact_patterns(self) -> Dict[str, str]:
        """Build patterns for common OCR artifacts and their corrections."""
        return {
            # Common OCR character substitutions
            r'[|1Il]': 'I',  # Vertical bars, 1s, lowercase l often confused
            r'[0O]': 'O',    # Zero and O confusion
            r'[5S]': 'S',    # 5 and S confusion
            r'[8B]': 'B',    # 8 and B confusion
            r'[6G]': 'G',    # 6 and G confusion
            r'[2Z]': 'Z',    # 2 and Z confusion
            r'[9g]': 'g',    # 9 and g confusion
            
            # Common OCR noise patterns
            r'[^\w\s\-.,;:!?()[\]{}"\']': '',  # Remove unusual characters
            r'\s+': ' ',     # Normalize whitespace
            r'([A-Z])\s+([A-Z])': r'\1\2',  # Remove spaces between caps (like "U T A H" -> "UTAH")
        }
    
    def match_blocks_enhanced(self, gbg_data: Dict[str, Any], engine_data: Dict[str, Any]) -> List[TesseractMatch]:
        """Enhanced version of match_blocks with additional OCR-specific features."""
        return self.match_blocks(gbg_data, engine_data)
    
    def match_blocks(self, gbg_data: Dict[str, Any], engine_data: Dict[str, Any]) -> List[TesseractMatch]:
        """
        Match Tesseract engine blocks to GBG blocks using OCR-aware strategies.
        
        Args:
            gbg_data: GBG analysis data
            engine_data: Tesseract engine data
            
        Returns:
            List of TesseractMatch objects
        """
        matches = []
        
        # Extract GBG blocks organized by page
        gbg_blocks_by_page = self._extract_gbg_blocks_by_page(gbg_data)
        
        # Extract Tesseract blocks organized by page
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
                        'text_length': len(text_content)
                    })
            
            if blocks:
                blocks_by_page[page_num] = blocks
        
        return blocks_by_page
    
    def _extract_engine_blocks_by_page(self, engine_data: Dict[str, Any]) -> Dict[int, List[Dict[str, Any]]]:
        """Extract Tesseract engine blocks organized by page."""
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
                    'text_length': len(text),
                    'confidence': block.get('confidence', 0.0)
                })
        
        return blocks_by_page
    
    def _match_blocks_on_page(self, engine_blocks: List[Dict[str, Any]], 
                             gbg_blocks: List[Dict[str, Any]], page_num: int) -> List[TesseractMatch]:
        """Match blocks on a specific page using OCR-aware strategies."""
        matches = []
        used_gbg_blocks = set()
        used_engine_blocks = set()
        
        # Strategy 1: EXACT TEXT MATCHING (for clean OCR)
        for engine_block in engine_blocks:
            if engine_block['block_id'] in used_engine_blocks:
                continue
                
            for gbg_block in gbg_blocks:
                if gbg_block['block_id'] in used_gbg_blocks:
                    continue
                
                match = self._try_exact_match(engine_block, gbg_block)
                if match:
                    matches.append(match)
                    used_gbg_blocks.add(match.gbg_block_id)
                    used_engine_blocks.add(match.engine_block_id)
                    break
        
        # Strategy 2: OCR NORMALIZATION MATCHING (for corrupted OCR)
        remaining_engine_blocks = [b for b in engine_blocks if b['block_id'] not in used_engine_blocks]
        remaining_gbg_blocks = [b for b in gbg_blocks if b['block_id'] not in used_gbg_blocks]
        
        for engine_block in remaining_engine_blocks:
            best_match = None
            best_score = 0.0
            
            for gbg_block in remaining_gbg_blocks:
                match = self._try_ocr_normalized_match(engine_block, gbg_block)
                if match and match.similarity_score > best_score:
                    best_score = match.similarity_score
                    best_match = match
            
            if best_match and best_score >= self.similarity_threshold:
                matches.append(best_match)
                used_gbg_blocks.add(best_match.gbg_block_id)
                used_engine_blocks.add(best_match.engine_block_id)
        
        # Strategy 3: FUZZY CONTENT MATCHING (for heavily corrupted OCR)
        remaining_engine_blocks = [b for b in engine_blocks if b['block_id'] not in used_engine_blocks]
        remaining_gbg_blocks = [b for b in gbg_blocks if b['block_id'] not in used_gbg_blocks]
        
        for engine_block in remaining_engine_blocks:
            best_match = None
            best_score = 0.0
            
            for gbg_block in remaining_gbg_blocks:
                match = self._try_fuzzy_content_match(engine_block, gbg_block)
                if match and match.similarity_score > best_score:
                    best_score = match.similarity_score
                    best_match = match
            
            if best_match and best_score >= (self.similarity_threshold * 0.8):  # Lower threshold for fuzzy
                matches.append(best_match)
                used_gbg_blocks.add(best_match.gbg_block_id)
                used_engine_blocks.add(best_match.engine_block_id)
        
        # Strategy 4: PATTERN-BASED MATCHING (for headers/footers)
        remaining_engine_blocks = [b for b in engine_blocks if b['block_id'] not in used_engine_blocks]
        remaining_gbg_blocks = [b for b in gbg_blocks if b['block_id'] not in used_gbg_blocks]
        
        for engine_block in remaining_engine_blocks:
            best_match = None
            best_score = 0.0
            
            for gbg_block in remaining_gbg_blocks:
                match = self._try_pattern_match(engine_block, gbg_block)
                if match and match.similarity_score > best_score:
                    best_score = match.similarity_score
                    best_match = match
            
            if best_match and best_score >= (self.similarity_threshold * 0.7):  # Even lower for patterns
                matches.append(best_match)
                used_gbg_blocks.add(best_match.gbg_block_id)
                used_engine_blocks.add(best_match.engine_block_id)
        
        return matches
    
    def _try_exact_match(self, engine_block: Dict[str, Any], gbg_block: Dict[str, Any]) -> Optional[TesseractMatch]:
        """Try exact text matching (for clean OCR)."""
        engine_text = engine_block['text'].strip()
        gbg_text = gbg_block['text'].strip()
        
        # Normalize whitespace for comparison
        engine_normalized = re.sub(r'\s+', ' ', engine_text).lower()
        gbg_normalized = re.sub(r'\s+', ' ', gbg_text).lower()
        
        if engine_normalized == gbg_normalized:
            return TesseractMatch(
                engine_block_id=engine_block['block_id'],
                gbg_block_id=gbg_block['block_id'],
                similarity_score=1.0,
                match_type='exact_text',
                engine_text_preview=engine_text[:100],
                gbg_text_preview=gbg_text[:100],
                page_match=True,
                bbox_similarity=self._calculate_bbox_similarity(
                    engine_block.get('bbox', []), gbg_block.get('bbox', {})
                ),
                ocr_confidence=engine_block.get('confidence', 0.0),
                normalization_applied='whitespace'
            )
        
        return None
    
    def _try_ocr_normalized_match(self, engine_block: Dict[str, Any], gbg_block: Dict[str, Any]) -> Optional[TesseractMatch]:
        """Try OCR normalization matching (for corrupted OCR)."""
        engine_text = engine_block['text'].strip()
        gbg_text = gbg_block['text'].strip()
        
        # Apply OCR normalization
        engine_normalized = self._normalize_ocr_text(engine_text)
        gbg_normalized = self._normalize_ocr_text(gbg_text)
        
        # Calculate similarity after normalization
        similarity = fuzz.ratio(engine_normalized, gbg_normalized) / 100.0
        
        if similarity >= 0.8:  # High similarity after normalization
            return TesseractMatch(
                engine_block_id=engine_block['block_id'],
                gbg_block_id=gbg_block['block_id'],
                similarity_score=similarity,
                match_type='ocr_normalized',
                engine_text_preview=engine_text[:100],
                gbg_text_preview=gbg_text[:100],
                page_match=True,
                bbox_similarity=self._calculate_bbox_similarity(
                    engine_block.get('bbox', []), gbg_block.get('bbox', {})
                ),
                ocr_confidence=engine_block.get('confidence', 0.0),
                normalization_applied='ocr_artifacts'
            )
        
        return None
    
    def _try_fuzzy_content_match(self, engine_block: Dict[str, Any], gbg_block: Dict[str, Any]) -> Optional[TesseractMatch]:
        """Try fuzzy content matching (for heavily corrupted OCR)."""
        engine_text = engine_block['text'].strip()
        gbg_text = gbg_block['text'].strip()
        
        # Extract key content words (ignore OCR artifacts)
        engine_words = self._extract_content_words(engine_text)
        gbg_words = self._extract_content_words(gbg_text)
        
        if not engine_words or not gbg_words:
            return None
        
        # Calculate word-level similarity
        engine_content = ' '.join(engine_words)
        gbg_content = ' '.join(gbg_words)
        
        similarity = fuzz.token_sort_ratio(engine_content, gbg_content) / 100.0
        
        if similarity >= 0.7:  # Moderate similarity for content words
            return TesseractMatch(
                engine_block_id=engine_block['block_id'],
                gbg_block_id=gbg_block['block_id'],
                similarity_score=similarity,
                match_type='fuzzy_content',
                engine_text_preview=engine_text[:100],
                gbg_text_preview=gbg_text[:100],
                page_match=True,
                bbox_similarity=self._calculate_bbox_similarity(
                    engine_block.get('bbox', []), gbg_block.get('bbox', {})
                ),
                ocr_confidence=engine_block.get('confidence', 0.0),
                normalization_applied='content_words'
            )
        
        return None
    
    def _try_pattern_match(self, engine_block: Dict[str, Any], gbg_block: Dict[str, Any]) -> Optional[TesseractMatch]:
        """Try pattern-based matching (for headers/footers)."""
        engine_text = engine_block['text'].strip()
        gbg_text = gbg_block['text'].strip()
        
        # Extract patterns (common phrases, repeated elements)
        engine_patterns = self._extract_text_patterns(engine_text)
        gbg_patterns = self._extract_text_patterns(gbg_text)
        
        # Check for pattern overlap
        common_patterns = engine_patterns.intersection(gbg_patterns)
        
        if common_patterns:
            # Calculate pattern similarity
            pattern_score = len(common_patterns) / max(len(engine_patterns), len(gbg_patterns))
            
            if pattern_score >= 0.5:  # At least 50% pattern overlap
                return TesseractMatch(
                    engine_block_id=engine_block['block_id'],
                    gbg_block_id=gbg_block['block_id'],
                    similarity_score=pattern_score,
                    match_type='pattern_based',
                    engine_text_preview=engine_text[:100],
                    gbg_text_preview=gbg_text[:100],
                    page_match=True,
                    bbox_similarity=self._calculate_bbox_similarity(
                        engine_block.get('bbox', []), gbg_block.get('bbox', {})
                    ),
                    ocr_confidence=engine_block.get('confidence', 0.0),
                    normalization_applied='pattern_extraction'
                )
        
        return None
    
    def _normalize_ocr_text(self, text: str) -> str:
        """Normalize text to handle common OCR artifacts."""
        normalized = text.lower()
        
        # Apply OCR artifact corrections
        for pattern, replacement in self.ocr_artifacts.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _extract_content_words(self, text: str) -> List[str]:
        """Extract meaningful content words, filtering out OCR artifacts."""
        # Remove obvious OCR artifacts and noise
        cleaned = re.sub(r'[^\w\s\-]', ' ', text)  # Keep only word chars, spaces, hyphens
        cleaned = re.sub(r'\b[A-Z]{1,2}\b', '', cleaned)  # Remove single/double caps (often artifacts)
        cleaned = re.sub(r'\b\d+\b', '', cleaned)  # Remove standalone numbers
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Extract words that are likely real content
        words = []
        for word in cleaned.split():
            if len(word) >= 3 and word.isalpha():  # At least 3 chars, all letters
                words.append(word.lower())
        
        return words
    
    def _extract_text_patterns(self, text: str) -> set:
        """Extract common patterns from text (phrases, repeated elements)."""
        patterns = set()
        
        # Common document patterns
        common_phrases = [
            'utah state', 'standards', 'english language arts', 'grade', 'strand',
            'speaking', 'listening', 'reading', 'writing', 'language',
            'standard', 'board of education', 'adopted', 'may 2023'
        ]
        
        text_lower = text.lower()
        for phrase in common_phrases:
            if phrase in text_lower:
                patterns.add(phrase)
        
        # Extract capitalized sequences (likely titles/headers)
        caps_sequences = re.findall(r'\b[A-Z][A-Z\s]{2,}\b', text)
        for seq in caps_sequences:
            if len(seq.strip()) >= 4:
                patterns.add(seq.strip().lower())
        
        return patterns
    
    def _calculate_bbox_similarity(self, engine_bbox: List[float], gbg_bbox: Dict[str, float]) -> float:
        """Calculate bounding box similarity between engine and GBG blocks."""
        if not engine_bbox or len(engine_bbox) < 4 or not gbg_bbox:
            return 0.0
        
        # Convert engine bbox [x1, y1, x2, y2] to center and dimensions
        engine_x = (engine_bbox[0] + engine_bbox[2]) / 2
        engine_y = (engine_bbox[1] + engine_bbox[3]) / 2
        engine_w = engine_bbox[2] - engine_bbox[0]
        engine_h = engine_bbox[3] - engine_bbox[1]
        
        # Get GBG bbox center and dimensions
        gbg_x = gbg_bbox.get('center', [0, 0])[0] if isinstance(gbg_bbox.get('center'), list) else gbg_bbox.get('x', 0)
        gbg_y = gbg_bbox.get('center', [0, 0])[1] if isinstance(gbg_bbox.get('center'), list) else gbg_bbox.get('y', 0)
        gbg_w = gbg_bbox.get('width', 0)
        gbg_h = gbg_bbox.get('height', 0)
        
        # Calculate overlap
        x_overlap = max(0, min(engine_x + engine_w/2, gbg_x + gbg_w/2) - max(engine_x - engine_w/2, gbg_x - gbg_w/2))
        y_overlap = max(0, min(engine_y + engine_h/2, gbg_y + gbg_h/2) - max(engine_y - engine_h/2, gbg_y - gbg_h/2))
        
        overlap_area = x_overlap * y_overlap
        engine_area = engine_w * engine_h
        gbg_area = gbg_w * gbg_h
        
        if engine_area <= 0 or gbg_area <= 0:
            return 0.0
        
        # Calculate IoU (Intersection over Union)
        union_area = engine_area + gbg_area - overlap_area
        if union_area <= 0:
            return 0.0
        
        return overlap_area / union_area
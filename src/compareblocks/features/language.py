# src/compareblocks/features/language.py
"""
Language fitness scoring for text variations.
Provides language detection and out-of-vocabulary (OOV) analysis.
"""

import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass
import string


@dataclass
class LanguageFeatures:
    """Language fitness features for text variations."""
    detected_language: str
    language_confidence: float
    word_count: int
    words_in_language: int
    oov_count: int
    word_in_language_rate: float
    oov_rate: float
    fitness_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert features to dictionary format."""
        return {
            'detected_language': self.detected_language,
            'language_confidence': self.language_confidence,
            'word_count': self.word_count,
            'words_in_language': self.words_in_language,
            'oov_count': self.oov_count,
            'word_in_language_rate': self.word_in_language_rate,
            'oov_rate': self.oov_rate,
            'fitness_score': self.fitness_score
        }


class LanguageFeatureExtractor:
    """Extracts language fitness features from text variations."""
    
    def __init__(self):
        """Initialize the language feature extractor."""
        # Common English words for basic language detection
        self._english_words = self._load_common_english_words()
        self._language_detector = None
        self._initialize_language_detector()
    
    def _load_common_english_words(self) -> Set[str]:
        """Load a set of common English words for basic language detection."""
        # Common English words (subset for basic detection)
        common_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have',
            'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you',
            'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they',
            'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my',
            'one', 'all', 'would', 'there', 'their', 'what', 'so',
            'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go',
            'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just',
            'him', 'know', 'take', 'people', 'into', 'year', 'your',
            'good', 'some', 'could', 'them', 'see', 'other', 'than',
            'then', 'now', 'look', 'only', 'come', 'its', 'over',
            'think', 'also', 'back', 'after', 'use', 'two', 'how',
            'our', 'work', 'first', 'well', 'way', 'even', 'new',
            'want', 'because', 'any', 'these', 'give', 'day', 'most',
            'us', 'is', 'was', 'are', 'been', 'has', 'had', 'were',
            'said', 'each', 'which', 'their', 'time', 'will', 'about',
            'if', 'up', 'out', 'many', 'then', 'them', 'these', 'so',
            'some', 'her', 'would', 'make', 'like', 'into', 'him',
            'two', 'more', 'very', 'what', 'know', 'just', 'first',
            'get', 'over', 'think', 'where', 'much', 'go', 'well',
            'were', 'been', 'through', 'when', 'much', 'before',
            'right', 'too', 'any', 'same', 'tell', 'boy', 'follow',
            'came', 'want', 'show', 'also', 'around', 'farm', 'three',
            'small', 'set', 'put', 'end', 'why', 'again', 'turn',
            'here', 'off', 'went', 'old', 'number', 'great', 'tell',
            'men', 'say', 'small', 'every', 'found', 'still', 'between',
            'name', 'should', 'home', 'big', 'give', 'air', 'line',
            'set', 'own', 'under', 'read', 'last', 'never', 'us',
            'left', 'end', 'along', 'while', 'might', 'next', 'sound',
            'below', 'saw', 'something', 'thought', 'both', 'few',
            'those', 'always', 'looked', 'show', 'large', 'often',
            'together', 'asked', 'house', 'don', 'world', 'going',
            'want', 'school', 'important', 'until', 'form', 'food',
            'keep', 'children', 'feet', 'land', 'side', 'without',
            'boy', 'once', 'animal', 'life', 'enough', 'took', 'four',
            'head', 'above', 'kind', 'began', 'almost', 'live', 'page',
            'got', 'earth', 'need', 'far', 'hand', 'high', 'year',
            'mother', 'light', 'country', 'father', 'let', 'night',
            'picture', 'being', 'study', 'second', 'soon', 'story',
            'since', 'white', 'ever', 'paper', 'hard', 'near', 'sentence',
            'better', 'best', 'across', 'during', 'today', 'however',
            'sure', 'knew', 'it', 'try', 'told', 'young', 'sun',
            'thing', 'whole', 'hear', 'example', 'heard', 'several',
            'change', 'answer', 'room', 'sea', 'against', 'top',
            'turned', 'learn', 'point', 'city', 'play', 'toward',
            'five', 'himself', 'usually', 'money', 'seen', 'didn',
            'car', 'morning', 'i', 'long', 'movement', 'right', 'black',
            'best', 'upon', 'several', 'become', 'side', 'hundred',
            'what', 'contain', 'course', 'surface', 'produce', 'building',
            'ocean', 'class', 'note', 'nothing', 'rest', 'carefully',
            'scientists', 'inside', 'wheels', 'stay', 'green', 'known',
            'island', 'week', 'less', 'machine', 'base', 'ago', 'stood',
            'plane', 'system', 'behind', 'ran', 'round', 'boat', 'game',
            'force', 'brought', 'heat', 'nothing', 'quite', 'person',
            'size', 'heard', 'best', 'hour', 'better', 'during', 'hundred',
            'am', 'remember', 'step', 'early', 'hold', 'west', 'ground',
            'interest', 'reach', 'fast', 'five', 'sing', 'listen',
            'six', 'table', 'travel', 'less', 'morning', 'ten', 'simple',
            'several', 'vowel', 'toward', 'war', 'lay', 'against',
            'pattern', 'slow', 'center', 'love', 'person', 'money',
            'serve', 'appear', 'road', 'map', 'science', 'rule',
            'govern', 'pull', 'cold', 'notice', 'voice', 'fall',
            'power', 'town', 'fine', 'certain', 'fly', 'unit', 'lead',
            'cry', 'dark', 'machine', 'note', 'wait', 'plan', 'figure',
            'star', 'box', 'noun', 'field', 'rest', 'correct', 'able',
            'pound', 'done', 'beauty', 'drive', 'stood', 'contain',
            'front', 'teach', 'week', 'final', 'gave', 'green', 'oh',
            'quick', 'develop', 'sleep', 'warm', 'free', 'minute',
            'strong', 'special', 'mind', 'behind', 'clear', 'tail',
            'produce', 'fact', 'street', 'inch', 'lot', 'nothing',
            'course', 'stay', 'wheel', 'full', 'force', 'blue', 'object',
            'decide', 'surface', 'deep', 'moon', 'island', 'foot',
            'yet', 'busy', 'test', 'record', 'boat', 'common', 'gold',
            'possible', 'plane', 'age', 'dry', 'wonder', 'laugh',
            'thousands', 'ago', 'ran', 'check', 'game', 'shape',
            'yes', 'hot', 'miss', 'brought', 'heat', 'snow', 'bed',
            'bring', 'sit', 'perhaps', 'fill', 'east', 'weight',
            'language', 'among'
        }
        return common_words
    
    def _initialize_language_detector(self):
        """Initialize language detection if langdetect is available."""
        try:
            import langdetect
            self._language_detector = langdetect
        except ImportError:
            # Fallback to basic detection if langdetect not available
            self._language_detector = None
    
    def _clean_text_for_analysis(self, text: str) -> str:
        """Clean text for language analysis."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove non-alphabetic characters for word analysis
        # Keep spaces and basic punctuation
        cleaned = re.sub(r'[^\w\s\'-]', ' ', cleaned)
        
        return cleaned.lower()
    
    def _extract_words(self, text: str) -> List[str]:
        """Extract words from text for analysis."""
        cleaned_text = self._clean_text_for_analysis(text)
        
        # Split into words and filter out empty strings and single characters
        words = [word.strip(string.punctuation) for word in cleaned_text.split()]
        words = [word for word in words if len(word) > 1 and word.isalpha()]
        
        return words
    
    def _detect_language(self, text: str) -> tuple[str, float]:
        """
        Detect language of text.
        
        Returns:
            Tuple of (language_code, confidence)
        """
        if not text or len(text.strip()) < 10:
            return 'unknown', 0.0
        
        if self._language_detector:
            try:
                # Use langdetect if available
                detected_lang = self._language_detector.detect(text)
                # Get confidence (langdetect doesn't provide confidence directly)
                # Use a simple heuristic based on text length and content
                confidence = min(0.9, len(text) / 100.0)
                return detected_lang, confidence
            except:
                # Fall back to basic detection
                pass
        
        # Basic English detection using common words
        words = self._extract_words(text)
        if not words:
            return 'unknown', 0.0
        
        english_word_count = sum(1 for word in words if word in self._english_words)
        english_ratio = english_word_count / len(words) if words else 0.0
        
        if english_ratio > 0.3:  # If more than 30% are common English words
            confidence = min(0.8, english_ratio)
            return 'en', confidence
        else:
            return 'unknown', 0.2
    
    def _calculate_word_in_language_rate(self, words: List[str], language: str) -> tuple[int, int]:
        """
        Calculate how many words are recognized as being in the detected language.
        
        Returns:
            Tuple of (words_in_language_count, total_word_count)
        """
        if not words:
            return 0, 0
        
        if language == 'en':
            # Use English word list
            words_in_language = sum(1 for word in words if word in self._english_words)
        else:
            # For other languages, use a simple heuristic
            # Words that look like they could be in a language (no numbers, reasonable length)
            words_in_language = sum(1 for word in words 
                                  if len(word) >= 2 and word.isalpha() and not word.isdigit())
        
        return words_in_language, len(words)
    
    def extract_language_features(self, text: str) -> LanguageFeatures:
        """
        Extract language fitness features from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            LanguageFeatures object with computed metrics
        """
        if not text or not text.strip():
            return LanguageFeatures(
                detected_language='unknown',
                language_confidence=0.0,
                word_count=0,
                words_in_language=0,
                oov_count=0,
                word_in_language_rate=0.0,
                oov_rate=0.0,
                fitness_score=0.0
            )
        
        # Detect language
        detected_language, language_confidence = self._detect_language(text)
        
        # Extract words
        words = self._extract_words(text)
        word_count = len(words)
        
        if word_count == 0:
            return LanguageFeatures(
                detected_language=detected_language,
                language_confidence=language_confidence,
                word_count=0,
                words_in_language=0,
                oov_count=0,
                word_in_language_rate=0.0,
                oov_rate=0.0,
                fitness_score=0.0
            )
        
        # Calculate word-in-language statistics
        words_in_language, total_words = self._calculate_word_in_language_rate(words, detected_language)
        oov_count = total_words - words_in_language
        
        word_in_language_rate = words_in_language / total_words if total_words > 0 else 0.0
        oov_rate = oov_count / total_words if total_words > 0 else 0.0
        
        # Calculate overall fitness score
        # Combine language confidence and word-in-language rate
        fitness_score = (language_confidence * 0.4 + word_in_language_rate * 0.6)
        
        # Penalize high OOV rates
        if oov_rate > 0.5:  # More than 50% OOV
            fitness_score *= (1.0 - (oov_rate - 0.5))
        
        fitness_score = max(0.0, min(1.0, fitness_score))
        
        return LanguageFeatures(
            detected_language=detected_language,
            language_confidence=language_confidence,
            word_count=word_count,
            words_in_language=words_in_language,
            oov_count=oov_count,
            word_in_language_rate=word_in_language_rate,
            oov_rate=oov_rate,
            fitness_score=fitness_score
        )
    
    def extract_features_for_variations(self, variations: List[str]) -> List[LanguageFeatures]:
        """
        Extract language features for multiple variations.
        
        Args:
            variations: List of text variations
            
        Returns:
            List of LanguageFeatures
        """
        return [self.extract_language_features(text) for text in variations]
    
    def get_language_statistics(self, variations: List[str]) -> Dict[str, Any]:
        """
        Get language statistics for a set of variations.
        
        Args:
            variations: List of text variations
            
        Returns:
            Dictionary with language statistics
        """
        if not variations:
            return {
                'total_variations': 0,
                'languages_detected': {},
                'avg_fitness_score': 0.0,
                'avg_word_in_language_rate': 0.0,
                'avg_oov_rate': 0.0,
                'fitness_variance': 0.0
            }
        
        features_list = self.extract_features_for_variations(variations)
        
        # Count languages
        languages = {}
        fitness_scores = []
        word_rates = []
        oov_rates = []
        
        for features in features_list:
            lang = features.detected_language
            languages[lang] = languages.get(lang, 0) + 1
            fitness_scores.append(features.fitness_score)
            word_rates.append(features.word_in_language_rate)
            oov_rates.append(features.oov_rate)
        
        import statistics
        
        return {
            'total_variations': len(variations),
            'languages_detected': languages,
            'avg_fitness_score': statistics.mean(fitness_scores) if fitness_scores else 0.0,
            'avg_word_in_language_rate': statistics.mean(word_rates) if word_rates else 0.0,
            'avg_oov_rate': statistics.mean(oov_rates) if oov_rates else 0.0,
            'fitness_variance': statistics.variance(fitness_scores) if len(fitness_scores) > 1 else 0.0
        }
    
    def compare_language_fitness(self, variations: List[str]) -> Dict[str, float]:
        """
        Compare language fitness scores across variations.
        
        Args:
            variations: List of text variations
            
        Returns:
            Dictionary mapping variation index to relative fitness score
        """
        if not variations:
            return {}
        
        features_list = self.extract_features_for_variations(variations)
        fitness_scores = [f.fitness_score for f in features_list]
        
        if not fitness_scores:
            return {str(i): 0.0 for i in range(len(variations))}
        
        max_score = max(fitness_scores)
        
        # Normalize scores relative to the best one
        relative_scores = {}
        for i, score in enumerate(fitness_scores):
            if max_score > 0:
                relative_scores[str(i)] = score / max_score
            else:
                relative_scores[str(i)] = 0.0
        
        return relative_scores
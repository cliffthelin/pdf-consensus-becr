# src/compareblocks/features/context.py
"""
Context similarity features for text variations.
Analyzes semantic coherence and subject similarity within document context.
"""

import re
from typing import List, Dict, Any, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter
import math


@dataclass
class ContextFeatures:
    """Context similarity features for text variations."""
    subject_keywords: List[str]
    context_similarity_score: float
    semantic_coherence_score: float
    topic_consistency_score: float
    keyword_overlap_ratio: float
    context_relevance_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert features to dictionary format."""
        return {
            'subject_keywords': self.subject_keywords,
            'context_similarity_score': self.context_similarity_score,
            'semantic_coherence_score': self.semantic_coherence_score,
            'topic_consistency_score': self.topic_consistency_score,
            'keyword_overlap_ratio': self.keyword_overlap_ratio,
            'context_relevance_score': self.context_relevance_score
        }


class ContextSimilarityExtractor:
    """Extracts context similarity features from text variations."""
    
    def __init__(self):
        """Initialize the context similarity extractor."""
        # Common stop words to filter out
        self.stop_words = {
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
            'said', 'each', 'much', 'before', 'right', 'too', 'same',
            'tell', 'should', 'never', 'here', 'off', 'went', 'old',
            'number', 'great', 'men', 'small', 'every', 'found',
            'still', 'between', 'name', 'home', 'big', 'give', 'air',
            'line', 'set', 'own', 'under', 'read', 'last', 'left',
            'end', 'along', 'while', 'might', 'next', 'sound', 'below',
            'saw', 'something', 'thought', 'both', 'few', 'those',
            'always', 'looked', 'show', 'large', 'often', 'together',
            'asked', 'house', 'world', 'going', 'school', 'important',
            'until', 'form', 'food', 'keep', 'children', 'feet',
            'land', 'side', 'without', 'boy', 'once', 'animal', 'life',
            'enough', 'took', 'four', 'head', 'above', 'kind', 'began',
            'almost', 'live', 'page', 'got', 'earth', 'need', 'far',
            'hand', 'high', 'mother', 'light', 'country', 'father',
            'let', 'night', 'picture', 'being', 'study', 'second',
            'soon', 'story', 'since', 'white', 'ever', 'paper', 'hard',
            'near', 'sentence', 'better', 'best', 'across', 'during',
            'today', 'however', 'sure', 'knew', 'try', 'told', 'young',
            'sun', 'thing', 'whole', 'hear', 'example', 'heard',
            'several', 'change', 'answer', 'room', 'sea', 'against',
            'top', 'turned', 'learn', 'point', 'city', 'play', 'toward',
            'five', 'himself', 'usually', 'money', 'seen', 'car',
            'morning', 'long', 'movement', 'black', 'upon', 'become',
            'hundred', 'contain', 'course', 'surface', 'produce',
            'building', 'ocean', 'class', 'note', 'nothing', 'rest',
            'carefully', 'scientists', 'inside', 'wheels', 'stay',
            'green', 'known', 'island', 'week', 'less', 'machine',
            'base', 'ago', 'stood', 'plane', 'system', 'behind', 'ran',
            'round', 'boat', 'game', 'force', 'brought', 'heat',
            'quite', 'person', 'size', 'hour', 'step', 'early', 'hold',
            'west', 'ground', 'interest', 'reach', 'fast', 'sing',
            'listen', 'six', 'table', 'travel', 'morning', 'ten',
            'simple', 'vowel', 'war', 'lay', 'pattern', 'slow',
            'center', 'love', 'serve', 'appear', 'road', 'map',
            'science', 'rule', 'govern', 'pull', 'cold', 'notice',
            'voice', 'fall', 'power', 'town', 'fine', 'certain', 'fly',
            'unit', 'lead', 'cry', 'dark', 'wait', 'plan', 'figure',
            'star', 'box', 'noun', 'field', 'correct', 'able', 'pound',
            'done', 'beauty', 'drive', 'contain', 'front', 'teach',
            'final', 'gave', 'oh', 'quick', 'develop', 'sleep', 'warm',
            'free', 'minute', 'strong', 'special', 'mind', 'clear',
            'tail', 'fact', 'street', 'inch', 'lot', 'stay', 'wheel',
            'full', 'blue', 'object', 'decide', 'deep', 'moon', 'foot',
            'yet', 'busy', 'test', 'record', 'common', 'gold', 'possible',
            'age', 'dry', 'wonder', 'laugh', 'thousands', 'check',
            'shape', 'yes', 'hot', 'miss', 'snow', 'bed', 'bring',
            'sit', 'perhaps', 'fill', 'east', 'weight', 'language',
            'among'
        }
        
        # Educational/academic keywords that might be relevant for document context
        self.domain_keywords = {
            'education': {
                'education', 'learning', 'student', 'teacher', 'school',
                'curriculum', 'instruction', 'assessment', 'grade',
                'classroom', 'academic', 'study', 'knowledge', 'skill',
                'standard', 'objective', 'lesson', 'course', 'program',
                'development', 'achievement', 'performance', 'literacy',
                'mathematics', 'science', 'reading', 'writing', 'language',
                'arts', 'social', 'studies', 'history', 'geography',
                'literature', 'comprehension', 'vocabulary', 'grammar',
                'phonics', 'fluency', 'critical', 'thinking', 'problem',
                'solving', 'analysis', 'synthesis', 'evaluation'
            }
        }
    
    def _extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """
        Extract meaningful keywords from text.
        
        Args:
            text: Input text
            min_length: Minimum word length to consider
            
        Returns:
            List of keywords
        """
        if not text:
            return []
        
        # Clean and normalize text
        cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = cleaned_text.split()
        
        # Filter words
        keywords = []
        for word in words:
            if (len(word) >= min_length and 
                word not in self.stop_words and 
                word.isalpha() and 
                not word.isdigit()):
                keywords.append(word)
        
        return keywords
    
    def _calculate_keyword_overlap(self, keywords1: List[str], keywords2: List[str]) -> float:
        """
        Calculate overlap ratio between two keyword lists.
        
        Args:
            keywords1: First keyword list
            keywords2: Second keyword list
            
        Returns:
            Overlap ratio (0.0 to 1.0)
        """
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(keywords1)
        set2 = set(keywords2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_cosine_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """
        Calculate cosine similarity between two keyword lists.
        
        Args:
            keywords1: First keyword list
            keywords2: Second keyword list
            
        Returns:
            Cosine similarity (0.0 to 1.0)
        """
        if not keywords1 or not keywords2:
            return 0.0
        
        # Create word frequency vectors
        all_words = set(keywords1 + keywords2)
        
        vector1 = []
        vector2 = []
        
        counter1 = Counter(keywords1)
        counter2 = Counter(keywords2)
        
        for word in all_words:
            vector1.append(counter1.get(word, 0))
            vector2.append(counter2.get(word, 0))
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = math.sqrt(sum(a * a for a in vector1))
        magnitude2 = math.sqrt(sum(b * b for b in vector2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _identify_domain_context(self, keywords: List[str]) -> Tuple[str, float]:
        """
        Identify the domain context of keywords.
        
        Args:
            keywords: List of keywords
            
        Returns:
            Tuple of (domain_name, confidence_score)
        """
        if not keywords:
            return 'unknown', 0.0
        
        keyword_set = set(keywords)
        best_domain = 'unknown'
        best_score = 0.0
        
        for domain, domain_words in self.domain_keywords.items():
            overlap = len(keyword_set.intersection(domain_words))
            score = overlap / len(keywords) if keywords else 0.0
            
            if score > best_score:
                best_score = score
                best_domain = domain
        
        return best_domain, best_score
    
    def _calculate_semantic_coherence(self, text: str) -> float:
        """
        Calculate semantic coherence of text based on keyword consistency.
        
        Args:
            text: Input text
            
        Returns:
            Coherence score (0.0 to 1.0)
        """
        if not text:
            return 0.0
        
        keywords = self._extract_keywords(text)
        if len(keywords) < 2:
            return 1.0 if keywords else 0.0
        
        # Calculate keyword frequency distribution
        keyword_counts = Counter(keywords)
        total_keywords = len(keywords)
        unique_keywords = len(keyword_counts)
        
        # Calculate entropy of keyword distribution
        entropy = 0.0
        for count in keyword_counts.values():
            probability = count / total_keywords
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        # Normalize entropy (higher entropy = lower coherence)
        max_entropy = math.log2(unique_keywords) if unique_keywords > 1 else 0.0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        
        # Coherence is inverse of normalized entropy
        coherence = 1.0 - normalized_entropy
        
        # Bonus for domain-specific keywords
        domain, domain_confidence = self._identify_domain_context(keywords)
        if domain != 'unknown':
            coherence = min(1.0, coherence + domain_confidence * 0.2)
        
        return coherence
    
    def extract_context_features(self, text: str, context_texts: Optional[List[str]] = None) -> ContextFeatures:
        """
        Extract context similarity features from text.
        
        Args:
            text: The text to analyze
            context_texts: Optional list of context texts for comparison
            
        Returns:
            ContextFeatures object with computed metrics
        """
        if not text:
            return ContextFeatures(
                subject_keywords=[],
                context_similarity_score=0.0,
                semantic_coherence_score=0.0,
                topic_consistency_score=0.0,
                keyword_overlap_ratio=0.0,
                context_relevance_score=0.0
            )
        
        # Extract keywords from the text
        keywords = self._extract_keywords(text)
        
        # Calculate semantic coherence
        semantic_coherence_score = self._calculate_semantic_coherence(text)
        
        # Initialize context-dependent scores
        context_similarity_score = 0.0
        topic_consistency_score = 0.0
        keyword_overlap_ratio = 0.0
        context_relevance_score = semantic_coherence_score  # Default to coherence
        
        if context_texts:
            # Calculate similarity with context texts
            similarities = []
            overlaps = []
            
            for context_text in context_texts:
                if context_text and context_text != text:
                    context_keywords = self._extract_keywords(context_text)
                    
                    # Calculate similarity metrics
                    cosine_sim = self._calculate_cosine_similarity(keywords, context_keywords)
                    overlap = self._calculate_keyword_overlap(keywords, context_keywords)
                    
                    similarities.append(cosine_sim)
                    overlaps.append(overlap)
            
            if similarities:
                context_similarity_score = sum(similarities) / len(similarities)
                keyword_overlap_ratio = sum(overlaps) / len(overlaps)
                
                # Topic consistency based on variance in similarities
                if len(similarities) > 1:
                    mean_sim = context_similarity_score
                    variance = sum((s - mean_sim) ** 2 for s in similarities) / len(similarities)
                    topic_consistency_score = max(0.0, 1.0 - variance)
                else:
                    topic_consistency_score = context_similarity_score
                
                # Overall context relevance
                context_relevance_score = (
                    semantic_coherence_score * 0.4 +
                    context_similarity_score * 0.4 +
                    topic_consistency_score * 0.2
                )
        
        return ContextFeatures(
            subject_keywords=keywords[:10],  # Top 10 keywords
            context_similarity_score=context_similarity_score,
            semantic_coherence_score=semantic_coherence_score,
            topic_consistency_score=topic_consistency_score,
            keyword_overlap_ratio=keyword_overlap_ratio,
            context_relevance_score=context_relevance_score
        )
    
    def extract_features_for_variations(self, variations: List[str], 
                                      context_texts: Optional[List[str]] = None) -> List[ContextFeatures]:
        """
        Extract context features for multiple variations.
        
        Args:
            variations: List of text variations
            context_texts: Optional list of context texts for comparison
            
        Returns:
            List of ContextFeatures
        """
        return [self.extract_context_features(text, context_texts) for text in variations]
    
    def compare_context_relevance(self, variations: List[str], 
                                context_texts: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Compare context relevance scores across variations.
        
        Args:
            variations: List of text variations
            context_texts: Optional list of context texts for comparison
            
        Returns:
            Dictionary mapping variation index to relative relevance score
        """
        if not variations:
            return {}
        
        features_list = self.extract_features_for_variations(variations, context_texts)
        relevance_scores = [f.context_relevance_score for f in features_list]
        
        if not relevance_scores:
            return {str(i): 0.0 for i in range(len(variations))}
        
        max_score = max(relevance_scores)
        
        # Normalize scores relative to the best one
        relative_scores = {}
        for i, score in enumerate(relevance_scores):
            if max_score > 0:
                relative_scores[str(i)] = score / max_score
            else:
                relative_scores[str(i)] = 0.0
        
        return relative_scores
    
    def get_context_statistics(self, variations: List[str], 
                             context_texts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get context statistics for a set of variations.
        
        Args:
            variations: List of text variations
            context_texts: Optional list of context texts for comparison
            
        Returns:
            Dictionary with context statistics
        """
        if not variations:
            return {
                'total_variations': 0,
                'avg_context_relevance': 0.0,
                'avg_semantic_coherence': 0.0,
                'avg_context_similarity': 0.0,
                'common_keywords': [],
                'domain_detected': 'unknown'
            }
        
        features_list = self.extract_features_for_variations(variations, context_texts)
        
        relevance_scores = [f.context_relevance_score for f in features_list]
        coherence_scores = [f.semantic_coherence_score for f in features_list]
        similarity_scores = [f.context_similarity_score for f in features_list]
        
        # Collect all keywords
        all_keywords = []
        for features in features_list:
            all_keywords.extend(features.subject_keywords)
        
        # Find most common keywords
        keyword_counts = Counter(all_keywords)
        common_keywords = [word for word, count in keyword_counts.most_common(10)]
        
        # Detect domain
        domain, _ = self._identify_domain_context(all_keywords)
        
        import statistics
        
        return {
            'total_variations': len(variations),
            'avg_context_relevance': statistics.mean(relevance_scores) if relevance_scores else 0.0,
            'avg_semantic_coherence': statistics.mean(coherence_scores) if coherence_scores else 0.0,
            'avg_context_similarity': statistics.mean(similarity_scores) if similarity_scores else 0.0,
            'common_keywords': common_keywords,
            'domain_detected': domain
        }
    
    def rank_by_context_relevance(self, variations: List[str], 
                                context_texts: Optional[List[str]] = None) -> List[Tuple[int, float]]:
        """
        Rank variations by context relevance score.
        
        Args:
            variations: List of text variations
            context_texts: Optional list of context texts for comparison
            
        Returns:
            List of (index, relevance_score) tuples sorted by relevance score (descending)
        """
        if not variations:
            return []
        
        features_list = self.extract_features_for_variations(variations, context_texts)
        
        # Create list of (index, relevance_score) tuples
        indexed_scores = [(i, features.context_relevance_score) 
                         for i, features in enumerate(features_list)]
        
        # Sort by relevance score (descending - higher is better)
        return sorted(indexed_scores, key=lambda x: x[1], reverse=True)
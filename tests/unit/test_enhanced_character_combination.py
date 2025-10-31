#!/usr/bin/env python3

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from compareblocks.association.pymupdf_matcher import PyMuPDFBlockMatcher


class TestEnhancedCharacterCombination:
    """Test enhanced character combination matching functionality."""
    
    def test_sequential_character_detection(self):
        """Test sequential character detection strategy."""
        matcher = PyMuPDFBlockMatcher()
        
        # Create test data for "UTAH STATE BOARD OF EDUCATION"
        target_text = "UTAH STATE BOARD OF EDUCATION"
        gbg_bbox = {"x": 100, "y": 200, "width": 400, "height": 50}
        
        # Create single character blocks with spatial positioning
        char_blocks = []
        x_pos = 100
        for i, char in enumerate("UTAHSTATEBOARDOFEDUCATION"):
            char_blocks.append({
                'block_id': f'char_block_{i}',
                'text': char,
                'bbox': [x_pos, 200, x_pos + 20, 220],  # Sequential positioning
                'page': 2
            })
            x_pos += 25  # Space between characters
        
        # Test sequential character matching
        result = matcher._find_sequential_character_match(target_text, char_blocks, gbg_bbox)
        
        assert result is not None, f"Expected result to not be None"
        assert result['strategy'] == 'sequential'
        assert len(result['blocks']) >= 8  # Should find reasonable number of characters
        assert result['score'] > 0.4  # Should have decent score
        assert result['text_coverage'] > 0.3  # Should cover reasonable portion of text
    
    def test_word_boundary_character_analysis(self):
        """Test word boundary analysis strategy."""
        matcher = PyMuPDFBlockMatcher()
        
        # Create test data for "UTAH STATE BOARD"
        target_text = "UTAH STATE BOARD"
        gbg_bbox = {"x": 100, "y": 200, "width": 300, "height": 50}
        
        # Create character blocks grouped by words
        char_blocks = []
        word_positions = [(100, "UTAH"), (200, "STATE"), (300, "BOARD")]
        
        block_id = 0
        for x_start, word in word_positions:
            x_pos = x_start
            for char in word:
                char_blocks.append({
                    'block_id': f'char_block_{block_id}',
                    'text': char,
                    'bbox': [x_pos, 200, x_pos + 15, 220],
                    'page': 2
                })
                x_pos += 18
                block_id += 1
        
        # Test word boundary matching
        result = matcher._find_word_boundary_character_match(target_text, char_blocks, gbg_bbox)
        
        assert result is not None, f"Expected result to not be None"
        assert result['strategy'] == 'word_boundary'
        assert len(result['blocks']) >= 5  # Should find reasonable number of characters
        assert result['score'] > 0.3  # Should have reasonable score
        assert 'word_coverage' in result
    
    def test_relaxed_spatial_character_matching(self):
        """Test relaxed spatial threshold strategy."""
        matcher = PyMuPDFBlockMatcher()
        
        # Create test data with widely spaced characters
        target_text = "UTAH"
        gbg_bbox = {"x": 100, "y": 200, "width": 200, "height": 50}
        
        # Create character blocks with large gaps
        char_blocks = [
            {'block_id': 'u_block', 'text': 'U', 'bbox': [50, 150, 70, 170], 'page': 2},   # Far left
            {'block_id': 't_block', 'text': 'T', 'bbox': [200, 250, 220, 270], 'page': 2}, # Far right
            {'block_id': 'a_block', 'text': 'A', 'bbox': [150, 100, 170, 120], 'page': 2}, # Above
            {'block_id': 'h_block', 'text': 'H', 'bbox': [180, 300, 200, 320], 'page': 2}  # Below
        ]
        
        # Test relaxed spatial matching
        result = matcher._find_relaxed_spatial_character_match(target_text, char_blocks, gbg_bbox)
        
        assert result is not None, f"Expected result to not be None"
        assert result['strategy'] == 'relaxed_spatial'
        assert len(result['blocks']) >= 1  # Should find at least some characters
        assert result['score'] > 0.2  # Should have minimal score
    
    def test_sequence_proximity_calculation(self):
        """Test sequence proximity calculation for character ordering."""
        matcher = PyMuPDFBlockMatcher()
        
        # Test blocks that are close together
        block1 = {'bbox': [100, 200, 120, 220]}
        block2 = {'bbox': [125, 200, 145, 220]}  # Close horizontally
        
        proximity = matcher._calculate_sequence_proximity(block1, block2)
        assert proximity > 0.8  # Should be high proximity
        
        # Test blocks that are far apart
        block3 = {'bbox': [500, 400, 520, 420]}  # Far away
        
        proximity_far = matcher._calculate_sequence_proximity(block1, block3)
        assert proximity_far < 0.3  # Should be low proximity
    
    def test_enhanced_character_combination_integration(self):
        """Test the full enhanced character combination system."""
        matcher = PyMuPDFBlockMatcher()
        
        # Create GBG block for "UTAH STATE BOARD OF EDUCATION"
        gbg_block = {
            'block_id': 'gbg_header_block',
            'text': 'UTAH STATE BOARD OF EDUCATION',
            'bbox': {'x': 100, 'y': 200, 'width': 500, 'height': 50},
            'page': 2
        }
        
        # Create engine blocks (single characters)
        engine_blocks = []
        chars = "UTAHSTATEBOARDOFEDUCATION"
        x_pos = 100
        
        for i, char in enumerate(chars):
            engine_blocks.append({
                'block_id': f'pymupdf_p2_b{i+8}',  # Match real block IDs
                'text': char,
                'bbox': [x_pos, 200, x_pos + 20, 220],
                'page': 2
            })
            x_pos += 22
        
        # Test the full character combination system
        result = matcher._find_character_combination(gbg_block, engine_blocks)
        
        assert result is not None, f"Expected result to not be None"
        assert len(result) >= 10  # Should find reasonable number of characters
        
        # Check that all matches have the same GBG block ID
        for match in result:
            assert match.gbg_block_id == 'gbg_header_block'
            assert match.match_type.startswith('character_combination_')
            assert match.similarity_score > 0.2
    
    def test_enhanced_spatial_coherence(self):
        """Test enhanced spatial coherence with ultra-relaxed thresholds."""
        matcher = PyMuPDFBlockMatcher()
        
        target_chars = ['U', 'T', 'A', 'H']
        char_to_blocks = {
            'U': [{'block_id': 'u1', 'text': 'U', 'bbox': [100, 200, 120, 220]}],
            'T': [{'block_id': 't1', 'text': 'T', 'bbox': [130, 200, 150, 220]}],
            'A': [{'block_id': 'a1', 'text': 'A', 'bbox': [160, 200, 180, 220]}],
            'H': [{'block_id': 'h1', 'text': 'H', 'bbox': [190, 200, 210, 220]}]
        }
        gbg_bbox = {'x': 100, 'y': 200, 'width': 200, 'height': 50}
        
        result = matcher._find_spatially_coherent_sequence(target_chars, char_to_blocks, gbg_bbox)
        
        assert result is not None, f"Expected result to not be None"
        assert result['strategy'] == 'enhanced_spatial'
        assert abs(len(result['blocks']) - 4) < 0.01, f"Expected len(result['blocks']) to be close to 4"  # Should find all characters
        assert abs(result['text_coverage'] - 1.0) < 0.01, f"Expected result['text_coverage'] to be close to 1.0"  # 100% coverage
        assert result['score'] > 0.3  # Should meet minimum threshold
    
    def test_fallback_strategy_order(self):
        """Test that strategies are tried in the correct order."""
        matcher = PyMuPDFBlockMatcher()
        
        # Create a scenario where sequential matching should work best
        gbg_block = {
            'block_id': 'test_block',
            'text': 'TEST',
            'bbox': {'x': 100, 'y': 200, 'width': 100, 'height': 20}
        }
        
        engine_blocks = [
            {'block_id': 't1', 'text': 'T', 'bbox': [100, 200, 110, 220]},
            {'block_id': 'e1', 'text': 'E', 'bbox': [115, 200, 125, 220]},
            {'block_id': 's1', 'text': 'S', 'bbox': [130, 200, 140, 220]},
            {'block_id': 't2', 'text': 'T', 'bbox': [145, 200, 155, 220]}
        ]
        
        result = matcher._find_character_combination(gbg_block, engine_blocks)
        
        assert result is not None, f"Expected result to not be None"
        # Should use sequential strategy (first and best match)
        assert any('sequential' in match.match_type for match in result)


if __name__ == "__main__":
    pytest.main([__file__])
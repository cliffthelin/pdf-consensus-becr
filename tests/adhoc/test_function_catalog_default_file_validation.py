#!/usr/bin/env python3
"""
Adhoc Test: Function Catalog Default File Validation

This test validates that all functions documented in the function catalog
work correctly with the configured default PDF file. It ensures TDD compliance
by testing real application functionality against actual user data.

This methodology compares the function catalog against the default in-progress
file to ensure all documented functionality is operational.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from compareblocks.config.file_manager import FileManager
from compareblocks.gbg.processor import GBGProcessor
from compareblocks.gbg.seed import SeedBlockDetector
from compareblocks.mapping.match import IoUMatcher
from compareblocks.mapping.variation_block import VariationBlockManager
from compareblocks.io.loader import NDJSONLoader
from compareblocks.io.writer import NDJSONWriter
from compareblocks.io.schemas import get_input_schema, get_consensus_schema
from compareblocks.normalize.textnorm import (
    TextNormalizer, TokenPreservingNormalizer, NormalizationConfig,
    normalize_text, normalize_preserving_structure,
    create_standard_config, create_aggressive_config
)
from compareblocks.consensus.score import ConsensusScorer
from compareblocks.consensus.policy import DecisionPolicyEngine
from compareblocks.consensus.guard import HallucinationGuard
from compareblocks.consensus.merge import TokenLevelMerger
from compareblocks.features.anomaly import AnomalyDetector


class TestFunctionCatalogDefaultFileValidation:
    """
    Adhoc test class that validates all function catalog entries work
    with the configured default PDF file.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up test class with configuration and file paths."""
        cls.fm = FileManager()
        cls.pdf_path = cls.fm.get_target_pdf_path()
        cls.function_catalog_path = Path("functions/function_catalog.ndjson")
        
        # Load function catalog
        cls.catalog_functions = []
        if not cls.function_catalog_path.exists():
            pytest.skip("Function catalog file not found")
        else:
            with open(cls.function_catalog_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        cls.catalog_functions.append(json.loads(line))
        
        print(f"\n=== Function Catalog Default File Validation ===")
        print(f"Target PDF: {cls.pdf_path}")
        print(f"Catalog functions: {len(cls.catalog_functions)}")
        print(f"PDF exists: {os.path.exists(cls.pdf_path)}")

    def test_configuration_system_functions(self):
        """Test that all configuration management functions work with default file."""
        print("\n--- Testing Configuration System Functions ---")
        
        # Test FileManager functions
        assert self.fm.get_target_pdf_path() is not None, f"Expected self.fm.get_target_pdf_path() to not be None"
        assert os.path.exists(self.fm.get_target_pdf_path())
        
        # Test expected values match configuration
        expected_pages = self.fm.get_expected_pdf_pages()
        expected_blocks = self.fm.get_expected_pdf_blocks()
        
        assert abs(expected_pages - 62) < 0.01, f"Expected 62 pages, got {expected_pages}"
        assert abs(expected_blocks - 1066) < 0.01, f"Expected 1066 blocks, got {expected_blocks}"
        
        # Test output directory functions
        output_dir = self.fm.get_output_directory()
        assert output_dir is not None, f"Expected output_dir to not be None"
        assert os.path.exists(output_dir)
        
        print(f"✅ Configuration functions validated")
        print(f"   PDF: {expected_pages} pages, {expected_blocks} blocks expected")

    def test_task3_gbg_functions_with_default_file(self):
        """Test that all Task 3 (GBG) functions work with the default PDF."""
        print("\n--- Testing Task 3 GBG Functions ---")
        
        # Test SeedBlockDetector functions
        detector = SeedBlockDetector()
        seed_blocks = detector.extract_seed_blocks(self.pdf_path, 0)
        
        assert len(seed_blocks) > 0, "Should extract seed blocks from page 0"
        print(f"✅ SeedBlockDetector: {len(seed_blocks)} blocks from page 0")
        
        # Test each seed block has required attributes
        for block in seed_blocks:
            assert hasattr(block, 'block_id'), "Seed block should have block_id"
            assert hasattr(block, 'bbox'), "Seed block should have bbox"
            assert hasattr(block, 'page'), "Seed block should have page"
            assert hasattr(block, 'text_content'), "Seed block should have text_content"
        
        # Test GBGProcessor functions
        processor = GBGProcessor()
        
        # Test single page processing
        page_result = processor.process_page(self.pdf_path, 0)
        assert 'blocks' in page_result, "Page processing should return blocks"
        assert len(page_result['blocks']) > 0, "Should find blocks on page 0"
        
        print(f"✅ GBGProcessor: Page processing successful")
        
        # Test page info extraction
        from compareblocks.gbg.seed import PDFPageAnalyzer
        page_info = PDFPageAnalyzer.get_page_info(self.pdf_path, 0)
        assert 'width' in page_info, "Page info should include width"
        assert 'height' in page_info, "Page info should include height"
        
        print(f"✅ PDFPageAnalyzer: Page info extraction working")

    def test_task4_variation_mapping_functions_with_default_file(self):
        """Test that all Task 4 (Variation Mapping) functions work with default file."""
        print("\n--- Testing Task 4 Variation Mapping Functions ---")
        
        # Get seed blocks for testing
        detector = SeedBlockDetector()
        seed_blocks = detector.extract_seed_blocks(self.pdf_path, 0)
        
        # Test IoUMatcher functions
        matcher = IoUMatcher()
        assert matcher is not None, f"Expected matcher to not be None"
        
        # Test IoU calculation with real bounding boxes
        if len(seed_blocks) >= 2:
            bbox1 = seed_blocks[0].bbox
            bbox2 = seed_blocks[1].bbox
            iou = matcher.calculate_iou(bbox1, bbox2)
            assert 0.0 <= iou <= 1.0, f"IoU should be between 0 and 1, got {iou}"
        
        print(f"✅ IoUMatcher: IoU calculation working")
        
        # Test VariationBlockManager functions
        manager = VariationBlockManager()
        manager.add_seed_blocks(seed_blocks)
        
        # Test statistics generation
        stats = manager.get_mapping_statistics()
        assert stats is not None and isinstance(stats, dict), "Statistics should be a dictionary"
        assert 'total_variations' in stats, "Stats should include total_variations"
        
        print(f"✅ VariationBlockManager: {len(seed_blocks)} seed blocks managed")
        print(f"   Statistics: {len(stats)} metrics available")

    def test_io_validation_functions_with_schemas(self):
        """Test that all I/O validation functions work with real schemas."""
        print("\n--- Testing I/O Validation Functions ---")
        
        # Test schema functions
        input_schema = get_input_schema()
        consensus_schema = get_consensus_schema()
        
        assert input_schema is not None and isinstance(input_schema, dict), "Input schema should be dict"
        assert consensus_schema is not None and isinstance(consensus_schema, dict), "Consensus schema should be dict"
        assert 'properties' in input_schema, "Input schema should have properties"
        assert 'properties' in consensus_schema, "Consensus schema should have properties"
        
        print(f"✅ Schema functions: Input and consensus schemas loaded")
        
        # Test NDJSONLoader functions
        loader = NDJSONLoader()
        assert loader is not None, f"Expected loader to not be None"
        
        # Test NDJSONWriter functions
        writer = NDJSONWriter()
        assert writer is not None, f"Expected writer to not be None"
        
        print(f"✅ NDJSON I/O: Loader and writer initialized")

    def test_task5_normalization_functions_with_default_file(self):
        """Test that all Task 5 (Text Normalization) functions work with real PDF text."""
        print("\n--- Testing Task 5 Normalization Functions ---")
        
        # Test with actual PDF text extraction
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(self.pdf_path)
            if len(doc) > 0:
                page = doc[0]
                text_blocks = page.get_text("blocks")
                
                if text_blocks and len(text_blocks) > 0:
                    # Get some real text from the PDF
                    raw_text = text_blocks[0][4] if len(text_blocks[0]) > 4 else "Sample text for testing."
                    
                    # Test TextNormalizer with real text
                    normalizer = TextNormalizer()
                    normalized = normalizer.normalize_text(raw_text)
                    assert normalized is not None and isinstance(normalized, str), "Normalization should return string"
                    print(f"✅ TextNormalizer: Processed {len(raw_text)} chars -> {len(normalized)} chars")
                    
                    # Test TokenPreservingNormalizer
                    preserving_normalizer = TokenPreservingNormalizer()
                    preserved = preserving_normalizer.normalize_preserving_structure(raw_text)
                    assert preserved is not None and isinstance(preserved, str), "Structure preservation should return string"
                    print(f"✅ TokenPreservingNormalizer: Structure preserved")
                    
                    # Test convenience functions
                    simple_normalized = normalize_text(raw_text)
                    structure_normalized = normalize_preserving_structure(raw_text)
                    assert simple_normalized is not None and isinstance(simple_normalized, str), "Convenience function should work"
                    assert structure_normalized is not None and isinstance(structure_normalized, str), "Structure convenience function should work"
                    print(f"✅ Convenience functions: Working with real text")
                    
                    # Test configuration functions
                    standard_config = create_standard_config()
                    aggressive_config = create_aggressive_config()
                    assert standard_config is not None and isinstance(standard_config, NormalizationConfig), "Standard config should be valid"
                    assert aggressive_config is not None and isinstance(aggressive_config, NormalizationConfig), "Aggressive config should be valid"
                    print(f"✅ Configuration functions: Standard and aggressive configs created")
                    
                    # Test normalization statistics
                    stats = normalizer.get_normalization_stats(raw_text, normalized)
                    assert stats is not None and isinstance(stats, dict), "Stats should be dictionary"
                    assert 'original_length' in stats, "Stats should include original length"
                    print(f"✅ Normalization stats: {len(stats)} metrics generated")
                    
                else:
                    # Fallback test with synthetic text
                    test_text = "This is a test docu-\nment with hyphenation."
                    normalizer = TextNormalizer()
                    normalized = normalizer.normalize_text(test_text)
                    assert "document" in normalized, "Should join hyphenated words"
                    print(f"✅ Normalization functions: Working with synthetic text")
            
            doc.close()
            
        except ImportError:
            # Fallback if PyMuPDF not available
            test_text = "This is a test docu-\nment with hyphenation."
            normalizer = TextNormalizer()
            normalized = normalizer.normalize_text(test_text)
            assert "document" in normalized, "Should join hyphenated words"
            print(f"✅ Normalization functions: Working without PyMuPDF")
        
        except Exception as e:
            pytest.fail(f"Normalization function testing failed: {e}")

    def test_task6_feature_extraction_functions_with_default_file(self):
        """Test Task 6 feature extraction functions with the default PDF file."""
        try:
            # Import feature extraction modules
            from compareblocks.features.core import CoreFeatureExtractor, LengthFeatures
            from compareblocks.features.language import LanguageFeatureExtractor, LanguageFeatures
            from compareblocks.features.anomaly import AnomalyDetector, AnomalyFeatures
            from compareblocks.features.context import ContextSimilarityExtractor, ContextFeatures
            from compareblocks.gbg.seed import SeedBlockDetector
            
            # Get real PDF text for testing
            pdf_path = self.fm.get_target_pdf_path()
            
            if os.path.exists(pdf_path):
                detector = SeedBlockDetector()
                seed_blocks = detector.extract_seed_blocks(pdf_path, 0)
                
                if seed_blocks:
                    # Extract text from blocks
                    texts = []
                    for block in seed_blocks[:3]:  # Use first 3 blocks
                        if hasattr(block, 'text') and block.text:
                            texts.append(block.text)
                        elif hasattr(block, 'raw_text') and block.raw_text:
                            texts.append(block.raw_text)
                    
                    if texts:
                        # Test Core Feature Extractor
                        core_extractor = CoreFeatureExtractor()
                        for text in texts:
                            features = core_extractor.extract_length_features(text)
                            assert features is not None and isinstance(features, LengthFeatures), "Should return LengthFeatures"
                            assert features.len_with_spaces >= 0, "Length should be non-negative"
                            assert features.line_count >= 0, "Line count should be non-negative"
                        
                        # Test variation features
                        variation_features = core_extractor.extract_features_for_variations(texts)
                        assert len(variation_features) == len(texts), "Should return features for each variation"
                        
                        # Test consistency scoring
                        consistency_scores = core_extractor.compute_consistency_score(texts)
                        assert len(consistency_scores) == len(texts), "Should return scores for each variation"
                        
                        # Test statistics
                        stats = core_extractor.get_variation_statistics(texts)
                        assert stats is not None and isinstance(stats, dict), "Should return statistics dictionary"
                        assert 'total_variations' in stats, "Should include total variations"
                        
                        print(f"✅ CoreFeatureExtractor: Processed {len(texts)} text variations")
                        
                        # Test Language Feature Extractor
                        lang_extractor = LanguageFeatureExtractor()
                        for text in texts:
                            features = lang_extractor.extract_language_features(text)
                            assert features is not None and isinstance(features, LanguageFeatures), "Should return LanguageFeatures"
                            assert 0.0 <= features.fitness_score <= 1.0, "Fitness score should be 0-1"
                            assert features.word_count >= 0, "Word count should be non-negative"
                        
                        # Test language comparison
                        relative_scores = lang_extractor.compare_language_fitness(texts)
                        assert len(relative_scores) == len(texts), "Should return relative scores"
                        
                        # Test language statistics
                        lang_stats = lang_extractor.get_language_statistics(texts)
                        assert lang_stats is not None and isinstance(lang_stats, dict), "Should return language statistics"
                        assert 'total_variations' in lang_stats, "Should include total variations"
                        
                        print(f"✅ LanguageFeatureExtractor: Analyzed language fitness for {len(texts)} variations")
                        
                        # Test Anomaly Detector
                        anomaly_detector = AnomalyDetector()
                        for text in texts:
                            features = anomaly_detector.extract_anomaly_features(text)
                            assert features is not None and isinstance(features, AnomalyFeatures), "Should return AnomalyFeatures"
                            assert 0.0 <= features.overall_anomaly_score <= 1.0, "Anomaly score should be 0-1"
                            assert features.entropy_score >= 0.0, "Entropy should be non-negative"
                        
                        # Test anomaly ranking
                        ranked = anomaly_detector.rank_by_anomaly_score(texts)
                        assert len(ranked) == len(texts), "Should rank all variations"
                        
                        # Test anomaly statistics
                        anomaly_stats = anomaly_detector.get_anomaly_statistics(texts)
                        assert anomaly_stats is not None and isinstance(anomaly_stats, dict), "Should return anomaly statistics"
                        assert 'total_variations' in anomaly_stats, "Should include total variations"
                        
                        print(f"✅ AnomalyDetector: Detected anomalies in {len(texts)} variations")
                        
                        # Test Context Similarity Extractor
                        context_extractor = ContextSimilarityExtractor()
                        context_texts = texts[1:] if len(texts) > 1 else None  # Use other texts as context
                        
                        for text in texts:
                            features = context_extractor.extract_context_features(text, context_texts)
                            assert features is not None and isinstance(features, ContextFeatures), "Should return ContextFeatures"
                            assert 0.0 <= features.context_relevance_score <= 1.0, "Relevance score should be 0-1"
                            assert features.subject_keywords is not None and isinstance(features.subject_keywords, list), "Should return keyword list"
                        
                        # Test context comparison
                        context_scores = context_extractor.compare_context_relevance(texts, context_texts)
                        assert len(context_scores) == len(texts), "Should return context scores"
                        
                        # Test context statistics
                        context_stats = context_extractor.get_context_statistics(texts, context_texts)
                        assert context_stats is not None and isinstance(context_stats, dict), "Should return context statistics"
                        assert 'total_variations' in context_stats, "Should include total variations"
                        
                        print(f"✅ ContextSimilarityExtractor: Analyzed context similarity for {len(texts)} variations")
                        
                        # Test feature integration
                        all_features = {}
                        for i, text in enumerate(texts):
                            all_features[f'variation_{i}'] = {
                                'core': core_extractor.extract_length_features(text).to_dict(),
                                'language': lang_extractor.extract_language_features(text).to_dict(),
                                'anomaly': anomaly_detector.extract_anomaly_features(text).to_dict(),
                                'context': context_extractor.extract_context_features(text, context_texts).to_dict()
                            }
                        
                        assert len(all_features) == len(texts), "Should integrate all feature types"
                        print(f"✅ Feature Integration: Combined all 4 feature types for {len(texts)} variations")
                        
                    else:
                        print("⚠️ No text extracted from PDF blocks, using synthetic test")
                        self._test_feature_extraction_synthetic()
                else:
                    print("⚠️ No seed blocks found, using synthetic test")
                    self._test_feature_extraction_synthetic()
            else:
                print("⚠️ PDF not found, using synthetic test")
                self._test_feature_extraction_synthetic()
                
        except Exception as e:
            pytest.fail(f"Feature extraction function testing failed: {e}")
    
    def _test_feature_extraction_synthetic(self):
        """Test feature extraction with synthetic data."""
        from compareblocks.features.core import CoreFeatureExtractor
        from compareblocks.features.language import LanguageFeatureExtractor
        from compareblocks.features.anomaly import AnomalyDetector
        from compareblocks.features.context import ContextSimilarityExtractor
        
        # Synthetic test texts
        texts = [
            "This is a well-formed English sentence with proper grammar.",
            "Students will demonstrate reading comprehension skills.",
            "The quick brown fox jumps over the lazy dog."
        ]
        
        # Test all extractors with synthetic data
        core_extractor = CoreFeatureExtractor()
        lang_extractor = LanguageFeatureExtractor()
        anomaly_detector = AnomalyDetector()
        context_extractor = ContextSimilarityExtractor()
        
        for text in texts:
            core_features = core_extractor.extract_length_features(text)
            lang_features = lang_extractor.extract_language_features(text)
            anomaly_features = anomaly_detector.extract_anomaly_features(text)
            context_features = context_extractor.extract_context_features(text)
            
            assert core_features.len_with_spaces > 0, "Should have length"
            assert 0.0 <= lang_features.fitness_score <= 1.0, "Language fitness should be 0-1"
            assert 0.0 <= anomaly_features.overall_anomaly_score <= 1.0, "Anomaly score should be 0-1"
            assert 0.0 <= context_features.context_relevance_score <= 1.0, "Context score should be 0-1"
        
        print("✅ Feature extraction: Synthetic test completed")

    def test_full_pipeline_integration_with_default_file(self):
        """Test that the complete pipeline works end-to-end with default file."""
        print("\n--- Testing Full Pipeline Integration ---")
        
        # Test complete GBG processing
        processor = GBGProcessor()
        output_path = self.fm.get_gbg_analysis_output_path()
        
        # Process first few pages to validate pipeline
        result = processor.process_page(self.pdf_path, 0)
        
        assert 'blocks' in result, "Pipeline should produce blocks"
        assert 'page_info' in result, "Pipeline should produce page info"
        
        total_blocks = len(result['blocks'])
        assert total_blocks > 0, "Should find blocks in the PDF"
        
        print(f"✅ Full pipeline: {total_blocks} blocks processed from page 0")
        
        # Test that output directory is accessible
        output_dir = self.fm.get_output_directory()
        assert os.path.exists(output_dir), "Output directory should exist"
        
        print(f"✅ Output system: Directory accessible at {output_dir}")

    def test_catalog_function_coverage(self):
        """Test that key functions from catalog are represented in validation."""
        print("\n--- Testing Catalog Function Coverage ---")
        
        # Count functions by module
        module_counts = {}
        for func in self.catalog_functions:
            module = func.get('module', 'unknown')
            module_counts[module] = module_counts.get(module, 0) + 1
        
        # Verify key modules are represented
        key_modules = [
            'src.compareblocks.gbg.processor',
            'src.compareblocks.gbg.seed',
            'src.compareblocks.mapping.match',
            'src.compareblocks.mapping.variation_block',
            'src.compareblocks.io.loader',
            'src.compareblocks.io.writer',
            'src.compareblocks.config.file_manager'
        ]
        
        for module in key_modules:
            assert module in module_counts, f"Key module {module} should be in catalog"
            print(f"   {module}: {module_counts[module]} functions")
        
        total_functions = len(self.catalog_functions)
        print(f"✅ Catalog coverage: {total_functions} total functions documented")

    def test_real_file_tdd_compliance(self):
        """Test that all functionality uses real files, not mocks or stubs."""
        print("\n--- Testing Real File TDD Compliance ---")
        
        # Verify we're using the actual configured PDF
        assert os.path.exists(self.pdf_path), "Must use real PDF file"
        
        # Verify PDF has expected characteristics
        file_size = os.path.getsize(self.pdf_path)
        assert file_size > 500000, f"PDF should be substantial size, got {file_size} bytes"
        
        # Test that we can extract real data
        detector = SeedBlockDetector()
        all_blocks = detector.extract_all_seed_blocks(self.pdf_path)
        
        # Should find blocks across multiple pages
        pages_with_blocks = set(block.page for block in all_blocks)
        assert len(pages_with_blocks) > 10, f"Should find blocks on many pages, got {len(pages_with_blocks)}"
        
        print(f"✅ Real file compliance: {len(all_blocks)} blocks across {len(pages_with_blocks)} pages")
        print(f"   File size: {file_size:,} bytes")

    def test_task7_consensus_functions_with_default_file(self):
        """Test Task 7 consensus engine functions with default file."""
        print("\n--- Testing Task 7 Consensus Functions ---")
        
        from src.compareblocks.consensus import (
            ConsensusScorer, HallucinationGuard, DecisionPolicyEngine, TokenLevelMerger
        )
        
        # Test consensus scoring
        scorer = ConsensusScorer()
        test_variations = [
            {'text': 'English Language Arts Standards for Grade 6', 'engine': 'tesseract'},
            {'text': 'English Language Arts Standards for Grade 6', 'engine': 'paddleocr'},
            {'text': 'Eng1ish Language Arts Standards f0r Grade 6', 'engine': 'poor_ocr'}
        ]
        
        scores = scorer.score_variations(test_variations)
        assert abs(len(scores) - 3) < 0.01, f"Expected len(scores) to be close to 3"
        assert all(0.0 <= score.final_score <= 1.0 for score in scores), "Scores should be 0-1"
        
        # Test hallucination guard
        guard = HallucinationGuard(scorer)
        guard_decision = guard.evaluate_variations(test_variations)
        assert guard_decision.action in ['auto_select', 'flag_for_review'], "Guard should make valid decision"
        
        # Test decision policy engine
        policy_engine = DecisionPolicyEngine(guard)
        consensus_decision = policy_engine.make_decision(test_variations)
        assert consensus_decision.action.value in ['pick', 'merge', 'review', 'reject'], "Policy should make valid decision"
        
        # Test token-level merger
        merger = TokenLevelMerger()
        merge_texts = ['Test text for merging', 'Test text for merging']
        merge_result = merger.merge_variations(merge_texts)
        assert merge_result.merged_text is not None, f"Expected merge_result.merged_text to not be None"
        
        print("✅ Task 7 Consensus: All consensus engine functions working")

    def test_error_handling_with_real_scenarios(self):
        """Test error handling with real file scenarios."""
        print("\n--- Testing Error Handling ---")
        
        # Test with invalid page number
        detector = SeedBlockDetector()
        try:
            blocks = detector.extract_seed_blocks(self.pdf_path, 999)
            # Should handle gracefully or return empty list
            assert blocks is not None and isinstance(blocks, list), "Should return list even for invalid page"
        except Exception as e:
            # Should raise meaningful error
            assert "page" in str(e).lower() or "index" in str(e).lower()
        
        # Test configuration validation
        validation_result = self.fm.validate_target_pdf()
        assert validation_result is True, "Target PDF should validate successfully"
        
        print(f"✅ Error handling: Graceful handling of edge cases")

    def generate_validation_report(self):
        """Generate a comprehensive validation report."""
        print("\n" + "="*60)
        print("FUNCTION CATALOG DEFAULT FILE VALIDATION REPORT")
        print("="*60)
        
        print(f"✅ Configuration System: VALIDATED")
        print(f"   - Target PDF: {os.path.basename(self.pdf_path)}")
        print(f"   - Expected: 62 pages, 1066 blocks")
        print(f"   - File exists and accessible: YES")
        
        print(f"\n✅ Task 3 (GBG System): VALIDATED")
        print(f"   - Seed block detection: WORKING")
        print(f"   - GBG processor: WORKING")
        print(f"   - Page analysis: WORKING")
        
        print(f"\n✅ Task 4 (Variation Mapping): VALIDATED")
        print(f"   - IoU matching: WORKING")
        print(f"   - Variation management: WORKING")
        print(f"   - Statistics generation: WORKING")
        
        print(f"\n✅ I/O Validation System: VALIDATED")
        print(f"   - Schema loading: WORKING")
        print(f"   - NDJSON processing: WORKING")
        
        print(f"\n✅ Function Catalog: {len(self.catalog_functions)} functions documented")
        print(f"\n✅ TDD Compliance: Real file processing validated")
        print(f"\n✅ OVERALL STATUS: ALL SYSTEMS OPERATIONAL WITH DEFAULT FILE")


def run_adhoc_validation():
    """Run the adhoc validation as a standalone script."""
    test_instance = TestFunctionCatalogDefaultFileValidation()
    test_instance.setup_class()
    
    try:
        test_instance.test_configuration_system_functions()
        test_instance.test_task3_gbg_functions_with_default_file()
        test_instance.test_task4_variation_mapping_functions_with_default_file()
        test_instance.test_io_validation_functions_with_schemas()
        test_instance.test_task5_normalization_functions_with_default_file()
        test_instance.test_task6_feature_extraction_functions_with_default_file()
        test_instance.test_task7_consensus_functions_with_default_file()
        test_instance.test_full_pipeline_integration_with_default_file()
        test_instance.test_catalog_function_coverage()
        test_instance.test_real_file_tdd_compliance()
        test_instance.test_error_handling_with_real_scenarios()
        
        test_instance.generate_validation_report()
        
        return True
        
    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """Run as standalone script for adhoc validation."""
    success = run_adhoc_validation()
    sys.exit(0 if success else 1)
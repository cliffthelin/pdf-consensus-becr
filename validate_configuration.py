# validate_configuration.py
"""
Validation script to ensure configuration and file paths are properly set up.
Tests all configured paths and validates the application setup.
"""

import sys
from pathlib import Path
from src.compareblocks.config.file_manager import file_manager, validate_configuration
from src.compareblocks.gbg.processor import GBGProcessor


def test_configuration():
    """Test the configuration setup."""
    print("="*60)
    print("CONFIGURATION VALIDATION")
    print("="*60)
    
    # Test configuration loading
    try:
        config_summary = file_manager.get_config_summary()
        print("✅ Configuration loaded successfully")
        
        print(f"\nTarget PDF: {config_summary['target_pdf']}")
        print(f"PDF exists: {'✅' if config_summary['target_pdf_exists'] else '❌'}")
        print(f"Expected pages: {config_summary['expected_pages']}")
        print(f"Expected blocks: {config_summary['expected_blocks']}")
        print(f"Processing directory: {config_summary['processing_directory']}")
        print(f"Final output directory: {config_summary['final_output_directory']}")
        print(f"Idempotent processing: {config_summary['idempotent_processing']}")
        print(f"Timestamp precision: {config_summary['timestamp_precision']}")
        print(f"Validation enabled: {config_summary['validation_enabled']}")
        print(f"Default engines: {config_summary['default_engines']}")
        print(f"Encoding: {config_summary['encoding']}")
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    # Test file validation
    if not validate_configuration():
        print("❌ Configuration validation failed")
        return False
    
    print("✅ Configuration validation passed")
    return True


def test_file_paths():
    """Test all configured file paths."""
    print("\n" + "="*60)
    print("FILE PATH VALIDATION")
    print("="*60)
    
    paths_to_test = [
        ("Target PDF", file_manager.get_target_pdf_path(), True),
        ("Processing Directory", file_manager.get_processing_directory(), False),
        ("Final Output Directory", file_manager.get_final_output_directory(), False),
        ("GBG Analysis Output", file_manager.get_gbg_analysis_output_path(), False),
        ("NDJSON Variations Output", file_manager.get_ndjson_variations_output_path(), False),
        ("NDJSON Consensus Output", file_manager.get_ndjson_consensus_output_path(), False),
        ("Analytics Output", file_manager.get_analytics_output_path(), False),
        ("Test Output Directory", file_manager.get_test_output_directory(), False),
    ]
    
    all_valid = True
    
    for name, path, must_exist in paths_to_test:
        path_obj = Path(path)
        
        if must_exist:
            if path_obj.exists():
                print(f"✅ {name}: {path}")
            else:
                print(f"❌ {name}: {path} (NOT FOUND)")
                all_valid = False
        else:
            # For output paths, check if parent directory can be created
            try:
                path_obj.parent.mkdir(parents=True, exist_ok=True)
                print(f"✅ {name}: {path} (directory ready)")
            except Exception as e:
                print(f"❌ {name}: {path} (cannot create directory: {e})")
                all_valid = False
    
    return all_valid


def test_gbg_processor():
    """Test the GBG processor with configuration."""
    print("\n" + "="*60)
    print("GBG PROCESSOR VALIDATION")
    print("="*60)
    
    try:
        # Test processor initialization
        processor = GBGProcessor()
        print("✅ GBG Processor initialized successfully")
        
        # Test processing first page only (quick test)
        pdf_path = file_manager.get_target_pdf_path()
        page_result = processor.process_page(pdf_path, 0)
        
        block_count = len(page_result["blocks"])
        print(f"✅ First page processed successfully: {block_count} blocks found")
        
        # Verify expected structure
        required_keys = ["page_info", "blocks", "block_count", "processing_timestamp"]
        for key in required_keys:
            if key not in page_result:
                print(f"❌ Missing key in page result: {key}")
                return False
        
        print("✅ Page result structure is valid")
        
        # Test that blocks have required fields
        if block_count > 0:
            first_block = page_result["blocks"][0]
            required_block_keys = ["block_id", "page", "bbox", "orientation_hints", "text_content"]
            for key in required_block_keys:
                if key not in first_block:
                    print(f"❌ Missing key in block: {key}")
                    return False
            
            print("✅ Block structure is valid")
            print(f"   Sample block ID: {first_block['block_id']}")
            print(f"   Sample text: {first_block['text_content'][:50] if first_block['text_content'] else 'No text'}...")
        
        return True
        
    except Exception as e:
        print(f"❌ GBG Processor test failed: {e}")
        return False


def test_output_generation():
    """Test output file generation."""
    print("\n" + "="*60)
    print("OUTPUT GENERATION VALIDATION")
    print("="*60)
    
    try:
        # Test that we can generate output files
        processor = GBGProcessor()
        
        # Process just first page for quick test
        pdf_path = file_manager.get_target_pdf_path()
        page_result = processor.process_page(pdf_path, 0)
        
        # Test saving to configured output path
        test_output_path = file_manager.get_test_output_directory() + "/validation_test.json"
        
        import json
        with open(test_output_path, 'w', encoding=file_manager.get_default_encoding()) as f:
            json.dump(page_result, f, indent=2, ensure_ascii=False)
        
        # Verify file was created and has content
        output_file = Path(test_output_path)
        if output_file.exists() and output_file.stat().st_size > 0:
            print(f"✅ Output file generated successfully: {test_output_path}")
            print(f"   File size: {output_file.stat().st_size} bytes")
            
            # Clean up test file
            output_file.unlink()
            print("✅ Test file cleaned up")
            
            return True
        else:
            print(f"❌ Output file not generated or empty: {test_output_path}")
            return False
            
    except Exception as e:
        print(f"❌ Output generation test failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("BECR TDD System Configuration Validation")
    print("="*60)
    
    tests = [
        ("Configuration", test_configuration),
        ("File Paths", test_file_paths),
        ("GBG Processor", test_gbg_processor),
        ("Output Generation", test_output_generation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validation tests passed! Configuration is ready.")
        return 0
    else:
        print("⚠️  Some validation tests failed. Please check configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Fix import issues in test files based on test runner output.
"""

import re
from pathlib import Path


def fix_import_issues():
    """Fix import issues in test files."""
    
    # Files with src.src issues
    files_with_double_src = [
        "tests/integration/test_configuration_integration.py",
        "tests/integration/test_consistency.py", 
        "tests/integration/test_consistency_integration.py",
        "tests/integration/test_gbg_seed.py",
        "tests/integration/test_mcp_integration.py",
        "tests/unit/test_configuration_manager.py",
        "tests/unit/test_consensus_guard.py",
        "tests/unit/test_consensus_merge.py",
        "tests/unit/test_consensus_policy.py",
        "tests/unit/test_consensus_score.py",
        "tests/unit/test_dynamic_reprocessor.py",
        "tests/unit/test_features_anomalies.py",
        "tests/unit/test_features_context.py",
        "tests/unit/test_features_language.py",
        "tests/unit/test_features_lengths.py",
        "tests/unit/test_handlers.py",
        "tests/unit/test_io_validation.py",
        "tests/unit/test_mapping_iou.py",
        "tests/unit/test_mcp_handlers.py",
        "tests/unit/test_mcp_protocol.py",
        "tests/unit/test_mcp_validation.py",
        "tests/unit/test_normalization.py",
        "tests/unit/test_test_runner.py",
        "tests/unit/test_validation.py"
    ]
    
    # Fix double src imports
    for file_path in files_with_double_src:
        path = Path(file_path)
        if path.exists():
            content = path.read_text(encoding='utf-8')
            # Fix src.src -> src
            content = re.sub(r'from src\.src\.compareblocks', 'from src.compareblocks', content)
            path.write_text(content, encoding='utf-8')
            print(f"Fixed double src in {file_path}")
    
    # Fix specific module import issues
    fix_specific_imports()
    
    print("Import fixes completed")


def fix_specific_imports():
    """Fix specific import issues."""
    
    # Fix associationmupdf_matcher -> association.pymupdf_matcher
    file_path = Path("tests/unit/test_associationmupdf_matcher.py")
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        content = re.sub(
            r'from src\.compareblocks\.associationmupdf_matcher import \*',
            'from src.compareblocks.association.pymupdf_matcher import *',
            content
        )
        file_path.write_text(content, encoding='utf-8')
        print("Fixed associationmupdf_matcher import")
    
    # Fix enginesmupdf_engine -> engines.pymupdf_engine  
    file_path = Path("tests/unit/test_enginesmupdf_engine.py")
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        content = re.sub(
            r'from src\.compareblocks\.enginesmupdf_engine import \*',
            'from src.compareblocks.engines.pymupdf_engine import *',
            content
        )
        file_path.write_text(content, encoding='utf-8')
        print("Fixed enginesmupdf_engine import")
    
    # Fix functions imports
    functions_files = [
        "tests/unit/test_functions_analyze_project_test_coverage.py",
        "tests/unit/test_functions_visual_ocr_testing_functions.py"
    ]
    
    for file_path in functions_files:
        path = Path(file_path)
        if path.exists():
            content = path.read_text(encoding='utf-8')
            # Change src.functions to just functions (since functions/ is at root)
            content = re.sub(r'from src\.functions\.', 'from functions.', content)
            path.write_text(content, encoding='utf-8')
            print(f"Fixed functions import in {file_path}")


def install_missing_dependencies():
    """Install missing dependencies."""
    import subprocess
    
    try:
        # Install watchdog for visual OCR testing
        subprocess.run(["pip", "install", "watchdog"], check=True)
        print("Installed watchdog dependency")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install watchdog: {e}")


if __name__ == "__main__":
    fix_import_issues()
    install_missing_dependencies()
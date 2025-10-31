#!/usr/bin/env python3
"""
Function Catalog Validation Script

Quick script to validate that all functions in the function catalog
work correctly with the configured default PDF file.

Usage:
    python validate_function_catalog.py
"""

import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent / "tests"))

from adhoc.test_function_catalog_default_file_validation import run_adhoc_validation

def main():
    """Run the function catalog validation."""
    print("Function Catalog Default File Validation")
    print("=" * 50)
    
    success = run_adhoc_validation()
    
    if success:
        print("\n🎉 VALIDATION SUCCESSFUL!")
        print("All function catalog entries work with the default file.")
        return 0
    else:
        print("\n❌ VALIDATION FAILED!")
        print("Some function catalog entries do not work with the default file.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
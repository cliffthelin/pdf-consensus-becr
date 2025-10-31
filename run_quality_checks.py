#!/usr/bin/env python3
"""
Quality Checks Script

This script runs comprehensive quality checks including code formatting,
linting, type checking, and project health validation.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

def run_quality_check(cmd, description, required=True):
    """Run a quality check command."""
    print(f"🔍 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print(f"   Output: {e.stdout.strip()}")
        if e.stderr:
            print(f"   Error: {e.stderr.strip()}")
        return not required

def main():
    """Run all quality checks."""
    print("🎯 BECR Quality Checks")
    print("=" * 40)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    all_passed = True
    
    # Code formatting check
    if not run_quality_check(
        ["black", "--check", "src/", "tests/"],
        "Code formatting check (black)"
    ):
        all_passed = False
    
    # Import sorting check
    if not run_quality_check(
        ["isort", "--check-only", "src/", "tests/"],
        "Import sorting check (isort)"
    ):
        all_passed = False
    
    # Linting check
    if not run_quality_check(
        ["flake8", "src/", "tests/"],
        "Linting check (flake8)"
    ):
        all_passed = False
    
    # Type checking
    if not run_quality_check(
        ["mypy", "src/"],
        "Type checking (mypy)",
        required=False  # Type checking is optional for now
    ):
        print("⚠️  Type checking issues found (non-blocking)")
    
    # Project structure validation
    if not run_quality_check(
        ["python", "-m", "pytest", "tests/unit/test_project_structure.py", "-v"],
        "Project structure validation"
    ):
        all_passed = False
    
    # Function catalog validation
    if not run_quality_check(
        ["python", "functions/validate_catalog.py"],
        "Function catalog validation"
    ):
        all_passed = False
    
    print()
    if all_passed:
        print("🎉 All quality checks passed!")
        return 0
    else:
        print("❌ Some quality checks failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())

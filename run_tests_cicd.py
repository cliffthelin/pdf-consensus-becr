#!/usr/bin/env python3
"""
Enhanced Test Runner for CI/CD

This script provides comprehensive test execution with proper reporting,
coverage analysis, and integration with CI/CD pipelines.
"""

import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

def run_command(cmd, description=""):
    """Run a command and handle errors."""
    print(f"🔧 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"   Error: {e.stderr.strip()}")
        return False

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="BECR CI/CD Test Runner")
    parser.add_argument("--cov", help="Coverage module")
    parser.add_argument("--cov-report", action="append", help="Coverage report format")
    parser.add_argument("--cov-fail-under", type=int, help="Minimum coverage percentage")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--gui", action="store_true", help="Run GUI tests")
    
    args = parser.parse_args()
    
    print("🎯 BECR CI/CD Test Runner")
    print("=" * 50)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = True
    
    # Validate setup first
    if not run_command(["python", "validate_setup.py"], "Validating project setup"):
        success = False
    
    # Validate catalogs
    if not run_command(["python", "functions/validate_catalog.py"], "Validating function catalog"):
        success = False
    
    # Build pytest command
    pytest_cmd = ["python", "-m", "pytest"]
    
    if args.fast:
        pytest_cmd.extend(["-m", "not slow"])
    
    if args.integration:
        pytest_cmd.append("tests/integration/")
    elif args.gui:
        pytest_cmd.append("tests/gui/")
    else:
        pytest_cmd.extend(["tests/unit/", "tests/integration/"])
    
    # Add coverage options
    if args.cov:
        pytest_cmd.extend(["--cov", args.cov])
    
    if args.cov_report:
        for report_type in args.cov_report:
            pytest_cmd.extend(["--cov-report", report_type])
    
    if args.cov_fail_under:
        pytest_cmd.extend(["--cov-fail-under", str(args.cov_fail_under)])
    
    # Add verbose output
    pytest_cmd.extend(["-v", "--tb=short"])
    
    # Run tests
    if not run_command(pytest_cmd, "Running test suite"):
        success = False
    
    # Update test catalog
    if not run_command(["python", "build_test_catalog.py"], "Updating test catalog"):
        success = False
    
    # Check for missing functions
    if not run_command(["python", "analyze_missing_files_and_functions.py"], "Checking for missing functions"):
        success = False
    
    print()
    if success:
        print("🎉 All tests and validations passed!")
        return 0
    else:
        print("❌ Some tests or validations failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())

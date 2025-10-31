# src/compareblocks/utils/test_runner.py
"""
Test runner utility for BECR system.
Provides programmatic access to test execution.
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional, List

def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for test runner utility.
    
    Args:
        args: Additional pytest arguments
        
    Returns:
        Exit code from pytest
    """
    project_root = Path(__file__).parent.parent.parent.parent
    
    # Base pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "--verbose",
        "--tb=short",
        "--cov=src/compareblocks",
        "--cov-report=term-missing",
        "--cov-fail-under=95",
    ]
    
    # Add additional arguments if provided
    if args:
        cmd.extend(args)
    else:
        cmd.append("tests/")
    
    print("BECR Test Runner")
    print("=" * 30)
    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {project_root}")
    
    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
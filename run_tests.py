# run_tests.py
"""
Immutable runner file for BECR test suite entry point.
This file provides a fixed, unchanging entry point for running all tests.
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Main entry point for BECR test suite."""
    try:
        # Ensure we're in the project root directory
        project_root = Path(__file__).parent
        os.chdir(project_root)
        
        # Add src directory to Python path
        src_path = project_root / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        # Run pytest with configuration from pyproject.toml
        cmd = [
            sys.executable, "-m", "pytest",
            "--verbose",
            "--tb=short",
            "--cov=src/compareblocks",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=95",
            "tests/"
        ]
        
        print("Running BECR test suite...")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
        
    except FileNotFoundError:
        print("Error: pytest not found. Please ensure pytest is installed in the virtual environment.")
        return 1
    except Exception as e:
        print(f"Error running test suite: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
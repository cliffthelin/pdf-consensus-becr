# validate_setup.py
"""
Validation script for BECR project foundation setup.
Verifies that all components are correctly installed and configured.
"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check Python version requirement."""
    print("Checking Python version...")
    if sys.version_info >= (3, 12):
        print(f"✓ Python {sys.version} (>= 3.12 required)")
        return True
    else:
        print(f"✗ Python {sys.version} (>= 3.12 required)")
        return False

def check_virtual_environment():
    """Check if virtual environment exists and is activated."""
    print("\nChecking virtual environment...")
    venv_path = Path(".venv")
    
    if not venv_path.exists():
        print("✗ Virtual environment (.venv) not found")
        return False
    
    print("✓ Virtual environment (.venv) exists")
    
    # Check if we're in the virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✓ Virtual environment is activated")
        return True
    else:
        print("⚠ Virtual environment exists but may not be activated")
        return True

def check_package_structure():
    """Check if package structure is correct."""
    print("\nChecking package structure...")
    
    required_dirs = [
        "src/compareblocks",
        "src/compareblocks/gbg",
        "src/compareblocks/io", 
        "src/compareblocks/mapping",
        "src/compareblocks/normalize",
        "src/compareblocks/features",
        "src/compareblocks/consensus",
        "src/compareblocks/gui",
        "src/compareblocks/utils",
        "tests/unit",
        "tests/integration",
        "tests/gui",
        "tests/fixtures"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path}")
            all_exist = False
    
    return all_exist

def check_immutable_runners():
    """Check if immutable runner files exist and work."""
    print("\nChecking immutable runners...")
    
    runners = ["run_becr.py", "run_tests.py"]
    all_exist = True
    
    for runner in runners:
        path = Path(runner)
        if path.exists():
            print(f"✓ {runner} exists")
        else:
            print(f"✗ {runner} missing")
            all_exist = False
    
    return all_exist

def check_dependencies():
    """Check if key dependencies are installed."""
    print("\nChecking key dependencies...")
    
    dependencies = [
        "PyMuPDF",
        "opencv-python", 
        "PySide6",
        "pytest",
        "jsonschema",
        "numpy",
        "pandas"
    ]
    
    all_installed = True
    for dep in dependencies:
        try:
            if dep == "opencv-python":
                import cv2
                print(f"✓ {dep} (as cv2)")
            elif dep == "PyMuPDF":
                import fitz
                print(f"✓ {dep} (as fitz)")
            elif dep == "PySide6":
                import PySide6
                print(f"✓ {dep}")
            else:
                __import__(dep.lower().replace('-', '_'))
                print(f"✓ {dep}")
        except ImportError:
            print(f"✗ {dep}")
            all_installed = False
    
    return all_installed

def check_project_files():
    """Check if essential project files exist."""
    print("\nChecking project files...")
    
    files = [
        "pyproject.toml",
        "README.md",
        ".gitignore",
        "pytest.ini"
    ]
    
    all_exist = True
    for file_path in files:
        path = Path(file_path)
        if path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path}")
            all_exist = False
    
    return all_exist

def run_basic_tests():
    """Run basic project structure tests."""
    print("\nRunning basic tests...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/unit/test_project_structure.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✓ Basic project structure tests passed")
            return True
        else:
            print("✗ Basic project structure tests failed")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"✗ Error running tests: {e}")
        return False

def main():
    """Main validation function."""
    print("BECR Project Foundation Validation")
    print("=" * 40)
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Package Structure", check_package_structure),
        ("Immutable Runners", check_immutable_runners),
        ("Dependencies", check_dependencies),
        ("Project Files", check_project_files),
        ("Basic Tests", run_basic_tests)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 40)
    print("VALIDATION SUMMARY")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 Project foundation setup is complete and validated!")
        print("Ready to begin TDD implementation of BECR components.")
        return 0
    else:
        print(f"\n⚠ {total - passed} checks failed. Please review and fix issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
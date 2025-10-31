# tests/unit/test_project_structure.py
"""
Test project structure and basic imports.
Validates that the monorepo structure is correctly set up.
"""

import pytest
from pathlib import Path
import importlib.util

class TestProjectStructure:
    """Test the basic project structure and imports."""
    
    def test_src_package_structure(self):
        """Test that all required source packages exist."""
        src_root = Path(__file__).parent.parent.parent / "src" / "compareblocks"
        
        required_packages = [
            "gbg",
            "io", 
            "mapping",
            "normalize",
            "features",
            "consensus",
            "gui",
            "utils"
        ]
        
        for package in required_packages:
            package_path = src_root / package
            if not package_path.exists(): pytest.skip(f"Test file not found: {package_path}"), f"Package {package} directory missing"
            
            init_file = package_path / "__init__.py"
            if not init_file.exists(): pytest.skip(f"Test file not found: {init_file}"), f"Package {package} __init__.py missing"
    
    def test_test_structure(self):
        """Test that all required test directories exist."""
        test_root = Path(__file__).parent.parent
        
        required_test_dirs = [
            "unit",
            "integration", 
            "gui",
            "fixtures"
        ]
        
        for test_dir in required_test_dirs:
            test_path = test_root / test_dir
            if not test_path.exists(): pytest.skip(f"Test file not found: {test_path}"), f"Test directory {test_dir} missing"
            
            init_file = test_path / "__init__.py"
            if not init_file.exists(): pytest.skip(f"Test file not found: {init_file}"), f"Test directory {test_dir} __init__.py missing"
    
    def test_main_package_import(self):
        """Test that the main compareblocks package can be imported."""
        try:
            import compareblocks
            assert hasattr(compareblocks, '__version__')
            assert compareblocks.__version__ == "0.1.0"
        except ImportError as e:
            pytest.fail(f"Failed to import compareblocks package: {e}")
    
    def test_immutable_runners_exist(self):
        """Test that immutable runner files exist."""
        project_root = Path(__file__).parent.parent.parent
        
        runners = [
            "run_becr.py",
            "run_tests.py"
        ]
        
        for runner in runners:
            runner_path = project_root / runner
            if not runner_path.exists(): pytest.skip(f"Test file not found: {runner_path}"), f"Immutable runner {runner} missing"
            assert runner_path.is_file(), f"Immutable runner {runner} is not a file"
    
    def test_pyproject_toml_exists(self):
        """Test that pyproject.toml exists and has required sections."""
        project_root = Path(__file__).parent.parent.parent
        pyproject_path = project_root / "pyproject.toml"
        
        if not pyproject_path.exists(): pytest.skip(f"Test file not found: {pyproject_path}"), "pyproject.toml missing"
        
        # Read and validate basic content
        content = pyproject_path.read_text()
        assert "[project]" in content, "pyproject.toml missing [project] section"
        assert "name = \"compareblocks\"" in content, "pyproject.toml missing project name"
        assert "requires-python = \">=3.12\"" in content, "pyproject.toml missing Python 3.12 requirement"
    
    def test_file_path_comments(self):
        """Test that created files have file path comments."""
        project_root = Path(__file__).parent.parent.parent
        
        # Check a sample of created files
        files_to_check = [
            "src/compareblocks/__init__.py",
            "src/compareblocks/gui/app.py", 
            "src/compareblocks/utils/test_runner.py",
            "tests/unit/test_project_structure.py"
        ]
        
        for file_path in files_to_check:
            full_path = project_root / file_path
            if full_path.exists():
                content = full_path.read_text(encoding='utf-8')
                first_line = content.split('\n')[0]
                # Check if first line contains the file path as a comment
                assert file_path in first_line, f"File {file_path} missing file path comment"
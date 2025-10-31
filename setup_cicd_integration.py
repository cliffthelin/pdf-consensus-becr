#!/usr/bin/env python3
"""
Setup CI/CD Integration

This script creates CI/CD configuration files and workflows for continuous
validation of the BECR project, including test execution, catalog validation,
and quality assurance.
"""

import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

def create_github_actions_workflow():
    """Create GitHub Actions workflow for CI/CD."""
    
    workflow = {
        'name': 'BECR CI/CD Pipeline',
        'on': {
            'push': {
                'branches': ['main', 'develop']
            },
            'pull_request': {
                'branches': ['main', 'develop']
            },
            'schedule': [
                {'cron': '0 2 * * *'}  # Daily at 2 AM
            ]
        },
        'jobs': {
            'test': {
                'runs-on': 'ubuntu-latest',
                'strategy': {
                    'matrix': {
                        'python-version': ['3.12']
                    }
                },
                'steps': [
                    {
                        'uses': 'actions/checkout@v4'
                    },
                    {
                        'name': 'Set up Python ${{ matrix.python-version }}',
                        'uses': 'actions/setup-python@v4',
                        'with': {
                            'python-version': '${{ matrix.python-version }}'
                        }
                    },
                    {
                        'name': 'Install system dependencies',
                        'run': '''
                            sudo apt-get update
                            sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
                            sudo apt-get install -y poppler-utils
                        '''
                    },
                    {
                        'name': 'Create virtual environment',
                        'run': '''
                            python -m venv .venv
                            source .venv/bin/activate
                            echo "VIRTUAL_ENV=$VIRTUAL_ENV" >> $GITHUB_ENV
                            echo "$VIRTUAL_ENV/bin" >> $GITHUB_PATH
                        '''
                    },
                    {
                        'name': 'Install dependencies',
                        'run': '''
                            pip install --upgrade pip
                            pip install -e .
                            pip install -e .[dev]
                        '''
                    },
                    {
                        'name': 'Validate project setup',
                        'run': 'python validate_setup.py'
                    },
                    {
                        'name': 'Validate function catalog',
                        'run': 'python functions/validate_catalog.py'
                    },
                    {
                        'name': 'Run comprehensive tests',
                        'run': '''
                            python run_tests.py --cov=src/compareblocks --cov-report=xml --cov-report=html --cov-fail-under=95
                        '''
                    },
                    {
                        'name': 'Validate test catalog consistency',
                        'run': 'python build_test_catalog.py'
                    },
                    {
                        'name': 'Check for missing functions',
                        'run': 'python analyze_missing_files_and_functions.py'
                    },
                    {
                        'name': 'Upload coverage reports',
                        'uses': 'codecov/codecov-action@v3',
                        'with': {
                            'file': './coverage.xml',
                            'flags': 'unittests',
                            'name': 'codecov-umbrella'
                        }
                    }
                ]
            },
            'quality': {
                'runs-on': 'ubuntu-latest',
                'needs': 'test',
                'steps': [
                    {
                        'uses': 'actions/checkout@v4'
                    },
                    {
                        'name': 'Set up Python',
                        'uses': 'actions/setup-python@v4',
                        'with': {
                            'python-version': '3.12'
                        }
                    },
                    {
                        'name': 'Install dependencies',
                        'run': '''
                            pip install --upgrade pip
                            pip install -e .[dev]
                        '''
                    },
                    {
                        'name': 'Run code formatting check',
                        'run': 'black --check src/ tests/'
                    },
                    {
                        'name': 'Run import sorting check',
                        'run': 'isort --check-only src/ tests/'
                    },
                    {
                        'name': 'Run linting',
                        'run': 'flake8 src/ tests/'
                    },
                    {
                        'name': 'Run type checking',
                        'run': 'mypy src/'
                    }
                ]
            },
            'integration': {
                'runs-on': 'ubuntu-latest',
                'needs': ['test', 'quality'],
                'if': "github.ref == 'refs/heads/main'",
                'steps': [
                    {
                        'uses': 'actions/checkout@v4'
                    },
                    {
                        'name': 'Set up Python',
                        'uses': 'actions/setup-python@v4',
                        'with': {
                            'python-version': '3.12'
                        }
                    },
                    {
                        'name': 'Install dependencies',
                        'run': '''
                            pip install --upgrade pip
                            pip install -e .[dev]
                        '''
                    },
                    {
                        'name': 'Run integration tests',
                        'run': 'python -m pytest tests/integration/ -v'
                    },
                    {
                        'name': 'Test MCP integration',
                        'run': 'python functions/run_mcp_tests.py'
                    },
                    {
                        'name': 'Generate project health report',
                        'run': 'python show_remaining_issues.py'
                    }
                ]
            }
        }
    }
    
    # Create .github/workflows directory
    workflows_dir = Path('.github/workflows')
    workflows_dir.mkdir(parents=True, exist_ok=True)
    
    # Write workflow file
    workflow_file = workflows_dir / 'ci-cd.yml'
    with open(workflow_file, 'w', encoding='utf-8') as f:
        yaml.dump(workflow, f, default_flow_style=False, sort_keys=False)
    
    return workflow_file

def create_pre_commit_hooks():
    """Create pre-commit hooks configuration."""
    
    pre_commit_config = {
        'repos': [
            {
                'repo': 'https://github.com/pre-commit/pre-commit-hooks',
                'rev': 'v4.4.0',
                'hooks': [
                    {'id': 'trailing-whitespace'},
                    {'id': 'end-of-file-fixer'},
                    {'id': 'check-yaml'},
                    {'id': 'check-json'},
                    {'id': 'check-added-large-files'},
                    {'id': 'check-merge-conflict'},
                    {'id': 'debug-statements'}
                ]
            },
            {
                'repo': 'https://github.com/psf/black',
                'rev': '23.7.0',
                'hooks': [
                    {
                        'id': 'black',
                        'language_version': 'python3.12'
                    }
                ]
            },
            {
                'repo': 'https://github.com/pycqa/isort',
                'rev': '5.12.0',
                'hooks': [
                    {
                        'id': 'isort',
                        'args': ['--profile', 'black']
                    }
                ]
            },
            {
                'repo': 'https://github.com/pycqa/flake8',
                'rev': '6.0.0',
                'hooks': [
                    {
                        'id': 'flake8',
                        'args': ['--max-line-length=88', '--extend-ignore=E203,W503']
                    }
                ]
            },
            {
                'repo': 'local',
                'hooks': [
                    {
                        'id': 'validate-setup',
                        'name': 'Validate Project Setup',
                        'entry': 'python validate_setup.py',
                        'language': 'system',
                        'pass_filenames': False,
                        'always_run': True
                    },
                    {
                        'id': 'validate-catalogs',
                        'name': 'Validate Function Catalogs',
                        'entry': 'python functions/validate_catalog.py',
                        'language': 'system',
                        'pass_filenames': False,
                        'files': r'functions/.*\.ndjson$'
                    },
                    {
                        'id': 'update-test-catalog',
                        'name': 'Update Test Catalog',
                        'entry': 'python build_test_catalog.py',
                        'language': 'system',
                        'pass_filenames': False,
                        'files': r'tests/.*\.py$'
                    }
                ]
            }
        ]
    }
    
    # Write pre-commit config
    pre_commit_file = Path('.pre-commit-config.yaml')
    with open(pre_commit_file, 'w', encoding='utf-8') as f:
        yaml.dump(pre_commit_config, f, default_flow_style=False, sort_keys=False)
    
    return pre_commit_file

def create_test_runner_script():
    """Create enhanced test runner script for CI/CD."""
    
    script_content = '''#!/usr/bin/env python3
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
'''
    
    # Write enhanced test runner
    runner_file = Path('run_tests_cicd.py')
    with open(runner_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Make executable on Unix systems
    try:
        runner_file.chmod(0o755)
    except:
        pass  # Windows doesn't support chmod
    
    return runner_file

def create_quality_checks_script():
    """Create quality checks script for CI/CD."""
    
    script_content = '''#!/usr/bin/env python3
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
'''
    
    # Write quality checks script
    quality_file = Path('run_quality_checks.py')
    with open(quality_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Make executable
    try:
        quality_file.chmod(0o755)
    except:
        pass
    
    return quality_file

def create_makefile():
    """Create Makefile for common development tasks."""
    
    makefile_content = '''# BECR Project Makefile
# Provides common development tasks and CI/CD integration

.PHONY: help install test test-fast test-integration test-gui quality format lint type-check clean setup-dev validate

# Default target
help:
	@echo "BECR Project Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  install      Install project dependencies"
	@echo "  setup-dev    Setup development environment"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test         Run all tests with coverage"
	@echo "  test-fast    Run fast tests only"
	@echo "  test-integration  Run integration tests"
	@echo "  test-gui     Run GUI tests"
	@echo ""
	@echo "Quality Commands:"
	@echo "  quality      Run all quality checks"
	@echo "  format       Format code with black and isort"
	@echo "  lint         Run linting checks"
	@echo "  type-check   Run type checking"
	@echo ""
	@echo "Validation Commands:"
	@echo "  validate     Validate project setup and catalogs"
	@echo ""
	@echo "Utility Commands:"
	@echo "  clean        Clean up generated files"

# Setup commands
install:
	pip install --upgrade pip
	pip install -e .
	pip install -e .[dev]

setup-dev: install
	pre-commit install
	python validate_setup.py

# Testing commands
test:
	python run_tests_cicd.py --cov=src/compareblocks --cov-report=html --cov-report=xml --cov-fail-under=95

test-fast:
	python run_tests_cicd.py --fast

test-integration:
	python run_tests_cicd.py --integration

test-gui:
	python run_tests_cicd.py --gui

# Quality commands
quality:
	python run_quality_checks.py

format:
	black src/ tests/
	isort src/ tests/

lint:
	flake8 src/ tests/

type-check:
	mypy src/

# Validation commands
validate:
	python validate_setup.py
	python functions/validate_catalog.py
	python build_test_catalog.py

# Utility commands
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ coverage.xml
	rm -rf .pytest_cache/
	rm -rf build/ dist/

# CI/CD integration
ci-test: validate test quality

ci-integration: test-integration
	python functions/run_mcp_tests.py
	python show_remaining_issues.py
'''
    
    # Write Makefile
    makefile = Path('Makefile')
    with open(makefile, 'w', encoding='utf-8') as f:
        f.write(makefile_content)
    
    return makefile

def setup_cicd_integration():
    """Setup complete CI/CD integration."""
    print("🚀 Setting up CI/CD Integration")
    print("=" * 50)
    
    created_files = []
    
    # Create GitHub Actions workflow
    print("📝 Creating GitHub Actions workflow...")
    workflow_file = create_github_actions_workflow()
    created_files.append(workflow_file)
    print(f"✅ Created: {workflow_file}")
    
    # Create pre-commit hooks
    print("📝 Creating pre-commit hooks configuration...")
    pre_commit_file = create_pre_commit_hooks()
    created_files.append(pre_commit_file)
    print(f"✅ Created: {pre_commit_file}")
    
    # Create enhanced test runner
    print("📝 Creating enhanced test runner...")
    test_runner = create_test_runner_script()
    created_files.append(test_runner)
    print(f"✅ Created: {test_runner}")
    
    # Create quality checks script
    print("📝 Creating quality checks script...")
    quality_script = create_quality_checks_script()
    created_files.append(quality_script)
    print(f"✅ Created: {quality_script}")
    
    # Create Makefile
    print("📝 Creating Makefile...")
    makefile = create_makefile()
    created_files.append(makefile)
    print(f"✅ Created: {makefile}")
    
    print(f"\n📊 CI/CD Integration Summary:")
    print(f"  Files created: {len(created_files)}")
    print(f"  GitHub Actions: Configured")
    print(f"  Pre-commit hooks: Configured")
    print(f"  Quality checks: Automated")
    print(f"  Test execution: Enhanced")
    
    print(f"\n💡 Next Steps:")
    print("1. Install pre-commit: pip install pre-commit")
    print("2. Setup hooks: pre-commit install")
    print("3. Test locally: make test")
    print("4. Run quality checks: make quality")
    print("5. Commit changes to trigger CI/CD")
    
    return created_files

if __name__ == "__main__":
    files = setup_cicd_integration()
    print(f"\n🎉 CI/CD integration setup complete!")
    print(f"Created {len(files)} configuration files for continuous validation.")
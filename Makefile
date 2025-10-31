# BECR Project Makefile
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

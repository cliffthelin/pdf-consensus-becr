# Technology Stack & Build System

## Core Technologies

- **Python 3.12+**: Required minimum version
- **Build System**: setuptools with pyproject.toml configuration
- **Package Management**: pip with virtual environment (.venv)

## Key Dependencies

### PDF & Image Processing
- PyMuPDF (>=1.23.0): PDF manipulation and rendering
- OpenCV (>=4.8.0): Computer vision and image processing

### GUI Framework
- PySide6 (>=6.6.0): Qt-based desktop interface

### Data & Validation
- Pydantic (>=2.5.0): Data validation and settings
- jsonschema (>=4.19.0): NDJSON schema validation
- NumPy (>=1.24.0): Numerical operations
- Pandas (>=2.1.0): Data manipulation

### Text Processing
- langdetect (>=1.0.9): Language detection
- rapidfuzz (>=3.5.0): Fuzzy string matching

### Testing & Quality
- pytest (>=7.4.0): Test framework with 95%+ coverage requirement
- pytest-qt (>=4.2.0): GUI testing support
- pytest-cov (>=4.1.0): Coverage reporting
- black, isort, flake8, mypy: Code formatting and linting

## Common Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install package in development mode
pip install -e .
pip install -e .[dev]
```

### Running Applications
```bash
# Run main application (immutable entry point)
python run_becr.py

# Run test suite (immutable entry point)
python run_tests.py

# Alternative: use installed console scripts
becr              # Main GUI application
becr-test         # Test runner utility
```

### Testing & Quality
```bash
# Run tests with coverage (configured in pyproject.toml)
pytest --cov=src/compareblocks --cov-report=html --cov-fail-under=95

# Code formatting
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

## Configuration Files

- **pyproject.toml**: Primary configuration for build, dependencies, and tools
- **pytest.ini**: Additional pytest configuration (legacy format)
- **.gitignore**: Standard Python gitignore with project-specific additions

## Development Philosophy

- **Test-Driven Development (TDD)**: Write tests first, 95%+ coverage mandatory
- **Real File Testing**: No mocks or stubs, use actual files and data
- **Immutable Runners**: Fixed entry points (run_becr.py, run_tests.py) that never change
- **Schema-First**: Strict NDJSON validation for all I/O operations
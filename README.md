# README.md
# BECR (Blockwise Extraction Comparison & Review) System

A test-driven system for comparing and reviewing text extraction results from PDFs at the block level.

## Project Structure

```
src/compareblocks/          # Main package
├── gbg/                    # Global Block Grid
├── io/                     # NDJSON Schema & I/O
├── mapping/                # Variation to Block Mapping
├── normalize/              # Text Normalization
├── features/               # Quality Metrics
├── consensus/              # Scoring & Decision Making
├── gui/                    # PySide6 Review Interface
└── utils/                  # Shared utilities

tests/                      # Test suite (95%+ coverage)
├── unit/                   # Unit tests
├── integration/            # Integration tests
├── gui/                    # GUI tests (pytest-qt)
└── fixtures/               # Test data and golden files
```

## Setup

1. Create virtual environment:
   ```bash
   python -m venv .venv
   ```

2. Activate virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Unix/macOS: `source .venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Install development dependencies:
   ```bash
   pip install -e .[dev]
   ```

## Running the Application

Use the immutable runner:
```bash
python run_becr.py
```

## Running Tests

Use the immutable test runner:
```bash
python run_tests.py
```

## Requirements

- Python 3.12+
- Virtual environment (.venv)
- All dependencies managed through pyproject.toml

## Testing Philosophy

- Test-Driven Development (TDD) methodology
- 95%+ test coverage requirement
- Real file-based testing (no mocks or stubs)
- Separate User_Function_Test and NonUser_Test categories
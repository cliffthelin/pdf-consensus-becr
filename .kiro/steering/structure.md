# Project Structure & Organization

## Root Directory Layout

```
├── src/compareblocks/          # Main package source code
├── tests/                      # Comprehensive test suite
├── docs/                       # Project documentation
├── config/                     # Configuration files
├── output/                     # Generated reports and analysis
├── Source_docs/                # Source documents for testing
├── .kiro/                      # Kiro IDE configuration
├── .venv/                      # Virtual environment (local)
├── run_becr.py                 # Immutable application entry point
├── run_tests.py                # Immutable test runner entry point
└── pyproject.toml              # Primary project configuration
```

## Source Code Architecture (`src/compareblocks/`)

```
src/compareblocks/
├── __init__.py                 # Package initialization
├── gbg/                        # Global Block Grid module
│   ├── __init__.py
│   ├── seed.py                 # Block seeding logic
│   ├── processor.py            # GBG processing
│   └── orientation.py          # Orientation detection
├── io/                         # Input/Output and schema validation
│   ├── __init__.py
│   ├── schemas.py              # NDJSON schema definitions
│   ├── loader.py               # Data loading utilities
│   └── writer.py               # Data writing utilities
├── mapping/                    # Variation to block mapping
│   ├── __init__.py
│   ├── variation_block.py      # Variation mapping logic
│   └── match.py                # Matching algorithms
├── normalize/                  # Text normalization (planned)
├── features/                   # Quality metrics (planned)
├── consensus/                  # Scoring & decision making (planned)
├── gui/                        # PySide6 review interface
│   ├── __init__.py
│   └── app.py                  # Main GUI application
├── config/                     # Configuration management
│   ├── __init__.py
│   └── file_manager.py         # File configuration handling
└── utils/                      # Shared utilities (planned)
```

## Test Structure (`tests/`)

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and fixtures
├── unit/                       # Unit tests (individual components)
│   ├── __init__.py
│   ├── test_*.py               # Unit test files
│   └── test_project_structure.py
├── integration/                # Integration tests (workflows)
│   ├── __init__.py
│   └── test_*.py               # Integration test files
├── gui/                        # GUI tests using pytest-qt
│   ├── __init__.py
│   └── test_*.py               # GUI test files
└── fixtures/                   # Test data and golden files
    ├── __init__.py
    ├── create_test_pdfs.py     # Test PDF generation
    └── *.pdf                   # Sample test files
```

## Naming Conventions

### Files & Modules
- **Snake case**: `variation_block.py`, `file_manager.py`
- **Test files**: `test_<module_name>.py` or `<module_name>_test.py`
- **Private modules**: Prefix with underscore `_internal.py`

### Classes & Functions
- **Classes**: PascalCase (`GlobalBlockGrid`, `VariationMapper`)
- **Functions/Methods**: snake_case (`process_variations`, `validate_schema`)
- **Constants**: UPPER_SNAKE_CASE (`INPUT_VARIATION_SCHEMA`)

### Test Categories
- **Unit tests**: `@pytest.mark.unit` - Individual component testing
- **Integration tests**: `@pytest.mark.integration` - Workflow testing
- **GUI tests**: `@pytest.mark.gui` - Interface testing with pytest-qt
- **Slow tests**: `@pytest.mark.slow` - Long-running tests

## Configuration Management

### Primary Configuration
- **pyproject.toml**: Build system, dependencies, tool configuration
- **pytest.ini**: Legacy pytest configuration (being migrated to pyproject.toml)

### Runtime Configuration
- **config/default_files.json**: Default file configurations
- **src/compareblocks/config/**: Runtime configuration management

## Import Patterns

### Internal Imports
```python
# Absolute imports from package root
from compareblocks.io.schemas import INPUT_VARIATION_SCHEMA
from compareblocks.gbg.processor import GlobalBlockProcessor

# Relative imports within modules
from .schemas import validate_input
from ..gbg import create_block_grid
```

### Test Imports
```python
# Tests use sys.path modification via conftest.py
import compareblocks
from compareblocks.io import schemas
```

## File Organization Principles

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Layered Architecture**: Clear dependencies from GUI → Business Logic → I/O
3. **Schema-First**: All data structures defined in schemas before implementation
4. **Test Proximity**: Tests mirror source structure for easy navigation
5. **Immutable Entry Points**: Fixed runners that never change for stability
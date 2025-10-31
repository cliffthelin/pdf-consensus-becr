# Adhoc Tests

This directory contains adhoc tests that validate specific aspects of the system using real data and files.

## Function Catalog Default File Validation

**File:** `test_function_catalog_default_file_validation.py`

### Purpose

This adhoc test validates that all functions documented in the function catalog (`functions/function_catalog.ndjson`) work correctly with the configured default PDF file. It ensures TDD compliance by testing real application functionality against actual user data.

### Methodology

The test compares the function catalog against the default in-progress file to ensure all documented functionality is operational. It validates:

1. **Configuration System Functions** - All file manager and configuration functions work with the default PDF
2. **Task 3 (GBG) Functions** - Global Block Grid processing works end-to-end with real PDF
3. **Task 4 (Variation Mapping) Functions** - IoU matching and variation management work with real blocks
4. **I/O Validation Functions** - Schema loading and NDJSON processing work correctly
5. **Full Pipeline Integration** - Complete processing pipeline works with default file
6. **Function Catalog Coverage** - All key modules are represented in the catalog
7. **Real File TDD Compliance** - All functionality uses real files, not mocks or stubs
8. **Error Handling** - Graceful handling of edge cases with real scenarios

### Running the Test

#### As Standalone Script
```bash
python tests/adhoc/test_function_catalog_default_file_validation.py
```

#### With pytest
```bash
python -m pytest tests/adhoc/test_function_catalog_default_file_validation.py -v
```

#### As part of full test suite
```bash
python -m pytest tests/adhoc/ -v
```

### Expected Output

The test should validate:
- ✅ 126 functions documented in catalog
- ✅ Configuration system working with default PDF (62 pages, 1066 blocks)
- ✅ Task 3 GBG system operational
- ✅ Task 4 variation mapping system operational
- ✅ I/O validation system working
- ✅ Full pipeline integration successful
- ✅ Real file TDD compliance validated

### Key Validation Points

1. **Real Data Usage**: Uses actual `English Language Arts Standards.pdf` (992KB, 62 pages)
2. **Function Coverage**: Validates 126 documented functions across 7 key modules
3. **End-to-End Testing**: Tests complete processing pipeline with real PDF
4. **TDD Compliance**: Ensures no mocks, stubs, or synthetic data used
5. **Configuration Integration**: Validates all components use centralized configuration

### When to Run

- After major changes to function catalog
- Before releases to ensure all documented functionality works
- When adding new functions to validate integration
- As part of CI/CD pipeline for comprehensive validation
- When troubleshooting issues with default file processing

### Maintenance

Update this test when:
- New functions are added to the catalog
- Default PDF file changes
- Configuration structure changes
- New modules are added to the system
- Function signatures or return types change

This adhoc test serves as a comprehensive validation that the documented function catalog accurately represents working functionality with real user data.
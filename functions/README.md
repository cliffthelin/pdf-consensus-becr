# Function Catalog Documentation

## Overview

The `function_catalog.ndjson` file contains a comprehensive catalog of all application functions in the BECR system with detailed field attributes that specify what is expected for each field from the functions.

## Enhanced Field Attributes

Each function entry now includes the following enhanced attributes:

### Core Function Information
- **function_name**: Full function name including class if applicable
- **module**: Python module path
- **class**: Class name (null for standalone functions)
- **description**: Detailed description of function purpose
- **parameters**: List of function parameters with types
- **return_type**: Expected return type
- **test_file**: Path to test file that validates the function
- **test_description**: Description of how the function is tested

### Enhanced Attributes

#### field_attributes
Detailed specifications for each field the function interacts with:

```json
"field_attributes": {
    "field_name": {
        "type": "Expected data type",
        "constraint": "Validation constraints",
        "description": "Field purpose and usage",
        "default": "Default value if applicable",
        "calculation": "How value is calculated if applicable",
        "required_keys": ["list", "of", "required", "keys"] // for dict returns
    }
}
```

#### side_effects
List of side effects the function may have:
- File system operations
- State modifications
- Exception raising
- Object creation/destruction

#### dependencies
List of external dependencies required:
- Python modules
- Third-party libraries
- Internal classes/functions

## Field Attribute Types

### Constraint Examples
- `">= 0.0"` - Numeric constraints
- `"not empty"` - String constraints  
- `"valid file path"` - Path constraints
- `"0.0 <= value <= 1.0"` - Range constraints
- `"length == 2"` - Collection constraints
- `"boolean value"` - Type constraints

### Type Examples
- `"float"`, `"int"`, `"str"`, `"bool"` - Basic types
- `"Optional[str]"` - Optional types
- `"List[SeedBlock]"` - Generic types
- `"Dict[str, Any]"` - Dictionary types
- `"Union[str, Path]"` - Union types

## Usage Examples

### Function with Input Validation
```json
{
    "function_name": "BoundingBox.__post_init__",
    "field_attributes": {
        "self.x": {
            "type": "float",
            "constraint": ">= 0.0",
            "description": "X coordinate of top-left corner"
        },
        "self.width": {
            "type": "float", 
            "constraint": "> 0.0",
            "description": "Width of bounding box"
        }
    },
    "side_effects": ["Raises ValueError if width/height <= 0 or coordinates < 0"]
}
```

### Function with Complex Return Type
```json
{
    "function_name": "GBGProcessor.process_pdf",
    "field_attributes": {
        "return_value": {
            "type": "Dict[str, Any]",
            "constraint": "complete processing results",
            "description": "Processing results with pages and summary",
            "required_keys": ["pdf_path", "pdf_name", "processing_metadata", "pages", "summary"]
        }
    }
}
```

### Function with Calculations
```json
{
    "function_name": "BoundingBox.area",
    "field_attributes": {
        "return_value": {
            "type": "float",
            "constraint": "> 0.0", 
            "description": "Area in square units",
            "calculation": "self.width * self.height"
        }
    }
}
```

## Testing Compliance

All functions are tested against real application data following TDD principles:

- **Real Data Testing**: Tests use actual PDF files and user configuration
- **No Artificial Scenarios**: No mocked or stubbed data
- **Production Equivalent**: Tests produce same results as production
- **Not Applicable Handling**: Tests skip when real data doesn't support scenario

## Validation

### Function Catalog Validation
```bash
python functions/validate_catalog.py
```
Validates the structure and completeness of the function catalog.

### Default File Integration Validation
```bash
python validate_function_catalog.py
```
Runs comprehensive adhoc test that validates all catalog functions work with the configured default PDF file. This ensures TDD compliance by testing real application functionality against actual user data.

## Maintenance

When adding new functions:

1. Include all required core attributes
2. Specify detailed field_attributes for all inputs/outputs
3. Document side_effects and dependencies
4. Ensure test_file uses real application data
5. Update this documentation if new attribute types are added

## Function Categories

The catalog covers these major system components:

- **Core Data Types** (6 functions) - BoundingBox, OrientationHints, SeedBlock
- **PDF Processing** (25 functions) - Seed detection, page analysis, orientation
- **I/O Operations** (20 functions) - NDJSON loading/writing, schema validation
- **Variation Mapping** (18 functions) - IoU matching, block association
- **Configuration Management** (25 functions) - File paths, output handling
- **Visual OCR Testing** (11 functions) - Multi-input feeds, JSON validation, test results
- **GUI Application** (1 function) - Main application entry point

Total: **301 functions** with comprehensive field attribute specifications.
#!/usr/bin/env python3
"""
Validation script for the enhanced function catalog.
Verifies that all required attributes are present and properly formatted.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Set

def validate_function_entry(entry: Dict[str, Any], line_num: int) -> List[str]:
    """Validate a single function catalog entry."""
    errors = []
    
    # Required core attributes
    required_attrs = [
        "function_name", "module", "description", "parameters", 
        "return_type", "test_file", "test_description"
    ]
    
    for attr in required_attrs:
        if attr not in entry:
            errors.append(f"Line {line_num}: Missing required attribute '{attr}'")
    
    # Enhanced attributes
    enhanced_attrs = ["field_attributes", "side_effects", "dependencies"]
    for attr in enhanced_attrs:
        if attr not in entry:
            errors.append(f"Line {line_num}: Missing enhanced attribute '{attr}'")
    
    # Validate field_attributes structure
    if "field_attributes" in entry:
        field_attrs = entry["field_attributes"]
        if not isinstance(field_attrs, dict):
            errors.append(f"Line {line_num}: field_attributes must be a dictionary")
        else:
            for field_name, field_spec in field_attrs.items():
                if not isinstance(field_spec, dict):
                    errors.append(f"Line {line_num}: field_attributes['{field_name}'] must be a dictionary")
                    continue
                
                # Check required field specification attributes
                required_field_attrs = ["type", "description"]
                for req_attr in required_field_attrs:
                    if req_attr not in field_spec:
                        errors.append(f"Line {line_num}: field_attributes['{field_name}'] missing '{req_attr}'")
    
    # Validate side_effects is a list
    if "side_effects" in entry and not isinstance(entry["side_effects"], list):
        errors.append(f"Line {line_num}: side_effects must be a list")
    
    # Validate dependencies is a list
    if "dependencies" in entry and not isinstance(entry["dependencies"], list):
        errors.append(f"Line {line_num}: dependencies must be a list")
    
    # Validate test file exists
    if "test_file" in entry:
        test_file_path = Path(entry["test_file"])
        if not test_file_path.exists():
            errors.append(f"Line {line_num}: Test file '{entry['test_file']}' does not exist")
    
    return errors

def validate_catalog(catalog_path: Path) -> Dict[str, Any]:
    """Validate the entire function catalog."""
    results = {
        "total_functions": 0,
        "valid_functions": 0,
        "errors": [],
        "warnings": [],
        "statistics": {
            "modules": set(),
            "classes": set(),
            "test_files": set(),
            "return_types": set()
        }
    }
    
    if not catalog_path.exists():
        results["errors"].append(f"Catalog file not found: {catalog_path}")
        return results
    
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    results["total_functions"] += 1
                    
                    # Validate entry
                    entry_errors = validate_function_entry(entry, line_num)
                    if entry_errors:
                        results["errors"].extend(entry_errors)
                    else:
                        results["valid_functions"] += 1
                    
                    # Collect statistics
                    if "module" in entry:
                        results["statistics"]["modules"].add(entry["module"])
                    if "class" in entry and entry["class"]:
                        results["statistics"]["classes"].add(entry["class"])
                    if "test_file" in entry:
                        results["statistics"]["test_files"].add(entry["test_file"])
                    if "return_type" in entry:
                        results["statistics"]["return_types"].add(entry["return_type"])
                
                except json.JSONDecodeError as e:
                    results["errors"].append(f"Line {line_num}: Invalid JSON - {e}")
    
    except Exception as e:
        results["errors"].append(f"Error reading catalog file: {e}")
    
    # Convert sets to lists for JSON serialization
    for key, value in results["statistics"].items():
        if isinstance(value, set):
            results["statistics"][key] = sorted(list(value))
    
    return results

def main():
    """Main validation function."""
    catalog_path = Path(__file__).parent / "function_catalog.ndjson"
    results = validate_catalog(catalog_path)
    
    print("Function Catalog Validation Results")
    print("=" * 40)
    print(f"Total functions: {results['total_functions']}")
    print(f"Valid functions: {results['valid_functions']}")
    print(f"Errors: {len(results['errors'])}")
    print(f"Warnings: {len(results['warnings'])}")
    
    if results["errors"]:
        print("\nErrors:")
        for error in results["errors"]:
            print(f"  - {error}")
    
    if results["warnings"]:
        print("\nWarnings:")
        for warning in results["warnings"]:
            print(f"  - {warning}")
    
    print("\nStatistics:")
    print(f"  Modules: {len(results['statistics']['modules'])}")
    print(f"  Classes: {len(results['statistics']['classes'])}")
    print(f"  Test files: {len(results['statistics']['test_files'])}")
    print(f"  Return types: {len(results['statistics']['return_types'])}")
    
    # Success/failure
    if results["errors"]:
        print(f"\n❌ Validation FAILED with {len(results['errors'])} errors")
        return 1
    else:
        print(f"\n✅ Validation PASSED - All {results['valid_functions']} functions are properly documented")
        return 0

if __name__ == "__main__":
    exit(main())
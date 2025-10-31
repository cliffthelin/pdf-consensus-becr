#!/usr/bin/env python3
"""
Add Missing Functions to Catalog

This script adds all missing functions identified in the analysis to the function_catalog.ndjson
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any
from datetime import datetime

def load_missing_functions_report() -> Dict[str, Any]:
    """Load the missing functions report."""
    report_path = Path('output/missing_files_and_functions_report.json')
    
    if not report_path.exists():
        print("❌ Missing functions report not found. Run analyze_missing_files_and_functions.py first.")
        return {}
    
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_existing_catalog() -> List[Dict]:
    """Load existing function catalog."""
    catalog_path = Path('functions/function_catalog.ndjson')
    functions = []
    
    if catalog_path.exists():
        with open(catalog_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        functions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    
    return functions

def determine_test_file(module_path: str, function_name: str, class_name: str = None) -> str:
    """Determine the appropriate test file for a function."""
    # Convert module path to test file path
    if module_path.startswith('compareblocks.'):
        # Source module
        parts = module_path.split('.')
        if len(parts) >= 2:
            category = parts[1]  # analytics, engines, etc.
            
            # Map to test categories
            if category in ['gui']:
                return f"tests/gui/test_{parts[-1]}.py"
            elif category in ['gbg', 'io', 'consensus', 'features', 'mapping', 'normalize']:
                return f"tests/integration/test_{parts[-1]}.py"
            else:
                return f"tests/unit/test_{parts[-1]}.py"
        else:
            return f"tests/unit/test_{parts[-1]}.py"
    else:
        # Root level utility
        return f"tests/unit/test_{module_path.replace('.', '_')}.py"

def create_function_description(function_name: str, docstring: str, parameters: List[str], class_name: str = None) -> str:
    """Create a function description."""
    if docstring:
        # Use first line of docstring
        return docstring.split('\n')[0].strip()
    
    # Generate description from function name
    if class_name:
        if function_name.startswith('__') and function_name.endswith('__'):
            return f"Initialize or manage {class_name} dunder method {function_name}"
        elif function_name.startswith('_'):
            return f"Internal {class_name} method for {function_name[1:].replace('_', ' ')}"
        else:
            return f"{class_name} method to {function_name.replace('_', ' ')}"
    else:
        if function_name == 'main':
            return "Main function for command-line usage"
        else:
            return f"Function to {function_name.replace('_', ' ')}"

def determine_return_type(function_name: str, class_name: str = None) -> str:
    """Determine likely return type based on function name."""
    if function_name.startswith('is_') or function_name.startswith('has_') or function_name.startswith('should_'):
        return "bool"
    elif function_name.startswith('get_') or function_name.startswith('find_'):
        if 'list' in function_name or 'all' in function_name:
            return "List[Any]"
        elif 'dict' in function_name or 'config' in function_name:
            return "Dict[str, Any]"
        else:
            return "Any"
    elif function_name.startswith('create_') or function_name.startswith('build_'):
        return "Any"
    elif function_name.startswith('save_') or function_name.startswith('write_') or function_name.startswith('update_'):
        return "None"
    elif function_name == '__init__':
        return "None"
    elif function_name == 'main':
        return "None"
    else:
        return "Any"

def create_catalog_entry(missing_func: Dict[str, Any]) -> Dict[str, Any]:
    """Create a catalog entry for a missing function."""
    function_name = missing_func['function_name']
    module = missing_func['module']
    class_name = missing_func.get('class')
    parameters = missing_func.get('parameters', [])
    docstring = missing_func.get('docstring', '')
    
    # Create parameters list
    if class_name and parameters and parameters[0] == 'self':
        param_list = ['self'] + [f"{p}: Any" for p in parameters[1:]]
    else:
        param_list = [f"{p}: Any" for p in parameters]
    
    # Determine test file
    test_file = determine_test_file(module, function_name, class_name)
    
    # Create description
    description = create_function_description(function_name, docstring, parameters, class_name)
    
    # Determine return type
    return_type = determine_return_type(function_name, class_name)
    
    # Create test description
    if class_name:
        test_description = f"Tests {class_name}.{function_name} functionality with real data"
    else:
        test_description = f"Tests {function_name} functionality with real data"
    
    entry = {
        "function_name": function_name,
        "module": f"src.{module}" if not module.startswith('src.') and not module in ['build_test_catalog', 'analyze_missing_files_and_functions', 'show_remaining_issues', 'visual_ocr_testing_tool'] else module,
        "class": class_name,
        "description": description,
        "parameters": param_list,
        "return_type": return_type,
        "test_file": test_file,
        "test_description": test_description,
        "field_attributes": {
            "metadata": {
                "enhanced": True,
                "enhancement_version": "2.0",
                "last_updated": "2024-10-27",
                "auto_generated": True
            }
        },
        "side_effects": [],
        "dependencies": [],
        "test_functions": [],
        "test_count": 0
    }
    
    # Add specific attributes based on function type
    if function_name == '__init__':
        entry["side_effects"] = ["Initializes object state"]
    elif function_name.startswith('save_') or function_name.startswith('write_'):
        entry["side_effects"] = ["File I/O operations"]
        entry["dependencies"] = ["pathlib"]
    elif function_name == 'main':
        entry["side_effects"] = ["Command-line execution"]
        entry["dependencies"] = ["sys", "argparse"]
    
    return entry

def add_missing_functions():
    """Add all missing functions to the catalog."""
    print("🔧 Adding Missing Functions to Catalog")
    print("=" * 50)
    
    # Load data
    report = load_missing_functions_report()
    if not report:
        return
    
    existing_catalog = load_existing_catalog()
    missing_functions = report.get('missing_functions', [])
    
    print(f"📚 Loaded {len(existing_catalog)} existing functions")
    print(f"➕ Adding {len(missing_functions)} missing functions")
    
    # Create new entries
    new_entries = []
    for missing_func in missing_functions:
        entry = create_catalog_entry(missing_func)
        new_entries.append(entry)
    
    # Combine with existing catalog
    all_entries = existing_catalog + new_entries
    
    # Sort by function name for consistency
    all_entries.sort(key=lambda x: x['function_name'])
    
    # Write updated catalog
    catalog_path = Path('functions/function_catalog.ndjson')
    backup_path = Path('functions/function_catalog_backup.ndjson')
    
    # Create backup
    if catalog_path.exists():
        catalog_path.rename(backup_path)
        print(f"📋 Created backup: {backup_path}")
    
    # Write new catalog
    with open(catalog_path, 'w', encoding='utf-8') as f:
        for entry in all_entries:
            f.write(json.dumps(entry, separators=(',', ':')) + '\n')
    
    print(f"✅ Updated catalog with {len(all_entries)} total functions")
    print(f"📁 Catalog saved to: {catalog_path}")
    
    # Generate summary
    by_module = {}
    for entry in new_entries:
        module = entry['module']
        if module not in by_module:
            by_module[module] = 0
        by_module[module] += 1
    
    print(f"\n📊 Functions Added by Module:")
    for module, count in sorted(by_module.items()):
        print(f"  {module}: {count} functions")
    
    return len(new_entries)

if __name__ == "__main__":
    added_count = add_missing_functions()
    if added_count:
        print(f"\n🎉 Successfully added {added_count} functions to catalog!")
        print("💡 Next steps:")
        print("  1. Run build_test_catalog.py to update cross-references")
        print("  2. Review and enhance function descriptions as needed")
        print("  3. Add proper dependencies and side effects")
    else:
        print("❌ No functions were added. Check the missing functions report.")
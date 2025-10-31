#!/usr/bin/env python3
"""
Identify Untested Functions

This script identifies all functions in the catalog that don't have tests
and creates a plan for adding comprehensive test coverage.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

def load_function_catalog() -> List[Dict]:
    """Load the function catalog."""
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

def analyze_test_coverage():
    """Analyze test coverage and identify untested functions."""
    print("🔍 Analyzing Test Coverage")
    print("=" * 40)
    
    functions = load_function_catalog()
    
    # Categorize functions by test status
    tested_functions = []
    untested_functions = []
    
    for func in functions:
        test_count = func.get('test_count', 0)
        if test_count > 0:
            tested_functions.append(func)
        else:
            untested_functions.append(func)
    
    print(f"📊 Coverage Statistics:")
    print(f"  Total functions: {len(functions)}")
    print(f"  Tested functions: {len(tested_functions)}")
    print(f"  Untested functions: {len(untested_functions)}")
    print(f"  Coverage percentage: {len(tested_functions)/len(functions)*100:.1f}%")
    print()
    
    # Group untested functions by module
    by_module = {}
    for func in untested_functions:
        module = func.get('module', 'unknown')
        if module not in by_module:
            by_module[module] = []
        by_module[module].append(func)
    
    print(f"📋 Untested Functions by Module:")
    print("-" * 40)
    
    for module, funcs in sorted(by_module.items()):
        print(f"\n{module} ({len(funcs)} functions):")
        for func in funcs:
            func_name = func['function_name']
            class_name = func.get('class')
            if class_name:
                print(f"  - {class_name}.{func_name}")
            else:
                print(f"  - {func_name}")
    
    # Save detailed report
    report = {
        'total_functions': len(functions),
        'tested_functions': len(tested_functions),
        'untested_functions': len(untested_functions),
        'coverage_percentage': len(tested_functions)/len(functions)*100,
        'untested_by_module': {
            module: [
                {
                    'function_name': f['function_name'],
                    'class': f.get('class'),
                    'module': f.get('module'),
                    'test_file': f.get('test_file'),
                    'description': f.get('description', ''),
                    'parameters': f.get('parameters', [])
                }
                for f in funcs
            ]
            for module, funcs in by_module.items()
        }
    }
    
    report_path = Path('output/untested_functions_report.json')
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    
    return untested_functions

if __name__ == "__main__":
    untested = analyze_test_coverage()
    print(f"\n🎯 Next step: Create tests for {len(untested)} untested functions")
#!/usr/bin/env python3
"""
Build Test Catalog Script

Analyzes all test files to create a comprehensive test catalog that mirrors
the function catalog structure and cross-references functions with their tests.
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime

class TestFunctionAnalyzer(ast.NodeVisitor):
    """AST visitor to extract test function information."""
    
    def __init__(self):
        self.test_functions = []
        self.current_class = None
        self.imports = []
    
    def visit_Import(self, node):
        """Visit import statements."""
        for alias in node.names:
            self.imports.append(alias.name)
    
    def visit_ImportFrom(self, node):
        """Visit from...import statements."""
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        if node.name.startswith('test_'):
            # Extract docstring
            docstring = ""
            if (node.body and isinstance(node.body[0], ast.Expr) and 
                isinstance(node.body[0].value, ast.Constant) and 
                isinstance(node.body[0].value.value, str)):
                docstring = node.body[0].value.value.strip()
            
            # Determine what function this test is testing
            tested_function = self._infer_tested_function(node.name, docstring)
            
            test_info = {
                "test_name": node.name,
                "test_class": self.current_class,
                "full_test_name": f"{self.current_class}.{node.name}" if self.current_class else node.name,
                "description": docstring.split('\n')[0] if docstring else f"Test {node.name}",
                "line_number": node.lineno,
                "tested_function": tested_function,
                "test_type": self._determine_test_type(node.name, docstring),
                "parameters": [arg.arg for arg in node.args.args if arg.arg != 'self'],
                "decorators": [self._get_decorator_name(dec) for dec in node.decorator_list]
            }
            
            self.test_functions.append(test_info)
    
    def _infer_tested_function(self, test_name: str, docstring: str) -> str:
        """Infer what function this test is testing."""
        # Remove test_ prefix
        base_name = test_name[5:] if test_name.startswith('test_') else test_name
        
        # Common patterns
        if base_name.endswith('_success') or base_name.endswith('_failure') or base_name.endswith('_error'):
            # Remove success/failure/error suffix
            for suffix in ['_success', '_failure', '_error', '_exception', '_invalid', '_valid']:
                if base_name.endswith(suffix):
                    base_name = base_name[:-len(suffix)]
                    break
        
        # Handle class method patterns
        if '_init' in base_name:
            base_name = base_name.replace('_init', '.__init__')
        
        # Handle main function patterns
        if base_name == 'main' or base_name.startswith('main_'):
            return 'main'
        
        return base_name
    
    def _determine_test_type(self, test_name: str, docstring: str) -> str:
        """Determine the type of test."""
        if 'success' in test_name or 'valid' in test_name:
            return 'success_case'
        elif 'failure' in test_name or 'error' in test_name or 'invalid' in test_name:
            return 'error_case'
        elif 'exception' in test_name:
            return 'exception_case'
        elif 'integration' in test_name or 'workflow' in test_name:
            return 'integration'
        else:
            return 'unit'
    
    def _get_decorator_name(self, decorator) -> str:
        """Get decorator name."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}" if hasattr(decorator.value, 'id') else decorator.attr
        else:
            return str(decorator)

def analyze_test_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a test file and extract test function information."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = TestFunctionAnalyzer()
        analyzer.visit(tree)
        
        # Extract module docstring
        module_docstring = ""
        if (tree.body and isinstance(tree.body[0], ast.Expr) and 
            isinstance(tree.body[0].value, ast.Constant) and 
            isinstance(tree.body[0].value.value, str)):
            module_docstring = tree.body[0].value.value.strip()
        
        return {
            "test_file": str(file_path),
            "module_name": file_path.stem,
            "module_docstring": module_docstring,
            "imports": analyzer.imports,
            "test_functions": analyzer.test_functions,
            "total_tests": len(analyzer.test_functions)
        }
    
    except Exception as e:
        return {
            "test_file": str(file_path),
            "module_name": file_path.stem,
            "error": str(e),
            "test_functions": [],
            "total_tests": 0
        }

def load_function_catalog(catalog_path: Path) -> Dict[str, Dict]:
    """Load the function catalog and create a lookup by function name."""
    functions = {}
    
    if not catalog_path.exists():
        return functions
    
    with open(catalog_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    function_name = entry.get('function_name', '')
                    functions[function_name] = entry
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON on line {line_num}: {e}")
    
    return functions

def find_test_files() -> List[Path]:
    """Find all test files in the project."""
    test_files = []
    
    # Unit tests
    tests_unit_dir = Path('tests/unit')
    if tests_unit_dir.exists():
        test_files.extend(tests_unit_dir.glob('test_*.py'))
    
    # Integration tests
    tests_integration_dir = Path('tests/integration')
    if tests_integration_dir.exists():
        test_files.extend(tests_integration_dir.glob('test_*.py'))
    
    # GUI tests
    tests_gui_dir = Path('tests/gui')
    if tests_gui_dir.exists():
        test_files.extend(tests_gui_dir.glob('test_*.py'))
    
    return sorted(test_files)

def create_test_catalog_entry(test_info: Dict, test_file_info: Dict, function_catalog: Dict) -> Dict:
    """Create a test catalog entry."""
    tested_function = test_info['tested_function']
    
    # Try to find the corresponding function in the catalog
    function_entry = None
    possible_names = [
        tested_function,
        f"{test_file_info['module_name'][5:]}.{tested_function}",  # Remove test_ prefix
        tested_function.replace('_', ''),
        tested_function.replace('_', '.'),
    ]
    
    for name in possible_names:
        if name in function_catalog:
            function_entry = function_catalog[name]
            break
    
    # Determine test file category
    test_category = "unit"
    if "integration" in test_file_info['test_file']:
        test_category = "integration"
    elif "gui" in test_file_info['test_file']:
        test_category = "gui"
    
    entry = {
        "test_name": test_info['full_test_name'],
        "test_file": test_file_info['test_file'],
        "test_module": test_file_info['module_name'],
        "test_class": test_info['test_class'],
        "test_function": test_info['test_name'],
        "description": test_info['description'],
        "tested_function": tested_function,
        "test_type": test_info['test_type'],
        "test_category": test_category,
        "line_number": test_info['line_number'],
        "parameters": test_info['parameters'],
        "decorators": test_info['decorators'],
        "function_exists_in_catalog": function_entry is not None,
        "function_module": function_entry.get('module', '') if function_entry else '',
        "function_test_file": function_entry.get('test_file', '') if function_entry else '',
        "cross_reference_valid": function_entry is not None and function_entry.get('test_file', '') == test_file_info['test_file'],
        "metadata": {
            "created": datetime.now().isoformat(),
            "analyzer_version": "1.0"
        }
    }
    
    return entry

def build_test_catalog():
    """Build the complete test catalog."""
    print("🔍 Building Test Catalog")
    print("=" * 50)
    
    # Load function catalog
    function_catalog_path = Path('functions/function_catalog.ndjson')
    function_catalog = load_function_catalog(function_catalog_path)
    print(f"📚 Loaded {len(function_catalog)} functions from catalog")
    
    # Find test files
    test_files = find_test_files()
    print(f"🧪 Found {len(test_files)} test files")
    
    # Analyze test files
    all_test_entries = []
    total_tests = 0
    
    for test_file in test_files:
        print(f"Analyzing: {test_file}")
        test_file_info = analyze_test_file(test_file)
        
        if 'error' in test_file_info:
            print(f"  ❌ Error: {test_file_info['error']}")
            continue
        
        file_test_count = len(test_file_info['test_functions'])
        total_tests += file_test_count
        print(f"  ✅ Found {file_test_count} test functions")
        
        # Create catalog entries for each test
        for test_info in test_file_info['test_functions']:
            entry = create_test_catalog_entry(test_info, test_file_info, function_catalog)
            all_test_entries.append(entry)
    
    # Write test catalog
    test_catalog_path = Path('functions/test_catalog.ndjson')
    with open(test_catalog_path, 'w', encoding='utf-8') as f:
        for entry in all_test_entries:
            f.write(json.dumps(entry, separators=(',', ':')) + '\n')
    
    print(f"\n📊 Test Catalog Summary:")
    print(f"  Total test functions: {total_tests}")
    print(f"  Test catalog entries: {len(all_test_entries)}")
    print(f"  Test catalog saved to: {test_catalog_path}")
    
    # Generate cross-reference report
    generate_cross_reference_report(all_test_entries, function_catalog)
    
    return all_test_entries

def generate_cross_reference_report(test_entries: List[Dict], function_catalog: Dict):
    """Generate a cross-reference report between functions and tests."""
    print(f"\n🔗 Cross-Reference Analysis:")
    print("=" * 50)
    
    # Count cross-references
    valid_cross_refs = sum(1 for entry in test_entries if entry['cross_reference_valid'])
    functions_with_tests = len(set(entry['tested_function'] for entry in test_entries if entry['function_exists_in_catalog']))
    functions_without_tests = len(function_catalog) - functions_with_tests
    
    print(f"✅ Valid cross-references: {valid_cross_refs}")
    print(f"📚 Functions with tests: {functions_with_tests}")
    print(f"❌ Functions without tests: {functions_without_tests}")
    
    # Test categories
    categories = {}
    for entry in test_entries:
        category = entry['test_category']
        categories[category] = categories.get(category, 0) + 1
    
    print(f"\n📋 Test Categories:")
    for category, count in categories.items():
        print(f"  {category}: {count} tests")
    
    # Test types
    test_types = {}
    for entry in test_entries:
        test_type = entry['test_type']
        test_types[test_type] = test_types.get(test_type, 0) + 1
    
    print(f"\n🏷️  Test Types:")
    for test_type, count in test_types.items():
        print(f"  {test_type}: {count} tests")

def update_function_catalog_with_tests(test_entries: List[Dict]):
    """Update function catalog entries to include their corresponding test names."""
    print(f"\n🔄 Updating Function Catalog with Test References")
    print("=" * 50)
    
    # Load existing function catalog
    function_catalog_path = Path('functions/function_catalog.ndjson')
    functions = []
    
    with open(function_catalog_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    functions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # Create mapping of function names to their tests
    function_to_tests = {}
    for test_entry in test_entries:
        if test_entry['function_exists_in_catalog']:
            func_name = test_entry['tested_function']
            if func_name not in function_to_tests:
                function_to_tests[func_name] = []
            function_to_tests[func_name].append(test_entry['test_name'])
    
    # Update function entries
    updated_count = 0
    for func_entry in functions:
        func_name = func_entry['function_name']
        
        # Find matching tests
        matching_tests = []
        for test_entry in test_entries:
            if (test_entry['function_exists_in_catalog'] and 
                test_entry['tested_function'] == func_name):
                matching_tests.append(test_entry['test_name'])
        
        if matching_tests:
            func_entry['test_functions'] = matching_tests
            func_entry['test_count'] = len(matching_tests)
            updated_count += 1
        else:
            func_entry['test_functions'] = []
            func_entry['test_count'] = 0
    
    # Write updated function catalog
    with open(function_catalog_path, 'w', encoding='utf-8') as f:
        for func_entry in functions:
            f.write(json.dumps(func_entry, separators=(',', ':')) + '\n')
    
    print(f"✅ Updated {updated_count} function entries with test references")
    print(f"📚 Function catalog updated: {function_catalog_path}")

def main():
    """Main function to build test catalog and update function catalog."""
    test_entries = build_test_catalog()
    update_function_catalog_with_tests(test_entries)
    
    print(f"\n🎉 Test Catalog Build Complete!")
    print(f"📁 Files created/updated:")
    print(f"  - functions/test_catalog.ndjson (new test catalog)")
    print(f"  - functions/function_catalog.ndjson (updated with test references)")

if __name__ == "__main__":
    main()
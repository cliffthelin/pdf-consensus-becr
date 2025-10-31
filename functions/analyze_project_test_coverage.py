#!/usr/bin/env python3
"""
Analyze all project files with functions and their test coverage status.

This script scans the entire project to identify all source files containing
functions and determines which have tests and which are missing tests.
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
import re

class FunctionAnalyzer(ast.NodeVisitor):
    """AST visitor to extract function and class information."""
    
    def __init__(self):
        self.functions = []
        self.classes = []
        self.current_class = None
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        self.classes.append({
            'name': node.name,
            'line': node.lineno,
            'methods': []
        })
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        func_info = {
            'name': node.name,
            'line': node.lineno,
            'class': self.current_class,
            'is_private': node.name.startswith('_'),
            'is_dunder': node.name.startswith('__') and node.name.endswith('__'),
            'args': [arg.arg for arg in node.args.args]
        }
        
        if self.current_class:
            # Add to current class methods
            for cls in self.classes:
                if cls['name'] == self.current_class:
                    cls['methods'].append(func_info)
                    break
        else:
            self.functions.append(func_info)
        
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions."""
        self.visit_FunctionDef(node)  # Same handling as regular functions

def analyze_python_file(file_path: Path) -> Dict:
    """Analyze a Python file for functions and classes."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = FunctionAnalyzer()
        analyzer.visit(tree)
        
        return {
            'file_path': str(file_path),
            'functions': analyzer.functions,
            'classes': analyzer.classes,
            'total_functions': len(analyzer.functions) + sum(len(cls['methods']) for cls in analyzer.classes),
            'has_functions': len(analyzer.functions) > 0 or any(len(cls['methods']) > 0 for cls in analyzer.classes)
        }
    except Exception as e:
        return {
            'file_path': str(file_path),
            'error': str(e),
            'has_functions': False,
            'total_functions': 0
        }

def find_test_files() -> Set[str]:
    """Find all test files in the project."""
    test_files = set()
    
    # Scan tests directory
    tests_dir = Path('tests')
    if tests_dir.exists():
        for test_file in tests_dir.rglob('*.py'):
            test_files.add(str(test_file))
    
    return test_files

def find_source_files() -> List[Path]:
    """Find all Python source files in the project."""
    source_files = []
    
    # Main source directory
    src_dir = Path('src/compareblocks')
    if src_dir.exists():
        for py_file in src_dir.rglob('*.py'):
            source_files.append(py_file)
    
    # Root level Python files (excluding tests)
    for py_file in Path('.').glob('*.py'):
        if not py_file.name.startswith('test_'):
            source_files.append(py_file)
    
    # Functions directory
    functions_dir = Path('functions')
    if functions_dir.exists():
        for py_file in functions_dir.glob('*.py'):
            source_files.append(py_file)
    
    return source_files

def determine_test_status(file_path: str, test_files: Set[str]) -> Dict:
    """Determine if a source file has corresponding tests."""
    file_path_obj = Path(file_path)
    module_name = file_path_obj.stem
    
    # Look for direct test file matches
    possible_test_names = [
        f"tests/unit/test_{module_name}.py",
        f"tests/integration/test_{module_name}.py", 
        f"tests/gui/test_{module_name}.py",
        f"test_{module_name}.py"
    ]
    
    # Check for module-specific tests
    found_tests = []
    for test_file in test_files:
        test_path = Path(test_file)
        if any(possible_name in str(test_path) for possible_name in possible_test_names):
            found_tests.append(test_file)
    
    # Check for pattern matches (e.g., engine tests, feature tests)
    pattern_matches = []
    for test_file in test_files:
        if module_name in test_file or any(part in test_file for part in file_path_obj.parts):
            pattern_matches.append(test_file)
    
    return {
        'has_direct_tests': len(found_tests) > 0,
        'direct_test_files': found_tests,
        'pattern_matches': pattern_matches,
        'total_related_tests': len(set(found_tests + pattern_matches))
    }

def analyze_project_coverage():
    """Analyze the entire project for function coverage."""
    print("🔍 Analyzing Project Test Coverage")
    print("=" * 60)
    
    # Find all source and test files
    source_files = find_source_files()
    test_files = find_test_files()
    
    print(f"📁 Found {len(source_files)} source files")
    print(f"🧪 Found {len(test_files)} test files")
    print()
    
    # Analyze each source file
    analysis_results = []
    files_with_functions = []
    files_without_tests = []
    total_functions = 0
    
    for source_file in source_files:
        print(f"Analyzing: {source_file}")
        
        # Analyze file content
        file_analysis = analyze_python_file(source_file)
        
        if file_analysis.get('has_functions', False):
            files_with_functions.append(file_analysis)
            total_functions += file_analysis.get('total_functions', 0)
            
            # Check test status
            test_status = determine_test_status(str(source_file), test_files)
            file_analysis.update(test_status)
            
            if not test_status['has_direct_tests']:
                files_without_tests.append(file_analysis)
        
        analysis_results.append(file_analysis)
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 60)
    
    print(f"Total source files analyzed: {len(source_files)}")
    print(f"Files with functions: {len(files_with_functions)}")
    print(f"Total functions found: {total_functions}")
    print(f"Files missing direct tests: {len(files_without_tests)}")
    print(f"Test coverage: {((len(files_with_functions) - len(files_without_tests)) / len(files_with_functions) * 100):.1f}%")
    
    # Detailed breakdown by category
    categories = {
        'Core Modules': [],
        'Engines': [],
        'GUI Components': [],
        'Analytics': [],
        'Configuration': [],
        'Testing': [],
        'MCP Integration': [],
        'Utilities': [],
        'Other': []
    }
    
    for file_info in files_with_functions:
        file_path = file_info['file_path']
        
        if 'engines/' in file_path:
            categories['Engines'].append(file_info)
        elif 'gui/' in file_path:
            categories['GUI Components'].append(file_info)
        elif 'analytics/' in file_path:
            categories['Analytics'].append(file_info)
        elif 'config/' in file_path:
            categories['Configuration'].append(file_info)
        elif 'testing/' in file_path:
            categories['Testing'].append(file_info)
        elif 'mcp/' in file_path:
            categories['MCP Integration'].append(file_info)
        elif any(core in file_path for core in ['gbg/', 'io/', 'consensus/', 'features/', 'mapping/', 'normalize/']):
            categories['Core Modules'].append(file_info)
        elif 'functions/' in file_path:
            categories['Utilities'].append(file_info)
        else:
            categories['Other'].append(file_info)
    
    print("\n📋 BREAKDOWN BY CATEGORY")
    print("-" * 40)
    
    for category, files in categories.items():
        if files:
            tested_count = sum(1 for f in files if f.get('has_direct_tests', False))
            print(f"{category}: {len(files)} files, {tested_count} tested ({tested_count/len(files)*100:.1f}%)")
    
    # Files missing tests
    print("\n❌ FILES MISSING DIRECT TESTS")
    print("-" * 40)
    
    for file_info in files_without_tests:
        file_path = file_info['file_path']
        func_count = file_info.get('total_functions', 0)
        pattern_matches = len(file_info.get('pattern_matches', []))
        
        status = "🔴 No tests" if pattern_matches == 0 else f"🟡 {pattern_matches} related tests"
        print(f"{status} - {file_path} ({func_count} functions)")
    
    # Files with good test coverage
    print("\n✅ FILES WITH DIRECT TESTS")
    print("-" * 40)
    
    tested_files = [f for f in files_with_functions if f.get('has_direct_tests', False)]
    for file_info in tested_files:
        file_path = file_info['file_path']
        func_count = file_info.get('total_functions', 0)
        test_count = len(file_info.get('direct_test_files', []))
        
        print(f"✅ {file_path} ({func_count} functions, {test_count} test files)")
    
    # Save detailed results
    output_file = Path('output/project_test_coverage_analysis.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total_source_files': len(source_files),
                'files_with_functions': len(files_with_functions),
                'total_functions': total_functions,
                'files_missing_tests': len(files_without_tests),
                'test_coverage_percentage': ((len(files_with_functions) - len(files_without_tests)) / len(files_with_functions) * 100) if files_with_functions else 0
            },
            'categories': {cat: len(files) for cat, files in categories.items() if files},
            'files_with_functions': files_with_functions,
            'files_without_tests': files_without_tests,
            'all_test_files': list(test_files)
        }, indent=2)
    
    print(f"\n💾 Detailed analysis saved to: {output_file}")
    
    return {
        'files_with_functions': files_with_functions,
        'files_without_tests': files_without_tests,
        'categories': categories
    }

if __name__ == "__main__":
    results = analyze_project_coverage()
    
    print(f"\n🎯 RECOMMENDATIONS")
    print("-" * 40)
    print("1. Prioritize creating tests for core modules without coverage")
    print("2. Focus on files with high function counts first")
    print("3. Consider integration tests for complex workflows")
    print("4. Maintain 95%+ test coverage for new code")
#!/usr/bin/env python3
"""
Analyze Missing Files and Functions

This script identifies:
1. Python files that should have functions but aren't in file_index_readme.md
2. Functions that exist in code but aren't in function_catalog.ndjson
3. Generates a comprehensive report of missing coverage
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any
from datetime import datetime

class FunctionExtractor(ast.NodeVisitor):
    """Extract all functions and classes from Python files."""
    
    def __init__(self, module_path: str):
        self.module_path = module_path
        self.functions = []
        self.classes = []
        self.current_class = None
        
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        class_info = {
            'name': node.name,
            'line_number': node.lineno,
            'docstring': self._get_docstring(node),
            'methods': []
        }
        
        old_class = self.current_class
        self.current_class = node.name
        
        # Visit class methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = {
                    'name': item.name,
                    'line_number': item.lineno,
                    'docstring': self._get_docstring(item),
                    'parameters': [arg.arg for arg in item.args.args],
                    'is_private': item.name.startswith('_'),
                    'is_dunder': item.name.startswith('__') and item.name.endswith('__')
                }
                class_info['methods'].append(method_info)
        
        self.classes.append(class_info)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        if self.current_class is None:  # Only module-level functions
            func_info = {
                'name': node.name,
                'line_number': node.lineno,
                'docstring': self._get_docstring(node),
                'parameters': [arg.arg for arg in node.args.args],
                'is_private': node.name.startswith('_'),
                'is_main': node.name == 'main'
            }
            self.functions.append(func_info)
    
    def _get_docstring(self, node):
        """Extract docstring from a node."""
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value.strip()
        return ""

def analyze_python_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a Python file and extract all functions and classes."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        extractor = FunctionExtractor(str(file_path))
        extractor.visit(tree)
        
        # Handle relative path safely
        try:
            relative_path = str(file_path.relative_to(Path.cwd()))
        except ValueError:
            relative_path = str(file_path)
        
        return {
            'file_path': str(file_path),
            'module_name': file_path.stem,
            'relative_path': relative_path,
            'functions': extractor.functions,
            'classes': extractor.classes,
            'total_functions': len(extractor.functions),
            'total_classes': len(extractor.classes),
            'has_main': any(f['name'] == 'main' for f in extractor.functions),
            'error': None
        }
    except Exception as e:
        # Handle relative path safely
        try:
            relative_path = str(file_path.relative_to(Path.cwd()))
        except ValueError:
            relative_path = str(file_path)
            
        return {
            'file_path': str(file_path),
            'module_name': file_path.stem,
            'relative_path': relative_path,
            'functions': [],
            'classes': [],
            'total_functions': 0,
            'total_classes': 0,
            'has_main': False,
            'error': str(e)
        }

def find_all_python_files() -> List[Path]:
    """Find all Python files in the project, excluding test files and __pycache__."""
    python_files = []
    
    # Root level utility files
    root_files = Path('.').glob('*.py')
    for file in root_files:
        if not file.name.startswith('test_') and file.name not in ['conftest.py']:
            python_files.append(file)
    
    # Functions directory
    functions_dir = Path('functions')
    if functions_dir.exists():
        for file in functions_dir.glob('*.py'):
            if not file.name.startswith('test_'):
                python_files.append(file)
    
    # Source code files
    src_dir = Path('src')
    if src_dir.exists():
        for file in src_dir.rglob('*.py'):
            # Exclude __pycache__, test files, and __init__.py files
            if ('__pycache__' not in str(file) and 
                not file.name.startswith('test_') and
                file.name != '__init__.py'):
                python_files.append(file)
    
    return sorted(python_files)

def load_function_catalog() -> Dict[str, Dict]:
    """Load existing function catalog."""
    catalog_path = Path('functions/function_catalog.ndjson')
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

def get_files_in_index() -> Set[str]:
    """Get files mentioned in file_index_readme.md."""
    index_path = Path('file_index_readme.md')
    files_in_index = set()
    
    if not index_path.exists():
        return files_in_index
    
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract file paths from markdown
    path_patterns = [
        r'\*\*Path:\*\*\s*`([^`]+)`',
        r'`([^`]+\.py)`',
        r'### `([^`]+\.py)`'
    ]
    
    for pattern in path_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            # Normalize path
            normalized = match.replace('./', '').replace('\\', '/')
            files_in_index.add(normalized)
    
    return files_in_index

def should_be_in_index(file_info: Dict[str, Any]) -> bool:
    """Determine if a file should be in the file index."""
    # Files with main functions are usually utilities
    if file_info['has_main']:
        return True
    
    # Files with multiple functions are likely utilities
    if file_info['total_functions'] >= 3:
        return True
    
    # Root level files are usually utilities
    if not file_info['relative_path'].startswith('src/'):
        return True
    
    # Functions directory files
    if file_info['relative_path'].startswith('functions/'):
        return True
    
    return False

def generate_function_name(func_info: Dict, class_name: str = None, module_path: str = "") -> str:
    """Generate function name in catalog format."""
    if class_name:
        return f"{class_name}.{func_info['name']}"
    else:
        return func_info['name']

def analyze_project():
    """Analyze the entire project for missing files and functions."""
    print("🔍 Analyzing Project Files and Functions")
    print("=" * 60)
    
    # Find all Python files
    python_files = find_all_python_files()
    print(f"📁 Found {len(python_files)} Python files")
    
    # Load existing catalogs
    function_catalog = load_function_catalog()
    files_in_index = get_files_in_index()
    
    print(f"📚 Loaded {len(function_catalog)} functions from catalog")
    print(f"📋 Found {len(files_in_index)} files in index")
    
    # Analyze each file
    all_file_info = []
    missing_from_index = []
    missing_functions = []
    
    for file_path in python_files:
        file_info = analyze_python_file(file_path)
        all_file_info.append(file_info)
        
        if file_info['error']:
            print(f"❌ Error analyzing {file_path}: {file_info['error']}")
            continue
        
        # Check if should be in index
        if should_be_in_index(file_info):
            normalized_path = file_info['relative_path'].replace('\\', '/')
            if normalized_path not in files_in_index:
                missing_from_index.append(file_info)
        
        # Check for missing functions in catalog
        module_name = file_info['relative_path'].replace('/', '.').replace('\\', '.').replace('.py', '')
        if module_name.startswith('src.'):
            module_name = module_name[4:]  # Remove 'src.' prefix
        
        # Check module-level functions
        for func in file_info['functions']:
            if not func['is_private']:  # Skip private functions
                func_name = func['name']
                if func_name not in function_catalog:
                    missing_functions.append({
                        'function_name': func_name,
                        'module': module_name,
                        'file_path': file_info['relative_path'],
                        'class': None,
                        'line_number': func['line_number'],
                        'docstring': func['docstring'],
                        'parameters': func['parameters']
                    })
        
        # Check class methods
        for class_info in file_info['classes']:
            for method in class_info['methods']:
                if not method['is_private']:  # Skip private methods
                    func_name = f"{class_info['name']}.{method['name']}"
                    if func_name not in function_catalog:
                        missing_functions.append({
                            'function_name': func_name,
                            'module': module_name,
                            'file_path': file_info['relative_path'],
                            'class': class_info['name'],
                            'line_number': method['line_number'],
                            'docstring': method['docstring'],
                            'parameters': method['parameters']
                        })
    
    # Generate report
    print(f"\n📊 Analysis Results:")
    print(f"  Total Python files analyzed: {len(all_file_info)}")
    print(f"  Files missing from index: {len(missing_from_index)}")
    print(f"  Functions missing from catalog: {len(missing_functions)}")
    
    # Report missing files
    if missing_from_index:
        print(f"\n📋 Files Missing from file_index_readme.md:")
        print("-" * 50)
        for file_info in missing_from_index:
            print(f"  {file_info['relative_path']}")
            print(f"    Functions: {file_info['total_functions']}")
            print(f"    Classes: {file_info['total_classes']}")
            print(f"    Has main: {file_info['has_main']}")
            print()
    
    # Report missing functions
    if missing_functions:
        print(f"\n🔧 Functions Missing from function_catalog.ndjson:")
        print("-" * 50)
        by_module = {}
        for func in missing_functions:
            module = func['module']
            if module not in by_module:
                by_module[module] = []
            by_module[module].append(func)
        
        for module, funcs in sorted(by_module.items()):
            print(f"  Module: {module}")
            for func in funcs:
                print(f"    - {func['function_name']} (line {func['line_number']})")
            print()
    
    # Save detailed report
    report = {
        'analysis_date': datetime.now().isoformat(),
        'total_files_analyzed': len(all_file_info),
        'files_missing_from_index': len(missing_from_index),
        'functions_missing_from_catalog': len(missing_functions),
        'missing_files': [
            {
                'path': f['relative_path'],
                'functions': f['total_functions'],
                'classes': f['total_classes'],
                'has_main': f['has_main']
            }
            for f in missing_from_index
        ],
        'missing_functions': missing_functions,
        'all_files': all_file_info
    }
    
    report_path = Path('output/missing_files_and_functions_report.json')
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    
    return report

if __name__ == "__main__":
    analyze_project()
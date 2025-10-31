#!/usr/bin/env python3
"""
Automated Missing Function Detection and Catalog Update Tool

This tool automatically discovers functions in the codebase and identifies
which ones are missing from the function catalog. It can append missing
functions to the catalog without requiring AI processing.
"""

import json
import ast
import inspect
import importlib
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional
import pkgutil


class FunctionDiscovery:
    """Automated function discovery system."""
    
    def __init__(self, src_root: str = "src"):
        """Initialize function discovery."""
        self.src_root = Path(src_root)
        self.discovered_functions = []
        self.catalog_functions = set()
        
        # Add src to Python path for imports
        if str(self.src_root) not in sys.path:
            sys.path.insert(0, str(self.src_root))
    
    def load_existing_catalog(self, catalog_path: Path) -> Set[str]:
        """Load existing function catalog and return set of function names."""
        catalog_functions = set()
        
        if catalog_path.exists():
            try:
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            catalog_functions.add(entry["function_name"])
            except Exception as e:
                print(f"Warning: Error reading catalog: {e}")
        
        return catalog_functions
    
    def discover_functions_from_ast(self, file_path: Path) -> List[Dict[str, Any]]:
        """Discover functions from a Python file using AST parsing."""
        functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Get module path relative to src
            try:
                module_path = str(file_path.relative_to(self.src_root)).replace('/', '.').replace('\\', '.').replace('.py', '')
            except ValueError:
                # File not under src directory
                module_path = str(file_path).replace('/', '.').replace('\\', '.').replace('.py', '')
            
            # Find all function and method definitions
            # Use direct iteration instead of ast.walk to avoid duplicates
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    # Module-level function
                    func_info = self._extract_function_info(node, module_path, file_path)
                    if func_info:
                        functions.append(func_info)
                
                elif isinstance(node, ast.ClassDef):
                    # Class methods
                    class_name = node.name
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            func_info = self._extract_function_info(
                                item, module_path, file_path, class_name
                            )
                            if func_info:
                                functions.append(func_info)
        
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
        
        return functions
    
    def _extract_function_info(self, node: ast.FunctionDef, module_path: str, 
                              file_path: Path, class_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Extract function information from AST node."""
        func_name = node.name
        
        # Skip private functions (but include __init__, __post_init__, etc.)
        if func_name.startswith('_') and not func_name.startswith('__'):
            return None
        
        # Build full function name
        if class_name:
            full_name = f"{class_name}.{func_name}"
        else:
            full_name = func_name
        
        # Extract parameters
        parameters = []
        for arg in node.args.args:
            parameters.append(arg.arg)
        
        # Extract return type annotation
        return_type = "Any"
        if node.returns:
            try:
                return_type = ast.unparse(node.returns)
            except:
                return_type = "Any"
        
        # Extract docstring
        description = "Function description"
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            description = node.body[0].value.value.strip().split('\n')[0]
        
        # Determine test file
        test_file = self._determine_test_file(file_path, module_path)
        
        return {
            "function_name": full_name,
            "module": module_path,
            "class": class_name,
            "description": description,
            "parameters": parameters,
            "return_type": return_type,
            "test_file": test_file,
            "test_description": f"Tests {full_name} functionality",
            "field_attributes": {},
            "side_effects": [],
            "dependencies": [],
            "source_file": str(file_path),
            "line_number": node.lineno
        }
    
    def _determine_test_file(self, source_file: Path, module_path: str) -> str:
        """Determine the appropriate test file for a source file."""
        # Convert module path to test file path
        parts = module_path.split('.')
        
        # Remove 'src' and 'compareblocks' if present
        if parts and parts[0] == 'src':
            parts = parts[1:]
        if parts and parts[0] == 'compareblocks':
            parts = parts[1:]
        
        # Build test file path
        if len(parts) == 1:
            # Top-level module
            test_file = f"tests/unit/test_{parts[0]}.py"
        else:
            # Nested module
            test_file = f"tests/unit/test_{parts[-1]}.py"
        
        return test_file
    
    def discover_all_functions(self) -> List[Dict[str, Any]]:
        """Discover all functions in the source directory."""
        all_functions = []
        
        # Walk through all Python files in src directory
        for py_file in self.src_root.rglob("*.py"):
            # Skip __pycache__ and other non-source files
            if "__pycache__" in str(py_file) or py_file.name.startswith('.'):
                continue
            
            functions = self.discover_functions_from_ast(py_file)
            all_functions.extend(functions)
        
        return all_functions
    
    def find_missing_functions(self, catalog_path: Path) -> List[Dict[str, Any]]:
        """Find functions that exist in code but are missing from catalog."""
        # Load existing catalog
        self.catalog_functions = self.load_existing_catalog(catalog_path)
        
        # Discover all functions
        all_functions = self.discover_all_functions()
        
        # Find missing functions
        missing_functions = []
        for func in all_functions:
            if func["function_name"] not in self.catalog_functions:
                missing_functions.append(func)
        
        return missing_functions
    
    def append_missing_functions(self, catalog_path: Path, missing_functions: List[Dict[str, Any]]) -> int:
        """Append missing functions to the catalog."""
        if not missing_functions:
            return 0
        
        # Ensure catalog directory exists
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Append missing functions to catalog
        with open(catalog_path, 'a', encoding='utf-8') as f:
            for func in missing_functions:
                f.write(json.dumps(func, separators=(',', ':')) + '\n')
        
        return len(missing_functions)
    
    def generate_missing_functions_report(self, missing_functions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a report of missing functions."""
        report = {
            "timestamp": self._get_timestamp(),
            "total_missing": len(missing_functions),
            "by_module": {},
            "by_class": {},
            "by_test_file": {},
            "functions": missing_functions
        }
        
        # Group by module
        for func in missing_functions:
            module = func["module"]
            if module not in report["by_module"]:
                report["by_module"][module] = 0
            report["by_module"][module] += 1
        
        # Group by class
        for func in missing_functions:
            class_name = func["class"] or "module_level"
            if class_name not in report["by_class"]:
                report["by_class"][class_name] = 0
            report["by_class"][class_name] += 1
        
        # Group by test file
        for func in missing_functions:
            test_file = func["test_file"]
            if test_file not in report["by_test_file"]:
                report["by_test_file"][test_file] = 0
            report["by_test_file"][test_file] += 1
        
        return report
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """Main function to detect and optionally append missing functions."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Detect missing functions in catalog")
    parser.add_argument("--catalog", default="functions/function_catalog.ndjson",
                       help="Path to function catalog file")
    parser.add_argument("--src", default="src", help="Source directory to scan")
    parser.add_argument("--append", action="store_true", 
                       help="Append missing functions to catalog")
    parser.add_argument("--report", help="Save missing functions report to file")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Initialize discovery
    discovery = FunctionDiscovery(args.src)
    catalog_path = Path(args.catalog)
    
    print(f"Scanning for functions in: {args.src}")
    print(f"Checking against catalog: {catalog_path}")
    
    # Find missing functions
    missing_functions = discovery.find_missing_functions(catalog_path)
    
    print(f"\nFound {len(missing_functions)} missing functions")
    
    if args.verbose and missing_functions:
        print("\nMissing functions:")
        for func in missing_functions[:10]:  # Show first 10
            print(f"  - {func['function_name']} ({func['module']})")
        if len(missing_functions) > 10:
            print(f"  ... and {len(missing_functions) - 10} more")
    
    # Generate report
    if missing_functions:
        report = discovery.generate_missing_functions_report(missing_functions)
        
        print(f"\nBreakdown:")
        print(f"  Modules: {len(report['by_module'])}")
        print(f"  Classes: {len(report['by_class'])}")
        print(f"  Test files needed: {len(report['by_test_file'])}")
        
        # Save report if requested
        if args.report:
            report_path = Path(args.report)
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\nReport saved to: {report_path}")
    
    # Append to catalog if requested
    if args.append and missing_functions:
        appended = discovery.append_missing_functions(catalog_path, missing_functions)
        print(f"\n✅ Appended {appended} missing functions to catalog")
    elif missing_functions:
        print(f"\n💡 Use --append to add these functions to the catalog")
    else:
        print(f"\n✅ No missing functions found - catalog is up to date")
    
    return 0 if not missing_functions else 1


if __name__ == "__main__":
    exit(main())
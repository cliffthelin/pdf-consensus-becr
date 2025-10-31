# src/compareblocks/testing/engine_validator.py
"""
Engine Testing and Validation System

Comprehensive system for validating all OCR engines with real PDF files.
Tracks test coverage, performance metrics, and identifies missing tests.
"""

import json
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..engines import (
    PyMuPDFEngine, TesseractEngine, PaddleOCREngine, 
    KreuzbergEngine, DoclingEngine, ExtractionEngineManager
)
from ..config.file_manager import file_manager


@dataclass
class FunctionTestStatus:
    """Test status for a single function."""
    function_name: str
    module_name: str
    engine_name: str
    has_test: bool
    test_file_path: Optional[str] = None
    test_function_name: Optional[str] = None
    parameters_tested: List[Dict[str, Any]] = None
    file_types_tested: List[str] = None
    last_test_run: Optional[str] = None
    test_success: Optional[bool] = None
    performance_metrics: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        if self.parameters_tested is None:
            self.parameters_tested = []
        if self.file_types_tested is None:
            self.file_types_tested = []


@dataclass
class EngineTestCoverage:
    """Test coverage summary for an engine."""
    engine_name: str
    total_functions: int
    tested_functions: int
    untested_functions: List[str]
    coverage_percentage: float
    test_files: List[str]
    function_tests: List[FunctionTestStatus]


class EngineValidator:
    """Validates engine functions and tracks test coverage."""
    
    def __init__(self):
        """Initialize engine validator."""
        self.engine_classes = {
            'pymupdf': PyMuPDFEngine,
            'tesseract': TesseractEngine,
            'paddleocr': PaddleOCREngine,
            'kreuzberg': KreuzbergEngine,
            'docling': DoclingEngine
        }
        
        self.test_directory = Path("tests")
        self.results_directory = Path("output/engine_validation")
        self.results_directory.mkdir(parents=True, exist_ok=True)
    
    def discover_engine_functions(self, engine_name: str) -> List[Tuple[str, str]]:
        """
        Discover all functions in an engine.
        
        Args:
            engine_name: Name of the engine
            
        Returns:
            List of (function_name, module_name) tuples
        """
        if engine_name not in self.engine_classes:
            return []
        
        engine_class = self.engine_classes[engine_name]
        functions = []
        
        # Get class methods
        for name, method in inspect.getmembers(engine_class, predicate=inspect.ismethod):
            if not name.startswith('_'):  # Skip private methods
                functions.append((name, engine_class.__module__))
        
        # Get instance methods
        try:
            instance = engine_class()
            for name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
                if not name.startswith('_') and hasattr(engine_class, name):
                    functions.append((name, engine_class.__module__))
        except Exception:
            pass  # Skip if engine can't be instantiated
        
        # Get module-level functions
        try:
            import importlib
            module = importlib.import_module(engine_class.__module__)
            for name, func in inspect.getmembers(module, predicate=inspect.isfunction):
                if not name.startswith('_') and engine_name in name.lower():
                    functions.append((name, engine_class.__module__))
        except Exception:
            pass
        
        # Remove duplicates
        return list(set(functions))
    
    def find_test_files(self) -> List[Path]:
        """Find all test files in the test directory."""
        test_files = []
        
        if self.test_directory.exists():
            # Find all test_*.py files
            test_files.extend(self.test_directory.rglob("test_*.py"))
            test_files.extend(self.test_directory.rglob("*_test.py"))
        
        return test_files
    
    def analyze_test_file(self, test_file: Path) -> Dict[str, List[str]]:
        """
        Analyze a test file to find tested functions.
        
        Args:
            test_file: Path to test file
            
        Returns:
            Dictionary mapping engine names to tested functions
        """
        tested_functions = {engine: [] for engine in self.engine_classes.keys()}
        
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for function calls and imports
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Check for engine function calls
                for engine_name in self.engine_classes.keys():
                    engine_class = self.engine_classes[engine_name]
                    
                    # Look for class instantiation
                    if f"{engine_class.__name__}(" in line:
                        tested_functions[engine_name].append("__init__")
                    
                    # Look for method calls
                    if f".{engine_name}" in line.lower() or engine_name in line.lower():
                        # Extract potential function names
                        import re
                        func_pattern = r'\.(\w+)\('
                        matches = re.findall(func_pattern, line)
                        for match in matches:
                            if not match.startswith('_'):
                                tested_functions[engine_name].append(match)
                    
                    # Look for direct function calls
                    functions = self.discover_engine_functions(engine_name)
                    for func_name, _ in functions:
                        if func_name in line and '(' in line:
                            tested_functions[engine_name].append(func_name)
        
        except Exception as e:
            print(f"Error analyzing test file {test_file}: {e}")
        
        # Remove duplicates
        for engine in tested_functions:
            tested_functions[engine] = list(set(tested_functions[engine]))
        
        return tested_functions
    
    def validate_engine_coverage(self, engine_name: str) -> EngineTestCoverage:
        """
        Validate test coverage for a specific engine.
        
        Args:
            engine_name: Name of the engine to validate
            
        Returns:
            Engine test coverage summary
        """
        print(f"Validating test coverage for {engine_name} engine...")
        
        # Discover all functions
        functions = self.discover_engine_functions(engine_name)
        total_functions = len(functions)
        
        # Find test files
        test_files = self.find_test_files()
        
        # Analyze test coverage
        tested_functions = set()
        test_file_paths = []
        function_tests = []
        
        for test_file in test_files:
            tested_in_file = self.analyze_test_file(test_file)
            
            if tested_in_file[engine_name]:
                test_file_paths.append(str(test_file))
                tested_functions.update(tested_in_file[engine_name])
        
        # Create function test status
        for func_name, module_name in functions:
            has_test = func_name in tested_functions
            
            # Find specific test file and function
            test_file_path = None
            test_function_name = None
            
            if has_test:
                for test_file in test_files:
                    tested_in_file = self.analyze_test_file(test_file)
                    if func_name in tested_in_file[engine_name]:
                        test_file_path = str(test_file)
                        # Try to find the specific test function
                        test_function_name = f"test_{func_name}"
                        break
            
            function_test = FunctionTestStatus(
                function_name=func_name,
                module_name=module_name,
                engine_name=engine_name,
                has_test=has_test,
                test_file_path=test_file_path,
                test_function_name=test_function_name
            )
            
            function_tests.append(function_test)
        
        # Calculate coverage
        tested_count = len(tested_functions)
        coverage_percentage = (tested_count / total_functions * 100) if total_functions > 0 else 0
        
        # Find untested functions
        all_function_names = {func_name for func_name, _ in functions}
        untested_functions = list(all_function_names - tested_functions)
        
        return EngineTestCoverage(
            engine_name=engine_name,
            total_functions=total_functions,
            tested_functions=tested_count,
            untested_functions=untested_functions,
            coverage_percentage=coverage_percentage,
            test_files=test_file_paths,
            function_tests=function_tests
        )
    
    def validate_all_engines(self) -> Dict[str, EngineTestCoverage]:
        """
        Validate test coverage for all engines.
        
        Returns:
            Dictionary mapping engine names to coverage summaries
        """
        print("Validating test coverage for all engines...")
        
        coverage_results = {}
        
        for engine_name in self.engine_classes.keys():
            try:
                coverage = self.validate_engine_coverage(engine_name)
                coverage_results[engine_name] = coverage
                
                print(f"✅ {engine_name}: {coverage.coverage_percentage:.1f}% coverage "
                      f"({coverage.tested_functions}/{coverage.total_functions} functions)")
                
            except Exception as e:
                print(f"❌ {engine_name}: Validation failed - {e}")
                
                # Create empty coverage result
                coverage_results[engine_name] = EngineTestCoverage(
                    engine_name=engine_name,
                    total_functions=0,
                    tested_functions=0,
                    untested_functions=[],
                    coverage_percentage=0.0,
                    test_files=[],
                    function_tests=[]
                )
        
        return coverage_results
    
    def run_engine_function_tests(self, engine_name: str, 
                                 pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run actual tests for engine functions with real PDF.
        
        Args:
            engine_name: Name of the engine
            pdf_path: Path to PDF file for testing
            
        Returns:
            Test execution results
        """
        if pdf_path is None:
            pdf_path = file_manager.get_target_pdf_path()
        
        print(f"Running function tests for {engine_name} with {pdf_path}")
        
        if engine_name not in self.engine_classes:
            return {"error": f"Unknown engine: {engine_name}"}
        
        engine_class = self.engine_classes[engine_name]
        test_results = {
            "engine_name": engine_name,
            "pdf_path": pdf_path,
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "function_results": {},
            "summary": {}
        }
        
        try:
            # Test engine availability
            if hasattr(engine_class, 'is_available'):
                engine_instance = engine_class()
                is_available = engine_instance.is_available()
                test_results["engine_available"] = is_available
                
                if not is_available:
                    test_results["summary"] = {
                        "total_tests": 0,
                        "passed_tests": 0,
                        "failed_tests": 0,
                        "error": f"{engine_name} engine not available"
                    }
                    return test_results
            else:
                test_results["engine_available"] = True
            
            # Test basic functions
            functions_to_test = [
                ("extract_pdf", {}),
                ("save_extraction", {}),
            ]
            
            passed_tests = 0
            failed_tests = 0
            
            for func_name, params in functions_to_test:
                try:
                    start_time = time.time()
                    
                    if hasattr(engine_class, func_name):
                        # Test instance method
                        engine_instance = engine_class()
                        func = getattr(engine_instance, func_name)
                        
                        if func_name == "extract_pdf":
                            result = func(pdf_path)
                        elif func_name == "save_extraction":
                            result = func(pdf_path)
                        else:
                            result = func(**params)
                        
                        execution_time = time.time() - start_time
                        
                        # Validate result
                        success = self._validate_function_result(func_name, result)
                        
                        test_results["function_results"][func_name] = {
                            "success": success,
                            "execution_time": execution_time,
                            "result_type": type(result).__name__,
                            "result_size": len(str(result)) if result else 0,
                            "parameters": params
                        }
                        
                        if success:
                            passed_tests += 1
                        else:
                            failed_tests += 1
                    
                    else:
                        test_results["function_results"][func_name] = {
                            "success": False,
                            "error": f"Function {func_name} not found in {engine_name}",
                            "parameters": params
                        }
                        failed_tests += 1
                
                except Exception as e:
                    execution_time = time.time() - start_time
                    test_results["function_results"][func_name] = {
                        "success": False,
                        "error": str(e),
                        "execution_time": execution_time,
                        "parameters": params
                    }
                    failed_tests += 1
            
            test_results["summary"] = {
                "total_tests": len(functions_to_test),
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests / len(functions_to_test) * 100) if functions_to_test else 0
            }
            
        except Exception as e:
            test_results["summary"] = {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 1,
                "error": f"Engine testing failed: {e}"
            }
        
        return test_results
    
    def _validate_function_result(self, func_name: str, result: Any) -> bool:
        """Validate function result based on expected output."""
        if result is None:
            return False
        
        if func_name == "extract_pdf":
            # Should return dictionary with required fields
            if isinstance(result, dict):
                required_fields = ["engine", "pdf_name", "summary"]
                return all(field in result for field in required_fields)
            return False
        
        elif func_name == "save_extraction":
            # Should return file path string
            if isinstance(result, str) and result:
                return Path(result).exists() if result else False
            return False
        
        return True
    
    def generate_coverage_report(self, coverage_results: Dict[str, EngineTestCoverage]) -> str:
        """
        Generate comprehensive coverage report.
        
        Args:
            coverage_results: Coverage results for all engines
            
        Returns:
            Path to generated report
        """
        report_data = {
            "report_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_engines": len(coverage_results),
            "engine_coverage": {},
            "overall_summary": {},
            "recommendations": []
        }
        
        # Process each engine
        total_functions = 0
        total_tested = 0
        
        for engine_name, coverage in coverage_results.items():
            report_data["engine_coverage"][engine_name] = asdict(coverage)
            total_functions += coverage.total_functions
            total_tested += coverage.tested_functions
        
        # Calculate overall summary
        overall_coverage = (total_tested / total_functions * 100) if total_functions > 0 else 0
        
        report_data["overall_summary"] = {
            "total_functions": total_functions,
            "total_tested": total_tested,
            "overall_coverage_percentage": overall_coverage,
            "engines_with_full_coverage": len([c for c in coverage_results.values() if c.coverage_percentage == 100]),
            "engines_needing_tests": len([c for c in coverage_results.values() if c.coverage_percentage < 100])
        }
        
        # Generate recommendations
        recommendations = []
        
        for engine_name, coverage in coverage_results.items():
            if coverage.coverage_percentage < 100:
                recommendations.append({
                    "engine": engine_name,
                    "priority": "high" if coverage.coverage_percentage < 50 else "medium",
                    "action": f"Add tests for {len(coverage.untested_functions)} untested functions",
                    "untested_functions": coverage.untested_functions[:5]  # Show first 5
                })
        
        report_data["recommendations"] = recommendations
        
        # Save report
        report_path = self.results_directory / "engine_test_coverage_report.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"Coverage report saved to: {report_path}")
        return str(report_path)
    
    def run_comprehensive_validation(self, pdf_path: Optional[str] = None) -> str:
        """
        Run comprehensive validation of all engines.
        
        Args:
            pdf_path: Path to PDF file for testing
            
        Returns:
            Path to comprehensive validation report
        """
        print("Running comprehensive engine validation...")
        
        # Validate test coverage
        coverage_results = self.validate_all_engines()
        
        # Run function tests for each engine
        function_test_results = {}
        
        for engine_name in self.engine_classes.keys():
            print(f"Testing {engine_name} functions...")
            function_test_results[engine_name] = self.run_engine_function_tests(engine_name, pdf_path)
        
        # Generate comprehensive report
        comprehensive_report = {
            "validation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pdf_path": pdf_path or file_manager.get_target_pdf_path(),
            "test_coverage": {engine: asdict(coverage) for engine, coverage in coverage_results.items()},
            "function_tests": function_test_results,
            "validation_summary": self._generate_validation_summary(coverage_results, function_test_results)
        }
        
        # Save comprehensive report
        report_path = self.results_directory / "comprehensive_engine_validation.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(comprehensive_report, f, indent=2, ensure_ascii=False)
        
        print(f"Comprehensive validation report saved to: {report_path}")
        
        # Also generate coverage report
        coverage_report_path = self.generate_coverage_report(coverage_results)
        
        return str(report_path)
    
    def _generate_validation_summary(self, coverage_results: Dict[str, EngineTestCoverage],
                                   function_test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation summary."""
        summary = {
            "engines_validated": len(coverage_results),
            "engines_available": 0,
            "engines_with_tests": 0,
            "engines_passing_tests": 0,
            "total_functions_discovered": 0,
            "total_functions_tested": 0,
            "overall_test_coverage": 0.0,
            "overall_function_success_rate": 0.0,
            "critical_issues": [],
            "recommendations": []
        }
        
        total_functions = 0
        total_tested = 0
        total_function_tests = 0
        total_function_passes = 0
        
        for engine_name in coverage_results.keys():
            coverage = coverage_results[engine_name]
            function_tests = function_test_results.get(engine_name, {})
            
            # Count totals
            total_functions += coverage.total_functions
            total_tested += coverage.tested_functions
            
            # Check availability
            if function_tests.get("engine_available", False):
                summary["engines_available"] += 1
            
            # Check test coverage
            if coverage.tested_functions > 0:
                summary["engines_with_tests"] += 1
            
            # Check function test results
            func_summary = function_tests.get("summary", {})
            if func_summary.get("passed_tests", 0) > 0:
                summary["engines_passing_tests"] += 1
            
            total_function_tests += func_summary.get("total_tests", 0)
            total_function_passes += func_summary.get("passed_tests", 0)
            
            # Identify critical issues
            if not function_tests.get("engine_available", True):
                summary["critical_issues"].append(f"{engine_name} engine not available")
            
            if coverage.coverage_percentage == 0:
                summary["critical_issues"].append(f"{engine_name} has no test coverage")
            
            if func_summary.get("failed_tests", 0) > 0:
                summary["critical_issues"].append(f"{engine_name} has failing function tests")
        
        # Calculate overall metrics
        summary["total_functions_discovered"] = total_functions
        summary["total_functions_tested"] = total_tested
        summary["overall_test_coverage"] = (total_tested / total_functions * 100) if total_functions > 0 else 0
        summary["overall_function_success_rate"] = (total_function_passes / total_function_tests * 100) if total_function_tests > 0 else 0
        
        # Generate recommendations
        if summary["overall_test_coverage"] < 80:
            summary["recommendations"].append("Increase overall test coverage to at least 80%")
        
        if summary["engines_available"] < len(coverage_results):
            summary["recommendations"].append("Install missing engine dependencies")
        
        if summary["overall_function_success_rate"] < 90:
            summary["recommendations"].append("Fix failing function tests to achieve 90%+ success rate")
        
        return summary


# Convenience functions
def validate_engine_coverage(engine_name: str) -> EngineTestCoverage:
    """Validate test coverage for a specific engine."""
    validator = EngineValidator()
    return validator.validate_engine_coverage(engine_name)


def validate_all_engines() -> Dict[str, EngineTestCoverage]:
    """Validate test coverage for all engines."""
    validator = EngineValidator()
    return validator.validate_all_engines()


def run_comprehensive_engine_validation(pdf_path: Optional[str] = None) -> str:
    """Run comprehensive validation of all engines."""
    validator = EngineValidator()
    return validator.run_comprehensive_validation(pdf_path)
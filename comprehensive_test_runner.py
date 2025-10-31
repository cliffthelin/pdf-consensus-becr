#!/usr/bin/env python3
"""
Comprehensive Test Runner - Discover and test all test files systematically
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

class ComprehensiveTestRunner:
    def __init__(self):
        self.results = {}
        self.syntax_errors = []
        self.untested_files = []
        
    def discover_all_test_files(self) -> List[Path]:
        """Discover all test files in the project."""
        test_files = []
        
        # Discover from all test directories
        patterns = [
            "tests/unit/test_*.py",
            "tests/integration/test_*.py", 
            "tests/gui/test_*.py",
            "tests/adhoc/test_*.py",
            "tests/fixtures/test_*.py"
        ]
        
        for pattern in patterns:
            test_files.extend(Path(".").glob(pattern))
        
        # Sort by category and name for organized execution
        test_files.sort(key=lambda x: (x.parent.name, x.name))
        
        return test_files
    
    def check_syntax_validity(self, test_file: Path) -> Tuple[bool, str]:
        """Check if a test file has valid Python syntax."""
        try:
            import ast
            content = test_file.read_text(encoding='utf-8', errors='ignore')
            ast.parse(content)
            return True, ""
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def run_single_test_file(self, test_file: Path, timeout: int = 60) -> Dict:
        """Run a single test file and return results."""
        start_time = time.time()
        
        # Check syntax first
        syntax_valid, syntax_error = self.check_syntax_validity(test_file)
        if not syntax_valid:
            return {
                "file": str(test_file),
                "status": "syntax_error",
                "duration": 0,
                "error": syntax_error,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0
            }
        
        try:
            # Run pytest on the file
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(test_file),
                "--tb=short",
                "-v",
                "--no-cov"
            ], capture_output=True, text=True, timeout=timeout)
            
            duration = time.time() - start_time
            
            # Parse pytest output for test counts
            output = result.stdout + result.stderr
            tests_run = output.count("PASSED") + output.count("FAILED") + output.count("ERROR")
            tests_passed = output.count("PASSED")
            tests_failed = output.count("FAILED") + output.count("ERROR")
            
            if result.returncode == 0:
                status = "passed"
            else:
                status = "failed"
            
            return {
                "file": str(test_file),
                "status": status,
                "duration": duration,
                "error": result.stderr if result.returncode != 0 else "",
                "tests_run": tests_run,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "output": output
            }
            
        except subprocess.TimeoutExpired:
            duration = timeout
            return {
                "file": str(test_file),
                "status": "timeout",
                "duration": duration,
                "error": f"Test timed out after {timeout}s",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "file": str(test_file),
                "status": "error",
                "duration": duration,
                "error": str(e),
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0
            }
    
    def run_tests_by_category(self, max_workers: int = 3) -> Dict:
        """Run all tests organized by category."""
        test_files = self.discover_all_test_files()
        
        print(f"🔍 Discovered {len(test_files)} test files")
        print("=" * 60)
        
        # Group by category
        categories = {}
        for test_file in test_files:
            category = test_file.parent.name
            if category not in categories:
                categories[category] = []
            categories[category].append(test_file)
        
        all_results = {}
        
        # Process each category
        for category, files in categories.items():
            print(f"\n📂 Testing {category} ({len(files)} files)")
            print("-" * 40)
            
            category_results = []
            
            # Use ThreadPoolExecutor for parallel execution within category
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all files in this category
                future_to_file = {
                    executor.submit(self.run_single_test_file, test_file): test_file 
                    for test_file in files
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_file):
                    test_file = future_to_file[future]
                    try:
                        result = future.result()
                        category_results.append(result)
                        
                        # Print immediate feedback
                        status_icon = {
                            "passed": "✅",
                            "failed": "❌", 
                            "timeout": "⏰",
                            "error": "💥",
                            "syntax_error": "🔧"
                        }.get(result["status"], "❓")
                        
                        duration_str = f"({result['duration']:.1f}s)"
                        test_info = ""
                        if result["tests_run"] > 0:
                            test_info = f" [{result['tests_passed']}/{result['tests_run']} passed]"
                        
                        print(f"{status_icon} {test_file.name} {duration_str}{test_info}")
                        
                        if result["status"] in ["failed", "error", "syntax_error"] and result["error"]:
                            # Show first line of error
                            error_line = result["error"].split('\n')[0][:100]
                            print(f"   Error: {error_line}")
                        
                    except Exception as e:
                        print(f"💥 {test_file.name} - Execution error: {e}")
            
            all_results[category] = category_results
        
        return all_results
    
    def generate_comprehensive_report(self, results: Dict) -> Dict:
        """Generate comprehensive test report."""
        total_files = 0
        total_tests_run = 0
        total_tests_passed = 0
        total_tests_failed = 0
        
        status_counts = {
            "passed": 0,
            "failed": 0,
            "timeout": 0,
            "error": 0,
            "syntax_error": 0
        }
        
        category_summaries = {}
        
        # Aggregate results
        for category, category_results in results.items():
            category_summary = {
                "files": len(category_results),
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "status_counts": {status: 0 for status in status_counts.keys()},
                "avg_duration": 0,
                "total_duration": 0
            }
            
            for result in category_results:
                total_files += 1
                total_tests_run += result["tests_run"]
                total_tests_passed += result["tests_passed"]
                total_tests_failed += result["tests_failed"]
                
                status_counts[result["status"]] += 1
                category_summary["status_counts"][result["status"]] += 1
                category_summary["tests_run"] += result["tests_run"]
                category_summary["tests_passed"] += result["tests_passed"]
                category_summary["tests_failed"] += result["tests_failed"]
                category_summary["total_duration"] += result["duration"]
            
            if category_results:
                category_summary["avg_duration"] = category_summary["total_duration"] / len(category_results)
            
            category_summaries[category] = category_summary
        
        # Calculate success rates
        file_success_rate = (status_counts["passed"] / total_files * 100) if total_files > 0 else 0
        test_success_rate = (total_tests_passed / total_tests_run * 100) if total_tests_run > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_files": total_files,
                "total_tests_run": total_tests_run,
                "total_tests_passed": total_tests_passed,
                "total_tests_failed": total_tests_failed,
                "file_success_rate": file_success_rate,
                "test_success_rate": test_success_rate,
                "status_counts": status_counts
            },
            "category_summaries": category_summaries,
            "detailed_results": results
        }
    
    def print_final_summary(self, report: Dict):
        """Print comprehensive final summary."""
        summary = report["summary"]
        
        print(f"\n{'='*60}")
        print("🎯 COMPREHENSIVE TEST EXECUTION SUMMARY")
        print(f"{'='*60}")
        
        print(f"📊 OVERALL RESULTS:")
        print(f"  Total Files: {summary['total_files']}")
        print(f"  Total Tests: {summary['total_tests_run']}")
        print(f"  File Success Rate: {summary['file_success_rate']:.1f}%")
        print(f"  Test Success Rate: {summary['test_success_rate']:.1f}%")
        
        print(f"\n📈 STATUS BREAKDOWN:")
        for status, count in summary["status_counts"].items():
            percentage = (count / summary["total_files"] * 100) if summary["total_files"] > 0 else 0
            icon = {"passed": "✅", "failed": "❌", "timeout": "⏰", "error": "💥", "syntax_error": "🔧"}[status]
            print(f"  {icon} {status.title()}: {count} ({percentage:.1f}%)")
        
        print(f"\n📂 BY CATEGORY:")
        for category, cat_summary in report["category_summaries"].items():
            cat_success = (cat_summary["status_counts"]["passed"] / cat_summary["files"] * 100) if cat_summary["files"] > 0 else 0
            print(f"  {category}: {cat_success:.1f}% ({cat_summary['status_counts']['passed']}/{cat_summary['files']} files)")
        
        # Show top issues
        print(f"\n🔧 TOP ISSUES TO FIX:")
        syntax_files = []
        failed_files = []
        
        for category_results in report["detailed_results"].values():
            for result in category_results:
                if result["status"] == "syntax_error":
                    syntax_files.append(result["file"])
                elif result["status"] == "failed":
                    failed_files.append(result["file"])
        
        if syntax_files:
            print(f"  Syntax Errors ({len(syntax_files)} files):")
            for file in syntax_files[:5]:  # Show top 5
                print(f"    - {Path(file).name}")
            if len(syntax_files) > 5:
                print(f"    ... and {len(syntax_files) - 5} more")
        
        if failed_files:
            print(f"  Failed Tests ({len(failed_files)} files):")
            for file in failed_files[:5]:  # Show top 5
                print(f"    - {Path(file).name}")
            if len(failed_files) > 5:
                print(f"    ... and {len(failed_files) - 5} more")

def main():
    print("🚀 Comprehensive Test Discovery and Execution")
    print("=" * 60)
    
    runner = ComprehensiveTestRunner()
    
    # Run all tests by category
    results = runner.run_tests_by_category(max_workers=2)  # Reduced workers to avoid overwhelming
    
    # Generate comprehensive report
    report = runner.generate_comprehensive_report(results)
    
    # Save detailed results
    output_file = Path("output/comprehensive_test_results.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)
    
    # Print final summary
    runner.print_final_summary(report)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    
    return 0

if __name__ == "__main__":
    exit(main())
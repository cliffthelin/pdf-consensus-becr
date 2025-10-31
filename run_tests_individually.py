#!/usr/bin/env python3
"""
Individual test runner with graceful recovery and timeout handling.
Runs each test file separately to identify problematic tests and provide better feedback.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

class IndividualTestRunner:
    def __init__(self, timeout_seconds: int = 300):  # 5 minute default timeout
        self.timeout_seconds = timeout_seconds
        self.results = []
        self.failed_tests = []
        self.slow_tests = []
        self.skipped_tests = []
        self.output_file = Path("output/individual_test_results.json")
        self.last_save_time = time.time()
        self.save_interval = 600  # Save every 10 minutes (600 seconds)
        
    def discover_test_files(self) -> List[Path]:
        """Discover all test files in the project."""
        test_files = []
        
        # Find all test files
        for pattern in ["tests/unit/test_*.py", "tests/integration/test_*.py", "tests/gui/test_*.py", "tests/adhoc/test_*.py"]:
            test_files.extend(Path(".").glob(pattern))
        
        return sorted(test_files)
    
    def run_single_test_file(self, test_file: Path) -> Dict[str, Any]:
        """Run a single test file with timeout and error handling."""
        print(f"\n{'='*60}")
        print(f"Running: {test_file}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Build pytest command for single file
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_file),
            "--verbose",
            "--tb=short",
            "--no-cov",  # Skip coverage for individual runs to speed up
            "-x"  # Stop on first failure
        ]
        
        try:
            # Run with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=Path.cwd()
            )
            
            duration = time.time() - start_time
            
            test_result = {
                "file": str(test_file),
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "status": "passed" if result.returncode == 0 else "failed",
                "timed_out": False
            }
            
            # Check if test is slow (over 30 seconds)
            if duration > 30:
                self.slow_tests.append(test_result)
                print(f"⚠️  SLOW TEST: {test_file} took {duration:.1f}s")
            
            if result.returncode == 0:
                print(f"✅ PASSED: {test_file} ({duration:.1f}s)")
            else:
                print(f"❌ FAILED: {test_file} ({duration:.1f}s)")
                self.failed_tests.append(test_result)
                
        except subprocess.TimeoutExpired:
            duration = self.timeout_seconds
            test_result = {
                "file": str(test_file),
                "duration": duration,
                "return_code": -1,
                "stdout": "",
                "stderr": f"Test timed out after {self.timeout_seconds}s",
                "status": "timeout",
                "timed_out": True
            }
            print(f"⏰ TIMEOUT: {test_file} (>{self.timeout_seconds}s)")
            self.failed_tests.append(test_result)
            
        except Exception as e:
            duration = time.time() - start_time
            test_result = {
                "file": str(test_file),
                "duration": duration,
                "return_code": -2,
                "stdout": "",
                "stderr": str(e),
                "status": "error",
                "timed_out": False
            }
            print(f"💥 ERROR: {test_file} - {e}")
            self.failed_tests.append(test_result)
        
        # Save results after each test
        self.save_incremental_results()
        
        return test_result
    
    def save_incremental_results(self):
        """Save results incrementally after each test and every 10 minutes."""
        current_time = time.time()
        
        # Always save after each test, but also check if 10 minutes have passed
        should_save = (current_time - self.last_save_time) >= self.save_interval
        
        if should_save or len(self.results) == 1:  # Always save first result
            self.last_save_time = current_time
            
        # Create incremental summary
        summary = self.generate_incremental_summary()
        
        # Ensure output directory exists
        self.output_file.parent.mkdir(exist_ok=True)
        
        # Save with timestamp backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.output_file.parent / f"test_results_backup_{timestamp}.json"
        
        try:
            # Save main file
            with open(self.output_file, "w") as f:
                json.dump(summary, f, indent=2)
            
            # Save backup every 10 minutes or on first save
            if should_save or len(self.results) == 1:
                with open(backup_file, "w") as f:
                    json.dump(summary, f, indent=2)
                print(f"💾 Progress saved: {len(self.results)} tests completed (backup: {backup_file.name})")
                
        except Exception as e:
            print(f"⚠️  Failed to save results: {e}")
    
    def generate_incremental_summary(self) -> Dict[str, Any]:
        """Generate summary with current progress."""
        passed = [r for r in self.results if r["status"] == "passed"]
        failed = [r for r in self.results if r["status"] == "failed"]
        timeouts = [r for r in self.results if r["status"] == "timeout"]
        errors = [r for r in self.results if r["status"] == "error"]
        
        total_duration = sum(r["duration"] for r in self.results)
        
        # Calculate progress percentage if we know total
        completion_percentage = "unknown"
        total_estimated = "unknown"
        if hasattr(self, '_total_files') and self._total_files > 0:
            total_estimated = self._total_files
            completion_percentage = (len(self.results) / self._total_files) * 100
        
        return {
            "timestamp": datetime.now().isoformat(),
            "progress": {
                "completed": len(self.results),
                "total_estimated": total_estimated,
                "completion_percentage": completion_percentage
            },
            "total_files_completed": len(self.results),
            "total_duration_so_far": total_duration,
            "passed": len(passed),
            "failed": len(failed),
            "timeouts": len(timeouts),
            "errors": len(errors),
            "slow_tests": len(self.slow_tests),
            "results": self.results,
            "failed_tests": self.failed_tests,
            "slow_tests": self.slow_tests,
            "timeout_seconds": self.timeout_seconds,
            "status": "in_progress"
        }
    
    def load_existing_results(self) -> bool:
        """Load existing results if available for resume functionality."""
        if self.output_file.exists():
            try:
                with open(self.output_file, "r") as f:
                    existing_data = json.load(f)
                
                if existing_data.get("status") == "in_progress":
                    self.results = existing_data.get("results", [])
                    self.failed_tests = existing_data.get("failed_tests", [])
                    self.slow_tests = existing_data.get("slow_tests", [])
                    
                    completed_files = {r["file"] for r in self.results}
                    print(f"📂 Found existing progress: {len(self.results)} tests completed")
                    print(f"🔄 Resuming from where we left off...")
                    return True
                    
            except Exception as e:
                print(f"⚠️  Could not load existing results: {e}")
        
        return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests individually with graceful recovery."""
        test_files = self.discover_test_files()
        
        print(f"Found {len(test_files)} test files")
        print(f"Timeout per file: {self.timeout_seconds}s")
        print(f"Results will be saved after each test to: {self.output_file}")
        print(f"Backup saves every {self.save_interval//60} minutes")
        
        # Check for existing progress
        resumed = self.load_existing_results()
        
        # Filter out already completed tests if resuming
        if resumed:
            completed_files = {r["file"] for r in self.results}
            test_files = [f for f in test_files if str(f) not in completed_files]
            print(f"📋 Remaining tests to run: {len(test_files)}")
        
        print(f"Starting individual test run at {datetime.now()}")
        
        # Store total for progress tracking
        self._total_files = len(self.discover_test_files())  # Original total
        
        total_start = time.time()
        
        # Update progress tracking with total count
        for i, test_file in enumerate(test_files, 1):
            print(f"\n[{i}/{len(test_files)}] ", end="")
            result = self.run_single_test_file(test_file)
            self.results.append(result)
            
            # Update progress in incremental summary
            if hasattr(self, '_total_files'):
                self._total_files = len(test_files)
            
            # Brief pause between tests to avoid resource conflicts
            time.sleep(0.5)
        
        total_duration = time.time() - total_start
        
        # Generate final summary
        summary = self.generate_summary(total_duration)
        summary["status"] = "completed"
        if "progress" not in summary:
            summary["progress"] = {}
        summary["progress"]["completed"] = len(self.results)
        summary["progress"]["total_estimated"] = len(test_files) if test_files else self._total_files
        summary["progress"]["completion_percentage"] = 100.0
        
        self.save_results(summary)
        self.print_summary(summary)
        
        # Update function catalog with test results
        self.update_function_catalog(summary)
        
        return summary
    
    def generate_summary(self, total_duration: float) -> Dict[str, Any]:
        """Generate test run summary."""
        passed = [r for r in self.results if r["status"] == "passed"]
        failed = [r for r in self.results if r["status"] == "failed"]
        timeouts = [r for r in self.results if r["status"] == "timeout"]
        errors = [r for r in self.results if r["status"] == "error"]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(self.results),
            "total_duration": total_duration,
            "passed": len(passed),
            "failed": len(failed),
            "timeouts": len(timeouts),
            "errors": len(errors),
            "slow_tests": len(self.slow_tests),
            "results": self.results,
            "failed_tests": self.failed_tests,
            "slow_tests": self.slow_tests,
            "timeout_seconds": self.timeout_seconds
        }
    
    def save_results(self, summary: Dict[str, Any]):
        """Save results to JSON file."""
        output_file = Path("output/individual_test_results.json")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📊 Results saved to: {output_file}")
    
    def update_function_catalog(self, summary: Dict[str, Any]):
        """Update function catalog with test execution results."""
        try:
            import subprocess
            
            print(f"\n🔄 Updating function catalog with test results...")
            
            # Run the catalog updater script
            result = subprocess.run([
                sys.executable, "update_catalog_with_test_results.py"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ Function catalog updated successfully")
            else:
                print(f"⚠️  Catalog update failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⚠️  Catalog update timed out")
        except Exception as e:
            print(f"⚠️  Catalog update error: {e}")
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print test run summary."""
        print(f"\n{'='*60}")
        print("INDIVIDUAL TEST RUN SUMMARY")
        print(f"{'='*60}")
        print(f"Total files: {summary['total_files']}")
        print(f"Total time: {summary['total_duration']:.1f}s")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⏰ Timeouts: {summary['timeouts']}")
        print(f"💥 Errors: {summary['errors']}")
        print(f"⚠️  Slow tests (>30s): {summary['slow_tests']}")
        
        if self.failed_tests:
            print(f"\n{'='*40}")
            print("FAILED TESTS:")
            print(f"{'='*40}")
            for test in self.failed_tests:
                status_icon = "⏰" if test["timed_out"] else "❌"
                print(f"{status_icon} {test['file']} ({test['duration']:.1f}s)")
                if test["stderr"] and not test["timed_out"]:
                    # Show first few lines of error
                    error_lines = test["stderr"].split('\n')[:3]
                    for line in error_lines:
                        if line.strip():
                            print(f"   {line}")
        
        if self.slow_tests:
            print(f"\n{'='*40}")
            print("SLOW TESTS (>30s):")
            print(f"{'='*40}")
            for test in sorted(self.slow_tests, key=lambda x: x["duration"], reverse=True):
                print(f"⚠️  {test['file']} ({test['duration']:.1f}s)")
        
        print(f"\n{'='*60}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run tests individually with graceful recovery")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per test file in seconds (default: 300)")
    parser.add_argument("--pattern", type=str, help="Run only test files matching pattern")
    parser.add_argument("--fresh", action="store_true", help="Start fresh, ignore existing progress")
    
    args = parser.parse_args()
    
    runner = IndividualTestRunner(timeout_seconds=args.timeout)
    
    # Clear existing results if fresh start requested
    if args.fresh and runner.output_file.exists():
        runner.output_file.unlink()
        print("🗑️  Cleared existing progress for fresh start")
    
    if args.pattern:
        # Filter test files by pattern
        all_files = runner.discover_test_files()
        filtered_files = [f for f in all_files if args.pattern in str(f)]
        print(f"Running {len(filtered_files)} files matching pattern '{args.pattern}'")
        
        # Temporarily override discovery method
        original_discover = runner.discover_test_files
        runner.discover_test_files = lambda: filtered_files
    
    try:
        summary = runner.run_all_tests()
        
        # Exit with appropriate code
        if summary["failed"] > 0 or summary["timeouts"] > 0 or summary["errors"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
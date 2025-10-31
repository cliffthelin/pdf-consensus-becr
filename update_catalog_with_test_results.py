#!/usr/bin/env python3
"""
Update Function Catalog with Test Execution Results

This script reads test execution results from the individual test runner
and updates the function catalog with timing and status information.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set

class CatalogTestResultsUpdater:
    def __init__(self):
        self.catalog_path = Path("functions/function_catalog.ndjson")
        self.results_path = Path("output/individual_test_results.json")
        self.backup_path = Path("functions/function_catalog_backup.ndjson")
        
    def load_test_results(self) -> Dict[str, Any]:
        """Load test execution results from individual test runner."""
        if not self.results_path.exists():
            print(f"No test results found at {self.results_path}")
            return {}
        
        with open(self.results_path, "r") as f:
            return json.load(f)
    
    def load_catalog(self) -> List[Dict[str, Any]]:
        """Load the function catalog."""
        if not self.catalog_path.exists():
            print(f"Function catalog not found at {self.catalog_path}")
            return []
        
        catalog = []
        with open(self.catalog_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        catalog.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"Skipping invalid JSON line: {e}")
        
        return catalog
    
    def create_test_file_mapping(self, catalog: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Create mapping from test file paths to catalog entries."""
        mapping = {}
        
        for entry in catalog:
            test_file = entry.get("test_file", "")
            if test_file:
                # Normalize path separators
                normalized_path = test_file.replace("/", "\\")
                if normalized_path not in mapping:
                    mapping[normalized_path] = []
                mapping[normalized_path].append(entry)
        
        return mapping
    
    def update_catalog_with_results(self, test_results: Dict[str, Any]) -> bool:
        """Update catalog entries with test execution results."""
        catalog = self.load_catalog()
        if not catalog:
            return False
        
        # Create backup
        if self.catalog_path.exists():
            with open(self.backup_path, "w") as f:
                for entry in catalog:
                    f.write(json.dumps(entry, separators=(',', ':')) + '\n')
            print(f"Created backup: {self.backup_path}")
        
        # Create test file mapping
        test_file_mapping = self.create_test_file_mapping(catalog)
        
        # Process test results
        updated_count = 0
        current_time = datetime.now().isoformat()
        
        for result in test_results.get("results", []):
            test_file = result["file"]
            # Normalize path for matching
            normalized_file = test_file.replace("/", "\\")
            
            if normalized_file in test_file_mapping:
                entries = test_file_mapping[normalized_file]
                
                for entry in entries:
                    # Add execution tracking fields if not present
                    self._ensure_tracking_fields(entry)
                    
                    # Update with current execution results
                    entry["last_run_time"] = current_time
                    entry["execution_duration"] = result["duration"]
                    entry["execution_count"] = entry.get("execution_count", 0) + 1
                    
                    # Update success/failure tracking
                    if result["status"] == "passed":
                        entry["last_passing_timestamp"] = current_time
                        entry["last_error_message"] = None
                    else:
                        entry["last_failure_timestamp"] = current_time
                        # Truncate error message to 512 chars
                        error_msg = result.get("stderr", "Unknown error")[:512]
                        entry["last_error_message"] = error_msg
                    
                    # Update average duration
                    if entry["execution_count"] > 0:
                        old_avg = entry.get("average_duration", 0) or 0
                        count = entry["execution_count"]
                        entry["average_duration"] = ((old_avg * (count - 1)) + result["duration"]) / count
                    
                    # Calculate success rate (simplified - would need historical data for accuracy)
                    # For now, just track if last run was successful
                    entry["success_rate"] = 1.0 if result["status"] == "passed" else 0.0
                    
                    # Update metadata
                    if "metadata" not in entry:
                        entry["metadata"] = {}
                    entry["metadata"]["last_test_update"] = current_time
                    entry["metadata"]["test_runner_integration"] = True
                    
                    updated_count += 1
        
        # Save updated catalog
        with open(self.catalog_path, "w") as f:
            for entry in catalog:
                f.write(json.dumps(entry, separators=(',', ':')) + '\n')
        
        print(f"Updated {updated_count} catalog entries with test results")
        return True
    
    def _ensure_tracking_fields(self, entry: Dict[str, Any]):
        """Ensure entry has all required tracking fields."""
        tracking_fields = {
            "last_run_time": None,
            "last_passing_timestamp": None,
            "last_failure_timestamp": None,
            "last_error_message": None,
            "execution_duration": None,
            "execution_count": 0,
            "average_duration": None,
            "success_rate": None
        }
        
        for field, default_value in tracking_fields.items():
            if field not in entry:
                entry[field] = default_value
    
    def generate_test_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of test results for catalog integration."""
        results = test_results.get("results", [])
        
        # Group by test file
        file_stats = {}
        for result in results:
            test_file = result["file"]
            if test_file not in file_stats:
                file_stats[test_file] = {
                    "total_functions": 0,
                    "duration": result["duration"],
                    "status": result["status"],
                    "error": result.get("stderr", "")
                }
        
        # Calculate overall stats
        total_files = len(results)
        passed_files = len([r for r in results if r["status"] == "passed"])
        failed_files = len([r for r in results if r["status"] == "failed"])
        timeout_files = len([r for r in results if r["status"] == "timeout"])
        
        total_duration = sum(r["duration"] for r in results)
        avg_duration = total_duration / total_files if total_files > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_test_files": total_files,
            "passed_files": passed_files,
            "failed_files": failed_files,
            "timeout_files": timeout_files,
            "total_duration": total_duration,
            "average_duration_per_file": avg_duration,
            "file_stats": file_stats,
            "success_rate": passed_files / total_files if total_files > 0 else 0
        }
    
    def run_update(self) -> bool:
        """Run the complete update process."""
        print("Updating Function Catalog with Test Results")
        print("=" * 60)
        
        # Load test results
        test_results = self.load_test_results()
        if not test_results:
            return False
        
        print(f"Loaded test results: {len(test_results.get('results', []))} test files")
        
        # Generate summary
        summary = self.generate_test_summary(test_results)
        
        # Save summary
        summary_path = Path("output/catalog_test_integration_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Test summary saved: {summary_path}")
        
        # Update catalog
        success = self.update_catalog_with_results(test_results)
        
        if success:
            print(f"\nCatalog integration completed successfully!")
            print(f"Function catalog updated with test execution data")
            print(f"Summary: {summary['passed_files']}/{summary['total_test_files']} files passed")
            print(f"Total execution time: {summary['total_duration']:.1f}s")
            print(f"Overall success rate: {summary['success_rate']:.1%}")
        
        return success

def main():
    """Main entry point."""
    updater = CatalogTestResultsUpdater()
    success = updater.run_update()
    
    if not success:
        print("\nCatalog update failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
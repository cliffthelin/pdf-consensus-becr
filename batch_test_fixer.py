#!/usr/bin/env python3
"""
Batch Test Fixer - Systematically identify and fix common test failure patterns
"""

import subprocess
import sys
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

class BatchTestFixer:
    def __init__(self):
        self.failure_patterns = defaultdict(list)
        self.common_errors = Counter()
        self.fixed_tests = []
        
    def analyze_test_failures(self, max_tests: int = 50) -> Dict[str, List[str]]:
        """Run a subset of tests to identify common failure patterns."""
        print(f"🔍 Analyzing test failures (running up to {max_tests} tests)...")
        
        # Get list of test files
        test_files = []
        for pattern in ["tests/unit/test_*.py", "tests/integration/test_*.py", "tests/gui/test_*.py"]:
            test_files.extend(Path(".").glob(pattern))
        
        # Limit to max_tests for analysis
        test_files = test_files[:max_tests]
        
        failure_analysis = {
            "import_errors": [],
            "assertion_errors": [],
            "file_not_found": [],
            "attribute_errors": [],
            "type_errors": [],
            "other_errors": []
        }
        
        for i, test_file in enumerate(test_files, 1):
            print(f"[{i}/{len(test_files)}] Analyzing {test_file}")
            
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", str(test_file), 
                    "--tb=short", "-x", "--no-cov"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    error_type, error_msg = self._categorize_error(result.stdout + result.stderr)
                    failure_analysis[error_type].append({
                        "file": str(test_file),
                        "error": error_msg
                    })
                    self.common_errors[error_type] += 1
                    
            except subprocess.TimeoutExpired:
                failure_analysis["other_errors"].append({
                    "file": str(test_file),
                    "error": "Test timeout (>30s)"
                })
            except Exception as e:
                failure_analysis["other_errors"].append({
                    "file": str(test_file),
                    "error": f"Analysis error: {e}"
                })
        
        return failure_analysis
    
    def _categorize_error(self, error_output: str) -> Tuple[str, str]:
        """Categorize error based on output patterns."""
        error_output = error_output.lower()
        
        if "importerror" in error_output or "modulenotfounderror" in error_output:
            # Extract import error details
            import_match = re.search(r"importerror.*?cannot import name '([^']+)'", error_output)
            if import_match:
                return "import_errors", f"Cannot import: {import_match.group(1)}"
            return "import_errors", "Import/Module error"
            
        elif "filenotfounderror" in error_output:
            # Extract file path
            file_match = re.search(r"filenotfounderror.*?not found:? ([^\n]+)", error_output)
            if file_match:
                return "file_not_found", f"File not found: {file_match.group(1).strip()}"
            return "file_not_found", "File not found error"
            
        elif "assertionerror" in error_output:
            # Extract assertion details
            assert_match = re.search(r"assert (.+?)(?:\n|$)", error_output)
            if assert_match:
                return "assertion_errors", f"Assertion: {assert_match.group(1).strip()}"
            return "assertion_errors", "Assertion error"
            
        elif "attributeerror" in error_output:
            # Extract attribute error
            attr_match = re.search(r"attributeerror.*?'([^']+)'.*?has no attribute '([^']+)'", error_output)
            if attr_match:
                return "attribute_errors", f"{attr_match.group(1)} has no attribute {attr_match.group(2)}"
            return "attribute_errors", "Attribute error"
            
        elif "typeerror" in error_output:
            return "type_errors", "Type error"
            
        else:
            return "other_errors", "Unknown error"
    
    def generate_fixes_for_import_errors(self, import_errors: List[Dict]) -> List[str]:
        """Generate fixes for common import errors."""
        fixes = []
        
        # Group by missing import
        missing_imports = defaultdict(list)
        for error in import_errors:
            if "Cannot import:" in error["error"]:
                import_name = error["error"].split("Cannot import: ")[1]
                missing_imports[import_name].append(error["file"])
        
        for import_name, files in missing_imports.items():
            if len(files) > 1:  # Common across multiple files
                fixes.append(f"# Fix missing import '{import_name}' in {len(files)} files")
                
                # Common import fixes
                if import_name == "validate_ndjson_record":
                    fixes.append("# Change: from compareblocks.io.schemas import validate_ndjson_record")
                    fixes.append("# To: from compareblocks.io.loader import validate_ndjson_record")
                elif import_name == "DataLoader":
                    fixes.append("# Change: from compareblocks.io.loader import DataLoader")
                    fixes.append("# To: from compareblocks.io.loader import NDJSONLoader")
                
        return fixes
    
    def generate_fixes_for_file_errors(self, file_errors: List[Dict]) -> List[str]:
        """Generate fixes for file not found errors."""
        fixes = []
        
        # Group by file pattern
        missing_files = defaultdict(list)
        for error in file_errors:
            if "File not found:" in error["error"]:
                file_path = error["error"].split("File not found: ")[1]
                missing_files[file_path].append(error["file"])
        
        for file_path, test_files in missing_files.items():
            if len(test_files) > 1:
                fixes.append(f"# Missing file '{file_path}' affects {len(test_files)} tests")
                
                # Common file fixes
                if "test" in file_path and "pdf" in file_path:
                    fixes.append("# Add graceful handling for missing test PDFs")
                elif "config" in file_path:
                    fixes.append("# Add default configuration handling")
        
        return fixes
    
    def apply_common_import_fixes(self) -> int:
        """Apply common import fixes across multiple files."""
        fixes_applied = 0
        
        # Fix 1: validate_ndjson_record import
        test_files = list(Path(".").glob("tests/**/*.py"))
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                if "from compareblocks.io.schemas import validate_ndjson_record" in content:
                    new_content = content.replace(
                        "from compareblocks.io.schemas import validate_ndjson_record",
                        "from compareblocks.io.loader import validate_ndjson_record"
                    )
                    test_file.write_text(new_content)
                    fixes_applied += 1
                    print(f"✅ Fixed validate_ndjson_record import in {test_file}")
            except Exception as e:
                print(f"⚠️ Error fixing {test_file}: {e}")
        
        # Fix 2: DataLoader -> NDJSONLoader
        for test_file in test_files:
            try:
                content = test_file.read_text()
                if "from compareblocks.io.loader import DataLoader" in content:
                    new_content = content.replace(
                        "from compareblocks.io.loader import DataLoader",
                        "from compareblocks.io.loader import NDJSONLoader"
                    )
                    # Also replace usage
                    new_content = new_content.replace("DataLoader()", "NDJSONLoader()")
                    test_file.write_text(new_content)
                    fixes_applied += 1
                    print(f"✅ Fixed DataLoader import in {test_file}")
            except Exception as e:
                print(f"⚠️ Error fixing {test_file}: {e}")
        
        return fixes_applied
    
    def apply_gui_test_fixes(self) -> int:
        """Apply GUI test fixes (widget.show() requirement)."""
        fixes_applied = 0
        
        gui_test_files = list(Path("tests/gui").glob("test_*.py"))
        for test_file in gui_test_files:
            try:
                content = test_file.read_text()
                
                # Check if it has widget fixture without show()
                if ("def widget(" in content and 
                    "widget.show()" not in content and
                    "QWidget" in content):
                    
                    # Add show() to widget fixture
                    pattern = r"(def widget\([^)]*\):[^}]+?widget = [^}]+?)\n(\s+return widget)"
                    replacement = r"\1\n        widget.show()  # Required for Qt visibility in tests\n        QApplication.processEvents()\2"
                    
                    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                    if new_content != content:
                        test_file.write_text(new_content)
                        fixes_applied += 1
                        print(f"✅ Added widget.show() to {test_file}")
                        
            except Exception as e:
                print(f"⚠️ Error fixing GUI test {test_file}: {e}")
        
        return fixes_applied
    
    def run_batch_fixes(self) -> Dict[str, int]:
        """Run all batch fixes and return summary."""
        print("🔧 Applying batch fixes...")
        
        results = {
            "import_fixes": self.apply_common_import_fixes(),
            "gui_fixes": self.apply_gui_test_fixes(),
        }
        
        total_fixes = sum(results.values())
        print(f"\n📊 Batch fixes applied: {total_fixes} total")
        for fix_type, count in results.items():
            print(f"  {fix_type}: {count}")
        
        return results
    
    def generate_report(self, analysis: Dict[str, List[str]]) -> str:
        """Generate a comprehensive analysis report."""
        report = ["# Test Failure Analysis Report", ""]
        
        # Summary
        total_errors = sum(len(errors) for errors in analysis.values())
        report.append(f"**Total Errors Analyzed**: {total_errors}")
        report.append("")
        
        # Error breakdown
        report.append("## Error Breakdown")
        for error_type, errors in analysis.items():
            if errors:
                report.append(f"- **{error_type.replace('_', ' ').title()}**: {len(errors)}")
        report.append("")
        
        # Top errors by category
        for error_type, errors in analysis.items():
            if errors and len(errors) > 0:
                report.append(f"## {error_type.replace('_', ' ').title()}")
                for error in errors[:5]:  # Show top 5
                    report.append(f"- `{error['file']}`: {error['error']}")
                if len(errors) > 5:
                    report.append(f"- ... and {len(errors) - 5} more")
                report.append("")
        
        # Recommendations
        report.append("## Recommended Fixes")
        
        if analysis["import_errors"]:
            report.extend(self.generate_fixes_for_import_errors(analysis["import_errors"]))
            report.append("")
        
        if analysis["file_not_found"]:
            report.extend(self.generate_fixes_for_file_errors(analysis["file_not_found"]))
            report.append("")
        
        return "\n".join(report)

def main():
    fixer = BatchTestFixer()
    
    print("🚀 Starting Batch Test Analysis and Fixes")
    print("=" * 60)
    
    # Step 1: Apply known common fixes first
    batch_results = fixer.run_batch_fixes()
    
    # Step 2: Analyze remaining failures
    analysis = fixer.analyze_test_failures(max_tests=30)  # Analyze 30 tests for patterns
    
    # Step 3: Generate report
    report = fixer.generate_report(analysis)
    
    # Save report
    report_file = Path("output/batch_test_analysis.md")
    report_file.parent.mkdir(exist_ok=True)
    report_file.write_text(report)
    
    print(f"\n📄 Analysis report saved to: {report_file}")
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"✅ Batch fixes applied: {sum(batch_results.values())}")
    print(f"🔍 Errors analyzed: {sum(len(errors) for errors in analysis.values())}")
    print(f"📊 Most common error: {fixer.common_errors.most_common(1)[0] if fixer.common_errors else 'None'}")
    
    return 0

if __name__ == "__main__":
    exit(main())
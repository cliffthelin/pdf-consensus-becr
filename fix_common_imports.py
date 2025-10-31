#!/usr/bin/env python3
"""
Fix Common Import Errors - Target the most frequent import issues
"""

import subprocess
import sys
from pathlib import Path

def fix_import_errors():
    """Fix the most common import errors found in tests."""
    fixes_applied = 0
    
    # Get all test files
    test_files = []
    for pattern in ["tests/**/*.py"]:
        test_files.extend(Path(".").glob(pattern))
    
    print(f"🔍 Checking {len(test_files)} test files for import issues...")
    
    for test_file in test_files:
        try:
            # Read with UTF-8 encoding to handle special characters
            content = test_file.read_text(encoding='utf-8', errors='ignore')
            original_content = content
            
            # Fix 1: validate_ndjson_record import location
            if "from compareblocks.io.schemas import validate_ndjson_record" in content:
                content = content.replace(
                    "from compareblocks.io.schemas import validate_ndjson_record",
                    "from compareblocks.io.loader import validate_ndjson_record"
                )
                print(f"✅ Fixed validate_ndjson_record import in {test_file}")
            
            # Fix 2: DataLoader -> NDJSONLoader
            if "from compareblocks.io.loader import DataLoader" in content:
                content = content.replace(
                    "from compareblocks.io.loader import DataLoader",
                    "from compareblocks.io.loader import NDJSONLoader"
                )
                # Also replace class usage
                content = content.replace("DataLoader()", "NDJSONLoader()")
                content = content.replace("DataLoader.", "NDJSONLoader.")
                print(f"✅ Fixed DataLoader -> NDJSONLoader in {test_file}")
            
            # Fix 3: Common missing imports that should be available
            missing_imports = [
                ("from compareblocks.io.loader import NDJSONLoader", "NDJSONLoader"),
                ("from compareblocks.io.writer import NDJSONWriter", "NDJSONWriter"),
                ("from compareblocks.consensus.score import ConsensusScorer", "ConsensusScorer"),
                ("from compareblocks.consensus.policy import DecisionPolicyEngine", "DecisionPolicyEngine"),
            ]
            
            for import_line, class_name in missing_imports:
                if class_name in content and import_line not in content:
                    # Add import at the top after existing imports
                    lines = content.split('\n')
                    import_section_end = 0
                    for i, line in enumerate(lines):
                        if line.startswith('from ') or line.startswith('import '):
                            import_section_end = i
                    
                    if import_section_end > 0:
                        lines.insert(import_section_end + 1, import_line)
                        content = '\n'.join(lines)
                        print(f"✅ Added missing import {class_name} to {test_file}")
            
            # Save if changes were made
            if content != original_content:
                test_file.write_text(content, encoding='utf-8')
                fixes_applied += 1
                
        except Exception as e:
            print(f"⚠️ Error processing {test_file}: {e}")
    
    return fixes_applied

def test_specific_failures():
    """Test a few specific files to see if fixes worked."""
    test_files = [
        "tests/unit/test_analytics_dashboard.py",
        "tests/unit/test_consensus_score.py",
        "tests/integration/test_complete_system_with_all_engines.py"
    ]
    
    print(f"\n🧪 Testing {len(test_files)} specific files...")
    
    for test_file in test_files:
        if Path(test_file).exists():
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", test_file, 
                    "--tb=line", "-x", "--no-cov"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"✅ {test_file} - PASSED")
                else:
                    print(f"❌ {test_file} - FAILED")
                    # Show first error line
                    error_lines = result.stdout.split('\n')
                    for line in error_lines:
                        if 'FAILED' in line or 'ERROR' in line:
                            print(f"   {line}")
                            break
                            
            except subprocess.TimeoutExpired:
                print(f"⏰ {test_file} - TIMEOUT")
            except Exception as e:
                print(f"💥 {test_file} - ERROR: {e}")

def main():
    print("🚀 Fixing Common Import Errors")
    print("=" * 50)
    
    # Apply fixes
    fixes = fix_import_errors()
    print(f"\n📊 Applied {fixes} import fixes")
    
    # Test some specific files
    test_specific_failures()
    
    print(f"\n✨ Import fix process complete!")
    return 0

if __name__ == "__main__":
    exit(main())
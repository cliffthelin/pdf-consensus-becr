#!/usr/bin/env python3
"""
Fix syntax errors in the adhoc test file without changing test logic.
"""

import re
from pathlib import Path


def fix_adhoc_test_syntax():
    """Fix syntax errors in adhoc test file."""
    
    file_path = Path("tests/adhoc/test_function_catalog_default_file_validation.py")
    
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False
    
    content = file_path.read_text(encoding='utf-8')
    original_content = content
    
    # Fix malformed assert statements with multiple f-strings
    content = re.sub(
        r'assert (.*?), f"(.*?)", f"(.*?)"',
        r'assert \1, f"\3"',
        content
    )
    
    # Fix malformed assert statements with mixed f-string and regular string
    content = re.sub(
        r'assert (.*?), f"(.*?)", "(.*?)"',
        r'assert \1, f"\2"',
        content
    )
    
    # Fix broken if statements
    content = re.sub(
        r'if not if (.*?):',
        r'if not \1:',
        content
    )
    
    # Fix malformed pytest.skip statements
    content = re.sub(
        r'pytest\.skip\("Test file not found"\)',
        r'pytest.skip("Function catalog file not found")',
        content
    )
    
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        print(f"Fixed syntax errors in {file_path}")
        return True
    else:
        print(f"No syntax errors found in {file_path}")
        return True


def main():
    """Main function."""
    success = fix_adhoc_test_syntax()
    
    if success:
        # Test the file
        import subprocess
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/adhoc/", "--tb=line", "-v"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Adhoc test is now working!")
            else:
                print("❌ Adhoc test still has issues:")
                print(result.stdout)
                print(result.stderr)
                
        except Exception as e:
            print(f"Error testing adhoc file: {e}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Fix integration test files for syntax errors and import issues.
"""

import re
from pathlib import Path
from typing import List


def fix_integration_tests():
    """Fix all integration test files."""
    
    integration_dir = Path("tests/integration")
    test_files = list(integration_dir.glob("test_*.py"))
    
    fixed_files = []
    
    for test_file in test_files:
        try:
            content = test_file.read_text(encoding='utf-8')
            original_content = content
            
            # Apply fixes
            content = fix_syntax_errors(content)
            content = fix_import_errors(content)
            content = fix_assertion_errors(content)
            content = fix_pytest_skip_statements(content)
            
            # Only write if changes were made
            if content != original_content:
                test_file.write_text(content, encoding='utf-8')
                fixed_files.append(str(test_file))
                print(f"Fixed {test_file}")
                
        except Exception as e:
            print(f"Error fixing {test_file}: {e}")
    
    return fixed_files


def fix_syntax_errors(content: str) -> str:
    """Fix common syntax errors."""
    
    # Fix unmatched parentheses in assert statements
    content = re.sub(
        r'assert (.*?)\.suffix == \'(.*?)\'\)',
        r'assert \1.suffix == "\2"',
        content
    )
    
    # Fix broken string literals
    content = re.sub(
        r'assert (.*?)\.suffix == \'(.*?)\'\}"',
        r'assert \1.suffix == "\2"',
        content
    )
    
    # Fix malformed assert statements with extra closing parentheses
    content = re.sub(
        r'assert (.*?)\)\s*assert (.*?)\}"',
        r'assert \1\nassert \2',
        content
    )
    
    return content


def fix_import_errors(content: str) -> str:
    """Fix import errors."""
    
    # Fix relative imports to absolute imports
    content = re.sub(
        r'from compareblocks\.(.*?) import',
        r'from src.compareblocks.\1 import',
        content
    )
    
    # Remove duplicate imports
    lines = content.split('\n')
    seen_imports = set()
    fixed_lines = []
    
    for line in lines:
        if line.strip().startswith(('import ', 'from ')):
            if line.strip() not in seen_imports:
                seen_imports.add(line.strip())
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_assertion_errors(content: str) -> str:
    """Fix assertion errors."""
    
    # Fix broken assert statements with multiple conditions
    content = re.sub(
        r'assert (.*?) is not None, f"Expected (.*?) to not be None", f"Expected (.*?) to not be None" and isinstance\((.*?), (.*?)\)',
        r'assert \1 is not None and isinstance(\4, \5), f"Expected \2 to not be None and be instance of \5"',
        content
    )
    
    # Fix assert statements with broken string formatting
    content = re.sub(
        r'assert abs\((.*?) - (.*?)\) < 0\.01, f"Expected (.*?) to be close to (.*?)"',
        r'assert abs(\1 - \2) < 0.01, f"Expected \3 to be close to \4"',
        content
    )
    
    return content


def fix_pytest_skip_statements(content: str) -> str:
    """Fix pytest.skip statements."""
    
    # Fix malformed pytest.skip in if statements
    content = re.sub(
        r'if not (.*?)\.exists\(\): pytest\.skip\(f"Test file not found: \{(.*?)\}"\)',
        r'if not \1.exists():\n                pytest.skip(f"Test file not found: {\2}")',
        content
    )
    
    # Fix pytest.skip with broken f-strings
    content = re.sub(
        r'pytest\.skip\(f"Test file not found: \{(.*?)\}"\)',
        r'pytest.skip(f"Test file not found: {\1}")',
        content
    )
    
    return content


def run_integration_tests():
    """Run integration tests to check for remaining issues."""
    
    import subprocess
    
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/integration/", "--tb=line", "-x"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ All integration tests are now passing!")
        else:
            print("❌ Some integration tests still failing:")
            print(result.stdout)
            print(result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Integration tests timed out")
        return False
    except Exception as e:
        print(f"Error running integration tests: {e}")
        return False


def main():
    """Main function to fix integration tests."""
    
    print("🔧 Fixing integration test files...")
    
    fixed_files = fix_integration_tests()
    
    if fixed_files:
        print(f"\n✅ Fixed {len(fixed_files)} integration test files:")
        for file in fixed_files:
            print(f"  - {file}")
    else:
        print("\n✅ No integration test files needed fixing")
    
    print("\n🧪 Running integration tests to verify fixes...")
    success = run_integration_tests()
    
    if success:
        print("\n🎉 All integration tests are working!")
    else:
        print("\n⚠️  Some integration tests may still need manual fixes")
    
    return success


if __name__ == "__main__":
    main()
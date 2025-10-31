#!/usr/bin/env python3
"""
Fix Syntax Errors - Clean up malformed f-strings and other syntax issues
"""

import re
import ast
from pathlib import Path

def fix_malformed_fstrings():
    """Fix malformed f-strings created by aggressive assertion fixing."""
    fixes = 0
    test_files = list(Path(".").glob("tests/**/*.py"))
    
    print("🔧 Fixing malformed f-strings...")
    
    for test_file in test_files:
        try:
            content = test_file.read_text(encoding='utf-8', errors='ignore')
            original_content = content
            
            # Fix common malformed f-string patterns
            fixes_patterns = [
                # Fix nested f-strings in assertions
                (r'assert ([^=]+) == ([^,]+), f"Expected \{([^}]+)\} to equal \{([^}]+)\}"', 
                 r'assert \1 == \2, f"Expected {\1} to equal {\2}"'),
                
                # Fix broken f-string concatenations
                (r'f"Expected \{([^}]+)\} to not be None" and isinstance\(([^,]+), ([^)]+)\)', 
                 r'f"Expected \1 to not be None and be instance of \3"'),
                
                # Fix malformed assertion messages
                (r'assert ([^,]+), f"Expected \{([^}]+)\} to equal \{([^}]+)\}"', 
                 r'assert \1, f"Expected {\2} to equal {\3}"'),
                
                # Fix broken dictionary access in f-strings
                (r"assert ([^']+)'([^']+)'\} to equal \{'([^']+)'\}", 
                 r"assert \1'\2'] == '\3', f\"Expected {\1'\2']} to equal '\3'\""),
                
                # Fix simple broken assertions
                (r'assert ([^=]+) == ([^,]+), f"Expected \{([^}]*)\} to equal \{([^}]*)\}"', 
                 r'assert \1 == \2'),
                
                # Remove malformed f-string parts
                (r', f"Expected \{[^}]*\} to equal \{[^}]*\}"', ''),
                
                # Fix isinstance with f-string
                (r'assert ([^,]+) is not None, f"[^"]*" and isinstance\(([^,]+), ([^)]+)\)', 
                 r'assert \1 is not None and isinstance(\2, \3)'),
            ]
            
            for pattern, replacement in fixes_patterns:
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    content = new_content
            
            # Try to parse the file to check for syntax errors
            try:
                ast.parse(content)
            except SyntaxError as e:
                print(f"⚠️ Syntax error in {test_file} at line {e.lineno}: {e.msg}")
                # Try to fix common syntax errors
                lines = content.split('\n')
                if e.lineno <= len(lines):
                    line = lines[e.lineno - 1]
                    
                    # Fix common f-string issues
                    if 'f-string' in str(e):
                        # Remove malformed f-strings
                        fixed_line = re.sub(r'f"[^"]*\{[^}]*\}[^"]*"', '""', line)
                        if fixed_line != line:
                            lines[e.lineno - 1] = fixed_line
                            content = '\n'.join(lines)
                            print(f"  Fixed f-string syntax error")
            
            if content != original_content:
                test_file.write_text(content, encoding='utf-8')
                fixes += 1
                print(f"✅ Fixed syntax errors in {test_file}")
                
        except Exception as e:
            print(f"⚠️ Error processing {test_file}: {e}")
    
    return fixes

def validate_python_syntax():
    """Validate Python syntax in all test files."""
    errors = []
    test_files = list(Path(".").glob("tests/**/*.py"))
    
    print("🔍 Validating Python syntax...")
    
    for test_file in test_files:
        try:
            content = test_file.read_text(encoding='utf-8', errors='ignore')
            ast.parse(content)
        except SyntaxError as e:
            errors.append((test_file, e.lineno, e.msg))
            print(f"❌ {test_file}:{e.lineno} - {e.msg}")
        except Exception as e:
            print(f"⚠️ Error checking {test_file}: {e}")
    
    if not errors:
        print("✅ All test files have valid Python syntax")
    
    return len(errors)

def main():
    print("🚀 Fixing Syntax Errors")
    print("=" * 40)
    
    # Fix malformed f-strings
    fixes = fix_malformed_fstrings()
    print(f"\n📊 Fixed {fixes} files with syntax errors")
    
    # Validate syntax
    error_count = validate_python_syntax()
    print(f"\n📊 Found {error_count} remaining syntax errors")
    
    return 0

if __name__ == "__main__":
    exit(main())
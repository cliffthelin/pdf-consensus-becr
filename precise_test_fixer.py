#!/usr/bin/env python3
"""
Precise test fixer for specific syntax errors in test files.
"""

import re
from pathlib import Path


def fix_specific_syntax_errors():
    """Fix specific syntax errors in test files."""
    
    test_files = [
        "tests/unit/test_analytics_engine.py",
        "tests/unit/test_analytics_export.py", 
        "tests/unit/test_advanced_engine_integration.py",
        "tests/unit/test_mapping_iou.py"
    ]
    
    for file_path in test_files:
        path = Path(file_path)
        if not path.exists():
            continue
            
        try:
            content = path.read_text(encoding='utf-8')
            original_content = content
            
            # Fix malformed assert statements
            content = fix_malformed_asserts(content)
            content = fix_broken_string_literals(content)
            content = fix_conditional_asserts(content)
            content = fix_import_issues(content)
            
            if content != original_content:
                path.write_text(content, encoding='utf-8')
                print(f"Fixed {file_path}")
                
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")


def fix_malformed_asserts(content: str) -> str:
    """Fix malformed assert statements."""
    
    # Fix broken assert with multiple conditions
    patterns = [
        # Pattern 1: assert abs(X is not None and isinstance(X, Y) assert len(X) - Z) < 0.01, f"..."
        (r'assert abs\((.*?) is not None and isinstance\((.*?), (.*?)\)\s+assert len\((.*?)\) - (.*?)\) < 0\.01, f"Expected (.*?)", f"Expected (.*?)" and isinstance\((.*?), (.*?)\)\s+assert len\((.*?)\) to be close to (.*?)"',
         r'assert \1 is not None and isinstance(\2, \3), f"Expected \6"\nassert len(\4) == \5, f"Expected len(\11) to be close to \12"'),
        
        # Pattern 2: assert abs(X - Y) < 0.01, f"Expected Z", f"Expected W" and isinstance(A, B)
        (r'assert abs\((.*?) - (.*?)\) < 0\.01, f"Expected (.*?)", f"Expected (.*?)" and isinstance\((.*?), (.*?)\)',
         r'assert abs(\1 - \2) < 0.01 and isinstance(\5, \6), f"Expected \3"'),
         
        # Pattern 3: Complex broken assertions
        (r'assert abs\((.*?) is not None and isinstance\((.*?), (.*?)\)\s+assert len\((.*?)\) - (.*?)\) < 0\.01, f"Expected (.*?) is not None, f"Expected (.*?) to not be None" and isinstance\((.*?), (.*?)\)\s+assert len\((.*?)\) to be close to (.*?)"',
         r'assert \1 is not None and isinstance(\2, \3), f"Expected \6 to not be None"\nassert len(\4) == \5, f"Expected len(\10) to be close to \11"'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    return content


def fix_broken_string_literals(content: str) -> str:
    """Fix broken string literals."""
    
    # Fix unterminated f-strings
    content = re.sub(
        r'f"Expected (.*?) is not None, f"Expected (.*?) to not be None" and isinstance\((.*?), (.*?)\)',
        r'f"Expected \1 is not None and isinstance(\3, \4)"',
        content
    )
    
    # Fix broken pytest.skip statements
    content = re.sub(
        r'if not (.*?)\.exists\(\): pytest\.skip\(f"Test file not found: \{(.*?)\}"\)',
        r'if not \1.exists(): pytest.skip(f"Test file not found: {\2}")',
        content
    )
    
    # Fix broken assert statements with string formatting
    content = re.sub(
        r'assert (.*?) to be close to (.*?)"',
        r'assert abs(\1 - \2) < 0.01, f"Expected \1 to be close to \2"',
        content
    )
    
    return content


def fix_conditional_asserts(content: str) -> str:
    """Fix conditional assert statements."""
    
    # Fix "if not X assert Y" patterns
    content = re.sub(
        r'if not (.*?)\s+assert (.*?)',
        r'assert \1, "\2"',
        content
    )
    
    # Fix "if not 'key' in dict assert" patterns
    content = re.sub(
        r'if not \'(.*?)\' in (.*?)\s+assert (.*?)',
        r'assert "\1" in \2, "\3"',
        content
    )
    
    return content


def fix_import_issues(content: str) -> str:
    """Fix import issues."""
    
    # Fix duplicate imports
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


if __name__ == "__main__":
    fix_specific_syntax_errors()
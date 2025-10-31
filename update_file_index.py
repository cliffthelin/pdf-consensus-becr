#!/usr/bin/env python3
"""
Update File Index

This script updates the file_index_readme.md to include all missing files
that should be documented.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

def load_missing_files_report() -> Dict[str, Any]:
    """Load the missing files report."""
    report_path = Path('output/missing_files_and_functions_report.json')
    
    if not report_path.exists():
        print("❌ Missing files report not found. Run analyze_missing_files_and_functions.py first.")
        return {}
    
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def categorize_file(file_info: Dict[str, Any]) -> str:
    """Categorize a file based on its path and characteristics."""
    path = file_info['path']
    
    # Root level utilities
    if not path.startswith('src/') and not path.startswith('functions/'):
        if file_info['has_main']:
            return "Processing & Analysis Tools"
        else:
            return "Validation & Monitoring Tools"
    
    # Functions directory
    if path.startswith('functions/'):
        return "Function Analysis & Management Tools"
    
    # Source code modules
    if path.startswith('src/compareblocks/'):
        parts = path.split('/')
        if len(parts) >= 3:
            category = parts[2]
            if category == 'analytics':
                return "Analytics & Reporting Modules"
            elif category == 'engines':
                return "OCR Engine Modules"
            elif category == 'gui':
                return "GUI Component Modules"
            elif category == 'io':
                return "Input/Output Modules"
            elif category == 'features':
                return "Feature Extraction Modules"
            elif category == 'consensus':
                return "Consensus & Decision Modules"
            elif category == 'mapping':
                return "Block Mapping Modules"
            elif category == 'association':
                return "Association & Alignment Modules"
            elif category == 'gbg':
                return "Global Block Grid Modules"
            elif category == 'config':
                return "Configuration Management Modules"
            elif category == 'mcp':
                return "MCP Integration Modules"
            elif category == 'processing':
                return "Processing Pipeline Modules"
            elif category == 'project':
                return "Project Management Modules"
            elif category == 'testing':
                return "Testing & Validation Modules"
            elif category == 'normalize':
                return "Text Normalization Modules"
            elif category == 'debug':
                return "Debug & Diagnostic Modules"
            else:
                return "Core System Modules"
    
    return "Utility Modules"

def determine_purpose(file_info: Dict[str, Any]) -> str:
    """Determine the purpose of a file."""
    path = file_info['path']
    filename = Path(path).name
    
    # Special cases
    if filename == 'build_test_catalog.py':
        return "Test catalog generation and cross-referencing system"
    elif filename == 'analyze_missing_files_and_functions.py':
        return "Project analysis for missing files and function coverage"
    elif 'engine' in filename:
        return "OCR engine implementation and integration"
    elif 'gui' in filename or 'dialog' in filename or 'viewer' in filename:
        return "User interface components and interactions"
    elif 'config' in filename:
        return "Configuration management and validation"
    elif 'test' in filename and not filename.startswith('test_'):
        return "Testing utilities and framework support"
    elif 'analytics' in filename:
        return "Analytics processing and reporting functionality"
    elif 'consensus' in filename:
        return "Consensus decision making and result merging"
    elif 'mcp' in filename:
        return "Model Context Protocol integration and communication"
    elif 'processing' in filename or 'processor' in filename:
        return "Data processing pipeline and workflow management"
    elif 'manager' in filename:
        return "Resource and workflow management functionality"
    elif filename.endswith('_matcher.py'):
        return "Block matching and spatial alignment algorithms"
    elif 'consistency' in filename:
        return "Text consistency tracking and validation"
    elif 'features' in filename:
        return "Feature extraction and quality metrics"
    elif 'normalize' in filename:
        return "Text normalization and standardization"
    elif 'debug' in filename:
        return "Debug utilities and diagnostic tools"
    else:
        return f"Core functionality for {filename.replace('.py', '').replace('_', ' ')}"

def create_file_entry(file_info: Dict[str, Any]) -> str:
    """Create a file index entry."""
    path = file_info['path'].replace('\\', '/')
    filename = Path(path).name
    purpose = determine_purpose(file_info)
    
    # Create description based on file characteristics
    description_parts = []
    
    if file_info['has_main']:
        description_parts.append("Command-line utility with main entry point.")
    
    if file_info['functions'] > 0:
        description_parts.append(f"Contains {file_info['functions']} utility functions.")
    
    if file_info['classes'] > 0:
        description_parts.append(f"Implements {file_info['classes']} classes.")
    
    # Add specific functionality description
    if 'engine' in filename:
        description_parts.append("Provides OCR engine integration with standardized interface and error handling.")
    elif 'gui' in filename:
        description_parts.append("Implements user interface components with PySide6 integration.")
    elif 'config' in filename:
        description_parts.append("Manages configuration validation and runtime settings.")
    elif 'analytics' in filename:
        description_parts.append("Processes analytics data and generates comprehensive reports.")
    elif 'consensus' in filename:
        description_parts.append("Implements consensus algorithms for result merging and decision making.")
    elif 'mcp' in filename:
        description_parts.append("Handles Model Context Protocol communication and integration.")
    elif 'test' in filename and not filename.startswith('test_'):
        description_parts.append("Provides testing utilities and framework integration.")
    
    description_parts.append("Essential for system functionality and workflow integration.")
    
    description = " ".join(description_parts)
    
    return f"""### `{path}`
**Path:** `./{path}`
**Purpose:** {purpose}
**Description:** {description}"""

def update_file_index():
    """Update the file index with missing files."""
    print("📋 Updating File Index")
    print("=" * 30)
    
    # Load missing files report
    report = load_missing_files_report()
    if not report:
        return
    
    missing_files = report.get('missing_files', [])
    print(f"📁 Found {len(missing_files)} missing files")
    
    # Categorize files
    categories = {}
    for file_info in missing_files:
        category = categorize_file(file_info)
        if category not in categories:
            categories[category] = []
        categories[category].append(file_info)
    
    # Generate new sections
    new_sections = []
    
    for category, files in sorted(categories.items()):
        if not files:
            continue
            
        new_sections.append(f"\n## {category}\n")
        
        for file_info in sorted(files, key=lambda x: x['path']):
            entry = create_file_entry(file_info)
            new_sections.append(entry + "\n")
    
    # Read current file index
    index_path = Path('file_index_readme.md')
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
    else:
        current_content = "# BECR Utility Files Index\n\nThis document provides a comprehensive index of all utility files in the BECR project.\n"
    
    # Find insertion point (before Usage Guidelines)
    usage_index = current_content.find("## Usage Guidelines")
    if usage_index == -1:
        # Append to end
        new_content = current_content + "\n" + "\n".join(new_sections)
    else:
        # Insert before Usage Guidelines
        new_content = (current_content[:usage_index] + 
                      "\n".join(new_sections) + "\n\n" + 
                      current_content[usage_index:])
    
    # Write updated file index
    backup_path = Path('file_index_readme_backup.md')
    if index_path.exists():
        index_path.rename(backup_path)
        print(f"📋 Created backup: {backup_path}")
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Updated file index with {len(missing_files)} files")
    print(f"📁 File index saved to: {index_path}")
    
    # Show summary by category
    print(f"\n📊 Files Added by Category:")
    for category, files in sorted(categories.items()):
        print(f"  {category}: {len(files)} files")

if __name__ == "__main__":
    update_file_index()
    print(f"\n🎉 File index update complete!")
    print("💡 Review the updated file_index_readme.md and adjust descriptions as needed.")
#!/usr/bin/env python3
"""
Enhance Test Catalog with Execution Tracking

This script adds execution tracking attributes to all entries in the test catalog,
ensuring every test has the required timing and result tracking fields.
"""

import json
from pathlib import Path
from datetime import datetime

def enhance_test_catalog():
    """Add execution tracking attributes to test catalog entries."""
    print("🔧 Enhancing Test Catalog with Execution Tracking")
    print("=" * 60)
    
    catalog_path = Path('functions/test_catalog.ndjson')
    if not catalog_path.exists():
        print("❌ Test catalog not found")
        return False
    
    # Load existing catalog
    catalog_entries = []
    with open(catalog_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    catalog_entries.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"⚠️ Skipping invalid JSON line: {e}")
                    continue
    
    print(f"📚 Loaded {len(catalog_entries)} test catalog entries")
    
    # Enhance each entry with execution tracking attributes
    enhanced_count = 0
    for entry in catalog_entries:
        # Add execution tracking attributes if not present
        attributes_added = []
        
        if 'last_run_time' not in entry:
            entry['last_run_time'] = None
            attributes_added.append('last_run_time')
        
        if 'last_passing_timestamp' not in entry:
            entry['last_passing_timestamp'] = None
            attributes_added.append('last_passing_timestamp')
        
        if 'last_failure_timestamp' not in entry:
            entry['last_failure_timestamp'] = None
            attributes_added.append('last_failure_timestamp')
        
        if 'last_error_message' not in entry:
            entry['last_error_message'] = None
            attributes_added.append('last_error_message')
        
        if 'execution_duration' not in entry:
            entry['execution_duration'] = None
            attributes_added.append('execution_duration')
        
        if 'execution_count' not in entry:
            entry['execution_count'] = 0
            attributes_added.append('execution_count')
        
        if 'average_duration' not in entry:
            entry['average_duration'] = None
            attributes_added.append('average_duration')
        
        if 'success_rate' not in entry:
            entry['success_rate'] = None
            attributes_added.append('success_rate')
        
        # Update metadata
        if 'metadata' not in entry:
            entry['metadata'] = {}
        
        entry['metadata']['execution_tracking_enabled'] = True
        entry['metadata']['last_enhanced'] = datetime.now().isoformat()
        
        if attributes_added:
            enhanced_count += 1
            print(f"✅ Enhanced {entry.get('test_name', 'unknown')}: {', '.join(attributes_added)}")
    
    # Create backup
    backup_path = Path('functions/test_catalog_backup.ndjson')
    if catalog_path.exists():
        catalog_path.rename(backup_path)
        print(f"📋 Created backup: {backup_path}")
    
    # Write enhanced catalog
    with open(catalog_path, 'w', encoding='utf-8') as f:
        for entry in catalog_entries:
            f.write(json.dumps(entry, separators=(',', ':')) + '\n')
    
    print(f"\n📊 Enhancement Summary:")
    print(f"  Total entries: {len(catalog_entries)}")
    print(f"  Enhanced entries: {enhanced_count}")
    print(f"  Catalog updated: {catalog_path}")
    
    # Validate the enhanced catalog
    print(f"\n🔍 Validating enhanced catalog...")
    validation_errors = []
    
    for i, entry in enumerate(catalog_entries):
        required_attrs = [
            'last_run_time', 'last_passing_timestamp', 'last_failure_timestamp',
            'last_error_message', 'execution_duration', 'execution_count',
            'average_duration', 'success_rate'
        ]
        
        for attr in required_attrs:
            if attr not in entry:
                validation_errors.append(f"Entry {i}: Missing {attr}")
    
    if validation_errors:
        print(f"❌ Validation errors found:")
        for error in validation_errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(validation_errors) > 10:
            print(f"  ... and {len(validation_errors) - 10} more errors")
        return False
    else:
        print(f"✅ Catalog validation passed - all entries have execution tracking attributes")
        return True

def create_execution_tracking_schema():
    """Create a schema document for execution tracking attributes."""
    schema = {
        "execution_tracking_attributes": {
            "last_run_time": {
                "type": "string|null",
                "format": "ISO 8601 timestamp",
                "description": "Timestamp of the last test execution"
            },
            "last_passing_timestamp": {
                "type": "string|null", 
                "format": "ISO 8601 timestamp",
                "description": "Timestamp of the last successful test execution"
            },
            "last_failure_timestamp": {
                "type": "string|null",
                "format": "ISO 8601 timestamp", 
                "description": "Timestamp of the last failed test execution"
            },
            "last_error_message": {
                "type": "string|null",
                "max_length": 512,
                "description": "Error message from the last failed execution (truncated to 512 chars)"
            },
            "execution_duration": {
                "type": "number|null",
                "unit": "seconds",
                "description": "Duration of the last test execution in seconds"
            },
            "execution_count": {
                "type": "integer",
                "minimum": 0,
                "description": "Total number of times this test has been executed"
            },
            "average_duration": {
                "type": "number|null",
                "unit": "seconds",
                "description": "Average execution duration across all runs"
            },
            "success_rate": {
                "type": "number|null",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Success rate as a decimal (0.0 to 1.0)"
            }
        },
        "metadata_enhancements": {
            "execution_tracking_enabled": {
                "type": "boolean",
                "description": "Indicates if execution tracking is enabled for this test"
            },
            "last_enhanced": {
                "type": "string",
                "format": "ISO 8601 timestamp",
                "description": "Timestamp when the entry was last enhanced"
            }
        }
    }
    
    schema_path = Path('functions/execution_tracking_schema.json')
    with open(schema_path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2)
    
    print(f"📄 Created execution tracking schema: {schema_path}")
    return schema_path

if __name__ == "__main__":
    success = enhance_test_catalog()
    schema_path = create_execution_tracking_schema()
    
    if success:
        print(f"\n🎉 Test catalog enhancement completed successfully!")
        print(f"📋 All {Path('functions/test_catalog.ndjson').stat().st_size // 1024}KB catalog entries now have execution tracking")
        print(f"📄 Schema documentation: {schema_path}")
        print(f"\n💡 Next steps:")
        print("  1. Run tests using the new test runner: python -m src.compareblocks.testing.test_execution_tracker")
        print("  2. Use the GUI test runner in the BECR application")
        print("  3. Check execution results in the enhanced test catalog")
    else:
        print(f"\n❌ Test catalog enhancement failed!")
        print("Please check the errors above and try again.")
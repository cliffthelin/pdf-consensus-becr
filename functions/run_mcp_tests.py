#!/usr/bin/env python3
"""
MCP Test Execution Script

Runs all MCP tests in the correct order with proper coverage tracking.
"""

import subprocess
import sys
from pathlib import Path

def run_mcp_tests():
    """Run all MCP tests with coverage."""
    
    test_files = [
        "tests/unit/test_mcp_protocol.py",
        "tests/unit/test_mcp_validation.py", 
        "tests/unit/test_mcp_handlers.py",
        "tests/integration/test_mcp_integration.py"
    ]
    
    print("🧪 Running MCP Integration Tests")
    print("=" * 50)
    
    # Run tests with coverage
    cmd = [
        "python", "-m", "pytest",
        *test_files,
        "--cov=src/compareblocks/mcp",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/mcp",
        "--cov-fail-under=95",
        "-v",
        "--tb=short"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print("\n✅ All MCP tests passed!")
    else:
        print("\n❌ Some MCP tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    run_mcp_tests()

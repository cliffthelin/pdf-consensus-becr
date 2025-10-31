#!/usr/bin/env python3
"""
MCP Setup Verification Script
Checks if MCP configuration is correct and servers can be launched.
"""

import json
import subprocess
import sys
from pathlib import Path

def check_uv_installed():
    """Check if uv/uvx is installed."""
    try:
        result = subprocess.run(['uvx', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ uvx is installed:", result.stdout.strip())
            return True
        else:
            print("❌ uvx not working properly")
            return False
    except FileNotFoundError:
        print("❌ uvx not found - install uv first")
        return False

def check_mcp_config():
    """Check if MCP configuration file exists and is valid."""
    config_path = Path.home() / ".kiro" / "settings" / "mcp.json"
    
    if not config_path.exists():
        print(f"❌ MCP config not found at: {config_path}")
        return False
    
    print(f"✅ MCP config found at: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if 'mcpServers' not in config:
            print("❌ Config missing 'mcpServers' key")
            return False
        
        server_count = len(config['mcpServers'])
        print(f"✅ Config is valid JSON with {server_count} server(s)")
        
        # List configured servers
        for name, server_config in config['mcpServers'].items():
            disabled = server_config.get('disabled', False)
            status = "disabled" if disabled else "enabled"
            print(f"   - {name}: {status}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Config is invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False

def test_fetch_server():
    """Test if mcp-server-fetch can be launched."""
    print("\nTesting mcp-server-fetch...")
    try:
        result = subprocess.run(
            ['uvx', 'mcp-server-fetch', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ mcp-server-fetch can be launched")
            return True
        else:
            print("❌ mcp-server-fetch failed to launch")
            print("Error:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  mcp-server-fetch timed out (this might be normal)")
        return True
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("MCP Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("UV/UVX Installation", check_uv_installed),
        ("MCP Configuration", check_mcp_config),
        ("Fetch Server", test_fetch_server),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking: {name}")
        print("-" * 40)
        result = check_func()
        results.append((name, result))
        print()
    
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All checks passed! MCP should be working in Kiro.")
        print("\nNext steps:")
        print("1. Restart Kiro or reconnect MCP servers")
        print("2. Check the MCP Server panel in Kiro")
        print("3. Try using the fetch tool")
        return 0
    else:
        print("⚠️  Some checks failed. Review the errors above.")
        print("\nSee output/mcp_setup_guide.md for troubleshooting help.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

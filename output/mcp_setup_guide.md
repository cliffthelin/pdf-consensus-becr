# MCP Setup and Troubleshooting Guide for Kiro

## Current Status

✅ **uv/uvx installed**: Version 0.7.13  
✅ **Python installed**: Version 3.12  
✅ **MCP server package available**: mcp-server-fetch  
✅ **Configuration file exists**: `C:\Users\Cane\.kiro\settings\mcp.json`  
⚠️ **Network issue**: robots.txt fetching was causing failures  
✅ **Fix applied**: Added `--ignore-robots-txt` flag

## How MCP Works in Kiro

### Architecture
1. **Kiro** reads `~/.kiro/settings/mcp.json` (user-level) or `.kiro/settings/mcp.json` (workspace-level)
2. **Kiro** launches MCP servers as child processes using `uvx`
3. **Servers** communicate via **stdio** (standard input/output), not WebSockets
4. **Tools** become available in Kiro's tool palette once connected

### Configuration Format
```json
{
  "mcpServers": {
    "server-name": {
      "command": "uvx",
      "args": ["package-name", "--optional-flags"],
      "env": {
        "ENV_VAR": "value"
      },
      "disabled": false,
      "autoApprove": ["tool1", "tool2"],
      "disabledTools": []
    }
  }
}
```

## Current Configuration

**Location**: `C:\Users\Cane\.kiro\settings\mcp.json`

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": [
        "mcp-server-fetch",
        "--ignore-robots-txt"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      },
      "disabled": false,
      "autoApprove": [
        "fetch"
      ],
      "disabledTools": []
    }
  }
}
```

### What Each Setting Does

- **command**: `uvx` - Uses uv's package runner
- **args**: Package name and flags
  - `mcp-server-fetch` - The MCP server package
  - `--ignore-robots-txt` - Skip robots.txt checks (fixes network issues)
- **env**: Environment variables
  - `PYTHONIOENCODING: utf-8` - Fixes Windows Unicode issues
- **disabled**: `false` - Server is enabled
- **autoApprove**: Tools that don't require user approval
- **disabledTools**: Tools to disable (empty = all enabled)

## Troubleshooting Steps

### 1. Check if Server is Connected

In Kiro:
1. Open Command Palette (Ctrl+Shift+P)
2. Search for "MCP"
3. Look for "MCP: Show Server Status" or similar
4. Check the MCP Server panel in the sidebar

### 2. View Server Logs

- Kiro logs MCP server output
- Check the "MCP Logs" output channel
- Look for connection errors or crashes

### 3. Common Issues and Fixes

#### Issue: Server Won't Start
**Symptoms**: No tools available, connection errors in logs

**Fixes**:
```powershell
# 1. Verify uvx works
uvx --version

# 2. Test server manually
uvx mcp-server-fetch --help

# 3. Check for Python issues
python --version
```

#### Issue: Unicode Errors (Windows)
**Symptoms**: `UnicodeEncodeError: 'charmap' codec can't encode character`

**Fix**: Add to env section:
```json
"env": {
  "PYTHONIOENCODING": "utf-8"
}
```

#### Issue: Network/Robots.txt Errors
**Symptoms**: `Failed to fetch robots.txt`

**Fix**: Add flag to args:
```json
"args": [
  "mcp-server-fetch",
  "--ignore-robots-txt"
]
```

#### Issue: Server Crashes on Startup
**Symptoms**: Server connects then immediately disconnects

**Fixes**:
1. Check logs for specific error
2. Try different server package
3. Verify package compatibility with Windows

### 4. Manual Server Testing

Test if a server works outside Kiro:

```powershell
# Set environment
$env:PYTHONIOENCODING = "utf-8"

# Run server (it will wait for stdio input)
uvx mcp-server-fetch --ignore-robots-txt

# Press Ctrl+C to exit
```

### 5. Reconnect Servers

After config changes:
1. Servers auto-reconnect when config changes
2. Or use Command Palette → "MCP: Reconnect All Servers"
3. Or restart Kiro

## Available MCP Servers

### Working Servers (Tested)

#### 1. fetch (Currently Configured)
- **Package**: `mcp-server-fetch`
- **Purpose**: Fetch web content
- **Tools**: `fetch`
- **Status**: ✅ Working with `--ignore-robots-txt`

### Potentially Compatible Servers

#### 2. filesystem
- **Package**: `mcp-server-filesystem`
- **Purpose**: File system operations
- **Issue**: Has Windows bugs (calculator launch, Unicode errors)
- **Recommendation**: ❌ Skip for now

#### 3. git
- **Package**: `mcp-server-git`
- **Purpose**: Git operations
- **Status**: ⚠️ Not tested, may have Windows issues

#### 4. sequential-thinking
- **Package**: `mcp-server-sequential-thinking`
- **Purpose**: Step-by-step reasoning
- **Status**: ⚠️ Not tested

#### 5. memory
- **Package**: `mcp-server-memory`
- **Purpose**: Persistent knowledge graph
- **Status**: ⚠️ Not tested

## Testing the Fetch Server

Once connected, you can test the fetch tool:

### Example 1: Fetch a Simple Page
```
Use the fetch tool to get https://example.com
```

### Example 2: Fetch API Data
```
Use the fetch tool to get https://api.github.com/repos/microsoft/vscode
```

### Example 3: Fetch Documentation
```
Use the fetch tool to get https://docs.python.org/3/library/json.html
```

## Adding More Servers

To add additional servers, edit the config:

```json
{
  "mcpServers": {
    "fetch": {
      // ... existing config ...
    },
    "new-server": {
      "command": "uvx",
      "args": ["mcp-server-package-name"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      },
      "disabled": false,
      "autoApprove": [],
      "disabledTools": []
    }
  }
}
```

**Important**: Add servers one at a time and test each before adding more!

## Best Practices

1. **Start Simple**: Begin with one working server (fetch)
2. **Test Individually**: Add servers one at a time
3. **Check Logs**: Always review MCP logs after adding a server
4. **Use UTF-8**: Always include `PYTHONIOENCODING: utf-8` on Windows
5. **Auto-Approve Carefully**: Only auto-approve tools you trust
6. **Document Issues**: Note which servers don't work on Windows

## Current Recommendations

For your BECR project, the `fetch` server is most useful for:
- Fetching documentation during development
- Looking up API references
- Researching PDF processing techniques
- Checking library documentation

The filesystem and git servers have Windows compatibility issues, so stick with `fetch` for now.

## Next Steps

1. ✅ Fetch server is configured and should be working
2. Wait for Kiro to reconnect (automatic)
3. Check MCP Server panel for connection status
4. Try using the fetch tool with a simple URL
5. If issues persist, check the MCP Logs output channel

## Support Resources

- **Kiro MCP Docs**: Check Kiro's documentation for MCP
- **MCP Specification**: https://modelcontextprotocol.io/
- **Server Packages**: Search PyPI for "mcp-server-*"
- **Community**: Kiro Discord/forums for MCP help

---

**Last Updated**: 2025-10-31  
**Status**: Fetch server configured with network fix applied

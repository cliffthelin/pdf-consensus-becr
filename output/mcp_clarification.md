# MCP Clarification: Two Different Systems

## The Confusion

You're asking about **two completely different "MCP" systems** that happen to share the same acronym:

### 1. Kiro IDE's MCP Servers (External Tools)
**What**: Third-party tools that extend Kiro's capabilities  
**Purpose**: Give Kiro (the IDE) new abilities like fetching web content  
**Examples**: `mcp-server-fetch`, `mcp-server-filesystem`  
**Where**: Configured in `~/.kiro/settings/mcp.json`  
**Protocol**: Model Context Protocol (stdio-based)  
**Status**: ✅ Working (fetch server is connected)

### 2. BECR's Internal MCP Architecture (Your Application)
**What**: Internal client/server architecture for your BECR application  
**Purpose**: Communication between BECR components  
**Location**: `src/compareblocks/mcp/` directory  
**Files**:
- `client.py` - MCP client for BECR
- `server.py` - MCP server for BECR  
- `handlers.py` - Request handlers
- `protocol.py` - Message protocol
- `validation.py` - Request validation

**Protocol**: WebSocket-based (ws://localhost:8765)  
**Status**: ⚠️ This is YOUR application code, not a Kiro IDE extension

## Key Differences

| Aspect | Kiro's MCP Servers | BECR's MCP System |
|--------|-------------------|-------------------|
| **Purpose** | Extend Kiro IDE | Internal BECR architecture |
| **Protocol** | stdio (standard input/output) | WebSocket |
| **Installation** | PyPI packages via `uvx` | Part of your codebase |
| **Configuration** | `mcp.json` file | Python code |
| **Usage** | I (Kiro agent) use them | Your BECR app uses it internally |
| **Examples** | fetch, filesystem, git | extraction, status, results |

## Your BECR MCP System

Looking at your code, your BECR project has:

### Server (`src/compareblocks/mcp/server.py`)
- WebSocket server on localhost:8765
- Handles extraction requests
- Manages client connections
- Methods:
  - `initialize`
  - `submit_extraction`
  - `get_status`
  - `get_results`
  - `subscribe_updates`
  - `unsubscribe_updates`

### Client (`src/compareblocks/mcp/client.py`)
- Connects to the BECR MCP server
- Sends extraction requests
- Receives results

### Purpose
This is for **your application's internal architecture**, allowing different parts of BECR to communicate, especially for:
- PDF extraction requests
- Status monitoring
- Result retrieval
- Real-time updates

## Can You Expose BECR's MCP to Kiro?

**Short answer**: Not directly, they're incompatible protocols.

**Why not**:
1. Kiro expects **stdio** protocol
2. Your BECR MCP uses **WebSocket** protocol
3. Different message formats
4. Different purposes

**What you CAN do**:
1. Keep them separate (recommended)
2. Create a **wrapper** that translates between protocols (complex)
3. Use BECR's MCP for internal communication
4. Use Kiro's MCP servers for IDE extensions

## Where to Get New Kiro MCP Servers

### Official Sources:
1. **PyPI**: Search for "mcp-server-*"
   ```bash
   pip search mcp-server
   ```

2. **GitHub**: Search for "mcp-server" repositories

3. **MCP Registry** (if available): Check https://modelcontextprotocol.io/

### Popular Servers:
- `mcp-server-fetch` ✅ (you have this)
- `mcp-server-filesystem` ⚠️ (Windows issues)
- `mcp-server-git` ⚠️ (untested)
- `mcp-server-sqlite` 
- `mcp-server-postgres`
- `mcp-server-brave-search`
- `mcp-server-puppeteer`

### How to Add:
1. Find the package name on PyPI
2. Add to `~/.kiro/settings/mcp.json`:
```json
{
  "mcpServers": {
    "new-server": {
      "command": "uvx",
      "args": ["package-name"],
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
3. Kiro will auto-reconnect

## Your PDF Extraction Mention

You mentioned "external ones in place for PDF extraction" - this is likely referring to:

1. **Your BECR MCP server** (internal, not a Kiro extension)
2. **PDF processing engines** in your code:
   - PyMuPDF
   - Tesseract
   - PaddleOCR
   - Docling
   - Kreuzberg

These are **Python libraries**, not MCP servers for Kiro.

## Summary

- ✅ **Kiro's MCP**: fetch server is working, use it for web content
- ✅ **BECR's MCP**: Your internal architecture, works independently
- ❌ **They don't talk to each other**: Different protocols, different purposes
- 📦 **Get new Kiro MCP servers**: Search PyPI for "mcp-server-*"
- 🔧 **Your PDF tools**: Are Python libraries, not MCP servers

The confusion is understandable - same acronym, completely different systems!

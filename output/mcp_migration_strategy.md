# MCP Migration Strategy: Protecting Current Functionality

## Current State Analysis

### What's Working (Direct Import Mode)
```
src/compareblocks/
├── engines/              # ✅ Direct Python imports - WORKING
│   ├── docling_engine.py
│   ├── kreuzberg_engine.py
│   ├── pymupdf_engine.py
│   ├── tesseract_engine.py
│   ├── paddleocr_engine.py
│   └── manager.py        # Manages direct imports
├── gui/                  # ✅ Uses direct imports - WORKING
│   └── app.py
└── mcp/                  # ⚠️ Built but not connected
    ├── client.py
    ├── server.py
    ├── handlers.py
    ├── protocol.py
    └── validation.py
```

### What Needs to Be Built (MCP Mode)
According to Requirements 21 & 22, all compareblocks functionality should be accessed through MCP.

## Protection Strategy

### 1. Keep Existing Code Untouched
**Files to NEVER modify during MCP implementation:**
- `src/compareblocks/engines/*.py` (all engine files)
- `src/compareblocks/engines/manager.py` (current manager)
- `src/compareblocks/gui/app.py` (current GUI)
- All existing tests

### 2. Create Parallel MCP Infrastructure
**New files to create (won't conflict with existing):**
```
src/compareblocks/
├── engines/
│   └── mcp_manager.py          # NEW: MCP-based engine manager
├── mcp/
│   ├── engine_handlers.py      # NEW: Engine-specific MCP handlers
│   ├── server_runner.py        # NEW: Standalone server runner
│   └── client_facade.py        # NEW: Easy client interface
└── gui/
    └── mcp_app.py              # NEW: MCP-enabled GUI (optional)
```

### 3. Dual-Mode Operation
Allow both modes to coexist:
- **Direct Mode** (current): Fast, simple, working
- **MCP Mode** (new): Follows spec, allows remote engines

## Implementation Plan

### Phase 1: MCP Server Enhancement (No Risk)
**Goal**: Make MCP server expose engine functionality
**Files**: NEW files only, no modifications

1. Create `src/compareblocks/mcp/engine_handlers.py`
   - Wraps existing engines for MCP access
   - Doesn't modify engine files

2. Update `src/compareblocks/mcp/handlers.py`
   - Add engine methods to existing handlers
   - Extends, doesn't replace

3. Create `src/compareblocks/mcp/server_runner.py`
   - Standalone script to run MCP server
   - Independent of main app

### Phase 2: MCP Client Facade (No Risk)
**Goal**: Easy interface for MCP-based engine access
**Files**: NEW files only

1. Create `src/compareblocks/mcp/client_facade.py`
   - Simple API: `mcp_client.extract_pdf(engine, pdf_path)`
   - Handles connection, requests, responses

2. Create `src/compareblocks/engines/mcp_manager.py`
   - Parallel to existing `manager.py`
   - Uses MCP client instead of direct imports

### Phase 3: Optional MCP GUI (No Risk)
**Goal**: GUI that uses MCP mode
**Files**: NEW file, doesn't touch existing GUI

1. Create `src/compareblocks/gui/mcp_app.py`
   - Copy of app.py but uses MCP manager
   - Completely separate from working GUI

### Phase 4: Configuration Toggle (Low Risk)
**Goal**: Choose mode at runtime
**Files**: Minimal config changes

1. Add to `config/default_files.json`:
```json
{
  "engine_mode": "direct",  // or "mcp"
  "mcp_server_url": "ws://localhost:8765"
}
```

2. Create `src/compareblocks/engines/factory.py`:
```python
def get_engine_manager(mode='direct'):
    if mode == 'mcp':
        return MCPEngineManager()
    else:
        return EngineManager()  # existing
```

## File-by-File Safety Plan

### Safe to Create (New Files)
✅ `src/compareblocks/mcp/engine_handlers.py`
✅ `src/compareblocks/mcp/client_facade.py`
✅ `src/compareblocks/mcp/server_runner.py`
✅ `src/compareblocks/engines/mcp_manager.py`
✅ `src/compareblocks/engines/factory.py`
✅ `src/compareblocks/gui/mcp_app.py`
✅ `tests/unit/test_mcp_engines.py`
✅ `tests/integration/test_mcp_engine_integration.py`

### Safe to Extend (Additive Only)
⚠️ `src/compareblocks/mcp/handlers.py` - Add new methods, don't modify existing
⚠️ `src/compareblocks/mcp/server.py` - Add engine routes, don't modify core
⚠️ `config/default_files.json` - Add new keys, don't modify existing

### DO NOT MODIFY
❌ `src/compareblocks/engines/docling_engine.py`
❌ `src/compareblocks/engines/kreuzberg_engine.py`
❌ `src/compareblocks/engines/pymupdf_engine.py`
❌ `src/compareblocks/engines/tesseract_engine.py`
❌ `src/compareblocks/engines/paddleocr_engine.py`
❌ `src/compareblocks/engines/manager.py`
❌ `src/compareblocks/gui/app.py`
❌ Any existing test files

## Architecture Diagram

```
Current (Direct Mode) - KEEP AS-IS:
┌─────────┐
│ GUI App │──────> EngineManager ──────> Engines (direct import)
└─────────┘                               ├── docling
                                          ├── kreuzberg
                                          └── pymupdf

New (MCP Mode) - BUILD PARALLEL:
┌─────────────┐
│ MCP GUI App │──> MCPEngineManager ──> MCP Client ──> MCP Server ──> Engines
└─────────────┘                                                        ├── docling
                                                                       ├── kreuzberg
                                                                       └── pymupdf

Hybrid (Both Modes):
┌─────────┐
│ GUI App │──> EngineFactory ──┬──> EngineManager (direct)
└─────────┘                     └──> MCPEngineManager (via MCP)
```

## Testing Strategy

### Test Isolation
1. **Existing tests**: Continue to test direct mode
2. **New tests**: Test MCP mode separately
3. **Integration tests**: Test both modes work

### Test Files
```
tests/
├── unit/
│   ├── test_engines.py              # Existing - don't touch
│   └── test_mcp_engines.py          # NEW - MCP mode tests
├── integration/
│   ├── test_engine_integration.py   # Existing - don't touch
│   └── test_mcp_integration.py      # NEW - MCP integration
└── comparison/
    └── test_mode_parity.py           # NEW - verify both modes work
```

## Migration Checklist

### Before Starting
- [ ] Commit all current working code
- [ ] Create branch: `feature/mcp-engine-access`
- [ ] Document current functionality
- [ ] Run all existing tests to establish baseline

### During Implementation
- [ ] Only create NEW files
- [ ] Never modify engine files
- [ ] Never modify current GUI
- [ ] Test both modes independently
- [ ] Keep direct mode as default

### After Implementation
- [ ] All existing tests still pass
- [ ] New MCP tests pass
- [ ] Both modes work independently
- [ ] Documentation updated
- [ ] User can choose mode via config

## Rollback Plan

If anything breaks:
1. **Direct mode unaffected**: Just delete new files
2. **No code changes**: Nothing to revert
3. **Tests isolated**: Existing tests unchanged
4. **Config optional**: Default stays "direct"

## Benefits of This Approach

1. **Zero Risk**: Current functionality completely protected
2. **Gradual Migration**: Can test MCP mode without affecting users
3. **Flexibility**: Choose mode based on needs
4. **Reversible**: Can remove MCP mode without impact
5. **Testable**: Both modes can be tested independently

## Next Steps

1. **Review this plan** - Ensure it meets your needs
2. **Create new files** - Start with MCP server enhancements
3. **Test incrementally** - Verify each new component
4. **Keep direct mode default** - Until MCP mode is proven
5. **Document both modes** - Clear usage instructions

## Success Criteria

✅ Current direct mode still works perfectly
✅ New MCP mode provides same functionality
✅ User can choose mode via configuration
✅ All tests pass for both modes
✅ No modifications to existing engine files
✅ No modifications to existing GUI
✅ Clear documentation for both approaches

---

**Status**: Ready to implement
**Risk Level**: Minimal (new files only)
**Estimated Effort**: 2-3 days for full MCP mode
**Fallback**: Delete new files, keep current code

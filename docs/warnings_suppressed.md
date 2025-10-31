# Suppressed Warnings Documentation

This document tracks all warnings that have been intentionally suppressed in the BECR system's pytest configuration. When adding new warning suppressions, update this document to maintain visibility and accountability.

## Configuration Location
- **File**: `pyproject.toml`
- **Section**: `[tool.pytest.ini_options]` → `filterwarnings`

## Currently Suppressed Warnings

### 1. Third-Party Library Deprecation Warnings

#### PyMuPDF (fitz) SWIG Warnings
```
"ignore::DeprecationWarning:fitz.*"
"ignore:builtin type SwigPyPacked has no __module__ attribute:DeprecationWarning"
"ignore:builtin type SwigPyObject has no __module__ attribute:DeprecationWarning" 
"ignore:builtin type swigvarlink has no __module__ attribute:DeprecationWarning"
```

**Source**: PyMuPDF's internal SWIG bindings  
**Reason**: These are deep within PyMuPDF's C++ bindings and cannot be fixed by our codebase  
**Action Required**: None - will be resolved by PyMuPDF maintainers  
**Risk Level**: None - purely cosmetic warnings from library internals  

#### Docling Framework Warnings
```
"ignore::DeprecationWarning:docling.*"
"ignore::DeprecationWarning:docling_core.*"
"ignore:.*@model_validator.*deprecated.*:DeprecationWarning"
"ignore:ListItem parent must be a list group.*:DeprecationWarning"
```

**Source**: Docling's internal Pydantic model validators  
**Reason**: Docling uses deprecated Pydantic v2.12 patterns that will be removed in v3.0  
**Action Required**: None - will be resolved when Docling updates to newer Pydantic  
**Risk Level**: None - internal to Docling's implementation  

#### Pydantic Framework Warnings
```
"ignore::DeprecationWarning:pydantic.*"
```

**Source**: Pydantic library deprecation notices  
**Reason**: Third-party libraries using deprecated Pydantic features  
**Action Required**: None - handled by library maintainers  
**Risk Level**: None - does not affect our code functionality  

### 2. General User Warnings
```
"ignore::UserWarning"
```

**Source**: Various libraries generating non-critical user warnings  
**Reason**: Reduces noise from third-party library informational messages  
**Action Required**: Monitor for any critical warnings that might be hidden  
**Risk Level**: Low - may hide some informational messages  

### 3. Preserved Warnings (NOT Suppressed)

#### Our Own Code Warnings
```
"default::DeprecationWarning:compareblocks.*"
"default::DeprecationWarning:tests.*"
```

**Purpose**: Ensures warnings from our own codebase remain visible  
**Reason**: We need to see and address deprecations in our own code  
**Action Required**: Address any warnings that appear from our modules  
**Risk Level**: None - these should be addressed when they appear  

## Warning Suppression Guidelines

### ✅ Safe to Suppress
- **Third-party library internal warnings** that we cannot fix
- **Deprecation warnings from dependencies** that will be resolved by maintainers
- **SWIG/C++ binding warnings** from compiled libraries
- **Framework internal warnings** (Pydantic, Docling, etc.)

### ⚠️ Suppress with Caution
- **User warnings** that might contain important information
- **Performance warnings** that could indicate real issues
- **Security warnings** (should never be suppressed)

### ❌ Never Suppress
- **Warnings from our own code** (`compareblocks.*`, `tests.*`)
- **Error-level warnings** that indicate real problems
- **Security-related warnings** from any source
- **Data corruption warnings** from any library

## Adding New Suppressions

When adding new warning suppressions:

1. **Document the warning** in this file with:
   - Exact warning text or pattern
   - Source library/module
   - Reason for suppression
   - Expected resolution timeline
   - Risk assessment

2. **Use specific patterns** rather than broad suppressions:
   ```python
   # Good - specific
   "ignore:specific warning text:DeprecationWarning:library_name.*"
   
   # Bad - too broad
   "ignore::DeprecationWarning"
   ```

3. **Test the suppression** to ensure it works correctly

4. **Update this documentation** with the new entry

## Monitoring and Maintenance

### Regular Review Schedule
- **Monthly**: Review this document for outdated suppressions
- **Before major updates**: Check if library updates resolve suppressed warnings
- **During dependency updates**: Verify suppressions are still needed

### Removal Criteria
Remove warning suppressions when:
- The underlying library fixes the issue
- We stop using the library that generates the warning
- The warning becomes actionable for our codebase

### Testing Suppression Effectiveness
```bash
# Run tests to see current warning levels
python -m pytest tests/ -v

# Run with all warnings enabled to see what's being suppressed
python -m pytest tests/ -v -W default

# Run specific test to check warning suppression
python -m pytest tests/unit/test_engine_validation_system.py -v
```

## Current Status Summary

| Warning Type | Count | Status | Action Needed |
|--------------|-------|--------|---------------|
| PyMuPDF SWIG | 3 | Partially Suppressed* | None - library internal |
| Docling/Pydantic | 4 | Partially Suppressed* | None - framework internal |
| User Warnings | 1 | Suppressed | Monitor for critical messages |
| Our Code | 0 | Preserved | Address if any appear |

**Note**: Some warnings marked with * may still appear during test runs because they are generated at the C extension level during import, before Python's warning filters take effect. This is a limitation of the warning system, not a configuration issue.

## Last Updated
- **Date**: 2024-12-19
- **Updated By**: Kiro AI Assistant
- **Reason**: Initial documentation of warning suppression strategy
- **Next Review**: 2025-01-19

---

**Note**: This document should be updated whenever warning suppressions are added, removed, or modified in `pyproject.toml`. Maintaining this documentation ensures transparency and helps future developers understand why certain warnings are suppressed.

## Known Limitations

### C Extension Warnings
Some warnings from C extensions (like PyMuPDF's SWIG bindings) cannot be fully suppressed because they are generated at the C level during module import, before Python's warning system can filter them. These warnings are:

- `builtin type SwigPyPacked has no __module__ attribute`
- `builtin type SwigPyObject has no __module__ attribute` 
- `builtin type swigvarlink has no __module__ attribute`

**Impact**: These warnings may still appear in test output but do not affect functionality.  
**Solution**: These will be resolved when PyMuPDF updates their SWIG bindings.  
**Workaround**: Use `pytest -W ignore::DeprecationWarning` to suppress all deprecation warnings if clean output is critical.

### Import-Time Warnings
Some Pydantic/Docling warnings occur during module import and may not be caught by pytest's filterwarnings. This is expected behavior and does not indicate a configuration problem.

## Alternative Suppression Methods

If you need completely clean test output for CI/CD or presentations:

```bash
# Suppress all deprecation warnings
python -m pytest tests/ -W ignore::DeprecationWarning

# Suppress all warnings
python -m pytest tests/ -W ignore

# Run with minimal output
python -m pytest tests/ -q --disable-warnings
```

**Caution**: These methods will also suppress warnings from your own code that you should address.
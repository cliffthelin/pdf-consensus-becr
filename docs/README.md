# BECR Documentation

This directory contains project documentation for the BECR (Blockwise Extraction Comparison & Review) system.

## Documentation Files

### Development & Maintenance
- **[warnings_suppressed.md](warnings_suppressed.md)** - Complete documentation of all suppressed test warnings
- **[testing_guidelines.md](../tests/README.md)** - Testing standards and practices (if exists)

### System Architecture
- **[project_structure.md](../README.md)** - Overall project structure (if exists)
- **[engine_validation.md](../output/task20_comprehensive_engine_validation_summary.md)** - Engine testing and validation system

### Configuration
- **[pyproject.toml](../pyproject.toml)** - Main project configuration including warning suppressions

## Quick Reference

### Warning Management
When you encounter new warnings during development:

1. **Check if it's from our code** - If yes, fix the underlying issue
2. **Check if it's from third-party libraries** - If yes, consider suppression
3. **Document any new suppressions** in [warnings_suppressed.md](warnings_suppressed.md)
4. **Update the configuration** in `pyproject.toml` with reference comment

### Testing
```bash
# Run tests with current warning configuration
python -m pytest tests/ -v

# See all warnings (including suppressed ones)
python -m pytest tests/ -v -W default
```

## Maintenance

This documentation should be updated when:
- New warning suppressions are added
- Dependencies are updated
- Testing procedures change
- System architecture evolves

Last updated: 2024-12-19
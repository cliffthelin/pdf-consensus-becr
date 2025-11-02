# src/compareblocks/project/__init__.py
"""
Project management module for BECR system.
Handles comprehensive file tracking, validation, project structure management,
and extraction version control.
"""

from .manager import (
    ProjectManager,
    ProjectStructure,
    FileStatus,
    create_project_structure,
    validate_project_structure,
    get_project_summary
)

from .extraction_version_manager import (
    ExtractionVersionManager,
    ExtractionMetadata,
    ExtractionVersion,
    EngineExtractionHistory,
    ExtractionFormat,
    register_extraction,
    get_engine_extraction_history,
    get_version_summary
)

__all__ = [
    'ProjectManager',
    'ProjectStructure', 
    'FileStatus',
    'create_project_structure',
    'validate_project_structure',
    'get_project_summary',
    'ExtractionVersionManager',
    'ExtractionMetadata',
    'ExtractionVersion',
    'EngineExtractionHistory',
    'ExtractionFormat',
    'register_extraction',
    'get_engine_extraction_history',
    'get_version_summary'
]
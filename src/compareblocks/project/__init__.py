# src/compareblocks/project/__init__.py
"""
Project management module for BECR system.
Handles comprehensive file tracking, validation, and project structure management.
"""

from .manager import (
    ProjectManager,
    ProjectStructure,
    FileStatus,
    create_project_structure,
    validate_project_structure,
    get_project_summary
)

__all__ = [
    'ProjectManager',
    'ProjectStructure', 
    'FileStatus',
    'create_project_structure',
    'validate_project_structure',
    'get_project_summary'
]
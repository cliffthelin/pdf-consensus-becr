# src/compareblocks/association/__init__.py
"""
Association system for handling multi-format extracted content.
Provides format-specific parsing, content alignment, and association management.
"""

from .parsers import (
    FormatParser,
    CSVParser,
    HTMLParser,
    JSONParser,
    MarkdownParser,
    TextParser,
    parse_association_file,
    detect_format
)

from .alignment import (
    ContentAligner,
    align_content_to_blocks,
    fuzzy_match_content
)

from .manager import (
    AssociationManager,
    load_associations_for_pdf,
    track_association_metadata
)

__all__ = [
    'FormatParser',
    'CSVParser',
    'HTMLParser', 
    'JSONParser',
    'MarkdownParser',
    'TextParser',
    'parse_association_file',
    'detect_format',
    'ContentAligner',
    'align_content_to_blocks',
    'fuzzy_match_content',
    'AssociationManager',
    'load_associations_for_pdf',
    'track_association_metadata'
]
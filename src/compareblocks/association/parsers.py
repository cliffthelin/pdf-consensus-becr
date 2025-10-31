# src/compareblocks/association/parsers.py
"""
Format-specific parsers for different extract formats (CSV, HTML, JSON, MD, TXT).
Implements content extraction that maintains meaning without formatting.
"""

import csv
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from bs4 import BeautifulSoup
import markdown


@dataclass
class ParsedContent:
    """Represents parsed content from an association file."""
    text_content: str
    format_type: str
    metadata: Dict[str, Any]
    structured_data: Optional[Dict[str, Any]] = None
    sections: Optional[List[Dict[str, Any]]] = None


class FormatParser(ABC):
    """Abstract base class for format-specific parsers."""
    
    @abstractmethod
    def parse(self, content: str, file_path: Optional[str] = None) -> ParsedContent:
        """Parse content and extract meaningful text."""
        pass
    
    @abstractmethod
    def get_format_type(self) -> str:
        """Return the format type this parser handles."""
        pass


class CSVParser(FormatParser):
    """Parser for CSV files - extracts tabular data as structured text."""
    
    def parse(self, content: str, file_path: Optional[str] = None) -> ParsedContent:
        """Parse CSV content and extract tabular data."""
        try:
            # Parse CSV content
            lines = content.strip().split('\n')
            reader = csv.reader(lines)
            rows = list(reader)
            
            if not rows:
                return ParsedContent(
                    text_content="",
                    format_type="csv",
                    metadata={"error": "Empty CSV content"}
                )
            
            # Extract text content preserving table structure
            text_parts = []
            headers = rows[0] if rows else []
            
            # Add headers
            if headers:
                text_parts.append(" | ".join(headers))
                text_parts.append("-" * len(" | ".join(headers)))
            
            # Add data rows
            for row in rows[1:]:
                if row:  # Skip empty rows
                    text_parts.append(" | ".join(str(cell) for cell in row))
            
            text_content = "\n".join(text_parts)
            
            # Create structured data
            structured_data = {
                "headers": headers,
                "rows": rows[1:] if len(rows) > 1 else [],
                "row_count": len(rows) - 1 if len(rows) > 1 else 0,
                "column_count": len(headers)
            }
            
            return ParsedContent(
                text_content=text_content,
                format_type="csv",
                metadata={
                    "rows": len(rows),
                    "columns": len(headers),
                    "has_headers": bool(headers)
                },
                structured_data=structured_data
            )
            
        except Exception as e:
            return ParsedContent(
                text_content=content,  # Fallback to raw content
                format_type="csv",
                metadata={"error": f"CSV parsing failed: {e}"}
            )
    
    def get_format_type(self) -> str:
        return "csv"


class HTMLParser(FormatParser):
    """Parser for HTML files - extracts text content while preserving structure."""
    
    def parse(self, content: str, file_path: Optional[str] = None) -> ParsedContent:
        """Parse HTML content and extract meaningful text."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text content
            text_content = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text_content.splitlines())
            text_content = '\n'.join(line for line in lines if line)
            
            # Extract structured information
            sections = []
            
            # Extract headings and their content
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                sections.append({
                    "type": "heading",
                    "level": int(heading.name[1]),
                    "text": heading.get_text().strip(),
                    "tag": heading.name
                })
            
            # Extract paragraphs
            for para in soup.find_all('p'):
                para_text = para.get_text().strip()
                if para_text:
                    sections.append({
                        "type": "paragraph",
                        "text": para_text
                    })
            
            # Extract tables
            for table in soup.find_all('table'):
                table_data = []
                for row in table.find_all('tr'):
                    row_data = [cell.get_text().strip() for cell in row.find_all(['td', 'th'])]
                    if row_data:
                        table_data.append(row_data)
                
                if table_data:
                    sections.append({
                        "type": "table",
                        "data": table_data,
                        "rows": len(table_data),
                        "columns": len(table_data[0]) if table_data else 0
                    })
            
            return ParsedContent(
                text_content=text_content,
                format_type="html",
                metadata={
                    "headings": len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
                    "paragraphs": len(soup.find_all('p')),
                    "tables": len(soup.find_all('table')),
                    "links": len(soup.find_all('a'))
                },
                sections=sections
            )
            
        except Exception as e:
            return ParsedContent(
                text_content=content,  # Fallback to raw content
                format_type="html",
                metadata={"error": f"HTML parsing failed: {e}"}
            )
    
    def get_format_type(self) -> str:
        return "html"


class JSONParser(FormatParser):
    """Parser for JSON files - extracts structured data as readable text."""
    
    def parse(self, content: str, file_path: Optional[str] = None) -> ParsedContent:
        """Parse JSON content and extract structured data."""
        try:
            data = json.loads(content)
            
            # Extract text content from JSON structure
            text_parts = []
            self._extract_text_from_json(data, text_parts)
            text_content = "\n".join(text_parts)
            
            # Create sections from JSON structure
            sections = []
            self._create_sections_from_json(data, sections)
            
            return ParsedContent(
                text_content=text_content,
                format_type="json",
                metadata={
                    "json_keys": self._count_keys(data),
                    "json_depth": self._calculate_depth(data),
                    "has_arrays": self._has_arrays(data)
                },
                structured_data=data,
                sections=sections
            )
            
        except json.JSONDecodeError as e:
            return ParsedContent(
                text_content=content,  # Fallback to raw content
                format_type="json",
                metadata={"error": f"JSON parsing failed: {e}"}
            )
    
    def _extract_text_from_json(self, obj: Any, text_parts: List[str], prefix: str = "") -> None:
        """Recursively extract text content from JSON object."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and value.strip():
                    text_parts.append(f"{prefix}{key}: {value}")
                elif isinstance(value, (dict, list)):
                    self._extract_text_from_json(value, text_parts, f"{prefix}{key}.")
                else:
                    text_parts.append(f"{prefix}{key}: {str(value)}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._extract_text_from_json(item, text_parts, f"{prefix}[{i}].")
        elif isinstance(obj, str) and obj.strip():
            text_parts.append(f"{prefix}{obj}")
    
    def _create_sections_from_json(self, obj: Any, sections: List[Dict], path: str = "") -> None:
        """Create sections from JSON structure."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, str) and value.strip():
                    sections.append({
                        "type": "text",
                        "path": current_path,
                        "text": value
                    })
                elif isinstance(value, (dict, list)):
                    self._create_sections_from_json(value, sections, current_path)
    
    def _count_keys(self, obj: Any) -> int:
        """Count total keys in JSON object."""
        if isinstance(obj, dict):
            return len(obj) + sum(self._count_keys(v) for v in obj.values())
        elif isinstance(obj, list):
            return sum(self._count_keys(item) for item in obj)
        return 0
    
    def _calculate_depth(self, obj: Any) -> int:
        """Calculate maximum depth of JSON object."""
        if isinstance(obj, dict):
            return 1 + max((self._calculate_depth(v) for v in obj.values()), default=0)
        elif isinstance(obj, list):
            return 1 + max((self._calculate_depth(item) for item in obj), default=0)
        return 0
    
    def _has_arrays(self, obj: Any) -> bool:
        """Check if JSON contains arrays."""
        if isinstance(obj, list):
            return True
        elif isinstance(obj, dict):
            return any(self._has_arrays(v) for v in obj.values())
        return False
    
    def get_format_type(self) -> str:
        return "json"


class MarkdownParser(FormatParser):
    """Parser for Markdown files - extracts text while preserving structure."""
    
    def parse(self, content: str, file_path: Optional[str] = None) -> ParsedContent:
        """Parse Markdown content and extract structured text."""
        try:
            # Convert markdown to HTML first, then extract text
            html_content = markdown.markdown(content)
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text_content.splitlines())
            text_content = '\n'.join(line for line in lines if line)
            
            # Extract markdown-specific sections
            sections = []
            
            # Extract headers
            header_pattern = r'^(#{1,6})\s+(.+)$'
            for line in content.split('\n'):
                match = re.match(header_pattern, line.strip())
                if match:
                    level = len(match.group(1))
                    text = match.group(2)
                    sections.append({
                        "type": "heading",
                        "level": level,
                        "text": text
                    })
            
            # Extract code blocks
            code_pattern = r'```(\w+)?\n(.*?)\n```'
            for match in re.finditer(code_pattern, content, re.DOTALL):
                language = match.group(1) or "text"
                code = match.group(2)
                sections.append({
                    "type": "code_block",
                    "language": language,
                    "text": code
                })
            
            # Extract lists
            list_pattern = r'^[\s]*[-*+]\s+(.+)$'
            for line in content.split('\n'):
                match = re.match(list_pattern, line)
                if match:
                    sections.append({
                        "type": "list_item",
                        "text": match.group(1)
                    })
            
            return ParsedContent(
                text_content=text_content,
                format_type="markdown",
                metadata={
                    "headers": len([s for s in sections if s["type"] == "heading"]),
                    "code_blocks": len([s for s in sections if s["type"] == "code_block"]),
                    "list_items": len([s for s in sections if s["type"] == "list_item"])
                },
                sections=sections
            )
            
        except Exception as e:
            return ParsedContent(
                text_content=content,  # Fallback to raw content
                format_type="markdown",
                metadata={"error": f"Markdown parsing failed: {e}"}
            )
    
    def get_format_type(self) -> str:
        return "markdown"


class TextParser(FormatParser):
    """Parser for plain text files - basic text processing."""
    
    def parse(self, content: str, file_path: Optional[str] = None) -> ParsedContent:
        """Parse plain text content."""
        # Clean up content
        text_content = content.strip()
        
        # Basic text analysis
        lines = text_content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Extract basic sections (paragraphs separated by empty lines)
        sections = []
        current_paragraph = []
        
        for line in lines:
            if line.strip():
                current_paragraph.append(line.strip())
            else:
                if current_paragraph:
                    sections.append({
                        "type": "paragraph",
                        "text": " ".join(current_paragraph)
                    })
                    current_paragraph = []
        
        # Add final paragraph if exists
        if current_paragraph:
            sections.append({
                "type": "paragraph", 
                "text": " ".join(current_paragraph)
            })
        
        return ParsedContent(
            text_content=text_content,
            format_type="text",
            metadata={
                "total_lines": len(lines),
                "non_empty_lines": len(non_empty_lines),
                "paragraphs": len(sections),
                "character_count": len(text_content),
                "word_count": len(text_content.split())
            },
            sections=sections
        )
    
    def get_format_type(self) -> str:
        return "text"


# Parser registry
_PARSERS = {
    'csv': CSVParser(),
    'html': HTMLParser(),
    'json': JSONParser(),
    'md': MarkdownParser(),
    'markdown': MarkdownParser(),
    'txt': TextParser(),
    'text': TextParser()
}


def detect_format(file_path: str) -> str:
    """Detect format from file extension."""
    path = Path(file_path)
    extension = path.suffix.lower().lstrip('.')
    
    # Map extensions to format types
    format_mapping = {
        'csv': 'csv',
        'html': 'html',
        'htm': 'html',
        'json': 'json',
        'md': 'md',
        'markdown': 'md',
        'txt': 'txt',
        'text': 'txt'
    }
    
    return format_mapping.get(extension, 'txt')


def parse_association_file(file_path: str, content: Optional[str] = None) -> ParsedContent:
    """Parse an association file using the appropriate format parser."""
    if content is None:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    
    format_type = detect_format(file_path)
    parser = _PARSERS.get(format_type, _PARSERS['txt'])
    
    return parser.parse(content, file_path)


def get_available_parsers() -> Dict[str, FormatParser]:
    """Get all available parsers."""
    return _PARSERS.copy()


def register_parser(format_type: str, parser: FormatParser) -> None:
    """Register a new parser for a format type."""
    _PARSERS[format_type] = parser
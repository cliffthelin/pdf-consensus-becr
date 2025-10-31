# tests/unit/test_association_parsers.py
"""
Tests for association format parsers using real association files.
Tests all parsers with actual extracted content from the default PDF.
"""

import pytest
from pathlib import Path

from compareblocks.association.parsers import (
    parse_association_file,
    detect_format,
    CSVParser,
    HTMLParser,
    JSONParser,
    MarkdownParser,
    TextParser,
    get_available_parsers
)
from compareblocks.config.file_manager import FileManager


class TestAssociationParsers:
    """Test association parsers with real files."""
    
    def setup_method(self):
        """Setup test environment with real association files."""
        self.file_manager = FileManager()
        self.pdf_path = Path(self.file_manager.get_target_pdf_path())
        self.association_dir = self.pdf_path.parent
        
        # Find all association files
        self.association_files = []
        for file_path in self.association_dir.glob("-English Language Arts Standards*"):
            if file_path.suffix in ['.csv', '.json', '.txt', '.html', '.md'] and file_path.is_file():
                self.association_files.append(file_path)
        
        assert len(self.association_files) > 0, "No association files found for testing"
        print(f"Found {len(self.association_files)} association files for testing")
    
    def test_format_detection(self):
        """Test format detection from file extensions."""
        test_cases = [
            ("file.csv", "csv"),
            ("file.html", "html"),
            ("file.htm", "html"),
            ("file.json", "json"),
            ("file.md", "md"),
            ("file.markdown", "md"),
            ("file.txt", "txt"),
            ("file.text", "txt"),
            ("file.unknown", "txt")  # Default fallback
        ]
        
        for file_path, expected_format in test_cases:
            detected = detect_format(file_path)
            assert detected == expected_format, f"Expected {expected_format}, got {detected} for {file_path}"
        
        print("✅ Format detection working correctly")
    
    def test_csv_parser_with_real_file(self):
        """Test CSV parser with real association file."""
        csv_files = [f for f in self.association_files if f.suffix == '.csv']
        if not csv_files:
            pytest.skip("No CSV association files found")
        
        csv_file = csv_files[0]
        print(f"Testing CSV parser with: {csv_file.name}")
        
        parsed = parse_association_file(str(csv_file))
        
        assert parsed.format_type == "csv"
        assert len(parsed.text_content) > 0
        assert "rows" in parsed.metadata
        assert "columns" in parsed.metadata
        
        # Should have structured data
        if parsed.structured_data:
            assert "headers" in parsed.structured_data
            assert "rows" in parsed.structured_data
        
        print(f"✅ CSV parser working - {parsed.metadata['rows']} rows, {parsed.metadata['columns']} columns")
    
    def test_html_parser_with_real_file(self):
        """Test HTML parser with real association file."""
        html_files = [f for f in self.association_files if f.suffix == '.html']
        if not html_files:
            pytest.skip("No HTML association files found")
        
        html_file = html_files[0]
        print(f"Testing HTML parser with: {html_file.name}")
        
        parsed = parse_association_file(str(html_file))
        
        assert parsed.format_type == "html"
        assert len(parsed.text_content) > 0
        assert "headings" in parsed.metadata
        assert "paragraphs" in parsed.metadata
        
        # Should have sections
        if parsed.sections:
            assert len(parsed.sections) > 0
            section_types = [s["type"] for s in parsed.sections]
            assert any(t in ["heading", "paragraph", "table"] for t in section_types)
        
        print(f"✅ HTML parser working - {parsed.metadata['headings']} headings, {parsed.metadata['paragraphs']} paragraphs")
    
    def test_json_parser_with_real_file(self):
        """Test JSON parser with real association file."""
        json_files = [f for f in self.association_files if f.suffix == '.json']
        if not json_files:
            pytest.skip("No JSON association files found")
        
        json_file = json_files[0]
        print(f"Testing JSON parser with: {json_file.name}")
        
        parsed = parse_association_file(str(json_file))
        
        assert parsed.format_type == "json"
        assert len(parsed.text_content) > 0
        assert "json_keys" in parsed.metadata
        assert "json_depth" in parsed.metadata
        
        # Should have structured data
        assert parsed.structured_data is not None, f"Expected parsed.structured_data to not be None"
        
        print(f"✅ JSON parser working - {parsed.metadata['json_keys']} keys, depth {parsed.metadata['json_depth']}")
    
    def test_markdown_parser_with_real_file(self):
        """Test Markdown parser with real association file."""
        md_files = [f for f in self.association_files if f.suffix == '.md']
        if not md_files:
            pytest.skip("No Markdown association files found")
        
        md_file = md_files[0]
        print(f"Testing Markdown parser with: {md_file.name}")
        
        parsed = parse_association_file(str(md_file))
        
        assert parsed.format_type == "markdown"
        assert len(parsed.text_content) > 0
        assert "headers" in parsed.metadata
        
        # Should have sections
        if parsed.sections:
            assert len(parsed.sections) > 0
        
        print(f"✅ Markdown parser working - {parsed.metadata['headers']} headers")
    
    def test_text_parser_with_real_file(self):
        """Test Text parser with real association file."""
        txt_files = [f for f in self.association_files if f.suffix == '.txt']
        if not txt_files:
            pytest.skip("No TXT association files found")
        
        txt_file = txt_files[0]
        print(f"Testing Text parser with: {txt_file.name}")
        
        parsed = parse_association_file(str(txt_file))
        
        assert parsed.format_type == "text"
        assert len(parsed.text_content) > 0
        assert "total_lines" in parsed.metadata
        assert "word_count" in parsed.metadata
        assert "character_count" in parsed.metadata
        
        print(f"✅ Text parser working - {parsed.metadata['word_count']} words, {parsed.metadata['character_count']} characters")
    
    def test_all_association_files_parsing(self):
        """Test that all association files can be parsed successfully."""
        results = {}
        
        for file_path in self.association_files:
            print(f"Parsing {file_path.name}...")
            
            try:
                parsed = parse_association_file(str(file_path))
                
                results[file_path.name] = {
                    "format": parsed.format_type,
                    "text_length": len(parsed.text_content),
                    "has_metadata": bool(parsed.metadata),
                    "has_sections": bool(parsed.sections),
                    "has_structured_data": bool(parsed.structured_data),
                    "success": True
                }
                
                # Basic validation
                assert len(parsed.text_content) > 0, f"No text content extracted from {file_path.name}"
                assert parsed.format_type in ["csv", "html", "json", "markdown", "text"], f"Invalid format type: {parsed.format_type}"
                
            except Exception as e:
                results[file_path.name] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"❌ Failed to parse {file_path.name}: {e}")
        
        # Print summary
        successful = sum(1 for r in results.values() if r.get("success", False))
        total = len(results)
        
        print(f"\n📊 Parsing Results Summary:")
        print(f"   - Total files: {total}")
        print(f"   - Successfully parsed: {successful}")
        print(f"   - Failed: {total - successful}")
        
        for file_name, result in results.items():
            if result.get("success"):
                print(f"   ✅ {file_name}: {result['format']} format, {result['text_length']} chars")
            else:
                print(f"   ❌ {file_name}: {result.get('error', 'Unknown error')}")
        
        # Ensure all files parsed successfully
        assert successful == total, f"Only {successful}/{total} files parsed successfully"
        
        print(f"✅ All {total} association files parsed successfully!")
    
    def test_parser_registry(self):
        """Test parser registry functionality."""
        parsers = get_available_parsers()
        
        expected_parsers = ['csv', 'html', 'json', 'md', 'markdown', 'txt', 'text']
        for parser_type in expected_parsers:
            assert parser_type in parsers, f"Parser {parser_type} not found in registry"
        
        # Test each parser type
        for parser_type, parser in parsers.items():
            assert hasattr(parser, 'parse'), f"Parser {parser_type} missing parse method"
            assert hasattr(parser, 'get_format_type'), f"Parser {parser_type} missing get_format_type method"
            assert parser.get_format_type() in ["csv", "html", "json", "markdown", "text"], f"Invalid format type from {parser_type}"
        
        print(f"✅ Parser registry working - {len(parsers)} parsers available")
    
    def test_error_handling(self):
        """Test error handling with malformed content."""
        # Test with invalid JSON
        json_parser = JSONParser()
        result = json_parser.parse("invalid json content")
        assert result.format_type == "json"
        assert "error" in result.metadata
        assert "JSON parsing failed" in result.metadata["error"]
        
        # Test with empty content
        text_parser = TextParser()
        result = text_parser.parse("")
        assert result.format_type == "text"
        assert result.text_content == ""
        
        print("✅ Error handling working correctly")


if __name__ == "__main__":
    # Run tests directly
    test = TestAssociationParsers()
    test.setup_method()
    
    print("Testing association parsers with real files...")
    test.test_format_detection()
    test.test_all_association_files_parsing()
    test.test_parser_registry()
    test.test_error_handling()
    
    print("\n🎉 All association parser tests passed!")
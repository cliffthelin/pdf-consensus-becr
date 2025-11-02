# tests/unit/test_extraction_version_manager.py
"""
Tests for extraction version management system.
Tests version tracking for multiple extractions from same engine with different configurations.
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from compareblocks.project.extraction_version_manager import (
    ExtractionVersionManager,
    ExtractionMetadata,
    ExtractionVersion,
    EngineExtractionHistory,
    ExtractionFormat,
    register_extraction,
    get_engine_extraction_history,
    get_version_summary
)


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_extraction_file(temp_storage_dir):
    """Create a sample extraction NDJSON file."""
    file_path = Path(temp_storage_dir) / "test_extraction.ndjson"
    
    # Write sample NDJSON data
    blocks = [
        {"block_id": "block_0", "text": "Sample text 1", "bbox": [0, 0, 100, 20]},
        {"block_id": "block_1", "text": "Sample text 2", "bbox": [0, 20, 100, 40]},
        {"block_id": "block_2", "text": "Sample text 3", "bbox": [0, 40, 100, 60]}
    ]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        for block in blocks:
            f.write(json.dumps(block) + '\n')
    
    return str(file_path)


@pytest.fixture
def sample_configuration():
    """Sample engine configuration."""
    return {
        "dpi": 300,
        "language": "eng",
        "psm": 3,
        "oem": 1,
        "preprocessing": {
            "denoise": True,
            "threshold": 128
        }
    }


@pytest.fixture
def version_manager(temp_storage_dir):
    """Create extraction version manager with temp storage."""
    return ExtractionVersionManager(storage_directory=temp_storage_dir)


class TestExtractionVersionManager:
    """Test extraction version manager functionality."""
    
    def test_initialization(self, version_manager, temp_storage_dir):
        """Test version manager initialization."""
        assert version_manager.storage_dir == Path(temp_storage_dir)
        assert version_manager.metadata_file.exists() or not version_manager.metadata_file.exists()
        assert isinstance(version_manager._metadata_cache, dict)
        assert isinstance(version_manager._version_cache, dict)
        assert isinstance(version_manager._history_cache, dict)
    
    def test_register_extraction(self, version_manager, sample_extraction_file, sample_configuration):
        """Test registering a new extraction."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        metadata = version_manager.register_extraction(
            file_path=sample_extraction_file,
            engine_name=engine_name,
            configuration=sample_configuration,
            pdf_source=pdf_source,
            tags=["test", "initial"],
            notes="Test extraction"
        )
        
        assert metadata.file_path == sample_extraction_file
        assert metadata.engine_name == engine_name
        assert metadata.pdf_source == pdf_source
        assert metadata.block_count == 3
        assert metadata.file_format == ExtractionFormat.NDJSON
        assert metadata.version_number == 1
        assert "test" in metadata.tags
        assert metadata.notes == "Test extraction"
        assert len(metadata.configuration_hash) > 0
        assert len(metadata.checksum) > 0
    
    def test_register_multiple_extractions_same_config(self, version_manager, temp_storage_dir, 
                                                       sample_configuration):
        """Test registering multiple extractions with same configuration."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        # Create multiple extraction files
        extractions = []
        for i in range(3):
            file_path = Path(temp_storage_dir) / f"extraction_{i}.ndjson"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
            
            metadata = version_manager.register_extraction(
                file_path=str(file_path),
                engine_name=engine_name,
                configuration=sample_configuration,
                pdf_source=pdf_source
            )
            extractions.append(metadata)
        
        # All should have same config hash but different version numbers
        assert extractions[0].configuration_hash == extractions[1].configuration_hash
        assert extractions[0].configuration_hash == extractions[2].configuration_hash
        assert extractions[0].version_number == 1
        assert extractions[1].version_number == 2
        assert extractions[2].version_number == 3
    
    def test_register_extractions_different_configs(self, version_manager, temp_storage_dir):
        """Test registering extractions with different configurations."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        configs = [
            {"dpi": 300, "language": "eng"},
            {"dpi": 600, "language": "eng"},
            {"dpi": 300, "language": "fra"}
        ]
        
        extractions = []
        for i, config in enumerate(configs):
            file_path = Path(temp_storage_dir) / f"extraction_{i}.ndjson"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
            
            metadata = version_manager.register_extraction(
                file_path=str(file_path),
                engine_name=engine_name,
                configuration=config,
                pdf_source=pdf_source
            )
            extractions.append(metadata)
        
        # All should have different config hashes
        assert extractions[0].configuration_hash != extractions[1].configuration_hash
        assert extractions[0].configuration_hash != extractions[2].configuration_hash
        assert extractions[1].configuration_hash != extractions[2].configuration_hash
        
        # All should be version 1 (different configs)
        assert all(e.version_number == 1 for e in extractions)
    
    def test_get_extraction_metadata(self, version_manager, sample_extraction_file, sample_configuration):
        """Test retrieving extraction metadata."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        # Register extraction
        original_metadata = version_manager.register_extraction(
            file_path=sample_extraction_file,
            engine_name=engine_name,
            configuration=sample_configuration,
            pdf_source=pdf_source
        )
        
        # Retrieve metadata
        retrieved_metadata = version_manager.get_extraction_metadata(sample_extraction_file)
        
        assert retrieved_metadata is not None
        assert retrieved_metadata.file_path == original_metadata.file_path
        assert retrieved_metadata.engine_name == original_metadata.engine_name
        assert retrieved_metadata.configuration_hash == original_metadata.configuration_hash
    
    def test_get_engine_history(self, version_manager, temp_storage_dir, sample_configuration):
        """Test getting engine extraction history."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        # Register multiple extractions
        for i in range(3):
            file_path = Path(temp_storage_dir) / f"extraction_{i}.ndjson"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
            
            version_manager.register_extraction(
                file_path=str(file_path),
                engine_name=engine_name,
                configuration=sample_configuration,
                pdf_source=pdf_source
            )
        
        # Get history
        history = version_manager.get_engine_history(engine_name, pdf_source)
        
        assert history.engine_name == engine_name
        assert history.pdf_path == pdf_source
        assert history.total_extractions == 3
        assert history.active_version_id is not None
    
    def test_get_extractions_by_engine(self, version_manager, temp_storage_dir, sample_configuration):
        """Test getting all extractions for an engine."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        # Register extractions
        for i in range(3):
            file_path = Path(temp_storage_dir) / f"extraction_{i}.ndjson"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
            
            version_manager.register_extraction(
                file_path=str(file_path),
                engine_name=engine_name,
                configuration=sample_configuration,
                pdf_source=pdf_source
            )
        
        # Get extractions
        extractions = version_manager.get_extractions_by_engine(engine_name, pdf_source)
        
        assert len(extractions) == 3
        assert all(e.engine_name == engine_name for e in extractions)
        assert all(e.pdf_source == pdf_source for e in extractions)
    
    def test_get_extractions_by_configuration(self, version_manager, temp_storage_dir):
        """Test getting extractions by specific configuration."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        config1 = {"dpi": 300}
        config2 = {"dpi": 600}
        
        # Register extractions with different configs
        for i in range(2):
            file_path = Path(temp_storage_dir) / f"extraction_config1_{i}.ndjson"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
            
            version_manager.register_extraction(
                file_path=str(file_path),
                engine_name=engine_name,
                configuration=config1,
                pdf_source=pdf_source
            )
        
        for i in range(3):
            file_path = Path(temp_storage_dir) / f"extraction_config2_{i}.ndjson"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
            
            version_manager.register_extraction(
                file_path=str(file_path),
                engine_name=engine_name,
                configuration=config2,
                pdf_source=pdf_source
            )
        
        # Get config hash for config1
        config1_hash = version_manager._calculate_configuration_hash(config1)
        
        # Get extractions for config1
        config1_extractions = version_manager.get_extractions_by_configuration(
            engine_name, pdf_source, config1_hash
        )
        
        assert len(config1_extractions) == 2
        assert all(e.configuration_hash == config1_hash for e in config1_extractions)
    
    def test_compare_configurations(self, version_manager, temp_storage_dir):
        """Test comparing two configurations."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        config1 = {"dpi": 300, "language": "eng", "psm": 3}
        config2 = {"dpi": 600, "language": "eng", "psm": 4}
        
        # Register extractions
        file1 = Path(temp_storage_dir) / "extraction1.ndjson"
        file2 = Path(temp_storage_dir) / "extraction2.ndjson"
        
        for file_path in [file1, file2]:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": "block_0", "text": "Text"}) + '\n')
        
        metadata1 = version_manager.register_extraction(
            str(file1), engine_name, config1, pdf_source
        )
        metadata2 = version_manager.register_extraction(
            str(file2), engine_name, config2, pdf_source
        )
        
        # Compare configurations
        comparison = version_manager.compare_configurations(
            metadata1.configuration_hash,
            metadata2.configuration_hash
        )
        
        assert "differences" in comparison
        assert "dpi" in comparison["differences"]
        assert "psm" in comparison["differences"]
        assert "language" not in comparison["differences"]  # Same value
        assert comparison["total_differences"] == 2
    
    def test_find_similar_extractions(self, version_manager, temp_storage_dir):
        """Test finding extractions with similar configurations."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        # Base config
        base_config = {"dpi": 300, "language": "eng", "psm": 3, "oem": 1}
        
        # Similar configs (1 difference each)
        similar_config1 = {"dpi": 600, "language": "eng", "psm": 3, "oem": 1}
        similar_config2 = {"dpi": 300, "language": "fra", "psm": 3, "oem": 1}
        
        # Very different config
        different_config = {"dpi": 150, "language": "deu", "psm": 6, "oem": 3}
        
        # Register extractions
        files = []
        configs = [base_config, similar_config1, similar_config2, different_config]
        
        for i, config in enumerate(configs):
            file_path = Path(temp_storage_dir) / f"extraction_{i}.ndjson"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
            
            version_manager.register_extraction(
                str(file_path), engine_name, config, pdf_source
            )
            files.append(str(file_path))
        
        # Find similar to base config
        similar = version_manager.find_similar_extractions(files[0], similarity_threshold=0.7)
        
        # Should find the two similar configs but not the very different one
        assert len(similar) >= 2
        assert files[1] in [path for path, _ in similar]
        assert files[2] in [path for path, _ in similar]
    
    def test_get_version_summary(self, version_manager, temp_storage_dir):
        """Test getting version summary."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        config1 = {"dpi": 300}
        config2 = {"dpi": 600}
        
        # Register multiple extractions with different configs
        for i in range(2):
            file_path = Path(temp_storage_dir) / f"extraction_c1_{i}.ndjson"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
            
            version_manager.register_extraction(
                str(file_path), engine_name, config1, pdf_source
            )
        
        for i in range(3):
            file_path = Path(temp_storage_dir) / f"extraction_c2_{i}.ndjson"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
            
            version_manager.register_extraction(
                str(file_path), engine_name, config2, pdf_source
            )
        
        # Get summary
        summary = version_manager.get_version_summary(engine_name, pdf_source)
        
        assert summary["engine_name"] == engine_name
        assert summary["pdf_path"] == pdf_source
        assert summary["total_extractions"] == 5
        assert summary["unique_configurations"] == 2
        assert len(summary["configuration_groups"]) == 2
    
    def test_cleanup_old_extractions(self, version_manager, temp_storage_dir, sample_configuration):
        """Test cleaning up old extraction files."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        # Register 5 extractions with same config
        files = []
        for i in range(5):
            file_path = Path(temp_storage_dir) / f"extraction_{i}.ndjson"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
            
            version_manager.register_extraction(
                str(file_path), engine_name, sample_configuration, pdf_source
            )
            files.append(file_path)
        
        # Verify all files exist
        assert all(f.exists() for f in files)
        
        # Cleanup, keeping only 3 most recent
        removed_count = version_manager.cleanup_old_extractions(
            engine_name, pdf_source, keep_per_config=3
        )
        
        assert removed_count == 2
        
        # Verify only 3 files remain
        remaining_files = [f for f in files if f.exists()]
        assert len(remaining_files) == 3
    
    def test_persistence(self, version_manager, sample_extraction_file, sample_configuration):
        """Test that data persists across manager instances."""
        pdf_source = "test_document.pdf"
        engine_name = "tesseract"
        
        # Register extraction
        metadata1 = version_manager.register_extraction(
            sample_extraction_file, engine_name, sample_configuration, pdf_source
        )
        
        # Create new manager instance with same storage
        new_manager = ExtractionVersionManager(storage_directory=str(version_manager.storage_dir))
        
        # Retrieve metadata
        metadata2 = new_manager.get_extraction_metadata(sample_extraction_file)
        
        assert metadata2 is not None
        assert metadata2.file_path == metadata1.file_path
        assert metadata2.configuration_hash == metadata1.configuration_hash
        assert metadata2.version_number == metadata1.version_number


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_register_extraction_function(self, temp_storage_dir, sample_configuration):
        """Test register_extraction convenience function."""
        # Create sample file
        file_path = Path(temp_storage_dir) / "test.ndjson"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps({"block_id": "block_0", "text": "Text"}) + '\n')
        
        # Use convenience function
        metadata = register_extraction(
            str(file_path),
            "tesseract",
            sample_configuration,
            "test.pdf",
            tags=["test"],
            notes="Test note"
        )
        
        assert metadata.file_path == str(file_path)
        assert metadata.engine_name == "tesseract"
        assert "test" in metadata.tags
    
    def test_get_engine_extraction_history_function(self, temp_storage_dir, sample_configuration):
        """Test get_engine_extraction_history convenience function."""
        # Create and register extraction
        file_path = Path(temp_storage_dir) / "test.ndjson"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps({"block_id": "block_0", "text": "Text"}) + '\n')
        
        register_extraction(str(file_path), "tesseract", sample_configuration, "test.pdf")
        
        # Get history
        history = get_engine_extraction_history("tesseract", "test.pdf")
        
        assert history.engine_name == "tesseract"
        assert history.pdf_path == "test.pdf"
        assert history.total_extractions >= 1
    
    def test_get_version_summary_function(self, temp_storage_dir, sample_configuration):
        """Test get_version_summary convenience function."""
        # Create and register extraction
        file_path = Path(temp_storage_dir) / "test.ndjson"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps({"block_id": "block_0", "text": "Text"}) + '\n')
        
        register_extraction(str(file_path), "tesseract", sample_configuration, "test.pdf")
        
        # Get summary
        summary = get_version_summary("tesseract", "test.pdf")
        
        assert summary["engine_name"] == "tesseract"
        assert summary["pdf_path"] == "test.pdf"
        assert summary["total_extractions"] >= 1


class TestFileFormatDetection:
    """Test file format detection."""
    
    def test_detect_ndjson_format(self, version_manager):
        """Test NDJSON format detection."""
        format_type = version_manager._detect_file_format("test.ndjson")
        assert format_type == ExtractionFormat.NDJSON
    
    def test_detect_json_format(self, version_manager):
        """Test JSON format detection."""
        format_type = version_manager._detect_file_format("test.json")
        assert format_type == ExtractionFormat.JSON
    
    def test_detect_csv_format(self, version_manager):
        """Test CSV format detection."""
        format_type = version_manager._detect_file_format("test.csv")
        assert format_type == ExtractionFormat.CSV
    
    def test_detect_html_format(self, version_manager):
        """Test HTML format detection."""
        format_type = version_manager._detect_file_format("test.html")
        assert format_type == ExtractionFormat.HTML
    
    def test_detect_markdown_format(self, version_manager):
        """Test Markdown format detection."""
        format_type = version_manager._detect_file_format("test.md")
        assert format_type == ExtractionFormat.MD


class TestConfigurationHashing:
    """Test configuration hashing."""
    
    def test_same_config_same_hash(self, version_manager):
        """Test that same configuration produces same hash."""
        config = {"dpi": 300, "language": "eng"}
        
        hash1 = version_manager._calculate_configuration_hash(config)
        hash2 = version_manager._calculate_configuration_hash(config)
        
        assert hash1 == hash2
    
    def test_different_config_different_hash(self, version_manager):
        """Test that different configurations produce different hashes."""
        config1 = {"dpi": 300, "language": "eng"}
        config2 = {"dpi": 600, "language": "eng"}
        
        hash1 = version_manager._calculate_configuration_hash(config1)
        hash2 = version_manager._calculate_configuration_hash(config2)
        
        assert hash1 != hash2
    
    def test_key_order_doesnt_matter(self, version_manager):
        """Test that key order doesn't affect hash."""
        config1 = {"dpi": 300, "language": "eng", "psm": 3}
        config2 = {"language": "eng", "psm": 3, "dpi": 300}
        
        hash1 = version_manager._calculate_configuration_hash(config1)
        hash2 = version_manager._calculate_configuration_hash(config2)
        
        assert hash1 == hash2

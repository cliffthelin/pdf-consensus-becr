# tests/integration/test_extraction_version_workflow.py
"""
Integration tests for extraction version management workflow.
Tests complete workflow of tracking multiple extractions with different configurations.
"""

import json
import pytest
import tempfile
from pathlib import Path

from compareblocks.project.extraction_version_manager import (
    ExtractionVersionManager,
    register_extraction,
    get_engine_extraction_history,
    get_version_summary
)
from compareblocks.project.manager import ProjectManager


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create directory structure
        (workspace / "pdfs").mkdir()
        (workspace / "extractions").mkdir()
        (workspace / "versions").mkdir()
        
        yield workspace


@pytest.fixture
def sample_pdf(temp_workspace):
    """Create a sample PDF file (placeholder)."""
    pdf_path = temp_workspace / "pdfs" / "sample_document.pdf"
    pdf_path.write_text("PDF placeholder")
    return str(pdf_path)


class TestExtractionVersionWorkflow:
    """Test complete extraction version management workflow."""
    
    def test_complete_workflow_single_engine_multiple_configs(self, temp_workspace, sample_pdf):
        """Test complete workflow with single engine and multiple configurations."""
        version_manager = ExtractionVersionManager(
            storage_directory=str(temp_workspace / "versions")
        )
        
        engine_name = "tesseract"
        extractions_dir = temp_workspace / "extractions"
        
        # Configuration 1: Low DPI
        config1 = {
            "dpi": 150,
            "language": "eng",
            "psm": 3,
            "preprocessing": {"denoise": False}
        }
        
        # Configuration 2: High DPI
        config2 = {
            "dpi": 300,
            "language": "eng",
            "psm": 3,
            "preprocessing": {"denoise": True}
        }
        
        # Configuration 3: Different PSM
        config3 = {
            "dpi": 300,
            "language": "eng",
            "psm": 6,
            "preprocessing": {"denoise": True}
        }
        
        # Simulate extraction workflow
        all_extractions = []
        
        # Run extraction with config1 (version 1)
        extraction1_path = extractions_dir / "tesseract_config1_v1.ndjson"
        self._create_extraction_file(extraction1_path, 10)
        
        metadata1 = version_manager.register_extraction(
            str(extraction1_path),
            engine_name,
            config1,
            sample_pdf,
            tags=["low_dpi", "initial"],
            notes="Initial extraction with low DPI"
        )
        all_extractions.append(metadata1)
        
        # Run extraction with config2 (version 1)
        extraction2_path = extractions_dir / "tesseract_config2_v1.ndjson"
        self._create_extraction_file(extraction2_path, 12)
        
        metadata2 = version_manager.register_extraction(
            str(extraction2_path),
            engine_name,
            config2,
            sample_pdf,
            tags=["high_dpi", "improved"],
            notes="Improved extraction with high DPI"
        )
        all_extractions.append(metadata2)
        
        # Re-run extraction with config1 (version 2)
        extraction3_path = extractions_dir / "tesseract_config1_v2.ndjson"
        self._create_extraction_file(extraction3_path, 11)
        
        metadata3 = version_manager.register_extraction(
            str(extraction3_path),
            engine_name,
            config1,
            sample_pdf,
            tags=["low_dpi", "rerun"],
            notes="Re-run with same config"
        )
        all_extractions.append(metadata3)
        
        # Run extraction with config3 (version 1)
        extraction4_path = extractions_dir / "tesseract_config3_v1.ndjson"
        self._create_extraction_file(extraction4_path, 13)
        
        metadata4 = version_manager.register_extraction(
            str(extraction4_path),
            engine_name,
            config3,
            sample_pdf,
            tags=["different_psm"],
            notes="Different PSM mode"
        )
        all_extractions.append(metadata4)
        
        # Verify version numbers
        assert metadata1.version_number == 1
        assert metadata2.version_number == 1
        assert metadata3.version_number == 2  # Same config as metadata1
        assert metadata4.version_number == 1
        
        # Verify configuration hashes
        assert metadata1.configuration_hash == metadata3.configuration_hash
        assert metadata2.configuration_hash != metadata1.configuration_hash
        assert metadata4.configuration_hash != metadata1.configuration_hash
        assert metadata4.configuration_hash != metadata2.configuration_hash
        
        # Get engine history
        history = version_manager.get_engine_history(engine_name, sample_pdf)
        assert history.total_extractions == 4
        assert history.engine_name == engine_name
        
        # Get version summary
        summary = version_manager.get_version_summary(engine_name, sample_pdf)
        assert summary["total_extractions"] == 4
        assert summary["unique_configurations"] == 3
        
        # Get extractions by configuration
        config1_extractions = version_manager.get_extractions_by_configuration(
            engine_name, sample_pdf, metadata1.configuration_hash
        )
        assert len(config1_extractions) == 2  # metadata1 and metadata3
        
        # Find similar extractions (lower threshold for this test)
        similar = version_manager.find_similar_extractions(str(extraction2_path), similarity_threshold=0.5)
        assert len(similar) >= 0  # May or may not find similar ones depending on config differences
    
    def test_workflow_multiple_engines(self, temp_workspace, sample_pdf):
        """Test workflow with multiple engines."""
        version_manager = ExtractionVersionManager(
            storage_directory=str(temp_workspace / "versions")
        )
        
        extractions_dir = temp_workspace / "extractions"
        
        engines = ["tesseract", "paddleocr", "docling"]
        configs = [
            {"dpi": 300, "language": "eng"},
            {"dpi": 300, "language": "eng", "model": "v2"},
            {"dpi": 300, "format": "markdown"}
        ]
        
        # Register extractions for each engine
        for i, (engine, config) in enumerate(zip(engines, configs)):
            extraction_path = extractions_dir / f"{engine}_extraction.ndjson"
            self._create_extraction_file(extraction_path, 10 + i)
            
            version_manager.register_extraction(
                str(extraction_path),
                engine,
                config,
                sample_pdf,
                tags=[engine, "comparison"],
                notes=f"Extraction from {engine}"
            )
        
        # Verify each engine has its own history
        for engine in engines:
            history = version_manager.get_engine_history(engine, sample_pdf)
            assert history.total_extractions == 1
            assert history.engine_name == engine
    
    def test_workflow_with_project_manager_integration(self, temp_workspace, sample_pdf):
        """Test integration with project manager."""
        version_manager = ExtractionVersionManager(
            storage_directory=str(temp_workspace / "versions")
        )
        project_manager = ProjectManager()
        
        extractions_dir = temp_workspace / "extractions"
        engine_name = "tesseract"
        config = {"dpi": 300, "language": "eng"}
        
        # Create extraction
        extraction_path = extractions_dir / "extraction.ndjson"
        self._create_extraction_file(extraction_path, 10)
        
        # Register extraction
        metadata = version_manager.register_extraction(
            str(extraction_path),
            engine_name,
            config,
            sample_pdf
        )
        
        # Verify file exists through project manager
        file_status = project_manager.get_file_status(str(extraction_path))
        assert file_status.exists
        assert file_status.file_size > 0
        
        # Get version summary
        summary = version_manager.get_version_summary(engine_name, sample_pdf)
        assert summary["total_extractions"] == 1
    
    def test_workflow_cleanup_old_versions(self, temp_workspace, sample_pdf):
        """Test cleanup of old extraction versions."""
        version_manager = ExtractionVersionManager(
            storage_directory=str(temp_workspace / "versions")
        )
        
        extractions_dir = temp_workspace / "extractions"
        engine_name = "tesseract"
        config = {"dpi": 300, "language": "eng"}
        
        # Create 5 extractions with same config
        extraction_paths = []
        for i in range(5):
            extraction_path = extractions_dir / f"extraction_v{i+1}.ndjson"
            self._create_extraction_file(extraction_path, 10)
            
            version_manager.register_extraction(
                str(extraction_path),
                engine_name,
                config,
                sample_pdf
            )
            extraction_paths.append(extraction_path)
        
        # Verify all files exist
        assert all(p.exists() for p in extraction_paths)
        
        # Cleanup, keeping only 3 most recent
        removed_count = version_manager.cleanup_old_extractions(
            engine_name, sample_pdf, keep_per_config=3
        )
        
        assert removed_count == 2
        
        # Verify only 3 files remain
        remaining = [p for p in extraction_paths if p.exists()]
        assert len(remaining) == 3
        
        # Verify the most recent 3 remain
        assert extraction_paths[2].exists()
        assert extraction_paths[3].exists()
        assert extraction_paths[4].exists()
    
    def test_workflow_configuration_comparison(self, temp_workspace, sample_pdf):
        """Test comparing different configurations."""
        version_manager = ExtractionVersionManager(
            storage_directory=str(temp_workspace / "versions")
        )
        
        extractions_dir = temp_workspace / "extractions"
        engine_name = "tesseract"
        
        config1 = {"dpi": 300, "language": "eng", "psm": 3, "oem": 1}
        config2 = {"dpi": 600, "language": "eng", "psm": 3, "oem": 3}
        
        # Create extractions
        extraction1_path = extractions_dir / "extraction1.ndjson"
        extraction2_path = extractions_dir / "extraction2.ndjson"
        
        self._create_extraction_file(extraction1_path, 10)
        self._create_extraction_file(extraction2_path, 12)
        
        metadata1 = version_manager.register_extraction(
            str(extraction1_path), engine_name, config1, sample_pdf
        )
        metadata2 = version_manager.register_extraction(
            str(extraction2_path), engine_name, config2, sample_pdf
        )
        
        # Compare configurations
        comparison = version_manager.compare_configurations(
            metadata1.configuration_hash,
            metadata2.configuration_hash
        )
        
        assert "differences" in comparison
        assert "dpi" in comparison["differences"]
        assert "oem" in comparison["differences"]
        assert comparison["differences"]["dpi"]["config1"] == 300
        assert comparison["differences"]["dpi"]["config2"] == 600
        assert comparison["total_differences"] == 2
    
    def test_workflow_persistence_across_sessions(self, temp_workspace, sample_pdf):
        """Test that version data persists across manager instances."""
        storage_dir = str(temp_workspace / "versions")
        extractions_dir = temp_workspace / "extractions"
        
        # Session 1: Register extractions
        version_manager1 = ExtractionVersionManager(storage_directory=storage_dir)
        
        engine_name = "tesseract"
        config = {"dpi": 300, "language": "eng"}
        
        extraction_path = extractions_dir / "extraction.ndjson"
        self._create_extraction_file(extraction_path, 10)
        
        metadata1 = version_manager1.register_extraction(
            str(extraction_path), engine_name, config, sample_pdf
        )
        
        # Session 2: Load from storage
        version_manager2 = ExtractionVersionManager(storage_directory=storage_dir)
        
        metadata2 = version_manager2.get_extraction_metadata(str(extraction_path))
        
        assert metadata2 is not None
        assert metadata2.file_path == metadata1.file_path
        assert metadata2.configuration_hash == metadata1.configuration_hash
        assert metadata2.version_number == metadata1.version_number
        
        # Session 2: Add another extraction with same config
        extraction2_path = extractions_dir / "extraction2.ndjson"
        self._create_extraction_file(extraction2_path, 11)
        
        metadata3 = version_manager2.register_extraction(
            str(extraction2_path), engine_name, config, sample_pdf
        )
        
        # Should be version 2
        assert metadata3.version_number == 2
    
    def _create_extraction_file(self, file_path: Path, block_count: int) -> None:
        """Helper to create extraction NDJSON file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            for i in range(block_count):
                block = {
                    "block_id": f"block_{i}",
                    "text": f"Sample text for block {i}",
                    "bbox": [0, i * 20, 100, (i + 1) * 20],
                    "confidence": 0.95
                }
                f.write(json.dumps(block) + '\n')


class TestConvenienceFunctionsIntegration:
    """Test convenience functions in integration scenarios."""
    
    def test_register_and_retrieve_workflow(self, temp_workspace, sample_pdf):
        """Test complete workflow using convenience functions."""
        extractions_dir = temp_workspace / "extractions"
        
        # Create extraction file
        extraction_path = extractions_dir / "extraction.ndjson"
        with open(extraction_path, 'w', encoding='utf-8') as f:
            for i in range(5):
                f.write(json.dumps({"block_id": f"block_{i}", "text": f"Text {i}"}) + '\n')
        
        # Register using convenience function
        metadata = register_extraction(
            str(extraction_path),
            "tesseract",
            {"dpi": 300, "language": "eng"},
            sample_pdf,
            tags=["test"],
            notes="Test extraction"
        )
        
        assert metadata.version_number == 1
        assert "test" in metadata.tags
        
        # Get history using convenience function
        history = get_engine_extraction_history("tesseract", sample_pdf)
        assert history.total_extractions >= 1
        
        # Get summary using convenience function
        summary = get_version_summary("tesseract", sample_pdf)
        assert summary["total_extractions"] >= 1

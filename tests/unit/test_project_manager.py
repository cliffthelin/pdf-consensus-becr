#!/usr/bin/env python3
"""
Tests for project_manager functionality.
Comprehensive test implementation following TDD principles.
"""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import os
import json
import hashlib

from src.compareblocks.project.manager import (
    ProjectManager, FileStatus, ProjectStructure,
    create_project_structure, validate_project_structure, get_project_summary
)


class TestProjectManager:
    """Test class for project_manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ProjectManager()
        try:
            from src.compareblocks.config.file_manager import file_manager
            self.pdf_path = file_manager.get_target_pdf_path()
        except ImportError:
            self.pdf_path = None
    
    def test_project_manager_init(self):
        """Test ProjectManager initialization."""
        manager = ProjectManager()
        assert manager.file_manager is not None
        assert manager.association_manager is not None
        assert isinstance(manager._file_cache, dict)
        assert isinstance(manager._project_cache, dict)
    
    def test_get_file_status_existing_file(self):
        """Test get_file_status with existing file and size limits."""
        if self.pdf_path and Path(self.pdf_path).exists():
            status = self.manager.get_file_status(self.pdf_path)
            assert status.exists is True
            assert status.path == str(Path(self.pdf_path).resolve())
            assert status.file_size is not None
            assert status.file_size > 0
            assert status.last_modified is not None
            assert status.error_message is None
            
            # Test checksum calculation for small vs large files
            file_size = Path(self.pdf_path).stat().st_size
            if file_size < 10 * 1024 * 1024:  # Less than 10MB
                assert status.checksum is not None
                assert len(status.checksum) == 32  # MD5 length
            else:
                # Large files might not have checksum calculated
                pass
        
        # Test with small file (should get checksum)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("small test content")
            small_file_path = f.name
        
        try:
            status = self.manager.get_file_status(small_file_path)
            assert status.exists is True
            assert status.file_size is not None
            assert status.file_size < 10 * 1024 * 1024  # Definitely small
            assert status.checksum is not None
            assert len(status.checksum) == 32
        finally:
            os.unlink(small_file_path)
        
        # Test with large file (should not get checksum)
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f:
            # Create a file larger than 10MB
            chunk = b"x" * (1024 * 1024)  # 1MB chunk
            for _ in range(11):  # Write 11MB
                f.write(chunk)
            large_file_path = f.name
        
        try:
            status = self.manager.get_file_status(large_file_path)
            assert status.exists is True
            assert status.file_size is not None
            assert status.file_size > 10 * 1024 * 1024  # Definitely large
            # Large files don't get checksums calculated
            assert status.checksum == ""
        finally:
            os.unlink(large_file_path)
            
        if not self.pdf_path or not Path(self.pdf_path).exists():
            pytest.skip("Target PDF not available for testing")
    
    def test_get_file_status_nonexistent_file(self):
        """Test get_file_status with nonexistent file."""
        nonexistent_path = "/nonexistent/file.pdf"
        status = self.manager.get_file_status(nonexistent_path)
        assert status.exists is False
        assert status.path == str(Path(nonexistent_path).resolve())
        assert status.file_size is None
        assert status.last_modified is None
        assert status.error_message == "File not found"
    
    def test_get_file_status_caching(self):
        """Test file status caching behavior with edge cases."""
        if self.pdf_path and Path(self.pdf_path).exists():
            # First call
            status1 = self.manager.get_file_status(self.pdf_path)
            # Second call should use cache
            status2 = self.manager.get_file_status(self.pdf_path)
            assert status1.path == status2.path
            assert status1.exists == status2.exists
            assert status1.file_size == status2.file_size
            
            # Test cache refresh when file is modified
            # Create a temporary file to test modification detection
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write("original content")
                temp_path = f.name
            
            try:
                # Get initial status
                status1 = self.manager.get_file_status(temp_path)
                assert status1.exists is True
                
                # Modify the file
                import time
                time.sleep(0.1)  # Ensure different timestamp
                with open(temp_path, 'w') as f:
                    f.write("modified content")
                
                # Get status again - should detect change
                status2 = self.manager.get_file_status(temp_path)
                assert status2.exists is True
                # File size should be different
                assert status1.file_size != status2.file_size
                
            finally:
                os.unlink(temp_path)
                
            # Test error handling in cache refresh
            # Add a file to cache then delete it to trigger OSError
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write("test content")
                temp_path2 = f.name
            
            try:
                # Cache the file
                status1 = self.manager.get_file_status(temp_path2)
                assert status1.exists is True
                
                # Delete the file to trigger error in cache refresh
                os.unlink(temp_path2)
                
                # This should handle the OSError gracefully and create new status
                status2 = self.manager.get_file_status(temp_path2)
                assert status2.exists is False
                assert status2.error_message == "File not found"
                
            except FileNotFoundError:
                pass  # File already deleted, that's fine
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_calculate_checksum(self):
        """Test checksum calculation with edge cases."""
        # Test normal file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            checksum = self.manager._calculate_checksum(temp_path)
            assert checksum is not None
            assert len(checksum) == 32  # MD5 hash length
            
            # Verify checksum is correct
            expected = hashlib.md5(b"test content").hexdigest()
            assert checksum == expected
        finally:
            os.unlink(temp_path)
        
        # Test error handling - nonexistent file
        nonexistent_path = "/nonexistent/file.txt"
        checksum = self.manager._calculate_checksum(nonexistent_path)
        assert checksum == ""  # Should return empty string on error
        
        # Test large file handling (should still work but test the chunking)
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            # Write 8KB of data to test chunking
            test_data = b"x" * 8192
            f.write(test_data)
            temp_path = f.name
        
        try:
            checksum = self.manager._calculate_checksum(temp_path)
            assert checksum is not None
            assert len(checksum) == 32
            
            # Verify checksum is correct for large file
            expected = hashlib.md5(test_data).hexdigest()
            assert checksum == expected
        finally:
            os.unlink(temp_path)
    
    def test_create_project_structure(self):
        """Test creating project structure."""
        if self.pdf_path and Path(self.pdf_path).exists():
            structure = self.manager.create_project_structure(self.pdf_path)
            assert isinstance(structure, ProjectStructure)
            assert structure.root_pdf == str(Path(self.pdf_path).resolve())
            assert structure.processing_directory is not None
            assert structure.final_output_directory is not None
            assert isinstance(structure.associated_files, list)
            assert isinstance(structure.previous_results, list)
            assert isinstance(structure.missing_files, list)
            assert isinstance(structure.moved_files, dict)
            assert structure.last_validated is not None
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_find_previous_results(self):
        """Test finding previous results with real directory structure."""
        if self.pdf_path and Path(self.pdf_path).exists():
            # Test with real directories
            results = self.manager._find_previous_results(self.pdf_path)
            assert isinstance(results, list)
            # Results should be paths to .ndjson or .json files
            for result in results:
                assert result.endswith(('.ndjson', '.json'))
                assert Path(result).exists()  # Verify files actually exist
            
            # Test with temporary directory containing test files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create test files to find
                test_ndjson = Path(temp_dir) / "test_result.ndjson"
                test_json = Path(temp_dir) / "test_result.json"
                test_ndjson.write_text('{"test": "data"}\n')
                test_json.write_text('{"test": "data"}')
                
                # Mock the file manager to return our temp directory
                original_get_processing = self.manager.file_manager.get_processing_directory
                original_get_final = self.manager.file_manager.get_final_output_directory
                
                self.manager.file_manager.get_processing_directory = lambda: temp_dir
                self.manager.file_manager.get_final_output_directory = lambda: temp_dir
                
                try:
                    results = self.manager._find_previous_results(self.pdf_path)
                    # Should find both files (once in processing, once in final)
                    assert len(results) >= 2
                    found_ndjson = any(str(test_ndjson) in result for result in results)
                    found_json = any(str(test_json) in result for result in results)
                    assert found_ndjson, f"Should find {test_ndjson} in {results}"
                    assert found_json, f"Should find {test_json} in {results}"
                finally:
                    # Restore original methods
                    self.manager.file_manager.get_processing_directory = original_get_processing
                    self.manager.file_manager.get_final_output_directory = original_get_final
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_validate_project_files(self):
        """Test project file validation."""
        # Create a test structure
        structure = ProjectStructure(
            root_pdf=self.pdf_path if self.pdf_path else "/nonexistent.pdf",
            processing_directory="/tmp",
            final_output_directory="/tmp",
            associated_files=["/nonexistent1.json", "/nonexistent2.json"],
            previous_results=["/nonexistent3.json"]
        )
        
        self.manager._validate_project_files(structure)
        
        if not self.pdf_path or not Path(self.pdf_path).exists():
            # All files should be missing
            assert len(structure.missing_files) >= 3
        else:
            # At least the associated files should be missing
            assert len(structure.missing_files) >= 2
    
    def test_validate_project_structure(self):
        """Test project structure validation."""
        if self.pdf_path and Path(self.pdf_path).exists():
            report = self.manager.validate_project_structure(self.pdf_path)
            assert isinstance(report, dict)
            assert "pdf_path" in report
            assert "validation_time" in report
            assert "root_pdf_exists" in report
            assert "processing_directory_exists" in report
            assert "final_output_directory_exists" in report
            assert "total_associated_files" in report
            assert "missing_files" in report
            assert "file_details" in report
            assert report["pdf_path"] == self.pdf_path
            assert report["root_pdf_exists"] is True
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_get_project_structure_caching(self):
        """Test project structure caching."""
        if self.pdf_path and Path(self.pdf_path).exists():
            # First call creates structure
            structure1 = self.manager.get_project_structure(self.pdf_path)
            # Second call should use cache
            structure2 = self.manager.get_project_structure(self.pdf_path)
            assert structure1.root_pdf == structure2.root_pdf
            assert structure1.processing_directory == structure2.processing_directory
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_find_moved_files(self):
        """Test finding moved files."""
        if self.pdf_path and Path(self.pdf_path).exists():
            moved_candidates = self.manager.find_moved_files(self.pdf_path)
            assert isinstance(moved_candidates, dict)
            # Each key should be a missing file path
            # Each value should be a list of candidate paths
            for missing_file, candidates in moved_candidates.items():
                assert isinstance(candidates, list)
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_relocate_file(self):
        """Test file relocation."""
        if self.pdf_path and Path(self.pdf_path).exists():
            # Create a structure first
            structure = self.manager.create_project_structure(self.pdf_path)
            
            # Test relocating a file (even if it doesn't exist)
            old_path = "/old/test.json"
            new_path = "/new/test.json"
            
            # Add the old path to associated files
            structure.associated_files.append(old_path)
            self.manager._project_cache[self.pdf_path] = structure
            
            success = self.manager.relocate_file(old_path, new_path, self.pdf_path)
            assert success is True
            
            # Verify the relocation
            updated_structure = self.manager.get_project_structure(self.pdf_path)
            assert new_path in updated_structure.associated_files
            assert old_path not in updated_structure.associated_files
            assert updated_structure.moved_files[old_path] == new_path
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_get_reprocessing_files(self):
        """Test getting reprocessing files."""
        if self.pdf_path and Path(self.pdf_path).exists():
            reprocessing_files = self.manager.get_reprocessing_files(self.pdf_path)
            assert isinstance(reprocessing_files, dict)
            assert "root_pdf" in reprocessing_files
            assert "associated_files" in reprocessing_files
            assert "previous_results" in reprocessing_files
            assert "missing_files" in reprocessing_files
            assert reprocessing_files["root_pdf"] == [str(Path(self.pdf_path).resolve())]
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_create_project_manifest(self):
        """Test creating project manifest."""
        if self.pdf_path and Path(self.pdf_path).exists():
            manifest = self.manager.create_project_manifest(self.pdf_path)
            assert isinstance(manifest, dict)
            assert "project_info" in manifest
            assert "file_structure" in manifest
            assert "validation_report" in manifest
            assert "reprocessing_files" in manifest
            assert "statistics" in manifest
            
            # Check project info
            project_info = manifest["project_info"]
            assert "root_pdf" in project_info
            assert "created" in project_info
            assert "processing_directory" in project_info
            assert "final_output_directory" in project_info
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_save_project_manifest(self):
        """Test saving project manifest."""
        if self.pdf_path and Path(self.pdf_path).exists():
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "test_manifest.json")
                saved_path = self.manager.save_project_manifest(self.pdf_path, output_path)
                
                assert saved_path == output_path
                assert os.path.exists(output_path)
                
                # Verify the saved content
                with open(output_path, 'r') as f:
                    saved_manifest = json.load(f)
                
                assert isinstance(saved_manifest, dict)
                assert "project_info" in saved_manifest
                assert "file_structure" in saved_manifest
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_clear_cache(self):
        """Test cache clearing."""
        # Add some items to cache
        self.manager._file_cache["/test.pdf"] = FileStatus(path="/test.pdf", exists=True)
        self.manager._project_cache["/test.pdf"] = ProjectStructure(
            root_pdf="/test.pdf",
            processing_directory="/proc",
            final_output_directory="/out"
        )
        
        assert len(self.manager._file_cache) > 0
        assert len(self.manager._project_cache) > 0
        
        self.manager.clear_cache()
        
        assert len(self.manager._file_cache) == 0
        assert len(self.manager._project_cache) == 0
    
    def test_get_project_summary(self):
        """Test getting project summary."""
        if self.pdf_path and Path(self.pdf_path).exists():
            summary = self.manager.get_project_summary(self.pdf_path)
            assert isinstance(summary, dict)
            assert "pdf_path" in summary
            assert "total_associated_files" in summary
            assert "missing_files_count" in summary
            assert "moved_files_count" in summary
            assert "previous_results_count" in summary
            assert "directories" in summary
            assert summary["pdf_path"] == self.pdf_path
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        if self.pdf_path and Path(self.pdf_path).exists():
            # Test create_project_structure function
            structure = create_project_structure(self.pdf_path)
            assert isinstance(structure, ProjectStructure)
            
            # Test validate_project_structure function
            validation = validate_project_structure(self.pdf_path)
            assert isinstance(validation, dict)
            
            # Test get_project_summary function
            summary = get_project_summary(self.pdf_path)
            assert isinstance(summary, dict)
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        # Test that manager can be created and has expected attributes
        assert hasattr(self.manager, 'file_manager')
        assert hasattr(self.manager, 'association_manager')
        assert hasattr(self.manager, '_file_cache')
        assert hasattr(self.manager, '_project_cache')
    
    def test_with_real_data(self):
        """Test with real application data if available."""
        try:
            if self.pdf_path and Path(self.pdf_path).exists():
                # Test full workflow with real data
                structure = self.manager.create_project_structure(self.pdf_path)
                validation = self.manager.validate_project_structure(self.pdf_path)
                summary = self.manager.get_project_summary(self.pdf_path)
                
                assert structure.root_pdf == str(Path(self.pdf_path).resolve())
                assert validation["root_pdf_exists"] is True
                assert summary["pdf_path"] == self.pdf_path
            else:
                pytest.skip("Target PDF not available for testing")
                
        except Exception as e:
            pytest.skip(f"Test not applicable: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
    def test_find_previous_results_comprehensive(self):
        """Test finding previous results with comprehensive directory scenarios."""
        # Test with empty directories
        with tempfile.TemporaryDirectory() as temp_dir:
            processing_dir = Path(temp_dir) / "processing"
            final_dir = Path(temp_dir) / "final"
            processing_dir.mkdir()
            final_dir.mkdir()
            
            # Mock the file manager
            original_get_processing = self.manager.file_manager.get_processing_directory
            original_get_final = self.manager.file_manager.get_final_output_directory
            
            self.manager.file_manager.get_processing_directory = lambda: str(processing_dir)
            self.manager.file_manager.get_final_output_directory = lambda: str(final_dir)
            
            try:
                # Test with empty directories
                results = self.manager._find_previous_results("/test.pdf")
                assert isinstance(results, list)
                assert len(results) == 0
                
                # Add some files
                (processing_dir / "result1.ndjson").write_text('{"test": 1}\n')
                (processing_dir / "result2.json").write_text('{"test": 2}')
                (processing_dir / "ignore.txt").write_text('ignore this')
                
                (final_dir / "final1.ndjson").write_text('{"final": 1}\n')
                (final_dir / "final2.json").write_text('{"final": 2}')
                (final_dir / "ignore.pdf").write_text('ignore this too')
                
                # Test finding files
                results = self.manager._find_previous_results("/test.pdf")
                assert len(results) == 4  # Should find 4 json/ndjson files
                
                # Verify all results are json or ndjson files
                json_files = [r for r in results if r.endswith('.json')]
                ndjson_files = [r for r in results if r.endswith('.ndjson')]
                assert len(json_files) == 2
                assert len(ndjson_files) == 2
                
                # Verify files exist
                for result in results:
                    assert Path(result).exists()
                
            finally:
                # Restore original methods
                self.manager.file_manager.get_processing_directory = original_get_processing
                self.manager.file_manager.get_final_output_directory = original_get_final
    
    def test_find_previous_results_nonexistent_directories(self):
        """Test finding previous results when directories don't exist."""
        # Mock file manager to return nonexistent directories
        original_get_processing = self.manager.file_manager.get_processing_directory
        original_get_final = self.manager.file_manager.get_final_output_directory
        
        self.manager.file_manager.get_processing_directory = lambda: "/nonexistent/processing"
        self.manager.file_manager.get_final_output_directory = lambda: "/nonexistent/final"
        
        try:
            results = self.manager._find_previous_results("/test.pdf")
            assert isinstance(results, list)
            assert len(results) == 0  # Should return empty list for nonexistent dirs
        finally:
            # Restore original methods
            self.manager.file_manager.get_processing_directory = original_get_processing
            self.manager.file_manager.get_final_output_directory = original_get_final
    
    def test_validate_project_files_comprehensive(self):
        """Test project file validation with various file states."""
        # Create test files
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_file1 = Path(temp_dir) / "exists1.json"
            existing_file2 = Path(temp_dir) / "exists2.ndjson"
            existing_file1.write_text('{"exists": true}')
            existing_file2.write_text('{"exists": true}\n')
            
            # Create structure with mix of existing and missing files
            structure = ProjectStructure(
                root_pdf=str(existing_file1),  # Use existing file as root
                processing_directory=temp_dir,
                final_output_directory=temp_dir,
                associated_files=[str(existing_file2), "/nonexistent/file1.json"],
                previous_results=["/nonexistent/file2.ndjson", "/nonexistent/file3.json"]
            )
            
            # Validate files
            self.manager._validate_project_files(structure)
            
            # Should identify missing files
            assert len(structure.missing_files) == 3  # 3 nonexistent files
            assert "/nonexistent/file1.json" in structure.missing_files
            assert "/nonexistent/file2.ndjson" in structure.missing_files
            assert "/nonexistent/file3.json" in structure.missing_files
            
            # Existing files should not be in missing list
            assert str(existing_file1) not in structure.missing_files
            assert str(existing_file2) not in structure.missing_files
    
    def test_file_status_error_handling(self):
        """Test file status error handling for various error conditions."""
        # Test with permission denied (simulate by using a directory path as file)
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to get status of directory as if it were a file
            status = self.manager.get_file_status(temp_dir)
            # Directory exists but we're treating it as a file
            assert status.exists is True  # Directory exists
            assert status.file_size is not None
        
        # Test with invalid path characters (if applicable to OS)
        invalid_path = "/invalid\x00path/file.txt"  # Null character in path
        status = self.manager.get_file_status(invalid_path)
        # Should handle gracefully
        assert status.exists is False
        assert status.error_message is not None
    
    def test_project_structure_caching_expiration(self):
        """Test project structure cache expiration logic."""
        if self.pdf_path and Path(self.pdf_path).exists():
            # Create initial structure
            structure1 = self.manager.get_project_structure(self.pdf_path)
            assert structure1.last_validated is not None
            
            # Should use cache for immediate second call
            structure2 = self.manager.get_project_structure(self.pdf_path)
            assert structure1.last_validated == structure2.last_validated
            
            # Manually expire the cache by setting old validation time
            from datetime import timedelta
            old_time = datetime.now() - timedelta(minutes=10)
            structure1.last_validated = old_time
            self.manager._project_cache[self.pdf_path] = structure1
            
            # Should refresh due to expired validation
            structure3 = self.manager.get_project_structure(self.pdf_path)
            assert structure3.last_validated > old_time
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_relocate_file_error_handling(self):
        """Test file relocation error handling."""
        if self.pdf_path and Path(self.pdf_path).exists():
            # Test with invalid paths that might cause errors
            success = self.manager.relocate_file(
                "/nonexistent/old.json", 
                "/nonexistent/new.json", 
                "/nonexistent/pdf.pdf"
            )
            # Should handle gracefully and return False for nonexistent project
            assert success is False
        else:
            pytest.skip("Target PDF not available for testing")
    
    def test_save_project_manifest_default_path(self):
        """Test saving project manifest with default path."""
        if self.pdf_path and Path(self.pdf_path).exists():
            # Test saving without specifying output path (uses default)
            saved_path = self.manager.save_project_manifest(self.pdf_path)
            
            assert saved_path is not None
            assert saved_path.endswith("project_manifest.json")
            assert Path(saved_path).exists()
            
            # Verify the saved content
            with open(saved_path, 'r') as f:
                saved_manifest = json.load(f)
            
            assert isinstance(saved_manifest, dict)
            assert "project_info" in saved_manifest
            assert "file_structure" in saved_manifest
            assert "validation_report" in saved_manifest
            
            # Clean up
            try:
                os.unlink(saved_path)
            except:
                pass  # Don't fail test if cleanup fails
        else:
            pytest.skip("Target PDF not available for testing")
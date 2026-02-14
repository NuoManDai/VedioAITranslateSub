"""
Tests for batch models and database layer (TDD)
"""

import pytest
import sqlite3
from datetime import datetime
from pathlib import Path
import tempfile

from models.batch_models import (
    BatchJob,
    BatchFile,
    BatchFileStatus,
    BatchJobStatus,
    BatchFileSettingsUpdate,
    BatchFileRegister,
)
from database.batch_db import BatchDB


class TestBatchModels:
    """Test Pydantic model validation and camelCase serialization"""

    def test_batch_file_creation_with_defaults(self):
        """Test BatchFile model creation with defaults"""
        file = BatchFile(
            job_id="job-123",
            filename="test.mp4",
        )
        assert file.id is not None
        assert file.job_id == "job-123"
        assert file.filename == "test.mp4"
        assert file.status == "pending"
        assert file.source_lang == "auto"
        assert file.target_lang == "简体中文"
        assert file.dubbing is False
        assert file.filepath is None
        assert file.output_path is None
        assert file.error_message is None
        assert isinstance(file.created_at, datetime)

    def test_batch_file_camel_case_serialization(self):
        """Test BatchFile camelCase alias generation"""
        file = BatchFile(
            job_id="job-123",
            filename="test.mp4",
            source_lang="en",
            target_lang="zh",
            dubbing=True,
        )
        data = file.model_dump(by_alias=True)
        assert "sourceLang" in data
        assert "targetLang" in data
        assert data["sourceLang"] == "en"
        assert data["targetLang"] == "zh"
        assert data["dubbing"] is True

    def test_batch_file_populate_by_name(self):
        """Test BatchFile accepts both snake_case and camelCase"""
        # Using snake_case
        file1 = BatchFile(job_id="job-123", filename="test.mp4", source_lang="en")
        assert file1.source_lang == "en"

        # Using camelCase (via model_validate)
        file2 = BatchFile.model_validate(
            {
                "jobId": "job-123",
                "filename": "test.mp4",
                "sourceLang": "en",
            }
        )
        assert file2.job_id == "job-123"
        assert file2.source_lang == "en"

    def test_batch_job_creation_with_defaults(self):
        """Test BatchJob model creation with defaults"""
        job = BatchJob()
        assert job.id is not None
        assert job.status == "pending"
        assert job.files == []
        assert job.total_files == 0
        assert job.completed_files == 0
        assert job.failed_files == 0
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)

    def test_batch_job_camel_case_serialization(self):
        """Test BatchJob camelCase alias generation"""
        job = BatchJob()
        data = job.model_dump(by_alias=True)
        assert "createdAt" in data
        assert "updatedAt" in data
        assert "totalFiles" in data
        assert "completedFiles" in data
        assert "failedFiles" in data

    def test_batch_file_settings_update(self):
        """Test BatchFileSettingsUpdate partial update model"""
        update = BatchFileSettingsUpdate(
            source_lang="fr",
            dubbing=True,
        )
        assert update.source_lang == "fr"
        assert update.dubbing is True
        assert update.target_lang is None

        data = update.model_dump(by_alias=True, exclude_none=True)
        assert "sourceLang" in data
        assert "dubbing" in data
        assert "targetLang" not in data

    def test_batch_file_register(self):
        """Test BatchFileRegister request model"""
        register = BatchFileRegister(filename="video.mp4")
        assert register.filename == "video.mp4"

        data = register.model_dump(by_alias=True)
        assert data["filename"] == "video.mp4"


class TestBatchDatabase:
    """Test SQLite batch database CRUD operations"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_batch.db"
            db = BatchDB(db_path=str(db_path))
            db.init_db()
            yield db

    def test_init_db_creates_tables(self, temp_db):
        """Test init_db creates required tables"""
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()

        # Check batch_jobs table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='batch_jobs'"
        )
        assert cursor.fetchone() is not None

        # Check batch_files table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='batch_files'"
        )
        assert cursor.fetchone() is not None

        conn.close()

    def test_create_job_returns_valid_id(self, temp_db):
        """Test create_job inserts job and returns ID"""
        job_id = temp_db.create_job()
        assert job_id is not None
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    def test_get_job_returns_batch_job(self, temp_db):
        """Test get_job retrieves created job"""
        job_id = temp_db.create_job()
        job = temp_db.get_job(job_id)

        assert job is not None
        assert isinstance(job, BatchJob)
        assert job.id == job_id
        assert job.status == "pending"
        assert job.files == []
        assert job.total_files == 0

    def test_get_job_returns_none_for_nonexistent_id(self, temp_db):
        """Test get_job returns None for non-existent ID"""
        job = temp_db.get_job("nonexistent-id")
        assert job is None

    def test_add_file_to_job(self, temp_db):
        """Test add_file inserts file and returns ID"""
        job_id = temp_db.create_job()
        file_id = temp_db.add_file(job_id, "video.mp4")

        assert file_id is not None
        assert isinstance(file_id, str)

        # Verify file was added
        file = temp_db.get_file(file_id)
        assert file is not None
        assert file.id == file_id
        assert file.job_id == job_id
        assert file.filename == "video.mp4"

    def test_get_files_for_job(self, temp_db):
        """Test get_files_for_job returns all files in job"""
        job_id = temp_db.create_job()
        file_id1 = temp_db.add_file(job_id, "video1.mp4")
        file_id2 = temp_db.add_file(job_id, "video2.mp4")

        files = temp_db.get_files_for_job(job_id)
        assert len(files) == 2
        assert all(isinstance(f, BatchFile) for f in files)
        assert {f.id for f in files} == {file_id1, file_id2}

    def test_update_file_status(self, temp_db):
        """Test update_file_status changes file status"""
        job_id = temp_db.create_job()
        file_id = temp_db.add_file(job_id, "video.mp4")

        temp_db.update_file_status(file_id, "processing")
        file = temp_db.get_file(file_id)
        assert file.status == "processing"

    def test_update_file_status_with_error(self, temp_db):
        """Test update_file_status records error message"""
        job_id = temp_db.create_job()
        file_id = temp_db.add_file(job_id, "video.mp4")

        error_msg = "Failed to process file"
        temp_db.update_file_status(file_id, "failed", error_message=error_msg)

        file = temp_db.get_file(file_id)
        assert file.status == "failed"
        assert file.error_message == error_msg

    def test_update_file_settings(self, temp_db):
        """Test update_file_settings modifies file settings"""
        job_id = temp_db.create_job()
        file_id = temp_db.add_file(job_id, "video.mp4")

        temp_db.update_file_settings(
            file_id,
            source_lang="en",
            target_lang="zh",
            dubbing=True,
        )

        file = temp_db.get_file(file_id)
        assert file.source_lang == "en"
        assert file.target_lang == "zh"
        assert file.dubbing is True

    def test_update_file_settings_partial(self, temp_db):
        """Test update_file_settings with partial updates"""
        job_id = temp_db.create_job()
        file_id = temp_db.add_file(job_id, "video.mp4", source_lang="en")

        # Update only target_lang
        temp_db.update_file_settings(
            file_id,
            target_lang="zh",
        )

        file = temp_db.get_file(file_id)
        assert file.source_lang == "en"  # Unchanged
        assert file.target_lang == "zh"  # Updated

    def test_update_file_path(self, temp_db):
        """Test update_file_path sets filepath"""
        job_id = temp_db.create_job()
        file_id = temp_db.add_file(job_id, "video.mp4")

        filepath = "/path/to/video.mp4"
        temp_db.update_file_path(file_id, filepath)

        file = temp_db.get_file(file_id)
        assert file.filepath == filepath

    def test_update_file_output(self, temp_db):
        """Test update_file_output sets output_path"""
        job_id = temp_db.create_job()
        file_id = temp_db.add_file(job_id, "video.mp4")

        output_path = "/output/result"
        temp_db.update_file_output(file_id, output_path)

        file = temp_db.get_file(file_id)
        assert file.output_path == output_path

    def test_list_jobs(self, temp_db):
        """Test list_jobs returns all jobs with files"""
        job_id1 = temp_db.create_job()
        job_id2 = temp_db.create_job()

        file_id1 = temp_db.add_file(job_id1, "video1.mp4")
        file_id2 = temp_db.add_file(job_id1, "video2.mp4")
        file_id3 = temp_db.add_file(job_id2, "video3.mp4")

        jobs = temp_db.list_jobs()
        assert len(jobs) == 2
        assert all(isinstance(j, BatchJob) for j in jobs)

        # Find jobs by id
        job1 = next(j for j in jobs if j.id == job_id1)
        job2 = next(j for j in jobs if j.id == job_id2)

        assert len(job1.files) == 2
        assert len(job2.files) == 1

    def test_delete_file(self, temp_db):
        """Test delete_file removes file record"""
        job_id = temp_db.create_job()
        file_id = temp_db.add_file(job_id, "video.mp4")

        temp_db.delete_file(file_id)

        file = temp_db.get_file(file_id)
        assert file is None

    def test_update_job_counts(self, temp_db):
        """Test update_job_counts recalculates file statistics"""
        job_id = temp_db.create_job()

        # Add files with different statuses
        file_id1 = temp_db.add_file(job_id, "video1.mp4")
        file_id2 = temp_db.add_file(job_id, "video2.mp4")
        file_id3 = temp_db.add_file(job_id, "video3.mp4")

        # Set statuses
        temp_db.update_file_status(file_id1, "completed")
        temp_db.update_file_status(file_id2, "completed")
        temp_db.update_file_status(file_id3, "failed")

        # Update counts
        temp_db.update_job_counts(job_id)

        job = temp_db.get_job(job_id)
        assert job.total_files == 3
        assert job.completed_files == 2
        assert job.failed_files == 1

    def test_get_active_batch(self, temp_db):
        """Test get_active_batch returns job with processing status"""
        job_id1 = temp_db.create_job()
        job_id2 = temp_db.create_job()

        # Set job2 to processing
        temp_db.update_job_status(job_id2, "processing")

        active = temp_db.get_active_batch()
        assert active is not None
        assert active.id == job_id2
        assert active.status == "processing"

    def test_get_active_batch_returns_none_when_no_processing(self, temp_db):
        """Test get_active_batch returns None when no job is processing"""
        job_id = temp_db.create_job()
        temp_db.update_job_status(job_id, "completed")

        active = temp_db.get_active_batch()
        assert active is None

    def test_update_job_status(self, temp_db):
        """Test update_job_status changes job status"""
        job_id = temp_db.create_job()

        temp_db.update_job_status(job_id, "processing")
        job = temp_db.get_job(job_id)
        assert job.status == "processing"

    def test_add_file_with_filepath(self, temp_db):
        """Test add_file with optional filepath parameter"""
        job_id = temp_db.create_job()
        filepath = "/path/to/file.mp4"

        file_id = temp_db.add_file(job_id, "video.mp4", filepath=filepath)

        file = temp_db.get_file(file_id)
        assert file.filepath == filepath

    def test_batch_job_with_multiple_files(self, temp_db):
        """Test get_job returns job with all files populated"""
        job_id = temp_db.create_job()

        for i in range(3):
            temp_db.add_file(job_id, f"video{i}.mp4")

        job = temp_db.get_job(job_id)
        assert len(job.files) == 3
        assert all(isinstance(f, BatchFile) for f in job.files)
        assert all(f.job_id == job_id for f in job.files)

    def test_file_timestamps_are_iso_formatted(self, temp_db):
        """Test file timestamps are properly formatted datetime objects"""
        job_id = temp_db.create_job()
        file_id = temp_db.add_file(job_id, "video.mp4")

        file = temp_db.get_file(file_id)
        assert isinstance(file.created_at, datetime)

    def test_job_timestamps_are_iso_formatted(self, temp_db):
        """Test job timestamps are properly formatted datetime objects"""
        job_id = temp_db.create_job()

        job = temp_db.get_job(job_id)
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)

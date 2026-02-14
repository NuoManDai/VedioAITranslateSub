"""
Tests for BatchService
"""

import pytest
import os
from pathlib import Path

from services.batch_service import BatchService


@pytest.fixture
def batch_service(tmp_path):
    """Create a BatchService with temporary database"""
    db_path = str(tmp_path / "test_batch.db")
    service = BatchService(db_path=db_path)
    return service


class TestBatchServiceCreate:
    def test_create_batch_returns_job_id(self, batch_service):
        job_id = batch_service.create_batch()
        assert job_id is not None
        assert len(job_id) > 0

    def test_create_batch_status_is_pending(self, batch_service):
        job_id = batch_service.create_batch()
        status = batch_service.get_batch_status(job_id)
        assert status is not None
        assert status.status == "pending"


class TestBatchServiceFiles:
    def test_add_file_to_batch(self, batch_service):
        job_id = batch_service.create_batch()
        file_id = batch_service.add_file_to_batch(job_id, "test.mp4", "/tmp/test.mp4")
        assert file_id is not None

    def test_add_file_updates_total_count(self, batch_service):
        job_id = batch_service.create_batch()
        batch_service.add_file_to_batch(job_id, "test1.mp4", "/tmp/test1.mp4")
        batch_service.add_file_to_batch(job_id, "test2.mp4", "/tmp/test2.mp4")
        status = batch_service.get_batch_status(job_id)
        assert status.total_files == 2

    def test_add_file_with_custom_settings(self, batch_service):
        job_id = batch_service.create_batch()
        file_id = batch_service.add_file_to_batch(
            job_id,
            "test.mp4",
            "/tmp/test.mp4",
            source_lang="en",
            target_lang="English",
            dubbing=True,
        )
        file = batch_service.get_file(file_id)
        assert file.source_lang == "en"
        assert file.target_lang == "English"
        assert file.dubbing is True

    def test_remove_file_from_batch(self, batch_service):
        job_id = batch_service.create_batch()
        file_id = batch_service.add_file_to_batch(job_id, "test.mp4", "/tmp/test.mp4")
        batch_service.remove_file_from_batch(job_id, file_id)
        status = batch_service.get_batch_status(job_id)
        assert status.total_files == 0


class TestBatchServiceSettings:
    def test_update_file_settings(self, batch_service):
        job_id = batch_service.create_batch()
        file_id = batch_service.add_file_to_batch(job_id, "test.mp4", "/tmp/test.mp4")
        batch_service.update_file_settings(
            job_id, file_id, source_lang="en", target_lang="English", dubbing=True
        )
        file = batch_service.get_file(file_id)
        assert file.source_lang == "en"
        assert file.target_lang == "English"
        assert file.dubbing is True

    def test_update_file_settings_partial(self, batch_service):
        job_id = batch_service.create_batch()
        file_id = batch_service.add_file_to_batch(job_id, "test.mp4", "/tmp/test.mp4")
        batch_service.update_file_settings(job_id, file_id, target_lang="日本語")
        file = batch_service.get_file(file_id)
        assert file.target_lang == "日本語"
        assert file.source_lang == "auto"  # unchanged
        assert file.dubbing is False  # unchanged


class TestBatchServiceStatus:
    def test_get_batch_status(self, batch_service):
        job_id = batch_service.create_batch()
        batch_service.add_file_to_batch(job_id, "test.mp4", "/tmp/test.mp4")
        status = batch_service.get_batch_status(job_id)
        assert status is not None
        assert status.total_files == 1
        assert len(status.files) == 1

    def test_get_batch_status_nonexistent(self, batch_service):
        status = batch_service.get_batch_status("nonexistent-id")
        assert status is None

    def test_list_batches(self, batch_service):
        batch_service.create_batch()
        batch_service.create_batch()
        batches = batch_service.list_batches()
        assert len(batches) == 2

    def test_list_batches_empty(self, batch_service):
        batches = batch_service.list_batches()
        assert len(batches) == 0


class TestBatchServiceCancel:
    def test_cancel_batch(self, batch_service):
        job_id = batch_service.create_batch()
        batch_service.add_file_to_batch(job_id, "test.mp4", "/tmp/test.mp4")
        batch_service.cancel_batch(job_id)
        status = batch_service.get_batch_status(job_id)
        assert status.status == "cancelled"

    def test_cancel_batch_updates_pending_files(self, batch_service):
        job_id = batch_service.create_batch()
        file_id = batch_service.add_file_to_batch(job_id, "test.mp4", "/tmp/test.mp4")
        batch_service.cancel_batch(job_id)
        file = batch_service.get_file(file_id)
        assert file.status == "cancelled"


class TestBatchServiceActiveBatch:
    def test_is_batch_processing_false_initially(self, batch_service):
        assert batch_service.is_batch_processing() is False

    def test_is_batch_processing_true_when_active(self, batch_service):
        job_id = batch_service.create_batch()
        batch_service.add_file_to_batch(job_id, "test.mp4", "/tmp/test.mp4")
        # Manually set status to processing
        batch_service.db.update_job_status(job_id, "processing")
        assert batch_service.is_batch_processing() is True

    def test_get_active_batch(self, batch_service):
        job_id = batch_service.create_batch()
        batch_service.db.update_job_status(job_id, "processing")
        active = batch_service.get_active_batch()
        assert active is not None
        assert active.id == job_id

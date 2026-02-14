"""
Batch Service - Business logic for batch video processing
"""

import logging
from typing import Optional
from pathlib import Path

from database.batch_db import BatchDB
from models.batch_models import BatchJob, BatchFile

logger = logging.getLogger(__name__)


class BatchService:
    """Service for batch job management"""

    def __init__(self, db_path: str = "data/batch.db"):
        self.db = BatchDB(db_path=db_path)
        self.db.init_db()

    def create_batch(self) -> str:
        """Create a new batch job, return job ID"""
        job_id = self.db.create_job()
        logger.info(f"Created batch job: {job_id}")
        return job_id

    def add_file_to_batch(
        self,
        job_id: str,
        filename: str,
        filepath: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        dubbing: Optional[bool] = None,
    ) -> str:
        """Add a file to a batch job, return file ID"""
        file_id = self.db.add_file(
            job_id=job_id,
            filename=filename,
            filepath=filepath,
            source_lang=source_lang,
            target_lang=target_lang,
            dubbing=dubbing,
        )
        logger.info(f"Added file {filename} to batch {job_id}")
        return file_id

    def remove_file_from_batch(self, job_id: str, file_id: str):
        """Remove a file from a batch job"""
        self.db.delete_file(file_id)
        logger.info(f"Removed file {file_id} from batch {job_id}")

    def update_file_settings(
        self,
        job_id: str,
        file_id: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        dubbing: Optional[bool] = None,
    ):
        """Update file settings"""
        self.db.update_file_settings(
            file_id=file_id,
            source_lang=source_lang,
            target_lang=target_lang,
            dubbing=dubbing,
        )
        logger.info(f"Updated settings for file {file_id}")

    def get_file(self, file_id: str) -> Optional[BatchFile]:
        """Get a single file by ID"""
        return self.db.get_file(file_id)

    def get_batch_status(self, job_id: str) -> Optional[BatchJob]:
        """Get batch job status with all files"""
        return self.db.get_job(job_id)

    def list_batches(self) -> list[BatchJob]:
        """List all batch jobs"""
        return self.db.list_jobs()

    def cancel_batch(self, job_id: str):
        """Cancel a batch job and all its pending files"""
        # Cancel all pending/queued files
        files = self.db.get_files_for_job(job_id)
        for file in files:
            if file.status in ("pending", "queued", "uploading"):
                self.db.update_file_status(file.id, "cancelled")

        # Cancel the job
        self.db.update_job_status(job_id, "cancelled")
        logger.info(f"Cancelled batch job: {job_id}")

    def is_batch_processing(self) -> bool:
        """Check if any batch is currently processing"""
        active = self.db.get_active_batch()
        return active is not None

    def get_active_batch(self) -> Optional[BatchJob]:
        """Get the currently processing batch, if any"""
        return self.db.get_active_batch()

    def update_file_path(self, file_id: str, filepath: str):
        """Update file path after upload"""
        self.db.update_file_path(file_id, filepath)

    def update_file_status(
        self, file_id: str, status: str, error_message: Optional[str] = None
    ):
        """Update file processing status"""
        self.db.update_file_status(file_id, status, error_message)

    def update_job_status(self, job_id: str, status: str):
        """Update job status"""
        self.db.update_job_status(job_id, status)

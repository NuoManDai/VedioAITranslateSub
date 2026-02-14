"""
SQLite database layer for batch processing
"""

import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime

from models.batch_models import BatchJob, BatchFile


class BatchDB:
    """SQLite database for batch jobs and files"""

    def __init__(self, db_path: str = "data/batch.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database tables"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create batch_jobs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Create batch_files table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_files (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                source_lang TEXT NOT NULL DEFAULT 'auto',
                target_lang TEXT NOT NULL DEFAULT '简体中文',
                dubbing INTEGER NOT NULL DEFAULT 0,
                output_path TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES batch_jobs(id)
            )
            """
        )

        conn.commit()
        conn.close()

    def create_job(self) -> str:
        """Create new batch job and return its ID"""
        from models.batch_models import BatchJob as BJ

        job = BJ()
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO batch_jobs (id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                job.id,
                job.status,
                job.created_at.isoformat(),
                job.updated_at.isoformat(),
            ),
        )

        conn.commit()
        conn.close()
        return job.id

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get batch job with all files"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM batch_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        # Get files for this job
        files = self.get_files_for_job(job_id)

        # Calculate counts
        total_files = len(files)
        completed_files = sum(1 for f in files if f.status == "completed")
        failed_files = sum(1 for f in files if f.status == "failed")

        conn.close()

        return BatchJob(
            id=row["id"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            files=files,
            total_files=total_files,
            completed_files=completed_files,
            failed_files=failed_files,
        )

    def list_jobs(self) -> list[BatchJob]:
        """Get all batch jobs with files"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM batch_jobs ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        jobs = []
        for row in rows:
            job = self.get_job(row["id"])
            if job:
                jobs.append(job)

        return jobs

    def update_job_status(self, job_id: str, status: str):
        """Update job status"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE batch_jobs 
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, datetime.now().isoformat(), job_id),
        )

        conn.commit()
        conn.close()

    def add_file(
        self,
        job_id: str,
        filename: str,
        filepath: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        dubbing: Optional[bool] = None,
    ) -> str:
        """Add file to batch job and return file ID"""
        from models.batch_models import BatchFile as BF

        # Build BatchFile with optional initial settings
        kwargs = {"job_id": job_id, "filename": filename}
        if filepath:
            kwargs["filepath"] = filepath
        if source_lang:
            kwargs["source_lang"] = source_lang
        if target_lang:
            kwargs["target_lang"] = target_lang
        if dubbing is not None:
            kwargs["dubbing"] = dubbing

        file = BF(**kwargs)
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO batch_files 
            (id, job_id, filename, filepath, status, source_lang, target_lang, dubbing, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file.id,
                file.job_id,
                file.filename,
                file.filepath,
                file.status,
                file.source_lang,
                file.target_lang,
                int(file.dubbing),
                file.created_at.isoformat(),
            ),
        )

        conn.commit()
        conn.close()
        return file.id

    def get_file(self, file_id: str) -> Optional[BatchFile]:
        """Get single batch file"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM batch_files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_batch_file(row)

    def get_files_for_job(self, job_id: str) -> list[BatchFile]:
        """Get all files for a batch job"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM batch_files WHERE job_id = ? ORDER BY created_at ASC",
            (job_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_batch_file(row) for row in rows]

    def _row_to_batch_file(self, row: sqlite3.Row) -> BatchFile:
        """Convert database row to BatchFile model"""
        return BatchFile(
            id=row["id"],
            job_id=row["job_id"],
            filename=row["filename"],
            filepath=row["filepath"],
            status=row["status"],
            source_lang=row["source_lang"],
            target_lang=row["target_lang"],
            dubbing=bool(row["dubbing"]),
            output_path=row["output_path"],
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def update_file_status(
        self, file_id: str, status: str, error_message: Optional[str] = None
    ):
        """Update file status"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE batch_files 
            SET status = ?, error_message = ?
            WHERE id = ?
            """,
            (status, error_message, file_id),
        )

        conn.commit()
        conn.close()

    def update_file_settings(
        self,
        file_id: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        dubbing: Optional[bool] = None,
    ):
        """Update file settings (partial update)"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build dynamic UPDATE query
        updates = []
        params = []

        if source_lang is not None:
            updates.append("source_lang = ?")
            params.append(source_lang)

        if target_lang is not None:
            updates.append("target_lang = ?")
            params.append(target_lang)

        if dubbing is not None:
            updates.append("dubbing = ?")
            params.append(int(dubbing))

        if not updates:
            conn.close()
            return

        params.append(file_id)
        query = f"UPDATE batch_files SET {', '.join(updates)} WHERE id = ?"

        cursor.execute(query, params)
        conn.commit()
        conn.close()

    def update_file_path(self, file_id: str, filepath: str):
        """Set file path after upload"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE batch_files 
            SET filepath = ?
            WHERE id = ?
            """,
            (filepath, file_id),
        )

        conn.commit()
        conn.close()

    def update_file_output(self, file_id: str, output_path: str):
        """Set output path after processing"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE batch_files 
            SET output_path = ?
            WHERE id = ?
            """,
            (output_path, file_id),
        )

        conn.commit()
        conn.close()

    def delete_file(self, file_id: str):
        """Delete file record"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM batch_files WHERE id = ?", (file_id,))

        conn.commit()
        conn.close()

    def update_job_counts(self, job_id: str):
        """Recalculate job file statistics"""
        files = self.get_files_for_job(job_id)

        total_files = len(files)
        completed_files = sum(1 for f in files if f.status == "completed")
        failed_files = sum(1 for f in files if f.status == "failed")

        # Note: We store these for reference, but they're calculated on-the-fly in get_job()
        # This function is kept for convenience in updating logic

    def get_active_batch(self) -> Optional[BatchJob]:
        """Get batch job with 'processing' status, if any"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM batch_jobs WHERE status = 'processing' LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self.get_job(row["id"])

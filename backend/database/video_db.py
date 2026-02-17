"""
SQLite database layer for video metadata storage
"""

import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime

from models.video import Video


class VideoDB:
    """SQLite database for videos"""

    def __init__(self, db_path: str = "data/videos.db"):
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

        # Create videos table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                filepath TEXT,
                source_type TEXT NOT NULL DEFAULT 'upload',
                youtube_url TEXT,
                status TEXT NOT NULL DEFAULT 'ready',
                file_size INTEGER,
                duration REAL,
                thumbnail_path TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.commit()
        conn.close()

    def create_video(
        self,
        filename: str,
        filepath: Optional[str] = None,
        source_type: str = "upload",
        youtube_url: Optional[str] = None,
        status: str = "ready",
        file_size: Optional[int] = None,
        duration: Optional[float] = None,
        thumbnail_path: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> str:
        """Create new video and return its ID"""
        video = Video(
            filename=filename,
            filepath=filepath or "",
            source_type=source_type,
            youtube_url=youtube_url,
            status=status,
            file_size=file_size,
            duration=duration,
            thumbnail_path=thumbnail_path,
            error_message=error_message,
        )

        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO videos 
            (id, filename, filepath, source_type, youtube_url, status, file_size, duration, thumbnail_path, error_message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                video.id,
                video.filename,
                filepath or "",
                source_type,
                youtube_url,
                status,
                file_size,
                duration,
                thumbnail_path,
                error_message,
                now,
                now,
            ),
        )

        conn.commit()
        conn.close()
        return video.id

    def get_video(self, video_id: str) -> Optional[Video]:
        """Get single video by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_video(row)

    def list_videos(
        self,
        offset: int = 0,
        limit: int = 20,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Video], int]:
        """Get videos with pagination, filtering, and sorting.
        Returns (videos, total_count) tuple.

        Args:
            offset: Pagination offset
            limit: Page size
            keyword: Search filename by keyword
            status: Filter by video status (ready, processing, completed, error, etc.)
            source_type: Filter by source type (upload, youtube)
            sort_by: Sort field (created_at, filename, duration)
            sort_order: Sort direction (asc, desc)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build WHERE conditions
        conditions: list[str] = []
        params: list = []

        if keyword:
            conditions.append("filename LIKE ?")
            params.append(f"%{keyword}%")

        if status:
            conditions.append("status = ?")
            params.append(status)

        if source_type:
            conditions.append("source_type = ?")
            params.append(source_type)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Validate sort_by to prevent SQL injection
        allowed_sort_fields = {"created_at", "filename", "duration"}
        if sort_by not in allowed_sort_fields:
            sort_by = "created_at"

        sort_direction = "ASC" if sort_order.lower() == "asc" else "DESC"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM videos {where_clause}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        # Get paginated results
        select_query = (
            f"SELECT * FROM videos {where_clause} "
            f"ORDER BY {sort_by} {sort_direction} LIMIT ? OFFSET ?"
        )
        cursor.execute(select_query, params + [limit, offset])
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_video(row) for row in rows], total

    def _row_to_video(self, row: sqlite3.Row) -> Video:
        """Convert database row to Video model"""
        return Video(
            id=row["id"],
            filename=row["filename"],
            filepath=row["filepath"],
            source_type=row["source_type"],
            youtube_url=row["youtube_url"],
            status=row["status"],
            file_size=row["file_size"],
            duration=row["duration"],
            thumbnail_path=row["thumbnail_path"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            error_message=row["error_message"],
        )

    def update_video_status(self, video_id: str, status: str):
        """Update video status and updated_at timestamp"""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        cursor.execute(
            """
            UPDATE videos 
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, now, video_id),
        )

        conn.commit()
        conn.close()

    def update_video(self, video_id: str, **fields):
        """Update video with arbitrary fields"""
        if not fields:
            return

        conn = self._get_connection()
        cursor = conn.cursor()

        # Build dynamic UPDATE query
        updates = []
        params = []

        # Always update updated_at
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())

        # Add provided fields
        for key, value in fields.items():
            if key not in ["id", "created_at"]:  # Never update id or created_at
                updates.append(f"{key} = ?")
                params.append(value)

        params.append(video_id)
        query = f"UPDATE videos SET {', '.join(updates)} WHERE id = ?"

        cursor.execute(query, params)
        conn.commit()
        conn.close()

    def delete_video(self, video_id: str):
        """Delete video by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))

        conn.commit()
        conn.close()

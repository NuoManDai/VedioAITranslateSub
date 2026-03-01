"""
Video Service - Business logic for video operations
"""

import logging
import subprocess
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import UploadFile

from models import Video
from api.deps import (
    get_output_dir,
    get_app_state,
    get_project_root,
    get_video_output_dir,
)
from database.video_db import VideoDB

logger = logging.getLogger(__name__)

# Video file extensions recognized by the system
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov", ".m4v", ".flv", ".wmv", ".ts", ".mpeg", ".mpg", ".3gp", ".rm", ".rmvb", ".vob", ".f4v"}


def get_video_duration(filepath: Path) -> Optional[float]:
    """Get video duration using cv2"""
    try:
        import cv2

        cap = cv2.VideoCapture(str(filepath))
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            if fps > 0 and frame_count > 0:
                return frame_count / fps
    except Exception as e:
        logger.warning(f"Error getting video duration with cv2: {e}")
    return None


def generate_thumbnail(video_path: Path, thumb_path: Path) -> bool:
    """Generate thumbnail from video using ffmpeg. Returns True on success."""
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vframes",
                "1",
                "-q:v",
                "2",
                "-y",
                str(thumb_path),
            ],
            capture_output=True,
            timeout=30,
        )
        return thumb_path.exists()
    except Exception as e:
        logger.warning(f"Thumbnail generation failed: {e}")
        return False


class VideoService:
    """Service for video upload, download, and management"""

    def __init__(self):
        self.output_dir = get_output_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db = VideoDB()

    # ----------------------------
    # Video CRUD via VideoDB
    # ----------------------------

    def get_video(self, video_id: str) -> Optional[Video]:
        """Get a video by ID from database"""
        return self.db.get_video(video_id)

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
        """List videos with pagination, filtering, and sorting"""
        return self.db.list_videos(
            offset=offset,
            limit=limit,
            keyword=keyword,
            status=status,
            source_type=source_type,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def delete_video(self, video_id: str) -> None:
        """Delete video record and its output directory"""
        video = self.db.get_video(video_id)
        if not video:
            raise ValueError(f"Video not found: {video_id}")

        # Remove per-video output directory
        video_dir = self.output_dir / video_id
        if video_dir.exists():
            shutil.rmtree(video_dir, ignore_errors=True)

        # Remove DB record
        self.db.delete_video(video_id)

    def rename_video(self, video_id: str, new_filename: str) -> Video:
        """Rename a video's filename in the database"""
        video = self.db.get_video(video_id)
        if not video:
            raise ValueError(f"Video not found: {video_id}")

        self.db.update_video(video_id, filename=new_filename)
        updated = self.db.get_video(video_id)
        if not updated:
            raise ValueError(f"Failed to retrieve video after rename: {video_id}")
        return updated

    # ----------------------------
    # Upload
    # ----------------------------

    async def save_uploaded_video(self, file: UploadFile) -> Video:
        """Save an uploaded video file to output/{video_id}/"""
        state = get_app_state()
        video_id = str(uuid.uuid4())

        # Sanitize filename
        original_name = file.filename or "video.mp4"
        safe_name = "".join(
            c if c.isalnum() or c in "._-" else "_" for c in original_name
        )

        # Create per-video output directory
        video_dir = get_video_output_dir(video_id)
        file_path = video_dir / safe_name

        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            file_size = file_path.stat().st_size
            duration = get_video_duration(file_path)
            relative_path = str(file_path.relative_to(get_project_root()))

            # Generate thumbnail
            thumb_path = video_dir / "thumbnail.jpg"
            thumb_relative = None
            if generate_thumbnail(file_path, thumb_path):
                thumb_relative = str(thumb_path.relative_to(get_project_root()))

            # Create DB record with pre-generated ID
            # VideoDB.create_video generates its own UUID, so we need to
            # get the returned ID and use that
            created_id = self.db.create_video(
                filename=safe_name,
                filepath=relative_path,
                source_type="upload",
                status="ready",
                file_size=file_size,
                duration=duration,
                thumbnail_path=thumb_relative,
            )

            # Retrieve full video from DB
            video = self.db.get_video(created_id)
            if not video:
                raise ValueError("Failed to create video record")

            # The DB generated its own UUID, but our directory uses video_id
            # Rename directory to match DB id if different
            if created_id != video_id:
                new_dir = self.output_dir / created_id
                if not new_dir.exists():
                    video_dir.rename(new_dir)
                    # Update filepath in DB
                    new_file_path = new_dir / safe_name
                    new_relative = str(new_file_path.relative_to(get_project_root()))
                    new_thumb_relative = None
                    new_thumb = new_dir / "thumbnail.jpg"
                    if new_thumb.exists():
                        new_thumb_relative = str(
                            new_thumb.relative_to(get_project_root())
                        )
                    self.db.update_video(
                        created_id,
                        filepath=new_relative,
                        thumbnail_path=new_thumb_relative,
                    )
                    video = self.db.get_video(created_id)

            # Update app state for backward compatibility
            state.current_video = video
            state.subtitle_job = None
            state.dubbing_job = None

            # Trigger transcode for non-MP4 files
            actual_id = created_id
            actual_dir = self.output_dir / actual_id
            actual_file = actual_dir / safe_name
            self._maybe_start_transcode(state, actual_id, actual_file, actual_dir)

            # Re-fetch video in case status was updated to 'transcoding'
            video = self.db.get_video(actual_id)
            if video:
                state.current_video = video

            return video

        except Exception as e:
            # Clean up on error
            if video_dir.exists():
                shutil.rmtree(video_dir, ignore_errors=True)
            raise e

    # ----------------------------
    # Transcode Helper
    # ----------------------------

    def _maybe_start_transcode(
        self, state, video_id: str, file_path: Path, video_dir: Path
    ) -> None:
        """Trigger transcode if file is not already H.264 MP4. Non-blocking."""
        from services.transcode_service import needs_transcode

        src = str(file_path)
        if not needs_transcode(src):
            logger.info("File already H.264 MP4, skipping transcode: %s", src)
            return

        # Update DB status to 'transcoding'
        self.db.update_video(video_id, status="transcoding")

        # Schedule async transcode via AppState's TranscodeManager
        tm = state.transcode_manager
        tm.start_transcode(video_id, src, str(video_dir))
        logger.info("Transcode scheduled for video %s: %s", video_id, src)

    # ----------------------------
    # YouTube Download
    # ----------------------------

    async def download_youtube_video(self, url: str, resolution: str) -> Video:
        """Download video from YouTube to output/{video_id}/"""
        import sys

        state = get_app_state()

        # Add project root to path for core imports
        project_root = get_project_root()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create DB record with downloading status first
        created_id = self.db.create_video(
            filename="downloading...",
            filepath="",
            source_type="youtube",
            youtube_url=url,
            status="downloading",
        )

        # Create per-video output directory using DB-assigned ID
        video_dir = get_video_output_dir(created_id)

        try:
            # Set app state for backward compat
            video = self.db.get_video(created_id)
            if video:
                state.current_video = video

            # Download video - core module writes to flat output/
            from core._1_ytdlp import download_video_ytdlp

            download_video_ytdlp(url, resolution)

            # Find the downloaded video in flat output/
            video_files = []
            for ext in VIDEO_EXTENSIONS:
                video_files.extend(
                    v
                    for v in self.output_dir.glob(f"*{ext}")
                    if not v.name.startswith("output") and v.is_file()
                )

            if not video_files:
                raise ValueError("Download failed: no video file found")

            latest_file = max(video_files, key=lambda p: p.stat().st_mtime)

            # Move downloaded file to per-video directory
            dest_path = video_dir / latest_file.name
            shutil.move(str(latest_file), str(dest_path))

            duration = get_video_duration(dest_path)
            relative_path = str(dest_path.relative_to(project_root))

            # Generate thumbnail
            thumb_path = video_dir / "thumbnail.jpg"
            thumb_relative = None
            if generate_thumbnail(dest_path, thumb_path):
                thumb_relative = str(thumb_path.relative_to(project_root))

            # Update DB record
            self.db.update_video(
                created_id,
                filename=latest_file.name,
                filepath=relative_path,
                status="ready",
                file_size=dest_path.stat().st_size,
                duration=duration,
                thumbnail_path=thumb_relative,
            )

            video = self.db.get_video(created_id)
            if not video:
                raise ValueError("Failed to retrieve video after download")

            # Update app state
            state.current_video = video
            state.subtitle_job = None
            state.dubbing_job = None

            return video

        except Exception as e:
            # Update DB status to error
            self.db.update_video(created_id, status="error", error_message=str(e))
            if state.current_video:
                state.current_video.status = "error"
                state.current_video.error_message = str(e)
            raise

    # ----------------------------
    # Backward Compatibility
    # ----------------------------

    async def delete_current_video(self):
        """Delete the current video (backward compat)"""
        state = get_app_state()

        if state.current_video and state.current_video.id:
            try:
                self.delete_video(state.current_video.id)
            except ValueError:
                pass

        # Also clean up legacy flat output files
        patterns_to_delete = ["*.srt", "*.json", "*.txt", "*.log"]
        for pattern in patterns_to_delete:
            for file in self.output_dir.glob(pattern):
                try:
                    file.unlink()
                except Exception:
                    pass

        state.reset()

    def detect_current_video(self) -> Optional[Video]:
        """Try to detect current video - check DB first, then filesystem"""
        # Check DB for most recently updated video
        videos, _ = self.db.list_videos(limit=1)
        if videos:
            return videos[0]  # Already sorted by created_at DESC

        # Fallback: scan flat output directory for legacy videos
        all_videos = []
        for ext in VIDEO_EXTENSIONS:
            found = [
                v
                for v in self.output_dir.glob(f"*{ext}")
                if not v.name.startswith("output")
            ]
            all_videos.extend(found)

        if not all_videos:
            return None

        latest = max(all_videos, key=lambda p: p.stat().st_mtime)
        duration = get_video_duration(latest)

        return Video(
            filename=latest.name,
            filepath=str(latest.relative_to(get_project_root())),
            source_type="upload",
            status="ready",
            file_size=latest.stat().st_size,
            duration=duration,
            created_at=datetime.fromtimestamp(latest.stat().st_mtime),
        )

    # ----------------------------
    # Stream / Thumbnail helpers
    # ----------------------------

    def find_video_file(
        self, video_id: str, with_subtitle: bool = False
    ) -> Optional[Path]:
        """Find the video file for streaming"""
        video_dir = self.output_dir / video_id

        if not video_dir.exists():
            return None

        # If subtitle version requested, check for output_sub.mp4
        if with_subtitle:
            sub_path = video_dir / "output_sub.mp4"
            if sub_path.exists():
                return sub_path

        # Find the main video file
        for ext in VIDEO_EXTENSIONS:
            files = [
                f for f in video_dir.glob(f"*{ext}") if not f.name.startswith("output")
            ]
            if files:
                return files[0]

        # Also check for output files if no source found
        for ext in VIDEO_EXTENSIONS:
            files = list(video_dir.glob(f"*{ext}"))
            if files:
                return files[0]

        return None

    def find_thumbnail(self, video_id: str) -> Optional[Path]:
        """Find thumbnail file for a video"""
        thumb_path = self.output_dir / video_id / "thumbnail.jpg"
        if thumb_path.exists():
            return thumb_path
        return None

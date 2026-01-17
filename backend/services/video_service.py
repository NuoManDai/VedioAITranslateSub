"""
Video Service - Business logic for video operations
"""
import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import UploadFile

from models import Video
from api.deps import get_output_dir, get_app_state, get_project_root


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
        print(f"Error getting video duration with cv2: {e}")
    return None


class VideoService:
    """Service for video upload, download, and management"""
    
    def __init__(self):
        self.output_dir = get_output_dir()
    
    async def save_uploaded_video(self, file: UploadFile) -> Video:
        """Save an uploaded video file"""
        state = get_app_state()
        
        # Generate unique filename
        original_name = file.filename or "video.mp4"
        file_ext = Path(original_name).suffix
        unique_filename = f"{uuid.uuid4().hex[:8]}_{original_name}"
        
        # Create video subdirectory if not exists
        video_dir = self.output_dir / "video"
        video_dir.mkdir(exist_ok=True)
        
        # Save file
        file_path = video_dir / unique_filename
        
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Get file size
            file_size = file_path.stat().st_size
            
            # Get video duration
            duration = get_video_duration(file_path)
            
            # Create video record
            video = Video(
                filename=unique_filename,
                filepath=str(file_path.relative_to(get_project_root())),
                source_type='upload',
                status='ready',
                file_size=file_size,
                duration=duration,
                created_at=datetime.now()
            )
            
            # Update app state
            state.current_video = video
            state.subtitle_job = None
            state.dubbing_job = None
            
            return video
            
        except Exception as e:
            # Clean up on error
            if file_path.exists():
                file_path.unlink()
            raise e
    
    async def download_youtube_video(self, url: str, resolution: str) -> Video:
        """Download video from YouTube"""
        import sys
        state = get_app_state()
        
        # Add project root to path for core imports
        project_root = get_project_root()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        try:
            # Import and call core YouTube download function
            from core._1_ytdlp import download_video_ytdlp
            
            # Create video object with downloading status
            video = Video(
                filename="downloading...",
                filepath="",
                source_type='youtube',
                youtube_url=url,
                status='downloading',
                created_at=datetime.now()
            )
            state.current_video = video
            
            # Download video
            download_video_ytdlp(url, resolution)
            
            # Find the downloaded video file
            video_files = list(self.output_dir.glob("*.mp4")) + \
                         list(self.output_dir.glob("*.webm")) + \
                         list(self.output_dir.glob("*.mkv"))
            
            if not video_files:
                raise ValueError("下载失败：未找到视频文件")
            
            # Get the most recent file
            latest_file = max(video_files, key=lambda p: p.stat().st_mtime)
            
            # Get video duration
            duration = get_video_duration(latest_file)
            
            # Update video object
            video.filename = latest_file.name
            video.filepath = str(latest_file.relative_to(get_project_root()))
            video.status = 'ready'
            video.file_size = latest_file.stat().st_size
            video.duration = duration
            
            # Reset processing jobs
            state.subtitle_job = None
            state.dubbing_job = None
            
            return video
            
        except Exception as e:
            if state.current_video:
                state.current_video.status = 'error'
                state.current_video.error_message = str(e)
            raise
    
    async def delete_current_video(self):
        """Delete the current video and all related files"""
        state = get_app_state()
        
        if not state.current_video:
            raise ValueError("没有视频可删除")
        
        # Delete video file
        video_path = get_project_root() / state.current_video.filepath
        if video_path.exists():
            video_path.unlink()
        
        # Clean output directory (optional - keep some files)
        # We'll keep the directory structure but remove processed files
        patterns_to_delete = ['*.srt', '*.json', '*.txt', '*.log']
        for pattern in patterns_to_delete:
            for file in self.output_dir.glob(pattern):
                try:
                    file.unlink()
                except:
                    pass
        
        # Reset state
        state.reset()
    
    def detect_current_video(self) -> Optional[Video]:
        """Try to detect current video from output directory"""
        # Look for video files in output directory
        video_extensions = {'.mp4', '.webm', '.mkv', '.avi', '.mov'}
        
        def find_latest_video(search_dir: Path) -> Optional[Path]:
            for ext in video_extensions:
                videos = list(search_dir.glob(f"*{ext}"))
                if videos:
                    return max(videos, key=lambda p: p.stat().st_mtime)
            return None
        
        # Check main output dir first, then video subdir
        latest = find_latest_video(self.output_dir)
        if not latest:
            video_dir = self.output_dir / "video"
            if video_dir.exists():
                latest = find_latest_video(video_dir)
        
        if latest:
            # Get duration in background - don't block
            duration = get_video_duration(latest)
            
            return Video(
                filename=latest.name,
                filepath=str(latest.relative_to(get_project_root())),
                source_type='upload',
                status='ready',
                file_size=latest.stat().st_size,
                duration=duration,
                created_at=datetime.fromtimestamp(latest.stat().st_mtime)
            )
        
        return None

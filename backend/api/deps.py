"""
API dependencies injection module
"""

from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.log_service import LogStore
    from models import ProcessingJob

# Project root directory (videoLongo/)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Backend directory (videoLongo/backend/)
BACKEND_DIR = Path(__file__).parent.parent

# Output directory for processed files (project_root/output/)
# Unified with core modules which use relative path "output/"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Config file path
CONFIG_FILE = PROJECT_ROOT / "config.yaml"


def get_output_dir() -> Path:
    """Get the output directory path"""
    return OUTPUT_DIR


def get_video_output_dir(video_id: str) -> Path:
    """Get the per-video output directory path: output/{video_id}/"""
    video_dir = OUTPUT_DIR / video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    return video_dir


def get_config_file() -> Path:
    """Get the config file path"""
    return CONFIG_FILE


def get_project_root() -> Path:
    """Get the project root directory"""
    return PROJECT_ROOT


# Global state for current video and processing jobs
# In production, this should be replaced with a proper database or cache
class AppState:
    """Application state management"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.current_video = None
        self.subtitle_job = None
        self.dubbing_job = None
        self._cancel_requested = False
        self._log_store = None
        # Per-video job cache: { video_id: { "subtitle_job": ..., "dubbing_job": ... } }
        self._video_jobs: dict[str, dict[str, Optional["ProcessingJob"]]] = {}

    @property
    def log_store(self) -> "LogStore":
        """Get the log store singleton (lazy initialization)"""
        if self._log_store is None:
            from services.log_service import LogStore

            self._log_store = LogStore()
        return self._log_store

    def get_subtitle_job(self, video_id: str) -> Optional["ProcessingJob"]:
        """Get subtitle job for a specific video.
        Returns the active job if it matches, otherwise checks the cache."""
        if (
            self.subtitle_job
            and getattr(self.subtitle_job, "video_id", None) == video_id
        ):
            return self.subtitle_job
        return self._video_jobs.get(video_id, {}).get("subtitle_job")

    def get_dubbing_job(self, video_id: str) -> Optional["ProcessingJob"]:
        """Get dubbing job for a specific video.
        Returns the active job if it matches, otherwise checks the cache."""
        if self.dubbing_job and getattr(self.dubbing_job, "video_id", None) == video_id:
            return self.dubbing_job
        return self._video_jobs.get(video_id, {}).get("dubbing_job")

    def set_subtitle_job(self, video_id: str, job: Optional["ProcessingJob"]) -> None:
        """Set subtitle job for a specific video into the cache."""
        if video_id not in self._video_jobs:
            self._video_jobs[video_id] = {}
        self._video_jobs[video_id]["subtitle_job"] = job

    def set_dubbing_job(self, video_id: str, job: Optional["ProcessingJob"]) -> None:
        """Set dubbing job for a specific video into the cache."""
        if video_id not in self._video_jobs:
            self._video_jobs[video_id] = {}
        self._video_jobs[video_id]["dubbing_job"] = job

    def clear_video_jobs(self, video_id: str) -> None:
        """Clear cached jobs for a specific video."""
        self._video_jobs.pop(video_id, None)

    def reset(self):
        """Reset all state"""
        self.current_video = None
        self.subtitle_job = None
        self.dubbing_job = None
        self._cancel_requested = False
        self._video_jobs.clear()
        # Don't reset log_store, just clear it
        if self._log_store:
            self._log_store.clear()

    def request_cancel(self):
        """Request cancellation of current processing"""
        self._cancel_requested = True

    def is_cancel_requested(self) -> bool:
        """Check if cancellation is requested"""
        return self._cancel_requested

    def clear_cancel_request(self):
        """Clear cancellation request"""
        self._cancel_requested = False


def get_app_state() -> AppState:
    """Get the application state singleton"""
    return AppState()


def get_log_store() -> "LogStore":
    """Get the log store from application state"""
    return get_app_state().log_store

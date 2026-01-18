"""
API dependencies injection module
"""
from pathlib import Path
from typing import Generator, TYPE_CHECKING
import os

if TYPE_CHECKING:
    from services.log_service import LogStore

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
    
    @property
    def log_store(self) -> 'LogStore':
        """Get the log store singleton (lazy initialization)"""
        if self._log_store is None:
            from services.log_service import LogStore
            self._log_store = LogStore()
        return self._log_store
    
    def reset(self):
        """Reset all state"""
        self.current_video = None
        self.subtitle_job = None
        self.dubbing_job = None
        self._cancel_requested = False
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


def get_log_store() -> 'LogStore':
    """Get the log store from application state"""
    return get_app_state().log_store

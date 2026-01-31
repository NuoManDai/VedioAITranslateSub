"""
Backend models package
"""

from .video import (
    Video,
    VideoCreate,
    VideoResponse,
    VideoSourceType,
    VideoStatus,
    YouTubeDownloadRequest,
)
from .stage import ProcessingStage, StageStatus, get_subtitle_stages, get_dubbing_stages
from .job import ProcessingJob, ProcessingStatus, JobType, JobStatus
from .config import (
    Configuration,
    ConfigurationUpdate,
    ApiConfig,
    WhisperConfig,
    SubtitleConfig,
    SubtitleStyleConfig,
    SubtitleLayoutConfig,
    SubtitleDisplayStyle,
    ApiValidateRequest,
    ApiValidateResponse,
)
from .log import LogEntry, LogQueryResponse
from .tts_config import (
    TTSConfig,
    TTSConfigUpdate,
    TTSConfigResponse,
    TTSMethod,
    AzureVoice,
    AzureVoiceListResponse,
)

__all__ = [
    "Video",
    "VideoCreate",
    "VideoResponse",
    "VideoSourceType",
    "VideoStatus",
    "YouTubeDownloadRequest",
    "ProcessingStage",
    "StageStatus",
    "get_subtitle_stages",
    "get_dubbing_stages",
    "ProcessingJob",
    "ProcessingStatus",
    "JobType",
    "JobStatus",
    "Configuration",
    "ConfigurationUpdate",
    "ApiConfig",
    "WhisperConfig",
    "SubtitleConfig",
    "SubtitleStyleConfig",
    "SubtitleLayoutConfig",
    "SubtitleDisplayStyle",
    "ApiValidateRequest",
    "ApiValidateResponse",
    # New models
    "LogEntry",
    "LogQueryResponse",
    "TTSConfig",
    "TTSConfigUpdate",
    "TTSConfigResponse",
    "TTSMethod",
    "AzureVoice",
    "AzureVoiceListResponse",
]

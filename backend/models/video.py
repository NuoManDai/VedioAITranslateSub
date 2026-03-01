"""
Video data model
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
import uuid


VideoSourceType = Literal["upload", "youtube"]
VideoStatus = Literal[
    "uploading", "downloading", "transcoding", "ready", "processing", "completed", "error"
]


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class VideoBase(BaseModel):
    """Base video model"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    filename: str = Field(..., description="文件名")
    source_type: VideoSourceType = Field(..., description="来源类型")
    youtube_url: Optional[str] = Field(None, description="YouTube 原始链接")


class VideoCreate(VideoBase):
    """Video creation model"""

    pass


class Video(VideoBase):
    """Video model with all fields"""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="视频唯一标识"
    )
    filepath: str = Field(..., description="文件完整路径")
    status: VideoStatus = Field(default="ready", description="视频状态")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    duration: Optional[float] = Field(None, description="视频时长（秒）")
    thumbnail_path: Optional[str] = Field(None, description="Thumbnail image path")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.now, description="Last updated time"
    )
    error_message: Optional[str] = Field(None, description="错误信息")


class VideoResponse(BaseModel):
    """Video response model for API"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    filename: str
    filepath: str
    source_type: VideoSourceType
    youtube_url: Optional[str] = None
    status: VideoStatus
    file_size: Optional[int] = None
    duration: Optional[float] = None
    thumbnail_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None


class YouTubeDownloadRequest(BaseModel):
    """YouTube download request model"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    url: str = Field(..., description="YouTube 视频链接")
    resolution: Literal["360", "1080", "best"] = Field(
        default="1080", description="视频分辨率"
    )


# ----------------------------
# Transcode Status Response
# ----------------------------


TranscodeJobStatus = Literal["none", "pending", "transcoding", "completed", "failed"]


class TranscodeStatusResponse(BaseModel):
    """Response model for video transcode status polling"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    video_id: str
    status: TranscodeJobStatus = "none"
    progress: float = 0.0
    error: Optional[str] = None

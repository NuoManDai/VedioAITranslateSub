"""
Video API routes
"""
import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse

from models import Video, VideoResponse, YouTubeDownloadRequest
from api.deps import get_output_dir, get_app_state, get_project_root
from services.video_service import VideoService

router = APIRouter()
video_service = VideoService()


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    上传视频文件
    
    支持的格式：MP4, AVI, MKV, MOV, WebM
    """
    # Validate file type
    allowed_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.webm', '.m4v'}
    file_ext = Path(file.filename or '').suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}"
        )
    
    try:
        video = await video_service.save_uploaded_video(file)
        return VideoResponse(
            id=video.id,
            filename=video.filename,
            filepath=video.filepath,
            source_type=video.source_type,
            youtube_url=video.youtube_url,
            status=video.status,
            file_size=video.file_size,
            duration=video.duration,
            created_at=video.created_at,
            error_message=video.error_message
        ).model_dump(by_alias=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/youtube")
async def download_youtube(
    request: YouTubeDownloadRequest,
    background_tasks: BackgroundTasks
):
    """
    从 YouTube 下载视频
    
    支持的分辨率: 360p, 1080p, best
    """
    try:
        video = await video_service.download_youtube_video(
            request.url,
            request.resolution
        )
        return VideoResponse(
            id=video.id,
            filename=video.filename,
            filepath=video.filepath,
            source_type=video.source_type,
            youtube_url=video.youtube_url,
            status=video.status,
            file_size=video.file_size,
            duration=video.duration,
            created_at=video.created_at,
            error_message=video.error_message
        ).model_dump(by_alias=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_video():
    """
    获取当前视频信息
    """
    state = get_app_state()
    if not state.current_video:
        # Try to detect video from output directory
        video = video_service.detect_current_video()
        if video:
            state.current_video = video
            return VideoResponse(
                id=video.id,
                filename=video.filename,
                filepath=video.filepath,
                source_type=video.source_type,
                youtube_url=video.youtube_url,
                status=video.status,
                file_size=video.file_size,
                duration=video.duration,
                created_at=video.created_at,
                error_message=video.error_message
            ).model_dump(by_alias=True)
        raise HTTPException(status_code=404, detail="没有视频")
    
    video = state.current_video
    return VideoResponse(
        id=video.id,
        filename=video.filename,
        filepath=video.filepath,
        source_type=video.source_type,
        youtube_url=video.youtube_url,
        status=video.status,
        file_size=video.file_size,
        duration=video.duration,
        created_at=video.created_at,
        error_message=video.error_message
    ).model_dump(by_alias=True)


@router.delete("/current")
async def delete_current_video():
    """
    删除当前视频
    """
    state = get_app_state()
    
    try:
        await video_service.delete_current_video()
        return {"message": "视频已删除"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/{filename}")
async def stream_video(filename: str):
    """
    获取视频流
    """
    output_dir = get_output_dir()
    
    # Try multiple possible locations
    possible_paths = [
        output_dir / filename,
        output_dir / "video" / filename,
        output_dir / "audio" / filename,
    ]
    
    video_path = None
    for path in possible_paths:
        if path.exists():
            video_path = path
            break
    
    if not video_path:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    # Determine content type
    content_type_map = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.mov': 'video/quicktime',
    }
    
    suffix = video_path.suffix.lower()
    content_type = content_type_map.get(suffix, 'video/mp4')
    
    return FileResponse(
        path=str(video_path),
        media_type=content_type,
        filename=filename
    )

"""
Video API routes - Multi-video management
"""

from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from models import VideoResponse, YouTubeDownloadRequest
from api.deps import get_app_state
from services.video_service import VideoService

router = APIRouter()
video_service = VideoService()


def _video_to_response(video) -> dict:
    """Convert Video model to API response dict"""
    return VideoResponse(
        id=video.id,
        filename=video.filename,
        filepath=video.filepath,
        source_type=video.source_type,
        youtube_url=video.youtube_url,
        status=video.status,
        file_size=video.file_size,
        duration=video.duration,
        thumbnail_path=video.thumbnail_path,
        created_at=video.created_at,
        updated_at=video.updated_at,
        error_message=video.error_message,
    ).model_dump(by_alias=True)


# ----------------------------
# Multi-video endpoints
# ----------------------------


@router.get("s")
async def list_videos():
    """
    Get list of all videos from database.
    Maps to GET /api/videos (router prefix is /api/video, route is "s").
    """
    videos = video_service.list_videos()
    return [_video_to_response(v) for v in videos]


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file.
    Saves to output/{video-id}/, creates DB record, returns video with UUID.
    """
    allowed_extensions = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".m4v"}
    file_ext = Path(file.filename or "").suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Allowed: {', '.join(allowed_extensions)}",
        )

    try:
        video = await video_service.save_uploaded_video(file)
        return _video_to_response(video)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/youtube")
async def download_youtube(request: YouTubeDownloadRequest):
    """
    Download video from YouTube.
    Downloads to output/{video-id}/, creates DB record, returns video.
    """
    try:
        video = await video_service.download_youtube_video(
            request.url, request.resolution
        )
        return _video_to_response(video)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------
# Backward compatibility (MUST be before /{video_id} to avoid route conflicts)
# ----------------------------


@router.get("/current")
async def get_current_video():
    """Get the current (most recently updated) video"""
    state = get_app_state()
    if not state.current_video:
        video = video_service.detect_current_video()
        if video:
            state.current_video = video
            return _video_to_response(video)
        raise HTTPException(status_code=404, detail="No video found")

    return _video_to_response(state.current_video)


@router.delete("/current")
async def delete_current_video():
    """Delete the current video (backward compat)"""
    try:
        await video_service.delete_current_video()
        return {"message": "Video deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------
# Per-video endpoints (dynamic {video_id} routes MUST come after static routes)
# ----------------------------


@router.get("/{video_id}")
async def get_video(video_id: str):
    """Get a single video by ID"""
    video = video_service.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return _video_to_response(video)


@router.delete("/{video_id}")
async def delete_video(video_id: str):
    """Delete a video by ID, removing DB record and output/{video-id}/ directory"""
    try:
        video_service.delete_video(video_id)
        return {"message": "Video deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/stream")
async def stream_video(video_id: str, with_subtitle: bool = False):
    """
    Stream video file from output/{video-id}/.
    If with_subtitle=True, returns output_sub.mp4 if available.
    """
    video_path = video_service.find_video_file(video_id, with_subtitle=with_subtitle)
    if not video_path:
        raise HTTPException(status_code=404, detail="Video file not found")

    content_type_map = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".mov": "video/quicktime",
    }

    suffix = video_path.suffix.lower()
    content_type = content_type_map.get(suffix, "video/mp4")

    return FileResponse(
        path=str(video_path),
        media_type=content_type,
        filename=video_path.name,
    )


@router.get("/{video_id}/thumbnail")
async def get_thumbnail(video_id: str):
    """Serve thumbnail image for a video"""
    thumb_path = video_service.find_thumbnail(video_id)
    if not thumb_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(
        path=str(thumb_path),
        media_type="image/jpeg",
        filename="thumbnail.jpg",
    )

"""
Subtitle API routes - Subtitle editing and timeline adjustment
"""

import logging
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from services.subtitle_service import SubtitleService

router = APIRouter()
subtitle_service = SubtitleService()
logger = logging.getLogger(__name__)


# ========== Pydantic Models ==========


class SubtitleEntryModel(BaseModel):
    """Subtitle entry for API"""

    index: int
    startTime: float  # seconds
    endTime: float  # seconds
    text: str  # Translation text
    originalText: Optional[str] = None  # Original text

    class Config:
        populate_by_name = True


class SubtitleDataResponse(BaseModel):
    """Response for subtitle data"""

    entries: List[SubtitleEntryModel]
    files: dict
    totalCount: int


class SaveSubtitlesRequest(BaseModel):
    """Request to save subtitles"""

    entries: List[SubtitleEntryModel]


class SaveSubtitlesResponse(BaseModel):
    """Response after saving subtitles"""

    success: bool
    savedFiles: List[str]
    entryCount: int


class MergeVideoResponse(BaseModel):
    """Response after merging subtitles to video"""

    success: bool
    outputVideo: Optional[str] = None
    exists: Optional[bool] = None
    error: Optional[str] = None


class BackupResponse(BaseModel):
    """Response for backup operation"""

    success: bool
    backedUp: List[str] = []
    skipped: List[str] = []
    backupDir: Optional[str] = None


class RestoreResponse(BaseModel):
    """Response for restore operation"""

    success: bool
    restored: List[str] = []
    message: Optional[str] = None
    error: Optional[str] = None


class HasBackupResponse(BaseModel):
    """Response for backup check"""

    hasBackup: bool


# ========== API Endpoints ==========


@router.get("", response_model=SubtitleDataResponse)
async def get_subtitles():
    """
    Get all subtitle data for editing

    Returns subtitle entries from trans_src.srt (or merged from src.srt + trans.srt)
    Each entry contains both translation and original text.
    """
    try:
        data = subtitle_service.get_all_subtitles()

        # Convert dataclass entries to Pydantic models
        entries = [
            SubtitleEntryModel(
                index=e.index,
                startTime=e.start_time,
                endTime=e.end_time,
                text=e.text,
                originalText=e.original_text,
            )
            for e in data["entries"]
        ]

        return SubtitleDataResponse(
            entries=entries, files=data["files"], totalCount=data["totalCount"]
        )
    except Exception as e:
        logger.error(f"Failed to get subtitles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=SaveSubtitlesResponse)
async def save_subtitles(request: SaveSubtitlesRequest):
    """
    Save edited subtitles to all SRT files

    Updates: src.srt, trans.srt, trans_src.srt, src_trans.srt
    All files are synchronized with the same timing.
    """
    try:
        from services.subtitle_service import SubtitleEntry

        # Convert Pydantic models to dataclass
        entries = [
            SubtitleEntry(
                index=e.index,
                start_time=e.startTime,
                end_time=e.endTime,
                text=e.text,
                original_text=e.originalText,
            )
            for e in request.entries
        ]

        result = subtitle_service.save_all_subtitles(entries)

        return SaveSubtitlesResponse(
            success=result["success"],
            savedFiles=result["savedFiles"],
            entryCount=result["entryCount"],
        )
    except Exception as e:
        logger.error(f"Failed to save subtitles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/merge-video", response_model=MergeVideoResponse)
async def merge_video():
    """
    Manually trigger merging subtitles to video

    This burns the subtitles into the video file.
    Requires subtitle files (src.srt, trans.srt) to exist.
    """
    try:
        result = subtitle_service.merge_subtitles_to_video()

        return MergeVideoResponse(
            success=result["success"],
            outputVideo=result.get("outputVideo"),
            exists=result.get("exists"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"Failed to merge video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio")
async def get_audio_stream():
    """
    Get audio stream for waveform visualization

    Returns the audio file (vocal.mp3 or raw.mp3) for wavesurfer.js
    """
    audio_path = subtitle_service.get_audio_path()

    if not audio_path or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=str(audio_path), media_type="audio/mpeg", filename=audio_path.name
    )


@router.post("/backup", response_model=BackupResponse)
async def backup_subtitles():
    """
    Backup current subtitle files

    Creates a backup of all SRT files before user edits.
    Only backs up if no backup exists (preserves original).
    """
    try:
        result = subtitle_service.backup_original_subtitles()
        return BackupResponse(
            success=result["success"],
            backedUp=result.get("backedUp", []),
            skipped=result.get("skipped", []),
            backupDir=result.get("backupDir"),
        )
    except Exception as e:
        logger.error(f"Failed to backup subtitles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/has-backup", response_model=HasBackupResponse)
async def check_backup():
    """
    Check if subtitle backup exists

    Returns true if original subtitles have been backed up.
    """
    try:
        has_backup = subtitle_service.has_backup()
        return HasBackupResponse(hasBackup=has_backup)
    except Exception as e:
        logger.error(f"Failed to check backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore", response_model=RestoreResponse)
async def restore_subtitles():
    """
    Restore subtitles from backup

    Restores all SRT files to their original state (before any edits).
    Requires backup to exist (call POST /backup first).
    """
    try:
        result = subtitle_service.restore_original_subtitles()
        return RestoreResponse(
            success=result["success"],
            restored=result.get("restored", []),
            message=result.get("message"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"Failed to restore subtitles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
Processing API routes
"""

import os
import sys
import zipfile
from pathlib import Path
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse

from models import ProcessingJob, ProcessingStatus
from api.deps import (
    get_app_state,
    get_output_dir,
    get_project_root,
    get_video_output_dir,
)
from services.processing_service import ProcessingService

# Import cancel flag utilities from core
_project_root = get_project_root()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
from core.utils.config_utils import set_cancel_flag

router = APIRouter()
processing_service = ProcessingService()


@router.post("/subtitle/start")
async def start_subtitle_processing(
    background_tasks: BackgroundTasks,
    video_id: Optional[str] = Query(None),
):
    """
    开始字幕处理

    处理流程：
    1. 语音识别 (ASR)
    2. NLP 分句
    3. 语义分割
    4. 内容总结
    5. 翻译
    6. 字幕分割
    7. 生成字幕
    8. 合并字幕到视频

    Args:
        video_id: Optional video ID to start processing for a specific video
    """
    state = get_app_state()

    # If video_id is provided, load the video and set as current
    if video_id and (state.current_video is None or state.current_video.id != video_id):
        from services.video_service import VideoService

        video_service = VideoService()
        video = video_service.get_video(video_id)
        if video:
            state.current_video = video

    if not state.current_video:
        raise HTTPException(status_code=400, detail="没有视频，请先上传视频")

    # Resolve the actual video_id
    vid = state.current_video.id

    # Check per-video subtitle job status
    sub_job = state.get_subtitle_job(vid)
    if sub_job and sub_job.status == "running":
        raise HTTPException(status_code=400, detail="字幕处理已在进行中")

    try:
        job = processing_service.create_subtitle_job(vid)
        state.subtitle_job = job
        state.set_subtitle_job(vid, job)

        # Start processing in background
        background_tasks.add_task(
            processing_service.run_subtitle_processing, job, state.current_video
        )

        return job.model_dump(by_alias=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dubbing/start", response_model=ProcessingJob)
async def start_dubbing_processing(
    background_tasks: BackgroundTasks,
    video_id: Optional[str] = Query(None),
):
    """
    开始配音处理

    处理流程：
    1. 生成音频任务
    2. 生成配音片段
    3. 提取参考音频
    4. 生成配音
    5. 合并音频
    6. 配音合并到视频

    Args:
        video_id: Optional video ID to start processing for a specific video
    """
    state = get_app_state()

    # If video_id is provided, load the video and set as current
    if video_id and (state.current_video is None or state.current_video.id != video_id):
        from services.video_service import VideoService

        video_service = VideoService()
        video = video_service.get_video(video_id)
        if video:
            state.current_video = video

    if not state.current_video:
        raise HTTPException(status_code=400, detail="没有视频")

    # Resolve the actual video_id
    vid = state.current_video.id

    # Check per-video subtitle job status
    sub_job = state.get_subtitle_job(vid)
    if not sub_job or sub_job.status != "completed":
        raise HTTPException(status_code=400, detail="请先完成字幕处理")

    # Check per-video dubbing job status
    dub_job = state.get_dubbing_job(vid)
    if dub_job and dub_job.status == "running":
        raise HTTPException(status_code=400, detail="配音处理已在进行中")

    try:
        job = processing_service.create_dubbing_job(vid)
        state.dubbing_job = job
        state.set_dubbing_job(vid, job)

        # Start processing in background
        background_tasks.add_task(
            processing_service.run_dubbing_processing, job, state.current_video
        )

        return job
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_processing_status(video_id: Optional[str] = None):
    """
    获取当前处理状态

    Args:
        video_id: Optional video ID. When provided and no current_video is set,
                  loads the video from DB and sets it as the current video.
    """
    state = get_app_state()

    # If video_id is provided and current_video is not set (or is a different video),
    # load the video from DB and set it as current_video
    if video_id and (state.current_video is None or state.current_video.id != video_id):
        from services.video_service import VideoService

        video_service = VideoService()
        video = video_service.get_video(video_id)
        if video:
            state.current_video = video

    # Resolve per-video job state
    current_vid = state.current_video.id if state.current_video else None

    # Get subtitle job for this specific video
    subtitle_job = (
        state.get_subtitle_job(current_vid) if current_vid else state.subtitle_job
    )

    # Try to restore subtitle job state if not exists but processing was completed
    if (
        subtitle_job is None
        or getattr(subtitle_job, "status", None) not in ("running", "completed")
    ) and current_vid:
        restored_job = processing_service.restore_job_state(
            "subtitle", video_id=current_vid
        )
        if restored_job:
            subtitle_job = restored_job
            state.set_subtitle_job(current_vid, restored_job)

    # Get dubbing job for this specific video
    dubbing_job = (
        state.get_dubbing_job(current_vid) if current_vid else state.dubbing_job
    )

    # Try to restore dubbing job state if not exists but processing was completed
    if (
        dubbing_job is None
        or getattr(dubbing_job, "status", None) not in ("running", "completed")
    ) and current_vid:
        restored_job = processing_service.restore_job_state(
            "dubbing", video_id=current_vid
        )
        if restored_job:
            dubbing_job = restored_job
            state.set_dubbing_job(current_vid, restored_job)

    # Check for unfinished task
    has_unfinished = False
    if subtitle_job and subtitle_job.status == "running":
        has_unfinished = True
    if dubbing_job and dubbing_job.status == "running":
        has_unfinished = True

    # Also check output directory for incomplete processing
    if not has_unfinished:
        has_unfinished = processing_service.detect_unfinished_task(video_id=current_vid)

    # Determine if subtitle processing can start
    # Can start if: video exists AND no subtitle job OR subtitle job failed/cancelled (not completed/running/pending)
    can_start_subtitle = state.current_video is not None and (
        subtitle_job is None or subtitle_job.status in ("failed", "cancelled")
    )

    # Determine if dubbing processing can start
    # Can start if: video exists AND subtitle completed AND no dubbing job running
    can_start_dubbing = (
        state.current_video is not None
        and subtitle_job is not None
        and subtitle_job.status == "completed"
        and (dubbing_job is None or dubbing_job.status not in ("running", "pending"))
    )

    # Check if subtitle has been merged into video (output_sub.mp4 exists)
    if current_vid:
        video_output_dir = get_video_output_dir(current_vid)
        subtitle_merged = (video_output_dir / "output_sub.mp4").exists()
    else:
        output_dir = get_output_dir()
        subtitle_merged = (output_dir / "output_sub.mp4").exists()

    status = ProcessingStatus(
        video=state.current_video.model_dump(by_alias=True)
        if state.current_video
        else None,
        subtitle_job=subtitle_job,
        dubbing_job=dubbing_job,
        has_unfinished_task=has_unfinished,
        can_start_subtitle=can_start_subtitle,
        can_start_dubbing=can_start_dubbing,
        subtitle_merged=subtitle_merged,
    )
    return status.model_dump(by_alias=True)


@router.post("/cancel")
async def cancel_processing():
    """
    取消当前处理
    """
    state = get_app_state()

    if not state.subtitle_job and not state.dubbing_job:
        raise HTTPException(status_code=400, detail="没有正在进行的处理")

    # Request cancellation - set both in-memory flag and file flag
    state.request_cancel()
    set_cancel_flag()  # Set file-based flag for core modules

    # Also write cancel flag in workspace for active dubbing jobs
    if state.dubbing_job and state.dubbing_job.status == "running":
        from services.core_path_manager import get_workspace_root
        active_vid = state.current_video.id if state.current_video else None
        if active_vid:
            workspace_cancel = get_workspace_root(active_vid) / "output" / ".cancel_requested"
            try:
                workspace_cancel.parent.mkdir(parents=True, exist_ok=True)
                workspace_cancel.touch(exist_ok=True)
            except OSError:
                pass

    # Update job status
    if state.subtitle_job and state.subtitle_job.status == "running":
        state.subtitle_job.cancel()
    if state.dubbing_job and state.dubbing_job.status == "running":
        state.dubbing_job.cancel()

    return {"message": "取消请求已发送"}


@router.get("/download/srt")
async def download_srt(video_id: Optional[str] = None):
    """
    下载字幕文件

    返回包含所有字幕文件的 ZIP 压缩包

    Args:
        video_id: Optional video ID to find SRT in output/{video_id}/ directory
    """
    state = get_app_state()

    # Resolve video_id from request or current_video
    vid = video_id or (state.current_video.id if state.current_video else None)

    # Determine output directory: per-video or global
    if vid:
        output_dir = get_video_output_dir(vid)
    else:
        output_dir = get_output_dir()

    # Find SRT files
    srt_files = list(output_dir.glob("*.srt"))
    if not srt_files:
        # Also check subdirectories
        srt_files = list(output_dir.glob("**/*.srt"))

    if not srt_files:
        raise HTTPException(status_code=404, detail="字幕文件不存在")

    # Create ZIP file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for srt_path in srt_files:
            zip_file.write(srt_path, srt_path.name)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=subtitles.zip"},
    )


# ============ Cleanup API ============


@router.post("/cleanup/subtitle")
async def cleanup_subtitle_files(video_id: Optional[str] = None):
    """
    清理字幕处理相关的中间文件

    清理内容:
    - log/ 目录
    - gpt_log/ 目录
    - *.srt 文件
    - 保留 audio/raw.mp3

    Args:
        video_id: Optional video ID to clean output/{video_id}/ directory
    """
    state = get_app_state()

    # Resolve video_id from request or current_video
    vid = video_id or (state.current_video.id if state.current_video else None)

    # Don't allow cleanup while processing
    if vid:
        sub_job = state.get_subtitle_job(vid)
        if sub_job and sub_job.status == "running":
            raise HTTPException(status_code=400, detail="字幕处理进行中，无法清理文件")
    elif state.subtitle_job and state.subtitle_job.status == "running":
        raise HTTPException(status_code=400, detail="字幕处理进行中，无法清理文件")

    try:
        result = processing_service.cleanup_subtitle_files(video_id=vid)

        # Reset subtitle job state for this video
        if vid:
            state.set_subtitle_job(vid, None)
        state.subtitle_job = None

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup/dubbing")
async def cleanup_dubbing_files(video_id: Optional[str] = None):
    """
    清理配音处理相关的中间文件

    清理内容:
    - audio/segs/ 目录
    - audio/refers/ 目录
    - audio/tmp/ 目录

    Args:
        video_id: Optional video ID to clean output/{video_id}/ directory
    """
    state = get_app_state()

    # Resolve video_id from request or current_video
    vid = video_id or (state.current_video.id if state.current_video else None)

    # Don't allow cleanup while processing
    if vid:
        dub_job = state.get_dubbing_job(vid)
        if dub_job and dub_job.status == "running":
            raise HTTPException(status_code=400, detail="配音处理进行中，无法清理文件")
    elif state.dubbing_job and state.dubbing_job.status == "running":
        raise HTTPException(status_code=400, detail="配音处理进行中，无法清理文件")

    try:
        result = processing_service.cleanup_dubbing_files(video_id=vid)

        # Reset dubbing job state for this video
        if vid:
            state.set_dubbing_job(vid, None)
        state.dubbing_job = None

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup/all")
async def cleanup_all_files(video_id: Optional[str] = None):
    """
    清理所有处理文件，重新开始

    清理内容:
    - output/log/ 目录
    - output/gpt_log/ 目录
    - output/audio/ 目录 (包括所有音频文件)
    - 所有 *.srt, output*.mp4, *.xlsx, *.json, *.mp3 文件

    保留:
    - 原始视频文件

    如果有任务正在运行，会先取消再清理。

    Args:
        video_id: Optional video ID to clean output/{video_id}/ directory
    """
    state = get_app_state()

    # Resolve video_id from request or current_video
    vid = video_id or (state.current_video.id if state.current_video else None)

    # Force-cancel any running jobs before cleanup
    if state.subtitle_job and state.subtitle_job.status == "running":
        state.request_cancel()
        set_cancel_flag()
        state.subtitle_job.cancel()
    if state.dubbing_job and state.dubbing_job.status == "running":
        state.request_cancel()
        set_cancel_flag()
        state.dubbing_job.cancel()

    try:
        result = processing_service.cleanup_all_files(video_id=vid)

        # Reset all job states for this video
        if vid:
            state.clear_video_jobs(vid)
        state.subtitle_job = None
        state.dubbing_job = None
        state.clear_cancel_request()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

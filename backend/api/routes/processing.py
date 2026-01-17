"""
Processing API routes
"""
import os
import zipfile
from pathlib import Path
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from models import ProcessingJob, ProcessingStatus
from api.deps import get_app_state, get_output_dir
from services.processing_service import ProcessingService

router = APIRouter()
processing_service = ProcessingService()


@router.post("/subtitle/start")
async def start_subtitle_processing(background_tasks: BackgroundTasks):
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
    """
    state = get_app_state()
    
    if not state.current_video:
        raise HTTPException(status_code=400, detail="没有视频，请先上传视频")
    
    if state.subtitle_job and state.subtitle_job.status == 'running':
        raise HTTPException(status_code=400, detail="字幕处理已在进行中")
    
    try:
        job = processing_service.create_subtitle_job(state.current_video.id)
        state.subtitle_job = job
        
        # Start processing in background
        background_tasks.add_task(
            processing_service.run_subtitle_processing,
            job,
            state.current_video
        )
        
        return job.model_dump(by_alias=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dubbing/start", response_model=ProcessingJob)
async def start_dubbing_processing(background_tasks: BackgroundTasks):
    """
    开始配音处理
    
    处理流程：
    1. 生成音频任务
    2. 生成配音片段
    3. 提取参考音频
    4. 生成配音
    5. 合并音频
    6. 配音合并到视频
    """
    state = get_app_state()
    
    if not state.current_video:
        raise HTTPException(status_code=400, detail="没有视频")
    
    if not state.subtitle_job or state.subtitle_job.status != 'completed':
        raise HTTPException(status_code=400, detail="请先完成字幕处理")
    
    if state.dubbing_job and state.dubbing_job.status == 'running':
        raise HTTPException(status_code=400, detail="配音处理已在进行中")
    
    try:
        job = processing_service.create_dubbing_job(state.current_video.id)
        state.dubbing_job = job
        
        # Start processing in background
        background_tasks.add_task(
            processing_service.run_dubbing_processing,
            job,
            state.current_video
        )
        
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_processing_status():
    """
    获取当前处理状态
    """
    state = get_app_state()
    
    # Check for unfinished task
    has_unfinished = False
    if state.subtitle_job and state.subtitle_job.status == 'running':
        has_unfinished = True
    if state.dubbing_job and state.dubbing_job.status == 'running':
        has_unfinished = True
    
    # Also check output directory for incomplete processing
    if not has_unfinished:
        has_unfinished = processing_service.detect_unfinished_task()
    
    status = ProcessingStatus(
        video=state.current_video.model_dump(by_alias=True) if state.current_video else None,
        subtitle_job=state.subtitle_job,
        dubbing_job=state.dubbing_job,
        has_unfinished_task=has_unfinished
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
    
    # Request cancellation
    state.request_cancel()
    
    # Update job status
    if state.subtitle_job and state.subtitle_job.status == 'running':
        state.subtitle_job.cancel()
    if state.dubbing_job and state.dubbing_job.status == 'running':
        state.dubbing_job.cancel()
    
    return {"message": "取消请求已发送"}


@router.get("/download/srt")
async def download_srt():
    """
    下载字幕文件
    
    返回包含所有字幕文件的 ZIP 压缩包
    """
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
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for srt_path in srt_files:
            zip_file.write(srt_path, srt_path.name)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=subtitles.zip"}
    )

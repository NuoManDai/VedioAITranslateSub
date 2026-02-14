"""
Batch API routes
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from models.batch_models import BatchFileRegister, BatchFileSettingsUpdate
from services.batch_service import BatchService
from services.batch_processing_service import BatchProcessingService
from api.deps import get_project_root, get_app_state

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize batch service with default database path
batch_service = BatchService(db_path="data/batch.db")
batch_processing_service = BatchProcessingService(batch_service)


# ------------
# Helper Functions
# ------------


def _get_batch_upload_dir(job_id: str) -> Path:
    """Get upload directory for a batch job"""
    project_root = get_project_root()
    upload_dir = project_root / "batch" / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


# ------------
# Batch Management Endpoints
# ------------


@router.post("/")
async def create_batch():
    """
    Create a new batch job

    Returns:
        {"jobId": "uuid-string"}
    """
    try:
        job_id = batch_service.create_batch()
        logger.info(f"Batch created: {job_id}")
        return {"jobId": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_batches():
    """
    List all batch jobs

    Returns:
        List of batch job objects with files
    """
    try:
        batches = batch_service.list_batches()
        return [batch.model_dump(by_alias=True) for batch in batches]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/status")
async def get_batch_status(job_id: str):
    """
    Get batch job status with all files

    Args:
        job_id: Batch job ID

    Returns:
        Batch job object with all files
    """
    try:
        batch = batch_service.get_batch_status(job_id)
        if not batch:
            raise HTTPException(status_code=404, detail="批次不存在")

        return batch.model_dump(by_alias=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/start")
async def start_batch_processing(job_id: str, background_tasks: BackgroundTasks):
    """
    Start batch processing

    Args:
        job_id: Batch job ID

    Returns:
        Updated batch job object
    """
    try:
        # Mutual exclusion: check if single-file processing is active
        state = get_app_state()
        if (state.subtitle_job and state.subtitle_job.status == "running") or (
            state.dubbing_job and state.dubbing_job.status == "running"
        ):
            raise HTTPException(
                status_code=409, detail="单文件处理正在进行中，无法启动批量处理"
            )

        # Mutual exclusion: check if another batch is already processing
        if batch_service.is_batch_processing():
            raise HTTPException(status_code=409, detail="已有批量任务正在处理中")

        # Check if batch exists
        batch = batch_service.get_batch_status(job_id)
        if not batch:
            raise HTTPException(status_code=404, detail="批次不存在")

        # Check if batch has files
        if not batch.files or len(batch.files) == 0:
            raise HTTPException(status_code=400, detail="批次中没有文件")

        # Check if batch is already finished
        if batch.status in ("completed", "failed", "cancelled"):
            raise HTTPException(status_code=400, detail="批次已结束，无法重新启动")

        # Update job status to processing
        batch_service.update_job_status(job_id, "processing")

        # Start background processing
        background_tasks.add_task(batch_processing_service.process_batch, job_id)
        logger.info(f"Batch processing started: {job_id}, files={len(batch.files)}")

        # Return updated batch
        updated_batch = batch_service.get_batch_status(job_id)
        if not updated_batch:
            raise HTTPException(status_code=500, detail="更新失败")
        return updated_batch.model_dump(by_alias=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/cancel")
async def cancel_batch(job_id: str):
    """
    Cancel batch job and all pending files

    Args:
        job_id: Batch job ID

    Returns:
        Updated batch job object
    """
    try:
        # Check if batch exists
        batch = batch_service.get_batch_status(job_id)
        if not batch:
            raise HTTPException(status_code=404, detail="批次不存在")

        # Check if batch is already finished
        if batch.status in ("completed", "failed"):
            raise HTTPException(status_code=400, detail="批次已结束，无法取消")

        # Signal processing service to stop
        batch_processing_service.request_cancel()

        # Cancel the batch
        batch_service.cancel_batch(job_id)
        logger.info(f"Batch cancelled: {job_id}")

        # Return updated batch
        updated_batch = batch_service.get_batch_status(job_id)
        if not updated_batch:
            raise HTTPException(status_code=500, detail="取消失败")
        return updated_batch.model_dump(by_alias=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------
# File Management Endpoints
# ------------


@router.post("/{job_id}/files")
async def register_file(job_id: str, file_data: BatchFileRegister):
    """
    Register a file to a batch job

    Args:
        job_id: Batch job ID
        file_data: File registration data (filename, optional settings)

    Returns:
        Created file object
    """
    try:
        # Check if batch exists
        batch = batch_service.get_batch_status(job_id)
        if not batch:
            raise HTTPException(status_code=404, detail="批次不存在")

        # Add file to batch
        file_id = batch_service.add_file_to_batch(
            job_id=job_id,
            filename=file_data.filename,
            source_lang=file_data.source_lang,
            target_lang=file_data.target_lang,
            dubbing=file_data.dubbing,
        )
        logger.info(f"File registered: {file_data.filename} -> batch {job_id}")

        # Get created file
        created_file = batch_service.get_file(file_id)
        if not created_file:
            raise HTTPException(status_code=500, detail="文件创建失败")

        return created_file.model_dump(by_alias=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{job_id}/files/{file_id}/upload")
async def upload_file(job_id: str, file_id: str, file: UploadFile = File(...)):
    """
    Upload file content

    Args:
        job_id: Batch job ID
        file_id: File ID
        file: File content

    Returns:
        Updated file object
    """
    # Validate file type
    allowed_extensions = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".m4v"}
    file_ext = Path(file.filename or "").suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}",
        )

    try:
        # Check if file record exists
        file_record = batch_service.get_file(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件记录不存在")

        # Get upload directory
        upload_dir = _get_batch_upload_dir(job_id)
        filename = file.filename or "unknown"
        file_path = upload_dir / filename

        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"File uploaded: {filename} -> {file_path}")

        # Update file path and status
        batch_service.update_file_path(file_id, str(file_path))
        batch_service.update_file_status(file_id, "queued")

        # Return updated file
        updated_file = batch_service.get_file(file_id)
        if not updated_file:
            raise HTTPException(status_code=500, detail="上传失败")
        return updated_file.model_dump(by_alias=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{job_id}/files/{file_id}")
async def update_file_settings(
    job_id: str, file_id: str, settings: BatchFileSettingsUpdate
):
    """
    Update file settings (source_lang, target_lang, dubbing)

    Args:
        job_id: Batch job ID
        file_id: File ID
        settings: File settings to update

    Returns:
        Updated file object
    """
    try:
        # Check if file exists
        file_record = batch_service.get_file(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")

        # Update settings
        batch_service.update_file_settings(
            job_id=job_id,
            file_id=file_id,
            source_lang=settings.source_lang,
            target_lang=settings.target_lang,
            dubbing=settings.dubbing,
        )

        # Return updated file
        updated_file = batch_service.get_file(file_id)
        if not updated_file:
            raise HTTPException(status_code=500, detail="更新失败")
        return updated_file.model_dump(by_alias=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}/files/{file_id}")
async def remove_file(job_id: str, file_id: str):
    """
    Remove a file from batch job

    Args:
        job_id: Batch job ID
        file_id: File ID

    Returns:
        Success message
    """
    try:
        # Check if file exists
        file_record = batch_service.get_file(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")

        # Delete file from filesystem if exists
        if file_record.filepath:
            file_path = Path(file_record.filepath)
            if file_path.exists():
                file_path.unlink()

        # Remove file from database
        batch_service.remove_file_from_batch(job_id, file_id)
        logger.info(f"File removed: {file_id} from batch {job_id}")

        return {"message": "文件已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

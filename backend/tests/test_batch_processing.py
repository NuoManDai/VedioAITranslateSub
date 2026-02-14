"""
Test batch processing service
"""

import os
import sys
import tempfile
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from database.batch_db import BatchDB
from services.batch_service import BatchService
from services.batch_processing_service import BatchProcessingService
from models.batch_models import BatchFile, BatchJob


def run_async(coro):
    """Run async coroutine in sync test (pytest-asyncio not installed)"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ------------
# Fixtures
# ------------


@pytest.fixture
def tmp_dirs(tmp_path):
    """Create temporary directories for testing"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    project_root = tmp_path
    batch_output = tmp_path / "batch" / "output"
    batch_output.mkdir(parents=True)
    return {
        "root": project_root,
        "output": output_dir,
        "batch_output": batch_output,
    }


@pytest.fixture
def test_db_path(tmp_path):
    """Create temporary database file"""
    return str(tmp_path / "test_batch.db")


@pytest.fixture
def batch_service(test_db_path):
    """Create batch service with test database"""
    return BatchService(db_path=test_db_path)


@pytest.fixture
def processing_service(batch_service, tmp_dirs):
    """Create batch processing service with mocked paths"""
    with (
        patch(
            "services.batch_processing_service.get_project_root",
            return_value=tmp_dirs["root"],
        ),
        patch(
            "services.batch_processing_service.get_output_dir",
            return_value=tmp_dirs["output"],
        ),
    ):
        service = BatchProcessingService(batch_service)
    return service


@pytest.fixture
def sample_video(tmp_dirs):
    """Create a sample video file for testing"""
    video_path = tmp_dirs["root"] / "test_video.mp4"
    video_path.write_bytes(b"fake video content")
    return str(video_path)


@pytest.fixture
def batch_with_file(batch_service, sample_video):
    """Create a batch job with one uploaded file"""
    job_id = batch_service.create_batch()
    file_id = batch_service.add_file_to_batch(
        job_id=job_id,
        filename="test_video.mp4",
        filepath=sample_video,
        source_lang="ja",
        target_lang="简体中文",
        dubbing=False,
    )
    # Mark file as queued (simulating upload complete)
    batch_service.update_file_status(file_id, "queued")
    return job_id, file_id


@pytest.fixture
def batch_with_dubbing_file(batch_service, sample_video):
    """Create a batch job with one file that has dubbing enabled"""
    job_id = batch_service.create_batch()
    file_id = batch_service.add_file_to_batch(
        job_id=job_id,
        filename="test_video.mp4",
        filepath=sample_video,
        source_lang="en",
        target_lang="简体中文",
        dubbing=True,
    )
    batch_service.update_file_status(file_id, "queued")
    return job_id, file_id


@pytest.fixture
def batch_with_multiple_files(batch_service, tmp_dirs):
    """Create a batch job with multiple files"""
    job_id = batch_service.create_batch()
    file_ids = []
    for i in range(3):
        video_path = tmp_dirs["root"] / f"video_{i}.mp4"
        video_path.write_bytes(f"fake video {i}".encode())
        file_id = batch_service.add_file_to_batch(
            job_id=job_id,
            filename=f"video_{i}.mp4",
            filepath=str(video_path),
            source_lang="ja",
            target_lang="简体中文",
            dubbing=False,
        )
        batch_service.update_file_status(file_id, "queued")
        file_ids.append(file_id)
    return job_id, file_ids


# ------------
# Cancel Flag Tests
# ------------


def test_cancel_request_default(processing_service):
    """Cancel flag starts as False"""
    assert processing_service.is_cancel_requested() is False


def test_request_cancel(processing_service):
    """request_cancel sets the flag"""
    processing_service.request_cancel()
    assert processing_service.is_cancel_requested() is True


def test_clear_cancel_request(processing_service):
    """clear_cancel_request resets the flag"""
    processing_service.request_cancel()
    processing_service.clear_cancel_request()
    assert processing_service.is_cancel_requested() is False


# ------------
# Output Directory Management Tests
# ------------


def test_clean_output_dir(processing_service, tmp_dirs):
    """_clean_output_dir removes everything from output/"""
    output_dir = tmp_dirs["output"]
    # Create some files
    (output_dir / "test.srt").write_text("test")
    (output_dir / "subdir").mkdir()
    (output_dir / "subdir" / "file.txt").write_text("test")

    processing_service._clean_output_dir()

    assert output_dir.exists()
    assert list(output_dir.iterdir()) == []


def test_clean_output_dir_creates_if_missing(processing_service, tmp_dirs):
    """_clean_output_dir creates output/ if it doesn't exist"""
    import shutil

    output_dir = tmp_dirs["output"]
    shutil.rmtree(str(output_dir))

    processing_service._clean_output_dir()

    assert output_dir.exists()


def test_copy_video_to_output(processing_service, tmp_dirs, sample_video):
    """_copy_video_to_output copies file to output/"""
    filename = processing_service._copy_video_to_output(sample_video)

    assert filename == "test_video.mp4"
    copied = tmp_dirs["output"] / "test_video.mp4"
    assert copied.exists()
    assert copied.read_bytes() == b"fake video content"


def test_copy_video_to_output_not_found(processing_service):
    """_copy_video_to_output raises error if file doesn't exist"""
    with pytest.raises(FileNotFoundError):
        processing_service._copy_video_to_output("/nonexistent/video.mp4")


def test_save_output(processing_service, tmp_dirs):
    """_save_output copies output/ to batch/output/{video_name}/"""
    output_dir = tmp_dirs["output"]
    # Simulate processed files in output/
    (output_dir / "output_sub.mp4").write_bytes(b"subtitled video")
    (output_dir / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHello")

    result_path = processing_service._save_output("test_video.mp4")

    assert Path(result_path).exists()
    assert (Path(result_path) / "output_sub.mp4").exists()
    assert (Path(result_path) / "subtitles.srt").exists()


# ------------
# Config Update Tests
# ------------


def test_update_config_for_file(processing_service, batch_service, sample_video):
    """_update_config_for_file calls config service with correct params"""
    file = BatchFile(
        job_id="test",
        filename="test.mp4",
        filepath=sample_video,
        source_lang="ja",
        target_lang="简体中文",
    )

    with patch.object(
        processing_service.config_service, "update_config"
    ) as mock_update:
        processing_service._update_config_for_file(file)

        mock_update.assert_called_once()
        config_arg = mock_update.call_args[0][0]
        # Check it sets source language via whisper config
        assert config_arg.whisper is not None
        assert config_arg.source_language == "ja"
        assert config_arg.target_language == "简体中文"


def test_update_config_auto_source_lang(processing_service):
    """_update_config_for_file skips whisper config when source_lang is 'auto'"""
    file = BatchFile(
        job_id="test",
        filename="test.mp4",
        source_lang="auto",
        target_lang="English",
    )

    with patch.object(
        processing_service.config_service, "update_config"
    ) as mock_update:
        processing_service._update_config_for_file(file)

        mock_update.assert_called_once()
        config_arg = mock_update.call_args[0][0]
        assert config_arg.whisper is None
        assert config_arg.target_language == "English"


# ------------
# Pipeline Stage Tests
# ------------


def test_run_stage_success(processing_service):
    """_run_stage runs a function in a thread"""
    called = False

    def stage_func():
        nonlocal called
        called = True

    run_async(processing_service._run_stage("test_stage", stage_func))
    assert called is True


def test_run_stage_failure(processing_service):
    """_run_stage re-raises exceptions from stage"""

    def bad_stage():
        raise ValueError("stage failed")

    with pytest.raises(ValueError, match="stage failed"):
        run_async(processing_service._run_stage("bad_stage", bad_stage))


def test_subtitle_pipeline_runs_all_stages(processing_service):
    """_run_subtitle_pipeline runs all 8 stages"""
    stage_calls = []

    async def mock_run_stage(name, func):
        stage_calls.append(name)

    with patch.object(processing_service, "_run_stage", side_effect=mock_run_stage):
        run_async(processing_service._run_subtitle_pipeline())

    expected_stages = [
        "asr",
        "split_nlp",
        "split_meaning",
        "summarize",
        "translate",
        "split_sub",
        "gen_sub",
        "merge_sub",
    ]
    assert stage_calls == expected_stages


def test_dubbing_pipeline_runs_all_stages(processing_service):
    """_run_dubbing_pipeline runs all 6 stages"""
    stage_calls = []

    async def mock_run_stage(name, func):
        stage_calls.append(name)

    with patch.object(processing_service, "_run_stage", side_effect=mock_run_stage):
        run_async(processing_service._run_dubbing_pipeline())

    expected_stages = [
        "audio_task",
        "dub_chunks",
        "refer_audio",
        "gen_audio",
        "merge_audio",
        "dub_to_vid",
    ]
    assert stage_calls == expected_stages


def test_subtitle_pipeline_cancellation(processing_service):
    """_run_subtitle_pipeline stops on cancel"""
    stage_calls = []

    async def mock_run_stage(name, func):
        stage_calls.append(name)
        if name == "split_nlp":
            processing_service.request_cancel()

    with patch.object(processing_service, "_run_stage", side_effect=mock_run_stage):
        with pytest.raises(asyncio.CancelledError):
            run_async(processing_service._run_subtitle_pipeline())

    # Should have run asr and split_nlp, then stopped before split_meaning
    assert stage_calls == ["asr", "split_nlp"]


# ------------
# Single File Processing Tests
# ------------


def test_process_single_file_success(
    processing_service, batch_service, batch_with_file
):
    """_process_single_file completes successfully with mocked pipeline"""
    job_id, file_id = batch_with_file

    file = batch_service.get_file(file_id)
    assert file is not None

    with (
        patch.object(
            processing_service, "_run_subtitle_pipeline", new_callable=AsyncMock
        ),
        patch.object(processing_service.config_service, "update_config"),
    ):
        result = run_async(processing_service._process_single_file(file))

    assert result is not None
    assert Path(result).exists()

    # Verify file status updated to completed
    updated_file = batch_service.get_file(file_id)
    assert updated_file is not None
    assert updated_file.status == "completed"


def test_process_single_file_with_dubbing(
    processing_service, batch_service, batch_with_dubbing_file
):
    """_process_single_file runs dubbing pipeline when dubbing=True"""
    job_id, file_id = batch_with_dubbing_file

    file = batch_service.get_file(file_id)
    assert file is not None

    with (
        patch.object(
            processing_service, "_run_subtitle_pipeline", new_callable=AsyncMock
        ) as mock_sub,
        patch.object(
            processing_service, "_run_dubbing_pipeline", new_callable=AsyncMock
        ) as mock_dub,
        patch.object(processing_service.config_service, "update_config"),
    ):
        result = run_async(processing_service._process_single_file(file))

    mock_sub.assert_called_once()
    mock_dub.assert_called_once()
    assert result is not None


def test_process_single_file_failure(
    processing_service, batch_service, batch_with_file
):
    """_process_single_file marks file as failed on error"""
    job_id, file_id = batch_with_file

    file = batch_service.get_file(file_id)
    assert file is not None

    with (
        patch.object(
            processing_service, "_run_subtitle_pipeline", new_callable=AsyncMock
        ) as mock_pipeline,
        patch.object(processing_service.config_service, "update_config"),
    ):
        mock_pipeline.side_effect = RuntimeError("ASR crashed")
        result = run_async(processing_service._process_single_file(file))

    assert result is None

    updated_file = batch_service.get_file(file_id)
    assert updated_file is not None
    assert updated_file.status == "failed"
    assert "ASR crashed" in (updated_file.error_message or "")


def test_process_single_file_no_filepath(processing_service, batch_service):
    """_process_single_file fails when file has no filepath"""
    job_id = batch_service.create_batch()
    file_id = batch_service.add_file_to_batch(
        job_id=job_id,
        filename="test.mp4",
    )
    batch_service.update_file_status(file_id, "queued")

    file = batch_service.get_file(file_id)
    assert file is not None
    assert file.filepath is None

    with patch.object(processing_service.config_service, "update_config"):
        result = run_async(processing_service._process_single_file(file))

    assert result is None
    updated_file = batch_service.get_file(file_id)
    assert updated_file is not None
    assert updated_file.status == "failed"


# ------------
# Batch Processing Tests
# ------------


def test_process_batch_success(processing_service, batch_service, batch_with_file):
    """process_batch processes all files and marks job completed"""
    job_id, file_id = batch_with_file

    with patch.object(
        processing_service, "_process_single_file", new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = "/some/output/path"
        run_async(processing_service.process_batch(job_id))

    mock_process.assert_called_once()

    job = batch_service.get_batch_status(job_id)
    assert job is not None
    assert job.status == "completed"


def test_process_batch_multiple_files(
    processing_service, batch_service, batch_with_multiple_files
):
    """process_batch processes all files sequentially"""
    job_id, file_ids = batch_with_multiple_files

    call_order = []

    async def mock_process(batch_file):
        call_order.append(batch_file.filename)
        return f"/output/{batch_file.filename}"

    with patch.object(
        processing_service, "_process_single_file", side_effect=mock_process
    ):
        run_async(processing_service.process_batch(job_id))

    assert len(call_order) == 3
    assert call_order == ["video_0.mp4", "video_1.mp4", "video_2.mp4"]

    job = batch_service.get_batch_status(job_id)
    assert job is not None
    assert job.status == "completed"


def test_process_batch_best_effort(
    processing_service, batch_service, batch_with_multiple_files
):
    """process_batch continues even if one file fails"""
    job_id, file_ids = batch_with_multiple_files

    call_count = 0

    async def mock_process(batch_file):
        nonlocal call_count
        call_count += 1
        if batch_file.filename == "video_1.mp4":
            return None  # Simulates failure
        return f"/output/{batch_file.filename}"

    with patch.object(
        processing_service, "_process_single_file", side_effect=mock_process
    ):
        run_async(processing_service.process_batch(job_id))

    # All 3 files should have been attempted
    assert call_count == 3

    job = batch_service.get_batch_status(job_id)
    assert job is not None
    # completed because some files succeeded
    assert job.status == "completed"


def test_process_batch_all_failed(
    processing_service, batch_service, batch_with_multiple_files
):
    """process_batch marks job as failed when all files fail"""
    job_id, file_ids = batch_with_multiple_files

    # Mark all files' status to track processing
    for fid in file_ids:
        batch_service.update_file_status(fid, "queued")

    async def mock_process(batch_file):
        # Simulate failure by updating status and returning None
        batch_service.update_file_status(batch_file.id, "failed", error_message="error")
        return None

    with patch.object(
        processing_service, "_process_single_file", side_effect=mock_process
    ):
        run_async(processing_service.process_batch(job_id))

    job = batch_service.get_batch_status(job_id)
    assert job is not None
    assert job.status == "failed"


def test_process_batch_cancellation(
    processing_service, batch_service, batch_with_multiple_files
):
    """process_batch stops processing when cancel is requested"""
    job_id, file_ids = batch_with_multiple_files

    processed = []

    async def mock_process(batch_file):
        processed.append(batch_file.filename)
        # Request cancel after first file
        if len(processed) == 1:
            processing_service.request_cancel()
        return f"/output/{batch_file.filename}"

    with patch.object(
        processing_service, "_process_single_file", side_effect=mock_process
    ):
        run_async(processing_service.process_batch(job_id))

    # Only 1 file should have been processed before cancel check kicked in
    assert len(processed) == 1


def test_process_batch_empty_job(processing_service, batch_service):
    """process_batch handles job with no files"""
    job_id = batch_service.create_batch()

    run_async(processing_service.process_batch(job_id))

    job = batch_service.get_batch_status(job_id)
    assert job is not None
    assert job.status == "completed"


def test_process_batch_nonexistent_job(processing_service):
    """process_batch handles nonexistent job gracefully"""
    # Should not raise, just log and return
    run_async(processing_service.process_batch("nonexistent-job-id"))


def test_process_batch_skips_non_pending(
    processing_service, batch_service, batch_with_multiple_files
):
    """process_batch skips files that are already completed or failed"""
    job_id, file_ids = batch_with_multiple_files

    # Mark first file as completed already
    batch_service.update_file_status(file_ids[0], "completed")
    # Mark second file as failed already
    batch_service.update_file_status(file_ids[1], "failed")

    processed = []

    async def mock_process(batch_file):
        processed.append(batch_file.filename)
        return f"/output/{batch_file.filename}"

    with patch.object(
        processing_service, "_process_single_file", side_effect=mock_process
    ):
        run_async(processing_service.process_batch(job_id))

    # Only the third file (still queued) should have been processed
    assert len(processed) == 1
    assert processed[0] == "video_2.mp4"


def test_process_batch_clears_cancel_flag(
    processing_service, batch_service, batch_with_file
):
    """process_batch clears cancel flag on start and finish"""
    job_id, file_id = batch_with_file

    # Set cancel flag before starting
    processing_service.request_cancel()

    with patch.object(
        processing_service, "_process_single_file", new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = "/output/path"
        run_async(processing_service.process_batch(job_id))

    # Cancel flag should be cleared after processing
    assert processing_service.is_cancel_requested() is False


# ------------
# Route Integration Tests (mutual exclusion)
# ------------


def test_start_batch_mutual_exclusion_single_file(tmp_path, monkeypatch):
    """Start batch returns 409 when single-file processing is active"""
    from fastapi.testclient import TestClient
    from main import app
    from api.routes import batch as batch_module
    from services.batch_service import BatchService

    test_db = str(tmp_path / "test.db")
    test_service = BatchService(db_path=test_db)
    monkeypatch.setattr(batch_module, "batch_service", test_service)

    # Mock AppState to show single-file processing active
    mock_state = MagicMock()
    mock_state.subtitle_job = MagicMock()
    mock_state.subtitle_job.status = "running"
    mock_state.dubbing_job = None
    monkeypatch.setattr(batch_module, "get_app_state", lambda: mock_state)

    client = TestClient(app)

    # Create a batch with a file
    resp = client.post("/api/batch/")
    job_id = resp.json()["jobId"]

    resp = client.post(f"/api/batch/{job_id}/start")
    assert resp.status_code == 409


def test_start_batch_mutual_exclusion_other_batch(tmp_path, monkeypatch):
    """Start batch returns 409 when another batch is already processing"""
    from fastapi.testclient import TestClient
    from main import app
    from api.routes import batch as batch_module
    from services.batch_service import BatchService

    test_db = str(tmp_path / "test.db")
    test_service = BatchService(db_path=test_db)
    monkeypatch.setattr(batch_module, "batch_service", test_service)

    # Mock AppState to show no single-file processing
    mock_state = MagicMock()
    mock_state.subtitle_job = None
    mock_state.dubbing_job = None
    monkeypatch.setattr(batch_module, "get_app_state", lambda: mock_state)

    client = TestClient(app)

    # Create first batch and set it to processing
    resp = client.post("/api/batch/")
    job_id1 = resp.json()["jobId"]
    test_service.update_job_status(job_id1, "processing")

    # Create second batch with a file
    resp = client.post("/api/batch/")
    job_id2 = resp.json()["jobId"]

    resp = client.post(f"/api/batch/{job_id2}/start")
    assert resp.status_code == 409

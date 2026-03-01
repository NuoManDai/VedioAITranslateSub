"""
Shared fixtures for backend tests.

All fixtures use tmp_path or mock to avoid touching real filesystem / database.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend/ is on sys.path so ``from services.xxx import ...`` works
# when running ``cd backend && pytest tests/ -v``.
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))


# ----------
# Event loop fixture (replaces pytest-asyncio)
# ----------


@pytest.fixture
def event_loop():
    """Create a new event loop for each test that needs one."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ----------
# Fake Video / Job helpers
# ----------


def make_fake_video(video_id: str = "aaaa-bbbb-cccc-dddd", filename: str = "test.mp4"):
    """Return a lightweight Video-like object (MagicMock with required attrs)."""
    video = MagicMock()
    video.id = video_id
    video.filename = filename
    video.status = "completed"
    video.error_message = None
    return video


def make_fake_job(video_id: str = "aaaa-bbbb-cccc-dddd", job_type: str = "dubbing"):
    """Return a lightweight ProcessingJob-like object."""
    job = MagicMock()
    job.id = "job-1234"
    job.video_id = video_id
    job.job_type = job_type
    job.status = "pending"
    job.start = MagicMock()
    job.complete = MagicMock()
    job.fail = MagicMock()
    job.update_stage = MagicMock()
    job.current_stage = None
    return job


# ----------
# Patched OUTPUT_DIR fixture (points to tmp_path)
# ----------


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Patch ``api.deps.OUTPUT_DIR`` and helper functions to use tmp_path."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    patches = [
        patch("api.deps.OUTPUT_DIR", output_dir),
        patch("services.core_path_manager.OUTPUT_DIR", output_dir),
    ]
    for p in patches:
        p.start()

    yield output_dir

    for p in patches:
        p.stop()

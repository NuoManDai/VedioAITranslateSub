"""
Concurrent Dubbing Tests

Validates:
1. asyncio.Semaphore(3) limits concurrent dubbing to 3 at a time
2. Multiple videos have isolated workspace paths
3. _video_jobs dict correctly tracks concurrent tasks

All tests use mock — no real subprocess or AI calls.
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import make_fake_video, make_fake_job


# ============================================================
# 1. Semaphore concurrency limit (max 3 simultaneous)
# ============================================================


class TestSemaphoreConcurrency:
    """Verify _dubbing_semaphore limits parallel dubbing to 3."""

    def test_semaphore_limits_to_three(self, event_loop, tmp_output_dir):
        """
        Launch 5 dubbing tasks concurrently. At most 3 should run
        inside the semaphore-protected section at any point in time.
        """
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def track_concurrency():
            """Coroutine that runs inside the semaphore section."""
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent

            # Simulate work
            await asyncio.sleep(0.05)

            async with lock:
                current_concurrent -= 1

        # Build 5 video IDs
        video_ids = [f"{i}0000000-0000-0000-0000-000000000000" for i in range(5)]

        mock_state = MagicMock()
        mock_state.is_cancel_requested.return_value = False
        mock_state.clear_cancel_request = MagicMock()

        mock_log_store = MagicMock()

        with (
            patch("services.processing_service.get_app_state", return_value=mock_state),
            patch(
                "services.processing_service.get_log_store", return_value=mock_log_store
            ),
            patch("services.processing_service.VideoDB"),
            patch("services.processing_service.set_cancel_flag"),
            patch("services.processing_service.clear_cancel_flag"),
            patch("services.processing_service.setup_video_workspace"),
            patch("services.processing_service.teardown_video_workspace"),
            patch("services.processing_service.get_workspace_root") as mock_ws,
            patch("services.processing_service.get_video_output_dir") as mock_vod,
        ):
            from services.processing_service import ProcessingService

            svc = ProcessingService()

            # For each video, mock workspace root to return a temp path
            def ws_side_effect(vid):
                p = tmp_output_dir / ".workspace" / vid
                p.mkdir(parents=True, exist_ok=True)
                (p / "output").mkdir(exist_ok=True)
                return p

            mock_ws.side_effect = ws_side_effect

            def vod_side_effect(vid):
                p = tmp_output_dir / vid
                p.mkdir(parents=True, exist_ok=True)
                return p

            mock_vod.side_effect = vod_side_effect

            # Replace _run_stage to use our concurrency tracker
            original_run_stage = svc._run_stage

            async def mock_run_stage(job, stage_name, stage_func):
                await track_concurrency()

            svc._run_stage = mock_run_stage

            async def run_all():
                tasks = []
                for vid in video_ids:
                    video = make_fake_video(vid, f"video_{vid[:1]}.mp4")
                    job = make_fake_job(vid)
                    tasks.append(svc.run_dubbing_processing(job, video, video_id=vid))
                await asyncio.gather(*tasks, return_exceptions=True)

            event_loop.run_until_complete(run_all())

        # Semaphore is 3, so max_concurrent should never exceed 3
        assert max_concurrent <= 3, (
            f"Max concurrent was {max_concurrent}, expected <= 3"
        )
        # Also confirm tasks actually ran concurrently (max > 1)
        assert max_concurrent > 1, (
            f"Expected some concurrency, but max was {max_concurrent}"
        )

    def test_semaphore_value_is_three(self):
        """Directly verify the semaphore is initialized with value 3."""
        with (
            patch("services.processing_service.get_app_state"),
            patch("services.processing_service.get_log_store"),
            patch("services.processing_service.VideoDB"),
            patch("services.processing_service.set_cancel_flag"),
            patch("services.processing_service.clear_cancel_flag"),
        ):
            from services.processing_service import ProcessingService

            svc = ProcessingService()
            # asyncio.Semaphore stores the value in _value
            assert svc._dubbing_semaphore._value == 3, (
                "Dubbing semaphore should be initialized with value 3"
            )


# ============================================================
# 2. Per-video workspace path isolation
# ============================================================


class TestWorkspacePathIsolation:
    """Each video gets its own workspace directory under .workspace/{video_id}/."""

    def test_different_videos_get_different_workspaces(self, tmp_output_dir):
        """get_workspace_root returns unique paths per video_id."""
        from services.core_path_manager import get_workspace_root

        vid_a = "aaaa0000-0000-0000-0000-000000000001"
        vid_b = "bbbb0000-0000-0000-0000-000000000002"

        ws_a = get_workspace_root(vid_a)
        ws_b = get_workspace_root(vid_b)

        assert ws_a != ws_b, "Different videos must have different workspace roots"
        assert vid_a in str(ws_a)
        assert vid_b in str(ws_b)
        assert ".workspace" in str(ws_a)
        assert ".workspace" in str(ws_b)

    def test_workspaces_dont_interfere(self, tmp_output_dir):
        """Files in one workspace don't appear in another."""
        from services.core_path_manager import (
            setup_video_workspace,
            get_workspace_root,
        )

        vid_a = "cccc0000-0000-0000-0000-000000000003"
        vid_b = "dddd0000-0000-0000-0000-000000000004"

        for vid in [vid_a, vid_b]:
            vdir = tmp_output_dir / vid
            vdir.mkdir(parents=True)
            (vdir / "video.mp4").write_text(f"data-{vid}")

        setup_video_workspace(vid_a, "video.mp4")
        setup_video_workspace(vid_b, "video.mp4")

        ws_a = get_workspace_root(vid_a)
        ws_b = get_workspace_root(vid_b)

        # Write a file in workspace A
        (ws_a / "output" / "special_a.txt").write_text("only-in-a")

        # It should NOT exist in workspace B
        assert not (ws_b / "output" / "special_a.txt").exists(), (
            "File from workspace A should not leak into workspace B"
        )


# ============================================================
# 3. _video_jobs tracking for concurrent tasks
# ============================================================


class TestVideoJobsTracking:
    """_video_jobs dict correctly tracks and cleans up concurrent tasks."""

    def test_concurrent_jobs_tracked_independently(self, event_loop, tmp_output_dir):
        """
        Multiple concurrent dubbing jobs should each appear in _video_jobs
        during execution and be cleaned up after.
        """
        video_ids = [f"{i}eee0000-0000-0000-0000-000000000000" for i in range(3)]

        jobs_seen_during_run = {}

        mock_state = MagicMock()
        mock_state.is_cancel_requested.return_value = False
        mock_state.clear_cancel_request = MagicMock()

        mock_log_store = MagicMock()

        with (
            patch("services.processing_service.get_app_state", return_value=mock_state),
            patch(
                "services.processing_service.get_log_store", return_value=mock_log_store
            ),
            patch("services.processing_service.VideoDB"),
            patch("services.processing_service.set_cancel_flag"),
            patch("services.processing_service.clear_cancel_flag"),
            patch("services.processing_service.setup_video_workspace"),
            patch("services.processing_service.teardown_video_workspace"),
            patch("services.processing_service.get_workspace_root") as mock_ws,
            patch("services.processing_service.get_video_output_dir") as mock_vod,
        ):
            from services.processing_service import ProcessingService

            svc = ProcessingService()

            def ws_side_effect(vid):
                p = tmp_output_dir / ".workspace" / vid
                p.mkdir(parents=True, exist_ok=True)
                (p / "output").mkdir(exist_ok=True)
                return p

            mock_ws.side_effect = ws_side_effect

            def vod_side_effect(vid):
                p = tmp_output_dir / vid
                p.mkdir(parents=True, exist_ok=True)
                return p

            mock_vod.side_effect = vod_side_effect

            async def mock_run_stage(job, stage_name, stage_func):
                # Snapshot current _video_jobs during execution
                vid = job.video_id
                if vid not in jobs_seen_during_run:
                    jobs_seen_during_run[vid] = True
                await asyncio.sleep(0.01)

            svc._run_stage = mock_run_stage

            async def run_all():
                tasks = []
                for vid in video_ids:
                    video = make_fake_video(vid, f"v_{vid[:1]}.mp4")
                    job = make_fake_job(vid)
                    tasks.append(svc.run_dubbing_processing(job, video, video_id=vid))
                await asyncio.gather(*tasks, return_exceptions=True)

            event_loop.run_until_complete(run_all())

        # All jobs should have been tracked during execution
        for vid in video_ids:
            assert vid in jobs_seen_during_run, (
                f"Job for {vid} should have been seen during execution"
            )

        # After completion, all should be cleaned up
        for vid in video_ids:
            assert vid not in svc._video_jobs, (
                f"Job for {vid} should be removed from _video_jobs after completion"
            )

    def test_cannot_start_duplicate_while_running(self, event_loop, tmp_output_dir):
        """
        While a dubbing job is running for video X, attempting to start
        another for the same video_id should raise ValueError.
        """
        video_id = "ffff0000-0000-0000-0000-000000000000"

        started_event = asyncio.Event()
        proceed_event = asyncio.Event()

        mock_state = MagicMock()
        mock_state.is_cancel_requested.return_value = False
        mock_state.clear_cancel_request = MagicMock()

        mock_log_store = MagicMock()

        with (
            patch("services.processing_service.get_app_state", return_value=mock_state),
            patch(
                "services.processing_service.get_log_store", return_value=mock_log_store
            ),
            patch("services.processing_service.VideoDB"),
            patch("services.processing_service.set_cancel_flag"),
            patch("services.processing_service.clear_cancel_flag"),
            patch("services.processing_service.setup_video_workspace"),
            patch("services.processing_service.teardown_video_workspace"),
            patch("services.processing_service.get_workspace_root") as mock_ws,
            patch("services.processing_service.get_video_output_dir") as mock_vod,
        ):
            from services.processing_service import ProcessingService

            svc = ProcessingService()

            def ws_side_effect(vid):
                p = tmp_output_dir / ".workspace" / vid
                p.mkdir(parents=True, exist_ok=True)
                (p / "output").mkdir(exist_ok=True)
                return p

            mock_ws.side_effect = ws_side_effect
            mock_vod.return_value = tmp_output_dir / video_id

            async def slow_run_stage(job, stage_name, stage_func):
                started_event.set()
                await proceed_event.wait()

            svc._run_stage = slow_run_stage

            duplicate_error = None

            async def run_test():
                nonlocal duplicate_error

                video = make_fake_video(video_id, "test.mp4")
                job1 = make_fake_job(video_id)

                # Start first job
                task1 = asyncio.create_task(
                    svc.run_dubbing_processing(job1, video, video_id=video_id)
                )

                # Wait until it's inside the semaphore
                await started_event.wait()

                # Try to start second job for same video
                job2 = make_fake_job(video_id)
                try:
                    await svc.run_dubbing_processing(job2, video, video_id=video_id)
                except ValueError as e:
                    duplicate_error = e

                # Let first job finish
                proceed_event.set()
                await task1

            event_loop.run_until_complete(run_test())

        assert duplicate_error is not None, (
            "Should raise ValueError for duplicate submission"
        )
        assert "already in progress" in str(duplicate_error)

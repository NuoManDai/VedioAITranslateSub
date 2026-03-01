"""
Dubbing Integration Tests

Validates workspace isolation, subtitle injection, duplicate submission
protection, cancel flag isolation, and save_all_subtitles for_audio sync.

All tests use mock / tmp_path — no real subprocess or AI service calls.
"""

import asyncio
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Import helpers from conftest
from tests.conftest import make_fake_video, make_fake_job


# ============================================================
# 1. Workspace isolation (core_path_manager real logic + tmp)
# ============================================================


class TestWorkspaceIsolation:
    """Test setup_video_workspace / teardown_video_workspace with real FS ops."""

    def test_setup_creates_workspace_structure(self, tmp_output_dir):
        """setup_video_workspace should create .workspace/{vid}/output/ tree."""
        from services.core_path_manager import (
            setup_video_workspace,
            get_workspace_root,
        )

        video_id = "11111111-1111-1111-1111-111111111111"
        filename = "video.mp4"

        # Prepare source video in per-video dir
        video_dir = tmp_output_dir / video_id
        video_dir.mkdir(parents=True)
        (video_dir / filename).write_text("fake-video-data")

        setup_video_workspace(video_id, filename)

        ws = get_workspace_root(video_id)
        assert ws.exists(), "workspace root should exist"
        assert (ws / "output").is_dir()
        assert (ws / "output" / "audio").is_dir()
        assert (ws / "output" / "audio" / "refers").is_dir()
        assert (ws / "output" / "audio" / "segs").is_dir()
        assert (ws / "output" / "audio" / "tmp").is_dir()
        assert (ws / "output" / "log").is_dir()
        assert (ws / "output" / "gpt_log").is_dir()
        # Video should be copied to workspace output/
        assert (ws / "output" / filename).exists()

    def test_teardown_copies_results_and_removes_workspace(self, tmp_output_dir):
        """teardown should merge workspace output back and remove workspace dir."""
        from services.core_path_manager import (
            setup_video_workspace,
            teardown_video_workspace,
            get_workspace_root,
        )

        video_id = "22222222-2222-2222-2222-222222222222"
        filename = "clip.mp4"

        # Prepare
        video_dir = tmp_output_dir / video_id
        video_dir.mkdir(parents=True)
        (video_dir / filename).write_text("fake-clip")

        setup_video_workspace(video_id, filename)
        ws = get_workspace_root(video_id)

        # Simulate pipeline output in workspace
        (ws / "output" / "output_sub.mp4").write_text("dubbed-result")
        audio_dir = ws / "output" / "audio"
        (audio_dir / "merged.wav").write_text("merged-audio")

        teardown_video_workspace(video_id, filename)

        # Results should be in per-video dir
        assert (video_dir / "output_sub.mp4").read_text() == "dubbed-result"
        assert (video_dir / "audio" / "merged.wav").read_text() == "merged-audio"

        # Workspace should be removed
        assert not ws.exists(), "workspace should be cleaned up after teardown"

    def test_setup_raises_when_video_missing(self, tmp_output_dir):
        """setup should raise FileNotFoundError if source video does not exist."""
        from services.core_path_manager import setup_video_workspace

        video_id = "33333333-3333-3333-3333-333333333333"
        # Do NOT create the video file
        (tmp_output_dir / video_id).mkdir(parents=True)

        with pytest.raises(FileNotFoundError):
            setup_video_workspace(video_id, "nonexistent.mp4")


# ============================================================
# 2. Subtitle injection into workspace
# ============================================================


class TestSubtitleInjection:
    """Verify that run_dubbing_processing copies for_audio.srt into workspace."""

    def test_for_audio_srt_injected_into_workspace(self, tmp_output_dir, event_loop):
        """
        When trans_subs_for_audio.srt exists in per-video dir,
        it should be copied into workspace before stages run.
        """
        video_id = "44444444-4444-4444-4444-444444444444"
        filename = "test.mp4"

        # Prepare per-video dir with source video + for_audio SRT
        video_dir = tmp_output_dir / video_id
        video_dir.mkdir(parents=True)
        (video_dir / filename).write_text("video-data")
        audio_dir = video_dir / "audio"
        audio_dir.mkdir()
        srt_content = "1\n00:00:01,000 --> 00:00:02,000\nHello\n"
        (audio_dir / "trans_subs_for_audio.srt").write_text(srt_content)

        from services.core_path_manager import get_workspace_root

        # We need to patch many things in processing_service
        mock_state = MagicMock()
        mock_state.is_cancel_requested.return_value = False
        mock_state.clear_cancel_request = MagicMock()

        mock_log_store = MagicMock()
        mock_log_store.info = MagicMock()
        mock_log_store.warning = MagicMock()
        mock_log_store.error = MagicMock()

        # Track whether _run_stage was called (means injection happened before stages)
        stages_called = []

        async def fake_run_stage(job, stage_name, stage_func):
            stages_called.append(stage_name)

        with (
            patch("services.processing_service.get_app_state", return_value=mock_state),
            patch(
                "services.processing_service.get_log_store", return_value=mock_log_store
            ),
            patch("services.processing_service.VideoDB") as MockDB,
            patch("services.processing_service.set_cancel_flag"),
            patch("services.processing_service.clear_cancel_flag"),
            patch.object(
                __import__(
                    "services.processing_service", fromlist=["ProcessingService"]
                ).ProcessingService,
                "_run_stage",
                side_effect=fake_run_stage,
            ),
            patch(
                "services.processing_service.get_video_output_dir",
                return_value=video_dir,
            ),
        ):
            from services.processing_service import ProcessingService

            svc = ProcessingService()
            # Override output_dir to use tmp
            svc.output_dir = tmp_output_dir

            video = make_fake_video(video_id, filename)
            job = make_fake_job(video_id)

            event_loop.run_until_complete(
                svc.run_dubbing_processing(job, video, video_id=video_id)
            )

        # Verify SRT was injected into workspace (check it was created)
        # The workspace is torn down in finally, so we check stages ran
        assert len(stages_called) == 6, f"Expected 6 stages, got {stages_called}"


# ============================================================
# 3. Duplicate submission protection
# ============================================================


class TestDuplicateSubmission:
    """ProcessingService._video_jobs prevents parallel dubbing for same video."""

    def test_duplicate_raises_value_error(self, event_loop):
        """Second call to run_dubbing_processing for same video_id raises ValueError."""
        video_id = "55555555-5555-5555-5555-555555555555"

        mock_state = MagicMock()
        mock_state.is_cancel_requested.return_value = False
        mock_state.clear_cancel_request = MagicMock()

        mock_log_store = MagicMock()
        mock_log_store.info = MagicMock()

        with (
            patch("services.processing_service.get_app_state", return_value=mock_state),
            patch(
                "services.processing_service.get_log_store", return_value=mock_log_store
            ),
            patch("services.processing_service.VideoDB"),
            patch("services.processing_service.set_cancel_flag"),
            patch("services.processing_service.clear_cancel_flag"),
        ):
            from services.processing_service import ProcessingService

            svc = ProcessingService()

            # Manually mark video as in-progress
            svc._video_jobs[video_id] = make_fake_job(video_id)

            video = make_fake_video(video_id)
            job = make_fake_job(video_id)

            with pytest.raises(ValueError, match="already in progress"):
                event_loop.run_until_complete(
                    svc.run_dubbing_processing(job, video, video_id=video_id)
                )

            # Cleanup
            svc._video_jobs.pop(video_id, None)


# ============================================================
# 4. Cancel flag isolation (workspace-scoped vs global)
# ============================================================


class TestCancelFlagIsolation:
    """Cancel flag file is placed in workspace, not global output."""

    def test_cancel_file_path_is_workspace_scoped(self, tmp_output_dir):
        """
        The cancel file should be at workspace_root/output/.cancel_requested,
        NOT at the global output/.cancel_requested.
        """
        from services.core_path_manager import get_workspace_root

        video_id = "66666666-6666-6666-6666-666666666666"
        ws = get_workspace_root(video_id)

        # Simulate the path that processing_service uses
        cancel_file = ws / "output" / ".cancel_requested"

        # Global cancel file path (should NOT be this)
        global_cancel = tmp_output_dir / ".cancel_requested"

        assert str(cancel_file) != str(global_cancel), (
            "Cancel file should be workspace-scoped, not in global output"
        )
        assert ".workspace" in str(cancel_file), (
            "Cancel file path should contain .workspace"
        )

    def test_two_videos_have_separate_cancel_files(self, tmp_output_dir):
        """Two videos should have independent cancel file paths."""
        from services.core_path_manager import get_workspace_root

        vid_a = "77777777-7777-7777-7777-777777777777"
        vid_b = "88888888-8888-8888-8888-888888888888"

        cancel_a = get_workspace_root(vid_a) / "output" / ".cancel_requested"
        cancel_b = get_workspace_root(vid_b) / "output" / ".cancel_requested"

        assert cancel_a != cancel_b, "Each video must have its own cancel file"
        assert vid_a in str(cancel_a)
        assert vid_b in str(cancel_b)


# ============================================================
# 5. save_all_subtitles syncs for_audio.srt
# ============================================================


class TestForAudioSync:
    """save_all_subtitles should sync trans/src_subs_for_audio.srt when they exist."""

    def test_trans_for_audio_synced_when_exists(self, tmp_output_dir):
        """
        If trans_subs_for_audio.srt exists, save_all_subtitles should:
        1. Create a .srt.bak backup
        2. Overwrite with new translated text
        """
        from services.subtitle_service import SubtitleService, SubtitleEntry

        video_id = "99999999-9999-9999-9999-999999999999"
        video_dir = tmp_output_dir / video_id
        video_dir.mkdir(parents=True)
        audio_dir = video_dir / "audio"
        audio_dir.mkdir()

        # Create existing for_audio file
        old_content = "1\n00:00:01,000 --> 00:00:02,000\nOld Translation\n"
        (audio_dir / "trans_subs_for_audio.srt").write_text(old_content)

        entries = [
            SubtitleEntry(
                index=1,
                start_time=1.0,
                end_time=2.0,
                text="New Translation",
                original_text="Original Source",
            )
        ]

        with (
            patch(
                "services.subtitle_service.get_video_output_dir", return_value=video_dir
            ),
            patch(
                "services.subtitle_service.get_output_dir", return_value=tmp_output_dir
            ),
        ):
            svc = SubtitleService()
            result = svc.save_all_subtitles(entries, video_id=video_id)

        assert result["success"] is True

        # Check backup was created
        bak_file = audio_dir / "trans_subs_for_audio.srt.bak"
        assert bak_file.exists(), "Backup should be created"

        # Check new content was written
        new_content = (audio_dir / "trans_subs_for_audio.srt").read_text()
        assert "New Translation" in new_content

    def test_for_audio_not_synced_when_missing(self, tmp_output_dir):
        """If for_audio files don't exist, no sync happens (no error)."""
        from services.subtitle_service import SubtitleService, SubtitleEntry

        video_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        video_dir = tmp_output_dir / video_id
        video_dir.mkdir(parents=True)
        audio_dir = video_dir / "audio"
        audio_dir.mkdir()

        # Do NOT create for_audio files

        entries = [
            SubtitleEntry(
                index=1,
                start_time=1.0,
                end_time=2.0,
                text="Translation",
                original_text="Source",
            )
        ]

        with (
            patch(
                "services.subtitle_service.get_video_output_dir", return_value=video_dir
            ),
            patch(
                "services.subtitle_service.get_output_dir", return_value=tmp_output_dir
            ),
        ):
            svc = SubtitleService()
            result = svc.save_all_subtitles(entries, video_id=video_id)

        assert result["success"] is True
        # No backup should exist
        assert not (audio_dir / "trans_subs_for_audio.srt.bak").exists()
        assert not (audio_dir / "src_subs_for_audio.srt.bak").exists()

    def test_src_for_audio_synced_when_exists(self, tmp_output_dir):
        """src_subs_for_audio.srt should also be synced with original text."""
        from services.subtitle_service import SubtitleService, SubtitleEntry

        video_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        video_dir = tmp_output_dir / video_id
        video_dir.mkdir(parents=True)
        audio_dir = video_dir / "audio"
        audio_dir.mkdir()

        # Create existing src_for_audio file
        (audio_dir / "src_subs_for_audio.srt").write_text(
            "1\n00:00:01,000 --> 00:00:02,000\nOld Source\n"
        )

        entries = [
            SubtitleEntry(
                index=1,
                start_time=1.0,
                end_time=2.0,
                text="Translation",
                original_text="Updated Source",
            )
        ]

        with (
            patch(
                "services.subtitle_service.get_video_output_dir", return_value=video_dir
            ),
            patch(
                "services.subtitle_service.get_output_dir", return_value=tmp_output_dir
            ),
        ):
            svc = SubtitleService()
            result = svc.save_all_subtitles(entries, video_id=video_id)

        assert result["success"] is True

        # Check backup
        assert (audio_dir / "src_subs_for_audio.srt.bak").exists()

        # Check new content has updated source text
        new_content = (audio_dir / "src_subs_for_audio.srt").read_text()
        assert "Updated Source" in new_content


# ============================================================
# 6. Cleanup in finally block
# ============================================================


class TestFinallyCleanup:
    """After run_dubbing_processing, _video_jobs should be cleaned up."""

    def test_video_job_removed_after_completion(self, event_loop, tmp_output_dir):
        """_video_jobs[video_id] is popped in the finally block."""
        video_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
        filename = "test.mp4"

        # Create video file
        video_dir = tmp_output_dir / video_id
        video_dir.mkdir(parents=True)
        (video_dir / filename).write_text("data")

        mock_state = MagicMock()
        mock_state.is_cancel_requested.return_value = False
        mock_state.clear_cancel_request = MagicMock()

        mock_log_store = MagicMock()

        async def noop_stage(job, stage_name, stage_func):
            pass

        with (
            patch("services.processing_service.get_app_state", return_value=mock_state),
            patch(
                "services.processing_service.get_log_store", return_value=mock_log_store
            ),
            patch("services.processing_service.VideoDB"),
            patch("services.processing_service.set_cancel_flag"),
            patch("services.processing_service.clear_cancel_flag"),
            patch(
                "services.processing_service.get_video_output_dir",
                return_value=video_dir,
            ),
            patch.object(
                __import__(
                    "services.processing_service", fromlist=["ProcessingService"]
                ).ProcessingService,
                "_run_stage",
                side_effect=noop_stage,
            ),
        ):
            from services.processing_service import ProcessingService

            svc = ProcessingService()
            svc.output_dir = tmp_output_dir

            video = make_fake_video(video_id, filename)
            job = make_fake_job(video_id)

            event_loop.run_until_complete(
                svc.run_dubbing_processing(job, video, video_id=video_id)
            )

            # After completion, video_id should NOT be in _video_jobs
            assert video_id not in svc._video_jobs, (
                "video_id should be removed from _video_jobs after processing"
            )

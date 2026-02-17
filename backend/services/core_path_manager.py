"""
Core Path Manager - Workspace manager for per-video output directory isolation

This module implements the workspace copy pattern:
1. setup_video_workspace: Clean flat output/ and copy video file there
2. Core pipeline runs and writes to flat output/
3. teardown_video_workspace: Move results back to output/{video_id}/

This approach avoids modifying core modules and ensures process isolation.
"""

import logging
import shutil
from pathlib import Path
from uuid import UUID

from api.deps import PROJECT_ROOT, OUTPUT_DIR

logger = logging.getLogger(__name__)


def _is_uuid_dir(name: str) -> bool:
    """
    Check if a directory name matches UUID format (video_id directory).

    Args:
        name: Directory name to check

    Returns:
        True if name is a valid UUID hex format
    """
    try:
        UUID(name)
        return True
    except (ValueError, AttributeError):
        return False


def _ensure_video_dirs(video_id: str) -> None:
    """
    Create output directory structure for a specific video.

    Creates:
    - output/{video_id}/
    - output/{video_id}/log/
    - output/{video_id}/gpt_log/
    - output/{video_id}/audio/
    - output/{video_id}/audio/refers/
    - output/{video_id}/audio/segs/
    - output/{video_id}/audio/tmp/

    Args:
        video_id: The video UUID
    """
    video_dir = OUTPUT_DIR / video_id

    # Create all required subdirectories
    subdirs = [
        video_dir,
        video_dir / "log",
        video_dir / "gpt_log",
        video_dir / "audio",
        video_dir / "audio" / "refers",
        video_dir / "audio" / "segs",
        video_dir / "audio" / "tmp",
    ]

    for subdir in subdirs:
        subdir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory: {subdir}")


def _clean_flat_output() -> None:
    """
    Clean the flat output/ directory for pipeline processing.

    Removes all files and non-UUID subdirectories from output/ while
    preserving per-video directories (those with UUID names).

    Pipeline writes to: output/log/, output/audio/, output/gpt_log/, etc.
    Per-video dirs: output/{uuid}/ are preserved.
    """
    if not OUTPUT_DIR.exists():
        logger.debug("Output directory does not exist, nothing to clean")
        return

    for item in OUTPUT_DIR.iterdir():
        # Skip UUID-named directories (per-video directories)
        if item.is_dir() and _is_uuid_dir(item.name):
            logger.debug(f"Skipping per-video directory: {item.name}")
            continue

        # Remove files and non-UUID directories (pipeline output)
        try:
            if item.is_dir():
                shutil.rmtree(str(item))
                logger.debug(f"Removed directory: {item.name}")
            else:
                item.unlink()
                logger.debug(f"Removed file: {item.name}")
        except Exception as e:
            logger.error(f"Failed to clean {item.name}: {e}")
            raise


def _copy_video_to_flat_output(video_id: str, video_filename: str) -> str:
    """
    Copy video file from per-video directory to flat output/ directory.

    The core pipeline expects the video file to be at output/{filename}.
    This copies from output/{video_id}/{filename} to output/{filename}.

    Args:
        video_id: The video UUID
        video_filename: Name of the video file (e.g., 'video.mp4')

    Returns:
        The filename in the flat output directory

    Raises:
        FileNotFoundError: If source video file does not exist
    """
    src = OUTPUT_DIR / video_id / video_filename
    dst = OUTPUT_DIR / video_filename

    if not src.exists():
        raise FileNotFoundError(f"Video file not found: {src}")

    try:
        shutil.copy2(str(src), str(dst))
        logger.info(f"Copied video to flat output: {video_filename}")
        return video_filename
    except Exception as e:
        logger.error(f"Failed to copy video {src} to {dst}: {e}")
        raise


def _save_pipeline_output(video_id: str, video_filename: str) -> None:
    """
    Move pipeline output from flat output/ back to per-video directory.

    After pipeline runs and produces files in output/log/, output/audio/,
    etc., this moves all those files to output/{video_id}/.

    Args:
        video_id: The video UUID
        video_filename: Original source video filename to skip during move

    Raises:
        Exception: If move operation fails
    """
    video_dir = OUTPUT_DIR / video_id

    # Ensure target directory exists
    video_dir.mkdir(parents=True, exist_ok=True)

    if not OUTPUT_DIR.exists():
        logger.warning(f"Flat output directory does not exist: {OUTPUT_DIR}")
        return

    # Move all files and non-UUID directories from flat output to video dir
    for item in OUTPUT_DIR.iterdir():
        # Skip the per-video directories
        if item.is_dir() and _is_uuid_dir(item.name):
            logger.debug(f"Skipping per-video directory during move: {item.name}")
            continue

        # Skip ONLY the original source video (not pipeline outputs like output_sub.mp4)
        if item.is_file() and item.name == video_filename:
            logger.debug(f"Skipping source video during move: {item.name}")
            continue

        # Move files and directories
        dst = video_dir / item.name
        try:
            if item.is_dir():
                # If target exists, remove it first
                if dst.exists():
                    shutil.rmtree(str(dst))
                shutil.move(str(item), str(dst))
                logger.debug(f"Moved directory: {item.name} -> {video_id}/{item.name}")
            else:
                shutil.move(str(item), str(dst))
                logger.debug(f"Moved file: {item.name} -> {video_id}/{item.name}")
        except Exception as e:
            logger.error(f"Failed to move {item.name} to {video_dir}: {e}")
            raise


def setup_video_workspace(video_id: str, video_filename: str) -> None:
    """
    Setup workspace for video processing.

    This performs the initial setup for processing a video:
    1. Ensure per-video directory structure exists
    2. Clean the flat output/ directory
    3. Copy the video file to flat output/

    After this, the core pipeline can run with video at output/{video_filename}
    and will write output to output/log/, output/audio/, etc.

    Args:
        video_id: The video UUID (e.g., 'a1b2c3d4-e5f6-...')
        video_filename: Name of the video file (e.g., 'video.mp4')

    Raises:
        FileNotFoundError: If video file not found in per-video directory
        Exception: If any file operation fails
    """
    logger.info(f"Setting up workspace for video {video_id}: {video_filename}")

    try:
        # Step 1: Ensure per-video directory structure
        _ensure_video_dirs(video_id)
        logger.debug(f"Created per-video directories for {video_id}")

        # Step 2: Clean the flat output directory
        _clean_flat_output()
        logger.debug("Cleaned flat output directory")

        # Step 3: Copy video to flat output
        _copy_video_to_flat_output(video_id, video_filename)
        logger.info(f"Workspace ready for video {video_id}")

    except Exception as e:
        logger.error(f"Failed to setup workspace for {video_id}: {e}")
        raise


def teardown_video_workspace(video_id: str, video_filename: str) -> None:
    """
    Teardown workspace after video processing.

    This performs final cleanup after pipeline completes:
    1. Ensure per-video directory exists
    2. Move all pipeline output from flat output/ to output/{video_id}/
    3. Clean up remaining files in flat output/

    Args:
        video_id: The video UUID
        video_filename: Original source video filename to skip during move

    Raises:
        Exception: If any file operation fails
    """
    logger.info(f"Tearing down workspace for video {video_id}")

    try:
        # Step 1: Ensure per-video directory exists
        _ensure_video_dirs(video_id)
        logger.debug(f"Ensured per-video directories for {video_id}")

        # Step 2: Move pipeline output to per-video directory
        _save_pipeline_output(video_id, video_filename)
        logger.debug(f"Moved pipeline output to {video_id}")

        # Step 3: Clean remaining non-UUID items from flat output
        _clean_flat_output()
        logger.debug("Final cleanup of flat output directory")

        logger.info(f"Workspace teardown completed for {video_id}")

    except Exception as e:
        logger.error(f"Failed to teardown workspace for {video_id}: {e}")
        raise

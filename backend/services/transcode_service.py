"""
Transcode Service - FFmpeg-based video transcoding utilities.

Provides probe/detection functions and the core transcode_to_mp4() function.
TranscodeManager (async concurrency management) is in the same module below.
"""

import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ----------------------------
# Custom Exception
# ----------------------------


class TranscodeError(Exception):
    """Raised when ffprobe/ffmpeg operations fail."""


# ----------------------------
# Codec & Duration Probe
# ----------------------------


def probe_video_codec(filepath: str) -> dict:
    """
    Probe video file for codec name and duration using ffprobe.

    Args:
        filepath: Absolute or relative path to the video file.

    Returns:
        Dict with keys:
            video_codec (str): e.g. "h264", "hevc", "vp9", or "unknown"
            duration (float): Duration in seconds (0.0 if undetectable)

    Raises:
        TranscodeError: If ffprobe fails or the file does not exist.
    """
    if not os.path.exists(filepath):
        raise TranscodeError(f"File not found: {filepath}")

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        filepath,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as e:
        raise TranscodeError(f"ffprobe timed out for {filepath}") from e
    except FileNotFoundError as e:
        raise TranscodeError("ffprobe not found — is ffmpeg installed?") from e

    if result.returncode != 0:
        raise TranscodeError(
            f"ffprobe failed (exit {result.returncode}): {result.stderr.strip()}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise TranscodeError(f"ffprobe returned invalid JSON: {e}") from e

    streams = data.get("streams", [])
    video_codec = streams[0].get("codec_name", "unknown") if streams else "unknown"

    fmt = data.get("format", {})
    try:
        duration = float(fmt.get("duration", 0.0))
    except (TypeError, ValueError):
        duration = 0.0

    return {"video_codec": video_codec, "duration": duration}


# ----------------------------
# Transcode Decision
# ----------------------------


def needs_transcode(filepath: str) -> bool:
    """
    Determine whether a video file needs to be transcoded to MP4/H.264.

    Short-circuits on extension: if file is not .mp4, returns True immediately
    without running ffprobe. Only probes codec when the file is already .mp4.

    Args:
        filepath: Path to the video file.

    Returns:
        True if the file should be transcoded, False if it can be used as-is.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext != ".mp4":
        return True

    # File is .mp4 — check if codec is already H.264/H.265 compatible
    try:
        info = probe_video_codec(filepath)
        return info["video_codec"] not in ("h264", "hevc", "avc")
    except TranscodeError:
        # Cannot probe → assume transcode needed to be safe
        logger.warning("Could not probe codec for %s — will transcode", filepath)
        return True


# ----------------------------
# Core Transcode Function
# ----------------------------


def transcode_to_mp4(
    input_path: str,
    output_dir: str,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> str:
    """
    Transcode a video file to H.264/AAC MP4 format.

    If the file already meets the requirements (H.264/H.265 in .mp4 container),
    returns the original path unchanged (short-circuit, no file modification).

    Progress is reported as a float 0.0–100.0 via the optional callback.
    The callback receives 100.0 only after the output file has been verified
    and the original deleted.

    Args:
        input_path: Path to the source video file.
        output_dir: Directory where the output .mp4 will be written.
        progress_callback: Optional callable that receives progress (float 0–100).

    Returns:
        Path to the resulting .mp4 file (may equal input_path if short-circuited).

    Raises:
        TranscodeError: If transcoding fails at any stage.
    """

    # ----------------------------
    # Short-circuit check
    # ----------------------------
    if not needs_transcode(input_path):
        logger.info("Skipping transcode (already H.264 MP4): %s", input_path)
        if progress_callback is not None:
            progress_callback(100.0)
        return input_path

    # ----------------------------
    # Probe duration for progress
    # ----------------------------
    try:
        info = probe_video_codec(input_path)
        total_duration = info["duration"]
    except TranscodeError:
        total_duration = 0.0

    # ----------------------------
    # Build output paths
    # ----------------------------
    stem = Path(input_path).stem
    temp_output = Path(output_dir) / f"{stem}.tmp.mp4"
    final_output = Path(output_dir) / f"{stem}.mp4"

    # Remove stale temp file if present
    if temp_output.exists():
        try:
            temp_output.unlink()
        except OSError as e:
            logger.warning("Could not remove stale temp file %s: %s", temp_output, e)

    # ----------------------------
    # Build ffmpeg command
    # ----------------------------
    cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",  # ? = optional, handles files with no audio stream
        "-movflags",
        "+faststart",
        "-y",  # overwrite without asking
        str(temp_output),
    ]

    logger.info("Starting transcode: %s → %s", input_path, final_output)

    # ----------------------------
    # Run ffmpeg with progress
    # ----------------------------
    # Regex for ffmpeg stderr time progress lines
    _TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            universal_newlines=True,
        )

        for line in proc.stderr:  # type: ignore[union-attr]
            match = _TIME_RE.search(line)
            if match and progress_callback is not None and total_duration > 0:
                h, m, s = (
                    int(match.group(1)),
                    int(match.group(2)),
                    float(match.group(3)),
                )
                current_seconds = h * 3600 + m * 60 + s
                pct = min(99.0, (current_seconds / total_duration) * 100.0)
                progress_callback(pct)

        proc.wait(timeout=600)

        if proc.returncode != 0:
            raise TranscodeError(
                f"ffmpeg exited with code {proc.returncode} for {input_path}"
            )

    except subprocess.TimeoutExpired as e:
        if proc is not None:
            proc.kill()
        raise TranscodeError(f"ffmpeg timed out (600s) for {input_path}") from e
    except OSError as e:
        raise TranscodeError(f"ffmpeg process error for {input_path}: {e}") from e
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()

    # ----------------------------
    # Verify output integrity
    # ----------------------------
    if not temp_output.exists() or temp_output.stat().st_size == 0:
        raise TranscodeError(f"Output file is missing or empty: {temp_output}")

    try:
        probe_video_codec(str(temp_output))
    except TranscodeError as e:
        raise TranscodeError(
            f"Output file failed verification ({temp_output}): {e}"
        ) from e

    # ----------------------------
    # Safe delete + rename
    # ----------------------------
    # Delete the original file (Windows may need retry due to file locks)
    _safe_delete(input_path)

    # Rename temp → final
    try:
        temp_output.rename(final_output)
    except OSError as e:
        raise TranscodeError(
            f"Failed to rename {temp_output} → {final_output}: {e}"
        ) from e

    logger.info("Transcode complete: %s", final_output)

    if progress_callback is not None:
        progress_callback(100.0)

    return str(final_output)


# ----------------------------
# Helpers
# ----------------------------


def _safe_delete(filepath: str, retries: int = 3, delay: float = 0.5) -> None:
    """
    Delete a file with retry logic for Windows file-lock issues.

    Args:
        filepath: Path to the file to delete.
        retries: Number of retry attempts.
        delay: Seconds to wait between retries.
    """
    path = Path(filepath)
    for attempt in range(retries):
        try:
            path.unlink(missing_ok=True)
            return
        except OSError as e:
            if attempt < retries - 1:
                logger.debug(
                    "Delete attempt %d failed for %s: %s — retrying in %.1fs",
                    attempt + 1,
                    filepath,
                    e,
                    delay,
                )
                time.sleep(delay)
            else:
                raise TranscodeError(
                    f"Failed to delete {filepath} after {retries} attempts: {e}"
                ) from e

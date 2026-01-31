"""
Subtitle Service - SRT parsing, editing and synchronization
"""

import re
import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from datetime import timedelta

from api.deps import get_output_dir, get_project_root

logger = logging.getLogger(__name__)


@dataclass
class SubtitleEntry:
    """Represents a single subtitle entry"""

    index: int
    start_time: float  # seconds
    end_time: float  # seconds
    text: str  # Main text (translation for trans files, original for src)
    original_text: Optional[str] = (
        None  # Original text (for trans_src dual-language files)
    )

    def to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, secs = divmod(remainder, 60)
        milliseconds = int((secs % 1) * 1000)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(secs):02d},{milliseconds:03d}"

    def to_srt_block(self, include_original: bool = False) -> str:
        """Convert to SRT format block"""
        start = self.to_srt_time(self.start_time)
        end = self.to_srt_time(self.end_time)

        if include_original and self.original_text:
            text = f"{self.text}\n{self.original_text}"
        else:
            text = self.text

        return f"{self.index}\n{start} --> {end}\n{text}\n"


class SubtitleService:
    """Service for subtitle file operations"""

    def __init__(self):
        self.output_dir = get_output_dir()

    # ========== SRT Parsing ==========

    @staticmethod
    def parse_srt_time(time_str: str) -> float:
        """Parse SRT timestamp to seconds"""
        # Format: HH:MM:SS,mmm or HH:MM:SS.mmm
        time_str = time_str.replace(",", ".")
        parts = time_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def parse_srt_file(self, filepath: Path) -> List[SubtitleEntry]:
        """Parse an SRT file into subtitle entries"""
        if not filepath.exists():
            logger.warning(f"SRT file not found: {filepath}")
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        return self.parse_srt_content(content)

    def parse_srt_content(self, content: str) -> List[SubtitleEntry]:
        """Parse SRT content string into subtitle entries"""
        entries = []

        # Split by double newline (subtitle blocks)
        blocks = re.split(r"\n\s*\n", content.strip())

        for block in blocks:
            if not block.strip():
                continue

            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue

            try:
                # First line: index
                index = int(lines[0].strip())

                # Second line: timestamps
                time_match = re.match(
                    r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
                    lines[1].strip(),
                )
                if not time_match:
                    continue

                start_time = self.parse_srt_time(time_match.group(1))
                end_time = self.parse_srt_time(time_match.group(2))

                # Remaining lines: text
                text_lines = lines[2:]

                # Check if this is a dual-language subtitle (trans_src format)
                # First line is translation, second line (if exists) is original
                if len(text_lines) >= 2:
                    text = text_lines[0].strip()
                    original_text = text_lines[1].strip()
                else:
                    text = "\n".join(text_lines).strip()
                    original_text = None

                entries.append(
                    SubtitleEntry(
                        index=index,
                        start_time=start_time,
                        end_time=end_time,
                        text=text,
                        original_text=original_text,
                    )
                )

            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse subtitle block: {e}")
                continue

        return entries

    # ========== SRT Writing ==========

    def write_srt_file(
        self,
        entries: List[SubtitleEntry],
        filepath: Path,
        include_original: bool = False,
    ):
        """Write subtitle entries to SRT file"""
        content = self.entries_to_srt_content(entries, include_original)

        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Written {len(entries)} subtitles to {filepath}")

    def entries_to_srt_content(
        self, entries: List[SubtitleEntry], include_original: bool = False
    ) -> str:
        """Convert subtitle entries to SRT format string"""
        blocks = []
        for entry in entries:
            blocks.append(entry.to_srt_block(include_original))
        return "\n".join(blocks)

    # ========== Multi-file Operations ==========

    def get_all_subtitles(self) -> dict:
        """
        Get all subtitle files data

        Returns dict with:
        - entries: List of unified subtitle entries (using trans_src as base)
        - files: Dict of file paths and their existence status
        """
        src_srt = self.output_dir / "src.srt"
        trans_srt = self.output_dir / "trans.srt"
        trans_src_srt = self.output_dir / "trans_src.srt"
        src_trans_srt = self.output_dir / "src_trans.srt"

        files_status = {
            "src": {"path": str(src_srt), "exists": src_srt.exists()},
            "trans": {"path": str(trans_srt), "exists": trans_srt.exists()},
            "trans_src": {"path": str(trans_src_srt), "exists": trans_src_srt.exists()},
            "src_trans": {"path": str(src_trans_srt), "exists": src_trans_srt.exists()},
        }

        # Parse entries - prefer trans_src as it has both languages
        entries = []

        if trans_src_srt.exists():
            entries = self.parse_srt_file(trans_src_srt)
        elif src_srt.exists() and trans_srt.exists():
            # Merge src and trans
            src_entries = self.parse_srt_file(src_srt)
            trans_entries = self.parse_srt_file(trans_srt)

            # Combine by index
            trans_map = {e.index: e for e in trans_entries}
            for src_entry in src_entries:
                trans_entry = trans_map.get(src_entry.index)
                entries.append(
                    SubtitleEntry(
                        index=src_entry.index,
                        start_time=src_entry.start_time,
                        end_time=src_entry.end_time,
                        text=trans_entry.text if trans_entry else "",
                        original_text=src_entry.text,
                    )
                )
        elif src_srt.exists():
            entries = self.parse_srt_file(src_srt)

        return {"entries": entries, "files": files_status, "totalCount": len(entries)}

    def save_all_subtitles(self, entries: List[SubtitleEntry]) -> dict:
        """
        Save subtitle entries to all SRT files

        Updates:
        - src.srt: Original text only
        - trans.srt: Translation text only
        - trans_src.srt: Translation + Original (line by line)
        - src_trans.srt: Original + Translation (line by line)
        """
        # Reindex entries
        for i, entry in enumerate(entries, 1):
            entry.index = i

        src_srt = self.output_dir / "src.srt"
        trans_srt = self.output_dir / "trans.srt"
        trans_src_srt = self.output_dir / "trans_src.srt"
        src_trans_srt = self.output_dir / "src_trans.srt"

        saved_files = []

        # Write src.srt (original text only)
        src_entries = []
        for entry in entries:
            src_entries.append(
                SubtitleEntry(
                    index=entry.index,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                    text=entry.original_text or entry.text,
                    original_text=None,
                )
            )
        self.write_srt_file(src_entries, src_srt)
        saved_files.append(str(src_srt))

        # Write trans.srt (translation only)
        trans_entries = []
        for entry in entries:
            trans_entries.append(
                SubtitleEntry(
                    index=entry.index,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                    text=entry.text,
                    original_text=None,
                )
            )
        self.write_srt_file(trans_entries, trans_srt)
        saved_files.append(str(trans_srt))

        # Write trans_src.srt (translation + original)
        self.write_srt_file(entries, trans_src_srt, include_original=True)
        saved_files.append(str(trans_src_srt))

        # Write src_trans.srt (original + translation)
        src_trans_entries = []
        for entry in entries:
            src_trans_entries.append(
                SubtitleEntry(
                    index=entry.index,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                    text=entry.original_text or "",
                    original_text=entry.text,
                )
            )
        self.write_srt_file(src_trans_entries, src_trans_srt, include_original=True)
        saved_files.append(str(src_trans_srt))

        logger.info(f"Saved subtitles to {len(saved_files)} files")

        return {"success": True, "savedFiles": saved_files, "entryCount": len(entries)}

    # ========== Merge to Video ==========

    def merge_subtitles_to_video(self, subtitle_type: str = "dual") -> dict:
        """
        Manually trigger subtitle merge to video

        subtitle_type options:
        - "dual": Both src.srt and trans.srt (default, dual language overlay)
        - "trans_only": Only translation subtitles
        - "src_only": Only source/original subtitles
        - "trans_src": trans_src.srt (single file with both languages)
        - "src_trans": src_trans.srt (single file with both languages, reversed order)
        """
        import sys

        project_root = get_project_root()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from core._7_sub_into_vid import merge_subtitles_to_video as core_merge

        try:
            # Determine which subtitle files to use based on subtitle_type
            if subtitle_type == "dual":
                # Default behavior: use src.srt and trans.srt
                core_merge()
            elif subtitle_type == "trans_only":
                # Only translation: temporarily copy trans.srt to both
                self._merge_with_single_subtitle("trans.srt", is_translation=True)
            elif subtitle_type == "src_only":
                # Only source: temporarily copy src.srt to both
                self._merge_with_single_subtitle("src.srt", is_translation=False)
            elif subtitle_type == "trans_src":
                # Single bilingual file: trans_src.srt
                self._merge_with_bilingual_file("trans_src.srt")
            elif subtitle_type == "src_trans":
                # Single bilingual file: src_trans.srt (reversed order)
                self._merge_with_bilingual_file("src_trans.srt")
            else:
                # Fallback to default
                core_merge()

            output_video = self.output_dir / "output_sub.mp4"

            return {
                "success": True,
                "outputVideo": str(output_video),
                "exists": output_video.exists(),
            }
        except Exception as e:
            logger.error(f"Failed to merge subtitles to video: {e}")
            return {"success": False, "error": str(e)}

    def _escape_ffmpeg_path(self, path: str) -> str:
        """
        Escape path for FFmpeg subtitles filter.

        FFmpeg subtitles filter has special requirements for Windows paths:
        - Backslashes must be escaped or use forward slashes instead
        - Colons must be escaped with backslash (e.g., C\:/path)
        """
        # Convert to forward slashes (works on Windows too)
        escaped = str(path).replace("\\", "/")
        # Escape colons in drive letter (e.g., D: -> D\:)
        # FFmpeg uses : as option separator in filter syntax
        if len(escaped) >= 2 and escaped[1] == ":":
            escaped = escaped[0] + "\\:" + escaped[2:]
        return escaped

    def _merge_with_single_subtitle(self, srt_filename: str, is_translation: bool):
        """Merge video with a single subtitle file (either src or trans only)"""
        import subprocess
        import time
        import cv2
        from core._1_ytdlp import find_video_files
        from core.utils import load_key
        from core._7_sub_into_vid import get_subtitle_style

        video_file = find_video_files()
        srt_path = self.output_dir / srt_filename
        output_video = self.output_dir / "output_sub.mp4"

        if not srt_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {srt_path}")

        if not load_key("burn_subtitles"):
            import numpy as np

            # Create placeholder
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(str(output_video), fourcc, 1, (1920, 1080))
            out.write(frame)
            out.release()
            return

        video = cv2.VideoCapture(video_file)
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video.release()

        # Get dynamic style from config
        style = get_subtitle_style()
        if is_translation:
            font_size = style["trans_font_size"]
            font_color = style["trans_font_color"]
        else:
            font_size = style["src_font_size"]
            font_color = style["src_font_color"]
        margin_v = style["margin_v"]

        # Escape path for FFmpeg subtitles filter
        escaped_srt_path = self._escape_ffmpeg_path(str(srt_path))

        ffmpeg_cmd = [
            "ffmpeg",
            "-i",
            video_file,
            "-vf",
            (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                f"subtitles='{escaped_srt_path}':force_style='FontSize={font_size},"
                f"FontName=Arial,PrimaryColour={font_color},OutlineColour=&H000000,"
                f"OutlineWidth=1,BorderStyle=1,Alignment=2,MarginV={margin_v}'"
            ),
        ]

        if load_key("ffmpeg_gpu"):
            ffmpeg_cmd.extend(["-c:v", "h264_nvenc"])
        ffmpeg_cmd.extend(["-y", str(output_video)])

        logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        process = subprocess.Popen(
            ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            logger.error(f"FFmpeg stderr: {stderr.decode('utf-8', errors='ignore')}")
            raise RuntimeError(
                f"FFmpeg execution failed: {stderr.decode('utf-8', errors='ignore')[:500]}"
            )

    def _merge_with_bilingual_file(self, srt_filename: str):
        """Merge video with a single bilingual subtitle file"""
        import subprocess
        import cv2
        from core._1_ytdlp import find_video_files
        from core.utils import load_key
        from core._7_sub_into_vid import get_subtitle_style

        video_file = find_video_files()
        srt_path = self.output_dir / srt_filename
        output_video = self.output_dir / "output_sub.mp4"

        if not srt_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {srt_path}")

        if not load_key("burn_subtitles"):
            import numpy as np

            # Create placeholder
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(str(output_video), fourcc, 1, (1920, 1080))
            out.write(frame)
            out.release()
            return

        video = cv2.VideoCapture(video_file)
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video.release()

        # Get dynamic style from config
        style = get_subtitle_style()
        # For bilingual, use translation font size (larger, as it includes both lines)
        font_size = style["trans_font_size"]
        font_color = style["trans_font_color"]
        margin_v = style["margin_v"]

        # Escape path for FFmpeg subtitles filter
        escaped_srt_path = self._escape_ffmpeg_path(str(srt_path))

        ffmpeg_cmd = [
            "ffmpeg",
            "-i",
            video_file,
            "-vf",
            (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                f"subtitles='{escaped_srt_path}':force_style='FontSize={font_size},"
                f"FontName=Arial,PrimaryColour={font_color},OutlineColour=&H000000,"
                f"OutlineWidth=1,BorderStyle=1,Alignment=2,MarginV={margin_v}'"
            ),
        ]

        if load_key("ffmpeg_gpu"):
            ffmpeg_cmd.extend(["-c:v", "h264_nvenc"])
        ffmpeg_cmd.extend(["-y", str(output_video)])

        logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        process = subprocess.Popen(
            ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            logger.error(f"FFmpeg stderr: {stderr.decode('utf-8', errors='ignore')}")
            raise RuntimeError(
                f"FFmpeg execution failed: {stderr.decode('utf-8', errors='ignore')[:500]}"
            )

    # ========== Audio Stream ==========

    def get_audio_path(self) -> Optional[Path]:
        """Get path to audio file for waveform generation"""
        # Prefer raw/original audio for waveform display
        # This shows the complete audio track including background music
        raw_audio = self.output_dir / "audio" / "raw.mp3"
        vocal_audio = self.output_dir / "audio" / "vocal.mp3"

        if raw_audio.exists():
            return raw_audio
        elif vocal_audio.exists():
            return vocal_audio

        return None

    # ========== Backup & Restore ==========

    def get_backup_dir(self) -> Path:
        """Get backup directory path"""
        return self.output_dir / "backup"

    def backup_original_subtitles(self) -> dict:
        """
        Backup original subtitle files after generation (before any edits)

        Creates backup directory and copies all SRT files there.
        Only creates backup if it doesn't already exist (preserves original).
        """
        backup_dir = self.get_backup_dir()

        # List of files to backup
        srt_files = ["src.srt", "trans.srt", "trans_src.srt", "src_trans.srt"]
        backed_up = []
        skipped = []

        for filename in srt_files:
            src_file = self.output_dir / filename
            backup_file = backup_dir / filename

            if not src_file.exists():
                continue

            # Only backup if backup doesn't exist (preserve original)
            if backup_file.exists():
                skipped.append(filename)
                continue

            # Create backup directory if needed
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Copy file to backup
            shutil.copy2(src_file, backup_file)
            backed_up.append(filename)
            logger.info(f"Backed up {filename} to {backup_file}")

        return {
            "success": True,
            "backedUp": backed_up,
            "skipped": skipped,
            "backupDir": str(backup_dir),
        }

    def has_backup(self) -> bool:
        """Check if backup exists"""
        backup_dir = self.get_backup_dir()
        if not backup_dir.exists():
            return False

        # Check if at least trans_src.srt backup exists
        return (backup_dir / "trans_src.srt").exists()

    def restore_original_subtitles(self) -> dict:
        """
        Restore subtitle files from backup

        Copies all backed up SRT files back to output directory,
        overwriting any user edits.
        """
        backup_dir = self.get_backup_dir()

        if not backup_dir.exists():
            return {
                "success": False,
                "error": "No backup found. Cannot restore.",
                "restored": [],
            }

        # List of files to restore
        srt_files = ["src.srt", "trans.srt", "trans_src.srt", "src_trans.srt"]
        restored = []

        for filename in srt_files:
            backup_file = backup_dir / filename
            dest_file = self.output_dir / filename

            if not backup_file.exists():
                continue

            # Copy backup back to output
            shutil.copy2(backup_file, dest_file)
            restored.append(filename)
            logger.info(f"Restored {filename} from backup")

        if not restored:
            return {
                "success": False,
                "error": "No backup files found to restore.",
                "restored": [],
            }

        return {
            "success": True,
            "restored": restored,
            "message": f"Restored {len(restored)} subtitle files from backup.",
        }

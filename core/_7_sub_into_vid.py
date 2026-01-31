import os, subprocess, time
from core._1_ytdlp import find_video_files
import cv2
import numpy as np
import platform
from core.utils import *

# ==================== Default Subtitle Style ====================
# These values can be overridden by config.yaml subtitle.style section


def get_subtitle_style():
    """Get subtitle style from config with fallback to defaults"""
    try:
        style_config = load_key("subtitle.style")
    except KeyError:
        style_config = {}

    # Translation subtitle settings
    trans_config = style_config.get("translation", {}) if style_config else {}
    trans_font_size = trans_config.get("font_size", 17)
    trans_font_color = hex_to_ass_color(trans_config.get("font_color", "#FFFFFF"))

    # Original subtitle settings
    orig_config = style_config.get("original", {}) if style_config else {}
    src_font_size = orig_config.get("font_size", 15)
    src_font_color = hex_to_ass_color(orig_config.get("font_color", "#FFFFFF"))

    # Layout settings
    layout_config = style_config.get("layout", {}) if style_config else {}
    margin_v = layout_config.get("margin_bottom", 27)

    return {
        "src_font_size": src_font_size,
        "trans_font_size": trans_font_size,
        "src_font_color": src_font_color,
        "trans_font_color": trans_font_color,
        "margin_v": margin_v,
    }


def hex_to_ass_color(hex_color: str) -> str:
    """Convert hex color (#RRGGBB) to ASS color format (&HBBGGRR)"""
    if not hex_color.startswith("#"):
        return hex_color  # Already in ASS format
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
        return f"&H{b}{g}{r}"
    return "&HFFFFFF"  # Default white


def escape_ffmpeg_path(path: str) -> str:
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


# Font names by platform
FONT_NAME = "Arial"
TRANS_FONT_NAME = "Arial"

# Linux need to install google noto fonts: apt-get install fonts-noto
if platform.system() == "Linux":
    FONT_NAME = "NotoSansCJK-Regular"
    TRANS_FONT_NAME = "NotoSansCJK-Regular"
# Mac OS has different font names
elif platform.system() == "Darwin":
    FONT_NAME = "Arial Unicode MS"
    TRANS_FONT_NAME = "Arial Unicode MS"

# Outline and shadow colors (fixed)
SRC_OUTLINE_COLOR = "&H000000"
SRC_OUTLINE_WIDTH = 1
SRC_SHADOW_COLOR = "&H80000000"
TRANS_OUTLINE_COLOR = "&H000000"
TRANS_OUTLINE_WIDTH = 1
TRANS_BACK_COLOR = "&H33000000"

OUTPUT_DIR = "output"
OUTPUT_VIDEO = f"{OUTPUT_DIR}/output_sub.mp4"
SRC_SRT = f"{OUTPUT_DIR}/src.srt"
TRANS_SRT = f"{OUTPUT_DIR}/trans.srt"


def check_gpu_available():
    try:
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        return "h264_nvenc" in result.stdout
    except:
        return False


def merge_subtitles_to_video():
    video_file = find_video_files()
    os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)

    # Check resolution
    if not load_key("burn_subtitles"):
        rprint(
            "[bold yellow]Warning: A 0-second black video will be generated as a placeholder as subtitles are not burned in.[/bold yellow]"
        )

        # Create a black frame
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, 1, (1920, 1080))
        out.write(frame)
        out.release()

        rprint("[bold green]Placeholder video has been generated.[/bold green]")
        return

    if not os.path.exists(SRC_SRT) or not os.path.exists(TRANS_SRT):
        rprint("Subtitle files not found in the 'output' directory.")
        exit(1)

    video = cv2.VideoCapture(video_file)
    TARGET_WIDTH = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    TARGET_HEIGHT = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video.release()
    rprint(f"[bold green]Video resolution: {TARGET_WIDTH}x{TARGET_HEIGHT}[/bold green]")

    # Get dynamic subtitle style from config
    style = get_subtitle_style()
    SRC_FONT_SIZE = style["src_font_size"]
    SRC_FONT_COLOR = style["src_font_color"]
    TRANS_FONT_SIZE = style["trans_font_size"]
    TRANS_FONT_COLOR = style["trans_font_color"]
    MARGIN_V = style["margin_v"]

    # Escape paths for FFmpeg subtitles filter
    escaped_src_srt = escape_ffmpeg_path(SRC_SRT)
    escaped_trans_srt = escape_ffmpeg_path(TRANS_SRT)

    ffmpeg_cmd = [
        "ffmpeg",
        "-i",
        video_file,
        "-vf",
        (
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            f"subtitles='{escaped_src_srt}':force_style='FontSize={SRC_FONT_SIZE},FontName={FONT_NAME},"
            f"PrimaryColour={SRC_FONT_COLOR},OutlineColour={SRC_OUTLINE_COLOR},OutlineWidth={SRC_OUTLINE_WIDTH},"
            f"ShadowColour={SRC_SHADOW_COLOR},BorderStyle=1',"
            f"subtitles='{escaped_trans_srt}':force_style='FontSize={TRANS_FONT_SIZE},FontName={TRANS_FONT_NAME},"
            f"PrimaryColour={TRANS_FONT_COLOR},OutlineColour={TRANS_OUTLINE_COLOR},OutlineWidth={TRANS_OUTLINE_WIDTH},"
            f"ShadowColour={SRC_SHADOW_COLOR},BorderStyle=1,Alignment=2,MarginV={MARGIN_V}'"
        ),
    ]

    ffmpeg_gpu = load_key("ffmpeg_gpu")
    if ffmpeg_gpu:
        rprint("[bold green]will use GPU acceleration.[/bold green]")
        ffmpeg_cmd.extend(["-c:v", "h264_nvenc"])
    ffmpeg_cmd.extend(["-y", OUTPUT_VIDEO])

    rprint("🎬 Start merging subtitles to video...")
    start_time = time.time()
    process = subprocess.Popen(
        ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    try:
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            rprint(f"\n✅ Done! Time taken: {time.time() - start_time:.2f} seconds")
        else:
            rprint(
                f"\n❌ FFmpeg execution error: {stderr.decode('utf-8', errors='ignore')[:500]}"
            )
            raise RuntimeError("FFmpeg execution failed")
    except Exception as e:
        rprint(f"\n❌ Error occurred: {e}")
        if process.poll() is None:
            process.kill()
        raise


if __name__ == "__main__":
    merge_subtitles_to_video()

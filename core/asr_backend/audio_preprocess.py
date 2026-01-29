import os, subprocess
import pandas as pd
from typing import Dict, List, Tuple
from pydub import AudioSegment
from core.utils import *
from core.utils.models import *
from pydub import AudioSegment
from pydub.silence import detect_silence
from pydub.utils import mediainfo
from rich import print as rprint


def normalize_audio_volume(audio_path, output_path, target_db=-20.0, format="wav"):
    audio = AudioSegment.from_file(audio_path)
    change_in_dBFS = target_db - audio.dBFS
    normalized_audio = audio.apply_gain(change_in_dBFS)
    normalized_audio.export(output_path, format=format)
    rprint(
        f"[green]✅ Audio normalized from {audio.dBFS:.1f}dB to {target_db:.1f}dB[/green]"
    )
    return output_path


def get_video_audio_channels(video_file: str) -> int:
    """Get the number of audio channels from video file using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=channels",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        channels = int(result.stdout.strip())
        return channels
    except Exception as e:
        rprint(
            f"[yellow]⚠️ Failed to detect audio channels: {e}, defaulting to 2[/yellow]"
        )
        return 2  # 默认双声道


def convert_video_to_audio(video_file: str):
    os.makedirs(_AUDIO_DIR, exist_ok=True)
    if not os.path.exists(_RAW_AUDIO_FILE):
        # 检测原始视频的声道数
        channels = get_video_audio_channels(video_file)
        bitrate = 32 * channels  # 每声道 32kbps
        rprint(
            f"[blue]🎬➡️🎵 Converting to audio (channels: {channels}, bitrate: {bitrate}k) ......[/blue]"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_file,
                "-vn",
                "-c:a",
                "libmp3lame",
                "-b:a",
                f"{bitrate}k",
                "-ar",
                "16000",
                "-ac",
                str(channels),
                "-metadata",
                "encoding=UTF-8",
                _RAW_AUDIO_FILE,
            ],
            check=True,
            stderr=subprocess.PIPE,
        )
        rprint(
            f"[green]🎬➡️🎵 Converted <{video_file}> to <{_RAW_AUDIO_FILE}> ({channels} channels)\n[/green]"
        )


def get_audio_duration(audio_file: str) -> float:
    """Get the duration of an audio file using ffmpeg."""
    cmd = ["ffmpeg", "-i", audio_file]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, stderr = process.communicate()
    output = stderr.decode("utf-8", errors="ignore")

    try:
        duration_str = [line for line in output.split("\n") if "Duration" in line][0]
        duration_parts = duration_str.split("Duration: ")[1].split(",")[0].split(":")
        duration = (
            float(duration_parts[0]) * 3600
            + float(duration_parts[1]) * 60
            + float(duration_parts[2])
        )
    except Exception as e:
        print(f"[red]❌ Error: Failed to get audio duration: {e}[/red]")
        duration = 0
    return duration


def split_audio(
    audio_file: str, target_len: float = 30 * 60, win: float = 60
) -> List[Tuple[float, float]]:
    ## 在 [target_len-win, target_len+win] 区间内用 pydub 检测静默，切分音频
    rprint(
        f"[blue]🎙️ Starting audio segmentation {audio_file} {target_len} {win}[/blue]"
    )
    audio = AudioSegment.from_file(audio_file)
    duration = float(mediainfo(audio_file)["duration"])
    if duration <= target_len + win:
        return [(0, duration)]
    segments, pos = [], 0.0
    safe_margin = 0.5  # 静默点前后安全边界，单位秒

    while pos < duration:
        if duration - pos <= target_len:
            segments.append((pos, duration))
            break

        threshold = pos + target_len
        ws, we = int((threshold - win) * 1000), int((threshold + win) * 1000)

        # 获取完整的静默区域
        silence_regions = detect_silence(
            audio[ws:we], min_silence_len=int(safe_margin * 1000), silence_thresh=-30
        )
        silence_regions = [
            (s / 1000 + (threshold - win), e / 1000 + (threshold - win))
            for s, e in silence_regions
        ]
        # 筛选长度足够（至少1秒）且位置适合的静默区域
        valid_regions = [
            (start, end)
            for start, end in silence_regions
            if (end - start) >= (safe_margin * 2)
            and threshold <= start + safe_margin <= threshold + win
        ]

        if valid_regions:
            start, end = valid_regions[0]
            split_at = start + safe_margin  # 在静默区域起始点后0.5秒处切分
        else:
            rprint(
                f"[yellow]⚠️ No valid silence regions found for {audio_file} at {threshold}s, using threshold[/yellow]"
            )
            split_at = threshold

        segments.append((pos, split_at))
        pos = split_at

    rprint(f"[green]🎙️ Audio split completed {len(segments)} segments[/green]")
    return segments


def smooth_speaker_ids(
    df: pd.DataFrame, min_segment_duration: float = 0.5, gap_threshold: float = 0.3
) -> pd.DataFrame:
    """
    Smooth speaker IDs to fix fragmented speaker assignments.

    Problem: WhisperX diarization is time-based, not semantic-based. This can cause:
    - Same sentence split across different speakers (e.g., "こいつがグラムアメリア様")
    - Rapid speaker switches within short time windows

    Solution: Apply smoothing rules:
    1. Short segments (< min_segment_duration) inherit speaker from surrounding context
    2. Segments with small gaps (< gap_threshold) are merged with neighbors
    3. Majority vote within semantic units (same segment from WhisperX)

    Args:
        df: DataFrame with columns ['text', 'start', 'end', 'speaker_id']
        min_segment_duration: Minimum duration (seconds) for a valid speaker segment
        gap_threshold: Maximum gap (seconds) to consider words as continuous speech

    Returns:
        DataFrame with smoothed speaker_id assignments
    """
    if df.empty or "speaker_id" not in df.columns:
        return df

    # Skip if all speaker_ids are None
    if df["speaker_id"].isna().all():
        return df

    df = df.copy()

    # Step 1: Forward fill None speaker_ids (inherit from previous word)
    df["speaker_id"] = df["speaker_id"].ffill()
    # Backward fill any remaining None at the beginning
    df["speaker_id"] = df["speaker_id"].bfill()

    # Step 2: Identify speaker segments (consecutive words with same speaker)
    df["speaker_change"] = (df["speaker_id"] != df["speaker_id"].shift()).cumsum()

    # Step 3: Fix short speaker segments (likely errors)
    segment_stats = (
        df.groupby("speaker_change")
        .agg({"start": "min", "end": "max", "speaker_id": "first"})
        .reset_index()
    )
    segment_stats["duration"] = segment_stats["end"] - segment_stats["start"]

    # Find short segments that should be merged
    short_segments = segment_stats[segment_stats["duration"] < min_segment_duration][
        "speaker_change"
    ].tolist()

    for seg_id in short_segments:
        # Get previous and next segment speakers
        seg_idx = segment_stats[segment_stats["speaker_change"] == seg_id].index[0]

        prev_speaker = None
        next_speaker = None

        if seg_idx > 0:
            prev_speaker = segment_stats.iloc[seg_idx - 1]["speaker_id"]
        if seg_idx < len(segment_stats) - 1:
            next_speaker = segment_stats.iloc[seg_idx + 1]["speaker_id"]

        # Decide which speaker to assign
        if prev_speaker == next_speaker and prev_speaker is not None:
            # Surrounded by same speaker - definitely an error
            new_speaker = prev_speaker
        elif prev_speaker is not None:
            # Default to previous speaker (more natural in conversation)
            new_speaker = prev_speaker
        elif next_speaker is not None:
            new_speaker = next_speaker
        else:
            continue  # Can't determine, skip

        # Update speaker_id for this segment
        df.loc[df["speaker_change"] == seg_id, "speaker_id"] = new_speaker

    # Step 4: Fix rapid switches (words very close together but different speakers)
    df["gap_to_prev"] = df["start"] - df["end"].shift()
    df["gap_to_prev"] = df["gap_to_prev"].fillna(0)

    for i in range(1, len(df)):
        if df.iloc[i]["gap_to_prev"] < gap_threshold:
            # Check if this is an isolated speaker switch
            prev_speaker = df.iloc[i - 1]["speaker_id"]
            curr_speaker = df.iloc[i]["speaker_id"]

            if prev_speaker != curr_speaker:
                # Look ahead to see if this is a real switch or just noise
                lookahead = min(i + 5, len(df))
                future_speakers = df.iloc[i:lookahead]["speaker_id"].tolist()

                # If most future words return to prev_speaker, this is likely noise
                if future_speakers.count(prev_speaker) > future_speakers.count(
                    curr_speaker
                ):
                    df.iloc[i, df.columns.get_loc("speaker_id")] = prev_speaker

    # Clean up temporary columns
    df = df.drop(columns=["speaker_change", "gap_to_prev"], errors="ignore")

    rprint(f"[cyan]Speaker ID smoothing complete[/cyan]")
    return df


def split_by_punctuation(text: str, start: float, end: float, speaker_id) -> list:
    """Split a long segment by punctuation marks and spaces, estimate timestamps.
    
    For CJK languages (Japanese, Chinese), splits on:
    - Sentence-ending punctuation: 。！？!?
    - Spaces (half-width and full-width) - indicates speaker/pause in Japanese
    
    Timestamps are estimated proportionally based on character count.
    
    Args:
        text: The segment text to split
        start: Start time of the segment
        end: End time of the segment
        speaker_id: Speaker ID for the segment
        
    Returns:
        List of dicts with text, start, end, speaker_id
    """
    import re
    
    # First, split by sentence-ending punctuation
    # Japanese: 。！？  Chinese: 。！？  Western: .!?
    punct_pattern = r'([。！？!?]+)'
    
    parts = re.split(punct_pattern, text)
    
    # Combine text with its punctuation
    sentences = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if not part:
            i += 1
            continue
        # Check if next part is punctuation
        if i + 1 < len(parts) and re.match(r'[。！？!?]+', parts[i + 1]):
            sentences.append(part + parts[i + 1])
            i += 2
        else:
            if part.strip():
                sentences.append(part.strip())
            i += 1
    
    # If no punctuation split happened, try splitting by spaces
    if len(sentences) <= 1 and text.strip():
        # Split by spaces (both half-width and full-width)
        space_parts = re.split(r'[ 　]+', text.strip())
        # Filter empty parts and only use if we get multiple parts
        space_parts = [p.strip() for p in space_parts if p.strip()]
        if len(space_parts) > 1:
            sentences = space_parts
    
    # If still no split happened, return original
    if len(sentences) <= 1:
        return [{
            "text": text.strip(),
            "start": start,
            "end": end,
            "speaker_id": speaker_id,
        }]
    
    # Estimate timestamps proportionally by character count
    total_chars = sum(len(s) for s in sentences)
    if total_chars == 0:
        return [{
            "text": text.strip(),
            "start": start,
            "end": end,
            "speaker_id": speaker_id,
        }]
    
    duration = end - start
    result = []
    current_time = start
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        char_ratio = len(sentence) / total_chars
        sentence_duration = duration * char_ratio
        
        result.append({
            "text": sentence,
            "start": round(current_time, 3),
            "end": round(current_time + sentence_duration, 3),
            "speaker_id": speaker_id,
        })
        current_time += sentence_duration
    
    return result


def process_transcription_segment_mode(result: Dict) -> pd.DataFrame:
    """Process transcription using Whisper's native segment-level output.
    
    Each segment is treated as one subtitle unit. This uses Whisper's natural
    sentence breaks, which works well for most languages.
    
    For CJK languages, long segments are further split by punctuation marks
    (。！？) and spaces (speaker changes) to create more natural subtitle lengths.
    """
    all_rows = []
    
    for segment in result["segments"]:
        text = segment.get("text", "").strip()
        if not text:
            continue
            
        # Clean up text (French guillemets etc.)
        text = text.replace("»", "").replace("«", "")
        
        # Get speaker from segment level (if available from diarization)
        segment_speaker = segment.get("speaker", segment.get("speaker_id", None))
        
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        
        # Split long segments by punctuation and spaces for better subtitle lengths
        split_rows = split_by_punctuation(text, start, end, segment_speaker)
        all_rows.extend(split_rows)
    
    df = pd.DataFrame(all_rows)
    rprint(f"[green]✓ Segment mode: {len(df)} segments created (split by punctuation/spaces)[/green]")
    return df


def process_transcription_word_mode(result: Dict) -> pd.DataFrame:
    """Process transcription using word-level output with speaker-based splitting.
    
    Each word is output separately, then grouped by speaker changes.
    This provides more precise control but may result in character-level output for CJK.
    """
    all_words = []
    for segment in result["segments"]:
        # Get speaker_id from 'speaker' (WhisperX diarization output) or 'speaker_id'
        segment_speaker = segment.get("speaker", segment.get("speaker_id", None))

        # Collect all word-level speakers in this segment for majority vote
        segment_words = segment.get("words", [])
        word_speakers = [w.get("speaker", segment_speaker) for w in segment_words]

        # Count speaker occurrences (excluding None)
        speaker_counts = {}
        for sp in word_speakers:
            if sp is not None:
                speaker_counts[sp] = speaker_counts.get(sp, 0) + 1

        # Determine segment's dominant speaker (majority vote)
        if speaker_counts:
            dominant_speaker = max(
                speaker_counts.keys(), key=lambda x: speaker_counts[x]
            )
        else:
            dominant_speaker = segment_speaker

        for word in segment_words:
            # Use word-level speaker if available, otherwise use segment's dominant speaker
            word_speaker = word.get("speaker", None)

            # If word speaker differs from dominant speaker and segment is short,
            # prefer dominant speaker (reduces fragmentation)
            if word_speaker is None:
                word_speaker = dominant_speaker
            elif word_speaker != dominant_speaker:
                # Calculate if this word is isolated (different from surrounding words)
                word_idx = segment_words.index(word)
                prev_speaker = (
                    segment_words[word_idx - 1].get("speaker", dominant_speaker)
                    if word_idx > 0
                    else dominant_speaker
                )
                next_speaker = (
                    segment_words[word_idx + 1].get("speaker", dominant_speaker)
                    if word_idx < len(segment_words) - 1
                    else dominant_speaker
                )

                # If surrounded by different speaker, likely this word's speaker is noise
                if prev_speaker == next_speaker and prev_speaker != word_speaker:
                    word_speaker = prev_speaker

            # Check word length
            if len(word["word"]) > 30:
                rprint(
                    f"[yellow]⚠️ Warning: Detected word longer than 30 characters, skipping: {word['word']}[/yellow]"
                )
                continue

            # ! For French, we need to convert guillemets to empty strings
            word["word"] = word["word"].replace("»", "").replace("«", "")

            if "start" not in word and "end" not in word:
                if all_words:
                    # Assign the end time of the previous word as the start and end time of the current word
                    word_dict = {
                        "text": word["word"],
                        "start": all_words[-1]["end"],
                        "end": all_words[-1]["end"],
                        "speaker_id": word_speaker,
                    }
                    all_words.append(word_dict)
                else:
                    # If it's the first word, look next for a timestamp then assign it to the current word
                    next_word = next(
                        (w for w in segment_words if "start" in w and "end" in w), None
                    )
                    if next_word:
                        word_dict = {
                            "text": word["word"],
                            "start": next_word["start"],
                            "end": next_word["end"],
                            "speaker_id": word_speaker,
                        }
                        all_words.append(word_dict)
                    else:
                        raise Exception(
                            f"No next word with timestamp found for the current word : {word}"
                        )
            else:
                # Normal case, with start and end times
                word_dict = {
                    "text": f"{word['word']}",
                    "start": word.get(
                        "start", all_words[-1]["end"] if all_words else 0
                    ),
                    "end": word["end"],
                    "speaker_id": word_speaker,
                }

                all_words.append(word_dict)

    df = pd.DataFrame(all_words)

    # Apply speaker ID smoothing to fix fragmented assignments
    if not df.empty and "speaker_id" in df.columns:
        df = smooth_speaker_ids(df)

    rprint(f"[green]✓ Word mode: {len(df)} words created[/green]")
    return df


def process_transcription(result: Dict) -> pd.DataFrame:
    """Process transcription result to DataFrame.
    
    Always uses word mode now (segment mode switch removed from config):
    - Word mode: Uses word-level timestamps with speaker-based splitting (more precise)
    """
    rprint("[cyan]📝 Using word mode (character-level with speaker splitting)[/cyan]")
    return process_transcription_word_mode(result)


def save_results(df: pd.DataFrame, is_segment_mode: bool = False):
    os.makedirs("output/log", exist_ok=True)

    # Remove rows where 'text' is empty
    initial_rows = len(df)
    df = df[df["text"].str.len() > 0]
    removed_rows = initial_rows - len(df)
    if removed_rows > 0:
        rprint(f"[blue]ℹ️ Removed {removed_rows} row(s) with empty text.[/blue]")

    # Only check for abnormally long words in word mode (not segment mode)
    # In segment mode, each row is a full sentence which can be very long
    if not is_segment_mode:
        long_words = df[df["text"].str.len() > 30]
        if not long_words.empty:
            rprint(
                f"[yellow]⚠️ Warning: Detected {len(long_words)} word(s) longer than 30 characters. These will be removed.[/yellow]"
            )
            df = df[df["text"].str.len() <= 30]

    df["text"] = df["text"].apply(lambda x: f'"{x}"')
    df.to_excel(_2_CLEANED_CHUNKS, index=False)
    rprint(f"[green]📊 Excel file saved to {_2_CLEANED_CHUNKS}[/green]")


def save_segments(result: dict):
    """Save segment-level timestamps for CJK languages.
    
    This processes Whisper's raw VAD segments and optionally splits them by punctuation
    to create sentence-level output. Each segment contains the text, start/end 
    time, and speaker info. Used for subtitle alignment and adjustment.
    """
    from core.utils.models import _2_SEGMENTS

    segments_data = []
    for segment in result["segments"]:
        text = segment.get("text", "").strip()
        if not text:
            continue
            
        # Clean up text (French guillemets etc.)
        text = text.replace("»", "").replace("«", "")
        
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        speaker = segment.get("speaker", "")
        
        # Split by punctuation for WhisperX; keep raw segments for native whisper
        runtime = load_key("whisper.runtime")
        if runtime in ("whisperx_local", "local", "cloud"):
            split_rows = split_by_punctuation(text, start, end, speaker)
            segments_data.extend(split_rows)
        else:
            segments_data.append({
                "text": text,
                "start": start,
                "end": end,
                "speaker_id": speaker,
            })

    df_segments = pd.DataFrame(segments_data)
    # Rename speaker_id to speaker for consistency
    if 'speaker_id' in df_segments.columns:
        df_segments = df_segments.rename(columns={'speaker_id': 'speaker'})
    df_segments.to_excel(_2_SEGMENTS, index=False)
    rprint(f"[green]Segments file saved to {_2_SEGMENTS} ({len(segments_data)} sentences)[/green]")


def save_language(language: str):
    update_key("whisper.detected_language", language)

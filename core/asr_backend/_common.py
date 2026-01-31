"""
Common utilities for ASR backends.
Shared functions for device config, model loading, alignment, and speaker diarization.
"""
import math
import os
import time
import subprocess
import torch
import whisperx
from pydub import AudioSegment
from rich import print as rprint
from core.utils import load_key, update_key, except_handler

MODEL_DIR = load_key("model_dir")


def get_language_prompt(language: str) -> str:
    """Get default language prompt for punctuation guidance."""
    language_prompts = {
        "ja": "タイトルは、瓢箪屋のドーナツに賭けます。アニメの字幕です。",
        "zh": "这是中文字幕，请使用正确的标点符号。",
        "ko": "한국어 자막입니다. 정확한 문장 부호를 사용하세요.",
        "en": "Subtitles for video. Please use proper punctuation.",
    }
    return language_prompts.get(language, "")


def select_vad_parameters(audio_path: str) -> dict:
    """Select VAD parameters based on RMS loudness (dBFS)."""
    try:
        audio = AudioSegment.from_file(audio_path)
        rms_dbfs = audio.dBFS
    except Exception as exc:
        rprint(f"[yellow]⚠️ Failed to read audio RMS: {exc}, using default VAD[/yellow]")
        rms_dbfs = None

    if rms_dbfs is None or math.isinf(rms_dbfs):
        rms_dbfs = -120.0

    if rms_dbfs < -30.0:
        return {
            "threshold": 0.1,
            "min_speech_duration_ms": 40,
            "min_silence_duration_ms": 40,
            "_rms_dbfs": rms_dbfs,
        }
    if rms_dbfs < -20.0:
        return {
            "threshold": 0.15,
            "min_speech_duration_ms": 60,
            "min_silence_duration_ms": 60,
            "_rms_dbfs": rms_dbfs,
        }
    return {
        "threshold": 0.2,
        "min_speech_duration_ms": 80,
        "min_silence_duration_ms": 80,
        "_rms_dbfs": rms_dbfs,
    }


# ============================================================================
# Device Configuration
# ============================================================================

def get_device_config():
    """Get device, compute_type, and batch_size based on hardware."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if device == "cuda":
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        compute_type = "float16" if torch.cuda.is_bf16_supported() else "int8"
        batch_size = 16 if gpu_mem > 8 else 2
        rprint(f"[cyan]🎮 GPU:[/cyan] {gpu_mem:.2f} GB, [cyan]Compute:[/cyan] {compute_type}, [cyan]Batch:[/cyan] {batch_size}")
    else:
        compute_type = "int8"
        batch_size = 1
        rprint(f"[cyan]💻 CPU mode, Compute:[/cyan] {compute_type}")
    
    return device, compute_type, batch_size


# ============================================================================
# Model Path Resolution
# ============================================================================

def find_whisper_model_path(language: str = None):
    """
    Find local Whisper model path or return model name for download.
    Returns: (model_path, model_name)
    """
    if language == "zh":
        model_name = "Huan69/Belle-whisper-large-v3-zh-punct-fasterwhisper"
        local_model = os.path.join(MODEL_DIR, "Belle-whisper-large-v3-zh-punct-fasterwhisper")
    else:
        model_name = load_key("whisper.model")
        possible_paths = [
            os.path.join(MODEL_DIR, f"faster-whisper-{model_name}"),
            os.path.join(MODEL_DIR, model_name),
            os.path.join(MODEL_DIR, f"Systran_faster-whisper-{model_name}"),
            os.path.join(MODEL_DIR, f"models--Systran--faster-whisper-{model_name}", "snapshots"),
        ]
        local_model = None
        for path in possible_paths:
            if os.path.exists(path):
                if "snapshots" in path:
                    snapshots = os.listdir(path)
                    if snapshots:
                        path = os.path.join(path, snapshots[0])
                if os.path.isfile(os.path.join(path, "model.bin")):
                    local_model = path
                    break
    
    model_path = local_model if local_model else model_name
    if local_model:
        rprint(f"[green]📥 Loading local model:[/green] {model_path}")
    else:
        rprint(f"[green]📥 Using model from HuggingFace:[/green] {model_name}")
    
    return model_path, model_name


# ============================================================================
# Audio Loading
# ============================================================================

def load_audio_segment(audio_file: str, start: float, end: float):
    """Load audio segment from file."""
    full_audio = whisperx.load_audio(audio_file)
    start_sample = int(start * 16000)
    end_sample = min(int(end * 16000), len(full_audio))
    return full_audio[start_sample:end_sample]


# ============================================================================
# WhisperX Alignment
# ============================================================================

def align_transcription(result: dict, audio_segment, device: str, language: str):
    """Align transcription with WhisperX for word-level timestamps."""
    align_start_time = time.time()
    model_cache_dir = os.path.abspath(MODEL_DIR)
    
    try:
        os.environ["HF_HUB_OFFLINE"] = "1"
        model_a, metadata = whisperx.load_align_model(
            language_code=language, device=device, model_dir=model_cache_dir
        )
        rprint("[green]✓ Alignment model loaded[/green]")
    except Exception:
        os.environ.pop("HF_HUB_OFFLINE", None)
        model_a, metadata = whisperx.load_align_model(
            language_code=language, device=device, model_dir=model_cache_dir
        )
    finally:
        os.environ.pop("HF_HUB_OFFLINE", None)
    
    aligned_result = whisperx.align(
        result["segments"], model_a, metadata, audio_segment, device,
        return_char_alignments=False,
    )
    
    del model_a
    torch.cuda.empty_cache()
    rprint(f"[cyan]⏱️ Alignment:[/cyan] {time.time() - align_start_time:.2f}s")
    
    return aligned_result


# ============================================================================
# Speaker Diarization
# ============================================================================

def run_speaker_diarization(result: dict, audio_segment, device: str):
    """Run speaker diarization on transcription result."""
    if not load_key("speaker_diarization"):
        return result
    
    hf_token = load_key("hf_token")
    if not hf_token or hf_token == "hf_xxx":
        rprint("[yellow]⚠️ Speaker diarization enabled but no valid hf_token[/yellow]")
        return result
    
    try:
        diarize_start_time = time.time()
        rprint("[cyan]🎭 Starting speaker diarization...[/cyan]")
        
        hf_mirror = load_key("hf_mirror")
        if hf_mirror:
            os.environ["HF_ENDPOINT"] = hf_mirror
        
        from pyannote.audio import Pipeline
        import pandas as pd
        
        diarize_model = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1", token=hf_token
        )
        diarize_model = diarize_model.to(torch.device(device))
        
        waveform = torch.from_numpy(audio_segment).unsqueeze(0)
        audio_dict = {"waveform": waveform, "sample_rate": 16000}
        
        # Get min/max speakers from config
        min_speakers = load_key("diarization.min_speakers")
        max_speakers = load_key("diarization.max_speakers")
        
        diarize_kwargs = {}
        if min_speakers:
            diarize_kwargs["min_speakers"] = min_speakers
        if max_speakers:
            diarize_kwargs["max_speakers"] = max_speakers
        
        diarize_result = diarize_model(audio_dict, **diarize_kwargs) if diarize_kwargs else diarize_model(audio_dict)
        
        diarization = diarize_result.speaker_diarization if hasattr(diarize_result, "speaker_diarization") else diarize_result
        
        diarize_df = pd.DataFrame(
            diarization.itertracks(yield_label=True),
            columns=["segment", "label", "speaker"],
        )
        diarize_df["start"] = diarize_df["segment"].apply(lambda x: x.start)
        diarize_df["end"] = diarize_df["segment"].apply(lambda x: x.end)
        
        result = whisperx.assign_word_speakers(diarize_df, result)

        # Fill missing segment-level speakers if assign_word_speakers didn't label all segments
        for segment in result.get("segments", []):
            if segment.get("speaker"):
                continue
            seg_start = segment.get("start")
            seg_end = segment.get("end")
            if seg_start is None or seg_end is None:
                continue
            overlaps = {}
            for _, row in diarize_df.iterrows():
                overlap_start = max(seg_start, row["start"])
                overlap_end = min(seg_end, row["end"])
                overlap = max(0.0, overlap_end - overlap_start)
                if overlap > 0:
                    overlaps[row["speaker"]] = overlaps.get(row["speaker"], 0.0) + overlap
            if overlaps:
                segment["speaker"] = max(overlaps.items(), key=lambda item: item[1])[0]
        
        if load_key("diarization.auto_generate_samples"):
            samples_dir = load_key("diarization.samples_dir") or "speaker_samples"
            existing_files = [
                f for f in os.listdir(samples_dir)
                if os.path.isfile(os.path.join(samples_dir, f))
            ] if os.path.exists(samples_dir) else []
            if not existing_files:
                from core.asr_backend.speaker_identification import generate_speaker_samples
                generate_speaker_samples(
                    diarization,
                    audio_segment,
                    sample_rate=16000,
                    output_dir=samples_dir,
                    samples_per_speaker=load_key("diarization.samples_per_speaker") or 2,
                    min_duration=load_key("diarization.sample_min_duration") or 1.5,
                    max_duration=load_key("diarization.sample_max_duration") or 8.0,
                )
        rprint(f"[cyan]⏱️ Diarization:[/cyan] {time.time() - diarize_start_time:.2f}s")
        
        speakers = set(seg.get("speaker") for seg in result.get("segments", []) if "speaker" in seg)
        rprint(f"[green]✓ {len(speakers)} speakers detected[/green]")
        
        # Speaker identification (optional)
        if load_key("diarization.speaker_identification"):
            try:
                from core.asr_backend.speaker_identification import identify_speakers_in_result
                threshold = load_key("diarization.identification_threshold") or 0.5
                result = identify_speakers_in_result(
                    result, diarization, audio_segment,
                    device=device, hf_token=hf_token, threshold=threshold
                )
            except Exception as e:
                rprint(f"[yellow]⚠️ Speaker identification failed: {e}[/yellow]")
        
        del diarize_model
        torch.cuda.empty_cache()
        
    except Exception as e:
        import traceback
        rprint(f"[yellow]⚠️ Speaker diarization failed: {e}[/yellow]")
        rprint(f"[yellow]{traceback.format_exc()}[/yellow]")
    
    return result


# ============================================================================
# Timestamp Adjustment
# ============================================================================

def adjust_timestamps(result: dict, offset: float):
    """Adjust all timestamps in result by offset."""
    for segment in result["segments"]:
        segment["start"] += offset
        segment["end"] += offset
        for word in segment.get("words", []):
            if "start" in word:
                word["start"] += offset
            if "end" in word:
                word["end"] += offset
    return result


# ============================================================================
# HuggingFace Mirror Check
# ============================================================================

@except_handler("failed to check hf mirror", default_return=None)
def check_hf_mirror():
    """Check and return fastest HuggingFace mirror."""
    existing_endpoint = os.environ.get("HF_ENDPOINT", "")
    if existing_endpoint:
        rprint(f"[cyan]🚀 Using pre-configured mirror:[/cyan] {existing_endpoint}")
        return existing_endpoint

    config_mirror = load_key("hf_mirror")
    if config_mirror:
        rprint(f"[cyan]🚀 Using config mirror:[/cyan] {config_mirror}")
        return config_mirror

    mirrors = {"Official": "huggingface.co", "Mirror": "hf-mirror.com"}
    default_mirror = "https://hf-mirror.com"
    fastest_url = default_mirror
    best_time = float("inf")
    
    rprint("[cyan]🔍 Checking HuggingFace mirrors...[/cyan]")
    for name, domain in mirrors.items():
        if os.name == "nt":
            cmd = ["ping", "-n", "1", "-w", "3000", domain]
        else:
            cmd = ["ping", "-c", "1", "-W", "3", domain]
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        response_time = time.time() - start
        if result.returncode == 0:
            if response_time < best_time:
                best_time = response_time
                fastest_url = f"https://{domain}"
            rprint(f"[green]✓ {name}:[/green] {response_time:.2f}s")
    
    if best_time == float("inf"):
        rprint(f"[yellow]⚠️ All mirrors failed, using default: {default_mirror}[/yellow]")
        fastest_url = default_mirror
    
    rprint(f"[cyan]🚀 Selected mirror:[/cyan] {fastest_url} ({best_time:.2f}s)")
    return fastest_url

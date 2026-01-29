import os
import warnings
import time
import subprocess
import torch
import whisperx
import librosa
from rich import print as rprint
from core.utils import *
from core.asr_backend._common import select_vad_parameters, run_speaker_diarization

warnings.filterwarnings("ignore")
MODEL_DIR = load_key("model_dir")


@except_handler("failed to check hf mirror", default_return=None)
def check_hf_mirror():
    # Check if HF_ENDPOINT is already set (e.g., by backend or environment)
    existing_endpoint = os.environ.get('HF_ENDPOINT', '')
    if existing_endpoint:
        rprint(f"[cyan]🚀 Using pre-configured mirror:[/cyan] {existing_endpoint}")
        return existing_endpoint
    
    # Check config file for hf_mirror setting
    config_mirror = load_key("hf_mirror")
    if config_mirror:
        rprint(f"[cyan]🚀 Using config mirror:[/cyan] {config_mirror}")
        return config_mirror
    
    # Auto-detect fastest mirror
    mirrors = {'Official': 'huggingface.co', 'Mirror': 'hf-mirror.com'}
    default_mirror = "https://hf-mirror.com"  # Default fallback
    fastest_url = default_mirror
    best_time = float('inf')
    rprint("[cyan]🔍 Checking HuggingFace mirrors...[/cyan]")
    for name, domain in mirrors.items():
        if os.name == 'nt':
            cmd = ['ping', '-n', '1', '-w', '3000', domain]
        else:
            cmd = ['ping', '-c', '1', '-W', '3', domain]
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        response_time = time.time() - start
        if result.returncode == 0:
            if response_time < best_time:
                best_time = response_time
                fastest_url = f"https://{domain}"
            rprint(f"[green]✓ {name}:[/green] {response_time:.2f}s")
    if best_time == float('inf'):
        rprint(f"[yellow]⚠️ All mirrors failed, using default: {default_mirror}[/yellow]")
        fastest_url = default_mirror
    rprint(f"[cyan]🚀 Selected mirror:[/cyan] {fastest_url} ({best_time:.2f}s)")
    return fastest_url

@except_handler("WhisperX processing error:")
def transcribe_audio(raw_audio_file, vocal_audio_file, start, end, WHISPER_LANGUAGE=None, device=None):
    # Note: hf-mirror.com cannot bypass xethub CDN for large files
    # If you need to download models, use a proxy with HF_ENDPOINT=https://huggingface.co
    # Or pre-download models to MODEL_DIR using: 
    #   curl -L -x http://127.0.0.1:PROXY_PORT -o model.bin "https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/model.bin"
    
    # Use passed parameters or load from config
    if WHISPER_LANGUAGE is None:
        WHISPER_LANGUAGE = load_key("whisper.language")
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    rprint(f"🚀 Starting WhisperX using device: {device} ...")
    
    if device == "cuda":
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        batch_size = 16 if gpu_mem > 8 else 2
        compute_type = "float16" if torch.cuda.is_bf16_supported() else "int8"
        rprint(f"[cyan]🎮 GPU memory:[/cyan] {gpu_mem:.2f} GB, [cyan]📦 Batch size:[/cyan] {batch_size}, [cyan]⚙️ Compute type:[/cyan] {compute_type}")
    else:
        batch_size = 1
        compute_type = "int8"
        rprint(f"[cyan]📦 Batch size:[/cyan] {batch_size}, [cyan]⚙️ Compute type:[/cyan] {compute_type}")
    rprint(f"[green]▶️ Starting WhisperX for segment {start:.2f}s to {end:.2f}s...[/green]")
    
    if WHISPER_LANGUAGE == 'zh':
        model_name = "Huan69/Belle-whisper-large-v3-zh-punct-fasterwhisper"
        local_model = os.path.join(MODEL_DIR, "Belle-whisper-large-v3-zh-punct-fasterwhisper")
    else:
        model_name = load_key("whisper.model")
        # Check multiple possible local model paths
        possible_paths = [
            os.path.join(MODEL_DIR, f"faster-whisper-{model_name}"),  # e.g., faster-whisper-large-v3
            os.path.join(MODEL_DIR, model_name),                      # e.g., large-v3
            os.path.join(MODEL_DIR, f"Systran_faster-whisper-{model_name}"),  # HF cache format
        ]
        local_model = None
        for path in possible_paths:
            if os.path.exists(path) and os.path.isfile(os.path.join(path, "model.bin")):
                local_model = path
                break
        
    if local_model:
        rprint(f"[green]📥 Loading local WHISPER model:[/green] {local_model} ...")
        model_name = local_model
    else:
        rprint(f"[green]📥 Using WHISPER model from HuggingFace:[/green] {model_name} ...")

    whisper_language = None if 'auto' in WHISPER_LANGUAGE else WHISPER_LANGUAGE

    def load_audio_segment(audio_file, start, end):
        audio, _ = librosa.load(audio_file, sr=16000, offset=start, duration=end - start, mono=True)
        return audio

    raw_audio_segment = load_audio_segment(raw_audio_file, start, end)
    vocal_audio_segment = load_audio_segment(vocal_audio_file, start, end)

    # -------------------------
    # 1. transcribe raw audio
    # -------------------------
    transcribe_start_time = time.time()
    rprint("[bold green]Note: You will see Progress if working correctly ↓[/bold green]")

    if whisper_language == "ja":
        from faster_whisper import WhisperModel as FwModel

        vad_params = select_vad_parameters(vocal_audio_file)
        rms_dbfs = vad_params.pop("_rms_dbfs", None)
        rprint(
            f"[cyan]🎤 VAD:[/cyan] RMS={rms_dbfs:.1f} dBFS, Silero threshold={vad_params['threshold']}"
        )

        asr_temperatures = load_key("whisper.temperatures") or [0]
        temperature = asr_temperatures[0] if isinstance(asr_temperatures, list) else asr_temperatures
        asr_initial_prompt = load_key("whisper.initial_prompt") or ""
        asr_no_speech_threshold = load_key("whisper.no_speech_threshold")
        asr_log_prob_threshold = load_key("whisper.log_prob_threshold")
        asr_compression_ratio_threshold = load_key("whisper.compression_ratio_threshold")

        fw_model = FwModel(model_name, device=device, compute_type=compute_type, download_root=MODEL_DIR)
        fw_segments, fw_info = fw_model.transcribe(
            raw_audio_segment,
            language=whisper_language,
            beam_size=load_key("whisper.beam_size") or 5,
            best_of=load_key("whisper.best_of") or 5,
            patience=load_key("whisper.patience") or 1.0,
            word_timestamps=False,
            vad_filter=True,
            vad_parameters=vad_params,
            initial_prompt=asr_initial_prompt,
            temperature=temperature,
            no_speech_threshold=asr_no_speech_threshold,
            log_prob_threshold=asr_log_prob_threshold,
            compression_ratio_threshold=asr_compression_ratio_threshold,
        )

        result = {
            "segments": [
                {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
                for seg in fw_segments
            ],
            "language": fw_info.language if hasattr(fw_info, "language") else whisper_language,
        }

        del fw_model
        torch.cuda.empty_cache()
    else:
        vad_params = select_vad_parameters(vocal_audio_file)
        rms_dbfs = vad_params.pop("_rms_dbfs", None)
        vad_onset = load_key("whisper.vad_onset") or vad_params["threshold"]
        vad_offset = load_key("whisper.vad_offset") or vad_params["threshold"]
        vad_options = {
            "vad_onset": vad_onset,
            "vad_offset": vad_offset,
            "min_duration_on": min(0.05, vad_params["min_speech_duration_ms"] / 1000.0),
            "min_duration_off": min(0.05, vad_params["min_silence_duration_ms"] / 1000.0),
        }
        rprint(
            f"[cyan]🎤 VAD:[/cyan] RMS={rms_dbfs:.1f} dBFS, onset/offset={vad_options['vad_onset']}, min_on/off={vad_options['min_duration_on']:.2f}s"
        )
        asr_temperatures = load_key("whisper.temperatures") or [0]
        asr_initial_prompt = load_key("whisper.initial_prompt") or ""
        asr_no_speech_threshold = load_key("whisper.no_speech_threshold")
        asr_log_prob_threshold = load_key("whisper.log_prob_threshold")
        asr_compression_ratio_threshold = load_key("whisper.compression_ratio_threshold")
        asr_options = {
            "temperatures": asr_temperatures,
            "initial_prompt": asr_initial_prompt,
            "no_speech_threshold": asr_no_speech_threshold,
            "log_prob_threshold": asr_log_prob_threshold,
            "compression_ratio_threshold": asr_compression_ratio_threshold,
        }
        rprint("[bold yellow] You can ignore warning of `Model was trained with torch 1.10.0+cu102, yours is 2.0.0+cu118...`[/bold yellow]")
        model = whisperx.load_model(
            model_name,
            device,
            compute_type=compute_type,
            language=whisper_language,
            vad_options=vad_options,
            asr_options=asr_options,
            download_root=MODEL_DIR,
        )

        result = model.transcribe(raw_audio_segment, batch_size=batch_size, print_progress=True)

        # Free GPU resources
        del model
        torch.cuda.empty_cache()

    transcribe_time = time.time() - transcribe_start_time
    rprint(f"[cyan]⏱️ time transcribe:[/cyan] {transcribe_time:.2f}s")

    # Save language
    update_key("whisper.language", result['language'])
    if result['language'] == 'zh' and WHISPER_LANGUAGE != 'zh':
        raise ValueError("Please specify the transcription language as zh and try again!")

    # -------------------------
    # 2. align by vocal audio
    # -------------------------
    align_start_time = time.time()
    # Align timestamps using vocal audio
    # Pass model_dir for local model cache
    model_cache_dir = os.path.abspath(MODEL_DIR)
    rprint(f"[cyan]🔍 Loading alignment model from:[/cyan] {model_cache_dir}")
    
    # Try to load alignment model - first attempt with local cache, then online
    try:
        # First try with offline mode to use local cache
        os.environ['HF_HUB_OFFLINE'] = '1'
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device, model_dir=model_cache_dir)
        rprint(f"[green]✓ Alignment model loaded from local cache[/green]")
    except Exception as e:
        rprint(f"[yellow]⚠️ Local cache miss, trying online download...[/yellow]")
        # Fallback to online download
        os.environ.pop('HF_HUB_OFFLINE', None)
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device, model_dir=model_cache_dir)
    finally:
        # Reset offline mode
        os.environ.pop('HF_HUB_OFFLINE', None)
    
    result = whisperx.align(result["segments"], model_a, metadata, vocal_audio_segment, device, return_char_alignments=False)
    align_time = time.time() - align_start_time
    rprint(f"[cyan]⏱️ time align:[/cyan] {align_time:.2f}s")

    # Speaker diarization (optional)
    result = run_speaker_diarization(result, raw_audio_segment, device)

    # Free GPU resources again
    torch.cuda.empty_cache()
    del model_a

    # Adjust timestamps
    for segment in result['segments']:
        segment['start'] += start
        segment['end'] += start
        for word in segment['words']:
            if 'start' in word:
                word['start'] += start
            if 'end' in word:
                word['end'] += start
    return result
import os
import torch
import torchaudio
import soundfile as sf
import numpy as np
from rich.console import Console
from rich import print as rprint
from demucs.pretrained import get_model
from demucs.audio import save_audio
from torch.cuda import is_available as is_cuda_available
from typing import Optional
from demucs.api import Separator
from demucs.apply import BagOfModels
import gc
from pydub import AudioSegment
from core.utils.models import *

class PreloadedSeparator(Separator):
    def __init__(self, model: BagOfModels, shifts: int = 1, overlap: float = 0.25,
                 split: bool = True, segment: Optional[int] = None, jobs: int = 0):
        self._model, self._audio_channels, self._samplerate = model, model.audio_channels, model.samplerate
        device = "cuda" if is_cuda_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        self.update_parameter(device=device, shifts=shifts, overlap=overlap, split=split,
                            segment=segment, jobs=jobs, progress=True, callback=None, callback_arg=None)
    
    def _load_audio(self, track):
        """Override _load_audio to use pydub instead of torchaudio (avoids torchcodec issues)"""
        # Convert mp3 to wav in memory using pydub
        audio_segment = AudioSegment.from_file(str(track))
        # Convert to model's sample rate
        audio_segment = audio_segment.set_frame_rate(self._samplerate)
        # Convert to stereo if needed (demucs expects stereo)
        if audio_segment.channels == 1:
            audio_segment = audio_segment.set_channels(2)
        # Get raw audio data as numpy array
        samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
        # Normalize to [-1, 1]
        samples = samples / (2 ** (audio_segment.sample_width * 8 - 1))
        # Reshape for stereo: (samples, channels) -> (channels, samples)
        samples = samples.reshape((-1, audio_segment.channels)).T
        # Convert to torch tensor
        wav = torch.from_numpy(samples)
        # Return only wav tensor (not tuple) - demucs expects just the tensor
        return wav

def demucs_audio():
    if os.path.exists(_VOCAL_AUDIO_FILE) and os.path.exists(_BACKGROUND_AUDIO_FILE):
        rprint(f"[yellow]⚠️ {_VOCAL_AUDIO_FILE} and {_BACKGROUND_AUDIO_FILE} already exist, skip Demucs processing.[/yellow]")
        return
    
    console = Console()
    os.makedirs(_AUDIO_DIR, exist_ok=True)
    
    console.print("🤖 Loading <htdemucs> model...")
    model = get_model('htdemucs')
    separator = PreloadedSeparator(model=model, shifts=1, overlap=0.25)
    
    console.print("🎵 Separating audio...")
    _, outputs = separator.separate_audio_file(_RAW_AUDIO_FILE)
    
    kwargs = {"samplerate": model.samplerate, "bitrate": 128, "preset": 2, 
             "clip": "rescale", "as_float": False, "bits_per_sample": 16}
    
    console.print("🎤 Saving vocals track...")
    save_audio(outputs['vocals'].cpu(), _VOCAL_AUDIO_FILE, **kwargs)
    
    console.print("🎹 Saving background music...")
    background = sum(audio for source, audio in outputs.items() if source != 'vocals')
    save_audio(background.cpu(), _BACKGROUND_AUDIO_FILE, **kwargs)
    
    # Clean up memory
    del outputs, background, model, separator
    gc.collect()
    
    console.print("[green]✨ Audio separation completed![/green]")

if __name__ == "__main__":
    demucs_audio()

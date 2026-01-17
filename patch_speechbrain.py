"""Patch speechbrain for torchaudio 2.9+ compatibility"""
import os

path = r'D:\conda_data\envs\videolingo\lib\site-packages\speechbrain\utils\torch_audio_backend.py'

new_content = '''"\"\"Library for checking the torchaudio backend.

Authors
-------
 * Mirco Ravanelli 2021
 * Adel Moumen 2025
\"\"\"

import platform
from typing import Optional

import torchaudio

from speechbrain.utils.logger import get_logger

logger = get_logger(__name__)


def try_parse_torchaudio_major_version() -> Optional[int]:
    \"\"\"Tries parsing the torchaudio major version.

    Returns
    -------
    The parsed major version, otherwise ``None``.
    \"\"\"
    if not hasattr(torchaudio, "__version__"):
        return None

    version_split = torchaudio.__version__.split(".")

    if len(version_split) <= 2:
        return None

    try:
        major_version = int(version_split[0])
        minor_version = int(version_split[1])
    except Exception:
        return None

    return major_version, minor_version


def check_torchaudio_backend():
    \"\"\"Checks the torchaudio backend and sets it to soundfile if
    windows is detected.
    
    Modified to support torchaudio >= 2.9 where list_audio_backends() was removed.
    \"\"\"
    version_info = try_parse_torchaudio_major_version()
    
    if version_info is None:
        logger.warning(
            "Failed to detect torchaudio major version; unsure how to check your setup."
        )
        return
    
    torchaudio_major, torchaudio_minor = version_info
    
    # For torchaudio >= 2.9, the list_audio_backends() function was removed
    if torchaudio_major >= 2 and torchaudio_minor >= 9:
        logger.info(f"Using torchaudio {torchaudio.__version__} with automatic backend handling.")
        return
    
    if torchaudio_major >= 2 and torchaudio_minor >= 1:
        if hasattr(torchaudio, 'list_audio_backends'):
            available_backends = torchaudio.list_audio_backends()
            if len(available_backends) == 0:
                logger.warning(
                    "SpeechBrain could not find any working torchaudio backend."
                )
        return
    
    logger.warning(
        "This version of torchaudio is old. Update to >=2.1.0."
    )
    current_system = platform.system()
    if current_system == "Windows" and hasattr(torchaudio, 'set_audio_backend'):
        logger.warning('Switched audio backend to "soundfile" for Windows.')
        torchaudio.set_audio_backend("soundfile")


def validate_backend(backend):
    \"\"\"Validates the specified audio backend.\"\"\"
    allowed_backends = [None, "ffmpeg", "sox", "soundfile"]
    if backend not in allowed_backends:
        available_info = ""
        if hasattr(torchaudio, 'list_audio_backends'):
            available_info = f" Available: {torchaudio.list_audio_backends()}"
        raise ValueError(f"backend must be one of {allowed_backends}.{available_info}")
'''

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Successfully patched speechbrain torch_audio_backend.py for torchaudio 2.9+ compatibility')

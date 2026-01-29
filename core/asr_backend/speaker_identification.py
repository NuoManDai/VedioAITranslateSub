"""
Speaker identification using voice fingerprinting.

This module provides functionality to identify speakers by matching their voice
against pre-recorded reference samples. It uses pyannote's speaker embedding
model to extract voice features and cosine similarity for matching.

Usage:
1. Create a `speaker_samples/` directory in your project
2. Add WAV/MP3 files named after each speaker (e.g., "角色A.wav", "角色B.wav")
3. Enable speaker_identification in config.yaml
4. The system will match detected speakers to your reference samples
"""

import os
import re
import torch
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rich import print as rprint
from core.utils import load_key

# Speaker samples directory
SPEAKER_SAMPLES_DIR = "speaker_samples"
DEFAULT_QDRANT_COLLECTION = "speaker_embeddings"


def generate_speaker_samples(
    diarization_result,
    raw_audio: np.ndarray,
    sample_rate: int = 16000,
    output_dir: str = SPEAKER_SAMPLES_DIR,
    samples_per_speaker: int = 2,
    min_duration: float = 1.5,
    max_duration: float = 8.0,
) -> List[str]:
    """Generate speaker sample clips from diarization result."""
    import pandas as pd
    import soundfile as sf

    os.makedirs(output_dir, exist_ok=True)

    diarize_df = pd.DataFrame(
        diarization_result.itertracks(yield_label=True),
        columns=["segment", "label", "speaker"],
    )
    diarize_df["start"] = diarize_df["segment"].apply(lambda x: x.start)
    diarize_df["end"] = diarize_df["segment"].apply(lambda x: x.end)
    diarize_df["duration"] = diarize_df["end"] - diarize_df["start"]

    saved_files: List[str] = []
    for speaker_label, group in diarize_df.groupby("speaker"):
        candidates = group[group["duration"] >= min_duration].sort_values(
            "duration", ascending=False
        )
        if candidates.empty:
            continue
        for idx, row in enumerate(candidates.head(samples_per_speaker).itertuples()):
            start = float(row.start)
            end = float(row.end)
            clip_end = min(end, start + max_duration)
            start_sample = int(start * sample_rate)
            end_sample = int(clip_end * sample_rate)
            if end_sample <= start_sample or end_sample > len(raw_audio):
                continue
            clip = raw_audio[start_sample:end_sample]
            filename = f"{speaker_label}_{idx + 1}.wav"
            file_path = os.path.join(output_dir, filename)
            sf.write(file_path, clip, sample_rate)
            saved_files.append(file_path)

    if saved_files:
        rprint(f"[green]Auto-generated {len(saved_files)} speaker samples[/green]")
    return saved_files


def get_qdrant_client():
    """Get Qdrant client if configured."""
    qdrant_enabled = load_key("speaker_vector_db.enabled")
    qdrant_url = load_key("speaker_vector_db.url")
    if not qdrant_enabled or not qdrant_url:
        return None, None
    try:
        from qdrant_client import QdrantClient
        collection = load_key("speaker_vector_db.collection") or DEFAULT_QDRANT_COLLECTION
        return QdrantClient(url=qdrant_url), collection
    except Exception as exc:
        rprint(f"[yellow]⚠️ Qdrant client init failed: {exc}[/yellow]")
        return None, None


def ensure_qdrant_collection(client, collection: str, vector_size: int):
    """Ensure Qdrant collection exists with cosine distance."""
    from qdrant_client.http import models as qdrant_models
    try:
        client.get_collection(collection)
        return
    except Exception:
        pass
    client.create_collection(
        collection_name=collection,
        vectors_config=qdrant_models.VectorParams(
            size=vector_size,
            distance=qdrant_models.Distance.COSINE,
        ),
    )


def upsert_qdrant_embedding(client, collection: str, speaker_name: str, embedding: np.ndarray):
    """Upsert speaker embedding into Qdrant."""
    from qdrant_client.http import models as qdrant_models
    from uuid import uuid5, NAMESPACE_DNS

    vector = embedding.flatten().tolist()
    point_id = uuid5(NAMESPACE_DNS, speaker_name)
    point = qdrant_models.PointStruct(
        id=str(point_id),
        vector=vector,
        payload={"speaker": speaker_name},
    )
    client.upsert(collection_name=collection, points=[point])


def query_qdrant_embedding(
    client,
    collection: str,
    embedding: np.ndarray,
    top_k: int = 5,
) -> Tuple[Optional[str], float]:
    """Query Qdrant for best matching speaker."""
    vector = embedding.flatten().tolist()
    results = []

    if hasattr(client, "search"):
        results = client.search(collection_name=collection, query_vector=vector, limit=top_k)
    elif hasattr(client, "query_points"):
        response = client.query_points(collection_name=collection, query=vector, limit=top_k)
        results = response.points if hasattr(response, "points") else []

    if not results:
        return None, 0.0

    speaker_scores: Dict[str, List[float]] = {}
    for item in results:
        payload = item.payload if hasattr(item, "payload") else None
        score = item.score if hasattr(item, "score") else 0.0
        speaker = payload.get("speaker") if payload else None
        if speaker:
            speaker_scores.setdefault(speaker, []).append(float(score))

    if not speaker_scores:
        return None, 0.0

    best_speaker = None
    best_score = 0.0
    for speaker, scores in speaker_scores.items():
        avg_score = float(np.mean(scores))
        if avg_score > best_score:
            best_score = avg_score
            best_speaker = speaker

    return best_speaker, best_score


def load_speaker_embedding_model(device: str = "cuda", hf_token: str = None):
    """Load the pyannote speaker embedding model."""
    from pyannote.audio import Model, Inference
    
    # Use wespeaker-voxceleb-resnet34-LM for speaker embeddings
    model = Model.from_pretrained(
        "pyannote/wespeaker-voxceleb-resnet34-LM",
        use_auth_token=hf_token
    )
    inference = Inference(model, window="whole")
    inference.to(torch.device(device))
    
    return inference


def extract_embedding(inference, audio_path: str) -> np.ndarray:
    """Extract speaker embedding from an audio file."""
    import whisperx
    
    # Use whisperx to load audio (more reliable than pyannote's decoder on Windows)
    audio = whisperx.load_audio(audio_path)
    waveform = torch.from_numpy(audio).unsqueeze(0)
    audio_dict = {"waveform": waveform, "sample_rate": 16000}
    
    embedding = inference(audio_dict)
    return embedding


def extract_embedding_from_waveform(inference, waveform: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
    """Extract speaker embedding from a waveform array."""
    # Create a temporary dict format for pyannote
    audio_dict = {
        "waveform": torch.from_numpy(waveform).unsqueeze(0),
        "sample_rate": sample_rate
    }
    embedding = inference(audio_dict)
    return embedding


def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings."""
    emb1 = emb1.flatten()
    emb2 = emb2.flatten()
    return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))


def _normalize_speaker_name(name: str) -> str:
    """Normalize speaker name by stripping trailing numeric suffix."""
    match = re.match(r"^(.*?)(?:_\d+)$", name)
    return match.group(1) if match else name


def load_reference_embeddings(
    inference,
    samples_dir: str = SPEAKER_SAMPLES_DIR,
) -> Tuple[Dict[str, List[np.ndarray]], Optional[object], Optional[str]]:
    """
    Load and compute embeddings for all reference speaker samples.
    
    Args:
        inference: The speaker embedding inference model
        samples_dir: Directory containing speaker sample audio files
        
    Returns:
        Dictionary mapping speaker names to their embeddings
    """
    reference_embeddings: Dict[str, List[np.ndarray]] = {}
    samples_path = Path(samples_dir)

    qdrant_client, qdrant_collection = get_qdrant_client()
    
    if not samples_path.exists():
        rprint(f"[yellow]Speaker samples directory not found: {samples_dir}[/yellow]")
        return reference_embeddings
    
    # Supported audio formats
    audio_extensions = {'.wav', '.mp3', '.flac', '.ogg', '.m4a'}
    
    for audio_file in samples_path.iterdir():
        if audio_file.suffix.lower() in audio_extensions:
            raw_name = audio_file.stem
            speaker_name = _normalize_speaker_name(raw_name)
            try:
                embedding = extract_embedding(inference, str(audio_file))
                reference_embeddings.setdefault(speaker_name, []).append(embedding)
                rprint(f"[green]Loaded reference: {speaker_name} ({raw_name})[/green]")
            except Exception as e:
                rprint(f"[yellow]Failed to load {audio_file}: {e}[/yellow]")

    if qdrant_client and reference_embeddings:
        try:
            vector_size = next(iter(reference_embeddings.values()))[0].flatten().shape[0]
            ensure_qdrant_collection(qdrant_client, qdrant_collection, vector_size)
            upsert_count = 0
            for speaker_name, embeddings in reference_embeddings.items():
                for embedding in embeddings:
                    upsert_qdrant_embedding(qdrant_client, qdrant_collection, speaker_name, embedding)
                    upsert_count += 1
            rprint(f"[green]Qdrant upserted {upsert_count} speaker embeddings[/green]")
        except Exception as e:
            rprint(f"[yellow]Qdrant upsert failed: {e}[/yellow]")

    return reference_embeddings, qdrant_client, qdrant_collection


def identify_speaker(
    embedding: np.ndarray,
    reference_embeddings: Dict[str, List[np.ndarray]],
    threshold: float = 0.5,
) -> Tuple[Optional[str], float]:
    """
    Identify a speaker by comparing their embedding to reference embeddings.
    
    Args:
        embedding: The speaker embedding to identify
        reference_embeddings: Dictionary of reference speaker embeddings
        threshold: Minimum similarity score to consider a match
        
    Returns:
        Tuple of (speaker_name, similarity_score) or (None, 0.0) if no match
    """
    if not reference_embeddings:
        return None, 0.0
    
    best_match = None
    best_score = 0.0
    
    for speaker_name, ref_embeddings in reference_embeddings.items():
        for ref_embedding in ref_embeddings:
            similarity = cosine_similarity(embedding, ref_embedding)
            if similarity > best_score:
                best_score = similarity
                best_match = speaker_name
    
    if best_score >= threshold:
        return best_match, best_score
    else:
        return None, best_score


def map_speakers_to_identities(
    diarization_result,
    raw_audio: np.ndarray,
    inference,
    reference_embeddings: Dict[str, List[np.ndarray]],
    sample_rate: int = 16000,
    threshold: float = 0.5,
    qdrant_client=None,
    qdrant_collection: Optional[str] = None,
    segment_min_duration: float = 1.0,
    segment_top_n: int = 3,
    qdrant_top_k: int = 5,
) -> Dict[str, str]:
    """
    Map anonymous speaker labels (SPEAKER_00, SPEAKER_01) to identified names.
    
    This function extracts embeddings from each detected speaker's audio segments
    and matches them against reference samples.
    
    Args:
        diarization_result: pyannote diarization Annotation object
        raw_audio: The full audio waveform as numpy array
        inference: Speaker embedding inference model
        reference_embeddings: Dictionary of reference speaker embeddings
        sample_rate: Audio sample rate
        threshold: Minimum similarity for a match
        
    Returns:
        Dictionary mapping anonymous labels to identified names
    """
    import pandas as pd
    
    # Convert diarization to DataFrame
    diarize_df = pd.DataFrame(
        diarization_result.itertracks(yield_label=True),
        columns=["segment", "label", "speaker"]
    )
    diarize_df["start"] = diarize_df["segment"].apply(lambda x: x.start)
    diarize_df["end"] = diarize_df["segment"].apply(lambda x: x.end)
    
    # Get unique speakers
    unique_speakers = diarize_df["speaker"].unique()
    speaker_mapping = {}
    
    for speaker_label in unique_speakers:
        # Get all segments for this speaker
        speaker_segments = diarize_df[diarize_df["speaker"] == speaker_label]
        
        # Collect audio from this speaker's segments (up to 30 seconds)
        segments_sorted = speaker_segments.copy()
        segments_sorted["duration"] = segments_sorted["end"] - segments_sorted["start"]
        segments_sorted = segments_sorted[segments_sorted["duration"] >= segment_min_duration]
        segments_sorted = segments_sorted.sort_values("duration", ascending=False)

        embeddings: List[np.ndarray] = []
        for _, row in segments_sorted.head(segment_top_n).iterrows():
            start_sample = int(row["start"] * sample_rate)
            end_sample = int(row["end"] * sample_rate)
            if end_sample <= len(raw_audio) and end_sample > start_sample:
                chunk = raw_audio[start_sample:end_sample]
                try:
                    emb = extract_embedding_from_waveform(inference, chunk, sample_rate)
                    embeddings.append(emb)
                except Exception as exc:
                    rprint(f"[yellow]Failed embedding chunk for {speaker_label}: {exc}[/yellow]")

        if embeddings:
            embedding = np.mean(np.stack(embeddings, axis=0), axis=0)
            try:
                if qdrant_client and qdrant_collection:
                    identified_name, score = query_qdrant_embedding(
                        qdrant_client, qdrant_collection, embedding, top_k=qdrant_top_k
                    )
                else:
                    identified_name, score = identify_speaker(
                        embedding, reference_embeddings, threshold
                    )

                if identified_name and score >= threshold:
                    speaker_mapping[speaker_label] = identified_name
                    rprint(f"[green]Matched {speaker_label} -> {identified_name} (score: {score:.3f})[/green]")
                else:
                    speaker_mapping[speaker_label] = speaker_label
                    rprint(f"[yellow]No match for {speaker_label} (best score: {score:.3f})[/yellow]")
            except Exception as e:
                rprint(f"[yellow]Failed to identify {speaker_label}: {e}[/yellow]")
                speaker_mapping[speaker_label] = speaker_label
        else:
            speaker_mapping[speaker_label] = speaker_label
    
    return speaker_mapping


def apply_speaker_mapping(
    result: dict,
    speaker_mapping: Dict[str, str]
) -> dict:
    """
    Apply speaker name mapping to transcription result.
    
    Args:
        result: WhisperX transcription result with speaker labels
        speaker_mapping: Mapping from anonymous labels to identified names
        
    Returns:
        Updated result with mapped speaker names
    """
    for segment in result.get("segments", []):
        if "speaker" in segment:
            segment["speaker"] = speaker_mapping.get(segment["speaker"], segment["speaker"])
        for word in segment.get("words", []):
            if "speaker" in word:
                word["speaker"] = speaker_mapping.get(word["speaker"], word["speaker"])
    
    return result


def identify_speakers_in_result(
    result: dict,
    diarization,
    raw_audio: np.ndarray,
    device: str = "cuda",
    hf_token: str = None,
    samples_dir: str = SPEAKER_SAMPLES_DIR,
    threshold: float = 0.5
) -> dict:
    """
    Main function to identify speakers in a transcription result.
    
    Args:
        result: WhisperX transcription result
        diarization: pyannote diarization Annotation object
        raw_audio: The audio waveform
        device: Device to run on ("cuda" or "cpu")
        hf_token: HuggingFace token
        samples_dir: Directory containing speaker reference samples
        threshold: Minimum similarity score for matching
        
    Returns:
        Updated result with identified speaker names
    """
    samples_path = Path(samples_dir)
    
    # Check if samples directory exists and has files
    if not samples_path.exists():
        rprint(f"[yellow]No speaker samples directory found at: {samples_dir}[/yellow]")
        rprint("[yellow]Create this directory and add speaker audio samples to enable identification[/yellow]")
        return result
    
    audio_extensions = {'.wav', '.mp3', '.flac', '.ogg', '.m4a'}
    sample_files = [f for f in samples_path.iterdir() if f.suffix.lower() in audio_extensions]
    
    if not sample_files:
        rprint(f"[yellow]No audio files found in {samples_dir}[/yellow]")
        return result
    
    rprint(f"[cyan]Loading speaker embedding model...[/cyan]")
    
    try:
        # Load embedding model
        inference = load_speaker_embedding_model(device, hf_token)
        
        # Load reference embeddings
        rprint(f"[cyan]Loading {len(sample_files)} reference samples...[/cyan]")
        reference_embeddings, qdrant_client, qdrant_collection = load_reference_embeddings(
            inference, samples_dir
        )
        
        if not reference_embeddings and not qdrant_client:
            rprint("[yellow]No valid reference embeddings loaded[/yellow]")
            return result
        
        # Map speakers
        rprint("[cyan]Matching speakers to references...[/cyan]")
        speaker_mapping = map_speakers_to_identities(
            diarization,
            raw_audio,
            inference,
            reference_embeddings,
            threshold=threshold,
            qdrant_client=qdrant_client,
            qdrant_collection=qdrant_collection,
            segment_min_duration=load_key("diarization.identification_segment_min_duration") or 1.0,
            segment_top_n=load_key("diarization.identification_segment_top_n") or 3,
            qdrant_top_k=load_key("diarization.identification_top_k") or 5,
        )
        
        # Apply mapping
        result = apply_speaker_mapping(result, speaker_mapping)
        
        rprint(f"[green]Speaker identification complete: {len(speaker_mapping)} speakers mapped[/green]")
        
        # Cleanup
        del inference
        torch.cuda.empty_cache()
        
    except Exception as e:
        import traceback
        rprint(f"[yellow]Speaker identification failed: {e}[/yellow]")
        rprint(f"[yellow]{traceback.format_exc()}[/yellow]")
    
    return result

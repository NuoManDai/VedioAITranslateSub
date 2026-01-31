"""
使用 Silero VAD 的原生 Faster-Whisper 转写。
流程类似 PotPlayer/Faster-Whisper-XXL：
- Silero VAD 进行语音活动检测
- 句子级后处理
- 直接调用 faster-whisper 输出词级时间戳

注意：不要用 librosa 读音频！会导致识别错误。
faster-whisper 内部用 PyAV，能正确处理音频。
"""
import os
import re
import time
import torch
from faster_whisper import WhisperModel
from rich import print as rprint
from core.utils import *
from core.asr_backend._common import get_language_prompt, select_vad_parameters

MODEL_DIR = load_key("model_dir")

# -------------------------
# 句子边界规则（类似 Faster-Whisper-XXL --sentence）
# -------------------------
# 句末标点
SENTENCE_ENDINGS = re.compile(r'[.!?。！？]$')
# 句末省略号（允许切分）
ELLIPSIS_END = re.compile(r'\.{3}$|…$')
# 分句时忽略这些缩写
ABBREVIATIONS = {'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.', 'Sr.', 'Jr.', 'etc.', 'vs.'}


def split_into_sentences(segments, max_gap=0.5):
    """
    将分段后处理为更自然的句子，类似 Faster-Whisper-XXL 的 --sentence。
    
    参数：
        segments: 带词级时间戳的分段列表
        max_gap: 同一句内允许的最大词间隔（秒）
    
    返回：
        句子级分段列表
    """
    if not segments:
        return segments
    
    sentences = []
    current_sentence = None
    
    for seg in segments:
        if not seg.get('words'):
            # 没有词级时间戳，直接使用分段
            sentences.append(seg)
            continue
        
        for word_info in seg['words']:
            word = word_info['word'].strip()
            if not word:
                continue
            
            # 需要时开始新句子
            if current_sentence is None:
                current_sentence = {
                    'start': word_info['start'],
                    'end': word_info['end'],
                    'text': word,
                    'words': [word_info]
                }
            else:
                # 判断是否开始新句
                gap = word_info['start'] - current_sentence['end']
                prev_text = current_sentence['text']
                
                # 开启新句的条件：
                # 1. 词间隔很大
                # 2. 上一句以句末标点结束（且不是缩写）
                should_split = False
                
                if gap > max_gap:
                    should_split = True
                elif SENTENCE_ENDINGS.search(prev_text):
                    # 确保不是缩写
                    last_word = prev_text.split()[-1] if prev_text.split() else ''
                    if last_word not in ABBREVIATIONS:
                        # 省略号仅允许在分段边界切分
                        if not ELLIPSIS_END.search(prev_text):
                            should_split = True
                
                if should_split:
                    # 保存当前句
                    sentences.append(current_sentence)
                    # 开始新句
                    current_sentence = {
                        'start': word_info['start'],
                        'end': word_info['end'],
                        'text': word,
                        'words': [word_info]
                    }
                else:
                    # 继续当前句
                    current_sentence['end'] = word_info['end']
                    current_sentence['text'] += word
                    current_sentence['words'].append(word_info)
    
    # 追加最后一句
    if current_sentence is not None:
        sentences.append(current_sentence)
    
    return sentences


def get_local_model_path(model_name: str) -> str:
    """查找本地模型路径。"""
    possible_paths = [
        os.path.join(MODEL_DIR, f"faster-whisper-{model_name}"),
        os.path.join(MODEL_DIR, model_name),
        os.path.join(MODEL_DIR, f"Systran_faster-whisper-{model_name}"),
    ]
    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(os.path.join(path, "model.bin")):
            return path
    return None


@except_handler("Native Whisper processing error:")
def transcribe_audio_native(raw_audio_file, vocal_audio_file, start, end, WHISPER_LANGUAGE=None, device=None):
    """
    原生 Faster-Whisper 转写（不使用 WhisperX VAD）。
    
    特点：
    - 不做 pyannote VAD 预处理（减少漏段）
    - 直接调用 faster-whisper 转写
    - 输出词级时间戳
    - 效果接近 PotPlayer 的转写方式
    """
    # 使用传入参数或从配置读取
    if WHISPER_LANGUAGE is None:
        WHISPER_LANGUAGE = load_key("whisper.language")
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    rprint(f"🚀 Starting Native Faster-Whisper using device: {device} ...")
    
    # -------------------------
    # 计算设置
    # -------------------------
    if device == "cuda":
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        compute_type = "float16" if gpu_mem > 6 else "int8"
        rprint(f"[cyan]🎮 GPU memory:[/cyan] {gpu_mem:.2f} GB, [cyan]⚙️ Compute type:[/cyan] {compute_type}")
    else:
        compute_type = "int8"
        rprint(f"[cyan]⚙️ Compute type:[/cyan] {compute_type}")
    
    rprint(f"[green]▶️ Processing segment {start:.2f}s to {end:.2f}s...[/green]")
    
    # -------------------------
    # 加载模型
    # -------------------------
    if WHISPER_LANGUAGE == 'zh':
        model_name = "Huan69/Belle-whisper-large-v3-zh-punct-fasterwhisper"
        local_model = os.path.join(MODEL_DIR, "Belle-whisper-large-v3-zh-punct-fasterwhisper")
    else:
        model_name = load_key("whisper.model")
        local_model = get_local_model_path(model_name)
    
    if local_model and os.path.exists(local_model):
        rprint(f"[green]📥 Loading local model:[/green] {local_model}")
        model_path = local_model
    else:
        rprint(f"[green]📥 Loading model from HuggingFace:[/green] Systran/faster-whisper-{model_name}")
        model_path = f"Systran/faster-whisper-{model_name}"
    
    # 直接加载 Faster-Whisper 模型
    model = WhisperModel(
        model_path,
        device=device,
        compute_type=compute_type,
        download_root=MODEL_DIR
    )
    
    # -------------------------
    # 转写音频
    # -------------------------
    # 注意：直接传文件路径给 faster-whisper，不要用 librosa 读入！
    # librosa 重采样会导致识别错误（如“人物混行”而非“神仏根香”）
    # faster-whisper 内部使用 PyAV，能正确处理音频
    
    transcribe_start_time = time.time()
    
    # 读取高级配置
    beam_size = load_key("whisper.beam_size") or 5
    best_of = load_key("whisper.best_of") or 5
    patience = load_key("whisper.patience") or 1.0
    
    whisper_language = None if WHISPER_LANGUAGE == 'auto' else WHISPER_LANGUAGE
    
    rprint(f"[cyan]🔧 Settings:[/cyan] beam_size={beam_size}, best_of={best_of}, patience={patience}")
    
    # -------------------------
    # 语言初始提示词（类似 faster-whisper-xxl 自动提示）
    # 用于引导模型输出正确标点和汉字/汉字
    # -------------------------
    initial_prompt = get_language_prompt(whisper_language)
    
    if initial_prompt:
        rprint(f"[cyan]📝 Initial prompt:[/cyan] {initial_prompt}")
    
    # -------------------------
    # VAD 参数（基于 RMS 自动选择）
    # -------------------------
    vad_parameters = select_vad_parameters(vocal_audio_file)
    rms_dbfs = vad_parameters.pop("_rms_dbfs", None)
    rprint(
        f"[cyan]🎤 VAD:[/cyan] RMS={rms_dbfs:.1f} dBFS, threshold={vad_parameters['threshold']}"
    )
    
    # 使用词级时间戳 + Silero VAD 转写
    # 直接传文件路径，PyAV 会正确处理音频
    segments_iter, info = model.transcribe(
        vocal_audio_file,  # 直接传文件路径，不要用 librosa
        language=whisper_language,
        beam_size=beam_size,
        best_of=best_of,
        patience=patience,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=vad_parameters,
        initial_prompt=initial_prompt,
        condition_on_previous_text=True,  # 启用以获得更好标点
        no_speech_threshold=0.6,
        log_prob_threshold=-1.0,
    )
    
    # 转为列表并构建结果
    segments = []
    for seg in segments_iter:
        # 注意：使用文件路径时，时间戳已是绝对时间
        # 仅在需要时按 start/end 过滤
        if seg.start < start or seg.end > end:
            continue
            
        segment_data = {
            'start': seg.start,  # Already correct timestamps
            'end': seg.end,
            'text': seg.text.strip(),
            'words': []
        }
        
        # 添加词级时间戳
        if seg.words:
            for word in seg.words:
                if word.start < start or word.end > end:
                    continue
                segment_data['words'].append({
                    'word': word.word,
                    'start': word.start,
                    'end': word.end,
                    'probability': word.probability
                })
        
        segments.append(segment_data)
    
    transcribe_time = time.time() - transcribe_start_time
    rprint(f"[cyan]⏱️ Transcription time:[/cyan] {transcribe_time:.2f}s")
    rprint(f"[cyan]📝 Found {len(segments)} raw segments[/cyan]")
    
    # -------------------------
    # 句子级后处理（类似 --sentence）
    # 已关闭分句，直接使用原始分段
    # -------------------------
    sentences = segments
    rprint("[cyan]✂️ Sentence split disabled[/cyan]")
    
    # 更新检测到的语言
    detected_lang = info.language if hasattr(info, 'language') else WHISPER_LANGUAGE
    update_key("whisper.detected_language", detected_lang)
    
    # 释放 GPU 资源
    del model
    if device == "cuda":
        torch.cuda.empty_cache()
    
    return {'segments': sentences, 'language': detected_lang}

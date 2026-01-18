# Data Model: 字幕配音分离与日语支持优化

**Feature**: 002-dubbing-subtitle-separation  
**Date**: 2026-01-18

## 新增数据模型

### 1. LogEntry (日志条目)

**文件**: `backend/models/log.py`

```python
class LogEntry(BaseModel):
    """日志条目模型"""
    id: str                      # 唯一标识
    timestamp: datetime          # 时间戳
    level: str                   # 日志级别 (DEBUG, INFO, WARNING, ERROR)
    source: str                  # 来源 (backend, core, tts, asr)
    message: str                 # 日志消息
    details: Optional[dict]      # 额外详情
```

**用途**: 前端控制台面板展示实时日志

### 2. TTSConfig (TTS 配置)

**文件**: `backend/models/tts_config.py`

```python
class TTSConfig(BaseModel):
    """TTS 配置模型"""
    method: str                  # TTS 方法 (edge, openai, fish, sovits)
    voice: Optional[str]         # 语音选择
    speed: float = 1.0           # 语速
    pitch: float = 1.0           # 音调
    # 各方法特定配置
    openai_api_key: Optional[str]
    fish_api_key: Optional[str]
    sovits_api_url: Optional[str]
```

**用途**: TTS 服务配置管理

### 3. FileInfo (文件信息)

**文件**: `backend/api/routes/files.py` (内联定义)

```python
class FileInfo(BaseModel):
    """文件信息模型"""
    name: str                    # 文件名
    path: str                    # 相对路径
    size: int                    # 文件大小 (bytes)
    modified: datetime           # 修改时间
    type: str                    # 文件类型 (file, directory)
```

**用途**: 文件预览 API 返回

## 扩展数据模型

### 4. ProcessingStage (处理阶段) - 扩展

**文件**: `backend/models/stage.py`

**新增常量**:

```python
# 阶段输出文件映射
STAGE_OUTPUT_FILES = {
    'asr': [
        'output/log/cleaned_chunks.xlsx',
        'output/audio/raw.mp3',
        'output/audio/raw.wav',
        'output/audio/vocal.mp3',
        'output/audio/background.mp3'
    ],
    'split_nlp': ['output/log/split_by_nlp.txt'],
    'split_meaning': ['output/log/split_by_meaning.txt'],
    'summarize': ['output/log/terminology.json'],
    'translate': [
        'output/log/translation_results.xlsx',
        'output/log/translation_results_compare.xlsx'
    ],
    'split_sub': ['output/log/translation_results_for_subtitles.xlsx'],
    'gen_sub': [
        'output/src.srt',
        'output/trans.srt',
        'output/src_trans.srt',
        'output/trans_src.srt'
    ],
    'sub_into_vid': ['output/output_sub.mp4'],
    'audio_task': ['output/audio/sovits_tasks.xlsx'],
    'dub_chunks': ['output/audio/segs/'],
    'refer_audio': ['output/audio/refers/'],
    'gen_audio': ['output/audio/trans_vocal.mp3'],
    'merge_audio': ['output/audio/trans_vocal_mixed.mp3'],
    'dub_to_vid': ['output/output_dub.mp4'],
}

# 字幕处理阶段
SUBTITLE_STAGES = ['asr', 'split_nlp', 'split_meaning', 'summarize', 
                   'translate', 'split_sub', 'gen_sub', 'sub_into_vid']

# 配音处理阶段
DUBBING_STAGES = ['audio_task', 'dub_chunks', 'refer_audio', 
                  'gen_audio', 'merge_audio', 'dub_to_vid']
```

## 日语分句数据流

### 输入数据 (cleaned_chunks.xlsx)

```
| text | start  | end    |
|------|--------|--------|
| 今   | 0.500  | 0.520  |
| 回   | 0.520  | 0.540  |
| は   | 0.540  | 0.560  |
| ...  | ...    | ...    |
```

### 处理后输出 (split_by_nlp.txt)

```
今回は動画を作成します
そして翻訳もします
これはテストです
...
```

### 分句逻辑数据结构

```python
class SentenceChunk:
    """内部使用的句子块"""
    text: str           # 句子文本
    start: float        # 开始时间
    end: float          # 结束时间
    gap_before: float   # 与前一个 chunk 的时间间隔
```

## 清理操作数据

### 字幕清理范围

```python
SUBTITLE_CLEANUP_PATTERNS = [
    'output/log/*.txt',
    'output/log/*.xlsx',
    'output/log/*.json',
    'output/*.srt',
    'output/output_sub.mp4'
]
```

### 配音清理范围

```python
DUBBING_CLEANUP_PATTERNS = [
    'output/audio/segs/*',
    'output/audio/refers/*',
    'output/audio/trans_*.mp3',
    'output/output_dub.mp4'
]
```

## API 请求/响应模型

### CleanupRequest

```python
class CleanupRequest(BaseModel):
    confirm: bool = False  # 确认清理
```

### CleanupResponse

```python
class CleanupResponse(BaseModel):
    success: bool
    deleted_files: List[str]
    message: str
```

### FilePreviewResponse

```python
class FilePreviewResponse(BaseModel):
    path: str
    content: str
    type: str              # text, json, excel, srt
    total_lines: int
    truncated: bool        # 是否被截断
```

# Data Model: 前后端分离重构

**Feature**: 001-fastapi-react-refactor  
**Date**: 2026-01-17

## 实体定义

### Video

表示用户上传或下载的视频文件。

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| id | string | 是 | 视频唯一标识（UUID） |
| filename | string | 是 | 文件名 |
| filepath | string | 是 | 文件完整路径（相对于 output/） |
| source_type | enum | 是 | 来源类型：`upload` \| `youtube` |
| youtube_url | string | 否 | YouTube 原始链接（仅 youtube 类型） |
| status | enum | 是 | 状态：`uploading` \| `downloading` \| `ready` \| `processing` \| `completed` \| `error` |
| file_size | number | 否 | 文件大小（字节） |
| duration | number | 否 | 视频时长（秒） |
| created_at | datetime | 是 | 创建时间 |
| error_message | string | 否 | 错误信息（仅 error 状态） |

**状态转换图**:
```
uploading → ready → processing → completed
    ↓         ↓          ↓
   error    error      error

downloading → ready → processing → completed
     ↓          ↓          ↓
    error     error      error
```

### ProcessingJob

表示一个处理任务（字幕处理或配音处理）。

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| id | string | 是 | 任务唯一标识（UUID） |
| video_id | string | 是 | 关联的视频 ID |
| job_type | enum | 是 | 任务类型：`subtitle` \| `dubbing` |
| status | enum | 是 | 状态：`pending` \| `running` \| `completed` \| `failed` \| `cancelled` |
| current_stage | string | 否 | 当前处理阶段名称 |
| progress | number | 是 | 进度百分比 (0-100) |
| stages | ProcessingStage[] | 是 | 各阶段状态列表 |
| started_at | datetime | 否 | 开始时间 |
| completed_at | datetime | 否 | 完成时间 |
| error_message | string | 否 | 错误信息（仅 failed 状态） |

**字幕处理阶段** (job_type = `subtitle`):
1. `asr` - 语音识别 (WhisperX)
2. `split_nlp` - NLP 分句
3. `split_meaning` - 语义分割
4. `summarize` - 内容总结
5. `translate` - 翻译
6. `split_sub` - 字幕分割
7. `gen_sub` - 生成字幕
8. `merge_sub` - 合并字幕到视频

**配音处理阶段** (job_type = `dubbing`):
1. `audio_task` - 生成音频任务
2. `dub_chunks` - 生成配音片段
3. `refer_audio` - 提取参考音频
4. `gen_audio` - 生成配音
5. `merge_audio` - 合并音频
6. `dub_to_vid` - 配音合并到视频

### ProcessingStage

表示处理流程中的一个阶段。

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| name | string | 是 | 阶段名称 |
| display_name | string | 是 | 显示名称（用于 UI） |
| status | enum | 是 | 状态：`pending` \| `running` \| `completed` \| `failed` \| `skipped` |
| progress | number | 否 | 阶段内进度 (0-100) |
| started_at | datetime | 否 | 开始时间 |
| completed_at | datetime | 否 | 完成时间 |
| error_message | string | 否 | 错误信息 |

### Configuration

系统配置，映射到 `config.yaml` 文件。

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| display_language | string | 是 | 界面显示语言 |
| api | ApiConfig | 是 | LLM API 配置 |
| target_language | string | 是 | 翻译目标语言 |
| demucs | boolean | 是 | 是否启用人声分离 |
| whisper | WhisperConfig | 是 | Whisper 配置 |
| burn_subtitles | boolean | 是 | 是否烧录字幕 |
| tts_method | string | 是 | TTS 方法 |
| ... | ... | ... | 其他配置项 |

#### ApiConfig

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| key | string | 是 | API 密钥 |
| base_url | string | 是 | API 基础 URL |
| model | string | 是 | 模型名称 |
| llm_support_json | boolean | 是 | 是否支持 JSON 模式 |

#### WhisperConfig

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| model | string | 是 | 模型名称 |
| language | string | 是 | 识别语言 |
| runtime | string | 是 | 运行模式：local/cloud/elevenlabs |
| whisperX_302_api_key | string | 否 | 302.ai API 密钥 |
| elevenlabs_api_key | string | 否 | ElevenLabs API 密钥 |

## 关系图

```
┌─────────────┐     1:N     ┌─────────────────┐     1:N     ┌──────────────────┐
│    Video    │ ◄────────── │  ProcessingJob  │ ◄────────── │ ProcessingStage  │
└─────────────┘             └─────────────────┘             └──────────────────┘
       │                            │
       │                            │
       └────────── 1:1 ─────────────┘
                   (当前正在处理的视频)

┌─────────────────┐
│  Configuration  │  (单例，对应 config.yaml)
└─────────────────┘
```

## 存储策略

| 实体 | 存储位置 | 持久化方式 |
|------|----------|------------|
| Video | 内存 + output/ 目录 | 文件系统检测恢复 |
| ProcessingJob | 内存 | 服务重启后通过 output/ 状态重建 |
| ProcessingStage | 内存（嵌入 Job） | 随 Job 一起 |
| Configuration | config.yaml | YAML 文件读写 |

## TypeScript 类型定义

```typescript
// types/index.ts

export type VideoSourceType = 'upload' | 'youtube';
export type VideoStatus = 'uploading' | 'downloading' | 'ready' | 'processing' | 'completed' | 'error';
export type JobType = 'subtitle' | 'dubbing';
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

export interface Video {
  id: string;
  filename: string;
  filepath: string;
  sourceType: VideoSourceType;
  youtubeUrl?: string;
  status: VideoStatus;
  fileSize?: number;
  duration?: number;
  createdAt: string;
  errorMessage?: string;
}

export interface ProcessingStage {
  name: string;
  displayName: string;
  status: StageStatus;
  progress?: number;
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
}

export interface ProcessingJob {
  id: string;
  videoId: string;
  jobType: JobType;
  status: JobStatus;
  currentStage?: string;
  progress: number;
  stages: ProcessingStage[];
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
}

export interface ApiConfig {
  key: string;
  baseUrl: string;
  model: string;
  llmSupportJson: boolean;
}

export interface WhisperConfig {
  model: string;
  language: string;
  runtime: 'local' | 'cloud' | 'elevenlabs';
  whisperX302ApiKey?: string;
  elevenlabsApiKey?: string;
}

export interface Configuration {
  displayLanguage: string;
  api: ApiConfig;
  targetLanguage: string;
  demucs: boolean;
  whisper: WhisperConfig;
  burnSubtitles: boolean;
  ttsMethod: string;
  // ... 其他配置
}
```

## Python Pydantic 模型

```python
# models/video.py
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class Video(BaseModel):
    id: str
    filename: str
    filepath: str
    source_type: Literal['upload', 'youtube']
    youtube_url: Optional[str] = None
    status: Literal['uploading', 'downloading', 'ready', 'processing', 'completed', 'error']
    file_size: Optional[int] = None
    duration: Optional[float] = None
    created_at: datetime
    error_message: Optional[str] = None

# models/job.py
class ProcessingStage(BaseModel):
    name: str
    display_name: str
    status: Literal['pending', 'running', 'completed', 'failed', 'skipped']
    progress: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class ProcessingJob(BaseModel):
    id: str
    video_id: str
    job_type: Literal['subtitle', 'dubbing']
    status: Literal['pending', 'running', 'completed', 'failed', 'cancelled']
    current_stage: Optional[str] = None
    progress: float = 0
    stages: list[ProcessingStage] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
```

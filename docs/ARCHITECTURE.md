# VideoLingo 字幕处理架构文档

## 📋 目录

1. [项目概述](#项目概述)
2. [系统架构图](#系统架构图)
3. [后端编排层](#后端编排层)
4. [前端处理面板](#前端处理面板)
5. [处理流程详解](#处理流程详解)
6. [UML 图](#uml-图)
7. [模型与技术选型](#模型与技术选型)
8. [数据流图](#数据流图)

---

## 项目概述

VideoLingo 是一个视频本地化处理系统，支持视频下载、语音识别（ASR）、字幕分割、翻译、字幕生成与合并等全流程自动化处理。本文档聚焦于**字幕处理流水线**的架构设计。

### 核心功能模块

| 模块编号 | 文件名 | 功能描述 |
|---------|--------|---------|
| Step 1  | `_1_ytdlp.py` | 视频下载（yt-dlp） |
| Step 2  | `_2_asr.py` | 语音识别转录 |
| Step 3.1| `_3_1_split_nlp.py` | NLP句子分割 |
| Step 3.2| `_3_2_split_meaning.py` | 语义分割 |
| Step 4.1| `_4_1_summarize.py` | 内容摘要与术语提取 |
| Step 4.2| `_4_2_translate.py` | 翻译处理 |
| Step 5  | `_5_split_sub.py` | 字幕分割对齐 |
| Step 6  | `_6_gen_sub.py` | 字幕文件生成 |
| Step 7  | `_7_sub_into_vid.py` | 字幕烧录到视频 |

### 处理阶段定义

```python
# backend/models/stage.py
SUBTITLE_STAGES = [
    ProcessingStage(name="asr", display_name="语音识别"),
    ProcessingStage(name="split_nlp", display_name="文本粗切分"),
    ProcessingStage(name="split_meaning", display_name="GPT 语义分句"),
    ProcessingStage(name="summarize", display_name="内容总结"),
    ProcessingStage(name="translate", display_name="翻译"),
    ProcessingStage(name="split_sub", display_name="字幕分割"),
    ProcessingStage(name="gen_sub", display_name="生成字幕"),
]
```

---

## 系统架构图

```mermaid
flowchart TB
    subgraph Input["📥 输入层"]
        YT[YouTube URL]
        Local[本地视频]
    end

    subgraph Backend["🖥️ 后端编排层"]
        FastAPI["FastAPI 路由"]
        PS["ProcessingService<br/>7阶段顺序执行"]
        TC["TqdmCapture<br/>日志捕获"]
        LS["LogStore<br/>前端日志推送"]
    end

    subgraph Core["🔧 Core 处理层"]
        subgraph ASR["ASR 模块"]
            Demucs["Demucs 人声分离"]
            WhisperLocal["WhisperX Local<br/>(faster-whisper)"]
            WhisperCloud["WhisperX Cloud<br/>(302.ai)"]
            Demucs --> WhisperLocal
            Demucs --> WhisperCloud
        end
        
        subgraph NLP["NLP 模块"]
            SpaCy["spaCy 多语言分词"]
            Split["标点/逗号/连接词分割"]
            SyntaxTree["句法树分析"]
        end
        
        subgraph LLM["LLM 模块"]
            SemanticSplit["GPT 语义分割"]
            TermExtract["术语提取与摘要"]
            Translate["翻译 (忠实+达意)"]
            SubCompress["字幕压缩优化"]
        end
        
        subgraph Video["视频处理模块"]
            FFmpeg["FFmpeg"]
            OpenCV["OpenCV"]
        end
    end

    subgraph Frontend["🎨 前端展示层"]
        PP["ProcessingPanel<br/>3标签页"]
        SE["SubtitleEditor<br/>字幕校对"]
    end

    subgraph External["☁️ 外部 API"]
        LLMAPI["LLM API<br/>OpenAI / DeepSeek<br/>302.ai / SiliconFlow"]
    end

    subgraph Output["📤 输出层"]
        SubVideo["output_sub.mp4<br/>带双语字幕视频"]
        SRT["src.srt / trans.srt<br/>字幕文件"]
    end

    Input --> FastAPI
    FastAPI --> PS
    PS --> TC
    TC --> LS
    LS --> PP
    PS --> Core
    Core --> Output
    
    LLM <--> LLMAPI
    PP --> SE
```

---

## 后端编排层

### ProcessingService 架构

`ProcessingService`（`backend/services/processing_service.py`）负责编排字幕处理的 7 个阶段，提供取消机制、日志捕获、状态恢复等能力。

```mermaid
classDiagram
    class ProcessingService {
        -output_dir: Path
        +create_subtitle_job(video_id) ProcessingJob
        +run_subtitle_processing(job, video) void
        +detect_completed_stages(job_type) dict
        +restore_job_state(job, video) void
        +is_subtitle_processing_completed() bool
        +cleanup_subtitle_files() void
        -_run_stage(job, stage_name, stage_func) void
        -_run_asr() void
        -_run_split_nlp() void
        -_run_split_meaning() void
        -_run_summarize() void
        -_run_translate() void
        -_run_split_sub() void
        -_run_gen_sub() void
    }

    class TqdmCapture {
        -log_store: LogStore
        -source: str
        -job_id: str
        -original_stream: IO
        -stage_name: str
        -_buffer: str
        -_important_patterns: list
        +write(text) int
        +flush() void
    }

    class ProcessingJob {
        +id: str
        +video_id: str
        +job_type: str
        +status: str
        +stages: list~ProcessingStage~
        +current_stage: str
        +start() void
        +complete() void
        +fail(error) void
        +update_stage(name, status, message) void
    }

    class ProcessingStage {
        +name: str
        +display_name: str
        +status: str
        +message: str
        +progress: float
        +duration_ms: int
    }

    class AppState {
        +is_cancel_requested() bool
        +clear_cancel_request() void
        +request_cancel() void
    }

    ProcessingService --> TqdmCapture : 创建并使用
    ProcessingService --> ProcessingJob : 管理
    ProcessingService --> AppState : 检查取消
    ProcessingJob --> ProcessingStage : 包含多个
```

### run_subtitle_processing 执行流程

`run_subtitle_processing()` 方法按顺序执行 7 个阶段，每个阶段之间检查取消标志：

```python
async def run_subtitle_processing(self, job: ProcessingJob, video: Video):
    # 1. 清除取消标志（内存 + 文件）
    state.clear_cancel_request()
    clear_cancel_flag()
    
    # 2. 顺序执行 7 个阶段
    await self._run_stage(job, "asr", self._run_asr)
    if state.is_cancel_requested(): return  # 取消检查
    
    await self._run_stage(job, "split_nlp", self._run_split_nlp)
    if state.is_cancel_requested(): return
    
    # ... 依次执行剩余阶段 ...
    
    await self._run_stage(job, "gen_sub", self._run_gen_sub)
    
    # 3. 标记完成
    job.complete()
```

### _run_stage 单阶段执行

每个阶段通过 `_run_stage()` 包装执行：

1. 设置阶段状态为 `running`
2. 创建 `TqdmCapture` 捕获 stdout/stderr
3. 通过 `asyncio.to_thread()` 在线程池中运行（避免阻塞事件循环）
4. 记录执行耗时
5. 阶段完成后更新状态为 `completed`

### TqdmCapture 日志捕获

`TqdmCapture` 替换 `sys.stdout` 和 `sys.stderr`，捕获 core/ 模块的输出：

- 过滤 tqdm 进度条（避免日志刷屏）
- 识别重要日志行（emoji 前缀、ERROR/WARNING 等）
- 将重要信息发送到 `LogStore`，供前端实时展示
- 同时保留原始输出流（双写）

### 取消机制

采用**双层取消**策略：

| 层级 | 机制 | 用途 |
|------|------|------|
| 内存层 | `AppState.is_cancel_requested()` | ProcessingService 在阶段间检查 |
| 文件层 | `core/utils/config_utils` 的 cancel flag 文件 | core/ 模块内部长时间操作检查 |

### 状态恢复

服务器重启后，`detect_completed_stages()` 通过检查 `STAGE_OUTPUT_FILES` 中定义的输出文件是否存在，重建处理任务的完成状态：

```python
def detect_completed_stages(self, job_type="subtitle"):
    stage_order = ["asr", "split_nlp", "split_meaning", 
                   "summarize", "translate", "split_sub", "gen_sub"]
    
    for stage_name in stage_order:
        # 检查该阶段的输出文件是否存在
        stage_files = STAGE_OUTPUT_FILES[stage_name]
        completed_stages[stage_name] = any(file.exists() for file in stage_files)
    
    return completed_stages
```

---

## 前端处理面板

### ProcessingPanel 3标签页架构

`ProcessingPanel`（`frontend/src/components/ProcessingPanel.tsx`）提供 3 个标签页：

```mermaid
flowchart LR
    subgraph Tab1["标签1: 字幕处理"]
        S1["语音识别"]
        S2["文本粗切分"]
        S3["GPT 语义分句"]
        S4["内容总结"]
        S5["翻译"]
        S6["字幕分割"]
        S7["生成字幕"]
        S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7
    end

    subgraph Tab2["标签2: 字幕校对"]
        Editor["进入字幕编辑器<br/>SubtitleEditor"]
    end

    subgraph Tab3["标签3: 合并到视频"]
        Merge["选择合并类型<br/>烧录字幕到视频"]
    end
```

### 状态轮询

前端每 **2 秒** 向后端轮询处理状态：

```typescript
// 轮询间隔
const POLLING_INTERVAL = 2000; // 2秒

// 获取处理状态
const status = await getProcessingStatus();
// 更新每个阶段的状态（pending/running/completed/failed）
// 显示进度、耗时、日志信息
```

### 阶段状态展示

每个阶段显示以下信息：

| 状态 | 图标 | 说明 |
|------|------|------|
| pending | 灰色圆点 | 等待执行 |
| running | 蓝色旋转 | 正在执行，显示日志消息 |
| completed | 绿色勾 | 完成，显示耗时 |
| failed | 红色叉 | 失败，显示错误信息 |

---

## 处理流程详解

### 完整处理流程图

```mermaid
flowchart LR
    subgraph Stage1["阶段一: 预处理"]
        S1["Step 1<br/>视频下载"]
        S2["Step 2<br/>语音识别"]
    end
    
    subgraph Stage2["阶段二: 文本处理"]
        S3_1["Step 3.1<br/>NLP分割"]
        S3_2["Step 3.2<br/>语义分割"]
        S4_1["Step 4.1<br/>摘要提取"]
        S4_2["Step 4.2<br/>翻译"]
    end
    
    subgraph Stage3["阶段三: 字幕处理"]
        S5["Step 5<br/>字幕分割"]
        S6["Step 6<br/>生成字幕"]
        S7["Step 7<br/>烧录字幕"]
    end

    S1 --> S2 --> S3_1 --> S3_2 --> S4_1 --> S4_2
    S4_2 --> S5 --> S6 --> S7
```

### Step 2: 语音识别详细流程

```mermaid
flowchart TD
    A[输入: video.mp4] --> B[ffprobe 检测声道数]
    B --> C[FFmpeg 提取音频]
    C --> D[raw.mp3<br/>保持原始声道 16kHz]
    D --> E{启用人声分离?}
    E -->|是| F[Demucs 分离]
    F --> G[vocal.mp3 人声<br/>双声道]
    F --> H[background.mp3 背景<br/>双声道]
    E -->|否| I[使用 raw.mp3 作为 vocal]
    
    D --> J{ASR 模式}
    J -->|本地| K[faster-whisper 转录<br/>使用 raw.mp3]
    J -->|云端| L[302.ai Whisper API<br/>使用 raw.mp3]
    
    K --> M[WhisperX 时间戳对齐]
    L --> M
    G --> M
    I --> M
    M -->|对齐使用 vocal| N{启用说话人分离?}
    
    N -->|是| O[pyannote.audio 分离]
    N -->|否| P[speaker = NaN]
    
    O --> Q[whisperx.assign_word_speakers<br/>分配说话人到每个词]
    Q --> R[输出: cleaned_chunks.xlsx<br/>包含 speaker 列]
    P --> R
```

> **说明**: 
> - `raw.mp3` 保持与原始视频相同的声道数（动态检测），比特率 = 32k × 声道数
> - 转录阶段使用 `raw.mp3`，对齐阶段使用 `vocal.mp3`（如果启用了 Demucs）
> - Demucs 输出始终为双声道（模型特性）

### Step 2 补充：说话人分离（Speaker Diarization）

> **📌 说话人分离的作用**
>
> 当视频中有多个说话人时，说话人分离可以识别出"谁在什么时候说话"，
> 为后续的翻译和配音提供更精确的上下文信息。

#### 完整处理流程

```mermaid
flowchart TD
    A[raw.mp3<br/>原始音频 16kHz] --> B{speaker_diarization<br/>配置开启?}
    
    B -->|否| Z1[跳过说话人分离<br/>speaker = NaN]
    B -->|是| C{hf_token<br/>有效?}
    
    C -->|否| Z2[警告: 无有效 Token<br/>跳过说话人分离]
    C -->|是| D[加载 pyannote Pipeline]
    
    subgraph LoadModel["模型加载阶段"]
        D --> D1[检查 HF_ENDPOINT<br/>设置镜像地址]
        D1 --> D2[Pipeline.from_pretrained<br/>pyannote/speaker-diarization-3.1]
        D2 --> D3[模型移动到 GPU/CPU]
    end
    
    D3 --> E[音频预处理]
    
    subgraph AudioPrep["音频准备"]
        E --> E1[numpy → torch.Tensor]
        E1 --> E2[添加 batch 维度<br/>unsqueeze 0]
        E2 --> E3[构建音频字典<br/>waveform + sample_rate]
    end
    
    E3 --> F[执行说话人分离]
    
    subgraph Diarize["pyannote Pipeline 内部流程"]
        F --> F1["1️⃣ VAD 语音活动检测<br/>pyannote/segmentation-3.0"]
        F1 --> F2["2️⃣ 说话人嵌入提取<br/>speechbrain/spkrec-ecapa-voxceleb"]
        F2 --> F3["3️⃣ 聚类分析<br/>AgglomerativeClustering"]
        F3 --> F4["4️⃣ 重叠语音检测<br/>Overlapped Speech Detection"]
        F4 --> F5["5️⃣ 边界优化<br/>Segmentation Refinement"]
    end
    
    F5 --> G[Diarization 结果<br/>Annotation 对象]
    
    subgraph Convert["结果转换"]
        G --> G1[itertracks yield_label=True]
        G1 --> G2[转换为 DataFrame]
        G2 --> G3[提取 start/end/speaker]
    end
    
    G3 --> H[whisperx.assign_word_speakers]
    
    subgraph Assign["说话人分配到词"]
        H --> H1[遍历 WhisperX 结果]
        H1 --> H2[每个 segment/word<br/>计算时间范围]
        H2 --> H3[与 Diarization 时间段<br/>计算重叠率]
        H3 --> H4[分配最大重叠的 speaker]
    end
    
    H4 --> I[输出: 带 speaker 标签的结果]
    
    subgraph Cleanup["资源清理"]
        I --> I1[删除 diarize_model]
        I1 --> I2[torch.cuda.empty_cache]
    end
    
    I2 --> J[cleaned_chunks.xlsx<br/>包含 speaker 列]
    Z1 --> J
    Z2 --> J
```

#### 说话人识别与声纹库（Qdrant）

> **📌 说明**
> - 说话人分离只给出匿名标签（如 `SPEAKER_00`）。
> - 说话人识别会将匿名标签映射到角色名。
> - 若 `speaker_samples/` 为空，可自动从分离结果中提取最长片段生成样本。

**流程要点：**
1. 使用 `pyannote/wespeaker-voxceleb-resnet34-LM` 提取声纹 embedding。
2. 参考样本写入 Qdrant（如果启用 `speaker_vector_db`）。
3. 识别时优先从 Qdrant 检索最相似声纹，再回写到 `segment/word.speaker`。

**Qdrant 存储结构：**
- **Collection**: `speaker_embeddings`（可配置）
- **Point ID**: UUID（由角色名派生）
- **Vector**: 声纹 embedding（flatten 后的浮点数组）
- **Payload**: `{ "speaker": "角色名" }`

#### pyannote-audio 4.0 Pipeline 详解

```mermaid
flowchart LR
    subgraph Input["输入"]
        A["音频文件/Tensor<br/>{'waveform': tensor, 'sample_rate': 16000}"]
    end
    
    subgraph Stage1["阶段 1: 语音检测"]
        B1["Segmentation Model<br/>pyannote/segmentation-3.0"]
        B2["输出: 语音/非语音时间段<br/>+ 重叠检测"]
    end
    
    subgraph Stage2["阶段 2: 嵌入提取"]
        C1["Embedding Model<br/>speechbrain/spkrec-ecapa-voxceleb"]
        C2["每个语音段 → 512维向量"]
    end
    
    subgraph Stage3["阶段 3: 聚类"]
        D1["层次聚类<br/>AgglomerativeClustering"]
        D2["相似度阈值判断<br/>合并同一说话人"]
    end
    
    subgraph Stage4["阶段 4: 后处理"]
        E1["边界优化"]
        E2["重叠区域处理"]
        E3["最小时长过滤"]
    end
    
    subgraph Output["输出"]
        F["Annotation 对象<br/>[(start, end, speaker_id), ...]"]
    end
    
    A --> B1 --> B2 --> C1 --> C2 --> D1 --> D2 --> E1 --> E2 --> E3 --> F
```

#### 说话人分离依赖的模型

| 模型名称 | HuggingFace 地址 | 用途 | 是否 Gated | 模型大小 |
|---------|-----------------|------|-----------|---------|
| speaker-diarization-3.1 | `pyannote/speaker-diarization-3.1` | 主 Pipeline 配置 | ✅ 需同意条款 | ~1KB (配置文件) |
| segmentation-3.0 | `pyannote/segmentation-3.0` | VAD + 重叠检测 | ✅ 需同意条款 | ~5MB |
| spkrec-ecapa-voxceleb | `speechbrain/spkrec-ecapa-voxceleb` | 说话人嵌入 (ECAPA-TDNN) | ❌ | ~80MB |

> **📌 注意**: pyannote-audio 4.0 默认使用 `speechbrain/spkrec-ecapa-voxceleb` 作为嵌入模型，
> 替代了之前版本的 `wespeaker-voxceleb-resnet34-LM`。

#### 代码实现细节

```python
# 1. 加载 Pipeline (whisperX_local.py)
from pyannote.audio import Pipeline
diarize_model = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token=hf_token  # HuggingFace Token
)
diarize_model = diarize_model.to(torch.device(device))  # GPU 加速

# 2. 准备音频输入
waveform = torch.from_numpy(raw_audio_segment).unsqueeze(0)
audio_dict = {"waveform": waveform, "sample_rate": 16000}

# 3. 执行说话人分离
diarize_result = diarize_model(audio_dict)

# 4. 转换结果为 DataFrame
diarize_df = pd.DataFrame(
    diarization.itertracks(yield_label=True), 
    columns=['segment', 'label', 'speaker']
)
diarize_df['start'] = diarize_df['segment'].apply(lambda x: x.start)
diarize_df['end'] = diarize_df['segment'].apply(lambda x: x.end)

# 5. 分配说话人到每个词
result = whisperx.assign_word_speakers(diarize_df, result)
```

#### 配置参数

| 参数 | 配置键 | 默认值 | 说明 |
|-----|-------|-------|------|
| 启用说话人分离 | `speaker_diarization` | `false` | 是否启用 pyannote 说话人分离 |
| HuggingFace Token | `hf_token` | 空 | 访问 gated 模型需要的 token |
| HuggingFace 镜像 | `hf_mirror` | 空 | 国内用户可设置为 `https://hf-mirror.com` |

#### 首次使用配置步骤

1. 访问 https://huggingface.co/settings/tokens 创建 Token（选择 "Read" 权限）
2. 访问以下页面并点击 "Agree" 同意条款：
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0
3. 在 `config.yaml` 中配置：
   ```yaml
   hf_token: 'hf_your_token_here'
   speaker_diarization: true
   hf_mirror: 'https://hf-mirror.com'  # 国内用户可选
   ```

#### 模型缓存位置

- Windows: `C:\Users\<用户名>\.cache\huggingface\hub\`
- Linux/Mac: `~/.cache/huggingface/hub/`

#### 依赖版本

| 包名 | 版本 | 说明 |
|-----|------|------|
| pyannote-audio | 4.0.3 | 主库 |
| pyannote-core | 6.0.1 | 核心数据结构 |
| pyannote-pipeline | 4.0.0 | Pipeline 框架 |
| speechbrain | - | 说话人嵌入模型 |
| whisperx | - | 时间戳分配 |

> **注意**：首次运行需要联网下载模型（约 85MB），后续运行直接从本地缓存加载。
> GPU 加速显著提升处理速度，建议使用 CUDA 设备。

### Step 3.1: 文本粗切分（NLP 预处理）

> **📌 注意：这一步不是真正的"分句"，而是文本粗切分**
> 
> Step 3.1 的目的是将 ASR 输出的长文本按**标点、时间间隔、连接词**等规则进行**粗切分**，
> 为后续的语义分割提供较短的文本片段。spaCy 在这里主要用于：
> - **分词（tokenize）**：计算文本长度
> - **依存分析**：识别连接词、词根等语法结构
> 
> **真正的智能分句在 Step 3.2 由 GPT 完成。**

```mermaid
flowchart TD
    A[输入: cleaned_chunks.xlsx<br/>字符级时间戳数据] --> B[拼接全部文本]
    
    B --> C[spaCy 标点分句<br/>split_by_mark]
    
    C --> D{启用时间间隔切分?<br/>time_gap_threshold > 0}
    
    D -->|是| E[对每个 spaCy 句子<br/>检查内部时间间隔]
    E --> F[单词持续时间 > 阈值<br/>或 单词间隔 > 阈值]
    F --> G[在超时点切分]
    
    D -->|否| H[保持 spaCy 分句结果]
    
    G --> I[split_by_mark.txt]
    H --> I
    
    I --> J[split_by_comma<br/>按逗号切分]
    J --> K[split_by_connector<br/>按连接词切分<br/>spaCy 依存分析]
    K --> L{文本长度 >60 tokens?}
    L -->|是| M[split_long_by_root<br/>动态规划按词根切分]
    L -->|否| N[保持原文本]
    M --> O[split_by_nlp.txt]
    N --> O
```

**时间间隔切分处理顺序**：

1. **先 spaCy 标点分句**：使用 spaCy 的 `doc.sents` 对全文进行标点分句
2. **后时间二次切分**：对每个 spaCy 分出的句子，检查内部是否有超阈值的时间间隔
   - 检查单词的 `duration`（持续时间）：Whisper 会把停顿时间算入单词持续时间
   - 检查单词间的 `gap_to_next`（间隔）：真正的单词间停顿
   - 如果任一值超过阈值，在该位置切分

> **为什么是这个顺序**：
> - 如果先时间切分再 spaCy 分句，spaCy 可能会对时间切分产生的片段做错误的二次分句
> - 例如日语 spaCy 可能把"かね何..."错误地切成"か"和"ね何..."
> - 先 spaCy 再时间切分，可以保留 spaCy 的标点识别能力，同时利用时间信息做精确切分

**spaCy 在 Step 3.1 的作用**：

| 功能 | 用途 | 说明 |
|-----|------|------|
| 分词 (tokenize) | 计算文本长度 | 判断是否需要进一步切分 |
| 依存分析 (dep) | 识别连接词 | `that`, `which`, `ので`, `ため` 等 |
| 词性标注 (pos) | 识别词根 | 动词、名词等作为切分点 |
| 句子边界 (sents) | 标点分句 | 对全文做初步标点分句 |

**时间间隔切分参数**：

| 参数 | 配置键 | 默认值 | 说明 |
|-----|-------|-------|------|
| 时间间隔阈值 | `time_gap_threshold` | 空 (不启用) | 单词持续时间或间隔超过此值(秒)时在 spaCy 句子内部再切分 |

> **日语处理优化**：日语口语通常没有明显标点，但 Whisper ASR 会在自然停顿处产生较长的单词持续时间。
> 设置 `time_gap_threshold: 3` 可以利用这些停顿点进行切分。
> 
> **注意**：Whisper 通常把停顿时间算入前一个单词的 `duration`，而不是 `gap_to_next`。
> 因此代码同时检查这两个值，确保不遗漏任何停顿点。

**文件流**：

```
cleaned_chunks.xlsx     ← ASR 输出（字符级时间戳）
    ↓ split_by_mark()       
    │   1. 拼接全文
    │   2. spaCy 标点分句
    │   3. (可选) 按时间间隔二次切分
split_by_mark.txt (临时)
    ↓ split_by_comma_main() 按逗号切分
split_by_comma.txt (临时)
    ↓ split_sentences_main() 按连接词切分
split_by_connector.txt (临时)
    ↓ split_long_by_root_main() 按词根切分超长文本
split_by_nlp.txt        ← Step 3.1 最终输出（粗切分结果）
```

### Step 3.2: 语义分句（GPT 智能分割）

> **📌 这一步才是真正的"分句"**
> 
> Step 3.2 使用 **GPT 进行语义理解**，将粗切分的文本片段进一步分割成**语义完整的句子**。
> spaCy 在这里只用于 **分词（tokenize）** 来计算文本长度，判断是否需要调用 GPT。

```mermaid
flowchart TD
    A[输入: split_by_nlp.txt<br/>粗切分文本] --> B[加载 spaCy 模型]
    B --> C[遍历每个文本片段]
    C --> D[spaCy tokenize<br/>计算 token 数量]
    
    D --> E{token 数 > max_split_length?}
    E -->|≤ 20 tokens| F[保持原文本<br/>长度合适无需分割]
    E -->|> 20 tokens| G[需要 GPT 分句]
    
    G --> H[计算分割数<br/>num_parts = ceil tokens/20]
    H --> I[调用 GPT API]
    
    subgraph GPT["GPT 语义分句"]
        I --> I1[Prompt: 将句子分成 N 部分]
        I1 --> I2[GPT 理解语义]
        I2 --> I3[返回: 句子1 ∥ 句子2 ∥ 句子3]
    end
    
    I3 --> J[find_split_positions<br/>在原文中定位分割点]
    
    subgraph Align["分割点对齐"]
        J --> J1[计算 GPT 结果与原文的相似度]
        J1 --> J2{相似度 > 0.9?}
        J2 -->|是| J3[记录分割位置]
        J2 -->|否| J4[Warning + 尽力匹配]
    end
    
    J3 --> K[在分割点插入换行]
    J4 --> K
    F --> L[split_by_meaning.txt]
    K --> L
    
    L --> M{还有超长句子?}
    M -->|是| N[递归处理<br/>最多 3 次]
    M -->|否| O[完成]
    N --> C
```

**spaCy 在 Step 3.2 的作用**：

| 功能 | 用途 |
|-----|------|
| **分词 (tokenize)** | 计算文本的 token 数量，判断是否超过阈值需要 GPT 分句 |

> **注意**：Step 3.2 中 spaCy **不做分句**，分句完全由 GPT 完成。

**语义分句关键参数**:

| 参数 | 配置键 | 默认值 | 说明 |
|-----|-------|-------|------|
| 最大分割长度 | `max_split_length` | 20 | 超过此 token 数触发 GPT 分句 |
| 时间间隔阈值 | `time_gap_threshold` | 空 (不启用) | Step 3.1 中按时间切分的阈值(秒) |
| 并发数 | `max_workers` | 4 | GPT 请求并发数 |
| 相似度阈值 | - | 0.9 | 分割点定位的最小相似度 |
| 最大重试次数 | - | 3 | 递归处理超长句子的次数 |

**语言模型选择逻辑**:

```python
# init_nlp() 语言选择 - 用于分词
user_language = load_key("whisper.language")      # 用户设置的语言
detected_language = load_key("whisper.detected_language")  # 自动检测的语言
language = user_language if user_language else detected_language

# 映射到 spaCy 模型（用于分词，不是分句）
SPACY_MODEL_MAP = {
    "ja": "ja_core_news_md",
    "en": "en_core_web_md", 
    "zh": "zh_core_web_md",
    ...
}
```

**GPT 分割 Prompt 示例**:

```
请将以下句子分成 3 部分，用 || 分隔:
"高レベルの警戒隠蔽を使うことはヨガラスのカメラを通して見ていたのでなお前が王女につきまとっていると知りサラムの魔眼に似せた仕組みを作らせたのだ"

GPT 返回:
"高レベルの警戒隠蔽を使うことはヨガラスのカメラを通して見ていたので||なお前が王女につきまとっていると知り||サラムの魔眼に似せた仕組みを作らせたのだ"
```

### Step 4.2: 翻译双步骤流程

> **⚠️ CJK 模式的分句"破坏"与重建**
>
> 对于 CJK 语言（日语 ja、中文 zh、韩语 ko），Step 4.2 会**打破 Step 3.2 的分句结构**：
> - Step 3.2 精心分割的语义句子在 Step 4.2 被**合并成大块**发送给 LLM 翻译
> - 翻译结果按 LLM 自然换行分割，**不再与原文行数对应**
> - 原文字符被**按字符数均匀分配**到翻译行中（用于显示对照，非语义对应）
> - 时间戳也被**均匀分配**到新的翻译行上
>
> **目的**：CJK 语言的特点是没有空格分词，Step 3.2 的分句结果可能在翻译后产生不自然的断句。
> 让 LLM 在翻译时自主决定如何断句，可以获得更流畅的目标语言字幕。
>
> **后果**：原文与译文的**行级对应关系被破坏**，但 Step 5 会再次基于字幕长度限制进行分割对齐。

```mermaid
flowchart TD
    A[输入文本] --> B["Step 1: 忠实翻译<br/>(直译原文、保持原意、参考术语表)"]
    B --> C{reflect_translate?}
    C -->|true| D["Step 2: 达意翻译<br/>(润色表达、优化语序、适应目标语言)"]
    C -->|false| E[输出忠实翻译结果]
    D --> F[输出达意翻译结果]
```

#### CJK 模式技术实现

```mermaid
flowchart TD
    A[split_by_meaning.txt<br/>Step 3.2 分句结果] --> B{检测源语言}
    
    B -->|非 CJK| C[保持原行结构翻译]
    B -->|CJK: ja/zh/ko| D[CJK 模式]
    
    subgraph CJK["CJK 模式处理"]
        D --> D1[合并多行成大块<br/>600字符/10行上限]
        D1 --> D2[发送给 LLM 翻译]
        D2 --> D3[获取翻译结果<br/>LLM 自然断行]
        D3 --> D4[原文按字符数<br/>均匀分配到译文行]
        D4 --> D5[时间戳按译文行数<br/>均匀分配]
    end
    
    subgraph NonCJK["非 CJK 模式处理"]
        C --> C1[逐行翻译保持对应]
        C1 --> C2[相似度匹配验证]
        C2 --> C3[原行 ↔ 译行 1:1 对应]
    end
    
    D5 --> E[translation.xlsx]
    C3 --> E
    
    E --> F[Step 5: 字幕分割<br/>基于 subtitle.max_length 再次切分]
```

**CJK 模式关键代码逻辑**:

```python
# 检测是否为 CJK 语言
cjk_languages = ['ja', 'zh', 'ko', 'japanese', 'chinese', 'korean']
is_cjk = detected_language.lower() in cjk_languages

if is_cjk:
    # 原文字符均匀分配到译文行
    chars_per_line = len(src_block) // len(trans_lines)
    src_text.append(src_block[start_idx:end_idx])
    
    # 时间戳均匀分配
    duration_per_line = total_duration / num_lines
```

### Step 5: 字幕分割对齐（重建分句结构）

> **📌 Step 5 的核心作用**
>
> Step 5 基于**显示长度限制**重新切分字幕，确保每行字幕不超过 `subtitle.max_length` 字符。
> 这一步对于 CJK 模式尤其重要，因为 Step 4.2 已经破坏了原有的分句结构。

```mermaid
flowchart TD
    A[translation.xlsx<br/>Step 4.2 翻译结果] --> B[遍历每行字幕]
    
    B --> C{计算显示长度<br/>calc_len考虑CJK权重}
    
    C -->|原文 > max_length<br/>或 译文×1.2 > max_length| D[需要分割]
    C -->|长度合适| E[保持原样]
    
    subgraph Split["GPT 分割处理"]
        D --> D1[调用 split_sentence<br/>与 Step 3.2 相同函数]
        D1 --> D2[GPT 分成 2 部分]
        D2 --> D3[align_subs 对齐<br/>原文与译文同步分割]
    end
    
    D3 --> F{还有超长行?}
    F -->|是| G[递归处理<br/>最多 3 次]
    G --> B
    F -->|否| H[输出 split_sub.xlsx]
    E --> H
```

**字幕长度计算权重**：

```python
def calc_len(text: str) -> float:
    """计算字幕显示长度，考虑不同字符宽度"""
    # 中日文字符权重 1.75
    # 韩文字符权重 1.5
    # 泰文字符权重 1.0
    # 全角符号权重 1.75
    # 英文和半角符号权重 1.0
```

**Step 5 关键参数**：

| 参数 | 配置键 | 默认值 | 说明 |
|-----|-------|-------|------|
| 字幕最大长度 | `subtitle.max_length` | 75 | 每行字幕的最大字符数（考虑权重后） |
| 译文长度倍数 | `subtitle.target_multiplier` | 1.2 | 译文通常比原文长，乘以此倍数后判断是否超长 |

### Step 3-4-5 分句流程总览

```mermaid
flowchart LR
    subgraph Step3["Step 3: 初次分句"]
        A1["3.1 NLP 粗分"] --> A2["3.2 GPT 语义分句"]
    end
    
    subgraph Step4["Step 4: 翻译"]
        B1["4.1 术语提取"] --> B2["4.2 翻译"]
        B2 --> B3{CJK?}
        B3 -->|是| B4["破坏分句结构<br/>LLM 自然断行"]
        B3 -->|否| B5["保持 1:1 对应"]
    end
    
    subgraph Step5["Step 5: 重建分句"]
        C1["检查每行长度"] --> C2{超长?}
        C2 -->|是| C3["GPT 分割 + 对齐"]
        C2 -->|否| C4["保持原样"]
    end
    
    A2 --> B1
    B4 --> C1
    B5 --> C1
    C3 --> D["split_sub.xlsx<br/>最终字幕分句"]
    C4 --> D
    
    style B4 fill:#ffcccc,stroke:#cc0000
    style C3 fill:#ccffcc,stroke:#00cc00
```

> **设计意图总结**：
> - **Step 3.2**: 基于语义的"粗分"，为翻译提供合理的上下文单元
> - **Step 4.2 CJK 模式**: 打破分句，让 LLM 翻译时自然断行，获得流畅的目标语言
> - **Step 5**: 基于显示长度的"精分"，确保字幕可读性，使用同样的 GPT 分句函数重建结构

---

## UML 图

### 处理流程序列图

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as React 前端
    participant Backend as FastAPI 后端
    participant YT as yt-dlp
    participant Demucs as Demucs
    participant Whisper as WhisperX
    participant SpaCy as spaCy
    participant LLM as LLM API
    participant FFmpeg as FFmpeg

    User->>Frontend: 上传视频/输入 URL
    Frontend->>Backend: POST /api/processing/start
    
    Backend->>YT: Step 1. 下载视频
    YT-->>Backend: video.mp4
    
    Backend->>Demucs: Step 2. 人声分离
    Demucs-->>Backend: vocal.mp3 + background.mp3
    
    Backend->>Whisper: Step 2. 语音识别 (raw.mp3)
    Whisper-->>Backend: 转录文本
    Backend->>Whisper: 时间戳对齐 (vocal.mp3)
    Whisper-->>Backend: cleaned_chunks.xlsx
    
    loop 前端轮询 (每2秒)
        Frontend->>Backend: GET /api/processing/status
        Backend-->>Frontend: 阶段状态、进度、日志
    end
    
    rect rgb(200, 230, 255)
        Note over SpaCy: Step 3.1 NLP 分句
        Backend->>SpaCy: 标点/时间分句
        SpaCy-->>Backend: split_by_mark.txt
        Backend->>SpaCy: 逗号/连接词/词根分割
        SpaCy-->>Backend: split_by_nlp.txt
    end
    
    rect rgb(255, 230, 200)
        Note over LLM: Step 3.2 语义分割
        Backend->>SpaCy: Tokenize 计算长度
        SpaCy-->>Backend: token 数量
        Backend->>LLM: GPT 分割超长句
        LLM-->>Backend: 分割点 (||)
    end
    
    Backend->>LLM: Step 4.1 术语提取
    LLM-->>Backend: terminology.json
    
    Backend->>LLM: Step 4.2 翻译
    LLM-->>Backend: translation.xlsx
    
    Backend->>LLM: Step 5. 字幕分割对齐
    LLM-->>Backend: split_sub.xlsx
    
    Backend->>Backend: Step 6. 生成 SRT 字幕文件
    
    Backend->>FFmpeg: Step 7. 烧录字幕到视频
    FFmpeg-->>Backend: output_sub.mp4
    
    Backend-->>Frontend: 处理完成
    Frontend-->>User: 显示完成状态，可进入字幕校对
```

### 模块类图

```mermaid
classDiagram
    class Core {
        +_1_ytdlp.py
        +_2_asr.py
        +_3_1_split_nlp.py
        +_3_2_split_meaning.py
        +_4_1_summarize.py
        +_4_2_translate.py
        +_5_split_sub.py
        +_6_gen_sub.py
        +_7_sub_into_vid.py
    }
    
    class ASRBackend {
        +whisperX_local.py
        +whisperX_302.py
        +elevenlabs_asr.py
        +demucs_vl.py
        +audio_preprocess.py
        +transcribe_audio()
        +speaker_diarization()
    }
    
    class SpeakerDiarization {
        +pyannote.audio 4.0.3 Pipeline
        +speaker-diarization-3.1
        +segmentation-3.0
        +speechbrain/spkrec-ecapa-voxceleb
        +AgglomerativeClustering
        +whisperx.assign_word_speakers()
    }
    
    class SpacyUtils {
        +load_nlp_model()
        +split_by_mark()
        +split_by_comma()
        +split_by_connector()
        +split_long_by_root()
    }
    
    class ProcessingService {
        -current_task: Optional~Task~
        -progress: dict
        +start_processing(task_id)
        +cancel_processing()
        +get_status() ProcessingStatus
        +run_stage(stage: ProcessingStage)
        -_execute_pipeline()
    }
    
    class SubtitleService {
        +get_subtitles(task_id) SubtitleData
        +save_subtitles(task_id, data)
        +restore_subtitles(task_id)
        +merge_to_video(task_id)
        +get_backup_list(task_id)
    }
    
    class Utils {
        +ask_gpt()
        +load_key()
        +check_file_exists()
        +except_handler()
        +rprint()
    }
    
    ProcessingService --> Core : 调度执行
    Core --> ASRBackend : uses
    ASRBackend --> SpeakerDiarization : optional
    Core --> SpacyUtils : uses
    Core --> Utils : uses
    SubtitleService --> Core : 调用 _7_sub_into_vid
```

### 状态机图

```mermaid
stateDiagram-v2
    [*] --> Download: 开始处理
    
    Download --> ASR: 下载完成
    Download --> Error: 下载失败
    
    ASR --> NLPSplit: ASR完成
    ASR --> Error: ASR失败
    
    NLPSplit --> LLMSplit: NLP分割完成
    NLPSplit --> Error: 分割失败
    
    LLMSplit --> Summarize: 语义分割完成
    
    Summarize --> Translate: 术语提取完成
    
    Translate --> Pause: pause_before_translate=true
    Translate --> SubSplit: 翻译完成
    
    Pause --> SubSplit: 用户确认继续
    
    SubSplit --> GenSub: 字幕分割完成
    
    GenSub --> BurnSub: 字幕生成完成
    
    BurnSub --> [*]: 字幕烧录完成
    
    BurnSub --> Proofread: 进入字幕校对
    
    Proofread --> Merged: 校对完成，重新合成
    
    Merged --> [*]: 最终视频生成
    
    Error --> [*]: 处理终止
```

---

## 模型与技术选型

### ASR 模型对比

```mermaid
graph LR
    subgraph Local["本地模型"]
        A["faster-whisper-large-v3<br/>高精度"]
        B["faster-whisper-large-v3-turbo<br/>速度快"]
        C["Belle-whisper-large-v3-zh<br/>中文优化"]
    end
    
    subgraph Cloud["云端 API"]
        D["302.ai Whisper<br/>无需 GPU"]
        E["ElevenLabs ASR<br/>高质量"]
    end
    
    subgraph Alignment["时间戳对齐"]
        F["WhisperX<br/>单词级对齐"]
    end
    
    subgraph Diarization["说话人分离 (可选)"]
        G["pyannote.audio<br/>speaker-diarization-3.1"]
    end
    
    A --> F
    B --> F
    C --> F
    D --> F
    E --> F
    F --> G
```

### 说话人分离技术栈 (pyannote-audio 4.0.3)

| 组件 | 模型/库 | HuggingFace 地址 | 说明 |
|-----|--------|------------------|------|
| Pipeline | pyannote-audio 4.0.3 | `pyannote/speaker-diarization-3.1` | 主 Pipeline 配置文件 |
| VAD + OSD | segmentation-3.0 | `pyannote/segmentation-3.0` | 语音活动检测 + 重叠语音检测 |
| Speaker Embedding | ECAPA-TDNN | `speechbrain/spkrec-ecapa-voxceleb` | 提取说话人 512 维特征向量 |
| Clustering | AgglomerativeClustering | - | 层次聚类，合并同一说话人 |
| Speaker Assignment | whisperx | `whisperx.assign_word_speakers` | 将说话人标签分配到每个词 |

> **版本变更说明**: pyannote-audio 4.0 使用 `speechbrain/spkrec-ecapa-voxceleb` (ECAPA-TDNN) 替代了
> 之前版本的 `wespeaker-voxceleb-resnet34-LM`，提供更好的说话人嵌入质量。

### NLP 模型支持

| 语言 | spaCy 模型 | 用途 |
|-----|-----------|------|
| English | `en_core_web_md` | 分词、句法分析 |
| Chinese | `zh_core_web_md` | 中文分词 |
| Japanese | `ja_core_news_md` | 日文分词 |
| German | `de_core_news_md` | 德文分词 |
| French | `fr_core_news_md` | 法文分词 |
| Spanish | `es_core_news_md` | 西班牙文分词 |

---

## 数据流图

### 文件数据流

```mermaid
flowchart TD
    subgraph Input["输入"]
        V["video.mp4<br/>或 YouTube URL"]
    end
    
    subgraph Audio["output/audio/"]
        A1["raw.mp3"]
        A2["vocal.mp3"]
        A3["background.mp3"]
    end
    
    subgraph Log["output/log/"]
        L1["cleaned_chunks.xlsx<br/>(含 speaker 列)"]
        L2["split_by_nlp.txt"]
        L3["split_by_meaning.txt"]
        L4["translation.xlsx"]
        L5["split_sub.xlsx"]
    end
    
    subgraph GPTLog["output/gpt_log/"]
        G1["terminology.json"]
        G2["summary.json"]
    end
    
    subgraph Final["output/"]
        F1["src.srt"]
        F2["trans.srt"]
        F3["src_trans.srt"]
        F5["output_sub.mp4"]
    end
    
    V -->|Step 2| A1
    A1 -->|Demucs| A2
    A1 -->|Demucs| A3
    A2 -->|WhisperX| L1
    L1 -->|Step 3.1| L2
    L2 -->|Step 3.2| L3
    L3 -->|Step 4.1| G1
    L3 -->|Step 4.1| G2
    L3 -->|Step 4.2| L4
    L4 -->|Step 5| L5
    L5 -->|Step 6| F1
    L5 -->|Step 6| F2
    L5 -->|Step 6| F3
    F2 -->|Step 7| F5
```

### 配置参数关系图

```mermaid
mindmap
  root((config.yaml))
    API配置
      api.key
      api.base_url
      api.model
    语言配置
      source_language
      target_language
      whisper.method
      whisper.language
    处理参数
      max_workers
      max_split_length
      time_gap_threshold
      summary_length
      reflect_translate
    字幕配置
      subtitle.max_length
      subtitle.target_multiplier
      burn_subtitles
    网络配置
      hf_mirror
      http_proxy
    说话人分离
      speaker_diarization
      hf_token
```

---

## 总结

VideoLingo 字幕处理系统是一个模块化设计的视频字幕自动化工具，具有以下特点：

```mermaid
mindmap
  root((VideoLingo 字幕处理))
    架构特点
      流水线架构
        7个独立步骤
        中间文件产出
        断点续传支持
      多模型支持
        ASR引擎切换
        LLM模型切换
      前后端分离
        FastAPI 后端编排
        React 前端轮询
    核心能力
      智能处理
        LLM语义分割
        双步骤翻译
        术语一致性
      字幕校对
        Aegisub风格编辑
        波形时间轴
        草稿自动保存
        字幕还原
      性能优化
        并行处理
        GPU加速
        缓存机制
    配置灵活
      config.yaml
      API密钥管理
      多语言支持
```

### 技术栈总览

```mermaid
pie title 技术栈组成
    "Python Core" : 35
    "AI/ML Models" : 25
    "FFmpeg/Audio" : 15
    "React Frontend" : 15
    "External APIs" : 10
```

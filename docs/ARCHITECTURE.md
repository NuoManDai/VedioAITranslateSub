# VideoLingo Core 架构文档

## 📋 目录

1. [项目概述](#项目概述)
2. [系统架构图](#系统架构图)
3. [处理流程详解](#处理流程详解)
4. [UML 图](#uml-图)
5. [模型与技术选型](#模型与技术选型)
6. [数据流图](#数据流图)

---

## 项目概述

VideoLingo 是一个完整的视频本地化处理系统，支持视频下载、语音识别（ASR）、字幕分割、翻译、配音（TTS）、音视频合成等全流程自动化处理。

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
| Step 8.1| `_8_1_audio_task.py` | 配音任务生成 |
| Step 8.2| `_8_2_dub_chunks.py` | 配音分块处理 |
| Step 9  | `_9_refer_audio.py` | 参考音频提取 |
| Step 10 | `_10_gen_audio.py` | TTS 音频生成 |
| Step 11 | `_11_merge_audio.py` | 音频合并 |
| Step 12 | `_12_dub_to_vid.py` | 配音合成到视频 |

---

## 系统架构图

```mermaid
flowchart TB
    subgraph Input["📥 输入层"]
        YT[YouTube URL]
        Local[本地视频]
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
        
        subgraph TTS["TTS 模块"]
            AzureTTS["Azure TTS"]
            OpenAITTS["OpenAI TTS"]
            EdgeTTS["Edge TTS (免费)"]
            GPTSOVITS["GPT-SoVITS (本地)"]
            FishTTS["Fish TTS"]
            CosyVoice["CosyVoice2 / F5-TTS"]
        end
        
        subgraph Video["视频处理模块"]
            FFmpeg["FFmpeg"]
            OpenCV["OpenCV"]
            Pydub["pydub"]
        end
    end

    subgraph External["☁️ 外部 API"]
        LLMAPI["LLM API<br/>OpenAI / DeepSeek<br/>302.ai / SiliconFlow"]
        TTSAPI["TTS API<br/>Azure / OpenAI<br/>Fish / Edge"]
    end

    subgraph Output["📤 输出层"]
        SubVideo["output_sub.mp4<br/>带双语字幕视频"]
        DubVideo["output_dub.mp4<br/>带配音视频"]
        SRT["src.srt / trans.srt<br/>字幕文件"]
        DubAudio["dub.mp3<br/>配音音频"]
    end

    Input --> ASR
    ASR --> NLP
    NLP --> LLM
    LLM --> TTS
    TTS --> Video
    Video --> Output
    
    LLM <--> LLMAPI
    TTS <--> TTSAPI
```

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
    
    subgraph Stage4["阶段四: 配音处理"]
        S8_1["Step 8.1<br/>配音任务"]
        S8_2["Step 8.2<br/>配音分块"]
        S9["Step 9<br/>参考音频"]
        S10["Step 10<br/>TTS生成"]
        S11["Step 11<br/>音频合并"]
        S12["Step 12<br/>配音合成"]
    end

    S1 --> S2 --> S3_1 --> S3_2 --> S4_1 --> S4_2
    S4_2 --> S5 --> S6 --> S7
    S7 --> S8_1 --> S8_2 --> S9 --> S10 --> S11 --> S12
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
    M -->|对齐使用 vocal| N[输出: cleaned_chunks.xlsx]
```

> **说明**: 
> - `raw.mp3` 保持与原始视频相同的声道数（动态检测），比特率 = 32k × 声道数
> - 转录阶段使用 `raw.mp3`，对齐阶段使用 `vocal.mp3`（如果启用了 Demucs）
> - Demucs 输出始终为双声道（模型特性）

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
    A[输入: cleaned_chunks.xlsx<br/>字符级时间戳数据] --> B{启用时间间隔切分?<br/>time_gap_threshold > 0}
    
    B -->|是| B1[按时间间隔预切分<br/>单词持续时间 > 阈值秒]
    B -->|否| B2[跳过时间切分]
    
    B1 --> C[split_by_mark<br/>按标点粗切分]
    B2 --> C
    
    C --> D[split_by_comma<br/>按逗号切分]
    D --> E[split_by_connector<br/>按连接词切分<br/>spaCy 依存分析]
    E --> F{文本长度 >60 tokens?}
    F -->|是| G[split_long_by_root<br/>动态规划按词根切分]
    F -->|否| H[保持原文本]
    G --> I[split_by_nlp.txt]
    H --> I
```

**spaCy 在 Step 3.1 的作用**：

| 功能 | 用途 | 说明 |
|-----|------|------|
| 分词 (tokenize) | 计算文本长度 | 判断是否需要进一步切分 |
| 依存分析 (dep) | 识别连接词 | `that`, `which`, `ので`, `ため` 等 |
| 词性标注 (pos) | 识别词根 | 动词、名词等作为切分点 |
| 句子边界 (sents) | 粗切分 | 仅对有标点的语言有效 |

**时间间隔切分参数**：

| 参数 | 配置键 | 默认值 | 说明 |
|-----|-------|-------|------|
| 时间间隔阈值 | `time_gap_threshold` | 空 (不启用) | 单词持续时间超过此值(秒)时强制切分，日语推荐 1.0 |

> **日语处理优化**：日语口语通常没有明显标点，但 ASR 会在自然停顿处产生较长的单词持续时间。
> 设置 `time_gap_threshold: 1.0` 可以利用这些停顿点进行切分。

**文件流**：

```
cleaned_chunks.xlsx     ← ASR 输出（字符级时间戳）
    ↓ split_by_mark()       按标点/时间粗切分
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
| 最大分割长度 | `max_split_length` | 日语12 / 其他20 | 超过此 token 数触发 GPT 分句 |
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

```mermaid
flowchart TD
    A[输入文本] --> B[Step 1: 忠实翻译]
    B --> C{启用达意翻译?}
    C -->|是| D[Step 2: 达意翻译]
    C -->|否| E[输出翻译结果]
    D --> E
    
    subgraph Step1["忠实翻译 (Faithfulness)"]
        B1["直译原文"]
        B2["保持原意"]
        B3["参考术语表"]
    end
    
    subgraph Step2["达意翻译 (Expressiveness)"]
        D1["润色表达"]
        D2["优化语序"]
        D3["适应目标语言"]
    end
    
    B --> Step1
    D --> Step2
```

---

## UML 图

### 处理流程序列图

```mermaid
sequenceDiagram
    participant User as 用户
    participant YT as yt-dlp
    participant Demucs as Demucs
    participant Whisper as WhisperX
    participant SpaCy as spaCy
    participant LLM as LLM API
    participant TTS as TTS API
    participant FFmpeg as FFmpeg

    User->>YT: 1. 下载视频
    YT-->>User: video.mp4
    
    User->>Demucs: 2. 人声分离
    Demucs-->>User: vocal.mp3 + background.mp3
    
    User->>Whisper: 3. 语音识别 (raw.mp3)
    Whisper-->>User: 转录文本
    User->>Whisper: 时间戳对齐 (vocal.mp3)
    Whisper-->>User: cleaned_chunks.xlsx
    
    rect rgb(200, 230, 255)
        Note over SpaCy: Step 3.1 NLP 分句
        User->>SpaCy: 4a. 标点/时间分句
        SpaCy-->>User: split_by_mark.txt
        User->>SpaCy: 4b. 逗号分割
        SpaCy-->>User: split_by_comma.txt
        User->>SpaCy: 4c. 连接词分割
        SpaCy-->>User: split_by_connector.txt
        User->>SpaCy: 4d. 长句按词根分割
        SpaCy-->>User: split_by_nlp.txt
    end
    
    rect rgb(255, 230, 200)
        Note over LLM: Step 3.2 语义分割
        User->>SpaCy: 5a. 加载语言模型
        SpaCy-->>User: nlp (ja/en/zh...)
        User->>SpaCy: 5b. Tokenize 计算长度
        SpaCy-->>User: token 数量
        User->>LLM: 5c. GPT 分割超长句
        LLM-->>User: 分割点 (||)
        User->>User: 5d. 定位并应用分割
        User-->>User: split_by_meaning.txt
    end
    
    User->>LLM: 6. 术语提取
    LLM-->>User: terminology.json
    
    User->>LLM: 7. 翻译
    LLM-->>User: 翻译结果
    
    User->>LLM: 8. 字幕压缩
    LLM-->>User: 适配长度的字幕
    
    User->>TTS: 9. 生成配音
    TTS-->>User: 音频片段
    
    User->>FFmpeg: 10. 音视频合成
    FFmpeg-->>User: output_dub.mp4
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
        +_8_1_audio_task.py
        +_8_2_dub_chunks.py
        +_9_refer_audio.py
        +_10_gen_audio.py
        +_11_merge_audio.py
        +_12_dub_to_vid.py
    }
    
    class ASRBackend {
        +whisperX_local.py
        +whisperX_302.py
        +elevenlabs_asr.py
        +demucs_vl.py
        +audio_preprocess.py
        +transcribe_audio()
    }
    
    class SpacyUtils {
        +load_nlp_model()
        +split_by_mark()
        +split_by_comma()
        +split_by_connector()
        +split_long_by_root()
    }
    
    class TTSBackend {
        +tts_main.py
        +azure_tts.py
        +openai_tts.py
        +edge_tts.py
        +gpt_sovits_tts.py
        +fish_tts.py
        +sf_cosyvoice2.py
        +generate_audio()
    }
    
    class Utils {
        +ask_gpt()
        +load_key()
        +check_file_exists()
        +except_handler()
        +rprint()
    }
    
    Core --> ASRBackend : uses
    Core --> SpacyUtils : uses
    Core --> TTSBackend : uses
    Core --> Utils : uses
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
    
    BurnSub --> AudioTask: 字幕烧录完成
    
    AudioTask --> DubChunks: 任务生成完成
    
    DubChunks --> ReferAudio: 分块完成
    
    ReferAudio --> TTSGen: 参考音频提取完成
    
    TTSGen --> MergeAudio: TTS生成完成
    TTSGen --> Error: TTS失败
    
    MergeAudio --> DubVid: 音频合并完成
    
    DubVid --> [*]: 处理完成
    
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
    
    A --> F
    B --> F
    C --> F
    D --> F
    E --> F
```

### TTS 功能支持表

| 引擎 | 语言支持 | 声音克隆 | 成本 | API 来源 |
|-----|---------|---------|------|---------|
| **Azure TTS** | 100+ | ❌ | 付费 | 302.ai |
| **OpenAI TTS** | 多语言 | ❌ | 付费 | 302.ai |
| **Edge TTS** | 多语言 | ❌ | 免费 | 微软 |
| **GPT-SoVITS** | 多语言 | ✅ | 本地部署 | 本地 |
| **Fish TTS** | 中/英 | ✅ | 付费 | 302.ai / SiliconFlow |
| **CosyVoice2** | 中/英 | ✅ | 付费 | SiliconFlow |
| **F5-TTS** | 多语言 | ✅ | 付费 | 302.ai |

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
        A4["refers/*.wav"]
        A5["segs/*.wav"]
        A6["audio_task.xlsx"]
    end
    
    subgraph Log["output/log/"]
        L1["cleaned_chunks.xlsx"]
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
        F4["dub.mp3"]
        F5["output_sub.mp4"]
        F6["output_dub.mp4"]
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
    L5 -->|Step 8| A6
    A2 -->|Step 9| A4
    A6 -->|Step 10| A5
    A5 -->|Step 11| F4
    F4 -->|Step 12| F6
    A3 -->|Step 12| F6
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
    TTS配置
      tts_method
      speed_factor.accept
      speed_factor.min
      voice_character
    字幕配置
      subtitle.max_length
      subtitle.target_multiplier
      burn_subtitles
    网络配置
      hf_mirror
      http_proxy
```

---

## 总结

VideoLingo 是一个模块化设计的视频本地化系统，具有以下特点：

```mermaid
mindmap
  root((VideoLingo))
    架构特点
      流水线架构
        12个独立步骤
        中间文件产出
        断点续传支持
      多模型支持
        ASR引擎切换
        TTS引擎切换
        LLM模型切换
    核心能力
      智能处理
        LLM语义分割
        双步骤翻译
        术语一致性
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
    "Python Core" : 40
    "AI/ML Models" : 25
    "FFmpeg/Audio" : 15
    "FastAPI/React" : 12
    "External APIs" : 8
```

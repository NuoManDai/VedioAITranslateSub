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
            WhisperLocal["WhisperX Local<br/>(faster-whisper)"]
            WhisperCloud["WhisperX Cloud<br/>(302.ai)"]
            Demucs["Demucs 人声分离"]
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
    A[输入: video.mp4] --> B[FFmpeg 提取音频]
    B --> C{启用人声分离?}
    C -->|是| D[Demucs 分离]
    D --> E[vocal.mp3 人声]
    D --> F[background.mp3 背景]
    C -->|否| G[raw.mp3 原始音频]
    E --> H{ASR 模式}
    G --> H
    H -->|本地| I[faster-whisper]
    H -->|云端| J[302.ai Whisper API]
    I --> K[WhisperX 时间戳对齐]
    J --> K
    K --> L[输出: cleaned_chunks.xlsx]
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
    
    User->>Whisper: 3. 语音识别
    Whisper-->>User: 转录文本 + 时间戳
    
    User->>SpaCy: 4. NLP分割
    SpaCy-->>User: 分句结果
    
    User->>LLM: 5. 语义分割
    LLM-->>User: 优化分句
    
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
      target_language
      whisper.model
      whisper.language
      whisper.runtime
    处理参数
      max_workers
      max_split_length
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

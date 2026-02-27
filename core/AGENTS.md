# core/ — 只读流水线

> **禁止修改此目录中的任何文件。** 这是第一条规则。从 `backend/services/` 调用这些模块，绝不编辑。

## 概述

顺序视频处理流水线：下载 → 转录 → 分句 → 翻译 → 字幕 → TTS → 配音。12 个编号阶段，两条子流水线。

## 流水线阶段

| # | 文件 | 用途 | 备注 |
|---|------|------|------|
| 1 | `_1_ytdlp.py` | 通过 yt-dlp 下载视频 | |
| 2 | `_2_asr.py` | ASR 语音转录 | 委托给 `asr_backend/` |
| 3.1 | `_3_1_audio_split.py` | 按句拆分音频 | |
| 3.2 | `_3_2_lyric_split.py` | 拆分歌词/字幕 | |
| 4.1 | `_4_1_summarize.py` | 摘要以提供翻译上下文 | LLM 调用 |
| 4.2 | `_4_2_translate.py` | 翻译字幕 | LLM 调用 |
| 5 | `_5_split_sub.py` | 拆分翻译后的字幕 | |
| 6 | `_6_generate_final_timeline.py` | 生成最终时间轴 | |
| 7 | `_7_sub_into_vid.py` | 烧录字幕到视频 | **包含 `exit(1)`！** |
| 8.1 | `_8_1_audio_task.py` | 为 TTS 准备音频 | |
| 8.2 | `_8_2_gen_dub_chunks.py` | 生成配音音频块 | TTS 后端调用 |
| 9 | `_9_uvr_audio.py` | UVR 音频分离 | |
| 10 | `_10_gen_audio.py` | 生成最终音频 | **使用 `eval()`** |
| 11 | `_11_merge_audio.py` | 合并音频轨道 | **使用 `eval()`** |
| 12 | `_12_dub_to_vid.py` | 将配音合成到视频 | |

**阶段 1-7：** 字幕流水线。**阶段 8-12：** 配音流水线。

## 目录结构

- `asr_backend/` — 9 种 ASR 实现。WhisperX 为默认。无 `__init__.py`。
- `tts_backend/` — 11 种 TTS 实现。无 `__init__.py`。GPT-SoVITS 有 `os.chdir()` 问题。
- `spacy_utils/` — NLP 分句处理（6 个文件）。
- `utils/` — 配置加载器（`load_key()`）、路径辅助、共享模型。所有路径假设 `output/` 为相对路径。
- `prompts/` — 翻译和摘要的 LLM 提示词模板。

## 集成方式

后端用 `asyncio.to_thread()` 包装所有 core 调用。Core 函数都是阻塞的。

```python
# backend/services/processing_service.py
from core._2_asr import transcribe

async def run_stage_2():
    await asyncio.to_thread(transcribe)
```

工作空间配置：`core_path_manager`（在 backend 中）在每次运行前将文件拷贝到平铺的 `output/` 目录，运行后将结果拷回。Core 硬编码了 `output/` 相对路径，这一点不可更改。

取消机制：`config_utils.set_cancel_flag()` 写入 `.cancel_requested` 哨兵文件。各阶段在操作间检查此文件。

## 反模式

1. **编辑 core 文件。** 只读就是只读。零例外。
2. **在 `async def` 中直接调用 core。** 必须用 `asyncio.to_thread()`。Core 使用 `time.sleep()` 和阻塞 I/O。
3. **更改 `output/` 路径假设。** 所有路径辅助函数硬编码相对 `output/`。不要改动。
4. **复制 `eval()` 模式。** 阶段 10-11 对 DataFrame 字符串使用 `eval()`。新代码使用 JSON 解析。
5. **添加 `sys.path.insert()`。** `backend/main.py` 中已处理过一次，不要重复。
6. **捕获阶段 7 的 `exit(1)`。** 它直接调用 `exit()`。如需容错请在子进程中运行。

## 注意事项

- `gpt_sovits_tts.py` 通过 `os.chdir()` 修改全局工作目录。在异步环境中存在竞态条件。
- 通配符导入（`from utils import *`）很常见。不要在 backend 代码中复制此模式。
- 部分文件有裸 `except:` 块。不要复制该模式。
- 配置读取通过 `config_utils.load_key()`，从项目根目录读取 `config.yaml`。
- `asr_backend/` 和 `tts_backend/` 无 `__init__.py`。导入使用直接文件路径。

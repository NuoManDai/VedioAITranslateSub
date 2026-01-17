# Video AI Translate Sub

一站式视频翻译、本地化和配音工具，生成 Netflix 级别的字幕质量。

## 🌟 功能特性

- 🎥 通过 yt-dlp 下载 YouTube 视频
- **🎙️ WhisperX 词级识别和低幻觉字幕**
- **📝 NLP 和 AI 驱动的字幕分割**
- **📚 自定义 + AI 生成术语表，保证翻译一致性**
- **🔄 三步翻译-反思-调整流程，达到影视级质量**
- **✅ Netflix 标准单行字幕**
- **🗣️ 支持 GPT-SoVITS、Azure、OpenAI 等多种配音方案**
- 🚀 Streamlit 一键启动和处理
- 🌍 多语言界面支持
- 📝 详细日志和进度恢复

## 🎥 演示

<table>
<tr>
<td width="33%">

### 双语字幕
---
https://github.com/user-attachments/assets/a5c3d8d1-2b29-4ba9-b0d0-25896829d951

</td>
<td width="33%">

### Cosy2 语音克隆
---
https://github.com/user-attachments/assets/e065fe4c-3694-477f-b4d6-316917df7c0a

</td>
<td width="33%">

### GPT-SoVITS 配音
---
https://github.com/user-attachments/assets/47d965b2-b4ab-4a0b-9d08-b49a7bf3508c

</td>
</tr>
</table>

### 语言支持

**输入语言支持：**

🇺🇸 英语 🤩 | 🇷🇺 俄语 😊 | 🇫🇷 法语 🤩 | 🇩🇪 德语 🤩 | 🇮🇹 意大利语 🤩 | 🇪🇸 西班牙语 🤩 | 🇯🇵 日语 😐 | 🇨🇳 中文* 😊

> *中文使用单独的标点增强 whisper 模型

**翻译支持所有语言，配音语言取决于所选的 TTS 方法。**

## 安装

### 前置要求

> **Windows + NVIDIA GPU 用户：**
> 1. 安装 [CUDA Toolkit 12.6](https://developer.download.nvidia.com/compute/cuda/12.6.0/local_installers/cuda_12.6.0_560.76_windows.exe)
> 2. 安装 [CUDNN 9.3.0](https://developer.download.nvidia.com/compute/cudnn/9.3.0/local_installers/cudnn_9.3.0_windows.exe)
> 3. 将 `C:\Program Files\NVIDIA\CUDNN\v9.3\bin\12.6` 添加到系统 PATH
> 4. 重启电脑

> **FFmpeg 必需：**
> - Windows: `choco install ffmpeg` (通过 [Chocolatey](https://chocolatey.org/))
> - macOS: `brew install ffmpeg` (通过 [Homebrew](https://brew.sh/))
> - Linux: `sudo apt install ffmpeg` (Debian/Ubuntu)

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/NuoManDai/VedioAITranslateSub.git
cd VedioAITranslateSub
```

2. 安装依赖 (需要 `python=3.10`)

```bash
conda create -n videolingo python=3.10.0 -y
conda activate videolingo
python install.py
```

3. 启动应用

```bash
streamlit run st.py
```

### Docker

也可以使用 Docker（需要 CUDA 12.4 和 NVIDIA Driver 版本 >550）：

```bash
docker build -t video-ai-translate .
docker run -d -p 8501:8501 --gpus all video-ai-translate
```

## API 配置

支持 OpenAI-Like API 格式和多种 TTS 接口：

- **LLM**: `claude-3-5-sonnet`, `gpt-4.1`, `deepseek-v3`, `gemini-2.0-flash` 等
- **WhisperX**: 本地运行 whisperX (large-v3) 或使用云端 API
- **TTS**: `azure-tts`, `openai-tts`, `siliconflow-fishtts`, `fish-tts`, `GPT-SoVITS`, `edge-tts`, `custom-tts`

## 当前限制

1. WhisperX 转录性能可能受视频背景噪音影响。对于背景音乐较大的视频，请启用人声分离增强。

2. 使用较弱的模型可能因 JSON 格式要求导致错误。如果出现此错误，请删除 `output` 文件夹并使用其他 LLM 重试。

3. 由于不同语言的语速和语调差异，配音功能可能无法达到 100% 完美。

4. **多语言视频转录只会保留主要语言**。

5. **目前无法单独为多个角色配音**。

## 📬 联系

- 在 GitHub 提交 [Issues](https://github.com/NuoManDai/VedioAITranslateSub/issues) 或 [Pull Requests](https://github.com/NuoManDai/VedioAITranslateSub/pulls)

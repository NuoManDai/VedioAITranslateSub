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

#### 1. CUDA 环境配置（NVIDIA GPU 用户必需）

本项目使用 **PyTorch 2.9+ 和 CUDA 12.8**，支持最新的 NVIDIA GPU（包括 RTX 50 系列 Blackwell 架构）。

**Windows 安装步骤：**

1. **安装 CUDA Toolkit 12.8**
   - 下载地址：[CUDA 12.8.0](https://developer.download.nvidia.com/compute/cuda/12.8.0/local_installers/cuda_12.8.0_571.96_windows.exe)
   - 安装时选择 "Express" 快速安装即可

2. **安装 cuDNN 9.x**
   - 下载地址：[cuDNN 9.8.0](https://developer.download.nvidia.com/compute/cudnn/9.8.0/local_installers/cudnn_9.8.0_windows.exe)
   - 运行安装程序，自动安装到正确位置

3. **配置环境变量**
   - 将以下路径添加到系统 PATH：
     ```
     C:\Program Files\NVIDIA\CUDNN\v9.x\bin\12.x
     C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin
     ```

4. **验证安装**
   ```powershell
   nvcc --version  # 应显示 CUDA 12.8
   nvidia-smi      # 应显示 GPU 信息和驱动版本
   ```

5. **重启电脑**

> **支持的 GPU：** RTX 20/30/40/50 系列、Tesla、Quadro 等支持 CUDA 12.x 的显卡

#### 2. FFmpeg 安装（必需）

FFmpeg 用于音视频处理，**必须安装**。

**Windows 安装方法（任选一种）：**

**方法 A：手动安装（推荐）**
1. 下载 FFmpeg：[https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip)
2. 解压到 `C:\ffmpeg`（确保 `C:\ffmpeg\ffmpeg.exe` 存在）
3. 添加到系统 PATH：
   ```powershell
   # PowerShell 管理员运行
   [Environment]::SetEnvironmentVariable("Path", "$env:Path;C:\ffmpeg", "Machine")
   ```
4. 重新打开终端，验证：`ffmpeg -version`

**方法 B：通过 Chocolatey**
```powershell
# 安装 Chocolatey（如果没有）
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装 FFmpeg
choco install ffmpeg -y
```

**方法 C：通过 Winget**
```powershell
winget install Gyan.FFmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install ffmpeg -y
```

#### 3. Whisper 模型下载（中国用户）

由于 HuggingFace 在中国访问较慢，建议预先下载模型：

```powershell
# 通过代理下载（将 10809 替换为你的代理端口）
curl.exe -L -C - -x http://127.0.0.1:10809 -o "_model_cache\faster-whisper-large-v3\model.bin" "https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/model.bin"
```

或者从网盘下载模型文件放到 `_model_cache/faster-whisper-large-v3/` 目录。

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

# 安装 PyTorch (根据你的 GPU 选择)
# RTX 50 系列需要 CUDA 12.8
pip install torch==2.9.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
# RTX 40/30 系列可用 CUDA 12.4
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# 安装项目依赖
python install.py
```

3. 启动应用

**方式一：前后端分离模式（推荐开发）**

```powershell
# 终端 1：启动后端 (需要先激活 conda 环境)
conda activate videolingo
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 或使用启动脚本
.\start_backend.ps1    # Windows PowerShell
```

```powershell
# 终端 2：启动前端
cd frontend
npm install  # 首次运行需要安装依赖
npm run dev

# 或使用启动脚本
.\start_frontend.ps1   # Windows PowerShell
```

- 前端访问：http://localhost:5173
- 后端 Swagger 文档：http://localhost:8000/docs

**方式二：传统 Streamlit 模式**

```bash
streamlit run st.py
```

## 🏗️ 项目架构

```
.
├── backend/              # FastAPI 后端
│   ├── main.py           # 入口文件，配置 CORS 和路由
│   ├── api/              # API 路由
│   │   └── routes/       # video, processing, config 路由
│   ├── models/           # Pydantic 数据模型
│   └── services/         # 业务逻辑层
│
├── frontend/             # React 前端
│   ├── src/
│   │   ├── components/   # UI 组件
│   │   ├── pages/        # 页面
│   │   ├── hooks/        # React Hooks
│   │   ├── services/     # API 调用封装
│   │   ├── i18n/         # 国际化
│   │   └── types/        # TypeScript 类型
│   └── package.json
│
├── core/                 # 核心处理模块（共享）
│   ├── _1_ytdlp.py       # YouTube 下载
│   ├── _2_asr.py         # 语音识别
│   ├── _3_*.py           # NLP 分句
│   ├── _4_*.py           # 翻译
│   ├── _5_*.py - _7_*.py # 字幕处理
│   └── _8_*.py - _12_*.py # 配音处理
│
├── config.yaml           # 应用配置
└── output/               # 输出目录
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

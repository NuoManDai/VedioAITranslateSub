# Video AI Translate Sub

一站式视频翻译、本地化和配音工具，生成 Netflix 级别的字幕质量。

> 🙏 本项目基于 [VideoLingo](https://github.com/Huanshere/VideoLingo) 进行二次开发，感谢原作者的开源贡献！

## 🌟 功能特性

- 🎥 通过 yt-dlp 下载 YouTube 视频
- **🎙️ WhisperX 词级识别和低幻觉字幕**
- **📝 NLP 和 AI 驱动的字幕分割**
- **📚 自定义 + AI 生成术语表，保证翻译一致性**
- **🔄 三步翻译-反思-调整流程，达到影视级质量**
- **✅ Netflix 标准单行字幕**
- **🗣️ 支持 GPT-SoVITS、Azure、OpenAI、Fish TTS 等多种配音方案**
- 🚀 FastAPI + React 现代前后端架构
- 🌍 多语言界面支持（中/英/日/韩等）
- 📝 详细日志和进度恢复
- 🎨 支持语音克隆（Fish TTS、CosyVoice2、F5-TTS）

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

### 安装方式

#### 方式一：离线环境包安装（推荐 Windows 用户）

适合网络环境较差或希望快速部署的用户，无需联网下载依赖。

1. **下载环境包**
   - Windows x64: [videolingo_env_win64.tar.gz](https://your-cdn-domain.com/videolingo_env_win64.tar.gz) (~5GB)

2. **解压并激活**
   ```powershell
   # 克隆项目
   git clone https://github.com/NuoManDai/VedioAITranslateSub.git
   cd VedioAITranslateSub
   
   # 解压环境包（将下载的文件放到项目目录）
   mkdir videolingo_env
   tar -xzf videolingo_env_win64.tar.gz -C videolingo_env
   
   # 激活环境
   .\videolingo_env\Scripts\activate.bat
   
   # 修复环境路径（首次使用必须执行）
   conda-unpack
   ```

3. **启动应用**（见下方启动步骤）

#### 方式二：从源码安装

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
pip install -r requirements.txt
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

## 🏗️ 项目架构

```
.
├── backend/                  # FastAPI 后端
│   ├── main.py               # 入口文件，配置 CORS 和路由
│   ├── api/routes/           # API 路由
│   │   ├── video.py          # 视频上传/下载接口
│   │   ├── processing.py     # 处理流程控制
│   │   ├── config.py         # 配置管理
│   │   └── logs.py           # 日志查询
│   ├── models/               # Pydantic 数据模型
│   └── services/             # 业务逻辑层
│
├── frontend/                 # React + TypeScript 前端
│   └── src/
│       ├── components/       # UI 组件
│       │   ├── settings/     # 设置弹窗组件
│       │   ├── VideoUpload.tsx
│       │   ├── YouTubeDownload.tsx
│       │   ├── ProcessingPanel.tsx
│       │   └── ConsolePanel.tsx
│       ├── pages/            # 页面
│       ├── hooks/            # React Hooks
│       ├── services/         # API 调用封装
│       └── i18n/             # 国际化
│
├── core/                     # 核心处理模块
│   ├── _1_ytdlp.py           # YouTube 下载
│   ├── _2_asr.py             # 语音识别 (WhisperX)
│   ├── _3_1_split_nlp.py     # NLP 分句
│   ├── _3_2_split_meaning.py # 语义分句
│   ├── _4_1_summarize.py     # 内容摘要
│   ├── _4_2_translate.py     # AI 翻译
│   ├── _5_split_sub.py       # 字幕分割
│   ├── _6_gen_sub.py         # 生成字幕
│   ├── _7_sub_into_vid.py    # 字幕合成
│   ├── _8_1_audio_task.py    # 音频任务规划
│   ├── _8_2_dub_chunks.py    # 分段配音
│   ├── _9_refer_audio.py     # 参考音频处理
│   ├── _10_gen_audio.py      # 生成配音
│   ├── _11_merge_audio.py    # 合并音频
│   ├── _12_dub_to_vid.py     # 配音合成视频
│   ├── asr_backend/          # ASR 后端实现
│   └── tts_backend/          # TTS 后端实现
│
├── batch/                    # 批量处理模块
│   └── utils/batch_processor.py
│
├── config.yaml               # 应用配置
├── requirements.txt          # Python 依赖
├── environment.yml           # Conda 环境配置
└── output/                   # 输出目录
```

### Docker

也可以使用 Docker 部署（需要 NVIDIA GPU 和 Docker 支持）：

**前置要求：**
- NVIDIA Driver 版本 >= 550
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

**构建和运行：**

```bash
# 构建镜像
docker build -t video-ai-translate .

# 运行容器（后端 API）
docker run -d \
  --name videolingo \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/config.yaml:/app/config.yaml \
  video-ai-translate

# 查看日志
docker logs -f videolingo
```

**访问：**
- 后端 API：http://localhost:8000
- Swagger 文档：http://localhost:8000/docs

> 💡 前端需要单独运行 `npm run dev` 或部署静态文件

## API 配置

### API Key 获取

#### 302.AI（推荐）

[302.AI](https://302.ai) 是一站式 AI API 聚合平台，提供多种 AI 模型的统一调用接口。

**注册申请：**
1. 访问 [302.AI 官网](https://302.ai) 注册账号
2. 进入控制台 → [API 管理](https://302.ai/apis/) 创建 API Key
3. 充值后即可使用所有支持的模型

**支持的服务：**
- LLM：Claude、GPT-4、Deepseek、Gemini 等
- TTS：OpenAI TTS、Azure TTS、Fish TTS、F5-TTS
- 语音识别：Cloud Whisper

#### SiliconFlow（硅基流动）

[SiliconFlow](https://siliconflow.cn) 提供国产 AI 模型服务。

**注册申请：**
1. 访问 [SiliconFlow 官网](https://siliconflow.cn) 注册
2. 进入 [API 密钥管理](https://cloud.siliconflow.cn/account/ak) 创建 Key

**支持的服务：**
- TTS：Fish TTS（语音克隆）、CosyVoice2（语音克隆）

### API Key 来源汇总

| 类型 | 服务 | 厂商 | 获取 API Key |
|------|------|------|-------------|
| **LLM** | claude, gpt-4, deepseek, gemini 等 | [302.AI](https://302.ai) | 302.ai 中转，支持 OpenAI-Like 格式 |
| **语音识别** | Cloud Whisper | [302.AI](https://302.ai) | 可选，默认使用本地 WhisperX |
| **TTS** | OpenAI TTS | [302.AI](https://302.ai) | 302.ai 中转 |
| **TTS** | Azure TTS | [302.AI](https://302.ai) | 302.ai 中转 |
| **TTS** | Fish TTS | [302.AI](https://302.ai) | 302.ai 中转，支持语音克隆 |
| **TTS** | F5-TTS | [302.AI](https://302.ai) | 302.ai 中转，支持语音克隆 |
| **TTS** | SiliconFlow Fish TTS | [SiliconFlow](https://siliconflow.cn) | 直连，支持语音克隆 |
| **TTS** | SiliconFlow CosyVoice2 | [SiliconFlow](https://siliconflow.cn) | 直连，支持语音克隆 |
| **TTS** | Edge TTS | 微软 | 免费，无需 API Key |
| **TTS** | GPT-SoVITS | 本地 | 需自建服务，支持语音克隆 |
| **TTS** | Custom TTS | 自定义 | 自定义接口 |

### 支持的模型

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

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 🔗 参考项目

本项目的实现参考了以下开源项目和服务：

### 核心项目

| 项目 | 说明 |
|------|------|
| [VideoLingo](https://github.com/Huanshere/VideoLingo) | 本项目的基础框架，提供了完整的视频翻译工作流 |
| [WhisperX](https://github.com/m-bain/whisperx) | 高精度语音识别，支持词级时间戳 |
| [Demucs](https://github.com/adefossez/demucs) | Meta 开源的人声分离工具 |

### AI 服务商

| 服务商 | 说明 |
|--------|------|
| [302.AI](https://302.ai) | AI API 聚合平台，提供 LLM、TTS、Whisper 等服务 |
| [SiliconFlow](https://siliconflow.cn) | 硅基流动，提供 Fish TTS、CosyVoice2 语音合成 |
| [OpenAI](https://openai.com) | GPT 系列模型 |
| [Anthropic](https://anthropic.com) | Claude 系列模型 |
| [Fish Audio](https://fish.audio) | Fish TTS 语音合成 |

### 开源框架

| 框架 | 用途 |
|------|------|
| [FastAPI](https://fastapi.tiangolo.com) | 后端 API 框架 |
| [React](https://react.dev) | 前端 UI 框架 |
| [Ant Design](https://ant.design) | UI 组件库 |
| [Vite](https://vitejs.dev) | 前端构建工具 |
| [PyTorch](https://pytorch.org) | 深度学习框架 |

# Backend 环境安装指南

## 环境信息

- **Python 版本**: 3.10.0
- **PyTorch 版本**: 2.9.1+cu128
- **CUDA 版本**: 12.8
- **Conda 环境名**: videolingo

## 快速安装

### 1. 创建 Python 环境 (推荐 Python 3.10)

```bash
# 使用 conda
conda create -n videolingo python=3.10 -y
conda activate videolingo

# 或使用 venv
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
```

### 2. 安装 PyTorch (根据你的 GPU 选择)

```bash
# RTX 50 系列 (5080/5090) - 需要 PyTorch 2.9+ 和 CUDA 12.8
pip install torch==2.9.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# RTX 40 系列 (4090/4080等) - PyTorch 2.x + CUDA 12.4
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# RTX 30 系列 (3090/3080等) - PyTorch 2.x + CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CPU only
pip install torch torchvision torchaudio
```

### 3. 安装项目依赖

```bash
# 安装根目录的核心依赖
pip install -r requirements.txt

# 安装后端依赖
pip install -r backend/requirements.txt
```

### 4. 安装额外依赖 (PyTorch 2.9+ 需要)

```bash
# torchcodec (torchaudio 2.9+ 的依赖)
pip install torchcodec
```

## 核心依赖列表

### 后端 API
- fastapi>=0.109.0
- uvicorn[standard]>=0.27.0
- python-multipart>=0.0.6
- aiofiles>=23.2.1
- httpx>=0.25.0

### 视频/音频处理
- opencv-python>=4.8.0
- soundfile>=0.12.0
- pydub>=0.25.1
- ffmpeg (系统级安装)

### AI/ML
- torch>=2.0.0 (RTX 50系列需要 >=2.9.0)
- torchaudio>=2.0.0
- torchvision>=0.15.0
- whisperx (语音识别)
- demucs (音频分离)

## 验证安装

```bash
# 验证 PyTorch + CUDA
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

# 启动后端服务
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# 或使用启动脚本（在项目根目录）
.\start_backend.ps1    # Windows PowerShell
```

## 快速启动命令

### Windows (推荐)

```powershell
# 方式一：使用启动脚本
.\start_backend.ps1

# 方式二：手动启动
conda activate videolingo
cd backend
D:\conda_data\envs\videolingo\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Linux/macOS

```bash
conda activate videolingo
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 常见问题

### 1. CUDA 架构不匹配错误
```
FATAL: this function is for sm80, but was built for sm120
```
**解决**: 升级 PyTorch 到支持你 GPU 的版本（RTX 50系列需要 PyTorch 2.9+）

### 2. torchcodec 错误
```
TorchCodec is required for load_with_torchcodec
```
**解决**: `pip install torchcodec`

### 3. FFmpeg 未找到
**解决**: 确保 FFmpeg 在系统 PATH 中，或通过 conda 安装：
```bash
conda install -c conda-forge ffmpeg
```

## 核心依赖版本（当前环境）

| 包名 | 版本 |
|-----|------|
| Python | 3.10.0 |
| PyTorch | 2.9.1+cu128 |
| torchaudio | 2.9.1+cu128 |
| torchvision | (随 torch 安装) |
| torchcodec | 0.9.1 |
| FastAPI | 0.128.0 |
| uvicorn | 0.40.0 |
| whisperx | git+https://github.com/m-bain/whisperX.git |
| demucs | git+https://github.com/adefossez/demucs.git |
| faster-whisper | 1.2.1 |
| openai | 1.55.3 |
| spacy | 3.8.11 |
| moviepy | 1.0.3 |
| pydub | 0.25.1 |
| opencv-python | 4.10.0.84 |

完整依赖列表见 `pip-packages.txt`

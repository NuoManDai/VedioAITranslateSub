# VedioAITranslateSub Development Guidelines

Auto-generated from feature plans. Last updated: 2026-01-17

## Active Technologies
- Python 3.10+ (backend), TypeScript 5.3+ (frontend) + FastAPI 0.109+, uvicorn, React 18, Ant Design 5.12, Vite 5 (002-dubbing-subtitle-separation)
- 文件系统 (output/, gpt_log/, log/ 目录), config.yaml (002-dubbing-subtitle-separation)

### Backend (Python 3.10)
- FastAPI ^0.109.0 (REST API 框架)
- Uvicorn ^0.27.0 (ASGI 服务器)
- python-multipart ^0.0.6 (文件上传)
- 继承自 VideoLingo 的所有依赖 (requirements.txt)

### Frontend (TypeScript 5.x)
- React 18 + Vite 5 (UI 框架 + 构建工具)
- TailwindCSS 3.x (样式框架)
- Ant Design 5.x (UI 组件库)
- react-i18next (国际化)

### Existing Core (保持不变)
- WhisperX (ASR)
- 多种 TTS 后端 (Azure, OpenAI, Fish, Edge 等)
- OpenAI-compatible LLM API

## Project Structure

```text
backend/
├── main.py                 # FastAPI 入口
├── api/routes/             # API 路由
├── models/                 # Pydantic 数据模型
└── services/               # 业务逻辑

frontend/
├── src/
│   ├── components/         # React 组件
│   ├── pages/              # 页面
│   ├── services/           # API 调用
│   ├── hooks/              # 自定义 hooks
│   └── i18n/               # 国际化

core/                       # 视频处理管道（不修改）
config.yaml                 # 配置文件
output/                     # 输出目录
translations/               # 翻译文件
```

## Commands

```bash
# 后端
conda activate videolingo
cd backend && uvicorn main:app --reload --port 8000

# 前端
cd frontend && npm run dev

# 测试
cd backend && pytest
cd frontend && npm run test
```

## Code Style

- Python: PEP 8, 使用类型注解, Pydantic 模型
- TypeScript: 严格模式, 使用 interface 定义类型
- React: 函数组件 + Hooks, 避免 class 组件
- 样式: Ant Design 用于复杂组件, TailwindCSS 用于布局

## Key Conventions

1. API 路由前缀: `/api/`
2. 进度轮询间隔: 2 秒
3. 文件上传: 无大小限制
4. 国际化: 复用 `translations/*.json`
5. 配置: 通过 `config.yaml` 持久化

## Constitution Principles

1. **Pipeline Integrity**: 调用现有 core 模块，不修改管道逻辑
2. **Quality-First Translation**: 翻译逻辑不变，仅 UI 层重构
3. **Modular Backend**: 保持 ASR/TTS/LLM 模块可替换
4. **Configuration Transparency**: 通过 API 读写 config.yaml
5. **Internationalization**: 复用 translations/*.json

## Recent Changes
- 002-dubbing-subtitle-separation: Added Python 3.10+ (backend), TypeScript 5.3+ (frontend) + FastAPI 0.109+, uvicorn, React 18, Ant Design 5.12, Vite 5

- 001-fastapi-react-refactor: 前后端分离重构
  - 后端: Python 3.10 + FastAPI
  - 前端: React + TypeScript + TailwindCSS + Ant Design

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

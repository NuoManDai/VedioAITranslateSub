# Implementation Plan: 前后端分离重构

**Branch**: `001-fastapi-react-refactor` | **Date**: 2026-01-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-fastapi-react-refactor/spec.md`

## Summary

将现有 VideoLingo 的 Streamlit 单体应用重构为前后端分离架构：后端使用 FastAPI 提供 RESTful API（含 Swagger 文档），前端使用 React + TypeScript + TailwindCSS + Ant Design 构建现代化 UI。保持与现有 `core/` 处理模块的兼容性，使用 conda 虚拟环境管理依赖。

## Technical Context

**Language/Version**: Python 3.10 (后端), TypeScript 5.x (前端)  
**Primary Dependencies**: FastAPI, Uvicorn, python-multipart (后端); React 18, Vite, TailwindCSS 3.x, Ant Design 5.x (前端)  
**Storage**: 文件系统 (`output/` 目录), YAML 配置文件 (`config.yaml`)  
**Testing**: pytest (后端), Vitest (前端)  
**Target Platform**: Windows/Linux/macOS 桌面浏览器  
**Project Type**: Web application (frontend + backend)  
**Performance Goals**: 前端首次加载 <3s, 进度轮询间隔 2s  
**Constraints**: 无文件大小限制, 单用户本地运行, 禁止全局 pip 安装  
**Scale/Scope**: 单用户, 单视频处理

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate (Phase 0)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Pipeline Integrity | ✅ PASS | 后端 API 调用现有 `core/` 模块，不修改管道逻辑 |
| II. Quality-First Translation | ✅ PASS | 翻译逻辑不变，仅 UI 层重构 |
| III. Modular Backend Architecture | ✅ PASS | 后端保持调用现有 ASR/TTS/LLM 模块接口 |
| IV. Configuration Transparency | ✅ PASS | 后端 API 读写 `config.yaml`，前端通过设置模态框暴露配置 |
| V. Internationalization Compliance | ✅ PASS | 前端复用 `translations/*.json`，不硬编码字符串 |

**Pre-Research Gate Result**: ✅ ALL PASSED - 可进入 Phase 0

### Post-Design Re-check (Phase 1)

| Principle | Status | Verification |
|-----------|--------|--------------|
| I. Pipeline Integrity | ✅ PASS | `ProcessingService` 按顺序调用 `_1_ytdlp` → `_12_dub_to_vid`，通过 `ProcessingStage` 模型记录每阶段状态 |
| II. Quality-First Translation | ✅ PASS | 翻译流程不变：`_4_1_summarize` → `_4_2_translate`，保持 3 步翻译 |
| III. Modular Backend Architecture | ✅ PASS | API 契约不依赖具体后端实现，`tts_method` 配置可切换 TTS 后端 |
| IV. Configuration Transparency | ✅ PASS | `/api/config` 端点暴露完整配置，`SettingsModal` 组件覆盖所有选项 |
| V. Internationalization Compliance | ✅ PASS | `frontend/src/i18n/` 加载 `translations/*.json`，所有 UI 文本使用 `t()` 函数 |

**Post-Design Gate Result**: ✅ ALL PASSED - 设计符合 Constitution

## Project Structure

### Documentation (this feature)

```text
specs/001-fastapi-react-refactor/
├── plan.md              # 本文件
├── spec.md              # 功能规范
├── research.md          # Phase 0 研究输出
├── data-model.md        # Phase 1 数据模型
├── quickstart.md        # Phase 1 快速启动指南
├── contracts/           # Phase 1 API 契约
│   └── openapi.yaml
├── checklists/          # 检查清单
│   └── requirements.md
└── environment-setup.md # 环境配置指南
```

### Source Code (repository root)

```text
backend/
├── main.py                 # FastAPI 应用入口
├── requirements.txt        # 后端依赖 (引用 ../requirements.txt)
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── video.py        # 视频上传/下载 API
│   │   ├── processing.py   # 字幕/配音处理 API
│   │   └── config.py       # 配置读写 API
│   └── deps.py             # 依赖注入
├── models/
│   ├── __init__.py
│   ├── video.py            # Video 数据模型
│   ├── job.py              # ProcessingJob 数据模型
│   └── config.py           # Configuration 数据模型
├── services/
│   ├── __init__.py
│   ├── video_service.py    # 视频业务逻辑
│   ├── processing_service.py # 处理流程业务逻辑
│   └── config_service.py   # 配置业务逻辑
└── tests/
    ├── __init__.py
    ├── test_video_api.py
    └── test_processing_api.py

frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── index.html
├── public/
│   └── favicon.ico
├── src/
│   ├── main.tsx            # React 入口
│   ├── App.tsx             # 主组件
│   ├── vite-env.d.ts
│   ├── components/
│   │   ├── VideoUpload.tsx     # 视频上传组件
│   │   ├── YouTubeDownload.tsx # YouTube 下载组件
│   │   ├── VideoPlayer.tsx     # 视频播放器
│   │   ├── ProcessingPanel.tsx # 处理进度面板
│   │   ├── SettingsModal.tsx   # 设置模态框
│   │   └── LanguageSwitch.tsx  # 语言切换
│   ├── pages/
│   │   └── Home.tsx            # 首页
│   ├── services/
│   │   ├── api.ts              # API 调用封装
│   │   └── polling.ts          # 轮询逻辑
│   ├── hooks/
│   │   ├── useProcessingStatus.ts
│   │   └── useConfig.ts
│   ├── i18n/
│   │   ├── index.ts            # i18n 配置
│   │   └── locales/            # 复制自 translations/*.json
│   ├── types/
│   │   └── index.ts            # TypeScript 类型定义
│   └── styles/
│       └── globals.css         # TailwindCSS 入口
└── tests/
    └── components/

core/                       # 保持不变
config.yaml                 # 保持不变
translations/               # 保持不变
output/                     # 保持不变
```

**Structure Decision**: 选择 Option 2 (Web application) - 前后端完全分离，`backend/` 和 `frontend/` 目录独立，各自有独立的依赖管理和测试结构。

## Complexity Tracking

无 Constitution 违规，无需记录复杂性理由。

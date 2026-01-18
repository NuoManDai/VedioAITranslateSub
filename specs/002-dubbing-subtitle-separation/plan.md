# Implementation Plan: 字幕配音分离与日语支持优化

**Branch**: `002-dubbing-subtitle-separation` | **Date**: 2026-01-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-dubbing-subtitle-separation/spec.md`

## Summary

优化视频处理流程，实现字幕处理和配音处理的完全分离，添加日语 NLP 分句支持，增强处理状态恢复能力，并提供文件预览和清理功能。

## Technical Context

**Language/Version**: Python 3.10 (后端), TypeScript 5.x (前端)  
**Primary Dependencies**: FastAPI, spaCy (ja_core_news_md), pandas (后端); React 18, Ant Design 5.x (前端)  
**Storage**: 文件系统 (`output/` 目录), YAML 配置文件 (`config.yaml`)  
**Testing**: 手动测试（日语视频处理流程）  
**Target Platform**: Windows/Linux/macOS 桌面浏览器  
**Project Type**: Web application (frontend + backend)  
**Constraints**: 日语 ASR 输出无标点，需要基于时间间隔分句  
**Scale/Scope**: 单用户, 单视频处理

## Constitution Check

*GATE: Must pass before implementation.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Pipeline Integrity | ✅ PASS | 日语分句逻辑独立于现有流程，不修改核心管道 |
| II. Quality-First Translation | ✅ PASS | 翻译逻辑不变，分句优化提高翻译输入质量 |
| III. Modular Backend Architecture | ✅ PASS | 新功能通过独立服务和 API 端点实现 |
| IV. Configuration Transparency | ✅ PASS | 清理操作通过明确的 API 端点，不影响配置 |
| V. Internationalization Compliance | ✅ PASS | 前端新组件使用 `t()` 函数国际化 |

**Gate Result**: ✅ ALL PASSED - 可进入实现阶段

## Project Structure

### Documentation (this feature)

```text
specs/002-dubbing-subtitle-separation/
├── plan.md              # 本文件
├── spec.md              # 功能规范
├── research.md          # 研究输出
├── tasks.md             # 任务清单
├── data-model.md        # 数据模型
└── checklists/          # 检查清单
    └── requirements.md
```

### Source Code Changes

```text
backend/
├── api/routes/
│   ├── files.py         # [NEW] 文件预览 API
│   └── logs.py          # [NEW] 日志 API
├── models/
│   ├── log.py           # [NEW] 日志模型
│   ├── tts_config.py    # [NEW] TTS 配置模型
│   └── stage.py         # [MODIFIED] 扩展阶段输出文件映射
├── services/
│   ├── log_service.py   # [NEW] 日志服务
│   ├── tts_service.py   # [NEW] TTS 服务
│   └── processing_service.py # [MODIFIED] 状态恢复逻辑

core/
└── spacy_utils/
    └── split_by_mark.py # [MODIFIED] 添加日语分句逻辑

frontend/
├── src/components/
│   ├── ConsolePanel.tsx      # [NEW] 控制台面板
│   ├── StageOutputFiles.tsx  # [NEW] 阶段输出文件
│   ├── ProcessingPanel.tsx   # [MODIFIED] Tab 布局
│   ├── VideoPlayer.tsx       # [MODIFIED] 字幕切换
│   └── settings/             # [NEW] 设置组件拆分
│       ├── BasicSettings.tsx
│       ├── TranslationSettings.tsx
│       └── TTSSettings.tsx
```

## Implementation Phases

### Phase 1: 日语 NLP 分句支持
- 分析 WhisperX 日语 ASR 输出格式
- 实现基于时间间隔的分句逻辑
- 添加日语语法模式检测

### Phase 2: 处理状态恢复
- 定义阶段输出文件映射
- 实现完成状态检测
- 添加状态恢复 API

### Phase 3: 文件预览与清理
- 实现文件列表 API
- 实现文件预览 API
- 实现清理 API

### Phase 4: UI 优化
- Tab 布局重构
- 控制台面板
- 字幕切换功能

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 日语分句不准确 | Medium | Medium | 设置合理的时间阈值，依赖后续 LLM 分割 |
| 状态恢复不完整 | Low | Low | 检测多个输出文件确认完成状态 |
| 清理操作误删 | Low | High | 明确区分字幕/配音文件，提供确认提示 |

## Dependencies

- spaCy `ja_core_news_md` 模型（日语 NLP）
- WhisperX wav2vec2 模型（日语 ASR 字符级对齐）
- pandas（数据处理）

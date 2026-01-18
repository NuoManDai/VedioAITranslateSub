# Tasks: 字幕配音分离与日语支持优化

**Input**: Design documents from `/specs/002-dubbing-subtitle-separation/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 任务所属用户故事

---

## Phase 1: 日语 NLP 分句支持

**Goal**: 解决日语 ASR 输出无标点导致无法分句的问题

- [x] T001 分析 WhisperX 日语 ASR 输出格式 `output/log/cleaned_chunks.xlsx`
- [x] T002 研究 spaCy 日语句子边界检测机制
- [x] T003 实现 `split_japanese_by_time_and_grammar()` 函数 `core/spacy_utils/split_by_mark.py`
- [x] T004 集成日语分句到主处理流程 `core/_3_1_split_nlp.py`
- [x] T005 测试日语视频分句效果

**Checkpoint**: 日语视频可以正确分句（约 15-30 句/分钟）

---

## Phase 2: 处理状态恢复

**Goal**: 支持从已完成的输出文件恢复处理状态

- [x] T006 定义阶段输出文件映射 `backend/models/stage.py` - `STAGE_OUTPUT_FILES`
- [x] T007 实现 `detect_completed_stages()` `backend/services/processing_service.py`
- [x] T008 实现 `is_subtitle_processing_completed()` `backend/services/processing_service.py`
- [x] T009 实现 `is_dubbing_processing_completed()` `backend/services/processing_service.py`
- [x] T010 实现 `restore_job_state()` `backend/services/processing_service.py`
- [x] T011 添加状态恢复 API `backend/api/routes/processing.py` - GET `/api/processing/restore`

**Checkpoint**: 重启应用后可以正确恢复处理状态

---

## Phase 3: 文件预览与清理 API

**Goal**: 提供文件预览和清理功能

### 文件预览 API
- [x] T012 [P] 创建文件路由 `backend/api/routes/files.py`
- [x] T013 [P] 实现阶段输出文件列表 API - GET `/api/files/stage/{stage_name}`
- [x] T014 [P] 实现文件预览 API - GET `/api/files/preview`
- [x] T015 [P] 实现文件下载 API - GET `/api/files/download`
- [x] T016 [P] 实现文件夹列表 API - GET `/api/files/folder`

### 清理 API
- [x] T017 实现字幕清理 API - POST `/api/processing/cleanup/subtitle`
- [x] T018 实现配音清理 API - POST `/api/processing/cleanup/dubbing`
- [x] T019 实现全部清理 API - POST `/api/processing/cleanup/all`

**Checkpoint**: 可以预览处理输出文件，可以清理中间文件

---

## Phase 4: 日志服务

**Goal**: 提供实时日志监控功能

- [x] T020 创建日志模型 `backend/models/log.py`
- [x] T021 创建日志服务 `backend/services/log_service.py`
- [x] T022 创建日志路由 `backend/api/routes/logs.py`
- [x] T023 实现日志 API - GET `/api/logs`
- [x] T024 实现日志清空 API - DELETE `/api/logs`

**Checkpoint**: 前端可以获取实时处理日志

---

## Phase 5: TTS 服务扩展

**Goal**: 增强 TTS 配置管理

- [x] T025 创建 TTS 配置模型 `backend/models/tts_config.py`
- [x] T026 创建 TTS 服务 `backend/services/tts_service.py`
- [x] T027 添加 TTS 配置 API

**Checkpoint**: 可以通过 API 配置 TTS 参数

---

## Phase 6: 前端 UI 优化

**Goal**: 优化处理界面交互

### ProcessingPanel 重构
- [x] T028 重构 ProcessingPanel 为 Tab 布局 `frontend/src/components/ProcessingPanel.tsx`
- [x] T029 分离字幕处理 Tab
- [x] T030 分离配音处理 Tab
- [x] T031 添加重启/清理按钮

### 控制台面板
- [x] T032 [P] 创建 ConsolePanel 组件 `frontend/src/components/ConsolePanel.tsx`
- [x] T033 [P] 实现日志过滤（按级别、来源）
- [x] T034 [P] 实现自动滚动和全屏模式

### 文件预览组件
- [x] T035 [P] 创建 StageOutputFiles 组件 `frontend/src/components/StageOutputFiles.tsx`
- [x] T036 [P] 实现文件列表展示
- [x] T037 [P] 实现文件内容预览（JSON、文本、SRT）

### 视频播放器增强
- [x] T038 添加字幕切换开关 `frontend/src/components/VideoPlayer.tsx`

### 设置组件拆分
- [x] T039 [P] 创建 BasicSettings 组件 `frontend/src/components/settings/BasicSettings.tsx`
- [x] T040 [P] 创建 TranslationSettings 组件 `frontend/src/components/settings/TranslationSettings.tsx`
- [x] T041 [P] 创建 TTSSettings 组件 `frontend/src/components/settings/TTSSettings.tsx`
- [x] T042 重构 SettingsModal 使用拆分组件 `frontend/src/components/SettingsModal.tsx`

**Checkpoint**: UI 交互流畅，功能完整

---

## Phase 7: 清理旧代码

**Goal**: 移除不再使用的 Streamlit 相关代码

- [x] T043 删除 `st.py`
- [x] T044 删除 `install.py`
- [x] T045 删除 `translations/*.json`（已移至 frontend/src/i18n）
- [x] T046 删除 `core/st_utils/` 目录

**Checkpoint**: 代码库干净，无冗余文件

---

## Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: 日语 NLP | T001-T005 | ✅ Done |
| Phase 2: 状态恢复 | T006-T011 | ✅ Done |
| Phase 3: 文件 API | T012-T019 | ✅ Done |
| Phase 4: 日志服务 | T020-T024 | ✅ Done |
| Phase 5: TTS 服务 | T025-T027 | ✅ Done |
| Phase 6: UI 优化 | T028-T042 | ✅ Done |
| Phase 7: 代码清理 | T043-T046 | ✅ Done |

**Total**: 46 tasks completed

# Tasks: 前后端分离重构

**Input**: Design documents from `/specs/001-fastapi-react-refactor/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/openapi.yaml ✅

**Tests**: 本功能未明确要求测试，因此任务列表不包含测试任务。如需 TDD 方式开发，可后续添加。

**Organization**: 任务按用户故事分组，支持独立实现和测试每个故事。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 任务所属用户故事（如 US1, US2, US3）
- 描述中包含确切文件路径

## Path Conventions

- **后端**: `backend/` 目录
- **前端**: `frontend/` 目录
- **核心模块**: `core/` 目录（保持不变）

---

## Phase 1: Setup (共享基础设施)

**Purpose**: 项目初始化和基本结构

- [x] T001 创建后端目录结构 `backend/api/routes/`, `backend/models/`, `backend/services/`
- [x] T002 创建前端目录结构 `frontend/src/components/`, `frontend/src/pages/`, `frontend/src/services/`, `frontend/src/hooks/`, `frontend/src/i18n/`, `frontend/src/types/`, `frontend/src/styles/`
- [x] T003 [P] 创建后端 FastAPI 入口文件 `backend/main.py`，配置 CORS 和 Swagger 文档
- [x] T004 [P] 创建后端依赖文件 `backend/requirements.txt`，引用根目录 requirements.txt 并添加 FastAPI 依赖
- [x] T005 [P] 初始化前端 Vite + React + TypeScript 项目 `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`
- [x] T006 [P] 配置 TailwindCSS `frontend/tailwind.config.js`, `frontend/src/styles/globals.css`
- [x] T007 [P] 安装并配置 Ant Design `frontend/package.json` 添加依赖
- [x] T008 复制翻译文件到前端 `frontend/src/i18n/locales/` 从 `translations/*.json`

---

## Phase 2: Foundational (阻塞性前置条件)

**Purpose**: 所有用户故事实现前必须完成的核心基础设施

**⚠️ CRITICAL**: 此阶段完成前，不能开始任何用户故事的工作

- [x] T009 创建 Video 数据模型 `backend/models/video.py`（Pydantic 模型）
- [x] T010 创建 ProcessingStage 数据模型 `backend/models/stage.py`（Pydantic 模型）
- [x] T011 创建 ProcessingJob 数据模型 `backend/models/job.py`（Pydantic 模型）
- [x] T012 创建 Configuration 数据模型 `backend/models/config.py`（Pydantic 模型，映射 config.yaml）
- [x] T013 [P] 创建 TypeScript 类型定义 `frontend/src/types/index.ts`（Video, ProcessingJob, ProcessingStage, Configuration）
- [x] T014 [P] 创建 API 路由初始化 `backend/api/__init__.py`, `backend/api/routes/__init__.py`
- [x] T015 [P] 创建依赖注入模块 `backend/api/deps.py`
- [x] T016 [P] 创建服务层初始化 `backend/services/__init__.py`
- [x] T017 [P] 创建 API 调用封装 `frontend/src/services/api.ts`（基础 fetch 封装）
- [x] T018 配置 react-i18next `frontend/src/i18n/index.ts`（加载 locales 目录翻译文件）
- [x] T019 创建前端入口和主组件 `frontend/src/main.tsx`, `frontend/src/App.tsx`（集成 i18n 和 Ant Design ConfigProvider）
- [x] T020 创建 HTML 入口 `frontend/index.html` 并更新标题为 "VedioAITranslateSub"

**Checkpoint**: 基础设施就绪 - 可以开始并行实现用户故事

---

## Phase 3: User Story 1 - 视频上传与下载 (Priority: P1) 🎯 MVP

**Goal**: 用户可以上传本地视频或下载 YouTube 视频，并预览

**Independent Test**: 上传一个视频文件或输入 YouTube 链接下载，成功后视频预览可用

### 后端 API 实现

- [x] T021 [US1] 实现视频上传 API `backend/api/routes/video.py` - POST `/api/video/upload`
- [x] T022 [US1] 实现 YouTube 下载 API `backend/api/routes/video.py` - POST `/api/video/youtube`（调用 core/_1_ytdlp.py）
- [x] T023 [US1] 实现获取当前视频 API `backend/api/routes/video.py` - GET `/api/video/current`
- [x] T024 [US1] 实现删除视频 API `backend/api/routes/video.py` - DELETE `/api/video/current`
- [x] T025 [US1] 实现视频流 API `backend/api/routes/video.py` - GET `/api/video/stream/{filename}`
- [x] T026 [US1] 创建 VideoService `backend/services/video_service.py`（视频上传、下载、删除业务逻辑）

### 前端组件实现

- [x] T027 [P] [US1] 创建视频上传组件 `frontend/src/components/VideoUpload.tsx`（拖拽上传，使用 Ant Design Upload）
- [x] T028 [P] [US1] 创建 YouTube 下载组件 `frontend/src/components/YouTubeDownload.tsx`（URL 输入框 + 下载按钮）
- [x] T029 [P] [US1] 创建视频播放器组件 `frontend/src/components/VideoPlayer.tsx`（HTML5 video 播放器）
- [x] T030 [US1] 创建首页 `frontend/src/pages/Home.tsx`（整合上传、下载、播放器组件）
- [x] T031 [US1] 在 App.tsx 中添加路由，渲染 Home 页面

**Checkpoint**: 用户故事 1 应该可以完整独立测试 - 视频上传/下载/预览功能可用

---

## Phase 4: User Story 2 - 字幕处理流程 (Priority: P1) 🎯 MVP

**Goal**: 用户可以对上传的视频执行字幕处理，查看各阶段进度

**Independent Test**: 上传视频后点击开始处理，观察各阶段进度更新，最终生成带字幕视频

### 后端 API 实现

- [x] T032 [US2] 实现开始字幕处理 API `backend/api/routes/processing.py` - POST `/api/processing/subtitle/start`
- [x] T033 [US2] 实现获取处理状态 API `backend/api/routes/processing.py` - GET `/api/processing/status`
- [x] T034 [US2] 实现取消处理 API `backend/api/routes/processing.py` - POST `/api/processing/cancel`
- [x] T035 [US2] 实现下载字幕 API `backend/api/routes/processing.py` - GET `/api/processing/download/srt`
- [x] T036 [US2] 创建 ProcessingService `backend/services/processing_service.py`（字幕处理流程，调用 core/_2_asr 至 _7_sub_into_vid）

### 前端组件实现

- [x] T037 [P] [US2] 创建处理进度面板组件 `frontend/src/components/ProcessingPanel.tsx`（使用 Ant Design Steps + Progress）
- [x] T038 [P] [US2] 创建进度轮询 hook `frontend/src/hooks/useProcessingStatus.ts`（2 秒间隔轮询 /api/processing/status）
- [x] T039 [P] [US2] 创建轮询服务 `frontend/src/services/polling.ts`（通用轮询逻辑封装）
- [x] T040 [US2] 在 Home 页面集成处理面板，显示字幕处理进度和下载按钮

**Checkpoint**: 用户故事 1 + 2 都应该可以独立工作 - 完整的视频上传到字幕生成流程

---

## Phase 5: User Story 3 - 配音处理流程 (Priority: P2)

**Goal**: 用户可以在字幕处理完成后执行配音流程

**Independent Test**: 字幕处理完成后点击开始配音，观察进度更新，最终生成带配音视频

### 后端 API 实现

- [x] T041 [US3] 实现开始配音处理 API `backend/api/routes/processing.py` - POST `/api/processing/dubbing/start`
- [x] T042 [US3] 扩展 ProcessingService `backend/services/processing_service.py`（配音处理流程，调用 core/_8_1_audio_task 至 _12_dub_to_vid）

### 前端组件实现

- [x] T043 [US3] 扩展处理面板组件 `frontend/src/components/ProcessingPanel.tsx`（添加配音阶段显示）
- [x] T044 [US3] 在 Home 页面添加配音开始按钮（字幕完成后显示）

**Checkpoint**: 用户故事 1 + 2 + 3 都应该可以独立工作

---

## Phase 6: User Story 4 - 设置管理 (Priority: P2)

**Goal**: 用户可以通过设置面板配置 API 密钥、语言选项、TTS 方法等

**Independent Test**: 打开设置面板，修改配置项，保存后刷新页面验证配置持久化

### 后端 API 实现

- [x] T045 [US4] 实现获取配置 API `backend/api/routes/config.py` - GET `/api/config`
- [x] T046 [US4] 实现更新配置 API `backend/api/routes/config.py` - PUT `/api/config`
- [x] T047 [US4] 实现验证 API Key API `backend/api/routes/config.py` - POST `/api/config/validate-api`
- [x] T048 [US4] 创建 ConfigService `backend/services/config_service.py`（config.yaml 读写逻辑）

### 前端组件实现

- [x] T049 [P] [US4] 创建设置模态框组件 `frontend/src/components/SettingsModal.tsx`（Ant Design Modal + Form）
- [x] T050 [P] [US4] 创建配置 hook `frontend/src/hooks/useConfig.ts`（获取和更新配置）
- [x] T051 [US4] 在 App.tsx 或 Home.tsx 添加设置按钮，点击打开设置模态框

**Checkpoint**: 用户故事 1-4 都应该可以独立工作

---

## Phase 7: User Story 5 - 多语言界面支持 (Priority: P3)

**Goal**: 前端界面支持多语言切换

**Independent Test**: 切换语言下拉菜单，验证界面所有文本正确切换

### 前端组件实现

- [x] T052 [P] [US5] 创建语言切换组件 `frontend/src/components/LanguageSwitch.tsx`（Ant Design Select 下拉菜单）
- [x] T053 [US5] 在 App.tsx 头部或侧边栏添加语言切换组件
- [x] T054 [US5] 更新所有组件使用 `t()` 函数进行国际化（VideoUpload, YouTubeDownload, ProcessingPanel, SettingsModal）
- [x] T055 [US5] 确保语言选择持久化到 localStorage

**Checkpoint**: 所有用户故事都应该可以独立工作

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 影响多个用户故事的改进

- [x] T056 [P] 添加全局错误处理 `backend/main.py`（异常处理中间件）
- [x] T057 [P] 添加请求日志 `backend/main.py`（logging 中间件）
- [x] T058 [P] 创建后端启动脚本 `start_backend.ps1` 或 `start_backend.bat`
- [x] T059 [P] 创建前端启动脚本 `start_frontend.ps1` 或 `start_frontend.bat`
- [x] T060 [P] 更新 README 文档，说明新的前后端分离架构和启动方式
- [x] T061 实现未完成任务恢复提示逻辑（检测 output/ 目录状态，提示用户继续或重新开始）
- [x] T062 优化前端首次加载性能（代码分割、懒加载）
- [x] T063 运行 quickstart.md 验证完整流程

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 - **阻塞所有用户故事**
- **User Stories (Phase 3-7)**: 全部依赖 Foundational 完成
  - US1 (P1) 和 US2 (P1) 可并行开发
  - US3 (P2) 依赖 US2 的后端 ProcessingService 结构
  - US4 (P2) 独立于其他 US
  - US5 (P3) 独立于其他 US
- **Polish (Phase 8)**: 依赖所有需要的用户故事完成

### User Story Dependencies

```
┌─────────────┐     ┌─────────────┐
│    US1      │     │    US4      │
│  视频上传   │     │  设置管理   │
└──────┬──────┘     └─────────────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│    US2      │     │    US5      │
│  字幕处理   │     │  多语言     │
└──────┬──────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│    US3      │
│  配音处理   │
└─────────────┘
```

- **User Story 1 (P1)**: Foundational 完成后可开始 - 无其他 US 依赖
- **User Story 2 (P1)**: 依赖 US1 的视频上传功能
- **User Story 3 (P2)**: 依赖 US2 的字幕处理完成
- **User Story 4 (P2)**: 独立，可与 US1-3 并行
- **User Story 5 (P3)**: 独立，可与 US1-4 并行

### Within Each User Story

- 后端 API 先于前端组件
- 服务层先于路由层
- 核心实现先于集成

### Parallel Opportunities

- Setup 阶段 T003-T008 全部可并行
- Foundational 阶段 T013-T017 可并行
- US1 的前端组件 T027-T029 可并行
- US2 的前端组件 T037-T039 可并行
- US4 的前端组件 T049-T050 可并行
- US4 和 US5 可与其他 US 完全并行

---

## Parallel Example: User Story 1

```bash
# 后端 API 完成后，可同时启动所有前端组件：
Task T027: "创建视频上传组件 frontend/src/components/VideoUpload.tsx"
Task T028: "创建 YouTube 下载组件 frontend/src/components/YouTubeDownload.tsx"
Task T029: "创建视频播放器组件 frontend/src/components/VideoPlayer.tsx"

# 组件完成后再集成：
Task T030: "创建首页 frontend/src/pages/Home.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational (**CRITICAL - 阻塞所有故事**)
3. 完成 Phase 3: User Story 1 (视频上传)
4. 完成 Phase 4: User Story 2 (字幕处理)
5. **STOP and VALIDATE**: 独立测试 US1 + US2
6. 部署/演示 MVP

### Incremental Delivery

1. 完成 Setup + Foundational → 基础就绪
2. 添加 User Story 1 → 独立测试 → 部署/演示
3. 添加 User Story 2 → 独立测试 → 部署/演示 (MVP!)
4. 添加 User Story 3 → 独立测试 → 部署/演示
5. 添加 User Story 4 → 独立测试 → 部署/演示
6. 添加 User Story 5 → 独立测试 → 部署/演示
7. 每个故事增加价值而不破坏之前的故事

### Parallel Team Strategy

多开发者情况：

1. 团队一起完成 Setup + Foundational
2. Foundational 完成后：
   - 开发者 A: User Story 1 + 2 (后端)
   - 开发者 B: User Story 1 + 2 (前端)
   - 开发者 C: User Story 4 (设置功能)
   - 开发者 D: User Story 5 (国际化)
3. 各故事独立完成并集成

---

## Notes

- [P] 任务 = 不同文件，无依赖
- [Story] 标签将任务映射到特定用户故事以便追踪
- 每个用户故事应该可以独立完成和测试
- 每个任务或逻辑组完成后提交
- 在任何检查点停止以独立验证故事
- 避免：模糊任务、同文件冲突、破坏独立性的跨故事依赖

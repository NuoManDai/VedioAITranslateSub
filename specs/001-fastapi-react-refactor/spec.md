# Feature Specification: 前后端分离重构

**Feature Branch**: `001-fastapi-react-refactor`  
**Created**: 2026-01-17  
**Status**: Draft  
**Input**: User description: "阅读代码进行重构，要求：1.进行前后端分离 2.服务端使用FastAPI 3.服务端需要有Swagger文档 4.使用conda来创建虚拟环境（已有VideoLingo环境可参考，禁止全局pip安装）5.前端使用React重构 6.前端框架使用TypeScript, TailwindCSS和Ant Design，美化界面，去掉VideoLingo信息"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 视频上传与下载 (Priority: P1)

用户可以通过新的 React 前端界面上传本地视频文件或输入 YouTube 链接下载视频。系统通过 FastAPI 后端处理文件存储和视频下载，前端展示上传进度和下载状态。

**Why this priority**: 这是整个应用的入口功能，没有视频输入就无法进行后续的字幕处理和配音操作。此功能独立于其他处理步骤，是最基础的 MVP。

**Independent Test**: 可以通过上传一个视频文件或下载一个 YouTube 视频来完整测试，成功后视频预览可用。

**Acceptance Scenarios**:

1. **Given** 用户打开应用首页, **When** 用户拖拽或选择本地视频文件上传, **Then** 系统显示上传进度并在完成后预览视频
2. **Given** 用户在首页, **When** 用户输入有效的 YouTube 链接并点击下载, **Then** 系统显示下载进度并在完成后预览视频
3. **Given** 已有视频存在, **When** 用户点击删除重选, **Then** 系统删除当前视频并返回上传界面

---

### User Story 2 - 字幕处理流程 (Priority: P1)

用户可以对已上传的视频执行字幕处理流程，包括语音识别、句子分割、翻译和字幕合成。后端提供 API 端点触发处理流程，前端展示处理进度和各阶段状态。

**Why this priority**: 字幕处理是应用的核心功能，与视频上传同为 P1 优先级，两者结合即可交付基本可用的产品。

**Independent Test**: 可以通过上传视频后点击开始处理，观察各阶段进度更新，最终生成带字幕的视频文件。

**Acceptance Scenarios**:

1. **Given** 视频已上传, **When** 用户点击开始处理字幕, **Then** 系统依次执行语音识别、分割、翻译、合成步骤并显示进度
2. **Given** 处理进行中, **When** 某个阶段完成, **Then** 前端实时更新该阶段状态为已完成
3. **Given** 字幕处理完成, **When** 用户查看结果, **Then** 可预览带字幕的视频并下载 SRT 文件

---

### User Story 3 - 配音处理流程 (Priority: P2)

用户可以在字幕处理完成后执行配音流程，包括音频任务生成、参考音频提取、TTS 合成和音频合并。支持多种 TTS 后端选择。

**Why this priority**: 配音是字幕处理的增值功能，依赖字幕处理完成，属于第二优先级。

**Independent Test**: 可以在字幕处理完成后点击开始配音，观察进度更新，最终生成带配音的视频。

**Acceptance Scenarios**:

1. **Given** 字幕处理已完成, **When** 用户点击开始配音, **Then** 系统执行配音流程并显示各阶段进度
2. **Given** 配音进行中, **When** 用户查看进度, **Then** 可以看到当前正在处理的音频片段
3. **Given** 配音完成, **When** 用户查看结果, **Then** 可预览和下载带配音的视频

---

### User Story 4 - 设置管理 (Priority: P2)

用户可以通过设置面板配置 API 密钥、语言选项、TTS 方法等参数。设置通过 API 保存到后端配置文件，支持实时验证 API 有效性。

**Why this priority**: 设置功能是辅助功能，用户可以使用默认配置开始使用，因此优先级低于核心处理流程。

**Independent Test**: 可以通过打开设置面板，修改配置项，保存后刷新页面验证配置是否持久化。

**Acceptance Scenarios**:

1. **Given** 用户打开设置面板, **When** 修改 API Key 并保存, **Then** 系统保存配置并显示成功提示
2. **Given** 用户配置了 API Key, **When** 点击测试按钮, **Then** 系统验证 API 有效性并显示结果
3. **Given** 用户修改语言设置, **When** 保存后刷新页面, **Then** 界面语言正确切换

---

### User Story 5 - 多语言界面支持 (Priority: P3)

前端界面支持多种显示语言（英文、简体中文、繁体中文、日语、西班牙语、俄语、法语），用户可以切换界面语言，所有文本根据选择的语言显示。

**Why this priority**: 国际化是锦上添花的功能，核心功能完成后再实现，不影响基本使用。

**Independent Test**: 可以通过切换语言下拉菜单，验证界面所有文本正确切换为目标语言。

**Acceptance Scenarios**:

1. **Given** 用户在任意页面, **When** 从语言下拉菜单选择其他语言, **Then** 界面所有文本立即切换
2. **Given** 用户选择了特定语言, **When** 刷新页面, **Then** 语言选择保持不变

---

### Edge Cases

- 用户上传不支持的视频格式时应显示友好错误提示
- YouTube 链接无效或视频不可用时应提示具体原因
- API 调用失败时应显示错误详情并允许重试
- 处理过程中网络断开时应保存进度；用户返回时提示选择继续或重新开始
- 配置验证失败时应阻止保存并提示具体问题

## Requirements *(mandatory)*

### Functional Requirements

**后端 (FastAPI)**

- **FR-001**: 系统 MUST 提供 RESTful API 用于视频上传，支持断点续传，无文件大小限制
- **FR-002**: 系统 MUST 提供 API 端点触发 YouTube 视频下载，返回下载进度
- **FR-003**: 系统 MUST 提供 API 端点触发字幕处理流程，支持进度查询（前端通过轮询获取进度）
- **FR-004**: 系统 MUST 提供 API 端点触发配音处理流程，支持进度查询（前端通过轮询获取进度）
- **FR-005**: 系统 MUST 提供配置读写 API，支持验证 API 密钥有效性
- **FR-006**: 系统 MUST 自动生成 Swagger/OpenAPI 文档，可通过 `/docs` 访问
- **FR-007**: 系统 MUST 保持与现有 core 模块的兼容性，调用现有处理逻辑
- **FR-008**: 系统 MUST 在 `backend/` 目录下组织代码，独立于前端

**前端 (React)**

- **FR-009**: 前端 MUST 使用 TypeScript 编写，启用严格类型检查
- **FR-010**: 前端 MUST 使用 TailwindCSS 进行样式管理
- **FR-011**: 前端 MUST 使用 Ant Design 组件库构建 UI
- **FR-012**: 前端 MUST 移除所有 VideoLingo 品牌信息，使用新名称 "VedioAITranslateSub"
- **FR-013**: 前端 MUST 提供视频上传/下载界面，支持拖拽上传
- **FR-014**: 前端 MUST 提供处理进度展示，包含各阶段状态
- **FR-015**: 前端 MUST 提供设置面板（模态框形式），允许配置 API 和处理选项
- **FR-016**: 前端 MUST 支持多语言切换，复用现有翻译文件
- **FR-017**: 前端 MUST 在 `frontend/` 目录下组织代码，独立于后端

**环境管理**

- **FR-018**: 项目 MUST 使用 conda 创建虚拟环境，禁止全局 pip 安装
- **FR-019**: 项目 MUST 提供环境配置文档，说明如何基于现有 VideoLingo 环境扩展
- **FR-020**: 项目 MUST 提供前端和后端的独立启动脚本

### Key Entities

- **Video**: 用户上传或下载的视频文件，包含文件路径、来源类型、状态
- **ProcessingJob**: 处理任务，包含任务类型（字幕/配音）、当前阶段、进度百分比、状态
- **Configuration**: 系统配置，包含 API 设置、语言设置、TTS 设置等
- **ProcessingStage**: 处理阶段，包含阶段名称、状态、开始时间、完成时间

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 用户可以在 30 秒内完成视频上传（100MB 以内文件）
- **SC-002**: 用户可以在界面上实时查看处理进度，刷新频率至少每 2 秒一次
- **SC-003**: 所有 API 端点在 `/docs` 页面有完整的接口文档和示例
- **SC-004**: 前端首次加载时间不超过 3 秒（生产构建）
- **SC-005**: 界面切换语言后所有可见文本在 1 秒内完成切换
- **SC-006**: 配置修改保存后刷新页面，配置值正确保持
- **SC-007**: 用户可以顺利完成从上传视频到获得带字幕视频的完整流程

## Assumptions

- 现有 `core/` 目录下的处理逻辑保持不变，后端通过调用这些模块实现功能
- 现有 `translations/*.json` 文件可直接被前端复用
- 现有 `config.yaml` 格式保持兼容，后端 API 读写此文件
- 用户已安装 conda 且熟悉基本 conda 命令
- Node.js 18+ 用于前端开发和构建

## Out of Scope

- 用户认证和多用户支持
- 批量视频处理功能
- 视频编辑功能
- 移动端适配（仅支持桌面浏览器）
- 云端部署配置（仅支持本地运行）

## Clarifications

### Session 2026-01-17

- Q: 前端如何获取后端处理进度？ → A: 轮询 (Polling) - 前端每 2 秒调用进度查询 API
- Q: 视频处理任务被中断后用户返回时应如何处理？ → A: 提示恢复 - 检测到未完成任务时提示用户选择继续或重新开始
- Q: 去掉 VideoLingo 品牌后应用应显示什么名称？ → A: VedioAITranslateSub
- Q: 视频文件大小是否有上限限制？ → A: 无限制 - 允许任意大小文件上传
- Q: 设置面板应以何种方式呈现给用户？ → A: 模态框 (Modal) - 点击设置按钮弹出对话框

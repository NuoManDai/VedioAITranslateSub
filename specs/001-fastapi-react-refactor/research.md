# Research: 前后端分离重构

**Feature**: 001-fastapi-react-refactor  
**Date**: 2026-01-17

## 研究任务

### 1. FastAPI 与现有 core 模块集成

**问题**: 如何在 FastAPI 中调用现有的同步处理函数（如 `_2_asr.transcribe()`）而不阻塞 API？

**结论**: 使用 FastAPI 的 `BackgroundTasks` 或 `asyncio.to_thread()` 将同步处理函数放入后台线程执行。

**决策**: 
- 使用 `BackgroundTasks` 触发处理流程
- 处理进度存储在内存字典中（单用户场景足够）
- 提供 `/api/processing/status` 端点供前端轮询

**替代方案评估**:
- Celery 任务队列 - 过于复杂，单用户场景不需要
- 数据库持久化进度 - 增加依赖，文件系统足够

### 2. 文件上传处理

**问题**: 如何实现大文件上传和断点续传？

**结论**: FastAPI 的 `UploadFile` 支持流式上传，结合 `python-multipart` 可处理大文件。断点续传需要前端配合使用 tus 协议或分片上传。

**决策**:
- 初始版本使用简单的 `UploadFile` 流式上传
- 不实现完整的断点续传（复杂度高，单用户场景收益低）
- 前端显示上传进度通过 XMLHttpRequest 的 `onprogress` 事件

**替代方案评估**:
- tus 协议 - 需要额外库和前端实现，延后考虑
- 分片上传 - 实现复杂，延后考虑

### 3. React + TypeScript + Ant Design 集成

**问题**: 如何配置 Vite + React + TypeScript + TailwindCSS + Ant Design？

**结论**: 标准配置，Ant Design 5.x 原生支持 CSS-in-JS，与 TailwindCSS 可共存。

**决策**:
- 使用 Vite 作为构建工具（比 CRA 更快）
- Ant Design 用于复杂组件（Upload, Modal, Steps, Progress）
- TailwindCSS 用于布局和自定义样式
- 避免样式冲突：Ant Design 组件不使用 Tailwind 类

**替代方案评估**:
- Create React App - 已过时，Vite 是更好选择
- 纯 TailwindCSS - 需要自己实现复杂组件，工作量大

### 4. 国际化复用

**问题**: 如何复用现有 `translations/*.json` 文件？

**结论**: 使用 `react-i18next` 库，直接加载现有 JSON 文件。

**决策**:
- 使用 `react-i18next` 管理国际化
- 直接导入 `translations/*.json`（构建时复制到 `frontend/src/i18n/locales/`）
- 语言选择存储在 `localStorage`

**替代方案评估**:
- 重新定义翻译 key - 工作量大，不必要
- 动态从后端获取翻译 - 增加 API 调用，不必要

### 5. 进度轮询实现

**问题**: 前端如何高效轮询处理进度？

**结论**: 使用 React Query 或自定义 hook 实现轮询，间隔 2 秒。

**决策**:
- 创建 `useProcessingStatus` 自定义 hook
- 使用 `setInterval` + `fetch` 实现轮询
- 处理完成或失败时停止轮询
- 显示各阶段状态（未开始/进行中/完成）

**替代方案评估**:
- React Query - 功能强大但对于简单轮询可能过重
- WebSocket - 复杂度高，单用户场景收益低

### 6. Conda 环境管理

**问题**: 如何在现有 VideoLingo 环境基础上扩展？

**结论**: 直接在现有 `videolingo` 环境中安装 FastAPI 相关依赖。

**决策**:
- 在 `videolingo` 环境中安装 `fastapi uvicorn python-multipart`
- 后端 `requirements.txt` 引用根目录 `requirements.txt` 并添加 FastAPI 依赖
- 提供清晰的环境配置文档

**替代方案评估**:
- 创建独立环境 - 需要重新安装所有依赖，浪费资源
- Docker 容器 - 增加复杂度，本地开发不方便

## 技术栈确认

| 组件 | 技术选择 | 版本 |
|------|----------|------|
| 后端框架 | FastAPI | ^0.109.0 |
| ASGI 服务器 | Uvicorn | ^0.27.0 |
| 文件上传 | python-multipart | ^0.0.6 |
| 前端框架 | React | ^18.2.0 |
| 构建工具 | Vite | ^5.0.0 |
| 类型系统 | TypeScript | ^5.3.0 |
| CSS 框架 | TailwindCSS | ^3.4.0 |
| UI 组件库 | Ant Design | ^5.12.0 |
| 国际化 | react-i18next | ^14.0.0 |
| HTTP 客户端 | fetch (原生) | - |

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 大文件上传超时 | 用户体验差 | 增加服务器超时配置，显示上传进度 |
| 处理中断后进度丢失 | 需要重新处理 | 利用现有 output 目录状态检测恢复点 |
| Ant Design 与 TailwindCSS 样式冲突 | UI 不一致 | 明确分工：Ant Design 用于组件，Tailwind 用于布局 |
| 翻译 key 不匹配 | 界面显示 key 而非翻译 | 开发时验证所有 key，添加 fallback |

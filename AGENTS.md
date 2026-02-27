# AGENTS.md — VideoAITranslateSub

**生成时间:** 2026-02-28 | **提交:** deb9125 | **分支:** main

## 概述

视频本地化系统：上传 → ASR 语音识别 → NLP 分句 → 翻译 → 字幕生成 → TTS 配音 → 视频合成。后端 (Python FastAPI) 编排只读的 `core/` 流水线。前端 (React 18 + Vite + Ant Design + TailwindCSS) 提供多视频管理 + 实时进度 + 内联字幕编辑器。

## 目录结构

```
.
├── backend/             # FastAPI API + 服务层 + SQLite（见 backend/AGENTS.md）
│   ├── api/routes/      # REST 端点，/api/* 前缀
│   ├── services/        # 业务逻辑，流水线编排（见 backend/services/AGENTS.md）
│   ├── database/        # 原生 SQLite，无 ORM
│   └── models/          # Pydantic 模型，camelCase 别名
├── frontend/            # React SPA（见 frontend/src/AGENTS.md）
│   └── src/
│       ├── pages/       # VideoList、Home（详情）、SubtitleEditor
│       ├── components/  # UI 组件 + subtitle-editor/（见 subtitle-editor/AGENTS.md）
│       ├── services/    # API 客户端（api.ts、subtitleApi.ts）
│       ├── hooks/       # useSubtitleEditor、useProcessingStatus、useConfig
│       ├── types/       # 统一导出桶：types/index.ts
│       └── i18n/        # 7 种语言（en、zh-CN、zh-HK、ja、es、ru、fr）
├── core/                # 只读流水线（见 core/AGENTS.md）
│   ├── _1_ytdlp.py … _12_*.py   # 顺序处理阶段
│   ├── asr_backend/     # WhisperX、FunASR 等
│   ├── tts_backend/     # GPT-SoVITS、Fish、Azure 等
│   └── utils/           # 共享工具（配置、模型、路径）
├── translations/        # 仅 README 翻译（非 i18n 语言包）
├── batch/               # 纯数据目录（input/、uploads/），无代码
├── config.yaml          # 应用配置，敏感密钥在 git 中用占位符
└── specs/               # 设计规格文档
```

## 查找指南

| 任务 | 位置 | 备注 |
|------|------|------|
| 新增 API 端点 | `backend/api/routes/` | 静态路由必须在动态 `/{video_id}` 之前 |
| 新增业务逻辑 | `backend/services/` | 一个领域一个服务 |
| 新增 Pydantic 模型 | `backend/models/` | 必须使用 `alias_generator=to_camel` |
| 新增 React 页面 | `frontend/src/pages/` | 在 `App.tsx` 中懒加载 |
| 新增 React 组件 | `frontend/src/components/` | PascalCase 文件名 |
| 新增自定义 Hook | `frontend/src/hooks/` | `use` 前缀，从 `index.ts` 导出 |
| 新增 API 调用 | `frontend/src/services/api.ts` | 使用 `fetchApi<T>()` 封装 |
| 新增字幕 API | `frontend/src/services/subtitleApi.ts` | 独立客户端（有自己的 base URL） |
| 新增翻译键 | `frontend/src/i18n/locales/*.json` | 必须同时更新全部 7 个文件 |
| 修改流水线 | **禁止** | `core/` 是只读的 |
| 修改配置 | `config.yaml` 通过 `/api/config` | 前端不能直接写文件 |

## 编码规范

### Python
- PEP 8，函数签名需类型注解
- 区块注释用横线头：`# ----------\n# 章节\n# ----------`
- 所有注释用英文
- 变量赋值不加类型提示（`.cursorrules`）
- 导入顺序：标准库 → 第三方 → 本地（空行分隔）

### TypeScript
- 严格模式：`noUnusedLocals`、`noUnusedParameters`
- 优先 `interface` 而非 `type` 别名
- 仅使用函数组件 + Hooks
- 路径别名 `@/*` → `src/*`
- 导入顺序：React → 第三方 → 本地组件 → 类型 → 服务
- 组件文件：PascalCase。Hook 文件：camelCase + `use` 前缀

### API 契约
- 所有路由前缀 `/api/`
- Pydantic：每个模型必须有 `alias_generator=to_camel` + `populate_by_name=True`
- 响应序列化：`.model_dump(by_alias=True)` → camelCase JSON
- 前端期望 camelCase，后端内部使用 snake_case

### 状态与数据流
- 无 Redux/Zustand。纯 useState + 自定义 Hooks + props 传递
- 持久化：IndexedDB（字幕草稿）、localStorage（编辑器设置、i18n）
- 进度：通过 setTimeout 轮询（3000ms），非 WebSocket/SSE
- 取消：双标志（内存 AppState + 文件系统哨兵 `.cancel_requested`）

### 工作空间隔离
- 每个视频分配 `output/{uuid}/` 目录
- 流水线要求平铺 `output/` — `core_path_manager` 处理前后拷贝进/出
- 所有 core 代码硬编码 `output/` 相对路径 — 必须从项目根目录运行

## 反模式（绝对禁止）

1. **修改 `core/`**：流水线文件只读。调用但不编辑。
2. **`as any` / `@ts-ignore` / `@ts-expect-error`**：应扩展类型。
3. **裸 `except:` / `except Exception: pass`**：必须捕获特定异常。
4. **`os.chdir()`**：与异步存在竞态条件。gpt_sovits_tts.py 中已有问题。
5. **模块中使用 `exit()`**：应抛出异常。exit(1) 存在于 core — 不要复制。
6. **`eval()`**：core 中用于 DataFrame 字符串 — 新代码使用 JSON。
7. **`sys.path.insert()`**：main.py 中已做过 — 不要重复。
8. **通配符导入**：`from x import *` 存在于 core — backend/frontend 中使用显式导入。
9. **在 `async def` 中直接调用 core**：使用 `asyncio.to_thread()`。Core 使用阻塞 sleep。
10. **扩展 AppState 单例**：使用逐视频的 `_video_jobs` 字典，不要新增全局状态。
11. **提交真实 API 密钥**：config.yaml 在 git 中使用占位符。
12. **`dangerouslySetInnerHTML`**：StageOutputFiles 中有一处未消毒的使用，不要复制。

## 命令

```bash
# 后端
conda activate videolingo
cd backend && uvicorn main:app --reload --port 8000

# 前端
cd frontend && npm install && npm run dev     # 开发服务器（端口 5173）
cd frontend && npm run build                  # 类型检查 + 构建
cd frontend && npm run lint                   # ESLint（不允许警告）

# Windows 快捷方式
.\start_backend.ps1 [-Port 8000]
.\start_frontend.ps1 [-Port 5173]

# 测试（仅后端，目前为空）
cd backend && pytest
```

## 注意事项

- **轮询间隔 3000ms**，非旧文档说的 2000ms。使用 setTimeout 递归，非 setInterval。
- **根目录 `translations/`** = README 翻译。i18n 语言包在 `frontend/src/i18n/locales/`。
- **Vite 代理**目标是 `hsklw.vicp.fun:8000`（远程），非 localhost。
- **CORS** 仅允许 `localhost:5173` 和 `127.0.0.1:5173`。
- **SQLite 数据库**在 `backend/data/videos.db` — 相对于 backend/ 工作目录。
- **TailwindCSS preflight: false** — 禁用以避免与 Ant Design 冲突。
- **Ant Design 语言**：main.tsx 中硬编码 `zhCN`。
- **`subtitleApi.ts`** 复制了 `api.ts` 的 `API_BASE_URL` 和 `ApiRequestError` — 技术债务。
- **video.py 路由顺序**：静态路由（`/videos`、`/upload`）必须在 `/{video_id}` 之前。
- **无测试**：backend/tests/ 为空，前端没有测试框架。
- **任务状态**：仅存于内存。重启后通过文件系统在状态查询时恢复。

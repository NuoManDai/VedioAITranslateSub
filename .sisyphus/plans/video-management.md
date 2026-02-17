# 视频管理 - 多视频系统

## 概要

> **简要概述**: 将当前的单视频应用转变为多视频管理系统，包括卡片网格列表页面、每个视频独立目录、SQLite 元数据存储和正确的 React Router 路由。
> 
> **交付物**:
> - 视频列表页面（卡片网格）作为新首页，路径为 `/`
> - 每个视频独立输出目录 (`output/{video-id}/`)
> - SQLite 数据库存储视频元数据 (`data/videos.db`)
> - 重构路由，`/video/:id` 为详情页，`/video/:id/editor` 为字幕编辑器
> - 视频删除及目录清理
> - 自动迁移现有 `output/` 数据
> - 通过猴子补丁 `core.utils.models` 路径常量保持核心流水线兼容
> 
> **预估工作量**: 大
> **并行执行**: 是 - 3 个批次
> **关键路径**: 任务 1 (数据库) → 任务 2 (后端 API) → 任务 5 (前端视频列表) → 任务 6 (路由) → 任务 8 (集成 QA)

---

## 背景

### 原始需求
用户希望：
1. 添加一个视频管理列表页面，集成到当前路由中
2. 点击列表项进入视频翻译详情页，每个视频都有一个 ID
3. 删除视频时移除其文件目录并返回列表
4. 每个视频需要一个专用目录来存储其相关信息

### 需求讨论摘要
**关键讨论**:
- **路由**: `/` 作为视频列表（新首页），`/video/:id` 为详情页，`/video/:id/editor` 为字幕编辑器
- **存储**: SQLite 数据库 (`data/videos.db`) 存储元数据，遵循现有 `batch_db.py` 模式
- **目录结构**: 每个视频 `output/{video-id}/`
- **核心兼容性**: 在处理前对 `core.utils.models` 路径常量进行猴子补丁（不修改核心文件）
- **布局**: 卡片网格，包含缩略图、文件名+时长、处理状态、创建时间、来源标签
- **迁移**: 自动将现有 `output/` 数据迁移到新结构
- **测试**: 不写单元测试；仅使用 Agent 执行的 QA 场景

**调研发现**:
- 所有核心模块（`_2_asr.py` 到 `_12_dub_to_vid.py`）通过 `from core.utils.models import *` 导入路径常量
- 常量是基于 CWD 的相对字符串，如 `"output/log/cleaned_chunks.xlsx"`
- `check_file_exists` 装饰器使用 `os.path.exists(file_path)` — 也是基于 CWD 的相对路径
- `batch_processing_service.py` 已经展示了清理→复制→处理→保存的多视频处理模式
- 当前 `AppState` 在内存中保存单个 `current_video` — 必须替换为基于数据库的方案
- 前端路由使用手动 `location.pathname` 检查，而非正确的 `<Route>` 组件

### Metis 审查
**已识别的差距**（已解决）:
- 核心模块路径处理已调研 — 猴子补丁 `core.utils.models` 属性是最安全的方案
- 猴子补丁的线程安全问题已通过确保同一时间只有一个处理任务来解决（现有约束）
- 迁移边界情况：空的 output 目录、部分处理文件

---

## 工作目标

### 核心目标
通过列表页面实现多视频管理，每个视频都有专用存储，同时保持与只读核心流水线模块的完全兼容性。

### 具体交付物
- `backend/database/video_db.py` — 视频的 SQLite 数据库层
- `backend/api/routes/video.py` — 重构的视频 CRUD API（多视频感知）
- `backend/services/video_service.py` — 重构的服务层（基于数据库，每个视频独立目录）
- `backend/services/processing_service.py` — 更新以对每个视频进行核心路径猴子补丁
- `frontend/src/pages/VideoList.tsx` — 新的视频列表页面（卡片网格）
- `frontend/src/pages/Home.tsx` → 重构为视频详情页（通过 `:id` 参数化）
- `frontend/src/App.tsx` — 使用嵌套路由的正确 React Router
- `frontend/src/services/api.ts` — 更新包含视频 ID 的 API 调用
- 现有 `output/` 数据的迁移逻辑

### 完成标准
- [ ] `GET /api/videos` 从 SQLite 返回视频列表
- [ ] `POST /api/video/upload` 创建带 UUID 的视频记录，将文件存储在 `output/{id}/`
- [ ] `DELETE /api/video/{id}` 删除数据库记录和 `output/{id}/` 目录
- [ ] 视频列表页面在 `/` 显示卡片
- [ ] 点击卡片导航到 `/video/{id}`，显示完整处理界面
- [ ] 字幕编辑器可通过 `/video/{id}/editor` 访问
- [ ] 处理流水线使用每个视频独立的输出目录
- [ ] 现有单视频输出数据在首次启动时自动迁移

### 必须包含
- 每个视频的视频 ID (UUID)
- 每个视频独立目录隔离 (`output/{video-id}/`)
- 带状态指示器的卡片网格列表
- 删除时完全清理目录
- 与核心流水线模块的向后兼容性

### 禁止事项（护栏）
- **不得修改任何 `core/_*.py` 或 `core/utils/*.py` 文件** — 流水线为只读
- **不得更改批量处理系统** — `batch_db.py`、`batch_service.py`、`batch_processing_service.py` 保持不变
- **不得添加新的 i18n 键** — 尽可能复用现有翻译键；新 UI 元素使用英文字符串
- **不得过度设计** — 视频列表不加分页、搜索或筛选（后续可添加）
- **不得添加认证或用户管理**
- **不得创建抽象层** — 保持代码直接简单，匹配现有模式

---

## 验证策略

> **通用规则：零人工干预**
>
> 所有任务必须在无任何人工操作的情况下可验证。

### 测试决策
- **基础设施是否存在**: 是（后端有 pytest）
- **自动化测试**: 否（用户决定不写单元测试）
- **框架**: 不适用
- **主要验证方式**: Agent 执行的 QA 场景 (Playwright + curl)

### Agent 执行的 QA 场景（必须 — 所有任务）

每个任务都包含使用 curl（后端 API）和 Playwright（前端 UI 验证）的特定 QA 场景。

---

## 执行策略

### 并行执行批次

```
批次 1（立即开始）:
├── 任务 1: 视频数据库层 (backend/database/video_db.py)
├── 任务 3: 核心路径猴子补丁工具
└── 任务 5: VideoList 页面组件（前端，可以在没有 API 的情况下搭建骨架）

批次 2（批次 1 完成后）:
├── 任务 2: 视频 CRUD API + 服务层重构（依赖: 1）
├── 任务 4: 处理服务集成（依赖: 1, 3）
└── 任务 6: 前端路由重构（依赖: 5）

批次 3（批次 2 完成后）:
├── 任务 7: 前端 API 集成 + VideoDetail 重构（依赖: 2, 6）
├── 任务 8: 迁移逻辑（依赖: 1, 2）
└── 任务 9: 全面集成 QA（依赖: 全部）
```

### 依赖矩阵

| 任务 | 依赖于 | 阻塞 | 可并行执行 |
|------|--------|------|-----------|
| 1 | 无 | 2, 4, 8 | 3, 5 |
| 2 | 1 | 7, 9 | 4, 6 |
| 3 | 无 | 4 | 1, 5 |
| 4 | 1, 3 | 9 | 2, 6 |
| 5 | 无 | 6 | 1, 3 |
| 6 | 5 | 7 | 2, 4 |
| 7 | 2, 6 | 9 | 4, 8 |
| 8 | 1, 2 | 9 | 4, 7 |
| 9 | 全部 | 无（最终） | 无（最终） |

### Agent 分派概要

| 批次 | 任务 | 推荐 Agent |
|------|------|-----------|
| 1 | 1, 3, 5 | task(category="quick") 用于 1,3; task(category="visual-engineering") 用于 5 |
| 2 | 2, 4, 6 | task(category="unspecified-high") 用于 2,4; task(category="visual-engineering") 用于 6 |
| 3 | 7, 8, 9 | task(category="unspecified-high") 用于 7,8; task(category="deep") 用于 9 |

---

## 任务列表

- [ ] 1. 创建视频数据库层

  **任务内容**:
  - 创建 `backend/database/video_db.py`，完全遵循 `backend/database/batch_db.py` 的模式
  - SQLite 数据库位于 `data/videos.db`
  - `videos` 表包含以下列:
    - `id TEXT PRIMARY KEY` (UUID)
    - `filename TEXT NOT NULL`
    - `filepath TEXT`（视频文件在 output/{id}/ 内的路径）
    - `source_type TEXT NOT NULL DEFAULT 'upload'`（'upload' 或 'youtube'）
    - `youtube_url TEXT`
    - `status TEXT NOT NULL DEFAULT 'ready'`（'uploading', 'downloading', 'ready', 'processing', 'completed', 'error'）
    - `file_size INTEGER`
    - `duration REAL`
    - `thumbnail_path TEXT`
    - `error_message TEXT`
    - `created_at TEXT NOT NULL`
    - `updated_at TEXT NOT NULL`
  - 方法: `init_db()`, `create_video(...)`, `get_video(id)`, `list_videos()`, `update_video_status(id, status)`, `update_video(id, **fields)`, `delete_video(id)`
  - 在 `backend/main.py` 启动时初始化数据库（与批量数据库初始化模式相同）

  **禁止事项**:
  - 不得修改 `batch_db.py`
  - 不得添加 ORM（保持与 batch_db.py 相同的原生 sqlite3 方式）
  - 不得添加连接池 — 保持简单的每次调用创建连接的模式

  **推荐 Agent 配置**:
  - **类别**: `quick`
    - 原因: 单文件创建，遵循现有模式 (batch_db.py) — 简单的复制-适配
  - **技能**: `[]`
  - **已评估但未使用的技能**:
    - `git-master`: 此任务不需要 git 操作

  **并行化**:
  - **可并行执行**: 是
  - **并行组**: 批次 1（与任务 3, 5 同组）
  - **阻塞**: 任务 2, 4, 8
  - **被阻塞**: 无

  **参考资料**:

  **模式参考**（要遵循的现有代码）:
  - `backend/database/batch_db.py` — **主要参考**: 复制此文件的完整结构。相同的 `_get_connection()`、`_ensure_data_dir()`、`init_db()` 模式。将 batch_jobs/batch_files 替换为 videos 表。
  - `backend/models/video.py` — 视频 Pydantic 模型，字段需匹配数据库列（id, filename, filepath, source_type, youtube_url, status, file_size, duration, created_at, error_message）
  - `backend/main.py:16-25` — 启动时初始化批量数据库的位置。在同一个 `lifespan` 函数中添加视频数据库初始化。

  **API/类型参考**:
  - `backend/models/video.py:VideoStatus` — Literal 类型: `'uploading' | 'downloading' | 'ready' | 'processing' | 'completed' | 'error'`
  - `backend/models/video.py:VideoSourceType` — Literal 类型: `'upload' | 'youtube'`
  - `backend/models/video.py:Video` — 包含所有字段的完整模型 (第 34-44 行)

  **验收标准**:

  **Agent 执行的 QA 场景:**

  ```
  场景: 视频数据库在启动时初始化表
    工具: Bash (python)
    前置条件: 后端未运行，data/videos.db 不存在
    步骤:
      1. cd backend && python -c "from database.video_db import VideoDB; db = VideoDB(); db.init_db(); print('OK')"
      2. 断言: stdout 包含 "OK"
      3. 断言: 文件 data/videos.db 存在
      4. python -c "import sqlite3; conn = sqlite3.connect('data/videos.db'); print([row[1] for row in conn.execute('PRAGMA table_info(videos)').fetchall()])"
      5. 断言: 输出包含 'id', 'filename', 'filepath', 'source_type', 'status', 'created_at', 'updated_at'
    预期结果: 数据库文件创建，模式正确
    证据: 命令输出已捕获

  场景: CRUD 操作正常工作
    工具: Bash (python)
    前置条件: video_db.py 存在
    步骤:
      1. python -c "
         from database.video_db import VideoDB
         db = VideoDB('data/test_videos.db')
         db.init_db()
         vid = db.create_video(filename='test.mp4', filepath='output/abc/test.mp4', source_type='upload')
         print('created:', vid)
         v = db.get_video(vid)
         print('got:', v.filename if v else 'NONE')
         videos = db.list_videos()
         print('list:', len(videos))
         db.update_video_status(vid, 'processing')
         v2 = db.get_video(vid)
         print('status:', v2.status if v2 else 'NONE')
         db.delete_video(vid)
         v3 = db.get_video(vid)
         print('deleted:', v3 is None)
         "
      2. 断言: 输出显示创建的 UUID，得到 test.mp4，列表长度 1，状态为 processing，已删除为 True
    预期结果: 所有 CRUD 操作成功
    证据: 命令输出已捕获
  ```

  **提交**: 是
  - 消息: `feat(db): add video database layer for multi-video management`
  - 文件: `backend/database/video_db.py`, `backend/main.py`
  - 提交前检查: `cd backend && python -c "from database.video_db import VideoDB; print('import ok')"`

---

- [ ] 2. 重构视频 API 和服务层以支持多视频

  **任务内容**:
  - **重构 `backend/services/video_service.py`**:
    - 将内存中的 `AppState.current_video` 替换为 `VideoDB` 调用
    - `upload_video()`: 生成 UUID，创建 `output/{video-id}/` 目录，将文件保存到该目录，创建数据库记录，生成缩略图
    - `get_video(id)`: 从数据库获取
    - `list_videos()`: 从数据库获取全部，按 created_at DESC 排序
    - `delete_video(id)`: 删除数据库记录 + `shutil.rmtree(output/{video-id}/)` + 返回成功
    - `download_youtube(url, resolution, video_id)`: 下载到 `output/{video-id}/`，更新数据库记录
    - 添加 `generate_thumbnail(video_path, output_path)`: 使用 ffmpeg 提取第一帧作为缩略图
  - **重构 `backend/api/routes/video.py`**:
    - `GET /api/videos` → 列出所有视频
    - `GET /api/video/{video_id}` → 获取单个视频
    - `POST /api/video/upload` → 上传视频文件，返回带 ID 的视频
    - `POST /api/video/youtube` → 下载 YouTube 视频，返回带 ID 的视频
    - `DELETE /api/video/{video_id}` → 删除视频 + 目录
    - `GET /api/video/{video_id}/stream` → 从 `output/{video-id}/` 流式传输视频文件
    - `GET /api/video/{video_id}/thumbnail` → 提供缩略图图片
  - **更新 `backend/api/deps.py`**:
    - 添加 `get_video_output_dir(video_id: str) -> Path` 辅助函数，返回 `PROJECT_ROOT/output/{video_id}/`
    - 保留 `get_output_dir()` 以保持向后兼容，但标记为已弃用
  - **更新 `backend/models/video.py`**:
    - 向 Video 模型添加 `thumbnail_path: Optional[str]` 字段
    - 向 Video 模型添加 `updated_at: datetime` 字段
    - 更新 `VideoResponse` 以包含 `thumbnailPath` 和 `updatedAt`

  **禁止事项**:
  - 不得删除现有的上传/YouTube 下载逻辑 — 重构为使用每个视频独立目录
  - 不得更改批量处理路由
  - 不得添加文件大小限制

  **推荐 Agent 配置**:
  - **类别**: `unspecified-high`
    - 原因: 多文件重构，涉及业务逻辑变更，中等复杂度
  - **技能**: `[]`

  **并行化**:
  - **可并行执行**: 是（在批次 2 内）
  - **并行组**: 批次 2（与任务 4, 6 同组）
  - **阻塞**: 任务 7, 9
  - **被阻塞**: 任务 1

  **参考资料**:

  **模式参考**:
  - `backend/services/video_service.py` — **要重构的当前实现**。目前使用 `AppState.current_video`（内存中）。替换为 `VideoDB` 调用。
  - `backend/api/routes/video.py` — **要重构的当前路由**。目前为单视频端点。为所有路由添加 video_id 参数。
  - `backend/api/deps.py:12-38` — `PROJECT_ROOT`, `OUTPUT_DIR`, `get_output_dir()`, `get_project_root()`。添加 `get_video_output_dir(video_id)`。
  - `backend/services/batch_processing_service.py:61-76` — `_copy_video_to_output()` 和 `_clean_output_dir()` 模式，用于文件管理参考。
  - `backend/database/batch_db.py` — 数据库使用模式（实例化，调用方法）。

  **API/类型参考**:
  - `backend/models/video.py:Video`（第 34-44 行）— 完整模型。添加 `thumbnail_path` 和 `updated_at` 字段。
  - `backend/models/video.py:VideoResponse`（第 47-60 行）— API 响应模型。更新以包含新字段。
  - `backend/models/video.py:YouTubeDownloadRequest`（第 63-68 行）— YouTube 下载请求结构。

  **验收标准**:

  **Agent 执行的 QA 场景:**

  ```
  场景: 上传视频创建每个视频独立目录
    工具: Bash (curl)
    前置条件: 后端运行在 localhost:8000
    步骤:
      1. 创建一个小的测试视频: ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 -f lavfi -i sine=duration=1 test_upload.mp4
      2. curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/video/upload -F "file=@test_upload.mp4"
      3. 断言: HTTP 状态码为 200
      4. 解析响应 JSON — 提取视频 ID
      5. 断言: 响应包含 "id" 字段（UUID 格式）
      6. 断言: 目录 output/{video-id}/ 存在
      7. 断言: 视频文件存在于 output/{video-id}/ 内
    预期结果: 视频上传到每个视频独立目录，带 UUID
    证据: 响应体 + 目录列表已捕获

  场景: 列出视频返回所有已上传的视频
    工具: Bash (curl)
    前置条件: 至少上传了一个视频
    步骤:
      1. curl -s http://localhost:8000/api/videos
      2. 断言: HTTP 状态码 200
      3. 断言: 响应为 JSON 数组，至少包含 1 项
      4. 断言: 每项包含 id, filename, status, createdAt 字段
    预期结果: 返回视频列表
    证据: 响应体已捕获

  场景: 删除视频移除目录和数据库记录
    工具: Bash (curl)
    前置条件: 存在一个视频（使用上传场景中的 ID）
    步骤:
      1. curl -s -w "\n%{http_code}" -X DELETE http://localhost:8000/api/video/{video-id}
      2. 断言: HTTP 状态码 200
      3. 断言: 目录 output/{video-id}/ 不再存在
      4. curl -s -w "\n%{http_code}" http://localhost:8000/api/video/{video-id}
      5. 断言: HTTP 状态码 404
    预期结果: 视频完全删除（数据库 + 文件）
    证据: 响应体已捕获

  场景: 按 ID 获取单个视频
    工具: Bash (curl)
    前置条件: 存在一个视频
    步骤:
      1. 上传一个测试视频，获取 ID
      2. curl -s http://localhost:8000/api/video/{id}
      3. 断言: response.id 匹配
      4. 断言: response.filename 匹配上传的文件名
    预期结果: 正确获取单个视频
    证据: 响应体已捕获
  ```

  **提交**: 是
  - 消息: `feat(api): refactor video API for multi-video management with per-video directories`
  - 文件: `backend/services/video_service.py`, `backend/api/routes/video.py`, `backend/api/deps.py`, `backend/models/video.py`
  - 提交前检查: `cd backend && python -c "from api.routes.video import router; print('import ok')"`

---

- [ ] 3. 创建核心路径猴子补丁工具

  **任务内容**:
  - 创建 `backend/services/core_path_manager.py`，包含一个上下文管理器，临时覆盖 `core.utils.models` 路径常量
  - 上下文管理器:
    1. 保存 `core.utils.models` 中所有 `__all__` 属性的原始值
    2. 将每个字符串常量中的 `"output"` 前缀替换为 `"output/{video-id}"`
    3. 如果目标目录不存在，则创建 (`output/{video-id}/log/`, `output/{video-id}/audio/` 等)
    4. 退出时（或出错时），恢复所有原始值
  - 实现:
    ```python
    import core.utils.models as models
    from contextlib import contextmanager
    
    @contextmanager
    def video_output_context(video_id: str):
        """临时将核心模块输出路径重定向到每个视频独立目录"""
        originals = {}
        try:
            for attr in models.__all__:
                val = getattr(models, attr)
                if isinstance(val, str) and val.startswith("output"):
                    originals[attr] = val
                    new_val = f"output/{video_id}" + val[len("output"):]
                    setattr(models, attr, new_val)
            # 确保目录存在
            _ensure_video_dirs(video_id)
            yield
        finally:
            for attr, val in originals.items():
                setattr(models, attr, val)
    
    def _ensure_video_dirs(video_id: str):
        """为视频创建必要的子目录"""
        import os
        dirs = [
            f"output/{video_id}",
            f"output/{video_id}/log",
            f"output/{video_id}/gpt_log",
            f"output/{video_id}/audio",
            f"output/{video_id}/audio/refers",
            f"output/{video_id}/audio/segs",
            f"output/{video_id}/audio/tmp",
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)
    ```

  **禁止事项**:
  - 不得修改 `core/utils/models.py` — 只读
  - 不得使用 `os.chdir()` — 进程级副作用
  - 不得创建符号链接 — Windows 平台兼容性问题

  **推荐 Agent 配置**:
  - **类别**: `quick`
    - 原因: 单个工具文件，规格明确，范围小
  - **技能**: `[]`

  **并行化**:
  - **可并行执行**: 是
  - **并行组**: 批次 1（与任务 1, 5 同组）
  - **阻塞**: 任务 4
  - **被阻塞**: 无

  **参考资料**:

  **模式参考**:
  - `core/utils/models.py` — **被猴子补丁的模块**。`__all__` 列表中的所有 18 个常量（第 34-53 行）。所有以 `"output"` 前缀开头。
  - `core/utils/decorator.py:34-43` — `check_file_exists` 装饰器使用 `os.path.exists(file_path)` 检查这些常量。修补常量意味着装饰器会检查正确的路径。
  - `core/_2_asr.py:5,7` — 常量导入方式示例 (`from core.utils.models import *`) 和使用方式 (`@check_file_exists(_2_CLEANED_CHUNKS)`)。由于 `import *` 在导入时绑定名称，我们需要修补模块属性，而非局部变量。然而，由于核心模块执行 `from core.utils.models import *`，每个模块中的本地名称会成为独立副本。**关键**: 这意味着我们还需要修补每个核心模块中的局部变量，或者确保猴子补丁在核心模块导入之前执行。

  **关键调查说明**:
  > 每个核心模块中的 `from core.utils.models import *` 会创建字符串常量的本地副本。一旦导入完成，更改 `models._OUTPUT_DIR` 不会影响 `_2_asr._OUTPUT_DIR`。
  > 
  > 然而，核心模块是在处理服务方法中**延迟导入**的（例如 `def _run_asr(self): from core._2_asr import transcribe`）。如果我们在这些延迟导入发生之前修补 `core.utils.models`，并且 Python 尚未缓存核心模块，修补后的值将被采用。
  > 
  > **策略**: 要么 (A) 确保每次处理运行前核心模块不在 `sys.modules` 缓存中，这样延迟导入会使用修补后的值重新执行；要么 (B) 使用批量模式 — 将视频复制到扁平的 `output/`，处理后将结果移回 `output/{id}/`。
  > 
  > 更安全的方案是 **选项 B（批量模式）** — 它已经在 `batch_processing_service.py` 中得到验证。猴子补丁方案存在导入缓存风险。

  **修订方案**: 使用批量模式代替猴子补丁:
  1. 处理前: 确保 `output/`（扁平）是干净的，将视频文件从 `output/{video-id}/` 复制/链接到 `output/`
  2. 运行核心流水线阶段（它们照常写入 `output/`）
  3. 处理后: 将所有结果从 `output/` 移回 `output/{video-id}/`
  4. 这与 `batch_processing_service.py` 的做法完全一致

  **验收标准**:

  **Agent 执行的 QA 场景:**

  ```
  场景: 工具正确设置和清理视频输出上下文
    工具: Bash (python)
    前置条件: 项目根目录可访问，核心模块可导入
    步骤:
      1. python -c "
         from services.core_path_manager import setup_video_workspace, teardown_video_workspace
         import os
         # 设置
         setup_video_workspace('test-video-123', 'test.mp4')
         assert os.path.isdir('output'), 'output/ 应该存在'
         # 清理
         teardown_video_workspace('test-video-123')
         assert os.path.isdir('output/test-video-123'), 'output/test-video-123/ 应该存在'
         print('ALL PASSED')
         "
      2. 断言: 输出包含 "ALL PASSED"
    预期结果: 工作空间设置和清理正常工作
    证据: 命令输出已捕获
  ```

  **提交**: 是
  - 消息: `feat(core): add video workspace manager for per-video output directory isolation`
  - 文件: `backend/services/core_path_manager.py`
  - 提交前检查: `cd backend && python -c "from services.core_path_manager import setup_video_workspace; print('ok')"`

---

- [ ] 4. 在 ProcessingService 中集成每个视频独立处理

  **任务内容**:
  - 修改 `backend/services/processing_service.py`，使用 core_path_manager 实现每个视频独立的目录隔离
  - 运行流水线阶段之前:
    1. 调用 `setup_video_workspace(video_id, video_filename)` 将视频从 `output/{video-id}/` 复制/链接到扁平的 `output/`
    2. 正常运行所有核心阶段（它们写入 `output/`）
    3. 所有阶段完成后（或出错时），调用 `teardown_video_workspace(video_id)` 将结果从 `output/` 移到 `output/{video-id}/`
  - 更新 `run_subtitle_processing()` 和 `run_dubbing_processing()` 以包含工作空间设置/清理
  - 通过 `VideoDB` 更新视频状态，而非 `AppState`
  - 更新所有输出文件路径引用，在提供文件（字幕、配音视频等）时使用 `output/{video-id}/`

  **禁止事项**:
  - 不得更改核心模块的导入或行为
  - 不得修改 batch_processing_service.py
  - 不得允许并发处理不同视频（保持单处理约束）

  **推荐 Agent 配置**:
  - **类别**: `unspecified-high`
    - 原因: 修改 900+ 行的服务文件，需要仔细处理集成点
  - **技能**: `[]`

  **并行化**:
  - **可并行执行**: 是（在批次 2 内）
  - **并行组**: 批次 2（与任务 2, 6 同组）
  - **阻塞**: 任务 9
  - **被阻塞**: 任务 1, 3

  **参考资料**:

  **模式参考**:
  - `backend/services/processing_service.py:240-248` — 构造函数和 `_setup_core_imports()`。添加 `VideoDB` 实例化。
  - `backend/services/processing_service.py:257-350` — `run_subtitle_processing()` 流水线。包裹工作空间设置/清理。
  - `backend/services/processing_service.py:422-500` — `_run_stage()` 方法。此处无需更改。
  - `backend/services/processing_service.py:508-590` — 各个 `_run_*` 方法，延迟导入核心模块。保持不变。
  - `backend/services/batch_processing_service.py:52-99` — **参考模式**: `_clean_output_dir()`、`_copy_video_to_output()`、`_save_output()`。为 core_path_manager 适配此模式。

  **API/类型参考**:
  - `backend/database/video_db.py`（来自任务 1）— `VideoDB.update_video_status()` 用于跟踪处理状态
  - `backend/services/core_path_manager.py`（来自任务 3）— `setup_video_workspace()`, `teardown_video_workspace()`

  **验收标准**:

  **Agent 执行的 QA 场景:**

  ```
  场景: 处理服务使用每个视频独立工作空间
    工具: Bash (curl)
    前置条件: 后端运行中，已上传一个已知 ID 的视频
    步骤:
      1. 上传一个测试视频，从响应中获取 video_id
      2. curl -s -X POST http://localhost:8000/api/processing/start -H "Content-Type: application/json" -d '{"videoId": "{video_id}", "jobType": "subtitle"}'
      3. 断言: HTTP 状态码 200
      4. 等待 5 秒让第一个阶段开始
      5. 检查 output/ 目录是否有活动的处理文件
      6. 处理完成后（轮询 /api/processing/status/{video_id}）
      7. 断言: output/{video_id}/ 包含处理结果（log/、audio/ 子目录）
    预期结果: 处理输出存储在每个视频独立目录中
    证据: output/{video_id}/ 的目录列表已捕获

  场景: 处理失败仍然清理工作空间
    工具: Bash (curl)
    前置条件: 后端运行中
    步骤:
      1. 上传一个无效/空文件作为视频
      2. 启动处理（预期失败）
      3. 失败后，断言 output/{video_id}/ 目录仍然存在（保留部分结果）
      4. 断言扁平的 output/ 是干净的（工作空间已清理）
    预期结果: 即使失败也会清理工作空间
    证据: 目录状态已捕获
  ```

  **提交**: 是（与任务 3 一起分组）
  - 消息: `feat(processing): integrate per-video workspace isolation in processing pipeline`
  - 文件: `backend/services/processing_service.py`
  - 提交前检查: `cd backend && python -c "from services.processing_service import ProcessingService; print('ok')"`

---

- [ ] 5. 创建 VideoList 页面组件

  **任务内容**:
  - 创建 `frontend/src/pages/VideoList.tsx` — 新首页，卡片网格布局
  - 布局:
    - 头部: 应用名称 + 设置按钮（复用 App.tsx 中现有的 MainLayout）
    - 主体: 视频卡片网格（响应式: 移动端 1 列，平板 2 列，桌面端 3 列）
    - 空状态: 插画 + "上传你的第一个视频" CTA 按钮
    - "新建视频" 按钮（导航到新的视频创建流程或打开弹窗）
  - 每张视频卡片显示:
    - 缩略图图片（如果没有缩略图则显示占位图标）
    - 文件名（过长时截断显示省略号）
    - 时长（格式化为 MM:SS 或 HH:MM:SS）
    - 处理状态标签（颜色编码: ready=蓝色, processing=橙色, completed=绿色, error=红色）
    - 来源标签（上传图标或 YouTube 图标）
    - 创建时间（相对时间: "2 小时前"、"昨天"）
    - 删除按钮（带确认弹窗）
  - 使用 Ant Design 组件: `Card`, `Tag`, `Badge`, `Button`, `Modal`, `Empty`, `Row`, `Col`
  - 点击卡片主体使用 `useNavigate()` 导航到 `/video/{id}`

  **禁止事项**:
  - 不得添加分页、搜索或筛选
  - 不得添加拖拽排序
  - 不得使用外部日期库 — 使用简单的相对时间计算
  - 不得在 UI 中添加表情符号

  **推荐 Agent 配置**:
  - **类别**: `visual-engineering`
    - 原因: 前端 UI 页面，包含响应式网格布局、卡片组件、视觉设计
  - **技能**: `["frontend-ui-ux"]`
    - `frontend-ui-ux`: 卡片网格设计、响应式布局、空状态、视觉优化

  **并行化**:
  - **可并行执行**: 是
  - **并行组**: 批次 1（与任务 1, 3 同组）
  - **阻塞**: 任务 6
  - **被阻塞**: 无

  **参考资料**:

  **模式参考**:
  - `frontend/src/pages/Home.tsx` — **页面组件模式**: 现有页面的结构（导入、hooks、布局）。遵循相同的文件结构。
  - `frontend/src/pages/BatchUpload.tsx` — **另一个页面参考**: 展示不带 MainLayout 头部的备选布局模式。
  - `frontend/src/components/VideoUpload.tsx` — 已处理文件上传 + YouTube 下载的上传组件。可复用或适配为"新建视频"流程。
  - `frontend/src/App.tsx:28-76` — **MainLayout 组件**: 头部和底部布局。VideoList 应使用相同的布局包装器或类似的头部。

  **API/类型参考**:
  - `frontend/src/types/index.ts:Video`（第 9-20 行）— 视频接口，包含 id, filename, status, createdAt 等。
  - `frontend/src/types/index.ts:VideoStatus`（第 7 行）— 状态类型，用于标签颜色映射
  - `frontend/src/types/index.ts:VideoSourceType`（第 6 行）— 'upload' | 'youtube' 用于来源标签

  **文档参考**:
  - Ant Design Card: `https://ant.design/components/card` — Card 组件 API
  - Ant Design Grid: `https://ant.design/components/grid` — Row/Col 响应式网格

  **验收标准**:

  **Agent 执行的 QA 场景:**

  ```
  场景: VideoList 页面渲染空状态
    工具: Playwright (playwright skill)
    前置条件: 前端开发服务器运行在 localhost:5173，数据库中无视频
    步骤:
      1. 导航到: http://localhost:5173/
      2. 等待: 页面内容加载（超时: 10秒）
      3. 断言: 空状态消息可见（例如包含 "video" 文字或上传提示）
      4. 断言: "新建视频" 或上传按钮可见
      5. 截图: .sisyphus/evidence/task-5-empty-state.png
    预期结果: 干净的空状态，带上传 CTA
    证据: .sisyphus/evidence/task-5-empty-state.png

  场景: 有视频时 VideoList 页面渲染卡片
    工具: Playwright (playwright skill)
    前置条件: 前端 + 后端运行中，至少上传了 2 个视频
    步骤:
      1. 导航到: http://localhost:5173/
      2. 等待: 视频卡片出现（超时: 10秒）
      3. 断言: 至少 2 个卡片元素可见
      4. 断言: 每张卡片显示文件名文字
      5. 断言: 每张卡片显示状态标签
      6. 断言: 每张卡片有删除按钮或图标
      7. 截图: .sisyphus/evidence/task-5-video-cards.png
    预期结果: 卡片显示正确的视频信息
    证据: .sisyphus/evidence/task-5-video-cards.png

  场景: 点击视频卡片导航到详情页
    工具: Playwright (playwright skill)
    前置条件: 至少存在 1 个视频
    步骤:
      1. 导航到: http://localhost:5173/
      2. 等待: 视频卡片出现
      3. 点击: 第一张视频卡片的主体区域
      4. 等待: URL 变更为 /video/{some-id}（超时: 5秒）
      5. 断言: URL 匹配模式 /video/[uuid]
      6. 截图: .sisyphus/evidence/task-5-card-click-nav.png
    预期结果: 导航到视频详情页
    证据: .sisyphus/evidence/task-5-card-click-nav.png

  场景: 删除视频显示确认并移除卡片
    工具: Playwright (playwright skill)
    前置条件: 至少存在 1 个视频
    步骤:
      1. 导航到: http://localhost:5173/
      2. 等待: 视频卡片
      3. 记录: 卡片数量
      4. 点击: 第一张卡片上的删除按钮/图标
      5. 等待: 确认弹窗/对话框（超时: 3秒）
      6. 点击: 弹窗中的确认按钮
      7. 等待: 卡片消失或数量减少（超时: 5秒）
      8. 断言: 卡片数量减少 1
      9. 截图: .sisyphus/evidence/task-5-delete-confirm.png
    预期结果: 确认后删除视频
    证据: .sisyphus/evidence/task-5-delete-confirm.png
  ```

  **提交**: 是
  - 消息: `feat(ui): add VideoList page with card grid layout`
  - 文件: `frontend/src/pages/VideoList.tsx`
  - 提交前检查: `cd frontend && npm run build`

---

- [ ] 6. 重构前端路由

  **任务内容**:
  - 重构 `frontend/src/App.tsx`，使用正确的 React Router `<Route>` 组件:
    ```
    /                    → VideoList（新首页，MainLayout 包装器）
    /video/:id           → Home（重命名/重构为 VideoDetail，MainLayout 包装器）
    /video/:id/editor    → SubtitleEditor（独立布局，无头部/底部）
    /batch               → BatchUpload（独立布局）
    ```
  - 将使用 `location.pathname` 检查的 `AppRouter` 函数替换为正确的 `<Routes>` / `<Route>` 声明
  - 将 `MainLayout` 改为通过 `<Outlet />` 接受 `children`，使多个页面可以使用它
  - 将 `VideoList` 添加到懒加载导入
  - 在 VideoDetail (Home) 页面头部添加"返回列表"导航

  **禁止事项**:
  - 不得更改 BatchUpload 页面或其路由
  - 不得修改 SubtitleEditor 组件内部
  - 不得添加超出需要的嵌套路由布局

  **推荐 Agent 配置**:
  - **类别**: `visual-engineering`
    - 原因: 前端路由重构，涉及布局组件
  - **技能**: `["frontend-ui-ux"]`
    - `frontend-ui-ux`: 布局模式、导航用户体验

  **并行化**:
  - **可并行执行**: 是（在批次 2 内）
  - **并行组**: 批次 2（与任务 2, 4 同组）
  - **阻塞**: 任务 7
  - **被阻塞**: 任务 5

  **参考资料**:

  **模式参考**:
  - `frontend/src/App.tsx` — **要重构的完整文件**。当前路由使用 `location.pathname` 检查（第 79-102 行）。替换为正确的 `<Route>` 元素。
  - `frontend/src/App.tsx:28-76` — `MainLayout` 组件。需要重构为使用 `<Outlet />` 来渲染子路由。
  - `frontend/src/pages/Home.tsx` — 将成为在 `/video/:id` 渲染的 VideoDetail 页面。需要从 `useParams()` 读取 `video_id`。

  **API/类型参考**:
  - `react-router-dom` — `Routes`, `Route`, `Outlet`, `useParams`, `useNavigate`, `Link`

  **验收标准**:

  **Agent 执行的 QA 场景:**

  ```
  场景: 根路径显示 VideoList 页面
    工具: Playwright (playwright skill)
    前置条件: 前端开发服务器运行在 localhost:5173
    步骤:
      1. 导航到: http://localhost:5173/
      2. 等待: 页面内容（超时: 10秒）
      3. 断言: URL 恰好为 "/"
      4. 断言: VideoList 页面内容可见（卡片或空状态）
      5. 断言: 带设置按钮的应用头部可见
      6. 截图: .sisyphus/evidence/task-6-root-route.png
    预期结果: VideoList 在根路径渲染
    证据: .sisyphus/evidence/task-6-root-route.png

  场景: /video/:id 显示详情页
    工具: Playwright (playwright skill)
    前置条件: 至少存在一个视频
    步骤:
      1. 导航到: http://localhost:5173/video/{known-video-id}
      2. 等待: 视频详情内容（超时: 10秒）
      3. 断言: 处理面板或视频播放器可见
      4. 断言: 头部包含返回列表的导航
      5. 截图: .sisyphus/evidence/task-6-detail-route.png
    预期结果: 特定视频的详情页正常渲染
    证据: .sisyphus/evidence/task-6-detail-route.png

  场景: /video/:id/editor 显示字幕编辑器
    工具: Playwright (playwright skill)
    前置条件: 存在一个带字幕的视频
    步骤:
      1. 导航到: http://localhost:5173/video/{id}/editor
      2. 等待: 字幕编辑器内容（超时: 10秒）
      3. 断言: 编辑器布局可见（无应用头部/底部）
      4. 截图: .sisyphus/evidence/task-6-editor-route.png
    预期结果: 字幕编辑器渲染时不含主布局
    证据: .sisyphus/evidence/task-6-editor-route.png

  场景: /batch 仍然有效
    工具: Playwright (playwright skill)
    步骤:
      1. 导航到: http://localhost:5173/batch
      2. 等待: 批量上传页面内容（超时: 10秒）
      3. 断言: 批量上传页面正确渲染
      4. 截图: .sisyphus/evidence/task-6-batch-route.png
    预期结果: 批量功能未受影响
    证据: .sisyphus/evidence/task-6-batch-route.png
  ```

  **提交**: 是
  - 消息: `refactor(routing): restructure frontend routing with proper React Router routes`
  - 文件: `frontend/src/App.tsx`
  - 提交前检查: `cd frontend && npm run build`

---

- [ ] 7. 前端 API 集成和 VideoDetail 重构

  **任务内容**:
  - **更新 `frontend/src/services/api.ts`**:
    - 添加 `getVideos(): Promise<Video[]>` — `GET /api/videos`
    - 添加 `getVideo(id: string): Promise<Video>` — `GET /api/video/{id}`
    - 添加 `deleteVideo(id: string): Promise<void>` — `DELETE /api/video/{id}`
    - 更新 `uploadVideo()` 以返回带 ID 的 `Video`
    - 更新 `downloadYouTube()` 以返回带 ID 的 `Video`
    - 添加 `getVideoThumbnailUrl(id: string): string` — 返回缩略图 URL
    - 更新所有处理相关的 API 调用以包含 `video_id` 参数
    - 更新视频流 URL 使用 `/api/video/{id}/stream`
  - **重构 `frontend/src/pages/Home.tsx`**（变为 VideoDetail）:
    - 从 `useParams()` 读取 `video_id`
    - 挂载时使用 `getVideo(video_id)` 获取视频数据
    - 将 `video_id` 传递给所有子组件 (ProcessingPanel, VideoUpload 等)
    - 更新视频流 URL 使用每个视频的端点
    - 在页面头部添加"返回列表"按钮/链接
    - 处理 video_id 不存在的情况（显示错误，重定向到列表）
  - **更新 `frontend/src/types/index.ts`**:
    - 向 Video 接口添加 `thumbnailPath?: string`
    - 向 Video 接口添加 `updatedAt?: string`
  - **更新字幕编辑器导航**:
    - 将编辑器链接从 `/editor` 改为 `/video/${videoId}/editor`
    - 如需要，更新 SubtitleEditor.tsx 从 URL 参数读取 video_id

  **禁止事项**:
  - 不得重构 ProcessingPanel、VideoUpload 等组件内部（仅传递 video_id 属性）
  - 不得更改轮询逻辑（只确保使用正确的 video_id）
  - 不得修改字幕编辑器的内部状态管理

  **推荐 Agent 配置**:
  - **类别**: `unspecified-high`
    - 原因: 多文件更新，涉及 API 契约变更和组件属性传递
  - **技能**: `["frontend-ui-ux"]`
    - `frontend-ui-ux`: 组件重构、导航模式

  **并行化**:
  - **可并行执行**: 是（在批次 3 内）
  - **并行组**: 批次 3（与任务 8 同组）
  - **阻塞**: 任务 9
  - **被阻塞**: 任务 2, 6

  **参考资料**:

  **模式参考**:
  - `frontend/src/services/api.ts` — **要更新的 API 服务**。所有当前 API 调用都在这里。添加感知视频 ID 的端点。
  - `frontend/src/pages/Home.tsx` — **要重构为 VideoDetail 的页面**。目前假设全局单视频。必须通过 URL 中的 ID 参数化。
  - `frontend/src/pages/SubtitleEditor.tsx` — 检查它如何导航回 Home。更新为使用 `/video/${id}` 而非 `/`。
  - `frontend/src/components/ProcessingPanel.tsx` — 检查它是否直接进行 API 调用。如是，更新为使用 video_id。
  - `frontend/src/components/VideoUpload.tsx` — 上传组件。可能需要 video_id 上下文用于上传流程。
  - `frontend/src/hooks/usePolling.ts` — 轮询 hook。检查状态端点是否需要 video_id。

  **API/类型参考**:
  - `frontend/src/types/index.ts:Video`（第 9-20 行）— 添加 thumbnailPath 和 updatedAt
  - `frontend/src/types/index.ts:ProcessingStatus`（第 51-59 行）— 包含视频引用；可能需要 video_id 参数
  - 来自任务 2 的后端 API 契约: `GET /api/videos`, `GET /api/video/{id}`, `DELETE /api/video/{id}`

  **验收标准**:

  **Agent 执行的 QA 场景:**

  ```
  场景: VideoDetail 通过 ID 加载正确的视频
    工具: Playwright (playwright skill)
    前置条件: 后端 + 前端运行中，已上传已知 ID 的视频
    步骤:
      1. 导航到: http://localhost:5173/video/{known-id}
      2. 等待: 视频文件名出现在页面上（超时: 10秒）
      3. 断言: 显示的文件名匹配已上传视频的文件名
      4. 断言: 处理面板可见
      5. 截图: .sisyphus/evidence/task-7-detail-loads.png
    预期结果: 正确的视频数据已加载并显示
    证据: .sisyphus/evidence/task-7-detail-loads.png

  场景: VideoDetail 返回按钮回到列表
    工具: Playwright (playwright skill)
    前置条件: 在视频详情页上
    步骤:
      1. 导航到: http://localhost:5173/video/{id}
      2. 等待: 页面内容
      3. 点击: 返回列表按钮/链接
      4. 等待: URL 变为 "/"（超时: 5秒）
      5. 断言: VideoList 页面内容可见
      6. 截图: .sisyphus/evidence/task-7-back-to-list.png
    预期结果: 导航回视频列表
    证据: .sisyphus/evidence/task-7-back-to-list.png

  场景: 从详情页上传视频创建新视频
    工具: Playwright (playwright skill)
    前置条件: 前端运行中，在 VideoList 页面
    步骤:
      1. 导航到: http://localhost:5173/
      2. 点击: "新建视频" 按钮
      3. 上传一个测试视频文件
      4. 等待: 重定向到 /video/{new-id}（超时: 15秒）
      5. 断言: URL 匹配 /video/[uuid] 模式
      6. 断言: 已上传的文件名在页面上可见
      7. 截图: .sisyphus/evidence/task-7-upload-flow.png
    预期结果: 上传创建视频并重定向到详情页
    证据: .sisyphus/evidence/task-7-upload-flow.png

  场景: 无效的视频 ID 显示错误状态
    工具: Playwright (playwright skill)
    步骤:
      1. 导航到: http://localhost:5173/video/nonexistent-id-12345
      2. 等待: 错误状态或重定向（超时: 10秒）
      3. 断言: 显示错误消息或重定向到列表页
      4. 截图: .sisyphus/evidence/task-7-invalid-id.png
    预期结果: 优雅处理无效的视频 ID
    证据: .sisyphus/evidence/task-7-invalid-id.png
  ```

  **提交**: 是
  - 消息: `feat(ui): integrate video API and refactor Home to VideoDetail with URL params`
  - 文件: `frontend/src/services/api.ts`, `frontend/src/pages/Home.tsx`, `frontend/src/pages/SubtitleEditor.tsx`, `frontend/src/types/index.ts`
  - 提交前检查: `cd frontend && npm run build`

---

- [ ] 8. 现有输出数据的迁移逻辑

  **任务内容**:
  - 在 `backend/main.py` 启动时添加迁移逻辑（在数据库初始化之后）:
    1. 检查 `output/` 目录是否存在并直接包含视频文件（mp4, mkv, avi 等）（不在子目录中）
    2. 如果找到: 这是需要迁移的遗留单视频数据
    3. 为现有视频生成 UUID
    4. 创建 `output/{uuid}/` 目录
    5. 将 `output/` 的所有内容（文件和子目录如 `log/`, `audio/`, `gpt_log/`）移到 `output/{uuid}/`
    6. 创建数据库记录，包含视频的文件名、文件路径、status='completed'（如果没有处理产物则为 'ready'）
    7. 记录迁移日志
  - 迁移应该是幂等的 — 如果 `output/` 只包含 UUID 命名的子目录，则跳过迁移
  - 处理边界情况:
    - 空的 `output/` 目录 → 跳过
    - `output/` 不存在 → 跳过
    - 已经迁移（只有 UUID 风格命名的子目录）→ 跳过

  **禁止事项**:
  - 不得删除任何现有文件 — 只能移动
  - 如果没有需要迁移的内容，不得运行迁移
  - 不得因迁移错误阻塞启动（记录日志并继续）

  **推荐 Agent 配置**:
  - **类别**: `quick`
    - 原因: 单个函数，逻辑清晰，范围小
  - **技能**: `[]`

  **并行化**:
  - **可并行执行**: 是（在批次 3 内）
  - **并行组**: 批次 3（与任务 7 同组）
  - **阻塞**: 任务 9
  - **被阻塞**: 任务 1, 2

  **参考资料**:

  **模式参考**:
  - `backend/main.py` — 启动 lifespan 函数中数据库初始化的位置。在此添加迁移调用。
  - `backend/database/video_db.py`（来自任务 1）— `create_video()` 方法用于插入迁移的视频记录。
  - `backend/api/deps.py:18-19` — `OUTPUT_DIR = PROJECT_ROOT / "output"` — 需要检查遗留数据的目录。

  **验收标准**:

  **Agent 执行的 QA 场景:**

  ```
  场景: 迁移处理遗留单视频输出
    工具: Bash (python)
    前置条件: output/ 目录包含遗留数据（视频文件 + log/ + audio/ 子目录）
    步骤:
      1. 创建模拟遗留结构:
         mkdir -p output/log output/audio
         echo "test" > output/test_video.mp4
         echo "test" > output/log/cleaned_chunks.xlsx
      2. 运行迁移: python -c "from main import migrate_legacy_output; migrate_legacy_output()"
      3. 断言: output/ 不再直接包含 test_video.mp4
      4. 断言: output/ 恰好包含一个 UUID 命名的子目录
      5. 断言: output/{uuid}/test_video.mp4 存在
      6. 断言: output/{uuid}/log/cleaned_chunks.xlsx 存在
      7. 断言: 数据库中存在此视频的记录
    预期结果: 遗留数据迁移到每个视频独立目录
    证据: 目录列表和数据库查询输出已捕获

  场景: 迁移是幂等的（已迁移时为空操作）
    工具: Bash (python)
    前置条件: output/ 只包含 UUID 命名的子目录
    步骤:
      1. 再次运行迁移
      2. 断言: 没有创建新目录
      3. 断言: 输出中没有错误
    预期结果: 迁移被干净地跳过
    证据: 命令输出已捕获

  场景: 迁移处理空的 output 目录
    工具: Bash (python)
    前置条件: output/ 存在但为空
    步骤:
      1. mkdir -p output
      2. 运行迁移
      3. 断言: 没有错误，没有新目录
    预期结果: 空目录被优雅处理
    证据: 命令输出已捕获
  ```

  **提交**: 是
  - 消息: `feat(migration): add legacy output directory migration to per-video structure`
  - 文件: `backend/main.py`
  - 提交前检查: `cd backend && python -c "print('migration module ok')"`

---

- [ ] 9. 全面集成 QA

  **任务内容**:
  - 运行全面的端到端验证，覆盖整个多视频流程
  - 验证所有组件协同工作:
    1. 从干净状态开始（无视频）
    2. 上传一个视频 → 验证它出现在列表中
    3. 点击视频卡片 → 验证详情页加载
    4. 开始处理 → 验证输出进入每个视频独立目录
    5. 导航到字幕编辑器 → 验证它使用视频 ID 工作
    6. 导航回列表 → 验证卡片显示更新后的状态
    7. 上传第二个视频 → 验证两者都出现在列表中
    8. 删除第一个视频 → 验证目录已移除，卡片已移除
    9. 验证批量路由仍然工作
  - 修复 QA 过程中发现的任何集成问题

  **禁止事项**:
  - 不得跳过任何场景
  - 如果任何场景失败，不得标记为完成

  **推荐 Agent 配置**:
  - **类别**: `deep`
    - 原因: 复杂的端到端验证，需要深入调查和潜在的调试
  - **技能**: `["playwright"]`
    - `playwright`: 全面 UI 流程测试的浏览器自动化

  **并行化**:
  - **可并行执行**: 否
  - **并行组**: 顺序执行（最终任务）
  - **阻塞**: 无（最终）
  - **被阻塞**: 所有之前的任务

  **参考资料**:

  **所有之前任务的输出和交付物。**

  **验收标准**:

  **Agent 执行的 QA 场景:**

  ```
  场景: 完整视频生命周期 - 上传、查看、处理、删除
    工具: Playwright (playwright skill)
    前置条件: 后端 + 前端运行中，干净的数据库状态
    步骤:
      1. 导航到: http://localhost:5173/
      2. 断言: 显示空状态（无视频）
      3. 点击: "新建视频" / 上传按钮
      4. 上传: 一个测试视频文件（小文件，约 1 秒）
      5. 等待: 重定向到 /video/{id}（超时: 15秒）
      6. 断言: 视频详情页显示文件名
      7. 断言: 磁盘上目录 output/{id}/ 存在
      8. 导航到: http://localhost:5173/
      9. 断言: 1 张视频卡片可见
      10. 断言: 卡片显示正确的文件名和状态
      11. 点击: 视频卡片
      12. 断言: 回到详情页 /video/{id}
      13. 点击: 返回列表导航
      14. 断言: URL 为 "/"
      15. 点击: 视频卡片上的删除按钮
      16. 确认: 弹窗中的删除操作
      17. 等待: 卡片消失（超时: 5秒）
      18. 断言: 再次显示空状态
      19. 断言: 磁盘上目录 output/{id}/ 不再存在
      20. 截图: .sisyphus/evidence/task-9-full-lifecycle.png
    预期结果: 完整生命周期端到端工作正常
    证据: .sisyphus/evidence/task-9-full-lifecycle.png

  场景: 多个视频独立共存
    工具: Playwright (playwright skill)
    前置条件: 后端 + 前端运行中
    步骤:
      1. 上传视频 A
      2. 上传视频 B
      3. 导航到: http://localhost:5173/
      4. 断言: 2 张视频卡片可见
      5. 点击: 视频 A 的卡片
      6. 断言: 详情页显示视频 A 的文件名
      7. 导航回列表
      8. 点击: 视频 B 的卡片
      9. 断言: 详情页显示视频 B 的文件名
      10. 导航回列表
      11. 删除视频 A
      12. 断言: 剩余 1 张卡片（视频 B）
      13. 断言: output/{A-id}/ 已删除，output/{B-id}/ 仍存在
      14. 截图: .sisyphus/evidence/task-9-multi-video.png
    预期结果: 多个视频独立管理
    证据: .sisyphus/evidence/task-9-multi-video.png

  场景: 批量路由仍然正常
    工具: Playwright (playwright skill)
    步骤:
      1. 导航到: http://localhost:5173/batch
      2. 等待: 批量上传页面内容（超时: 10秒）
      3. 断言: 批量上传 UI 正确渲染
      4. 截图: .sisyphus/evidence/task-9-batch-intact.png
    预期结果: 批量功能未受影响
    证据: .sisyphus/evidence/task-9-batch-intact.png

  场景: 所有路由的直接 URL 导航正常
    工具: Playwright (playwright skill)
    前置条件: 至少存在 1 个视频
    步骤:
      1. 直接导航到: http://localhost:5173/ → 断言: 列表页
      2. 直接导航到: http://localhost:5173/video/{id} → 断言: 详情页
      3. 直接导航到: http://localhost:5173/video/{id}/editor → 断言: 编辑器页面
      4. 直接导航到: http://localhost:5173/batch → 断言: 批量页面
      5. 直接导航到: http://localhost:5173/video/invalid-uuid → 断言: 错误状态
      6. 每个截图: .sisyphus/evidence/task-9-route-{name}.png
    预期结果: 所有直接 URL 导航正常工作
    证据: 每个路由的截图
  ```

  **提交**: 是
  - 消息: `test(e2e): verify multi-video management integration`
  - 文件: QA 过程中发现的 bug 修复文件
  - 提交前检查: `cd frontend && npm run build`

---

## 提交策略

| 完成任务后 | 提交消息 | 关键文件 | 验证方式 |
|-----------|---------|---------|---------|
| 1 | `feat(db): add video database layer for multi-video management` | video_db.py, main.py | python 导入检查 |
| 2 | `feat(api): refactor video API for multi-video management with per-video directories` | video_service.py, video.py 路由, deps.py, models/video.py | python 导入检查 |
| 3 | `feat(core): add video workspace manager for per-video output directory isolation` | core_path_manager.py | python 导入检查 |
| 4 | `feat(processing): integrate per-video workspace isolation in processing pipeline` | processing_service.py | python 导入检查 |
| 5 | `feat(ui): add VideoList page with card grid layout` | VideoList.tsx | npm run build |
| 6 | `refactor(routing): restructure frontend routing with proper React Router routes` | App.tsx | npm run build |
| 7 | `feat(ui): integrate video API and refactor Home to VideoDetail with URL params` | api.ts, Home.tsx, SubtitleEditor.tsx, types/index.ts | npm run build |
| 8 | `feat(migration): add legacy output directory migration to per-video structure` | main.py | python 检查 |
| 9 | `test(e2e): verify multi-video management integration` | bug 修复文件 | npm run build |

---

## 成功标准

### 验证命令
```bash
# 后端无错误启动
cd backend && python -c "from main import app; print('Backend OK')"

# 前端无错误构建
cd frontend && npm run build

# 视频数据库模式正确
cd backend && python -c "
from database.video_db import VideoDB
db = VideoDB()
db.init_db()
print('DB OK')
"

# API 端点响应
curl -s http://localhost:8000/api/videos  # 应返回 []
curl -s -w '%{http_code}' http://localhost:8000/api/video/nonexistent  # 应返回 404
```

### 最终检查清单
- [ ] 视频列表页面在 `/` 渲染卡片网格
- [ ] 每个视频有 UUID 和专用的 `output/{id}/` 目录
- [ ] 视频上传创建数据库记录 + 目录
- [ ] 视频删除移除数据库记录 + 目录
- [ ] 处理流水线输出到每个视频独立目录
- [ ] 字幕编辑器可通过 `/video/:id/editor` 访问
- [ ] 批量路由 `/batch` 仍然工作
- [ ] 现有输出数据在首次启动时自动迁移
- [ ] 未修改任何 core/_*.py 文件
- [ ] 前端零错误构建
- [ ] 后端零错误启动

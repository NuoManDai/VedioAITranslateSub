# AGENTS.md — backend/

FastAPI 后端。分层架构：路由 → 服务 → 数据库。核心流水线通过 `asyncio.to_thread()` 调用。

## 概述

视频本地化 API 服务。管理视频、在后台线程编排 core 流水线、提供字幕/文件服务、通过日志环形缓冲区轮询进度。

## 目录结构

```
backend/
├── main.py              # 应用入口，生命周期，CORS，RequestLoggingMiddleware，sys.path.insert
├── deps.py              # AppState 单例，OUTPUT_DIR，get_app_state()
├── api/routes/
│   ├── __init__.py      # 导入所有路由器
│   ├── video.py         # /api/video/* 增删改查、上传、流媒体、缩略图、重命名
│   ├── processing.py    # /api/processing/* 启动/停止/状态 流水线
│   ├── config.py        # /api/config 读写 config.yaml
│   ├── logs.py          # /api/logs 轮询日志条目
│   ├── files.py         # /api/files/* 从 output 目录提供静态文件
│   └── subtitles.py     # /api/subtitles/* 字幕增删改查、合并、备份
├── services/
│   ├── video_service.py      # 上传、YouTube 下载、数据库、缩略图、流媒体
│   ├── processing_service.py # 流水线编排（835 行），TqdmCapture
│   ├── subtitle_service.py   # SRT 解析/写入、备份/恢复、合并（536 行）
│   ├── config_service.py     # 通过 ruamel.yaml 加载/保存 YAML（保留注释）
│   ├── log_service.py        # LogStore 环形缓冲区（deque，最大 1000）
│   ├── core_path_manager.py  # 流水线工作空间搭建/拆卸
│   └── tts_service.py        # TTS API 辅助方法
├── database/
│   └── video_db.py      # 原生 SQLite，CREATE TABLE IF NOT EXISTS，无 ORM
├── models/
│   ├── video.py         # Video、VideoResponse、YouTubeDownloadRequest、VideoRenameRequest
│   ├── job.py           # ProcessingJob、ProcessingStatus
│   ├── stage.py         # ProcessingStage、STAGE_OUTPUT_FILES、SUBTITLE/DUBBING_STAGES
│   ├── config.py        # Configuration、ConfigurationUpdate（大量字段）
│   ├── log.py           # LogEntry、LogQueryResponse
│   └── tts_config.py    # TTS 相关配置模型
├── tests/               # 空目录
└── data/videos.db       # SQLite（自动创建，相对于 backend/ 工作目录）
```

## 查找指南

| 任务 | 文件 | 备注 |
|------|------|------|
| 新端点 | `api/routes/` | 静态路由必须在 `/{video_id}` 之前 |
| 新 Pydantic 模型 | `models/` | 必须使用 `alias_generator=to_camel` |
| 业务逻辑 | `services/` | 一个领域一个服务 |
| 数据库变更 | `database/video_db.py` | 原生 SQL，无迁移机制 |
| 流水线集成 | `services/processing_service.py` | 延迟导入 core，用 `asyncio.to_thread()` 包装 |
| 配置读写 | `services/config_service.py` | ruamel.yaml，不直接访问文件 |
| 进度/日志 | `services/log_service.py` | 环形缓冲区，前端每 3 秒轮询 |
| 取消流水线 | `deps.py` + 文件系统 | 双标志：`AppState._cancel_requested` + `.cancel_requested` 文件 |

## 编码规范

- Pydantic：每个模型使用 `alias_generator=to_camel`、`populate_by_name=True`
- 序列化：`.model_dump(by_alias=True)` 输出 camelCase JSON
- Core 调用：延迟 `from core._N_xxx import fn`，始终在 `asyncio.to_thread()` 内
- 工作空间：`core_path_manager` 流水线前将文件拷贝到平铺 `output/`，流水线后移回
- 任务状态：仅存内存（`AppState._video_jobs` 字典），重启后从文件系统恢复
- 配置：`ConfigService.load_config()` 每次调用都重新读取，不缓存
- 路由注册：全部前缀 `/api/`，在 `api/routes/__init__.py` 中定义

## 反模式

1. **在 `async def` 中直接调用 core** ... core 使用阻塞 sleep。必须用 `asyncio.to_thread()`。
2. **扩展 AppState** ... 使用逐视频的 `_video_jobs` 字典，不要新增全局状态。
3. **添加 `sys.path.insert`** ... main.py 中已做过一次，不要重复。
4. **裸 `except:` 或静默捕获** ... 捕获特定异常，始终记录日志。
5. **使用 `core.utils.load_key()`** ... 通过 `ConfigService` 代替。
6. **更改 SQLite 路径** ... 必须保持相对于 `backend/` 工作目录。
7. **用 WebSocket/SSE 替代进度轮询** ... 系统使用轮询，不要引入新传输方式。

## 注意事项

- video.py 路由顺序：`/videos`、`/upload` 必须在 `/{video_id}` 之前，否则会被当作 ID 匹配。
- 任务状态重启后丢失。`processing_service` 在查询状态时从文件系统重建。
- `processing_service.py` 有 835 行，复杂度最高。修改前务必仔细阅读。
- `subtitle_service.py`（536 行）处理 SRT 解析、备份链和合并逻辑。
- `LogStore` 是 deque，上限 1000 条。旧日志静默丢弃。
- CORS 仅允许 `localhost:5173` 和 `127.0.0.1:5173`。
- 无测试。`backend/tests/` 为空。
- `data/videos.db` 首次查询时自动创建，无迁移系统。
- `tts_service.py` 使用普通 `yaml.dump`（不保留注释），与 `config_service.py` 不同。

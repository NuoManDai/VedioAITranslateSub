# AGENTS.md — backend/services/

后端服务层。一个领域一个服务。路由处理器委托到此。

## 文件一览

| 文件 | 用途 | 关键细节 |
|------|------|----------|
| `video_service.py` | 上传、YouTube 下载、数据库、缩略图、流媒体 | XHR 分片上传，yt-dlp 集成 |
| `processing_service.py` | 流水线编排（835 行） | `start_processing()` → `run_pipeline()` → 逐阶段执行。TqdmCapture 重定向 stdout/stderr。所有 core 调用通过 `asyncio.to_thread()`。阶段间检查 AppState 标志和文件系统哨兵来取消 |
| `subtitle_service.py` | SRT 解析/写入、备份/恢复、合并到视频（536 行） | 在 `output/{video_id}/` 工作空间中读写 `.srt` |
| `config_service.py` | YAML 配置加载/保存 | `ruamel.yaml` 保留注释。每次调用重新读取，不缓存。验证 API 密钥，管理环境变量（`HTTP_PROXY`、`HF_ENDPOINT`） |
| `log_service.py` | 线程安全日志环形缓冲区 | `LogStore`：deque（最大 1000 条）。`add()` + `query(last_id=N)`。由 TqdmCapture 填充 |
| `core_path_manager.py` | 工作空间隔离 | `setup_video_workspace()`：将视频拷贝到平铺 `output/`。`teardown_video_workspace()`：将结果移到 `output/{uuid}/`。Core 硬编码 `output/` 路径 |
| `tts_service.py` | TTS 提供者封装 | TTS 后端的轻量 API 辅助方法 |

## 数据流

```
路由处理器
  → 服务方法
    → 数据库 (video_db) / 配置 (ConfigService) / core 流水线 (asyncio.to_thread)

处理流程（详细）：
  start_processing()
    → core_path_manager.setup_video_workspace()
    → run_pipeline() 阶段 1..12
    → core_path_manager.teardown_video_workspace()
    → 更新 AppState._video_jobs 中的任务状态

日志积累：
  TqdmCapture → LogStore.add() → 前端轮询 /api/logs → LogStore.query(last_id)
```

## 编码规范

- 一个领域一个服务，一个路由文件对应一个服务
- 同步类，需要时使用异步方法
- Core 调用必须通过 `asyncio.to_thread()`。Core 使用阻塞 sleep/IO。
- 配置始终重新读取，不缓存配置对象
- 任务状态仅存内存（`AppState._video_jobs` 字典），重启后从文件系统恢复
- 取消使用双标志：内存 `AppState._cancel_requested` + 文件系统 `.cancel_requested` 文件

## 反模式

1. **不用 `asyncio.to_thread()` 调用 core** 会阻塞事件循环。所有 core 函数都是同步的。
2. **直接读取 `config.yaml`** 绕过验证和环境变量设置。使用 `ConfigService`。
3. **添加没有对应路由的服务** 会留下死代码。
4. **继续扩展 `processing_service.py`**。已有 835 行，新增阶段应抽取为独立函数。
5. **缓存配置** 破坏"每次调用重新读取"的契约。用户期望配置修改立即生效。
6. **在服务中使用 `os.chdir()`**。与异步存在竞态条件。使用 `core_path_manager` 代替。

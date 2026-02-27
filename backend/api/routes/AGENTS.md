# AGENTS.md — backend/api/routes/

REST 端点定义。薄层：验证输入 → 调用服务 → 返回响应。

## 路由一览

| 文件 | 前缀 | 端点 | 备注 |
|------|------|------|------|
| `video.py` | `/api/video` | `GET /s`（列表）、`POST /upload`、`POST /youtube`、`GET /{id}`、`GET /{id}/stream`、`GET /{id}/thumbnail`、`PATCH /{id}` | 静态路由必须在 `/{video_id}` 之前否则无法匹配 |
| `processing.py` | `/api/processing` | `POST /start/{id}`、`POST /stop/{id}`、`GET /status/{id}` | 状态查询时若内存中无记录则从文件系统恢复 |
| `config.py` | `/api/config` | `GET /`、`POST /` | 通过服务层读写 `config.yaml` |
| `logs.py` | `/api/logs` | `GET /?lastId=N` | 仅增量查询，返回 `lastId` 之后的日志 |
| `files.py` | `/api/files` | `GET /{video_id}/{filename}`、`GET /output/{filename}` | 从 `output/` 目录提供静态文件 |
| `subtitles.py` | `/api/subtitles` | `GET/PUT /{id}/subtitle`、`POST /{id}/merge`、`POST /{id}/backup`、`POST /{id}/restore`、`GET /{id}/audio/stream` | `.srt` 文件完整 CRUD + 音频流 |

## 编码规范

- 此处零业务逻辑。路由 → 服务 → 响应。
- 请求/响应体使用 Pydantic 模型，带 `alias_generator=to_camel`。
- 用 `.model_dump(by_alias=True)` 序列化为 camelCase JSON 输出。
- 错误：抛出 `HTTPException(status_code=..., detail=...)`。
- 新路由器？添加到 `__init__.py` 以便 `main.py` 自动注册。

## 注意事项

- **路由顺序会静默出错。** `video.py` 中 `/videos` 和 `/upload` 定义在 `/{video_id}` 之前。顺序反了 FastAPI 会把字面路径当作视频 ID 匹配。不报错，只返回错误数据。
- **`/api/videos` vs `/api/video`**：路由器前缀是 `/api/video`（单数）。列表端点加了 `s` 后缀，即 `router.get("s")` 生成 `/api/videos`。
- **`files.py` 前缀**：`/api/files`，未归入 video 路由组。还暴露了 `/output/{filename}` 兼容旧版平铺目录。
- **处理状态恢复**：`GET /status/{id}` 先查内存任务字典，回退到文件系统标记。服务重启后首次状态轮询会重建状态。
- **日志轮询**：客户端首次调用发送 `lastId=0`，之后使用响应中的最大 ID。缺省 `lastId` 参数返回全部日志。

# Quick Start: VedioAITranslateSub

本指南帮助您快速启动前后端分离版本的视频翻译应用。

## 前提条件

- Conda 已安装
- Node.js 18+ 已安装
- 已有 `videolingo` conda 环境（或愿意创建新环境）

## 1. 后端启动

### 1.1 激活环境并安装依赖

```bash
# 激活现有 VideoLingo 环境
conda activate videolingo

# 安装 FastAPI 相关依赖
pip install fastapi uvicorn python-multipart
```

### 1.2 启动后端服务

```bash
# 进入后端目录
cd backend

# 启动开发服务器（带热重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**验证**: 访问 http://localhost:8000/docs 查看 Swagger 文档

## 2. 前端启动

### 2.1 安装依赖

```bash
# 新开终端，进入前端目录
cd frontend

# 安装 Node 依赖
npm install
```

### 2.2 启动前端开发服务器

```bash
npm run dev
```

**验证**: 访问 http://localhost:5173 查看前端界面

## 3. 使用流程

1. **上传视频**: 在首页拖拽或选择视频文件上传，或输入 YouTube 链接下载
2. **处理字幕**: 视频就绪后，点击"开始处理字幕"按钮
3. **查看进度**: 观察各处理阶段的实时状态更新
4. **下载结果**: 处理完成后，可预览带字幕视频或下载 SRT 文件
5. **配音处理**: （可选）字幕完成后，可继续进行配音处理

## 4. 配置说明

点击右上角设置按钮打开配置面板：

- **LLM API**: 配置 API Key、Base URL、模型名称
- **语言设置**: 设置识别语言和翻译目标语言
- **Whisper 设置**: 选择本地/云端运行模式
- **TTS 设置**: 选择配音方法和相关参数

## 5. 常见问题

### Q: 后端启动失败？

确保在正确的 conda 环境中：
```bash
conda activate videolingo
which python  # 应显示 videolingo 环境路径
```

### Q: 前端无法连接后端？

1. 确认后端服务已启动并监听 8000 端口
2. 检查 `frontend/.env.local` 中的 API 地址：
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```

### Q: 进度不更新？

前端每 2 秒轮询一次，如果长时间无更新：
1. 检查后端控制台是否有错误
2. 刷新页面重试

## 6. 目录结构速览

```
project/
├── backend/           # FastAPI 后端
│   ├── main.py       # 应用入口
│   └── api/          # API 路由
├── frontend/          # React 前端
│   ├── src/          # 源代码
│   └── package.json  # Node 依赖
├── core/             # 处理逻辑（不修改）
├── config.yaml       # 配置文件
└── output/           # 输出目录
```

## 7. 开发命令速查

| 命令 | 说明 |
|------|------|
| `uvicorn main:app --reload` | 启动后端（开发模式） |
| `npm run dev` | 启动前端（开发模式） |
| `npm run build` | 构建前端生产版本 |
| `npm run preview` | 预览生产构建 |

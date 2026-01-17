# 环境配置指南

本文档说明如何为前后端分离重构项目配置开发环境。

## ⚠️ 重要提醒

**禁止全局 pip 安装！** 所有 Python 包必须安装在 conda 虚拟环境中。

## 后端环境 (Python/FastAPI)

### 使用现有 VideoLingo 环境

如果您已有 `videolingo` conda 环境，可以直接扩展使用：

```bash
# 激活现有环境
conda activate videolingo

# 安装 FastAPI 相关依赖（在环境内）
pip install fastapi uvicorn python-multipart

# 验证安装
python -c "import fastapi; print(f'FastAPI {fastapi.__version__} OK')"
```

### 创建新环境（推荐用于隔离开发）

```bash
# 创建新环境，基于 Python 3.10（与 VideoLingo 兼容）
conda create -n videolingo-api python=3.10.0 -y

# 激活环境
conda activate videolingo-api

# 安装后端依赖
pip install -r backend/requirements.txt
```

### 后端依赖清单 (backend/requirements.txt)

```
# FastAPI 核心
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6

# 从原项目继承的依赖
# （在 backend/requirements.txt 中引用或复制 requirements.txt）
-r ../requirements.txt
```

## 前端环境 (React/TypeScript)

### 前提条件

- Node.js 18.x 或更高版本
- npm 或 yarn 包管理器

### 安装前端依赖

```bash
cd frontend

# 使用 npm
npm install

# 或使用 yarn
yarn install
```

### 前端主要依赖

- React 18.x
- TypeScript 5.x
- TailwindCSS 3.x
- Ant Design 5.x
- Vite (构建工具)

## 开发启动流程

### 1. 启动后端服务

```bash
# 激活 conda 环境
conda activate videolingo  # 或 videolingo-api

# 进入后端目录
cd backend

# 启动开发服务器（带热重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Swagger 文档访问地址: http://localhost:8000/docs
```

### 2. 启动前端服务

```bash
# 新开终端，进入前端目录
cd frontend

# 启动开发服务器
npm run dev

# 前端访问地址: http://localhost:5173
```

## 环境变量配置

### 后端 (.env)

```env
# 可选：覆盖默认配置文件路径
CONFIG_PATH=../config.yaml

# 开发模式
DEBUG=true
```

### 前端 (.env.local)

```env
# API 基础地址
VITE_API_BASE_URL=http://localhost:8000

# 开发模式
VITE_DEV_MODE=true
```

## 目录结构预览

```
project-root/
├── backend/                 # FastAPI 后端
│   ├── main.py             # 应用入口
│   ├── requirements.txt    # Python 依赖
│   ├── api/                # API 路由
│   ├── models/             # 数据模型
│   └── services/           # 业务逻辑
├── frontend/               # React 前端
│   ├── package.json        # Node 依赖
│   ├── src/
│   │   ├── components/     # UI 组件
│   │   ├── pages/          # 页面
│   │   ├── services/       # API 调用
│   │   └── i18n/           # 国际化
│   └── public/
├── core/                   # 原有处理逻辑（保持不变）
├── config.yaml             # 配置文件
└── output/                 # 输出目录
```

## 常见问题

### Q: pip 安装提示权限错误？

确保您已激活 conda 环境：
```bash
conda activate videolingo
which pip  # 应显示 conda 环境内的 pip 路径
```

### Q: 前端无法连接后端？

1. 确认后端服务已启动并监听 8000 端口
2. 检查 CORS 配置是否允许前端域名
3. 确认 `.env.local` 中的 API 地址正确

### Q: 如何同时运行前后端？

使用两个终端分别运行，或使用 `concurrently` 等工具：
```bash
npm install -g concurrently
concurrently "cd backend && uvicorn main:app --reload" "cd frontend && npm run dev"
```

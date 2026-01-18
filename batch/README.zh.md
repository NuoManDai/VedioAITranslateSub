# VideoLingo Batch Mode

[English](./README.md) | [简体中文](./README.zh.md)

批量处理多个视频的字幕翻译和配音任务。

## 前置条件

在使用批处理模式前，请确保：
1. 已正确配置 `config.yaml` 中的 API 密钥等参数
2. 后端服务正在运行（`start_backend.bat`）

## 使用方法

### 1. 准备视频文件

- 将要处理的视频文件放入 `batch/input` 文件夹

### 2. 配置任务

编辑 `tasks_setting.xlsx` 文件：

| 字段 | 说明 | 可选值 |
|------|------|--------|
| Video File | 视频文件名（无需 `input/` 前缀） | - |
| Source Language | 源语言 | 'en', 'zh', ... 或留空使用默认设置 |
| Target Language | 翻译目标语言 | 使用自然语言描述，或留空使用默认设置 |
| Dubbing | 是否配音 | 0 或留空：仅字幕；1：字幕+配音 |
| Status | 任务状态（自动填写） | Done / Error: ... |

示例：

| Video File | Source Language | Target Language | Dubbing | Status |
|------------|-----------------|-----------------|---------|--------|
| video1.mp4 | en | 简体中文 | 0 | |
| video2.mp4 | ja | English | 1 | |
| video3.mp4 | | | 1 | Done |

### 3. 启动后端服务

在一个终端窗口中运行：
```bash
# Windows
.\start_backend.bat

# PowerShell
.\start_backend.ps1
```

### 4. 运行批处理

在另一个终端窗口中：
```bash
# 进入 batch 目录运行
cd batch
OneKeyBatch.bat
```

或者从项目根目录运行：
```bash
python -m batch.utils.batch_processor
```

### 5. 查看结果

- 成功的输出保存在 `batch/output/{视频名}/`
- 失败的输出保存在 `batch/output/ERROR/{视频名}/`
- 任务状态记录在 `tasks_setting.xlsx` 的 `Status` 列

> ⚠️ 注意：运行时请保持 `tasks_setting.xlsx` 关闭，否则会因文件占用而无法写入状态。

## 错误处理

### 重试失败任务

如果任务失败（Status 列显示 `Error: ...`）：
1. 检查并修复问题（如 API 配额、网络等）
2. 重新运行 `OneKeyBatch.bat`
3. 程序会自动从 ERROR 文件夹恢复中间文件并继续处理

### 跳过已完成任务

Status 为 `Done` 的任务会自动跳过。如需重新处理，清空对应的 Status 单元格即可。

## 目录结构

```
batch/
├── input/              # 放置待处理的视频文件
├── output/             # 处理完成的输出
│   ├── video1/         # 成功的输出
│   └── ERROR/          # 失败的输出（用于重试）
│       └── video2/
├── tasks_setting.xlsx  # 任务配置表
├── OneKeyBatch.bat     # 一键启动脚本
└── utils/
    └── batch_processor.py  # 批处理核心逻辑
```

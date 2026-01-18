# 002 - 字幕配音分离与日语支持优化

## 概述

本规范定义了字幕处理与配音处理的分离、日语 NLP 分句支持、以及相关 UI 改进。

## 目标

1. **字幕/配音流程分离** - 允许用户独立运行字幕处理和配音处理
2. **日语分词支持** - 解决日语 ASR 输出缺少标点导致无法分句的问题
3. **处理状态恢复** - 支持从已完成的输出文件恢复处理状态
4. **文件预览功能** - 在前端展示处理阶段的输出文件
5. **重启/清理功能** - 允许用户清理中间文件并重新开始处理

## 技术方案

### 1. 日语 NLP 分句

#### 问题分析
- WhisperX 对日语使用字符级对齐（wav2vec2），返回逐字时间戳
- 日语 ASR 输出几乎没有句号 `。`
- spaCy 的日语句子边界检测主要依赖标点符号

#### 解决方案
在 `core/spacy_utils/split_by_mark.py` 中为日语添加基于时间间隔和语法模式的分句逻辑：

```python
def split_japanese_by_time_and_grammar(chunks_df, nlp, gap_threshold=0.3):
    """
    日语分句策略：
    1. 时间间隔检测：chunk 间隔 > 0.3秒时分句
    2. 标点符号检测：遇到 ! ? 。等标点时分句
    3. 敬语结尾检测：ます、です 等敬语结尾且有小间隔时分句
    """
```

### 2. 处理状态恢复

#### 后端实现
`backend/services/processing_service.py`:
- `detect_completed_stages()` - 检测已完成的处理阶段
- `is_subtitle_processing_completed()` - 检查字幕处理是否完成
- `is_dubbing_processing_completed()` - 检查配音处理是否完成
- `restore_job_state()` - 从输出文件恢复任务状态

#### 阶段输出文件映射
`backend/models/stage.py` 中的 `STAGE_OUTPUT_FILES`:

```python
STAGE_OUTPUT_FILES = {
    'asr': ['output/log/cleaned_chunks.xlsx', 'output/audio/raw.mp3', ...],
    'split_nlp': ['output/log/split_by_nlp.txt'],
    'translate': ['output/log/translation_results.xlsx', ...],
    # ...
}
```

### 3. 文件预览 API

#### 端点
- `GET /api/files/stage/{stage_name}` - 获取阶段输出文件列表
- `GET /api/files/preview` - 预览文件内容
- `GET /api/files/download` - 下载文件
- `GET /api/files/folder` - 列出文件夹内容

#### 前端组件
`frontend/src/components/StageOutputFiles.tsx`:
- 显示已完成阶段的输出文件
- JSON 语法高亮预览
- 支持文本、Excel、SRT 等格式预览

### 4. 清理功能

#### API 端点
- `POST /api/processing/cleanup/subtitle` - 清理字幕处理文件
- `POST /api/processing/cleanup/dubbing` - 清理配音处理文件
- `POST /api/processing/cleanup/all` - 清理所有处理文件

#### 清理范围
```python
SUBTITLE_CLEANUP_PATTERNS = [
    'output/log/*.txt', 'output/log/*.xlsx', 'output/log/*.json',
    'output/*.srt', 'output/output_sub.mp4'
]
DUBBING_CLEANUP_PATTERNS = [
    'output/audio/segs/*', 'output/audio/refers/*',
    'output/audio/trans_*.mp3', 'output/output_dub.mp4'
]
```

### 5. UI 改进

#### ProcessingPanel 重构
- Tab 布局分离字幕/配音处理
- 每个 Tab 独立显示进度和状态
- 重启按钮和清理缓存功能

#### ConsolePanel 新增
- 实时日志监控
- 支持按级别和来源过滤
- 自动滚动和全屏模式

#### VideoPlayer 增强
- 字幕切换开关（显示/隐藏已烧录字幕版本）

## 文件变更

### 新增文件
- `backend/api/routes/files.py` - 文件预览 API
- `backend/api/routes/logs.py` - 日志 API
- `backend/models/log.py` - 日志模型
- `backend/models/tts_config.py` - TTS 配置模型
- `backend/services/log_service.py` - 日志服务
- `backend/services/tts_service.py` - TTS 服务
- `frontend/src/components/ConsolePanel.tsx` - 控制台面板
- `frontend/src/components/StageOutputFiles.tsx` - 阶段输出文件
- `frontend/src/components/settings/*.tsx` - 设置组件拆分

### 修改文件
- `core/spacy_utils/split_by_mark.py` - 添加日语分句逻辑
- `backend/services/processing_service.py` - 添加状态恢复逻辑
- `backend/models/stage.py` - 扩展阶段输出文件映射
- `frontend/src/components/ProcessingPanel.tsx` - Tab 布局重构
- `frontend/src/components/SettingsModal.tsx` - 设置组件拆分
- `frontend/src/components/VideoPlayer.tsx` - 字幕切换功能

### 删除文件
- `st.py` - 旧版 Streamlit 入口
- `install.py` - 旧版安装脚本
- `translations/*.json` - 旧版翻译文件（已移至 frontend/src/i18n）
- `core/st_utils/*` - Streamlit 工具函数

## 配置变更

### config.yaml
无需额外配置，日语分句自动启用。

## 测试要点

1. **日语视频处理**
   - 上传日语视频
   - 验证 ASR 输出正确
   - 验证分句结果合理（约 15-30 句/分钟）

2. **状态恢复**
   - 完成处理后关闭应用
   - 重新打开验证状态正确恢复

3. **文件预览**
   - 检查各阶段输出文件是否显示
   - 验证 JSON、文本、Excel 预览正常

4. **清理功能**
   - 测试字幕清理不影响配音文件
   - 测试配音清理不影响字幕文件
   - 测试全部清理后状态重置

## 已知限制

1. 日语分句依赖时间间隔，对语速很快的视频效果可能不佳
2. 长句子需要依赖后续 `split_by_meaning` 阶段（LLM）进一步分割
3. 文件预览对大文件有行数限制（默认 500 行）

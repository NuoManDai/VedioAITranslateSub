# Changelog

所有重要的版本变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [1.0.0] - 2025-01-31

### 新增

#### 核心功能
- **视频上传与下载**: 支持本地视频上传和 YouTube 视频下载（yt-dlp）
- **语音识别 (ASR)**: 集成 WhisperX，支持词级时间戳和低幻觉转录
- **NLP 智能分句**: 基于 spaCy 的文本粗切分 + GPT 语义分句
- **AI 翻译**: 三步翻译-反思-调整流程，支持术语表一致性
- **字幕生成**: Netflix 标准单行字幕，自动分割和时间轴对齐
- **配音合成**: 支持多种 TTS 后端（Azure、OpenAI、Fish TTS、GPT-SoVITS 等）
- **语音克隆**: 支持 Fish TTS、CosyVoice2、F5-TTS 语音克隆

#### 前端界面
- **现代化 UI**: React 18 + Ant Design 5 + TailwindCSS
- **字幕编辑器**: 波形可视化、时间轴编辑、实时预览
- **处理面板**: 分步骤进度展示（字幕处理、校对合并、配音处理）
- **设置管理**: API 配置、模型选择、处理参数可视化配置
- **多语言支持**: 中文/英文/日文/韩文界面

#### 后端架构
- **FastAPI**: RESTful API 设计，Swagger 文档自动生成
- **异步处理**: 后台任务队列，实时进度推送
- **状态管理**: 处理阶段状态持久化，支持断点续传
- **配置系统**: YAML 配置文件，API 动态修改

### 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.109+, Python 3.10+ |
| 前端框架 | React 18, TypeScript 5.3+, Vite 5 |
| UI 组件 | Ant Design 5.12, TailwindCSS 3.4 |
| 语音识别 | WhisperX (faster-whisper-large-v3) |
| 深度学习 | PyTorch 2.9+, CUDA 12.8 |
| 音视频处理 | FFmpeg, moviepy, pydub |

---

## 版本规划

### [1.1.0] - 计划中
- [ ] 批量视频处理
- [ ] 多说话人识别与分离配音
- [ ] 字幕样式自定义（字体、颜色、位置）
- [ ] 导出格式扩展（ASS、VTT）

### [1.2.0] - 计划中
- [ ] 云端部署支持
- [ ] 用户认证与多租户
- [ ] 处理历史记录
- [ ] WebSocket 实时进度推送

---

## 贡献

欢迎提交 Issue 和 Pull Request！

- [提交 Bug](https://github.com/NuoManDai/VedioAITranslateSub/issues)
- [功能建议](https://github.com/NuoManDai/VedioAITranslateSub/issues)
- [Pull Request](https://github.com/NuoManDai/VedioAITranslateSub/pulls)

# Research: 字幕配音分离与日语支持优化

**Feature**: 002-dubbing-subtitle-separation  
**Date**: 2026-01-18

## 研究任务

### 1. 日语 ASR 输出分析

**问题**: 为什么日语视频的分句结果只有一行？

**分析过程**:
1. 检查 WhisperX ASR 输出 `cleaned_chunks.xlsx`
2. 发现日语使用字符级对齐（wav2vec2 模型）
3. 每个字符单独一行，时间戳精确到字符级别
4. 统计标点符号：句号 `。` 数量为 0

**结论**: 
- WhisperX 对日语使用 `jonatasgrosman/wav2vec2-large-xlsr-53-japanese` 模型进行字符级对齐
- 这是非空格语言（日语、中文）的正常行为
- ASR 输出几乎不包含标点符号
- spaCy 的句子边界检测主要依赖标点，导致无法分句

**数据样例**:
```
| text | start | end |
|------|-------|-----|
| 今   | 0.50  | 0.52|
| 回   | 0.52  | 0.54|
| は   | 0.54  | 0.56|
| ...  | ...   | ... |
```

### 2. spaCy 日语分句机制

**问题**: spaCy 如何检测日语句子边界？

**分析**:
- spaCy 使用 `is_sent_start` 属性标记句子开始
- 日语模型 `ja_core_news_md` 主要依赖：
  1. 标点符号（句号、问号、感叹号）
  2. 换行符
  3. 特定的语法模式

**测试代码**:
```python
import spacy
nlp = spacy.load("ja_core_news_md")
text = "今回は動画を作成しますそして翻訳もします"  # 无标点
doc = nlp(text)
sentences = list(doc.sents)
# 结果: 只有 1 个句子
```

**结论**: 无标点时 spaCy 无法有效分句，需要额外策略

### 3. 日语分句替代策略

**问题**: 如何在无标点情况下分割日语句子？

**方案比较**:

| 方案 | 优点 | 缺点 |
|------|------|------|
| 时间间隔检测 | 简单可靠，语音停顿通常对应句子边界 | 需要调优阈值 |
| 敬语结尾检测 | 日语特有，准确度高 | 仅适用于敬体文 |
| 句尾助词检测 | 覆盖常见句式 | 需要小间隔辅助判断 |
| LLM 分句 | 最准确 | 成本高，延迟大 |

**决策**: 组合使用前三种策略
1. 时间间隔 > 0.3s 作为主要分句依据
2. 检测敬语结尾（ます、です、ました、でした）
3. 检测句尾助词（ね、よ、か、な、わ）配合小间隔

### 4. 时间间隔阈值研究

**问题**: 最佳的时间间隔阈值是多少？

**实验数据**:
| 阈值 | 分句数 | 效果 |
|------|--------|------|
| 0.1s | 过多 | 碎片化严重 |
| 0.2s | 较多 | 略有碎片 |
| 0.3s | 适中 | 效果较好 |
| 0.5s | 较少 | 可能漏分 |
| 1.0s | 很少 | 明显漏分 |

**结论**: 0.3s 是合适的阈值，与语音的自然停顿吻合

### 5. 处理状态恢复机制

**问题**: 如何从输出文件判断处理进度？

**分析**:
- 每个处理阶段产生特定的输出文件
- 检查这些文件是否存在即可判断阶段完成状态

**阶段-文件映射**:
```python
STAGE_OUTPUT_FILES = {
    'asr': ['output/log/cleaned_chunks.xlsx', 'output/audio/raw.mp3'],
    'split_nlp': ['output/log/split_by_nlp.txt'],
    'split_meaning': ['output/log/split_by_meaning.txt'],
    'summarize': ['output/log/terminology.json'],
    'translate': ['output/log/translation_results.xlsx'],
    'split_sub': ['output/log/translation_results_for_subtitles.xlsx'],
    'gen_sub': ['output/src.srt', 'output/trans.srt'],
    'sub_into_vid': ['output/output_sub.mp4'],
    # 配音阶段
    'audio_task': ['output/audio/sovits_tasks.xlsx'],
    'dub_chunks': ['output/audio/segs/'],
    'refer_audio': ['output/audio/refers/'],
    'gen_audio': ['output/audio/trans_vocal.mp3'],
    'merge_audio': ['output/audio/trans_vocal_mixed.mp3'],
    'dub_to_vid': ['output/output_dub.mp4'],
}
```

### 6. 文件清理策略

**问题**: 如何安全地清理处理文件？

**分析**:
- 字幕处理和配音处理的文件相互独立
- 需要分别定义清理范围

**清理范围**:
```python
SUBTITLE_CLEANUP_PATTERNS = [
    'output/log/*.txt',
    'output/log/*.xlsx', 
    'output/log/*.json',
    'output/*.srt',
    'output/output_sub.mp4'
]

DUBBING_CLEANUP_PATTERNS = [
    'output/audio/segs/*',
    'output/audio/refers/*',
    'output/audio/trans_*.mp3',
    'output/output_dub.mp4'
]
```

**决策**: 提供三个清理端点
- `/cleanup/subtitle` - 仅清理字幕相关
- `/cleanup/dubbing` - 仅清理配音相关
- `/cleanup/all` - 清理全部

## 技术栈确认

| 组件 | 选择 | 原因 |
|------|------|------|
| 日语 NLP | spaCy ja_core_news_md | 已有依赖，性能良好 |
| 时间间隔分析 | pandas DataFrame | 处理 chunks 数据方便 |
| 文件预览 | 纯文本读取 + JSON 解析 | 简单直接 |
| 前端日志 | Ant Design Table | 支持过滤和分页 |

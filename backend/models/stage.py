"""
Processing stage data model
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal, List
from datetime import datetime


StageStatus = Literal['pending', 'running', 'completed', 'failed', 'skipped']


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class StageOutputFile(BaseModel):
    """阶段输出文件"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    name: str = Field(..., description="文件名")
    path: str = Field(..., description="相对路径")
    type: str = Field(..., description="文件类型: xlsx, txt, json, srt, mp4, mp3")
    description: str = Field(..., description="文件描述")
    exists: bool = Field(default=False, description="文件是否存在")
    size: Optional[int] = Field(None, description="文件大小(bytes)")


class ProcessingStage(BaseModel):
    """处理阶段模型"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    
    name: str = Field(..., description="阶段名称")
    display_name: str = Field(..., description="显示名称")
    status: StageStatus = Field(default='pending', description="阶段状态")
    progress: Optional[float] = Field(None, ge=0, le=100, description="阶段内进度")
    message: Optional[str] = Field(None, description="当前处理详情消息")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    output_files: List[StageOutputFile] = Field(default_factory=list, description="输出文件列表")


# 每个阶段的输出文件定义
STAGE_OUTPUT_FILES = {
    # 字幕处理阶段
    'asr': [
        {'name': 'cleaned_chunks.xlsx', 'path': 'output/log/cleaned_chunks.xlsx', 'type': 'xlsx', 'description': 'ASR识别结果（带时间戳）'},
        {'name': 'raw.mp3', 'path': 'output/audio/raw.mp3', 'type': 'mp3', 'description': '提取的原始音频'},
        {'name': 'vocal.mp3', 'path': 'output/audio/vocal.mp3', 'type': 'mp3', 'description': '分离的人声音频'},
        {'name': 'background.mp3', 'path': 'output/audio/background.mp3', 'type': 'mp3', 'description': '分离的背景音乐'},
    ],
    'split_nlp': [
        {'name': 'split_by_mark.txt', 'path': 'output/log/split_by_mark.txt', 'type': 'txt', 'description': '标点分句结果'},
        {'name': 'split_by_comma.txt', 'path': 'output/log/split_by_comma.txt', 'type': 'txt', 'description': '逗号分句结果'},
        {'name': 'split_by_connector.txt', 'path': 'output/log/split_by_connector.txt', 'type': 'txt', 'description': '连接词分句结果'},
        {'name': 'split_by_nlp.txt', 'path': 'output/log/split_by_nlp.txt', 'type': 'txt', 'description': 'NLP最终分句结果'},
    ],
    'split_meaning': [
        {'name': 'split_by_meaning.txt', 'path': 'output/log/split_by_meaning.txt', 'type': 'txt', 'description': '语义分割结果'},
        {'name': 'split_by_meaning.json', 'path': 'output/gpt_log/split_by_meaning.json', 'type': 'json', 'description': 'LLM语义分割日志'},
    ],
    'summarize': [
        {'name': 'terminology.json', 'path': 'output/log/terminology.json', 'type': 'json', 'description': '术语表和主题摘要'},
        {'name': 'summary.json', 'path': 'output/gpt_log/summary.json', 'type': 'json', 'description': 'LLM摘要日志'},
    ],
    'translate': [
        {'name': 'translation_results.xlsx', 'path': 'output/log/translation_results.xlsx', 'type': 'xlsx', 'description': '翻译结果（带时间戳）'},
        {'name': 'translate_faithfulness.json', 'path': 'output/gpt_log/translate_faithfulness.json', 'type': 'json', 'description': 'LLM直译日志'},
        {'name': 'translate_expressiveness.json', 'path': 'output/gpt_log/translate_expressiveness.json', 'type': 'json', 'description': 'LLM意译日志'},
    ],
    'split_sub': [
        {'name': 'translation_results_for_subtitles.xlsx', 'path': 'output/log/translation_results_for_subtitles.xlsx', 'type': 'xlsx', 'description': '字幕分割结果'},
        {'name': 'translation_results_remerged.xlsx', 'path': 'output/log/translation_results_remerged.xlsx', 'type': 'xlsx', 'description': '重新合并的翻译'},
        {'name': 'align_subs.json', 'path': 'output/gpt_log/align_subs.json', 'type': 'json', 'description': 'LLM字幕对齐日志'},
    ],
    'gen_sub': [
        {'name': 'src.srt', 'path': 'output/src.srt', 'type': 'srt', 'description': '源语言字幕'},
        {'name': 'trans.srt', 'path': 'output/trans.srt', 'type': 'srt', 'description': '翻译字幕'},
        {'name': 'src_trans.srt', 'path': 'output/src_trans.srt', 'type': 'srt', 'description': '双语字幕（源语言在上）'},
        {'name': 'trans_src.srt', 'path': 'output/trans_src.srt', 'type': 'srt', 'description': '双语字幕（翻译在上）'},
    ],
    'merge_sub': [
        {'name': 'output_sub.mp4', 'path': 'output/output_sub.mp4', 'type': 'mp4', 'description': '带字幕的视频'},
    ],
    # 配音处理阶段
    'audio_task': [
        {'name': 'tts_tasks.xlsx', 'path': 'output/audio/tts_tasks.xlsx', 'type': 'xlsx', 'description': 'TTS任务列表'},
        {'name': 'trans_subs_for_audio.srt', 'path': 'output/audio/trans_subs_for_audio.srt', 'type': 'srt', 'description': '配音用字幕'},
        {'name': 'src_subs_for_audio.srt', 'path': 'output/audio/src_subs_for_audio.srt', 'type': 'srt', 'description': '源语言配音字幕'},
    ],
    'dub_chunks': [
        {'name': 'segs/', 'path': 'output/audio/segs', 'type': 'folder', 'description': '配音片段目录'},
    ],
    'refer_audio': [
        {'name': 'refers/', 'path': 'output/audio/refers', 'type': 'folder', 'description': '参考音频目录'},
    ],
    'gen_audio': [
        {'name': 'tmp/', 'path': 'output/audio/tmp', 'type': 'folder', 'description': '生成的临时音频文件'},
    ],
    'merge_audio': [
        {'name': 'dub.mp3', 'path': 'output/dub.mp3', 'type': 'mp3', 'description': '合并后的配音'},
        {'name': 'dub.srt', 'path': 'output/dub.srt', 'type': 'srt', 'description': '配音字幕'},
    ],
    'dub_to_vid': [
        {'name': 'output_dub.mp4', 'path': 'output/output_dub.mp4', 'type': 'mp4', 'description': '带配音的视频'},
    ],
}


# 字幕处理阶段定义
SUBTITLE_STAGES = [
    ProcessingStage(name='asr', display_name='语音识别'),
    ProcessingStage(name='split_nlp', display_name='NLP 分句'),
    ProcessingStage(name='split_meaning', display_name='语义分割'),
    ProcessingStage(name='summarize', display_name='内容总结'),
    ProcessingStage(name='translate', display_name='翻译'),
    ProcessingStage(name='split_sub', display_name='字幕分割'),
    ProcessingStage(name='gen_sub', display_name='生成字幕'),
    ProcessingStage(name='merge_sub', display_name='合并字幕到视频'),
]

# 配音处理阶段定义
DUBBING_STAGES = [
    ProcessingStage(name='audio_task', display_name='生成音频任务'),
    ProcessingStage(name='dub_chunks', display_name='生成配音片段'),
    ProcessingStage(name='refer_audio', display_name='提取参考音频'),
    ProcessingStage(name='gen_audio', display_name='生成配音'),
    ProcessingStage(name='merge_audio', display_name='合并音频'),
    ProcessingStage(name='dub_to_vid', display_name='配音合并到视频'),
]


def get_subtitle_stages() -> list[ProcessingStage]:
    """获取字幕处理阶段列表的副本"""
    return [stage.model_copy() for stage in SUBTITLE_STAGES]


def get_dubbing_stages() -> list[ProcessingStage]:
    """获取配音处理阶段列表的副本"""
    return [stage.model_copy() for stage in DUBBING_STAGES]

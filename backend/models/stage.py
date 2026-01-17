"""
Processing stage data model
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


StageStatus = Literal['pending', 'running', 'completed', 'failed', 'skipped']


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


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

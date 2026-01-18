"""
Log data models for processing logs
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


LogLevel = Literal['INFO', 'WARNING', 'ERROR']


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class LogEntry(BaseModel):
    """处理过程中的单条日志记录"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    
    id: int = Field(..., description="日志唯一标识，用于增量获取")
    timestamp: str = Field(..., description="日志时间戳 (ISO 8601)")
    level: LogLevel = Field(default='INFO', description="日志级别: INFO, WARNING, ERROR")
    message: str = Field(..., description="日志消息内容")
    source: str = Field(default='system', description="日志来源: asr, translate, tts, system 等")
    job_id: Optional[str] = Field(None, description="关联的任务 ID")
    duration_ms: Optional[float] = Field(None, description="操作耗时（毫秒）")


class LogQueryResponse(BaseModel):
    """日志查询 API 响应"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    
    logs: list[LogEntry] = Field(default_factory=list, description="日志列表")
    next_id: int = Field(..., description="下一个日志 ID（用于增量获取）")
    has_more: bool = Field(default=False, description="是否还有更多日志")

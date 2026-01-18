"""
Log Service - Thread-safe log storage with ring buffer
"""
from collections import deque
from threading import Lock
from datetime import datetime
from typing import Optional, List, Tuple, Literal
import logging

from models.log import LogEntry, LogQueryResponse

logger = logging.getLogger(__name__)


class LogStore:
    """线程安全的日志存储，使用环形缓冲区"""
    
    def __init__(self, max_size: int = 1000):
        self._logs: deque[dict] = deque(maxlen=max_size)
        self._next_id: int = 1
        self._lock = Lock()
    
    def add(
        self, 
        level: Literal['INFO', 'WARNING', 'ERROR'],
        message: str, 
        source: str = "system", 
        job_id: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> LogEntry:
        """添加日志条目
        
        Args:
            level: 日志级别 (INFO, WARNING, ERROR)
            message: 日志消息
            source: 日志来源 (asr, translate, tts, system 等)
            job_id: 关联的任务 ID
            duration_ms: 操作耗时（毫秒）
            
        Returns:
            创建的日志条目
        """
        with self._lock:
            entry = LogEntry(
                id=self._next_id,
                timestamp=datetime.utcnow().isoformat() + "Z",
                level=level,
                message=message,
                source=source,
                job_id=job_id,
                duration_ms=duration_ms
            )
            self._logs.append(entry.model_dump())
            self._next_id += 1
            return entry
    
    def info(self, message: str, source: str = "system", **kwargs) -> LogEntry:
        """添加 INFO 级别日志"""
        return self.add('INFO', message, source, **kwargs)
    
    def warning(self, message: str, source: str = "system", **kwargs) -> LogEntry:
        """添加 WARNING 级别日志"""
        return self.add('WARNING', message, source, **kwargs)
    
    def error(self, message: str, source: str = "system", **kwargs) -> LogEntry:
        """添加 ERROR 级别日志"""
        return self.add('ERROR', message, source, **kwargs)
    
    def get_since(
        self, 
        last_id: int = 0, 
        limit: int = 100,
        level: Optional[str] = None,
        source: Optional[str] = None
    ) -> LogQueryResponse:
        """获取 last_id 之后的日志
        
        Args:
            last_id: 上次获取的最后一条日志 ID，返回此 ID 之后的日志
            limit: 最大返回条数
            level: 按日志级别过滤
            source: 按日志来源过滤
            
        Returns:
            LogQueryResponse 包含日志列表、下一个 ID 和是否有更多
        """
        with self._lock:
            # 过滤日志
            filtered = [
                LogEntry(**log) for log in self._logs 
                if log['id'] > last_id
                and (level is None or log['level'] == level)
                and (source is None or log['source'] == source)
            ]
            
            # 限制返回数量
            result = filtered[:limit]
            has_more = len(filtered) > limit
            
            return LogQueryResponse(
                logs=result,
                next_id=self._next_id,
                has_more=has_more
            )
    
    def clear(self):
        """清空所有日志"""
        with self._lock:
            self._logs.clear()
            # 不重置 _next_id 以保持增量获取的一致性
    
    def get_count(self) -> int:
        """获取当前日志数量"""
        with self._lock:
            return len(self._logs)


# 全局单例实例
_log_store: Optional[LogStore] = None


def get_log_store() -> LogStore:
    """获取全局日志存储实例"""
    global _log_store
    if _log_store is None:
        _log_store = LogStore()
    return _log_store


def reset_log_store():
    """重置全局日志存储（主要用于测试）"""
    global _log_store
    _log_store = None

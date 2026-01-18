"""
Logs API routes - 日志查询 API
"""
from typing import Optional

from fastapi import APIRouter, Query

from models import LogQueryResponse
from api.deps import get_log_store

router = APIRouter()


@router.get("", response_model=LogQueryResponse)
async def get_logs(
    last_id: int = Query(0, alias="lastId", description="上次获取的最后一条日志 ID"),
    limit: int = Query(100, le=500, description="最大返回条数"),
    level: Optional[str] = Query(None, description="按日志级别过滤: INFO, WARNING, ERROR"),
    source: Optional[str] = Query(None, description="按日志来源过滤")
):
    """
    获取处理日志（支持增量获取）
    
    使用 lastId 参数实现增量获取，避免重复传输已显示的日志。
    """
    log_store = get_log_store()
    return log_store.get_since(last_id, limit, level, source)


@router.delete("")
async def clear_logs():
    """
    清空所有日志
    """
    log_store = get_log_store()
    log_store.clear()
    return {"message": "日志已清空"}

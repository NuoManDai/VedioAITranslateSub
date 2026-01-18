"""
File preview API routes
"""
import os
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.api.deps import OUTPUT_DIR, PROJECT_ROOT
from backend.models.stage import STAGE_OUTPUT_FILES, StageOutputFile


router = APIRouter(prefix='/files', tags=['files'])


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class FilePreviewResponse(BaseModel):
    """文件预览响应"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    name: str
    path: str
    type: str
    content: Optional[str] = None
    size: int
    preview_available: bool
    error: Optional[str] = None


def get_file_size(file_path: Path) -> int:
    """获取文件大小"""
    try:
        return file_path.stat().st_size if file_path.exists() else 0
    except:
        return 0


def is_previewable(file_type: str) -> bool:
    """判断文件类型是否可以预览"""
    return file_type in ['txt', 'json', 'srt', 'xlsx']


@router.get('/stage/{stage_name}')
async def get_stage_files(stage_name: str):
    """获取指定阶段的输出文件列表"""
    if stage_name not in STAGE_OUTPUT_FILES:
        raise HTTPException(status_code=404, detail=f"Stage '{stage_name}' not found")
    
    files = []
    for file_def in STAGE_OUTPUT_FILES[stage_name]:
        file_path = PROJECT_ROOT / file_def['path']
        exists = file_path.exists()
        size = get_file_size(file_path) if exists else 0
        
        files.append(StageOutputFile(
            name=file_def['name'],
            path=file_def['path'],
            type=file_def['type'],
            description=file_def['description'],
            exists=exists,
            size=size
        ))
    
    return {"stage": stage_name, "files": [f.model_dump(by_alias=True) for f in files]}


@router.get('/preview')
async def preview_file(
    path: str = Query(..., description="相对于项目根目录的文件路径"),
    max_lines: int = Query(500, description="最大预览行数")
):
    """预览文件内容"""
    # 安全检查：确保路径在 output 目录内
    file_path = PROJECT_ROOT / path
    
    try:
        # 确保路径在允许的范围内
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(PROJECT_ROOT.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    file_type = file_path.suffix.lower()[1:] if file_path.suffix else ''
    file_size = get_file_size(file_path)
    
    # 根据文件类型处理预览
    if file_type == 'json':
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            content = json.dumps(data, indent=2, ensure_ascii=False)
            # 限制行数
            lines = content.split('\n')
            if len(lines) > max_lines:
                content = '\n'.join(lines[:max_lines]) + f'\n\n... (truncated, showing {max_lines}/{len(lines)} lines)'
            return FilePreviewResponse(
                name=file_path.name,
                path=path,
                type='json',
                content=content,
                size=file_size,
                preview_available=True
            ).model_dump(by_alias=True)
        except Exception as e:
            return FilePreviewResponse(
                name=file_path.name,
                path=path,
                type='json',
                content=None,
                size=file_size,
                preview_available=False,
                error=str(e)
            ).model_dump(by_alias=True)
    
    elif file_type in ['txt', 'srt']:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) > max_lines:
                content = ''.join(lines[:max_lines]) + f'\n\n... (truncated, showing {max_lines}/{len(lines)} lines)'
            else:
                content = ''.join(lines)
            return FilePreviewResponse(
                name=file_path.name,
                path=path,
                type=file_type,
                content=content,
                size=file_size,
                preview_available=True
            ).model_dump(by_alias=True)
        except Exception as e:
            return FilePreviewResponse(
                name=file_path.name,
                path=path,
                type=file_type,
                content=None,
                size=file_size,
                preview_available=False,
                error=str(e)
            ).model_dump(by_alias=True)
    
    elif file_type == 'xlsx':
        try:
            import pandas as pd
            df = pd.read_excel(file_path)
            # 转换为 markdown 表格格式便于预览
            if len(df) > 100:
                content = df.head(100).to_markdown(index=False)
                content += f'\n\n... (truncated, showing 100/{len(df)} rows)'
            else:
                content = df.to_markdown(index=False)
            return FilePreviewResponse(
                name=file_path.name,
                path=path,
                type='xlsx',
                content=content,
                size=file_size,
                preview_available=True
            ).model_dump(by_alias=True)
        except Exception as e:
            return FilePreviewResponse(
                name=file_path.name,
                path=path,
                type='xlsx',
                content=None,
                size=file_size,
                preview_available=False,
                error=str(e)
            ).model_dump(by_alias=True)
    
    else:
        # 不支持预览的文件类型
        return FilePreviewResponse(
            name=file_path.name,
            path=path,
            type=file_type,
            content=None,
            size=file_size,
            preview_available=False,
            error=f"Preview not supported for {file_type} files"
        ).model_dump(by_alias=True)


@router.get('/download')
async def download_file(
    path: str = Query(..., description="相对于项目根目录的文件路径")
):
    """下载文件"""
    file_path = PROJECT_ROOT / path
    
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(PROJECT_ROOT.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type='application/octet-stream'
    )


@router.get('/folder')
async def list_folder(
    path: str = Query(..., description="相对于项目根目录的文件夹路径")
):
    """列出文件夹内容"""
    folder_path = PROJECT_ROOT / path
    
    try:
        folder_path = folder_path.resolve()
        if not str(folder_path).startswith(str(PROJECT_ROOT.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    if not folder_path.exists():
        raise HTTPException(status_code=404, detail="Folder not found")
    
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a folder")
    
    files = []
    try:
        for item in sorted(folder_path.iterdir()):
            file_type = item.suffix.lower()[1:] if item.suffix else ('folder' if item.is_dir() else 'unknown')
            files.append({
                'name': item.name,
                'path': str(item.relative_to(PROJECT_ROOT)).replace('\\', '/'),
                'type': file_type,
                'is_dir': item.is_dir(),
                'size': get_file_size(item) if not item.is_dir() else 0
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"folder": path, "files": files}

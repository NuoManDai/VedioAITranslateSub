"""
Batch processing job and file data models
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
import uuid

from .stage import to_camel


BatchFileStatus = Literal[
    "pending", "uploading", "queued", "processing", "completed", "failed", "cancelled"
]
BatchJobStatus = Literal[
    "pending", "uploading", "queued", "processing", "completed", "failed", "cancelled"
]


class BatchFile(BaseModel):
    """Batch file model"""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="File unique ID"
    )
    job_id: str = Field(..., description="Parent batch job ID")
    filename: str = Field(..., description="Original filename")
    filepath: Optional[str] = Field(None, description="File path on disk")
    status: BatchFileStatus = Field(default="pending", description="File status")
    source_lang: str = Field(default="auto", description="Source language")
    target_lang: str = Field(default="简体中文", description="Target language")
    dubbing: bool = Field(default=False, description="Enable dubbing")
    output_path: Optional[str] = Field(None, description="Output directory path")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Created time"
    )


class BatchJob(BaseModel):
    """Batch job model"""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Job unique ID"
    )
    status: BatchJobStatus = Field(default="pending", description="Job status")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Created time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Updated time"
    )
    files: list[BatchFile] = Field(
        default_factory=list, description="Files in this batch"
    )
    total_files: int = Field(default=0, description="Total file count")
    completed_files: int = Field(default=0, description="Completed file count")
    failed_files: int = Field(default=0, description="Failed file count")


class BatchFileSettingsUpdate(BaseModel):
    """Request model for updating file settings"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    source_lang: Optional[str] = Field(None, description="Source language")
    target_lang: Optional[str] = Field(None, description="Target language")
    dubbing: Optional[bool] = Field(None, description="Enable dubbing")


class BatchFileRegister(BaseModel):
    """Request model for registering a file"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    filename: str = Field(..., description="Original filename")
    source_lang: Optional[str] = Field(None, description="Source language")
    target_lang: Optional[str] = Field(None, description="Target language")
    dubbing: Optional[bool] = Field(None, description="Enable dubbing")

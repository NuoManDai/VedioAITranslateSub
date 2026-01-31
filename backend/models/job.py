"""
Processing job data model
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
import uuid

from .stage import ProcessingStage, get_subtitle_stages, get_dubbing_stages, to_camel


JobType = Literal["subtitle", "dubbing"]
JobStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class ProcessingJob(BaseModel):
    """处理任务模型"""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="任务唯一标识"
    )
    video_id: str = Field(..., description="关联的视频 ID")
    job_type: JobType = Field(..., description="任务类型")
    status: JobStatus = Field(default="pending", description="任务状态")
    current_stage: Optional[str] = Field(None, description="当前处理阶段名称")
    progress: float = Field(default=0, ge=0, le=100, description="进度百分比")
    stages: list[ProcessingStage] = Field(
        default_factory=list, description="各阶段状态列表"
    )
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")

    @classmethod
    def create_subtitle_job(cls, video_id: str) -> "ProcessingJob":
        """创建字幕处理任务"""
        return cls(video_id=video_id, job_type="subtitle", stages=get_subtitle_stages())

    @classmethod
    def create_dubbing_job(cls, video_id: str) -> "ProcessingJob":
        """创建配音处理任务"""
        return cls(video_id=video_id, job_type="dubbing", stages=get_dubbing_stages())

    def start(self):
        """开始任务"""
        self.status = "running"
        self.started_at = datetime.now()
        if self.stages:
            self.current_stage = self.stages[0].name

    def complete(self):
        """完成任务"""
        self.status = "completed"
        self.completed_at = datetime.now()
        self.progress = 100
        self.current_stage = None

    def fail(self, error_message: str):
        """任务失败"""
        self.status = "failed"
        self.completed_at = datetime.now()
        self.error_message = error_message

    def cancel(self):
        """取消任务"""
        self.status = "cancelled"
        self.completed_at = datetime.now()

    def update_stage(
        self,
        stage_name: str,
        status: str,
        progress: Optional[float] = None,
        error: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """更新阶段状态"""
        for stage in self.stages:
            if stage.name == stage_name:
                stage.status = status
                if status == "running":
                    stage.started_at = datetime.now()
                elif status in ("completed", "failed"):
                    stage.completed_at = datetime.now()
                if progress is not None:
                    stage.progress = progress
                if error:
                    stage.error_message = error
                if message is not None:
                    stage.message = message
                break

        # 计算总进度
        self._calculate_progress()

    def _calculate_progress(self):
        """计算总进度"""
        if not self.stages:
            return

        completed = sum(1 for s in self.stages if s.status == "completed")
        running = sum(1 for s in self.stages if s.status == "running")

        # 每个完成的阶段贡献 100/total 的进度
        # 正在运行的阶段贡献其内部进度的比例
        stage_weight = 100 / len(self.stages)

        progress = completed * stage_weight
        if running > 0:
            running_stage = next(
                (s for s in self.stages if s.status == "running"), None
            )
            if running_stage and running_stage.progress:
                progress += (running_stage.progress / 100) * stage_weight

        self.progress = min(progress, 100)


class ProcessingStatus(BaseModel):
    """处理状态响应模型"""

    video: Optional[dict] = None
    subtitle_job: Optional[ProcessingJob] = Field(
        default=None, alias="subtitleJob", serialization_alias="subtitleJob"
    )
    dubbing_job: Optional[ProcessingJob] = Field(
        default=None, alias="dubbingJob", serialization_alias="dubbingJob"
    )
    has_unfinished_task: bool = Field(
        default=False,
        alias="hasUnfinishedTask",
        serialization_alias="hasUnfinishedTask",
        description="是否有未完成的任务",
    )
    can_start_subtitle: bool = Field(
        default=False,
        alias="canStartSubtitle",
        serialization_alias="canStartSubtitle",
        description="是否可以开始字幕处理",
    )
    can_start_dubbing: bool = Field(
        default=False,
        alias="canStartDubbing",
        serialization_alias="canStartDubbing",
        description="是否可以开始配音处理",
    )
    subtitle_merged: bool = Field(
        default=False,
        alias="subtitleMerged",
        serialization_alias="subtitleMerged",
        description="字幕是否已合并到视频 (output_sub.mp4)",
    )

    class Config:
        populate_by_name = True

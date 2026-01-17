"""
Processing Service - Business logic for subtitle and dubbing processing
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

from models import ProcessingJob, Video
from api.deps import get_app_state, get_output_dir, get_project_root

logger = logging.getLogger(__name__)


class ProcessingService:
    """Service for video processing operations"""
    
    def __init__(self):
        self.output_dir = get_output_dir()
        self._setup_core_imports()
    
    def _setup_core_imports(self):
        """Setup imports for core modules"""
        project_root = get_project_root()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
    
    def create_subtitle_job(self, video_id: str) -> ProcessingJob:
        """Create a new subtitle processing job"""
        return ProcessingJob.create_subtitle_job(video_id)
    
    def create_dubbing_job(self, video_id: str) -> ProcessingJob:
        """Create a new dubbing processing job"""
        return ProcessingJob.create_dubbing_job(video_id)
    
    async def run_subtitle_processing(self, job: ProcessingJob, video: Video):
        """Run the subtitle processing pipeline"""
        state = get_app_state()
        job.start()
        
        try:
            # Stage 1: ASR (Speech Recognition)
            await self._run_stage(job, 'asr', self._run_asr)
            if state.is_cancel_requested():
                return
            
            # Stage 2: NLP Split
            await self._run_stage(job, 'split_nlp', self._run_split_nlp)
            if state.is_cancel_requested():
                return
            
            # Stage 3: Meaning Split
            await self._run_stage(job, 'split_meaning', self._run_split_meaning)
            if state.is_cancel_requested():
                return
            
            # Stage 4: Summarize
            await self._run_stage(job, 'summarize', self._run_summarize)
            if state.is_cancel_requested():
                return
            
            # Stage 5: Translate
            await self._run_stage(job, 'translate', self._run_translate)
            if state.is_cancel_requested():
                return
            
            # Stage 6: Split Subtitles
            await self._run_stage(job, 'split_sub', self._run_split_sub)
            if state.is_cancel_requested():
                return
            
            # Stage 7: Generate Subtitles
            await self._run_stage(job, 'gen_sub', self._run_gen_sub)
            if state.is_cancel_requested():
                return
            
            # Stage 8: Merge Subtitles to Video
            await self._run_stage(job, 'merge_sub', self._run_merge_sub)
            
            # Complete
            job.complete()
            video.status = 'completed'
            logger.info("Subtitle processing completed successfully")
            
        except Exception as e:
            logger.error(f"Subtitle processing failed: {e}", exc_info=True)
            job.fail(str(e))
            video.status = 'error'
            video.error_message = str(e)
        finally:
            state.clear_cancel_request()
    
    async def run_dubbing_processing(self, job: ProcessingJob, video: Video):
        """Run the dubbing processing pipeline"""
        state = get_app_state()
        job.start()
        
        try:
            # Stage 1: Audio Task
            await self._run_stage(job, 'audio_task', self._run_audio_task)
            if state.is_cancel_requested():
                return
            
            # Stage 2: Dub Chunks
            await self._run_stage(job, 'dub_chunks', self._run_dub_chunks)
            if state.is_cancel_requested():
                return
            
            # Stage 3: Refer Audio
            await self._run_stage(job, 'refer_audio', self._run_refer_audio)
            if state.is_cancel_requested():
                return
            
            # Stage 4: Generate Audio
            await self._run_stage(job, 'gen_audio', self._run_gen_audio)
            if state.is_cancel_requested():
                return
            
            # Stage 5: Merge Audio
            await self._run_stage(job, 'merge_audio', self._run_merge_audio)
            if state.is_cancel_requested():
                return
            
            # Stage 6: Dub to Video
            await self._run_stage(job, 'dub_to_vid', self._run_dub_to_vid)
            
            # Complete
            job.complete()
            video.status = 'completed'
            logger.info("Dubbing processing completed successfully")
            
        except Exception as e:
            logger.error(f"Dubbing processing failed: {e}", exc_info=True)
            job.fail(str(e))
            video.status = 'error'
            video.error_message = str(e)
        finally:
            state.clear_cancel_request()
    
    async def _run_stage(self, job: ProcessingJob, stage_name: str, stage_func):
        """Run a single processing stage"""
        logger.info(f"Starting stage: {stage_name}")
        
        # Stage description messages
        stage_messages = {
            'asr': '正在进行语音识别...',
            'split_nlp': '正在使用 NLP 进行分句处理...',
            'split_meaning': '正在按语义进行句子分割...',
            'summarize': '正在生成内容摘要...',
            'translate': '正在翻译字幕...',
            'split_sub': '正在分割字幕...',
            'gen_sub': '正在生成字幕文件...',
            'merge_sub': '正在将字幕合并到视频...',
            'audio_task': '正在生成音频任务...',
            'dub_chunks': '正在生成配音片段...',
            'refer_audio': '正在提取参考音频...',
            'gen_audio': '正在生成配音...',
            'merge_audio': '正在合并音频...',
            'dub_to_vid': '正在将配音合并到视频...',
        }
        
        message = stage_messages.get(stage_name, f'正在处理 {stage_name}...')
        job.update_stage(stage_name, 'running', message=message)
        job.current_stage = stage_name
        
        try:
            # Run the stage function in a thread pool to avoid blocking
            await asyncio.to_thread(stage_func)
            job.update_stage(stage_name, 'completed', progress=100, message='完成')
            logger.info(f"Stage {stage_name} completed")
        except Exception as e:
            logger.error(f"Stage {stage_name} failed: {e}")
            job.update_stage(stage_name, 'failed', error=str(e), message=f'失败: {str(e)[:50]}')
            raise
    
    # ========== Subtitle Processing Stages ==========
    
    def _run_asr(self):
        """Run speech recognition"""
        from core._2_asr import transcribe
        transcribe()
    
    def _run_split_nlp(self):
        """Run NLP-based sentence splitting"""
        from core._3_1_split_nlp import split_by_spacy
        split_by_spacy()
    
    def _run_split_meaning(self):
        """Run meaning-based splitting"""
        from core._3_2_split_meaning import split_sentences_by_meaning
        split_sentences_by_meaning()
    
    def _run_summarize(self):
        """Run content summarization"""
        from core._4_1_summarize import get_summary
        get_summary()
    
    def _run_translate(self):
        """Run translation"""
        from core._4_2_translate import translate_all
        translate_all()
    
    def _run_split_sub(self):
        """Run subtitle splitting"""
        from core._5_split_sub import split_for_sub_main
        split_for_sub_main()
    
    def _run_gen_sub(self):
        """Generate subtitles"""
        from core._6_gen_sub import align_timestamp_main
        align_timestamp_main()
    
    def _run_merge_sub(self):
        """Merge subtitles to video"""
        from core._7_sub_into_vid import merge_subtitles_to_video
        merge_subtitles_to_video()
    
    # ========== Dubbing Processing Stages ==========
    
    def _run_audio_task(self):
        """Generate audio tasks"""
        from core._8_1_audio_task import gen_audio_task_main
        gen_audio_task_main()
    
    def _run_dub_chunks(self):
        """Generate dubbing chunks"""
        from core._8_2_dub_chunks import gen_dub_chunks
        gen_dub_chunks()
    
    def _run_refer_audio(self):
        """Extract reference audio"""
        from core._9_refer_audio import extract_refer_audio_main
        extract_refer_audio_main()
    
    def _run_gen_audio(self):
        """Generate audio"""
        from core._10_gen_audio import gen_audio
        gen_audio()
    
    def _run_merge_audio(self):
        """Merge audio files"""
        from core._11_merge_audio import merge_full_audio
        merge_full_audio()
    
    def _run_dub_to_vid(self):
        """Merge dubbing to video"""
        from core._12_dub_to_vid import merge_video_audio
        merge_video_audio()
    
    def detect_unfinished_task(self) -> bool:
        """Detect if there's an unfinished task based on output directory state"""
        # Check for intermediate files that indicate incomplete processing
        markers = [
            'trans_subs_for_audio.json',  # Created during subtitle processing
            'audio_task.json',  # Created during dubbing
        ]
        
        for marker in markers:
            if (self.output_dir / marker).exists():
                # Check if final output exists
                final_outputs = list(self.output_dir.glob("*_with_*.mp4"))
                if not final_outputs:
                    return True
        
        return False

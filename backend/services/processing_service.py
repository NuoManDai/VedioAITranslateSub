"""
Processing Service - Business logic for subtitle and dubbing processing
"""

import sys
import asyncio
import time
import re
import io
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
from contextlib import redirect_stdout, redirect_stderr
import logging
import threading

from models import ProcessingJob, Video
from api.deps import get_app_state, get_output_dir, get_project_root, get_log_store

# Import cancel flag utilities from core
import sys

_project_root = get_project_root()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
from core.utils.config_utils import set_cancel_flag, clear_cancel_flag

logger = logging.getLogger(__name__)


class TqdmCapture(io.StringIO):
    """Capture stdout/stderr output and send important messages to LogStore"""

    def __init__(
        self, log_store, source: str, job_id: str, original_stream, stage_name: str = ""
    ):
        super().__init__()
        self.log_store = log_store
        self.source = source
        self.job_id = job_id
        self.original_stream = original_stream
        self.stage_name = stage_name
        self._buffer = ""
        self._last_progress = ""
        self._logged_lines = set()  # Avoid duplicate log lines
        self._lock = threading.Lock()

        # ANSI escape sequence pattern for cleaning rich output
        self._ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

        # Patterns for important log lines (emoji or key prefixes)
        self._important_patterns = [
            r"^[✅⚠️❌🎙️🎤🚀🎮▶️📥🔍⏱️💾📝🔊💬🌐📊📖💾⏱️🔄⬇️✂️🎬📦⚙️✓🔗📏🎵🎬➡️💡🔧📄🗣️🎯🔢📋]",  # Emoji prefixes
            r"📝",  # Explicit 📝 emoji match (for CJK mode etc.)
            r"^(INFO|WARNING|ERROR|DEBUG):",  # Log levels
            r"\d{4}-\d{2}-\d{2}.*-\s*(INFO|WARNING|ERROR)",  # Timestamped logs
            r"huggingface.*-\s*(WARNING|ERROR)",  # HuggingFace library logs
            r"(MaxRetryError|ConnectTimeoutError|ConnectionError)",  # Network errors
            r"(timed out|timeout|connection refused)",  # Connection issues
            r"LLM request took",  # LLM timing logs
            r"(Origin:|Direct:|Free:)",  # Translation results (simplified)
            r"Translation Results",  # Translation table title
            r"CJK mode",  # CJK mode indicator
            r"use cache response",  # Cache hit
            r"(Summarizing|translat|Processing|Loading|Starting)",  # Process stages
            r"(saved to|Successfully|Completed|finished|Done)",  # Completion messages
            r"(Source Line|Target Line|SRC_LANG|TARGET_LANG)",  # Subtitle split table content
            r"(Original|Split)\s*[│|]",  # Split result table (both Unicode │ and ASCII |)
            r"(Line \d+ needs to be split|Split attempt|Aligned parts)",  # Split progress
            r"(Start splitting|splitting subtitles)",  # Split start
            r"Sentence \d+ has been successfully split",  # GPT split success message
            r"All sentences have been successfully split",  # All split complete
            r"(low similarity|Unable to find.*split point)",  # Split warnings
            # ASR related
            r"(Transcrib|whisper|ASR|alignment|align)",  # ASR process
            r"(Demucs|separation|vocal|background)",  # Audio separation
            r"(audio|Audio|声道|channels)",  # Audio processing
            r"(segment|Segment|片段)",  # Segmentation
            # NLP related
            r"(spacy|SpaCy|NLP|分句|分词|sentence)",  # NLP processing
            r"(split_by_nlp|split_by_meaning)",  # Split stages
            # Subtitle related
            r"(subtitle|Subtitle|字幕|SRT|srt)",  # Subtitle processing
            r"(gen_sub|merge_sub|sub_into_vid)",  # Subtitle stages
            # TTS/Dubbing related
            r"(TTS|tts|配音|dubbing|dub)",  # TTS processing
            r"(audio_task|dub_chunks|refer_audio|gen_audio|merge_audio)",  # Dubbing stages
            # FFmpeg related
            r"(FFmpeg|ffmpeg|encoding|muxing)",  # Video processing
            r"(Converting|Converted|提取)",  # Conversion
            # Progress indicators
            r"(\d+/\d+|\d+%|进度)",  # Progress
            r"(Step|step|阶段|Stage|stage)",  # Stage indicators
            # Model loading
            r"(model|Model|模型)",  # Model related
            r"(downloading|download|加载|loaded)",  # Loading
            # Timing
            r"(time|Time|耗时|took|elapsed)",  # Timing info
            r"(\d+\.\d+s|\d+ms|\d+ seconds)",  # Time values
            # LLM sentence breaks
            r"Using LLM sentence breaks",  # LLM sentence break mode
            r"\(\d+ lines?\)",  # Line count indicator
        ]
        self._important_regex = re.compile(
            "|".join(self._important_patterns), re.IGNORECASE
        )

        # Patterns that indicate LLM-related logs (should use 'llm' as source)
        # Includes: translation results, split results, alignment results - all use LLM
        self._llm_patterns = re.compile(
            r"(LLM request took|use cache response|"
            r"Origin:|Direct:|Free:|Translation Results|"
            r"Original\s*\||Split\s*\||"
            r"SRC_LANG|TARGET_LANG|Aligned parts|"
            r"Source Line|Target Line|"
            r"Line \d+ needs to be split|Split attempt|"
            r"Summariz|翻译|译文)",
            re.IGNORECASE,
        )

    def _clean_ansi(self, text: str) -> str:
        """Remove ANSI escape sequences from text"""
        return self._ansi_escape.sub("", text)

    def write(self, text: str):
        # Always write to original stream
        if self.original_stream:
            self.original_stream.write(text)
            self.original_stream.flush()

        with self._lock:
            self._buffer += text

            # Check for progress patterns first
            progress_str = None

            # Try tqdm pattern: "29%|████████"
            tqdm_match = re.search(r"(\d+)%\|", self._buffer)
            if tqdm_match:
                progress_str = f"{tqdm_match.group(1)}%"
            else:
                # Try "Progress: XX.XX%" pattern
                progress_match = re.search(
                    r"Progress:\s*(\d+(?:\.\d+)?)%", self._buffer
                )
                if progress_match:
                    progress_str = f"{float(progress_match.group(1)):.0f}%"

            # Log progress updates
            if progress_str and progress_str != self._last_progress:
                self._last_progress = progress_str
                stage_prefix = f"[{self.stage_name}] " if self.stage_name else ""
                self.log_store.info(
                    f"{stage_prefix}进度: {progress_str}",
                    source=self.source,
                    job_id=self.job_id,
                )

            # Process complete lines for important messages
            if "\n" in self._buffer or "\r" in self._buffer:
                lines = re.split(r"[\n\r]+", self._buffer)
                # Keep last incomplete line in buffer
                self._buffer = lines[-1] if lines else ""

                # Check each complete line for important messages
                for line in lines[:-1]:
                    # Clean ANSI escape sequences first
                    clean_line = self._clean_ansi(line).strip()
                    if not clean_line:
                        continue

                    # Skip lines that are ONLY box-drawing characters (pure decorative lines)
                    # But keep lines that have actual content mixed with table borders
                    stripped_of_borders = re.sub(
                        r"[─│╭╮╰╯┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬┏┓┗┛┃┡┩━╇╈╋\s]+", "", clean_line
                    )
                    if not stripped_of_borders:
                        continue

                    # Skip if already logged
                    line_hash = hash(clean_line[:100])  # Use first 100 chars for hash
                    if line_hash in self._logged_lines:
                        continue

                    # Check if it's an important line
                    if self._important_regex.search(clean_line):
                        self._logged_lines.add(line_hash)
                        # Keep logged lines set manageable
                        if len(self._logged_lines) > 1000:
                            self._logged_lines.clear()

                        # Clean up the line for display - remove table border characters
                        display_line = clean_line
                        # Remove table border characters but keep content
                        display_line = re.sub(
                            r"^[│┃]\s*", "", display_line
                        )  # Leading border
                        display_line = re.sub(
                            r"\s*[│┃]$", "", display_line
                        )  # Trailing border
                        display_line = re.sub(
                            r"\s*[│┃]\s*", " | ", display_line
                        )  # Middle borders to readable separator
                        display_line = display_line.strip()

                        # Remove timestamp prefix if present
                        timestamp_match = re.match(
                            r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\d]*\s*-?\s*",
                            display_line,
                        )
                        if timestamp_match:
                            display_line = display_line[timestamp_match.end() :]

                        # Determine the appropriate source based on content
                        # LLM-related logs should use 'llm' as source
                        log_source = self.source
                        if self._llm_patterns.search(display_line):
                            log_source = "llm"

                        stage_prefix = (
                            f"[{self.stage_name}] " if self.stage_name else ""
                        )
                        self.log_store.info(
                            f"{stage_prefix}{display_line}",
                            source=log_source,
                            job_id=self.job_id,
                        )

        return len(text)

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()


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
        log_store = get_log_store()
        job.start()

        # Clear BOTH cancel flags at the start (memory + file)
        state.clear_cancel_request()  # Clear in-memory flag
        clear_cancel_flag()  # Clear file-based flag

        # Log pipeline start
        log_store.info(
            f"开始字幕处理流程 (视频: {video.filename})",
            source="subtitle",
            job_id=job.id,
        )

        try:
            # Stage 1: ASR (Speech Recognition)
            await self._run_stage(job, "asr", self._run_asr)
            if state.is_cancel_requested():
                log_store.warning(
                    "字幕处理被用户取消", source="subtitle", job_id=job.id
                )
                return

            # Stage 2: NLP Split
            await self._run_stage(job, "split_nlp", self._run_split_nlp)
            if state.is_cancel_requested():
                log_store.warning(
                    "字幕处理被用户取消", source="subtitle", job_id=job.id
                )
                return

            # Stage 3: Meaning Split
            await self._run_stage(job, "split_meaning", self._run_split_meaning)
            if state.is_cancel_requested():
                log_store.warning(
                    "字幕处理被用户取消", source="subtitle", job_id=job.id
                )
                return

            # Stage 4: Summarize
            await self._run_stage(job, "summarize", self._run_summarize)
            if state.is_cancel_requested():
                log_store.warning(
                    "字幕处理被用户取消", source="subtitle", job_id=job.id
                )
                return

            # Stage 5: Translate
            await self._run_stage(job, "translate", self._run_translate)
            if state.is_cancel_requested():
                log_store.warning(
                    "字幕处理被用户取消", source="subtitle", job_id=job.id
                )
                return

            # Stage 6: Split Subtitles
            await self._run_stage(job, "split_sub", self._run_split_sub)
            if state.is_cancel_requested():
                log_store.warning(
                    "字幕处理被用户取消", source="subtitle", job_id=job.id
                )
                return

            # Stage 7: Generate Subtitles
            await self._run_stage(job, "gen_sub", self._run_gen_sub)
            if state.is_cancel_requested():
                log_store.warning(
                    "字幕处理被用户取消", source="subtitle", job_id=job.id
                )
                return

            # Complete (校对和合并移至独立Tab，用户手动操作)
            job.complete()
            video.status = "completed"
            logger.info("Subtitle processing completed successfully")
            log_store.info(
                f"字幕处理完成 (视频: {video.filename})",
                source="subtitle",
                job_id=job.id,
            )

        except Exception as e:
            logger.error(f"Subtitle processing failed: {e}", exc_info=True)
            job.fail(str(e))
            video.status = "error"
            video.error_message = str(e)
            log_store.error(f"字幕处理失败: {str(e)}", source="subtitle", job_id=job.id)
        finally:
            state.clear_cancel_request()
            clear_cancel_flag()  # Also clear file-based flag

    async def run_dubbing_processing(self, job: ProcessingJob, video: Video):
        """Run the dubbing processing pipeline"""
        state = get_app_state()
        log_store = get_log_store()
        job.start()

        # Clear BOTH cancel flags at the start (memory + file)
        state.clear_cancel_request()  # Clear in-memory flag
        clear_cancel_flag()  # Clear file-based flag

        # Log pipeline start
        log_store.info(
            f"开始配音处理流程 (视频: {video.filename})",
            source="dubbing",
            job_id=job.id,
        )

        try:
            # Stage 1: Audio Task
            await self._run_stage(job, "audio_task", self._run_audio_task)
            if state.is_cancel_requested():
                log_store.warning("配音处理被用户取消", source="dubbing", job_id=job.id)
                return

            # Stage 2: Dub Chunks
            await self._run_stage(job, "dub_chunks", self._run_dub_chunks)
            if state.is_cancel_requested():
                log_store.warning("配音处理被用户取消", source="dubbing", job_id=job.id)
                return

            # Stage 3: Refer Audio
            await self._run_stage(job, "refer_audio", self._run_refer_audio)
            if state.is_cancel_requested():
                log_store.warning("配音处理被用户取消", source="dubbing", job_id=job.id)
                return

            # Stage 4: Generate Audio
            await self._run_stage(job, "gen_audio", self._run_gen_audio)
            if state.is_cancel_requested():
                log_store.warning("配音处理被用户取消", source="dubbing", job_id=job.id)
                return

            # Stage 5: Merge Audio
            await self._run_stage(job, "merge_audio", self._run_merge_audio)
            if state.is_cancel_requested():
                log_store.warning("配音处理被用户取消", source="dubbing", job_id=job.id)
                return

            # Stage 6: Dub to Video
            await self._run_stage(job, "dub_to_vid", self._run_dub_to_vid)

            # Complete
            job.complete()
            video.status = "completed"
            logger.info("Dubbing processing completed successfully")
            log_store.info(
                f"配音处理完成 (视频: {video.filename})",
                source="dubbing",
                job_id=job.id,
            )

        except Exception as e:
            logger.error(f"Dubbing processing failed: {e}", exc_info=True)
            job.fail(str(e))
            video.status = "error"
            video.error_message = str(e)
            log_store.error(f"配音处理失败: {str(e)}", source="dubbing", job_id=job.id)
        finally:
            state.clear_cancel_request()
            clear_cancel_flag()  # Also clear file-based flag

    async def _run_stage(self, job: ProcessingJob, stage_name: str, stage_func):
        """Run a single processing stage with output capture"""
        log_store = get_log_store()
        start_time = time.perf_counter()

        logger.info(f"Starting stage: {stage_name}")

        # Stage description messages
        stage_messages = {
            "asr": "正在进行语音识别...",
            "split_nlp": "正在使用 NLP 进行分句处理...",
            "split_meaning": "正在按语义进行句子分割...",
            "summarize": "正在生成内容摘要...",
            "translate": "正在翻译字幕...",
            "split_sub": "正在分割字幕...",
            "gen_sub": "正在生成字幕文件...",
            "merge_sub": "正在将字幕合并到视频...",
            "audio_task": "正在生成音频任务...",
            "dub_chunks": "正在生成配音片段...",
            "refer_audio": "正在提取参考音频...",
            "gen_audio": "正在生成配音...",
            "merge_audio": "正在合并音频...",
            "dub_to_vid": "正在将配音合并到视频...",
        }

        message = stage_messages.get(stage_name, f"正在处理 {stage_name}...")
        job.update_stage(stage_name, "running", message=message)
        job.current_stage = stage_name

        # Log stage start to LogStore (only once at the beginning)
        log_store.info(f"[{stage_name}] {message}", source=job.job_type, job_id=job.id)

        def run_with_capture():
            """Run stage function with stdout/stderr capture for tqdm progress"""
            # Capture both stdout and stderr where tqdm might write progress
            original_stderr = sys.stderr
            original_stdout = sys.stdout
            capture_stderr = TqdmCapture(
                log_store, job.job_type, job.id, original_stderr, stage_name
            )
            capture_stdout = TqdmCapture(
                log_store, job.job_type, job.id, original_stdout, stage_name
            )
            try:
                sys.stderr = capture_stderr
                sys.stdout = capture_stdout
                stage_func()
            finally:
                sys.stderr = original_stderr
                sys.stdout = original_stdout

        try:
            # Run the stage function in a thread pool with output capture
            await asyncio.to_thread(run_with_capture)

            # Calculate duration
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            job.update_stage(stage_name, "completed", progress=100, message="完成")
            logger.info(f"Stage {stage_name} completed in {duration_ms}ms")

            # Log stage completion with duration
            log_store.info(
                f"[{stage_name}] 完成 (耗时: {duration_ms}ms)",
                source=job.job_type,
                job_id=job.id,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Stage {stage_name} failed: {e}")
            job.update_stage(
                stage_name, "failed", error=str(e), message=f"失败: {str(e)[:50]}"
            )

            # Log stage failure
            log_store.error(
                f"[{stage_name}] 失败: {str(e)}",
                source=job.job_type,
                job_id=job.id,
                duration_ms=duration_ms,
            )
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
            "trans_subs_for_audio.json",  # Created during subtitle processing
            "audio_task.json",  # Created during dubbing
        ]

        for marker in markers:
            if (self.output_dir / marker).exists():
                # Check if final output exists
                final_outputs = list(self.output_dir.glob("*_with_*.mp4"))
                if not final_outputs:
                    return True

        return False

    def detect_completed_stages(self, job_type: str = "subtitle") -> dict:
        """
        Detect which stages are completed based on output files.
        Used to restore state after manual processing or server restart.

        Args:
            job_type: 'subtitle' or 'dubbing'

        Returns:
            dict with stage names and their completion status
        """
        from backend.models.stage import STAGE_OUTPUT_FILES

        completed_stages = {}

        if job_type == "subtitle":
            stage_order = [
                "asr",
                "split_nlp",
                "split_meaning",
                "summarize",
                "translate",
                "split_sub",
                "gen_sub",
            ]
        else:
            stage_order = [
                "audio_task",
                "dub_chunks",
                "refer_audio",
                "gen_audio",
                "merge_audio",
                "dub_to_vid",
            ]

        project_root = get_project_root()

        for stage_name in stage_order:
            if stage_name not in STAGE_OUTPUT_FILES:
                completed_stages[stage_name] = False
                continue

            # Check if at least one required output file exists
            stage_files = STAGE_OUTPUT_FILES[stage_name]
            has_output = False

            for file_def in stage_files:
                file_path = project_root / file_def["path"]
                if file_def["type"] == "folder":
                    # For folders, check if folder exists and has content
                    if file_path.exists() and file_path.is_dir():
                        if any(file_path.iterdir()):
                            has_output = True
                            break
                else:
                    if file_path.exists():
                        has_output = True
                        break

            completed_stages[stage_name] = has_output

        return completed_stages

    def is_subtitle_processing_completed(self) -> bool:
        """Check if subtitle processing has been completed"""
        # Check if final subtitle files exist
        src_srt = self.output_dir / "src.srt"
        trans_srt = self.output_dir / "trans.srt"
        return src_srt.exists() and trans_srt.exists()

    def is_dubbing_processing_completed(self) -> bool:
        """Check if dubbing processing has been completed"""
        # Check if final dubbing file exists
        dub_mp3 = self.output_dir / "dub.mp3"
        output_dub = self.output_dir / "output_dub.mp4"
        return dub_mp3.exists() or output_dub.exists()

    def restore_job_state(
        self, job_type: str = "subtitle"
    ) -> Optional["ProcessingJob"]:
        """
        Restore job state from output files.
        Creates a completed job if processing was done externally.

        Args:
            job_type: 'subtitle' or 'dubbing'

        Returns:
            ProcessingJob if state can be restored, None otherwise
        """
        from backend.models.stage import get_subtitle_stages, get_dubbing_stages
        from models import ProcessingJob

        if job_type == "subtitle":
            if not self.is_subtitle_processing_completed():
                return None
            stages = get_subtitle_stages()
        else:
            if not self.is_dubbing_processing_completed():
                return None
            stages = get_dubbing_stages()

        completed_stages = self.detect_completed_stages(job_type)

        # Create a job with restored state
        job = ProcessingJob(
            id=f"restored_{job_type}_{int(time.time())}",
            video_id="restored",
            job_type=job_type,
            status="completed",
            stages=stages,
        )

        # Mark completed stages
        for stage in job.stages:
            if completed_stages.get(stage.name, False):
                stage.status = "completed"

        return job

    def cleanup_subtitle_files(self) -> dict:
        """
        Clean up subtitle processing intermediate files

        Cleans:
        - output/log/ directory
        - output/gpt_log/ directory
        - *.srt files in output/

        Preserves:
        - audio/raw.mp3
        """
        cleaned_paths = []
        preserved_paths = []

        # Clean log directory
        log_dir = self.output_dir / "log"
        if log_dir.exists():
            import shutil

            shutil.rmtree(log_dir)
            cleaned_paths.append(str(log_dir))

        # Clean gpt_log directory
        gpt_log_dir = self.output_dir / "gpt_log"
        if gpt_log_dir.exists():
            import shutil

            shutil.rmtree(gpt_log_dir)
            cleaned_paths.append(str(gpt_log_dir))

        # Clean SRT files
        for srt_file in self.output_dir.glob("*.srt"):
            srt_file.unlink()
            cleaned_paths.append(str(srt_file))

        # Clean intermediate JSON files
        intermediate_files = [
            "transcript.json",
            "transcript_*.json",
            "sentence_*.json",
            "summary.json",
            "trans_*.json",
        ]
        for pattern in intermediate_files:
            for f in self.output_dir.glob(pattern):
                f.unlink()
                cleaned_paths.append(str(f))

        # Preserve raw audio
        raw_audio = self.output_dir / "audio" / "raw.mp3"
        if raw_audio.exists():
            preserved_paths.append(str(raw_audio))

        logger.info(
            f"Subtitle cleanup: cleaned {len(cleaned_paths)} items, preserved {len(preserved_paths)} items"
        )

        return {
            "success": True,
            "cleanedPaths": cleaned_paths,
            "preservedPaths": preserved_paths,
        }

    def cleanup_dubbing_files(self) -> dict:
        """
        Clean up dubbing processing intermediate files

        Cleans:
        - audio/segs/ directory
        - audio/refers/ directory
        - audio/tmp/ directory
        """
        cleaned_paths = []
        preserved_paths = []

        audio_dir = self.output_dir / "audio"

        # Clean segs directory
        segs_dir = audio_dir / "segs"
        if segs_dir.exists():
            import shutil

            shutil.rmtree(segs_dir)
            cleaned_paths.append(str(segs_dir))

        # Clean refers directory
        refers_dir = audio_dir / "refers"
        if refers_dir.exists():
            import shutil

            shutil.rmtree(refers_dir)
            cleaned_paths.append(str(refers_dir))

        # Clean tmp directory
        tmp_dir = audio_dir / "tmp"
        if tmp_dir.exists():
            import shutil

            shutil.rmtree(tmp_dir)
            cleaned_paths.append(str(tmp_dir))

        # Clean audio task and dub-related JSONs
        for json_file in self.output_dir.glob("audio_task*.json"):
            json_file.unlink()
            cleaned_paths.append(str(json_file))

        for json_file in self.output_dir.glob("*_dubbed*.json"):
            json_file.unlink()
            cleaned_paths.append(str(json_file))

        # Preserve raw audio
        raw_audio = audio_dir / "raw.mp3"
        if raw_audio.exists():
            preserved_paths.append(str(raw_audio))

        logger.info(
            f"Dubbing cleanup: cleaned {len(cleaned_paths)} items, preserved {len(preserved_paths)} items"
        )

        return {
            "success": True,
            "cleanedPaths": cleaned_paths,
            "preservedPaths": preserved_paths,
        }

    def cleanup_all_files(self) -> dict:
        """
        Clean up ALL processing files and reset to initial state

        Cleans everything EXCEPT the original video file:
        - output/log/ directory
        - output/gpt_log/ directory
        - output/audio/ directory (including raw.mp3, vocal.mp3, background.mp3)
        - All *.srt, output*.mp4 (output videos only), *.xlsx, *.json, *.mp3 files

        IMPORTANT: Original video files are preserved!
        """
        import shutil

        cleaned_paths = []
        preserved_paths = []

        # Use unified output directory (project_root/output/)
        output_dir = self.output_dir

        if not output_dir.exists():
            return {"success": True, "cleanedPaths": [], "preservedPaths": []}

        # First, identify and preserve original video files (any .mp4 not starting with "output")
        for video_file in output_dir.glob("*.mp4"):
            if not video_file.name.startswith("output"):
                preserved_paths.append(str(video_file))

        # Clean log directory
        log_dir = output_dir / "log"
        if log_dir.exists():
            shutil.rmtree(log_dir)
            cleaned_paths.append(str(log_dir))

        # Clean gpt_log directory
        gpt_log_dir = output_dir / "gpt_log"
        if gpt_log_dir.exists():
            shutil.rmtree(gpt_log_dir)
            cleaned_paths.append(str(gpt_log_dir))

        # Clean entire audio directory
        audio_dir = output_dir / "audio"
        if audio_dir.exists():
            shutil.rmtree(audio_dir)
            cleaned_paths.append(str(audio_dir))

        # Clean SRT files
        for srt_file in output_dir.glob("*.srt"):
            srt_file.unlink()
            cleaned_paths.append(str(srt_file))

        # Clean output video files ONLY (files starting with "output")
        for video_file in output_dir.glob("output*.mp4"):
            video_file.unlink()
            cleaned_paths.append(str(video_file))

        # Clean Excel files
        for xlsx_file in output_dir.glob("*.xlsx"):
            xlsx_file.unlink()
            cleaned_paths.append(str(xlsx_file))

        # Clean JSON files
        for json_file in output_dir.glob("*.json"):
            json_file.unlink()
            cleaned_paths.append(str(json_file))

        # Clean MP3 files in root output dir (dub.mp3 etc)
        for mp3_file in output_dir.glob("*.mp3"):
            mp3_file.unlink()
            cleaned_paths.append(str(mp3_file))

        logger.info(
            f"Full cleanup: cleaned {len(cleaned_paths)} items, preserved {len(preserved_paths)} original videos"
        )

        return {
            "success": True,
            "cleanedPaths": cleaned_paths,
            "preservedPaths": preserved_paths,
        }

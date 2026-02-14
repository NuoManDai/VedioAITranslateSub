"""
Batch Processing Service - Runs sequential pipeline processing for batch jobs
"""

import sys
import shutil
import asyncio
import logging
from pathlib import Path
from typing import Optional

from api.deps import get_project_root, get_output_dir
from services.batch_service import BatchService
from services.config_service import ConfigService
from models.batch_models import BatchFile

logger = logging.getLogger(__name__)


class BatchProcessingService:
    """Orchestrates sequential batch processing of video files"""

    def __init__(self, batch_service: BatchService):
        self.batch_service = batch_service
        self.config_service = ConfigService()
        self.project_root = get_project_root()
        self.output_dir = get_output_dir()
        self._cancel_requested = False
        self._setup_core_imports()

    def _setup_core_imports(self):
        """Setup imports for core modules"""
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))

    def request_cancel(self):
        """Request cancellation of batch processing"""
        self._cancel_requested = True

    def is_cancel_requested(self) -> bool:
        """Check if cancellation has been requested"""
        return self._cancel_requested

    def clear_cancel_request(self):
        """Clear the cancellation flag"""
        self._cancel_requested = False

    # ------------
    # Output Directory Management
    # ------------

    def _clean_output_dir(self):
        """
        Clean the output directory for the next file.
        Removes everything from output/ to start fresh.
        """
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _copy_video_to_output(self, filepath: str) -> str:
        """
        Copy uploaded video file to output/ directory.
        Core modules expect the video to be in output/.

        Returns:
            The filename in the output directory
        """
        src = Path(filepath)
        if not src.exists():
            raise FileNotFoundError(f"Video file not found: {filepath}")

        dst = self.output_dir / src.name
        shutil.copy2(str(src), str(dst))
        return src.name

    def _save_output(self, video_name: str) -> str:
        """
        Save processed output files to batch/output/{video_name}/.
        Copies all output files (SRT, MP4, etc.) to the batch output directory.

        Returns:
            The output directory path
        """
        base_name = Path(video_name).stem
        save_dir = self.project_root / "batch" / "output" / base_name
        save_dir.mkdir(parents=True, exist_ok=True)

        if self.output_dir.exists():
            for item in self.output_dir.iterdir():
                dst = save_dir / item.name
                if item.is_dir():
                    if dst.exists():
                        shutil.rmtree(str(dst))
                    shutil.copytree(str(item), str(dst))
                else:
                    shutil.copy2(str(item), str(dst))

        return str(save_dir)

    # ------------
    # Config Management
    # ------------

    def _update_config_for_file(self, batch_file: BatchFile):
        """
        Update config.yaml with the file's source/target language settings.
        Uses ConfigService.update_config for proper YAML handling.
        """
        from models import ConfigurationUpdate

        update_data = {}

        # Map source_lang to whisper.language
        if batch_file.source_lang and batch_file.source_lang != "auto":
            update_data["whisper"] = {"language": batch_file.source_lang}
            update_data["source_language"] = batch_file.source_lang

        # Map target_lang
        if batch_file.target_lang:
            update_data["target_language"] = batch_file.target_lang

        if update_data:
            config_update = ConfigurationUpdate(**update_data)
            self.config_service.update_config(config_update)

    # ------------
    # Pipeline Stages
    # ------------

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

    async def _run_stage(self, stage_name: str, stage_func):
        """Run a single processing stage in a thread pool"""
        logger.info(f"[Batch] Starting stage: {stage_name}")
        try:
            await asyncio.to_thread(stage_func)
            logger.info(f"[Batch] Stage completed: {stage_name}")
        except Exception as e:
            logger.error(f"[Batch] Stage failed: {stage_name} - {e}")
            raise

    # ------------
    # Subtitle Pipeline
    # ------------

    async def _run_subtitle_pipeline(self):
        """Run the full subtitle processing pipeline"""
        stages = [
            ("asr", self._run_asr),
            ("split_nlp", self._run_split_nlp),
            ("split_meaning", self._run_split_meaning),
            ("summarize", self._run_summarize),
            ("translate", self._run_translate),
            ("split_sub", self._run_split_sub),
            ("gen_sub", self._run_gen_sub),
            ("merge_sub", self._run_merge_sub),
        ]

        for stage_name, stage_func in stages:
            if self._cancel_requested:
                logger.warning("[Batch] Processing cancelled by user")
                raise asyncio.CancelledError("Batch processing cancelled")
            await self._run_stage(stage_name, stage_func)

    # ------------
    # Dubbing Pipeline
    # ------------

    async def _run_dubbing_pipeline(self):
        """Run the full dubbing processing pipeline"""
        stages = [
            ("audio_task", self._run_audio_task),
            ("dub_chunks", self._run_dub_chunks),
            ("refer_audio", self._run_refer_audio),
            ("gen_audio", self._run_gen_audio),
            ("merge_audio", self._run_merge_audio),
            ("dub_to_vid", self._run_dub_to_vid),
        ]

        for stage_name, stage_func in stages:
            if self._cancel_requested:
                logger.warning("[Batch] Dubbing cancelled by user")
                raise asyncio.CancelledError("Batch dubbing cancelled")
            await self._run_stage(stage_name, stage_func)

    # ------------
    # Single File Processing
    # ------------

    async def _process_single_file(self, batch_file: BatchFile) -> Optional[str]:
        """
        Process a single file through the pipeline.

        Returns:
            Output directory path on success, None on failure
        """
        logger.info(
            f"[Batch] Processing file: {batch_file.filename} (id={batch_file.id})"
        )

        # Update file status to processing
        self.batch_service.update_file_status(batch_file.id, "processing")

        try:
            # Step 1: Clean output directory
            self._clean_output_dir()

            # Step 2: Update config for this file's language settings
            self._update_config_for_file(batch_file)

            # Step 3: Copy video to output directory
            if not batch_file.filepath:
                raise ValueError(f"File has no filepath: {batch_file.filename}")
            self._copy_video_to_output(batch_file.filepath)

            # Step 4: Run subtitle pipeline
            await self._run_subtitle_pipeline()

            # Step 5: Run dubbing pipeline if enabled
            if batch_file.dubbing:
                await self._run_dubbing_pipeline()

            # Step 6: Save output to batch/output/{video_name}/
            output_path = self._save_output(batch_file.filename)

            # Step 7: Mark file as completed
            self.batch_service.update_file_status(batch_file.id, "completed")

            # Update output path in DB
            self.batch_service.db.update_file_output(batch_file.id, output_path)

            logger.info(f"[Batch] File completed: {batch_file.filename}")
            return output_path

        except asyncio.CancelledError:
            self.batch_service.update_file_status(
                batch_file.id, "cancelled", error_message="Cancelled by user"
            )
            raise
        except Exception as e:
            error_msg = str(e)[:500]
            logger.error(f"[Batch] File failed: {batch_file.filename} - {error_msg}")
            self.batch_service.update_file_status(
                batch_file.id, "failed", error_message=error_msg
            )
            return None

    # ------------
    # Main Processing Entry Point
    # ------------

    async def process_batch(self, job_id: str):
        """
        Process all files in a batch job sequentially.
        Best-effort: continues processing remaining files even if one fails.

        Args:
            job_id: The batch job ID to process
        """
        self.clear_cancel_request()

        # Get batch details
        batch = self.batch_service.get_batch_status(job_id)
        if not batch:
            logger.error(f"[Batch] Job not found: {job_id}")
            return

        if not batch.files:
            logger.warning(f"[Batch] No files in job: {job_id}")
            self.batch_service.update_job_status(job_id, "completed")
            return

        # Update job status to processing
        self.batch_service.update_job_status(job_id, "processing")

        completed_count = 0
        failed_count = 0

        try:
            # Process files sequentially
            for batch_file in batch.files:
                if self._cancel_requested:
                    logger.warning(
                        f"[Batch] Cancellation requested, stopping job {job_id}"
                    )
                    # Cancel remaining files
                    for remaining_file in batch.files:
                        if remaining_file.status in ("pending", "queued"):
                            self.batch_service.update_file_status(
                                remaining_file.id, "cancelled"
                            )
                    break

                # Skip files that are not in pending/queued state
                if batch_file.status not in ("pending", "queued"):
                    if batch_file.status == "completed":
                        completed_count += 1
                    elif batch_file.status == "failed":
                        failed_count += 1
                    continue

                # Process the file
                result = await self._process_single_file(batch_file)
                if result:
                    completed_count += 1
                else:
                    failed_count += 1

        except asyncio.CancelledError:
            logger.warning(f"[Batch] Job cancelled: {job_id}")
            self.batch_service.update_job_status(job_id, "cancelled")
            return
        except Exception as e:
            logger.error(f"[Batch] Unexpected error in job {job_id}: {e}")
            self.batch_service.update_job_status(job_id, "failed")
            return
        finally:
            self.clear_cancel_request()

        # Determine final job status
        if self._cancel_requested:
            self.batch_service.update_job_status(job_id, "cancelled")
        elif failed_count > 0 and completed_count == 0:
            self.batch_service.update_job_status(job_id, "failed")
        else:
            self.batch_service.update_job_status(job_id, "completed")

        logger.info(
            f"[Batch] Job {job_id} finished: "
            f"{completed_count} completed, {failed_count} failed"
        )

"""
VedioAITranslateSub Backend - FastAPI Application
"""

import os
import shutil
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

# Add project root and backend to path for module imports
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

# Configure FFmpeg path for pydub (Windows)
FFMPEG_PATH = r"C:\ffmpeg"
if os.path.exists(FFMPEG_PATH):
    # Add to PATH environment variable
    os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")
    # Configure pydub to use our FFmpeg installation
    from pydub import AudioSegment

    AudioSegment.converter = os.path.join(FFMPEG_PATH, "ffmpeg.exe")
    AudioSegment.ffmpeg = os.path.join(FFMPEG_PATH, "ffmpeg.exe")
    AudioSegment.ffprobe = os.path.join(FFMPEG_PATH, "ffprobe.exe")

# Configure HuggingFace mirror and HTTP proxy from config
try:
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

            # Configure HTTP proxy for HuggingFace downloads
            http_proxy = config.get("http_proxy", "")
            if http_proxy:
                os.environ["HTTP_PROXY"] = http_proxy
                os.environ["HTTPS_PROXY"] = http_proxy
                os.environ["HF_HUB_HTTP_PROXY"] = http_proxy

            # Configure HuggingFace mirror (use default if empty)
            hf_mirror = config.get("hf_mirror", "") or "https://hf-mirror.com"
            os.environ["HF_ENDPOINT"] = hf_mirror
            # Disable xethub storage backend which causes download issues in China
            os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
            os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
except Exception:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from api.routes import video, processing, config, logs, files, subtitles, batch
from database.video_db import VideoDB

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests and responses"""

    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()

        # Log request
        logger.info(f"→ {request.method} {request.url.path}")

        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"← {request.method} {request.url.path} "
                f"[{response.status_code}] ({duration:.3f}s)"
            )

            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"← {request.method} {request.url.path} "
                f"[ERROR] ({duration:.3f}s): {str(e)}"
            )
            raise


def _is_uuid_dir(name: str) -> bool:
    """Check if a directory name is a valid UUID."""
    try:
        uuid.UUID(name)
        return True
    except (ValueError, AttributeError):
        return False


# Video file extensions to detect during legacy migration
_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm"}


def migrate_legacy_output():
    """
    Migrate legacy single-video output/ directory to per-video structure.

    Legacy layout: output/video.mp4, output/log/, output/audio/, etc.
    New layout: output/{uuid}/video.mp4, output/{uuid}/log/, etc.

    This function is idempotent - it skips if already migrated.
    Errors are logged but don't block startup.
    """
    try:
        from api.deps import OUTPUT_DIR
        from database.video_db import VideoDB

        # Check if output directory exists
        if not OUTPUT_DIR.exists():
            return

        # Check if output directory is empty
        items = list(OUTPUT_DIR.iterdir())
        if not items:
            return

        # Check if already migrated: all items are UUID-named directories
        if all(item.is_dir() and _is_uuid_dir(item.name) for item in items):
            logger.debug("Output directory already migrated (only UUID dirs found)")
            return

        # Identify legacy video files (direct children of output/)
        video_files = [
            item
            for item in items
            if item.is_file() and item.suffix.lower() in _VIDEO_EXTENSIONS
        ]

        if not video_files:
            # No video files found at top level — could be partial state, skip
            logger.debug("No legacy video files found in output/, skipping migration")
            return

        # Pick the first video file (single-video mode should have only one)
        video_file = video_files[0]
        video_id = str(uuid.uuid4())
        target_dir = OUTPUT_DIR / video_id

        logger.info(
            f"Migrating legacy output to per-video structure: output/{video_id}/"
        )

        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Move ALL contents of output/ to output/{video_id}/
        # Skip any existing UUID-named subdirectories
        for item in items:
            if item.is_dir() and _is_uuid_dir(item.name):
                continue

            dst = target_dir / item.name
            shutil.move(str(item), str(dst))
            logger.debug(f"Moved {item.name} -> {video_id}/{item.name}")

        # Create database record for the migrated video
        db = VideoDB()
        video_filename = video_file.name
        video_filepath = f"output/{video_id}/{video_filename}"

        # Determine status: 'completed' if pipeline output exists, 'ready' otherwise
        has_output = (target_dir / "log").exists()
        status = "completed" if has_output else "ready"

        # Get file size
        video_path = target_dir / video_filename
        file_size = video_path.stat().st_size if video_path.exists() else None

        db.create_video(
            filename=video_filename,
            filepath=video_filepath,
            source_type="upload",
            status=status,
            file_size=file_size,
        )

        logger.info(f"Migrated legacy output to output/{video_id}/")

    except Exception as e:
        logger.error(f"Legacy output migration failed (non-fatal): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("=" * 50)
    logger.info("Starting VedioAITranslateSub Backend...")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info("=" * 50)

    # Initialize video database
    VideoDB().init_db()
    logger.info("Video database initialized")

    # Migrate legacy output data (if any)
    migrate_legacy_output()

    yield
    logger.info("Shutting down VedioAITranslateSub Backend...")


app = FastAPI(
    title="VedioAITranslateSub API",
    description="视频翻译字幕和配音处理 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# HTTP Exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": f"HTTP_{exc.status_code}"},
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please check logs for details.",
            "error": str(exc),
            "code": "INTERNAL_ERROR",
        },
    )


# Validation error handler
from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "code": "VALIDATION_ERROR",
        },
    )


# Include routers
app.include_router(video.router, prefix="/api/video", tags=["Video"])
app.include_router(processing.router, prefix="/api/processing", tags=["Processing"])
app.include_router(config.router, prefix="/api/config", tags=["Config"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(files.router, prefix="/api", tags=["Files"])
app.include_router(subtitles.router, prefix="/api/subtitles", tags=["Subtitles"])
app.include_router(batch.router, prefix="/api/batch", tags=["Batch"])


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"status": "ok", "app": "VedioAITranslateSub", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(PROJECT_ROOT / "backend"), str(PROJECT_ROOT / "core")],
    )

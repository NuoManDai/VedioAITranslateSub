@echo off
chcp 65001 >nul
cd /D "%~dp0"
cd ..

echo ========================================
echo    VideoLingo Batch Processor
echo ========================================
echo.
echo NOTE: Make sure the backend is running first!
echo       Run start_backend.bat in another terminal
echo.

call conda activate videolingo

@rem 运行批处理脚本
call python -m batch.utils.batch_processor

:end
pause

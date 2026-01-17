@echo off
REM VedioAITranslateSub Backend Startup Script
REM This script starts the FastAPI backend server

setlocal enabledelayedexpansion

set PORT=8000
set HOST=127.0.0.1

echo ================================
echo VedioAITranslateSub Backend
echo ================================
echo.

REM Change to project root
cd /d "%~dp0"

REM Check conda environment
if not "%CONDA_DEFAULT_ENV%"=="videolingo" (
    echo Activating conda environment 'videolingo'...
    call conda activate videolingo 2>nul
    if errorlevel 1 (
        echo Warning: Could not activate conda environment.
    )
)

REM Skip dependency check for faster startup
REM To install dependencies manually: pip install -r backend\requirements.txt

echo.
echo Starting FastAPI server on http://%HOST%:%PORT%
echo Swagger UI available at http://%HOST%:%PORT%/docs
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run uvicorn
python -m uvicorn backend.main:app --host %HOST% --port %PORT% --reload

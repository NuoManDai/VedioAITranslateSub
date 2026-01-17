@echo off
REM VedioAITranslateSub Frontend Startup Script
REM This script starts the React frontend development server

setlocal enabledelayedexpansion

set PORT=5173

echo ================================
echo VedioAITranslateSub Frontend
echo ================================
echo.

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VER=%%i
echo Node.js version: %NODE_VER%

REM Change to frontend directory
cd /d "%~dp0frontend"

REM Install dependencies if node_modules doesn't exist
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
    echo.
)

echo Starting Vite development server on http://localhost:%PORT%
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run Vite
set VITE_PORT=%PORT%
call npm run dev

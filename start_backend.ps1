# VedioAITranslateSub Backend Startup Script
# This script starts the FastAPI backend server

param(
    [int]$Port = 8000,
    [string]$Host = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

# Get project root directory
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "================================" -ForegroundColor Cyan
Write-Host "VedioAITranslateSub Backend" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the conda environment
$condaEnv = $env:CONDA_DEFAULT_ENV
if ($condaEnv -ne "videolingo") {
    Write-Host "Activating conda environment 'videolingo'..." -ForegroundColor Yellow
    # Try to activate conda environment
    try {
        conda activate videolingo
    } catch {
        Write-Host "Warning: Could not activate conda environment. Make sure it exists." -ForegroundColor Yellow
    }
}

# Change to project root
Set-Location $ProjectRoot

# Skip dependency check for faster startup
# To install dependencies manually: pip install -r backend\requirements.txt

# Start the FastAPI server
Write-Host ""
Write-Host "Starting FastAPI server on http://${Host}:${Port}" -ForegroundColor Green
Write-Host "Swagger UI available at http://${Host}:${Port}/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Run uvicorn
python -m uvicorn backend.main:app --host $Host --port $Port --reload

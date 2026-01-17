# VedioAITranslateSub Frontend Startup Script
# This script starts the React frontend development server

param(
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"

# Get project root directory
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "VedioAITranslateSub Frontend" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check Node.js version
try {
    $nodeVersion = node --version
    Write-Host "Node.js version: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Node.js is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Node.js 18+ from https://nodejs.org" -ForegroundColor Yellow
    exit 1
}

# Change to frontend directory
Set-Location $FrontendDir

# Install dependencies if node_modules doesn't exist
$nodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    npm install
    Write-Host ""
}

# Start the Vite dev server
Write-Host "Starting Vite development server on http://localhost:${Port}" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Set port and run
$env:VITE_PORT = $Port
npm run dev

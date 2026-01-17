# VideoLingo 快速启动脚本 (PowerShell)
# ========================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   VideoLingo 启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置 conda 环境路径
$CONDA_ENV = "D:\conda_data\envs\videolingo"

# 设置 PATH (解决 SQLite3 DLL 问题)
$env:Path = "$CONDA_ENV\Scripts;$CONDA_ENV\Library\bin;$CONDA_ENV\DLLs;$CONDA_ENV;" + $env:Path

# 切换到脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "[1/2] 正在初始化环境..." -ForegroundColor Yellow
Write-Host "环境路径: $CONDA_ENV" -ForegroundColor Gray
Write-Host ""

Write-Host "[2/2] 正在启动 VideoLingo..." -ForegroundColor Yellow
Write-Host "访问地址: " -NoNewline -ForegroundColor Gray
Write-Host "http://localhost:8501" -ForegroundColor Green
Write-Host ""

# 启动 Streamlit 应用
& "$CONDA_ENV\python.exe" -m streamlit run st.py

@echo off
chcp 65001 >nul
echo ========================================
echo    VideoLingo 启动脚本
echo ========================================
echo.

:: 设置 conda 环境路径
set CONDA_ENV=D:\conda_data\envs\videolingo
set PATH=%CONDA_ENV%\Scripts;%CONDA_ENV%\Library\bin;%CONDA_ENV%\DLLs;%CONDA_ENV%;%PATH%

:: 切换到项目目录
cd /d "%~dp0"

echo [1/2] 正在初始化环境...
echo 环境路径: %CONDA_ENV%
echo.

echo [2/2] 正在启动 VideoLingo...
echo 访问地址: http://localhost:8501
echo.

:: 启动 Streamlit 应用
"%CONDA_ENV%\python.exe" -m streamlit run st.py

pause

@echo off
rem ============================================
rem Lumina Live Demo Stream (MediaMTX + ffmpeg)
rem One-click: start MediaMTX then push demo frame
rem Usage:  start_demo_stream.bat [stream_key]
rem Default key = roomdemo (matches demo room)
rem ============================================
setlocal
set KEY=%~1
if "%KEY%"=="" set KEY=roomdemo

set VENV_PY=%~dp0..\..\服务\lumina-app\.venv\Scripts\python.exe
set MTX_EXE=%~dp0mediamtx\mediamtx.exe

if not exist "%VENV_PY%" (
  echo [ERROR] venv python not found: %VENV_PY%
  exit /b 1
)
if not exist "%MTX_EXE%" (
  echo [ERROR] mediamtx.exe not found. Run setup_stream.bat first.
  exit /b 1
)

echo [1/3] Starting MediaMTX (RTMP 1935 / HLS 8888) ...
start "MediaMTX" /min "%MTX_EXE%" "%~dp0mediamtx\mediamtx.yml"
timeout /t 3 /nobreak >nul

echo [2/3] Checking ffmpeg ...
"%VENV_PY%" -c "import shutil,imageio_ffmpeg,sys; print('ffmpeg:', shutil.which('ffmpeg') or imageio_ffmpeg.get_ffmpeg_exe())"

echo [3/3] Pushing stream to rtmp://127.0.0.1:1935/live/%KEY%  (Ctrl+C to stop)
"%VENV_PY%" "%~dp0media_demo_stream.py" --key "%KEY%"
endlocal
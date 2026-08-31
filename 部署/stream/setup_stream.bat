@echo off
rem ============================================
rem Lumina Live Demo Stream - setup (Windows)
rem Installs: mediamtx.exe + ffmpeg (venv imageio-ffmpeg)
rem For other OS: download mediamtx release and install ffmpeg manually.
rem ============================================
setlocal
set VENV_PY=%~dp0..\..\服务\lumina-app\.venv\Scripts\python.exe
set MTX_EXE=%~dp0mediamtx\mediamtx.exe

if exist "%MTX_EXE%" (
  echo [OK] mediamtx.exe already present.
) else (
  echo [..] mediamtx.exe missing. Download mediamtx v1.20.1 windows_amd64:
  echo      https://github.com/bluenviron/mediamtx/releases/download/v1.20.1/mediamtx_v1.20.1_windows_amd64.zip
  echo      Extract into: %~dp0mediamtx\  (keep mediamtx.exe + mediamtx.yml)
  echo.
  echo      Or run in PowerShell:
  echo      curl.exe -L -o %~dp0mediamtx.zip https://github.com/bluenviron/mediamtx/releases/download/v1.20.1/mediamtx_v1.20.1_windows_amd64.zip
  echo      then unzip it into this folder.
  echo Continuing only with ffmpeg step...
)

echo [..] Ensuring ffmpeg (imageio-ffmpeg) in lumina-app venv ...
if exist "%VENV_PY%" (
  "%VENV_PY%" -m pip install imageio-ffmpeg -q
  "%VENV_PY%" -c "import imageio_ffmpeg; print('[OK] ffmpeg:', imageio_ffmpeg.get_ffmpeg_exe())"
) else (
  echo [ERROR] venv python not found: %VENV_PY%
)
endlocal
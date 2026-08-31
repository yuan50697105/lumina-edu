@echo off
rem ============================================
rem Lumina Live Demo - stop MediaMTX & ffmpeg
rem ============================================
taskkill /IM mediamtx.exe /F >nul 2>&1
taskkill /IM ffmpeg.exe /F >nul 2>&1
taskkill /IM ffmpeg-win-x86_64-v7.1.exe /F >nul 2>&1
echo Stopped MediaMTX and ffmpeg.
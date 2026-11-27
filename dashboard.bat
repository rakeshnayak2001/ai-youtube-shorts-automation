@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
title yt-factory dashboard
REM Opens the control room at http://127.0.0.1:8765  (close this window to stop it)
python dashboard\server.py
pause

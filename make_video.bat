@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
REM Usage: make_video.bat            -> next topic from ideas.csv, render + upload (per config.json)
REM        make_video.bat --no-upload
REM        make_video.bat --topic "Why do cats purr?" --no-upload
python run.py %*
pause

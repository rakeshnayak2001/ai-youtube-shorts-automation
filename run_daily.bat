@echo off
REM Usage: run_daily.bat [start|finish]   (no argument = start)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set MODE=%1
if "%MODE%"=="" set MODE=start
if not exist state mkdir state
echo ===== %date% %time% (%MODE%) ===== >> state\log.txt
python run.py --daily-%MODE% >> state\log.txt 2>&1

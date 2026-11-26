@echo off
setlocal
cd /d "%~dp0"
title yt-factory setup
echo.
echo ===== yt-factory setup =====
echo.

set MISSING=0
where node >nul 2>nul || (echo [install] Node.js... & winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements & set MISSING=1)
where python >nul 2>nul || (echo [install] Python... & winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements & set MISSING=1)
where ffmpeg >nul 2>nul || (echo [install] FFmpeg... & winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements & set MISSING=1)

if "%MISSING%"=="1" (
  echo.
  echo Some tools were just installed. CLOSE this window and run setup.bat again
  echo so Windows picks up the new PATH.
  pause
  exit /b 0
)

where claude >nul 2>nul || echo [warn] 'claude' command not found. Install Claude Code CLI: npm install -g @anthropic-ai/claude-code   then run: claude   once to log in.

echo [1/3] Installing Node packages...
call npm install || goto :fail
echo [2/3] Installing Python packages...
python -m pip install -r requirements.txt || goto :fail
echo [3/3] Adding Remotion skills for Claude Code (optional)...
call npx --yes remotion skills add >nul 2>nul

echo.
echo Test render of the sample video (real voice, no upload)...
set PYTHONIOENCODING=utf-8
python run.py --slug why-does-a-week-have-7-days --no-upload || goto :fail

echo.
echo ===== Done! Your sample video is in the "out" folder. =====
echo Next: open this folder in Claude Code and type /make-video
start "" "%~dp0out"
pause
exit /b 0

:fail
echo.
echo Something failed above. Copy the error into Claude Code and ask it to fix it.
pause
exit /b 1

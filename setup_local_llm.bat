@echo off
setlocal
cd /d "%~dp0"
title yt-factory: local worker model setup
echo.
echo ===== Local worker LLM (Ollama) setup =====
echo Claude stays the master; this installs the free local "worker" model.
echo.
where ollama >nul 2>nul || (
  echo [install] Ollama...
  winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
  echo.
  echo Ollama was just installed. CLOSE this window and run setup_local_llm.bat again
  echo so Windows picks up the new PATH.
  pause
  exit /b 0
)

for /f "usebackq delims=" %%m in (`python -c "import json;print(json.load(open('config.json',encoding='utf-8')).get('llm',{}).get('worker',{}).get('model','qwen3:8b'))"`) do set MODEL=%%m
if "%MODEL%"=="" set MODEL=qwen3:8b

echo [1/3] Making sure the Ollama server is running...
ollama list >nul 2>nul || (start "" /min ollama serve & timeout /t 5 >nul)
echo [2/3] Downloading the worker model %MODEL% (a few GB, one time)...
ollama pull %MODEL% || goto :fail
echo [3/3] Python packages (MCP server for Claude Code)...
python -m pip install -r requirements.txt || goto :fail

echo.
python scripts\llm.py test local "Reply with exactly: worker ready"
echo.
echo ===== Done. Open the dashboard with dashboard.bat =====
pause
exit /b 0

:fail
echo Something failed above. Copy the error into Claude Code and ask it to fix it.
pause
exit /b 1

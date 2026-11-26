@echo off
cd /d "%~dp0"
set /p T=Time to run every day (24h, e.g. 18:30): 
schtasks /create /f /tn "yt-factory daily video" /sc daily /st %T% /tr "\"%~dp0run_daily.bat\""
echo.
echo Scheduled. To remove it later:  schtasks /delete /tn "yt-factory daily video" /f
echo Logs go to state\log.txt
pause

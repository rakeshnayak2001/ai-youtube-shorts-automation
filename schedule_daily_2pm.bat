@echo off
cd /d "%~dp0"
REM 2:00 PM start: plan a timely topic, start the film (or make the stickman video if credits are out)
schtasks /create /f /tn "yt-factory daily video" /sc daily /st 14:00 /tr "\"%~dp0run_daily.bat\" start"
REM 4:30 PM finish: render + upload the film (or a stickman video if its clips aren't ready)
schtasks /create /f /tn "yt-factory daily finish" /sc daily /st 16:30 /tr "\"%~dp0run_daily.bat\" finish"
echo.
echo Scheduled: 2:00 PM start and 4:30 PM finish, every day (while you're logged in).
echo One video per day. Logs: state\log.txt
echo Remove: schtasks /delete /tn "yt-factory daily video" /f  and  schtasks /delete /tn "yt-factory daily finish" /f
pause

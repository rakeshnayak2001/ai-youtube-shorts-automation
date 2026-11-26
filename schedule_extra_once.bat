@echo off
REM One-time extra video at the next 7:00 AM (render on this PC). Clips are made earlier by a Claude task.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$now=Get-Date; $t=$now.Date.AddHours(7); if ($now -ge $t) { $t=$t.AddDays(1) };" ^
  "$a=New-ScheduledTaskAction -Execute '%~dp0run_daily.bat' -Argument 'extra' -WorkingDirectory '%~dp0';" ^
  "Register-ScheduledTask -TaskName 'yt-factory extra video' -Trigger (New-ScheduledTaskTrigger -Once -At $t) -Action $a -Force | Out-Null;" ^
  "Write-Host ('Extra video scheduled for ' + $t.ToString('ddd dd MMM yyyy, hh:mm tt'))"
echo Logs: state\log.txt   Remove: schtasks /delete /tn "yt-factory extra video" /f
pause

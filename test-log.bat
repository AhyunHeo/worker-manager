@echo off
echo TEST START
echo Creating log file...

set "LOG_FILE=%USERPROFILE%\Downloads\test-log.txt"

echo This is a test > "%LOG_FILE%"
echo Log file created at: %LOG_FILE%

notepad "%LOG_FILE%"

pause

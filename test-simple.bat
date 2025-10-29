@echo off
echo Test batch file is running...
set "LOG_FILE=%~dp0test-simple.log"
echo [%date% %time%] Test log entry > "%LOG_FILE%"
echo Log file created at: %LOG_FILE%
pause

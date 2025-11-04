@echo off
REM Worker Manager Installation - BAT Wrapper
REM This wrapper executes the PowerShell script in hidden mode

setlocal

REM Get the directory where this BAT file is located
set "SCRIPT_DIR=%~dp0"
set "PS1_FILE=%SCRIPT_DIR%install-worker-manager.ps1"

REM Check if PS1 file exists
if not exist "%PS1_FILE%" (
    echo Error: install-worker-manager.ps1 not found
    pause
    exit /b 1
)

REM Execute PowerShell script in hidden mode
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%PS1_FILE%"

exit

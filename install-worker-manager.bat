@echo off
REM Check for administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-worker-manager.ps1"
) else (
    echo Requesting administrator privileges...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process '%~f0' -Verb RunAs"
)

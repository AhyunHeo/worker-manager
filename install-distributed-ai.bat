@echo off
REM ========================================
REM Distributed AI Platform Installer
REM Central Server + Worker Manager
REM ========================================

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Minimize current window
if not DEFINED IS_MINIMIZED (
    set IS_MINIMIZED=1
    start /min cmd /c "%~dpnx0" %*
    exit /b
)

REM Check for administrator privileges
net session >nul 2>&1
if !errorLevel! neq 0 (
    REM Request admin privileges with minimized window
    powershell.exe -NoProfile -Command "Start-Process cmd -ArgumentList '/min', '/c', '%~dpnx0' -Verb RunAs"
    exit /b
)

REM Run PowerShell script (same directory)
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-distributed-ai.ps1"

exit /b

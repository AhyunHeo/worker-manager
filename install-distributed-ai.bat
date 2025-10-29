@echo off
REM ========================================
REM Distributed AI Platform Installer
REM Central Server + Worker Manager
REM ========================================

echo.
echo ========================================
echo Distributed AI Platform Installer
echo ========================================
echo.
echo Launching GUI installer...
echo.

REM PowerShell GUI 버전 실행
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-distributed-ai.ps1"

if %errorlevel% neq 0 (
    echo.
    echo Installation failed or was cancelled.
    echo.
    pause
    exit /b %errorlevel%
)

exit /b 0

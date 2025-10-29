@echo off
REM ========================================
REM Distributed AI Platform Installer
REM Central Server + Worker Manager
REM ========================================

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Check for administrator privileges
net session >nul 2>&1
if !errorLevel! neq 0 (
    REM Request admin privileges
    powershell.exe -NoProfile -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

REM Run PowerShell script (GUI visible)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-distributed-ai.ps1"

exit /b

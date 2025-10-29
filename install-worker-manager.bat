@echo off
REM Simple wrapper to run PowerShell script
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-worker-manager.ps1"

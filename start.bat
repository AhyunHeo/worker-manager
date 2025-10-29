@echo off
REM Worker Manager Startup Script (Batch Launcher)
REM This script launches the PowerShell version (start.ps1) for full functionality

echo ========================================
echo Worker Manager - PowerShell Launcher
echo ========================================
echo.

REM PowerShell 사용 가능 여부 확인
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: PowerShell is not available on this system.
    echo Please install PowerShell or use manual setup.
    echo.
    pause
    exit /b 1
)

echo Starting Worker Manager via PowerShell...
echo.
echo Features:
echo   - LAN IP auto-detection
echo   - .env file auto-configuration
echo   - Firewall and port forwarding setup
echo   - Docker Compose startup
echo.

REM 전달된 인자를 수집
set "PS_ARGS="
:parse_args
if "%~1"=="" goto run_script
if /i "%~1"=="-d" set "PS_ARGS=%PS_ARGS% -d"
if /i "%~1"=="-f" set "PS_ARGS=%PS_ARGS% -f"
shift
goto parse_args

:run_script
REM PowerShell 스크립트 실행 (ExecutionPolicy 우회)
REM 관리자 권한은 start.ps1 내부에서 자동으로 요청됨
if defined PS_ARGS (
    echo Options:%PS_ARGS%
    echo.
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"%PS_ARGS%
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
)

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo PowerShell script completed
    echo ========================================
) else (
    echo.
    echo ERROR: PowerShell script failed
    echo Error code: %errorlevel%
    echo.
    pause
    exit /b %errorlevel%
)

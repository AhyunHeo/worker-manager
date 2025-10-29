@echo off
REM ========================================
REM Distributed AI Platform Installer
REM Central Server + Worker Manager
REM ========================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo Distributed AI Platform Installer
echo ========================================
echo.
echo This will install:
echo   - Central Server (Federated Learning Platform)
echo   - Worker Manager (Worker Node Management)
echo.
pause

REM ============================================
REM Step 1: LAN IP 자동 감지
REM ============================================
echo.
echo [1/7] Detecting LAN IP...

set "LAN_IP="
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    set "temp_ip=%%a"
    set "temp_ip=!temp_ip: =!"

    REM 192.168.x.x 대역만 허용 (Docker, WSL2 제외)
    echo !temp_ip! | findstr /R "^192\.168\." >nul
    if !errorlevel! equ 0 (
        echo !temp_ip! | findstr /R "^192\.168\.65\." >nul
        if !errorlevel! neq 0 (
            set "LAN_IP=!temp_ip!"
            goto :ip_found
        )
    )
)

:ip_found
if not defined LAN_IP (
    echo WARNING: Could not detect LAN IP automatically.
    set /p LAN_IP="Please enter your server LAN IP: "
)

echo Detected LAN IP: %LAN_IP%
echo.

REM ============================================
REM Step 2: Docker 확인
REM ============================================
echo [2/7] Checking Docker installation...

docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running!
    echo.
    echo Please install Docker Desktop from:
    echo https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)

echo Docker is installed and running.
echo.

REM ============================================
REM Step 3: 중앙서버 설치
REM ============================================
echo [3/7] Setting up Central Server...

set "CENTRAL_DIR=%USERPROFILE%\intown-central"
if not exist "%CENTRAL_DIR%" (
    mkdir "%CENTRAL_DIR%"
)

cd /d "%CENTRAL_DIR%"

REM docker-compose.yml 생성 (중앙서버)
echo Creating Central Server docker-compose.yml...
(
echo version: '3.8'
echo.
echo services:
echo   frontend:
echo     image: heoaa/intown-central-frontend:latest
echo     container_name: intown-frontend
echo     ports:
echo       - "0.0.0.0:3000:3000"
echo     environment:
echo       - NEXT_PUBLIC_API_URL=http://%LAN_IP%:8000
echo     restart: unless-stopped
echo     networks:
echo       - intown_net
echo.
echo   api:
echo     image: heoaa/intown-central-api:latest
echo     container_name: intown-api
echo     ports:
echo       - "0.0.0.0:8000:8000"
echo     environment:
echo       - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/intown
echo       - JWT_SECRET_KEY=your-secret-key-change-in-production
echo       - SERVER_IP=%LAN_IP%
echo     depends_on:
echo       - postgres
echo     restart: unless-stopped
echo     networks:
echo       - intown_net
echo.
echo   fl-server:
echo     image: heoaa/intown-fl-server:latest
echo     container_name: intown-fl-server
echo     ports:
echo       - "0.0.0.0:5002:5002"
echo     environment:
echo       - API_URL=http://api:8000
echo       - SERVER_IP=%LAN_IP%
echo     restart: unless-stopped
echo     networks:
echo       - intown_net
echo.
echo   postgres:
echo     image: postgres:15
echo     container_name: intown-postgres
echo     environment:
echo       - POSTGRES_DB=intown
echo       - POSTGRES_USER=postgres
echo       - POSTGRES_PASSWORD=postgres
echo     volumes:
echo       - central_db_data:/var/lib/postgresql/data
echo     ports:
echo       - "127.0.0.1:5432:5432"
echo     restart: unless-stopped
echo     networks:
echo       - intown_net
echo.
echo networks:
echo   intown_net:
echo     driver: bridge
echo.
echo volumes:
echo   central_db_data:
) > docker-compose.yml

echo Central Server docker-compose.yml created.
echo.

REM ============================================
REM Step 4: Worker Manager 설치
REM ============================================
echo [4/7] Setting up Worker Manager...

set "WM_DIR=%USERPROFILE%\worker-manager"
if not exist "%WM_DIR%" (
    mkdir "%WM_DIR%"
)

cd /d "%WM_DIR%"

REM docker-compose.yml 생성 (Worker Manager)
echo Creating Worker Manager docker-compose.yml...
(
echo version: '3.8'
echo.
echo services:
echo   worker-api:
echo     image: heoaa/worker-manager:latest
echo     container_name: worker-api
echo     privileged: true
echo     cap_add:
echo       - NET_ADMIN
echo       - NET_RAW
echo     environment:
echo       - DATABASE_URL=postgresql://worker:workerpass@postgres:5432/workerdb
echo       - API_PORT=8090
echo       - API_TOKEN=test-token-123
echo       - LOCAL_SERVER_IP=%LAN_IP%
echo       - CENTRAL_SERVER_URL=http://%LAN_IP%:8000
echo       - SERVERURL=%LAN_IP%
echo     volumes:
echo       - /var/run/docker.sock:/var/run/docker.sock
echo     ports:
echo       - "0.0.0.0:8090:8090"
echo     depends_on:
echo       - postgres
echo     restart: unless-stopped
echo     extra_hosts:
echo       - "host.docker.internal:host-gateway"
echo     networks:
echo       - worker_net
echo.
echo   postgres:
echo     image: postgres:15
echo     container_name: worker-postgres
echo     environment:
echo       - POSTGRES_DB=workerdb
echo       - POSTGRES_USER=worker
echo       - POSTGRES_PASSWORD=workerpass
echo     volumes:
echo       - worker_db_data:/var/lib/postgresql/data
echo     ports:
echo       - "127.0.0.1:5434:5432"
echo     restart: unless-stopped
echo     networks:
echo       - worker_net
echo.
echo   web-dashboard:
echo     image: heoaa/worker-manager-dashboard:latest
echo     container_name: worker-dashboard
echo     environment:
echo       - API_URL=http://worker-api:8090
echo       - API_TOKEN=test-token-123
echo       - LOCAL_SERVER_IP=%LAN_IP%
echo     ports:
echo       - "0.0.0.0:5000:5000"
echo     depends_on:
echo       - worker-api
echo     restart: unless-stopped
echo     networks:
echo       - worker_net
echo.
echo networks:
echo   worker_net:
echo     driver: bridge
echo.
echo volumes:
echo   worker_db_data:
) > docker-compose.yml

REM .env 파일 생성
(
echo LOCAL_SERVER_IP=%LAN_IP%
echo API_TOKEN=test-token-123
echo DATABASE_URL=postgresql://worker:workerpass@postgres:5432/workerdb
echo CENTRAL_SERVER_URL=http://%LAN_IP%:8000
echo TZ=Asia/Seoul
echo LOG_LEVEL=INFO
) > .env

echo Worker Manager files created.
echo.

REM ============================================
REM Step 5: 방화벽 설정 (PowerShell)
REM ============================================
echo [5/7] Setting up firewall rules...
echo This requires administrator privileges...
echo.

REM PowerShell 스크립트를 임시 파일로 생성
set "PS_SCRIPT=%TEMP%\setup-firewall-all.ps1"

(
echo # 관리자 권한 확인
echo $isAdmin = ^([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent^(^)^).IsInRole^([Security.Principal.WindowsBuiltInRole]::Administrator^)
echo if ^(-not $isAdmin^) {
echo     Write-Host "Requesting administrator privileges..." -ForegroundColor Yellow
echo     exit 1
echo }
echo.
echo Write-Host "Setting up firewall rules..." -ForegroundColor Cyan
echo.
echo # 포트 정의
echo $ports = @^(
echo     @{Name="Central-Frontend"; Port=3000; Protocol="TCP"},
echo     @{Name="Central-API"; Port=8000; Protocol="TCP"},
echo     @{Name="Central-FL"; Port=5002; Protocol="TCP"},
echo     @{Name="Worker-Dashboard"; Port=5000; Protocol="TCP"},
echo     @{Name="Worker-API"; Port=8090; Protocol="TCP"}
echo ^)
echo.
echo # 기존 규칙 삭제
echo foreach ^($portConfig in $ports^) {
echo     $ruleName = "DistributedAI-$^($portConfig.Name^)"
echo     $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
echo     if ^($existingRule^) {
echo         Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
echo     }
echo }
echo.
echo # 새 방화벽 규칙 추가
echo foreach ^($portConfig in $ports^) {
echo     $ruleName = "DistributedAI-$^($portConfig.Name^)"
echo     try {
echo         New-NetFirewallRule ``
echo             -DisplayName $ruleName ``
echo             -Direction Inbound ``
echo             -Protocol $portConfig.Protocol ``
echo             -LocalPort $portConfig.Port ``
echo             -Action Allow ``
echo             -Enabled True ``
echo             -Profile Domain,Private,Public ``
echo             -ErrorAction Stop ^| Out-Null
echo         Write-Host "  ✓ $^($portConfig.Name^): $^($portConfig.Port^)/$^($portConfig.Protocol^)" -ForegroundColor Green
echo     } catch {
echo         Write-Host "  ✗ $^($portConfig.Name^): Failed" -ForegroundColor Red
echo     }
echo }
echo.
echo Write-Host "Firewall setup completed!" -ForegroundColor Green
) > "%PS_SCRIPT%"

REM PowerShell 스크립트를 관리자 권한으로 실행
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process PowerShell.exe -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%PS_SCRIPT%\"' -Wait" 2>nul

del "%PS_SCRIPT%" 2>nul
echo.

REM ============================================
REM Step 6: Docker 이미지 Pull
REM ============================================
echo [6/7] Pulling Docker images...
echo This may take several minutes...
echo.

echo Pulling Central Server images...
cd /d "%CENTRAL_DIR%"
docker-compose pull

echo.
echo Pulling Worker Manager images...
cd /d "%WM_DIR%"
docker-compose pull

echo.

REM ============================================
REM Step 7: 서비스 시작
REM ============================================
echo [7/7] Starting services...
echo.

echo Starting Central Server...
cd /d "%CENTRAL_DIR%"
docker-compose down 2>nul
docker-compose up -d

echo.
echo Starting Worker Manager...
cd /d "%WM_DIR%"
docker-compose down 2>nul
docker-compose up -d

echo.
echo Waiting for services to start...
timeout /t 5 /nobreak >nul

REM ============================================
REM 완료
REM ============================================
echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Central Server:
echo   - Frontend:  http://%LAN_IP%:3000
echo   - API:       http://%LAN_IP%:8000
echo   - FL Server: http://%LAN_IP%:5002
echo.
echo Worker Manager:
echo   - Dashboard:    http://%LAN_IP%:5000
echo   - API:          http://%LAN_IP%:8090
echo   - Worker Setup: http://%LAN_IP%:8090/worker/setup
echo.
echo Installation directories:
echo   - Central Server: %CENTRAL_DIR%
echo   - Worker Manager: %WM_DIR%
echo.
echo Useful commands:
echo   View logs:  docker-compose logs -f
echo   Stop:       docker-compose down
echo   Restart:    docker-compose restart
echo.
pause

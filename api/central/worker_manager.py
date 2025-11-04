"""
Worker Manager Installation Module
중앙서버에 Worker Manager를 설치하는 스크립트 생성
"""


def generate_worker_manager_installer(server_ip: str) -> str:
    """
    Worker Manager 설치 스크립트 생성 (Docker Hub 이미지 사용)

    Args:
        server_ip: 서버 LAN IP

    Returns:
        str: 설치 스크립트 (PowerShell + Batch)
    """

    # Docker Compose 파일 내용
    docker_compose_yml = """version: '3.8'

services:
  worker-api:
    image: heoaa/worker-manager:latest
    container_name: worker-api
    privileged: true
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      - DATABASE_URL=$${DATABASE_URL:-postgresql://worker:workerpass@postgres:5432/workerdb}
      - API_PORT=8091
      - API_TOKEN=$${API_TOKEN:-test-token-123}
      - LOCAL_SERVER_IP=$${LOCAL_SERVER_IP}
      - CENTRAL_SERVER_URL=$${CENTRAL_SERVER_URL}
      - SERVERURL=$${LOCAL_SERVER_IP}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - "0.0.0.0:8091:8091"
    depends_on:
      - postgres
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - worker_net

  postgres:
    image: postgres:15
    container_name: worker-postgres
    environment:
      - POSTGRES_DB=workerdb
      - POSTGRES_USER=worker
      - POSTGRES_PASSWORD=workerpass
    volumes:
      - worker_db_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5434:5432"
    restart: unless-stopped
    networks:
      - worker_net

  web-dashboard:
    image: heoaa/worker-manager-dashboard:latest
    container_name: worker-dashboard
    environment:
      - API_URL=http://worker-api:8091
      - API_TOKEN=$${API_TOKEN:-test-token-123}
      - LOCAL_SERVER_IP=$${LOCAL_SERVER_IP}
    ports:
      - "0.0.0.0:5000:5000"
    depends_on:
      - worker-api
    restart: unless-stopped
    networks:
      - worker_net

networks:
  worker_net:
    driver: bridge

volumes:
  worker_db_data:
"""

    # .env 파일 내용
    env_content = f"""LOCAL_SERVER_IP={server_ip}
API_TOKEN=test-token-123
DATABASE_URL=postgresql://worker:workerpass@postgres:5432/workerdb
CENTRAL_SERVER_URL=http://{server_ip}:8000
TZ=Asia/Seoul
PUID=1000
PGID=1000
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO
"""

    # 설치 스크립트 - VBScript 래퍼로 숨김 실행
    script = """@echo off
REM Check if running hidden
if not "%%1"=="HIDDEN" (
    REM Create VBScript to run hidden
    echo Set WshShell = CreateObject("WScript.Shell") > "%%TEMP%%\\run_hidden.vbs"
    echo WshShell.Run "cmd.exe /c """"""%%~f0"" HIDDEN""", 0 >> "%%TEMP%%\\run_hidden.vbs"
    cscript //nologo "%%TEMP%%\\run_hidden.vbs"
    del "%%TEMP%%\\run_hidden.vbs"
    exit
)

REM ============================================
REM Worker Manager Installation (Hidden Mode)
REM ============================================

setlocal enabledelayedexpansion

REM 작업 디렉토리 생성
set "WM_DIR=%%USERPROFILE%%\\worker-manager"
if not exist "!WM_DIR!" mkdir "!WM_DIR!"

cd /d "!WM_DIR!"

REM docker-compose.yml 생성
(
%s
) > docker-compose.yml

REM .env 파일 생성
(
%s
) > .env

REM Docker 이미지 pull 및 실행
docker-compose pull >nul 2>&1
docker-compose up -d >nul 2>&1

if !errorlevel! equ 0 (
    powershell.exe -NoProfile -WindowStyle Hidden -Command "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; [System.Windows.Forms.MessageBox]::Show('Worker Manager installed successfully!`n`nAccess Dashboard: http://%s:5000', 'Installation Complete', 'OK', 'Information')" >nul
) else (
    powershell.exe -NoProfile -WindowStyle Hidden -Command "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; [System.Windows.Forms.MessageBox]::Show('Installation failed. Check Docker Desktop.', 'Installation Error', 'OK', 'Error')" >nul
)

exit
""" % (docker_compose_yml, env_content, server_ip)

    return script

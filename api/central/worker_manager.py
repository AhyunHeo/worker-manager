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

    # 설치 스크립트
    script = f"""
REM ============================================
REM Worker Manager Installation
REM ============================================

echo.
echo ========================================
echo Installing Worker Manager...
echo ========================================
echo.

REM 작업 디렉토리 생성
set "WM_DIR=%USERPROFILE%\\worker-manager"
if not exist "!WM_DIR!" (
    echo Creating Worker Manager directory...
    mkdir "!WM_DIR!"
)

cd /d "!WM_DIR!"

REM docker-compose.yml 생성
echo Creating docker-compose.yml...
(
{docker_compose_yml}
) > docker-compose.yml

REM .env 파일 생성
echo Creating .env file...
(
{env_content}
) > .env

REM Docker 이미지 pull
echo.
echo Pulling Docker images from Docker Hub...
docker pull heoaa/worker-manager:latest
docker pull heoaa/worker-manager-dashboard:latest
docker pull postgres:15

if !errorlevel! neq 0 (
    echo WARNING: Failed to pull some images
    echo This might be due to network issues or Docker Hub rate limits
    echo Continuing with local images if available...
)

REM Docker Compose 실행
echo.
echo Starting Worker Manager services...
docker-compose up -d

if !errorlevel! equ 0 (
    echo.
    echo ========================================
    echo Worker Manager installed successfully!
    echo ========================================
    echo.
    echo Access points:
    echo   - Web Dashboard:    http://{server_ip}:5000
    echo   - API Server:       http://{server_ip}:8091
    echo   - Worker Setup:     http://{server_ip}:8091/worker/setup
    echo   - Central Setup:    http://{server_ip}:8091/central/setup
    echo.
    echo Installation directory: !WM_DIR!
    echo.
) else (
    echo.
    echo ERROR: Failed to start Worker Manager
    echo Check Docker logs: docker-compose logs
    echo.
)
"""

    return script

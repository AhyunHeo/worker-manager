"""
Simplified Worker Node Docker Runner
워커노드용 간소화된 Docker Runner
"""
import json
from models import Node
import os

# Global configuration - 환경변수에서 한 번만 로드
LOCAL_SERVER_IP = os.getenv('LOCAL_SERVER_IP', '192.168.0.88')
CENTRAL_SERVER_URL = os.getenv('CENTRAL_SERVER_URL', 'http://192.168.0.88:8000')

def generate_simple_worker_runner_wsl(node: Node) -> str:
    """WSL용 워커노드 Docker Runner 생성 (Windows에서 WSL2 사용)"""

    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}

    # Docker 이미지 태그 설정
    DOCKER_TAG = "latest"

    # 서버 설정
    server_ip = LOCAL_SERVER_IP
    worker_manager_url = f"http://{server_ip}:8090"

    if metadata.get('central_server_ip'):
        central_ip = metadata.get('central_server_ip')
    else:
        central_url = metadata.get('central_server_url') or node.central_server_url or CENTRAL_SERVER_URL
        import re
        central_ip_match = re.search(r'://([^:]+)', central_url)
        central_ip = central_ip_match.group(1) if central_ip_match else "192.168.0.88"
    
    # 자동 설치 기능이 포함된 배치 파일
    wsl_batch_script = r"""@echo off
setlocal enabledelayedexpansion

REM Auto-elevate to Administrator if needed
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ==========================================
echo    WSL Docker Runner for Worker Node
echo ==========================================
echo.
echo [+] Running with Administrator privileges
echo.

REM Check and install WSL
wsl --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] WSL is not installed. Installing WSL2...
    echo.
    echo This will install WSL2 with Ubuntu.
    echo Press Ctrl+C to cancel, or
    pause
    
    REM Install WSL2 with Ubuntu
    wsl --install -d Ubuntu
    
    echo.
    echo [IMPORTANT] WSL2 installation initiated!
    echo.
    echo Please:
    echo 1. Restart your computer after installation completes
    echo 2. Open Ubuntu from Start Menu and create a user
    echo 3. Run this script again
    echo.
    pause
    exit /b 0
)

echo [+] WSL is installed
echo.

REM Check if any Linux distribution is installed
echo Checking for Linux distribution...
wsl -l -v >nul 2>&1
if errorlevel 1 (
    goto install_ubuntu
)

REM Check if default distribution exists
for /f "tokens=*" %%i in ('wsl -l -q 2^>nul ^| findstr /v "^$"') do (
    set HAS_DISTRO=1
    goto check_docker
)

:install_ubuntu
echo [INFO] No Linux distribution found. Installing Ubuntu...
echo.

REM Create PowerShell script for GUI input
echo Creating setup dialog...
(
echo Add-Type -AssemblyName System.Windows.Forms
echo Add-Type -AssemblyName System.Drawing
echo.
echo $form = New-Object System.Windows.Forms.Form
echo $form.Text = 'Ubuntu Setup for Worker Node'
echo $form.Size = New-Object System.Drawing.Size^(400,280^)
echo $form.StartPosition = 'CenterScreen'
echo $form.FormBorderStyle = 'FixedDialog'
echo $form.MaximizeBox = $false
echo.
echo $label = New-Object System.Windows.Forms.Label
echo $label.Location = New-Object System.Drawing.Point^(10,20^)
echo $label.Size = New-Object System.Drawing.Size^(370,40^)
echo $label.Text = 'Ubuntu needs to be installed for the Worker Node. Please provide a username and password for the Ubuntu installation:'
echo $form.Controls.Add^($label^)
echo.
echo $labelUser = New-Object System.Windows.Forms.Label
echo $labelUser.Location = New-Object System.Drawing.Point^(10,70^)
echo $labelUser.Size = New-Object System.Drawing.Size^(100,20^)
echo $labelUser.Text = 'Username:'
echo $form.Controls.Add^($labelUser^)
echo.
echo $textBoxUser = New-Object System.Windows.Forms.TextBox
echo $textBoxUser.Location = New-Object System.Drawing.Point^(120,70^)
echo $textBoxUser.Size = New-Object System.Drawing.Size^(250,20^)
echo $form.Controls.Add^($textBoxUser^)
echo.
echo $labelPass = New-Object System.Windows.Forms.Label
echo $labelPass.Location = New-Object System.Drawing.Point^(10,100^)
echo $labelPass.Size = New-Object System.Drawing.Size^(100,20^)
echo $labelPass.Text = 'Password:'
echo $form.Controls.Add^($labelPass^)
echo.
echo $textBoxPass = New-Object System.Windows.Forms.TextBox
echo $textBoxPass.Location = New-Object System.Drawing.Point^(120,100^)
echo $textBoxPass.Size = New-Object System.Drawing.Size^(250,20^)
echo $textBoxPass.PasswordChar = '*'
echo $form.Controls.Add^($textBoxPass^)
echo.
echo $labelNote = New-Object System.Windows.Forms.Label
echo $labelNote.Location = New-Object System.Drawing.Point^(10,130^)
echo $labelNote.Size = New-Object System.Drawing.Size^(370,40^)
echo $labelNote.Text = 'Note: This will install Ubuntu and Docker automatically. The process may take several minutes.'
echo $labelNote.ForeColor = [System.Drawing.Color]::Gray
echo $form.Controls.Add^($labelNote^)
echo.
echo $buttonOK = New-Object System.Windows.Forms.Button
echo $buttonOK.Location = New-Object System.Drawing.Point^(120,180^)
echo $buttonOK.Size = New-Object System.Drawing.Size^(75,30^)
echo $buttonOK.Text = 'Install'
echo $buttonOK.DialogResult = [System.Windows.Forms.DialogResult]::OK
echo $form.AcceptButton = $buttonOK
echo $form.Controls.Add^($buttonOK^)
echo.
echo $buttonCancel = New-Object System.Windows.Forms.Button
echo $buttonCancel.Location = New-Object System.Drawing.Point^(205,180^)
echo $buttonCancel.Size = New-Object System.Drawing.Size^(75,30^)
echo $buttonCancel.Text = 'Cancel'
echo $buttonCancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
echo $form.CancelButton = $buttonCancel
echo $form.Controls.Add^($buttonCancel^)
echo.
echo $result = $form.ShowDialog^(^)
echo.
echo if ^($result -eq [System.Windows.Forms.DialogResult]::OK^) {
echo     $username = $textBoxUser.Text
echo     $password = $textBoxPass.Text
echo     if ^([string]::IsNullOrWhiteSpace^($username^) -or [string]::IsNullOrWhiteSpace^($password^)^) {
echo         [System.Windows.Forms.MessageBox]::Show^('Username and password are required!', 'Error'^)
echo         exit 1
echo     }
echo     Write-Host "USERNAME:$username"
echo     Write-Host "PASSWORD:$password"
echo } else {
echo     exit 1
echo }
) > "%TEMP%\wsl_setup.ps1"

REM Run PowerShell script to get credentials
for /f "tokens=2 delims=:" %%a in ('powershell -ExecutionPolicy Bypass -File "%TEMP%\wsl_setup.ps1" ^| findstr "USERNAME:"') do set WSL_USER=%%a
for /f "tokens=2 delims=:" %%a in ('powershell -ExecutionPolicy Bypass -File "%TEMP%\wsl_setup.ps1" ^| findstr "PASSWORD:"') do set WSL_PASS=%%a

if "%WSL_USER%"=="" (
    echo [INFO] Installation cancelled by user
    del "%TEMP%\wsl_setup.ps1" 2>nul
    pause
    exit /b 1
)

echo.
echo [INFO] Installing Ubuntu...
wsl --install -d Ubuntu --no-launch

REM Wait for installation
echo Waiting for Ubuntu installation to complete...
timeout /t 10 /nobreak >nul

REM Create script to set up Ubuntu user
echo Creating Ubuntu setup script...
(
echo #!/bin/bash
echo useradd -m -s /bin/bash %WSL_USER%
echo echo '%WSL_USER%:%WSL_PASS%' ^| chpasswd
echo usermod -aG sudo %WSL_USER%
echo echo '%WSL_USER% ALL=^(ALL^) NOPASSWD:ALL' ^>^> /etc/sudoers
echo.
echo # Install Docker
echo apt-get update
echo apt-get install -y curl wget
echo curl -fsSL https://get.docker.com -o get-docker.sh
echo sh get-docker.sh
echo usermod -aG docker %WSL_USER%
echo.
echo # Install docker-compose
echo apt-get install -y docker-compose-plugin
echo.
echo # Start Docker service
echo service docker start
echo.
echo echo "Setup completed"
) > "%TEMP%\ubuntu_setup.sh"

REM Run setup in Ubuntu
echo Setting up Ubuntu user and Docker...
wsl -d Ubuntu -u root bash -c "cat > /tmp/setup.sh" < "%TEMP%\ubuntu_setup.sh"
wsl -d Ubuntu -u root bash -c "chmod +x /tmp/setup.sh && /tmp/setup.sh"

REM Set default user
wsl -d Ubuntu -u root bash -c "echo '[user]' > /etc/wsl.conf"
wsl -d Ubuntu -u root bash -c "echo 'default=%WSL_USER%' >> /etc/wsl.conf"

REM Clean up temp files
del "%TEMP%\wsl_setup.ps1" 2>nul
del "%TEMP%\ubuntu_setup.sh" 2>nul

echo.
echo [SUCCESS] Ubuntu and Docker installed successfully!
echo.

REM Restart WSL
echo Restarting WSL...
wsl --shutdown
timeout /t 5 /nobreak >nul
wsl -d Ubuntu -u %WSL_USER% echo "WSL is ready"

:check_docker
echo [+] Linux distribution detected
echo.

REM Check Docker in WSL with timeout
echo Checking Docker in WSL (5 second timeout)...
echo.

REM Create a temporary file to store result
set TEMP_FILE=%TEMP%\docker_check_%RANDOM%.txt
echo checking > "%TEMP_FILE%"

REM Try Docker version with timeout
start /B cmd /C "wsl docker version >nul 2>&1 && echo success > "%TEMP_FILE%" || echo failed > "%TEMP_FILE%""

REM Wait up to 5 seconds
for /L %%i in (1,1,5) do (
    timeout /t 1 /nobreak >nul
    set /p DOCKER_STATUS=<"%TEMP_FILE%" 2>nul
    if "!DOCKER_STATUS!"=="success" goto docker_ok
    if "!DOCKER_STATUS!"=="failed" goto docker_failed
    echo Waiting for Docker response... %%i/5
)

:docker_failed
del "%TEMP_FILE%" 2>nul

echo.
echo [INFO] Docker not found. Installing Docker in WSL...
echo.

REM Auto-install Docker in WSL
wsl bash -c "sudo apt-get update -qq"
wsl bash -c "sudo apt-get install -y -qq curl wget ca-certificates gnupg lsb-release"

echo Installing Docker Engine...
wsl bash -c "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg"
wsl bash -c "echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu focal stable' | sudo tee /etc/apt/sources.list.d/docker.list"
wsl bash -c "sudo apt-get update -qq"
wsl bash -c "sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin"

REM Configure Docker
wsl bash -c "sudo usermod -aG docker $USER"
wsl bash -c "sudo systemctl enable docker 2>/dev/null || true"
wsl bash -c "sudo service docker start"

echo Waiting for Docker to start...
timeout /t 5 /nobreak >nul

REM Test Docker
wsl bash -c "sudo docker version" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker installation failed
    echo.
    echo You can manually install Docker Desktop from:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

echo [SUCCESS] Docker installed successfully!
echo.

:docker_ok
del "%TEMP_FILE%" 2>nul

echo [+] Docker is ready in WSL
echo.

""" + f"""
REM Get Worker IP (LAN IP)
set WORKER_IP={node.vpn_ip}
echo [+] Worker IP: %WORKER_IP%
echo.

REM Get WSL2 IP address
echo Getting WSL2 IP address...
for /f "tokens=*" %%i in ('wsl hostname -I 2^>nul') do set WSL_IP=%%i

REM Check if WSL_IP is empty or contains error message
if "%WSL_IP%"=="" (
    echo [ERROR] Failed to get WSL2 IP address!
    echo.
    echo This usually means:
    echo 1. No Linux distribution is installed
    echo 2. WSL2 is not running
    echo 3. Network configuration issue
    echo.
    echo Please ensure Ubuntu is installed and running.
    echo.
    pause
    exit /b 1
)

REM Trim spaces
set WSL_IP=%WSL_IP: =%

REM Validate IP format (basic check)
echo %WSL_IP% | findstr /R "^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*" >nul
if errorlevel 1 (
    echo [ERROR] Invalid WSL2 IP: %WSL_IP%
    echo.
    echo Please check your WSL2 installation.
    echo.
    pause
    exit /b 1
)

echo [+] WSL2 IP: %WSL_IP%
echo.

REM Setup port forwarding from Worker IP to WSL2
echo Setting up port forwarding from Worker IP to WSL2...
echo.

REM Remove existing port forwarding rules
echo Cleaning up existing port forwarding...
netsh interface portproxy delete v4tov4 listenaddress=%WORKER_IP% listenport=8001 >nul 2>&1
netsh interface portproxy delete v4tov4 listenaddress=%WORKER_IP% listenport=8265 >nul 2>&1
netsh interface portproxy delete v4tov4 listenaddress=%WORKER_IP% listenport=6379 >nul 2>&1
netsh interface portproxy delete v4tov4 listenaddress=%WORKER_IP% listenport=8076 >nul 2>&1
netsh interface portproxy delete v4tov4 listenaddress=%WORKER_IP% listenport=8077 >nul 2>&1
netsh interface portproxy delete v4tov4 listenaddress=%WORKER_IP% listenport=10001 >nul 2>&1

REM Add new port forwarding rules
echo Adding port forwarding rules...

REM Worker API
netsh interface portproxy add v4tov4 listenaddress=%WORKER_IP% listenport=8001 connectaddress=%WSL_IP% connectport=8001
echo [+] Worker API: %WORKER_IP%:8001 -^> WSL2:8001

REM Ray Dashboard
netsh interface portproxy add v4tov4 listenaddress=%WORKER_IP% listenport=8265 connectaddress=%WSL_IP% connectport=8265
echo [+] Ray Dashboard: %WORKER_IP%:8265 -^> WSL2:8265

REM Redis
netsh interface portproxy add v4tov4 listenaddress=%WORKER_IP% listenport=6379 connectaddress=%WSL_IP% connectport=6379
echo [+] Redis: %WORKER_IP%:6379 -^> WSL2:6379

REM Ray ports
netsh interface portproxy add v4tov4 listenaddress=%WORKER_IP% listenport=8076 connectaddress=%WSL_IP% connectport=8076
netsh interface portproxy add v4tov4 listenaddress=%WORKER_IP% listenport=8077 connectaddress=%WSL_IP% connectport=8077
echo [+] Ray GCS: %WORKER_IP%:8076-8077 -^> WSL2:8076-8077

REM Ray object manager
netsh interface portproxy add v4tov4 listenaddress=%WORKER_IP% listenport=10001 connectaddress=%WSL_IP% connectport=10001
echo [+] Ray Object Manager: %WORKER_IP%:10001 -^> WSL2:10001

REM Add port ranges for distributed training
echo Adding port ranges for distributed training...
for /L %%p in (29500,1,29510) do (
    netsh interface portproxy add v4tov4 listenaddress=%WORKER_IP% listenport=%%p connectaddress=%WSL_IP% connectport=%%p >nul 2>&1
)
echo [+] PyTorch DDP ports: %WORKER_IP%:29500-29510 -^> WSL2

for /L %%p in (11000,1,11020) do (
    netsh interface portproxy add v4tov4 listenaddress=%WORKER_IP% listenport=%%p connectaddress=%WSL_IP% connectport=%%p >nul 2>&1
)
echo [+] Ray worker ports: %WORKER_IP%:11000-11020 -^> WSL2

echo.
echo [SUCCESS] Port forwarding configured!
echo.

""" + f"""
REM Create directory
wsl mkdir -p ~/worker-{node.node_id}

REM Clean up
wsl bash -c "cd ~/worker-{node.node_id} && docker compose down 2>/dev/null || true"

REM Download docker-compose.yml (bridge mode for WSL2)
echo Downloading docker-compose.yml...
wsl bash -c "cd ~/worker-{node.node_id} && wget -O docker-compose.yml '{worker_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}'"

REM Create .env file
echo Creating .env file...
wsl bash -c "cd ~/worker-{node.node_id} && echo 'NODE_ID={node.node_id}' > .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'DESCRIPTION={metadata.get('description', 'Worker Node')}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'CENTRAL_SERVER_IP={central_ip}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'CENTRAL_SERVER_URL=http://{central_ip}:8000' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'WORKER_IP={node.vpn_ip}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'HOST_IP={node.vpn_ip}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'API_TOKEN={metadata.get('api_token', 'your-api-token')}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'REGISTRY=docker.io' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'IMAGE_NAME=heoaa/worker-node-prod' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'TAG={DOCKER_TAG}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'MEMORY_LIMIT=24g' >> .env"

REM Start Docker Compose
echo Starting Docker Compose...
wsl bash -c "cd ~/worker-{node.node_id} && docker compose up -d"

REM Check status
timeout /t 5 /nobreak
wsl bash -c "cd ~/worker-{node.node_id} && docker compose ps"

echo.
echo ==========================================
echo    SETUP COMPLETED SUCCESSFULLY!
echo ==========================================
echo.
echo Node ID: {node.node_id}
echo Worker IP: {node.vpn_ip}
echo.
echo [SUCCESS] Port forwarding is active!
echo.
echo Worker services are accessible at:
echo   - Worker API: http://{node.vpn_ip}:8001
echo   - Ray Dashboard: http://{node.vpn_ip}:8265
echo   - Redis: {node.vpn_ip}:6379
echo   - Ray GCS: {node.vpn_ip}:8076-8077
echo   - PyTorch DDP: {node.vpn_ip}:29500-29510
echo.
echo Local access from Windows:
echo   - Worker API: http://localhost:8001
echo   - Ray Dashboard: http://localhost:8265
echo.
echo Management commands:
echo   - View logs: wsl bash -c "cd ~/worker-{node.node_id} && docker compose logs -f"
echo   - Stop: wsl bash -c "cd ~/worker-{node.node_id} && docker compose down"
echo   - Restart: wsl bash -c "cd ~/worker-{node.node_id} && docker compose restart"
echo.
echo To view port forwarding rules:
echo   netsh interface portproxy show v4tov4
echo.
echo To remove port forwarding (when stopping):
echo   Run this script again to clean up old rules
echo.
pause
"""
    
    return wsl_batch_script


def generate_simple_worker_runner(node: Node) -> str:
    """Windows용 워커노드 Docker Runner 생성"""
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    # Docker 이미지 태그 설정 (한 곳에서 관리)
    DOCKER_TAG = "latest"  # v1.2, v1.3 등으로 변경 가능
    
    # API 서버 주소 (실제 호스트)
    # Worker Manager 서버 주소 - 호스트의 실제 IP 사용
    server_ip = LOCAL_SERVER_IP
    worker_manager_url = f"http://{server_ip}:8090"
    # 중앙서버 설정
    # metadata에 central_server_ip가 있으면 사용, 없으면 URL에서 추출
    if metadata.get('central_server_ip'):
        central_ip = metadata.get('central_server_ip')
        central_url = f"http://{central_ip}:8000"
    else:
        # 기존 방식: URL에서 IP 추출
        central_url = metadata.get('central_server_url') or node.central_server_url or os.getenv("CENTRAL_SERVER_URL", "http://192.168.0.88:8000")
        import re
        central_ip_match = re.search(r'://([^:]+)', central_url)
        central_ip = central_ip_match.group(1) if central_ip_match else "192.168.0.88"
    
    # Worker IP (LAN IP stored in vpn_ip field)
    worker_ip = node.vpn_ip

    # 간단한 배치 파일
    batch_script = f"""@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
title Worker Node Docker Runner - {node.node_id}
color 0A

echo ==========================================
echo    Worker Node Docker Runner
echo    Node ID: {node.node_id}
echo    Worker IP: {worker_ip}
echo ==========================================
echo.

:: Check Docker installation
echo Checking Docker installation...
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed!
    echo.
    echo Please install Docker Desktop from:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

:: Check Docker service
echo Checking Docker service...
docker version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running!
    echo.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

echo [+] Docker is ready
echo.

:: Create work directory
set WORK_DIR=%USERPROFILE%\\intown-worker
echo Creating work directory: %WORK_DIR%
if not exist "%WORK_DIR%" mkdir "%WORK_DIR%"
cd /d "%WORK_DIR%"

:: Create subdirectories
if not exist "cache" mkdir cache
if not exist "cache\\torch" mkdir cache\\torch
if not exist "cache\\huggingface" mkdir cache\\huggingface
if not exist "data" mkdir data
if not exist "models" mkdir models

echo [+] Work directory ready: %CD%
echo.

:: Detect OS type and download appropriate docker-compose.yml
echo Detecting OS type for appropriate network mode...

:: Windows doesn't support host network mode, use bridge mode with port mapping
echo [INFO] Windows detected - using bridge mode with port mapping
echo Downloading docker-compose.yml from Worker Manager...
echo URL: {worker_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}
echo.

:: Try to download using curl (bridge mode for Windows)
curl -o docker-compose.yml "{worker_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}" 2>nul
if errorlevel 1 (
    echo [WARNING] curl failed, trying PowerShell...
    :: Fallback to PowerShell if curl is not available
    powershell -Command "Invoke-WebRequest -Uri '{worker_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}' -OutFile 'docker-compose.yml' -UseBasicParsing" 2>nul
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to download docker-compose.yml
        echo.
        echo Please ensure:
        echo   1. Worker Manager API is running at {worker_manager_url}
        echo   2. Node {node.node_id} is registered in the system
        echo.
        echo You can manually download from:
        echo   {worker_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}
        echo.
        pause
        exit /b 1
    )
)

echo [+] Successfully downloaded latest docker-compose.yml for node {node.node_id}
echo [INFO] Using bridge mode (Windows limitation - host mode not supported)
echo.

:: Create .env file
echo Creating .env file...
(
echo # Auto-generated environment file
echo # Node: {node.node_id}
echo.
echo # Node Configuration
echo NODE_ID={node.node_id}
echo DESCRIPTION={metadata.get('description', 'Worker Node')}
echo CENTRAL_SERVER_IP={central_ip}
echo CENTRAL_SERVER_URL=http://{central_ip}:8000
echo HOST_IP={worker_ip}
echo WORKER_IP={worker_ip}
echo.
echo # API Token for authentication
echo API_TOKEN={metadata.get('api_token', 'your-api-token')}
echo.
echo # Docker Registry ^(optional^)
echo REGISTRY=docker.io
echo IMAGE_NAME=heoaa/worker-node-prod
echo TAG={DOCKER_TAG}
echo.
echo # Resource Limits
echo MEMORY_LIMIT=24g
echo.
echo # System
echo PYTHONUNBUFFERED=1
) > .env

echo [+] Configuration files ready
echo.

:: Clean up existing containers
echo Cleaning up existing containers...
docker compose down 2>nul
echo.

:: Login to Docker registry if needed
echo Checking Docker registry...
docker pull heoaa/worker-node-prod:{DOCKER_TAG} 2>nul
if errorlevel 1 (
    echo [WARNING] Cannot pull image. Make sure you have access to the registry.
    echo You may need to run: docker login
)
echo.

:: Start containers
echo Starting containers...
set NODE_ID={node.node_id}
set CENTRAL_SERVER_IP={central_ip}
set HOST_IP={worker_ip}
set WORKER_IP={worker_ip}
set DESCRIPTION={metadata.get('description', 'Worker Node')}
set IMAGE_NAME=heoaa/worker-node-prod
set TAG={DOCKER_TAG}

echo Running docker compose up -d with environment variables...
docker compose up -d

:: Check result
timeout /t 5 /nobreak >nul
echo.

:: Check if containers are running
docker compose ps

echo.
echo ==========================================
echo    Docker Runner Completed
echo ==========================================
echo.
echo [+] Using latest docker-compose.yml from Worker Manager (bridge mode for Windows)
echo [+] Node ID: {node.node_id}
echo [+] Worker IP: {worker_ip}
echo.
echo Services should be available at:
echo   - Worker API: http://{worker_ip}:8001
echo   - Ray Dashboard: http://{worker_ip}:8265
echo   - Redis: {worker_ip}:6379
echo   - Central Server: http://{central_ip}:8000
echo.
echo Useful commands:
echo   - View logs:    docker compose logs -f
echo   - Stop:         docker compose down
echo   - Restart:      docker compose restart
echo   - Status:       docker compose ps
echo   - Update:       Re-run this script to get latest config
echo.
pause
"""
    
    return batch_script
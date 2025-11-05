"""
Central Server Docker Runner Generator
중앙서버 Docker 실행을 위한 배치 파일 생성 모듈
"""

import json
from models import Node
import base64
import os
from .worker_manager import generate_worker_manager_installer

# Global configuration - 환경변수에서 한 번만 로드
LOCAL_SERVER_IP = os.getenv('LOCAL_SERVER_IP', '192.168.0.88')
CENTRAL_SERVER_URL = os.getenv('CENTRAL_SERVER_URL', 'http://192.168.0.88:8000')

def generate_central_docker_runner(node: Node) -> str:
    """중앙서버 전용 Docker Runner 생성 (GUI 프로그레스바 버전)"""
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    # 중앙서버 IP (사용자 지정 또는 기본값)
    local_ip = metadata.get('server_ip', '192.168.0.88')
    
    # JWT 키 생성 (보안)
    jwt_key = metadata.get('jwt_secret_key', '2Yw1k3J8v3Qk1n2p5l6s7d3f9g0h1j2k3l4m5n6o7p3q9r0s1t2u3v4w5x6y7z3A9')
    
    # PowerShell 스크립트
    ps_script = f'''
# Error logging
$ErrorActionPreference = "Continue"
$LogFile = "$env:USERPROFILE\\Downloads\\central-ps-error.log"
Start-Transcript -Path $LogFile -Append

try {{
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
}} catch {{
    Write-Host "Error loading assemblies: $_"
    Stop-Transcript
    [System.Console]::WriteLine("Error: $_")
    Read-Host "Press Enter to exit"
    exit 1
}}

# 프로그레스 폼 생성
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Central Server Docker Runner'
$form.Size = New-Object System.Drawing.Size(500, 250)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

# 타이틀 라벨
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = 'Central Server Docker Runner'
$titleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 14, [System.Drawing.FontStyle]::Bold)
$titleLabel.Location = New-Object System.Drawing.Point(20, 20)
$titleLabel.Size = New-Object System.Drawing.Size(460, 30)
$titleLabel.TextAlign = 'MiddleCenter'
$form.Controls.Add($titleLabel)

# 서버 정보 라벨
$infoLabel = New-Object System.Windows.Forms.Label
$infoLabel.Text = 'Server IP: {local_ip}'
$infoLabel.Font = New-Object System.Drawing.Font('Segoe UI', 10)
$infoLabel.Location = New-Object System.Drawing.Point(20, 55)
$infoLabel.Size = New-Object System.Drawing.Size(460, 20)
$infoLabel.TextAlign = 'MiddleCenter'
$form.Controls.Add($infoLabel)

# 상태 라벨
$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = 'Initializing...'
$statusLabel.Font = New-Object System.Drawing.Font('Segoe UI', 10)
$statusLabel.Location = New-Object System.Drawing.Point(20, 90)
$statusLabel.Size = New-Object System.Drawing.Size(460, 25)
$statusLabel.TextAlign = 'MiddleCenter'
$form.Controls.Add($statusLabel)

# 프로그레스바
$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(20, 120)
$progressBar.Size = New-Object System.Drawing.Size(460, 30)
$progressBar.Style = 'Continuous'
$progressBar.Maximum = 100
$form.Controls.Add($progressBar)

# 닫기 버튼
$closeButton = New-Object System.Windows.Forms.Button
$closeButton.Text = 'Close'
$closeButton.Location = New-Object System.Drawing.Point(200, 165)
$closeButton.Size = New-Object System.Drawing.Size(100, 30)
$closeButton.Enabled = $false
$closeButton.Add_Click({{
    $form.Close()
    [System.Windows.Forms.Application]::Exit()
}})
$form.Controls.Add($closeButton)

$form.Show()
[System.Windows.Forms.Application]::DoEvents()

# 작업 디렉토리
$workDir = "$env:USERPROFILE\\intown-central"

try {{
    # Docker Desktop 확인
    $statusLabel.Text = 'Checking Docker Desktop...'
    $progressBar.Value = 10
    [System.Windows.Forms.Application]::DoEvents()
    
    $dockerPath = @(
        'C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe',
        "$env:ProgramFiles\\Docker\\Docker\\Docker Desktop.exe"
    )
    
    $dockerInstalled = $false
    foreach ($path in $dockerPath) {{
        if (Test-Path $path) {{
            $dockerInstalled = $true
            break
        }}
    }}
    
    if (-not $dockerInstalled) {{
        $statusLabel.Text = 'Docker Desktop not installed!'
        Write-Host "ERROR: Docker Desktop is not installed!"
        Write-Host "Checked paths:"
        foreach ($path in $dockerPath) {{
            Write-Host "  - $path : $(Test-Path $path)"
        }}
        $result = [System.Windows.Forms.MessageBox]::Show(
            "Docker Desktop is not installed.`n`nWould you like to download it?",
            'Docker Required',
            'YesNo',
            'Warning'
        )
        Write-Host "User response: $result"
        if ($result -eq 'Yes') {{
            Start-Process 'https://www.docker.com/products/docker-desktop/'
        }}
        $closeButton.Enabled = $true
        # Wait for close button click
        while ($form.Visible) {{
            [System.Windows.Forms.Application]::DoEvents()
            Start-Sleep -Milliseconds 100
        }}
        Write-Host "Exiting: Docker Desktop not installed"
        Stop-Transcript
        return
    }}
    
    # Docker 시작
    $statusLabel.Text = 'Starting Docker Desktop...'
    $progressBar.Value = 30
    [System.Windows.Forms.Application]::DoEvents()
    
    docker version 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {{
        foreach ($path in $dockerPath) {{
            if (Test-Path $path) {{
                Start-Process $path
                break
            }}
        }}
        
        # Docker 시작 대기
        $maxWait = 60
        $waited = 0
        while ($waited -lt $maxWait) {{
            Start-Sleep -Seconds 5
            $waited += 5
            $progressBar.Value = 30 + ([int](($waited / $maxWait) * 30))
            [System.Windows.Forms.Application]::DoEvents()
            
            docker version 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {{
                break
            }}
        }}
        
        if ($LASTEXITCODE -ne 0) {{
            Write-Host "ERROR: Docker Desktop failed to start after waiting $maxWait seconds"
            Write-Host "Last exit code: $LASTEXITCODE"
            throw "Docker Desktop failed to start"
        }}
    }}

    Write-Host "SUCCESS: Docker is running"

    # 관리자 권한 확인
    $statusLabel.Text = 'Checking administrator privileges...'
    $progressBar.Value = 50
    [System.Windows.Forms.Application]::DoEvents()

    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    Write-Host "Administrator check: $isAdmin"

    if (-NOT $isAdmin) {{
        Write-Host "ERROR: Not running with administrator privileges"
        throw "관리자 권한이 필요합니다. 스크립트를 관리자 권한으로 실행해주세요."
    }}

    Write-Host "SUCCESS: Running with administrator privileges"

    # WSL IP 가져오기
    $statusLabel.Text = 'Detecting WSL IP address...'
    $progressBar.Value = 52
    [System.Windows.Forms.Application]::DoEvents()

    Write-Host "Detecting WSL IP address..."
    try {{
        $wslOutput = wsl hostname -I 2>&1
        Write-Host "WSL command output: $wslOutput"
        Write-Host "WSL exit code: $LASTEXITCODE"

        if ($LASTEXITCODE -ne 0) {{
            Write-Host "ERROR: WSL command failed with exit code $LASTEXITCODE"
            throw "WSL not running or not installed"
        }}
        $wslIP = $wslOutput.Trim().Split()[0]
        Write-Host "Detected WSL IP: $wslIP"

        if (-not $wslIP -or $wslIP -eq "") {{
            Write-Host "ERROR: WSL IP is empty or null"
            throw "Failed to detect WSL IP address"
        }}
    }} catch {{
        $statusLabel.Text = "Error: WSL IP detection failed"
        Write-Host "ERROR: WSL IP detection failed: $_"
        throw "WSL이 실행되고 있지 않거나 설치되지 않았습니다. WSL을 실행한 후 다시 시도해주세요.`n`n오류: $_"
    }}

    Write-Host "SUCCESS: WSL IP detected: $wslIP"

    # 주요 포트 목록 (중앙서버 + Worker Manager)
    $ports = @(3000, 8000, 5002, 5000, 8091, 5432, 27017)

    # 기존 포트포워딩 규칙 삭제 (Docker 시작 전에 먼저 정리)
    $statusLabel.Text = 'Removing old port forwarding rules...'
    $progressBar.Value = 52
    [System.Windows.Forms.Application]::DoEvents()

    Write-Host "Removing old port forwarding rules..."
    foreach ($port in $ports) {{
        netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port 2>$null | Out-Null
        netsh interface portproxy delete v4tov4 listenaddress={local_ip} listenport=$port 2>$null | Out-Null
    }}
    Write-Host "Old port forwarding rules removed"

    # Wait for ports to be released
    Write-Host "Waiting for ports to be released..."
    Start-Sleep -Seconds 2

    # 작업 디렉토리 생성
    $statusLabel.Text = 'Preparing directories...'
    $progressBar.Value = 60
    [System.Windows.Forms.Application]::DoEvents()
    
    if (-not (Test-Path $workDir)) {{
        New-Item -ItemType Directory -Path $workDir -Force | Out-Null
    }}
    Set-Location $workDir
    
    @('config', 'session_models', 'uploads', 'app\\data\\uploads') | ForEach-Object {{
        if (-not (Test-Path $_)) {{
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
        }}
    }}
    
    # Docker Compose 파일 생성
    $statusLabel.Text = 'Creating configuration...'
    $progressBar.Value = 70
    [System.Windows.Forms.Application]::DoEvents()
    
    $composeContent = @'
# Central Server Protected Docker Compose
services:
  api:
    image: heoaa/central-server:latest
    container_name: central-server-api-prod
    ports:
      - "0.0.0.0:{metadata.get('api_port', 8000)}:8000"
    volumes:
      - ./config:/app/config:ro
      - ./session_models:/app/session_models
      - ./uploads:/app/uploads
      - ./app/data/uploads:/app/data/uploads
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/ai_db
      - MONGODB_URL=mongodb://mongo:27017/ai_logs
      - JWT_SECRET_KEY={jwt_key}
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRE_MINUTES=240
      - PYTHONUNBUFFERED=1
      - WS_MESSAGE_QUEUE_SIZE=100
    depends_on:
      - db
      - redis
      - mongo
    restart: unless-stopped

  fl-api:
    image: heoaa/central-server-fl:latest
    container_name: fl-server-api-prod
    ports:
      - "0.0.0.0:{metadata.get('fl_port', 5002)}:5002"
    volumes:
      - ./config:/app/config:ro
      - ./session_models:/app/session_models
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/ai_db
      - MONGODB_URL=mongodb://mongo:27017/ai_logs
      - JWT_SECRET_KEY={jwt_key}
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRE_MINUTES=240
      - PYTHONUNBUFFERED=1
      - WS_MESSAGE_QUEUE_SIZE=100
      - FL_SERVER_PORT=5002
    depends_on:
      - db
      - redis
      - mongo
    restart: unless-stopped

  frontend:
    image: heoaa/central-frontend:latest
    container_name: central-server-frontend
    ports:
      - "0.0.0.0:{metadata.get('frontend_port', 3000)}:3000"
    environment:
      - API_URL_INTERNAL=http://api:8000
      - FL_API_URL_INTERNAL=http://fl-api:5002
      - NEXT_PUBLIC_API_URL=http://{local_ip}:{metadata.get('api_port', 8000)}
      - NEXT_PUBLIC_WS_URL=ws://{local_ip}:{metadata.get('api_port', 8000)}
      - NEXT_PUBLIC_FL_API_URL=http://{local_ip}:{metadata.get('fl_port', 5002)}
      - NEXT_PUBLIC_FL_WS_URL=ws://{local_ip}:{metadata.get('fl_port', 5002)}
      - NEXT_PUBLIC_WORKER_MANAGER_IP={metadata.get('worker_manager_ip', LOCAL_SERVER_IP)}
    depends_on:
      - api
      - fl-api
    restart: unless-stopped

  db:
    image: postgres:16
    container_name: central-server-db-protected
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: ai_db
      TZ: Asia/Seoul
      PGTZ: Asia/Seoul
    ports:
      - "0.0.0.0:{metadata.get('db_port', 5432)}:5432"
    volumes:
      - db_data_protected:/var/lib/postgresql/data
    restart: unless-stopped

  mongo:
    image: mongo:7
    container_name: central-server-mongo-protected
    environment:
      TZ: Asia/Seoul
    ports:
      - "0.0.0.0:{metadata.get('mongo_port', 27017)}:27017"
    volumes:
      - mongo_data_protected:/data/db
    restart: unless-stopped

  redis:
    image: redis:7
    container_name: central-server-redis-protected
    restart: unless-stopped

volumes:
  db_data_protected:
  mongo_data_protected:
'@
    
    Set-Content -Path 'docker-compose.yml' -Value $composeContent
    Write-Host "SUCCESS: docker-compose.yml created"

    # .env 파일 생성
    $envContent = @"
# Auto-generated environment file
# Node: {node.node_id}

# Host Configuration
HOST_IP={local_ip}
SERVER_IP={local_ip}

# Port Configuration
FRONTEND_PORT={metadata.get('frontend_port', 3000)}
API_PORT={metadata.get('api_port', 8000)}
FL_PORT={metadata.get('fl_port', 5002)}
DB_PORT={metadata.get('db_port', 5432)}
MONGO_PORT={metadata.get('mongo_port', 27017)}

# Worker Manager Configuration
WORKER_MANAGER_IP={metadata.get('worker_manager_ip', LOCAL_SERVER_IP)}

# Security
JWT_SECRET_KEY={jwt_key}

# System
PYTHONUNBUFFERED=1
WS_MESSAGE_QUEUE_SIZE=100
"@

    Set-Content -Path '.env' -Value $envContent
    Write-Host "SUCCESS: .env file created"

    # Docker 이미지 Pull
    $statusLabel.Text = 'Downloading Docker images...'
    $progressBar.Value = 80
    [System.Windows.Forms.Application]::DoEvents()

    Write-Host "Pulling Docker images..."
    $pullOutput = docker compose pull 2>&1
    Write-Host "Docker pull output: $pullOutput"
    Write-Host "Docker pull exit code: $LASTEXITCODE"

    # 컨테이너 시작
    $statusLabel.Text = 'Starting central server...'
    $progressBar.Value = 90
    [System.Windows.Forms.Application]::DoEvents()

    Write-Host "Stopping ALL existing containers with 'central' in name..."
    $existingContainers = docker ps -a --filter "name=central" --format "{{{{.Names}}}}" 2>&1
    Write-Host "Existing containers: $existingContainers"

    if ($existingContainers) {{
        Write-Host "Force removing existing central containers..."
        docker ps -a --filter "name=central" --format "{{{{.Names}}}}" | ForEach-Object {{
            Write-Host "  Removing container: $_"
            docker rm -f $_ 2>&1 | Out-Null
        }}
    }}

    # Wait for ports to be released
    Write-Host "Waiting for ports to be released..."
    Start-Sleep -Seconds 3

    Write-Host "Stopping containers via docker compose..."
    $downOutput = docker compose down -v 2>&1
    Write-Host "Docker down output: $downOutput"

    Write-Host "Starting containers..."
    $upOutput = docker compose up -d 2>&1
    $upExitCode = $LASTEXITCODE
    Write-Host "Docker up output: $upOutput"
    Write-Host "Docker up exit code: $upExitCode"

    if ($upExitCode -ne 0) {{
        Write-Host "ERROR: Docker compose up failed with exit code $upExitCode"
        Write-Host "Checking which containers are running..."
        $runningContainers = docker ps --filter "name=central" --format "table {{{{.Names}}}}\t{{{{.Status}}}}" 2>&1
        Write-Host "Running containers: $runningContainers"
        throw "Docker 컨테이너 시작에 실패했습니다. 로그를 확인하세요: $LogFile"
    }}

    Start-Sleep -Seconds 5

    # 실제로 컨테이너가 실행 중인지 확인
    Write-Host "Verifying containers are running..."
    $runningCount = (docker ps --filter "name=central" --format "{{{{.Names}}}}" | Measure-Object -Line).Lines
    Write-Host "Number of running central containers: $runningCount"

    if ($runningCount -lt 5) {{
        Write-Host "ERROR: Expected at least 5 containers, but only $runningCount are running"
        $containerStatus = docker ps -a --filter "name=central" --format "table {{{{.Names}}}}\t{{{{.Status}}}}" 2>&1
        Write-Host "Container status: $containerStatus"
        throw "일부 컨테이너가 시작되지 않았습니다. 컨테이너 수: $runningCount/6"
    }}

    # 이제 Docker 컨테이너가 시작되었으니 포트포워딩과 방화벽 규칙 추가
    $statusLabel.Text = 'Configuring network rules...'
    $progressBar.Value = 95
    [System.Windows.Forms.Application]::DoEvents()

    # 포트포워딩 규칙 추가
    Write-Host "Adding port forwarding rules (WSL IP: $wslIP)..."
    $portForwardSuccess = 0
    foreach ($port in $ports) {{
        Write-Host "  Adding port forwarding for port $port..."
        $result = netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=$port connectaddress=$wslIP connectport=$port 2>&1
        if ($LASTEXITCODE -eq 0) {{
            $portForwardSuccess++
            Write-Host "    SUCCESS: Port $port forwarded"
        }} else {{
            Write-Host "    WARNING: Port $port forwarding failed - Exit code $LASTEXITCODE - $result"
        }}
    }}
    Write-Host "Port forwarding: $portForwardSuccess/$($ports.Count) successful"

    # 방화벽 규칙 추가
    Write-Host "Adding firewall rules..."
    $firewallSuccess = 0
    foreach ($port in $ports) {{
        $ruleName = "Central-Server-Port-$port"
        Write-Host "  Adding firewall rule for port $port..."

        # 기존 규칙 삭제
        netsh advfirewall firewall delete rule name="$ruleName" 2>$null | Out-Null

        # 새 규칙 추가
        $result = netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=$port 2>&1
        if ($LASTEXITCODE -eq 0) {{
            $firewallSuccess++
            Write-Host "    SUCCESS: Firewall rule for port $port added"
        }} else {{
            Write-Host "    WARNING: Firewall rule for port $port failed - Exit code $LASTEXITCODE - $result"
        }}
    }}
    Write-Host "Firewall rules: $firewallSuccess/$($ports.Count) successful"

    $progressBar.Value = 100
    $statusLabel.Text = 'Central server started successfully!'

    Write-Host "SUCCESS: Central server started successfully! ($runningCount containers running)"
    Write-Host "========================================="
    Write-Host "Access URLs:"
    Write-Host "- Frontend: http://{local_ip}:{metadata.get('frontend_port', 3000)}"
    Write-Host "- API: http://{local_ip}:{metadata.get('api_port', 8000)}"
    Write-Host "- FL Server: http://{local_ip}:{metadata.get('fl_port', 5002)}"
    Write-Host "Network Configuration:"
    Write-Host "- WSL IP: $wslIP"
    Write-Host "- Port Forwarding: $portForwardSuccess/$($ports.Count) ports"
    Write-Host "- Firewall Rules: $firewallSuccess/$($ports.Count) rules"
    Write-Host "========================================="

    [System.Windows.Forms.MessageBox]::Show(
        "🎉 Central Server Started Successfully!`n`n" +
        "📡 Access URLs:`n" +
        "- Frontend: http://{local_ip}:{metadata.get('frontend_port', 3000)}`n" +
        "- API: http://{local_ip}:{metadata.get('api_port', 8000)}`n" +
        "- FL Server: http://{local_ip}:{metadata.get('fl_port', 5002)}`n`n" +
        "🔧 Network Configuration:`n" +
        "- WSL IP: $wslIP`n" +
        "- Port Forwarding: $portForwardSuccess/$($ports.Count) ports configured`n" +
        "- Firewall Rules: $firewallSuccess/$($ports.Count) rules added`n`n" +
        "✅ Configured Ports: 3000, 8000, 5002, 5000, 8091, 5432, 27017",
        'Success',
        'OK',
        'Information'
    )

}} catch {{
    $statusLabel.Text = "Error: $_"
    Write-Host "========================================="
    Write-Host "ERROR: Installation failed!"
    Write-Host "Error message: $_"
    Write-Host "Error type: $($_.Exception.GetType().FullName)"
    Write-Host "Stack trace: $($_.ScriptStackTrace)"
    Write-Host "========================================="

    [System.Windows.Forms.MessageBox]::Show(
        "An error occurred:`n`n$_`n`nCheck log: $LogFile",
        'Error',
        'OK',
        'Error'
    )
}} finally {{
    $closeButton.Enabled = $true
    Write-Host "Cleaning up..."
}}

# Wait for form to close
while ($form.Visible) {{
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 100
}}

Stop-Transcript
Write-Host "Installation completed. Log saved to: $LogFile"
'''

    # PowerShell 스크립트를 Base64로 인코딩 - certutil은 UTF-8 사용
    ps_bytes = ps_script.encode('utf-8')
    ps_base64 = base64.b64encode(ps_bytes).decode('ascii')

    # Base64를 64자씩 나눔 (파일로 저장하기 위해)
    b64_lines = []
    for i in range(0, len(ps_base64), 64):
        b64_lines.append(ps_base64[i:i+64])

    # echo 명령으로 변환 (한 번에 실행하도록)
    b64_echo_lines = '\n'.join(f'echo {line}' for line in b64_lines)

    # BAT 파일 - 워커노드 스타일 (간단하고 빠름)
    batch_script = f'''@echo off
REM Minimize the console window
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~f0" %* && exit

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Create error log file immediately
set "ERROR_LOG=%USERPROFILE%\\Downloads\\central-bat-error.log"
echo [%DATE% %TIME%] Starting Central Server Docker Runner > "%ERROR_LOG%"

REM Create temporary files
set "TEMP_PS1=%TEMP%\\central-docker-runner-%RANDOM%.ps1"
set "B64_FILE=%TEMP%\\ps-script-%RANDOM%.b64"

REM Write Base64 data to file (certutil format) - Fast method
echo [%DATE% %TIME%] Creating Base64 file... >> "%ERROR_LOG%"
(
echo -----BEGIN CERTIFICATE-----
{b64_echo_lines}
echo -----END CERTIFICATE-----
) > "%B64_FILE%"

if not exist "%B64_FILE%" (
    echo [%DATE% %TIME%] ERROR: Failed to create Base64 file >> "%ERROR_LOG%"
    powershell.exe -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Failed to create Base64 file.`n`nCheck log: %ERROR_LOG%', 'Error', 'OK', 'Error')" 2>> "%ERROR_LOG%"
    pause
    exit /b 1
)

REM Decode Base64 file to PowerShell script using certutil (faster and more reliable)
echo [%DATE% %TIME%] Decoding PowerShell script... >> "%ERROR_LOG%"
certutil -decode "%B64_FILE%" "%TEMP_PS1%" >nul 2>&1

REM Cleanup Base64 file
del "%B64_FILE%" 2>nul

if not exist "%TEMP_PS1%" (
    echo [%DATE% %TIME%] ERROR: Failed to create PowerShell script >> "%ERROR_LOG%"
    powershell.exe -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Failed to create PowerShell script.`n`nCheck log: %ERROR_LOG%', 'Error', 'OK', 'Error')" 2>> "%ERROR_LOG%"
    pause
    exit /b 1
)

echo [%DATE% %TIME%] PowerShell script created successfully >> "%ERROR_LOG%"

REM Check for administrator privileges
echo [%DATE% %TIME%] Checking administrator privileges... >> "%ERROR_LOG%"
net session >nul 2>&1

if %errorLevel% == 0 (
    echo [%DATE% %TIME%] Running with admin privileges >> "%ERROR_LOG%"
    REM Already running as admin - execute PowerShell (hidden console, GUI only)
    powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%TEMP_PS1%" 2>> "%ERROR_LOG%"
    set "PS_EXIT=!errorLevel!"

    echo [%DATE% %TIME%] PowerShell exited with code: !PS_EXIT! >> "%ERROR_LOG%"

    REM Cleanup
    del "%TEMP_PS1%" 2>nul

    if !PS_EXIT! neq 0 (
        powershell.exe -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Installation failed with exit code !PS_EXIT!`n`nCheck logs:`n- %ERROR_LOG%`n- %USERPROFILE%\\Downloads\\central-ps-error.log', 'Error', 'OK', 'Error')"
        pause
    )
) else (
    echo [%DATE% %TIME%] Requesting admin privileges... >> "%ERROR_LOG%"
    REM Request admin privileges (hidden console, GUI only)
    powershell.exe -NoProfile -Command "Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','%TEMP_PS1%' -Verb RunAs" 2>> "%ERROR_LOG%"

    REM Cleanup after a delay
    timeout /t 5 >nul
    del "%TEMP_PS1%" 2>nul

    echo [%DATE% %TIME%] Admin request sent, waiting for completion... >> "%ERROR_LOG%"
)

echo [%DATE% %TIME%] Script completed >> "%ERROR_LOG%"
exit /b
'''

    return batch_script
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
        $result = [System.Windows.Forms.MessageBox]::Show(
            "Docker Desktop is not installed.`n`nWould you like to download it?",
            'Docker Required',
            'YesNo',
            'Warning'
        )
        if ($result -eq 'Yes') {{
            Start-Process 'https://www.docker.com/products/docker-desktop/'
        }}
        $closeButton.Enabled = $true
        # Wait for close button click
        while ($form.Visible) {{
            [System.Windows.Forms.Application]::DoEvents()
            Start-Sleep -Milliseconds 100
        }}
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
            throw "Docker Desktop failed to start"
        }}
    }}

    # 관리자 권한 확인
    $statusLabel.Text = 'Checking administrator privileges...'
    $progressBar.Value = 50
    [System.Windows.Forms.Application]::DoEvents()

    if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {{
        throw "관리자 권한이 필요합니다. 스크립트를 관리자 권한으로 실행해주세요."
    }}

    # WSL IP 가져오기
    $statusLabel.Text = 'Detecting WSL IP address...'
    $progressBar.Value = 52
    [System.Windows.Forms.Application]::DoEvents()

    try {{
        $wslOutput = wsl hostname -I 2>&1
        if ($LASTEXITCODE -ne 0) {{
            throw "WSL not running or not installed"
        }}
        $wslIP = $wslOutput.Trim().Split()[0]
        if (-not $wslIP -or $wslIP -eq "") {{
            throw "Failed to detect WSL IP address"
        }}
    }} catch {{
        $statusLabel.Text = "Error: WSL IP detection failed"
        throw "WSL이 실행되고 있지 않거나 설치되지 않았습니다. WSL을 실행한 후 다시 시도해주세요.`n`n오류: $_"
    }}

    # 주요 포트 목록 (중앙서버 + Worker Manager)
    $ports = @(3000, 8000, 5002, 5000, 8091, 5432, 27017)

    # 기존 포트포워딩 규칙 삭제
    $statusLabel.Text = 'Removing old port forwarding rules...'
    $progressBar.Value = 54
    [System.Windows.Forms.Application]::DoEvents()

    foreach ($port in $ports) {{
        netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port 2>$null | Out-Null
        netsh interface portproxy delete v4tov4 listenaddress={local_ip} listenport=$port 2>$null | Out-Null
    }}

    # 새로운 포트포워딩 규칙 추가
    $statusLabel.Text = 'Adding port forwarding rules...'
    $progressBar.Value = 55
    [System.Windows.Forms.Application]::DoEvents()

    $portForwardSuccess = 0
    foreach ($port in $ports) {{
        $result = netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=$port connectaddress=$wslIP connectport=$port 2>&1
        if ($LASTEXITCODE -eq 0) {{
            $portForwardSuccess++
        }}
    }}

    if ($portForwardSuccess -eq 0) {{
        throw "포트포워딩 규칙 추가에 실패했습니다. 관리자 권한으로 실행되고 있는지 확인하세요."
    }}

    # 방화벽 규칙 추가 (인바운드)
    $statusLabel.Text = 'Configuring firewall rules...'
    $progressBar.Value = 57
    [System.Windows.Forms.Application]::DoEvents()

    $firewallSuccess = 0
    foreach ($port in $ports) {{
        $ruleName = "Central-Server-Port-$port"

        # 기존 규칙 삭제
        netsh advfirewall firewall delete rule name="$ruleName" 2>$null | Out-Null

        # 새 규칙 추가
        $result = netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=$port 2>&1
        if ($LASTEXITCODE -eq 0) {{
            $firewallSuccess++
        }}
    }}

    if ($firewallSuccess -eq 0) {{
        throw "방화벽 규칙 추가에 실패했습니다. 관리자 권한으로 실행되고 있는지 확인하세요."
    }}

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
    
    # Docker 이미지 Pull
    $statusLabel.Text = 'Downloading Docker images...'
    $progressBar.Value = 80
    [System.Windows.Forms.Application]::DoEvents()
    
    docker compose pull 2>&1 | Out-Null
    
    # 컨테이너 시작
    $statusLabel.Text = 'Starting central server...'
    $progressBar.Value = 90
    [System.Windows.Forms.Application]::DoEvents()
    
    docker compose down 2>&1 | Out-Null
    docker compose up -d 2>&1 | Out-Null

    Start-Sleep -Seconds 3

    $progressBar.Value = 100
    $statusLabel.Text = 'Central server started successfully!'

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
    [System.Windows.Forms.MessageBox]::Show(
        "An error occurred:`n`n$_`n`nCheck log: $LogFile",
        'Error',
        'OK',
        'Error'
    )
    Write-Host "Error in main try block: $_"
}} finally {{
    $closeButton.Enabled = $true
}}

# Wait for form to close
while ($form.Visible) {{
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 100
}}

Stop-Transcript
Write-Host "Installation completed. Log saved to: $LogFile"
'''

    # Base64 인코딩 - UTF-8 사용 (certutil 호환성 향상)
    ps_bytes = ps_script.encode('utf-8')
    ps_base64 = base64.b64encode(ps_bytes).decode('ascii')

    # Base64를 64자씩 나눔 (certutil 표준 형식)
    b64_lines = []
    for i in range(0, len(ps_base64), 64):
        b64_lines.append(ps_base64[i:i+64])

    # Base64 라인들을 echo 명령으로 변환
    b64_echo_lines = '\n'.join(f'echo {line}' for line in b64_lines)

    # BAT 파일 - certutil을 사용한 Base64 디코딩
    batch_script = f'''@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Check if running hidden
if not "%1"=="HIDDEN" (
    REM Create VBScript to run hidden
    echo Set WshShell = CreateObject("WScript.Shell") > "%TEMP%\\run_hidden.vbs"
    echo WshShell.Run "cmd.exe /c """"%~f0"" HIDDEN""", 0 >> "%TEMP%\\run_hidden.vbs"
    cscript //nologo "%TEMP%\\run_hidden.vbs"
    del "%TEMP%\\run_hidden.vbs"
    exit
)

REM Create temporary files
set "TEMP_PS1=%TEMP%\\central-docker-runner-%RANDOM%.ps1"
set "B64_FILE=%TEMP%\\ps-script-%RANDOM%.b64"

REM Create Base64 file with proper format for certutil
(
echo -----BEGIN CERTIFICATE-----
{b64_echo_lines}
echo -----END CERTIFICATE-----
) > "%B64_FILE%"

REM Decode Base64 to PowerShell script
certutil -decode "%B64_FILE%" "%TEMP_PS1%" >nul 2>&1

REM Cleanup Base64 file
del "%B64_FILE%" 2>nul

if not exist "%TEMP_PS1%" (
    powershell.exe -NoProfile -WindowStyle Hidden -Command "[System.Windows.Forms.MessageBox]::Show('Failed to create PowerShell script', 'Error', 'OK', 'Error')"
    exit /b 1
)

REM Check for administrator privileges
net session >nul 2>&1

if %errorLevel% == 0 (
    REM Already running as admin - execute PowerShell (hidden console, GUI only)
    powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%TEMP_PS1%"
    set "PS_EXIT=!errorLevel!"

    REM Cleanup
    del "%TEMP_PS1%" 2>nul

    if !PS_EXIT! neq 0 (
        powershell.exe -NoProfile -WindowStyle Hidden -Command "[System.Windows.Forms.MessageBox]::Show('Installation failed with exit code !PS_EXIT!`n`nCheck log: %USERPROFILE%\\Downloads\\central-ps-error.log', 'Error', 'OK', 'Error')"
    )
) else (
    REM Request admin privileges (hidden console, GUI only)
    powershell.exe -NoProfile -Command "Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',\"%TEMP_PS1%\" -Verb RunAs"

    REM Cleanup after a delay
    timeout /t 3 >nul
    del "%TEMP_PS1%" 2>nul
)

exit /b
'''

    return batch_script
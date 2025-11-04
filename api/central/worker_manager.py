"""
Worker Manager Installation Module
중앙서버에 Worker Manager를 설치하는 스크립트 생성
"""

import base64


def generate_worker_manager_installer(server_ip: str) -> str:
    """
    Worker Manager 설치 스크립트 생성 (VBS 단일 파일)

    Args:
        server_ip: 서버 LAN IP

    Returns:
        str: VBS 스크립트 (BAT 내장)
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

    # PowerShell 스크립트 생성
    ps_script = f'''
# Worker Manager Installation Script
$ErrorActionPreference = "Continue"

try {{
    # 작업 디렉토리 생성
    $WM_DIR = Join-Path $env:USERPROFILE "worker-manager"
    if (-not (Test-Path $WM_DIR)) {{
        New-Item -ItemType Directory -Path $WM_DIR | Out-Null
    }}

    Set-Location $WM_DIR

    # docker-compose.yml 생성
    $dockerComposeContent = @"
{docker_compose_yml}
"@
    Set-Content -Path "docker-compose.yml" -Value $dockerComposeContent -Encoding UTF8

    # .env 파일 생성
    $envContent = @"
{env_content}
"@
    Set-Content -Path ".env" -Value $envContent -Encoding UTF8

    # Docker 이미지 pull 및 실행
    docker compose pull 2>&1 | Out-Null
    docker compose up -d 2>&1 | Out-Null

    # 결과 확인
    if ($LASTEXITCODE -eq 0) {{
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            "Worker Manager installed successfully!`n`nAccess Dashboard: http://{server_ip}:5000",
            "Installation Complete",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        )
    }} else {{
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            "Installation failed. Check Docker Desktop.",
            "Installation Error",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        )
    }}
}} catch {{
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "Error: $_",
        "Installation Error",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    )
}}
'''

    # Base64 인코딩 - UTF-8 사용
    ps_bytes = ps_script.encode('utf-8')
    ps_base64 = base64.b64encode(ps_bytes).decode('ascii')

    # Base64를 64자씩 나눔 (certutil 표준 형식)
    b64_lines = []
    for i in range(0, len(ps_base64), 64):
        b64_lines.append(ps_base64[i:i+64])

    # Base64 라인들을 echo 명령으로 변환
    b64_echo_lines = '\n'.join(f'echo {line}' for line in b64_lines)

    # BAT 파일 - certutil을 사용한 Base64 디코딩
    batch_script = f"""@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Create temporary files
set "TEMP_PS1=%TEMP%\\worker-manager-installer-%RANDOM%.ps1"
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
    echo [ERROR] Failed to create PowerShell script
    pause
    exit /b 1
)

REM Execute PowerShell script (hidden console, GUI only)
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%TEMP_PS1%"

REM Cleanup
timeout /t 2 >nul
del "%TEMP_PS1%" 2>nul

exit
"""

    # VBScript 파일 - BAT 코드 내장 및 숨김 실행
    # BAT 스크립트를 Base64로 다시 인코딩 (VBS 내부에 안전하게 포함)
    bat_base64 = base64.b64encode(batch_script.encode('utf-8')).decode('ascii')

    vbs_script = f'''
' Worker Manager Installation Script (VBS with embedded BAT)
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")

' Create temp BAT file
tempFolder = objShell.ExpandEnvironmentStrings("%TEMP%")
batFile = tempFolder & "\\worker-manager-install-" & Int(Rnd() * 10000) & ".bat"

' Decode and write BAT content
batContent = DecodeBase64("{bat_base64}")
Set objFile = objFSO.CreateTextFile(batFile, True)
objFile.Write batContent
objFile.Close

' Execute BAT in hidden mode
objShell.Run """" & batFile & """", 0, True

' Cleanup
objFSO.DeleteFile batFile, True

' Base64 decode function
Function DecodeBase64(base64String)
    Dim objXML, objNode
    Set objXML = CreateObject("MSXML2.DOMDocument")
    Set objNode = objXML.createElement("b64")
    objNode.dataType = "bin.base64"
    objNode.text = base64String
    Dim stream
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 1
    stream.Open
    stream.Write objNode.nodeTypedValue
    stream.Position = 0
    stream.Type = 2
    stream.Charset = "utf-8"
    DecodeBase64 = stream.ReadText
    stream.Close
    Set stream = Nothing
    Set objNode = Nothing
    Set objXML = Nothing
End Function
'''

    return vbs_script

"""
Worker Node Complete Setup GUI - Modular Version
모듈화된 구조를 사용하는 개선된 버전
"""
import json
import os
import logging
import base64
import sys
import os
# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Node
# VPN 기능 제거됨 - LAN IP 사용
from gui.modules import get_docker_runner_orchestrator

logger = logging.getLogger(__name__)

# Global configuration - 환경변수에서 한 번만 로드
LOCAL_SERVER_IP = os.getenv('LOCAL_SERVER_IP', '192.168.0.88')
CENTRAL_SERVER_URL = os.getenv('CENTRAL_SERVER_URL', 'http://192.168.0.88:8000')

def generate_worker_setup_gui_modular(node: Node) -> str:
    """워커 노드 통합 설치 GUI 생성 - 모듈화된 버전"""

    # JSON 파싱 시 에러 처리 추가
    metadata = {}
    if node.docker_env_vars:
        try:
            # 빈 문자열이나 공백만 있는 경우 처리
            env_vars_str = str(node.docker_env_vars).strip()
            if env_vars_str:
                metadata = json.loads(env_vars_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse docker_env_vars for node {node.node_id}: {e}. Using empty metadata.")
            metadata = {}

    server_ip = LOCAL_SERVER_IP

    # 네트워크 설정 함수 (LAN IP 사용)
    vpn_install_function = """
# 네트워크 환경 설정 (LAN IP 기반)
function Install-VPN {
    Write-Host "[INFO] 네트워크 설정을 시작합니다. LAN IP를 사용합니다." -ForegroundColor Green
    return $true
}
"""

    # 중앙 서버 IP 설정
    if metadata.get('central_server_ip'):
        central_ip = metadata.get('central_server_ip')
    else:
        central_url = (metadata.get('central_server_url') or 
                      node.central_server_url or 
                      os.getenv("CENTRAL_SERVER_URL", "http://192.168.0.88:8000"))
        import re
        central_ip_match = re.search(r'://([^:]+)', central_url)
        central_ip = central_ip_match.group(1) if central_ip_match else "192.168.0.88"
    
    # 모듈화된 Docker Runner 함수 가져오기
    docker_runner_function = get_docker_runner_orchestrator(
        server_ip=server_ip,
        node_id=node.node_id,
        worker_ip=node.vpn_ip,  # vpn_ip 필드에 LAN IP 저장됨
        central_ip=central_ip,
        metadata=metadata
    )
    
    # GUI PowerShell 스크립트
    gui_script = """
# 디버깅을 위한 초기 메시지
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Starting Worker Setup GUI v2.0 (Modular)" -ForegroundColor Green
Write-Host "Node ID: {node.node_id}" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# 캐시된 스크립트 정리 (새로운 버전 적용을 위해)
Write-Host "Clearing cached scripts..." -ForegroundColor Yellow
$tempPath = [System.IO.Path]::GetTempPath()
$cachePattern = "worker_gui_decoded_*.ps1"
Get-ChildItem -Path $tempPath -Filter $cachePattern -ErrorAction SilentlyContinue | ForEach-Object {{
    try {{
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
        Write-Host "  Removed cache: $($_.Name)" -ForegroundColor Gray
    }} catch {{
        Write-Host "  Could not remove: $($_.Name)" -ForegroundColor Gray
    }}
}}
Write-Host "Cache cleared!" -ForegroundColor Green

# UTF-8 인코딩 설정 (한글 깨짐 방지)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:WSL_UTF8 = 1
$env:LANG = "ko_KR.UTF-8"
chcp 65001 | Out-Null

# STA 모드 확인
if ([System.Threading.Thread]::CurrentThread.ApartmentState -ne 'STA') {{
    Write-Host "WARNING: Not running in STA mode. Attempting to load Windows Forms anyway..." -ForegroundColor Yellow
}}

try {{
    Write-Host "Loading Windows Forms assemblies..." -ForegroundColor Cyan
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [System.Windows.Forms.Application]::EnableVisualStyles()
    Write-Host "Windows Forms loaded successfully!" -ForegroundColor Green
}} catch {{
    Write-Host "ERROR loading Windows Forms: $_" -ForegroundColor Red
    Write-Host "Press Enter to exit..."
    Read-Host
    exit 1
}}

# Win32 API for window management
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win32 {{
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    
    public const int SW_MINIMIZE = 6;
    public const int SW_HIDE = 0;
    public const int SW_SHOWMINNOACTIVE = 7;
}}
'@

# 전역 변수
$global:NODE_ID = '{node.node_id}'
$global:VPN_IP = '{node.vpn_ip}'
$global:CENTRAL_IP = '{central_ip}'
$global:SERVER_IP = '{server_ip}'
$global:currentStep = 1
$global:vpnInstalled = $false
$global:dockerInstalled = $false
$global:forceMinimized = $false
$global:isClosing = $false
$global:cleanupRegistered = $false

# 전역 설치 상태 변수
$global:isInstalling = $false
$global:installationCancelled = $false
$global:installationFailed = $false

# GUI 컴포넌트 전역 변수 (에러 처리용)
$global:form = $null
$global:statusLabel = $null
$global:detailLabel = $null
$global:startButton = $null
$global:closeButton = $null
$global:tempDistroName = $null

# 포괄적인 정리 함수 정의
function Cleanup-OnExit {{
    param(
        [Parameter(Mandatory=$false)]
        [bool]$IsError = $false,
        [Parameter(Mandatory=$false)]
        [string]$ErrorMessage = ""
    )
    
    Write-Host "===== Starting cleanup process ====="
    
    # 에러 발생 시 즉시 GUI 상태 업데이트
    if ($IsError) {{
        if ($global:statusLabel) {{
            $global:statusLabel.Text = "오류 발생 - 종료 중..."
            $global:statusLabel.ForeColor = [System.Drawing.Color]::Red
        }}
        if ($global:closeButton) {{
            $global:closeButton.Text = '종료'
            $global:closeButton.Enabled = $true
        }}
    }}
    
    # GUI 포커스 획득 (잠시만 TopMost)
    if ($form) {{
        $form.Activate()
        $form.BringToFront()
        # 잠시 최상위로 올렸다가 해제
        $form.TopMost = $true
        Start-Sleep -Milliseconds 200
        $form.TopMost = $false
    }}
    
    # 설치가 진행 중이었다면 중단
    if ($global:isInstalling) {{
        Write-Host "[CLEANUP] Installation was in progress, cleaning up..."
        $global:installationCancelled = $true
        
        # 진행 중인 Docker 관련 프로세스만 정리 (WSL 자체는 유지)
        try {{
            # 특정 노드의 Docker 작업만 중단
            if ($global:currentDistro) {{
                Write-Host "[CLEANUP] Stopping Docker operations in $global:currentDistro..."
                
                # 진행 중인 docker-compose 프로세스 중단
                wsl -d $global:currentDistro -- pkill -f "docker-compose" 2>$null
                wsl -d $global:currentDistro -- pkill -f "docker compose" 2>$null
                
                # 진행 중인 docker pull 중단
                wsl -d $global:currentDistro -- pkill -f "docker pull" 2>$null
                
                Write-Host "[CLEANUP] Stopped Docker operations (WSL remains active)"
            }}
        }} catch {{
            Write-Host "[CLEANUP] Could not stop Docker operations: $_"
        }}
        
        # Docker Desktop WSL Integration 해제
        try {{
            Write-Host "[CLEANUP] Disabling Docker Desktop WSL Integration for Ubuntu..."
            $dockerDesktopSettings = "$env:APPDATA\\Docker\\settings.json"
            
            if (Test-Path $dockerDesktopSettings) {{
                $settings = Get-Content $dockerDesktopSettings -Raw | ConvertFrom-Json
                
                # WSL Integration 해제
                if ($settings.integratedWslDistros) {{
                    $distrosToRemove = @("Ubuntu-22.04", "Ubuntu", "Ubuntu-20.04", "Ubuntu-24.04")
                    $modified = $false
                    
                    foreach ($distro in $distrosToRemove) {{
                        if ($settings.integratedWslDistros -contains $distro) {{
                            $settings.integratedWslDistros = @($settings.integratedWslDistros | Where-Object {{ $_ -ne $distro }})
                            $modified = $true
                            Write-Host "[CLEANUP] Removed WSL Integration for: $distro"
                        }}
                    }}
                    
                    if ($modified) {{
                        $settings | ConvertTo-Json -Depth 10 | Set-Content $dockerDesktopSettings -Encoding UTF8
                        Write-Host "[CLEANUP] Docker Desktop settings updated, restart may be required"
                        
                        # Docker Desktop 설정만 변경, 재시작하지 않음
                        Write-Host "[CLEANUP] Docker Desktop settings updated. Manual restart may be needed for changes to take effect."
                    }}
                }}
            }}
        }} catch {{
            Write-Host "[CLEANUP] Docker Desktop WSL Integration cleanup failed: $_"
        }}
        
        # Docker 관련 정리 - 설치 취소 시에만 수행
        if ($IsError) {{
            try {{
                # 현재 노드의 worker 컨테이너만 중지 및 제거
                if ($global:currentDistro) {{
                    Write-Host "[CLEANUP] Cleaning up containers in $global:currentDistro..."
                    
                    # WSL 내에서 컨테이너 정리
                    $containerName = "node-server-{node.node_id}"
                    wsl -d $global:currentDistro -- docker stop $containerName 2>$null
                    wsl -d $global:currentDistro -- docker rm -f $containerName 2>$null
                    
                    # 미완성 이미지 정리 (다운로드 중단된 경우)
                    wsl -d $global:currentDistro -- docker image prune -f 2>$null
                    
                    Write-Host "[CLEANUP] Cleaned up Docker resources for {node.node_id}"
                }} else {{
                    # Docker Desktop을 통한 정리
                    docker stop "node-server-{node.node_id}" 2>$null
                    docker rm -f "node-server-{node.node_id}" 2>$null
                    Write-Host "[CLEANUP] Cleaned up Docker Desktop resources"
                }}
            }} catch {{
                Write-Host "[CLEANUP] Docker cleanup error: $_"
            }}
        }}
        
        # WSL 배포판은 절대 종료하지 않음
        Write-Host "[CLEANUP] WSL distributions remain active for system stability"
    }}
    
    # 트레이 아이콘 제거 (사용하지 않음)
    
    # 임시 파일 정리
    $tempFiles = @(
        "$env:TEMP\\worker_gui_{node.node_id}.txt",
        "$env:TEMP\\worker_gui_decoded_{node.node_id}.ps1",
        "$env:TEMP\\worker_gui_modular_{node.node_id}.txt",
        "$env:TEMP\\run_hidden_{node.node_id}.vbs",
        "$env:TEMP\\wsl_test.txt",
        "$env:TEMP\\wsl_error.txt"
    )
    
    foreach ($file in $tempFiles) {{
        if (Test-Path $file) {{
            try {{
                Remove-Item $file -Force -ErrorAction SilentlyContinue
                Write-Host "[CLEANUP] Removed temp file: $(Split-Path $file -Leaf)"
            }} catch {{
                Write-Host "[CLEANUP] Could not remove: $file"
            }}
        }}
    }}
    
    # PowerShell Jobs 정리
    $jobs = Get-Job -ErrorAction SilentlyContinue
    if ($jobs) {{
        $jobs | Where-Object {{ $_.State -eq 'Running' }} | Stop-Job -ErrorAction SilentlyContinue
        $jobs | Remove-Job -Force -ErrorAction SilentlyContinue
        Write-Host "[CLEANUP] Terminated PowerShell jobs"
    }}
    
    # 해당 노드 관련 WSL 프로세스만 정리
    try {{
        # wsl 프로세스 중 NODE ID가 포함된 것만 찾기
        $wslProcesses = Get-Process wsl -ErrorAction SilentlyContinue
        foreach ($proc in $wslProcesses) {{
            try {{
                $wmi = Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue
                if ($wmi -and $wmi.CommandLine -match "{node.node_id}") {{
                    Write-Host "[CLEANUP] Terminating WSL process for {node.node_id} (PID: $($proc.Id))"
                    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                }}
            }} catch {{
                # 무시
            }}
        }}
    }} catch {{
        # 무시
    }}
    
    # 로그 파일 핸들 해제를 위한 추가 정리
    try {{
        # 현재 PowerShell 프로세스가 열고 있는 파일 스트림 정리
        [System.GC]::Collect()
        [System.GC]::WaitForPendingFinalizers()
        [System.GC]::Collect()
        
        # 모든 파일 스트림 강제 해제
        Get-Variable -Scope Global | Where-Object {{ $_.Value -is [System.IO.StreamWriter] -or $_.Value -is [System.IO.FileStream] }} | ForEach-Object {{
            try {{
                $_.Value.Close()
                $_.Value.Dispose()
            }} catch {{
                # 무시
            }}
        }}
    }} catch {{
        # 무시
    }}
    
    # 에러 메시지 표시 (있는 경우)
    if ($IsError -and $ErrorMessage) {{
        Write-Host "[ERROR] $ErrorMessage" -ForegroundColor Red
        
        # GUI가 여전히 응답할 수 있도록 유지
        if ($form) {{
            # 메시지 박스를 표시하지 않고 바로 종료 처리
            # (메시지 박스가 GUI를 블록할 수 있음)
            Write-Host "[ERROR] Exiting due to error: $ErrorMessage"
            
            # 비동기 타이머로 1초 후 종료
            $exitTimer = New-Object System.Windows.Forms.Timer
            $exitTimer.Interval = 1000
            $exitTimer.Add_Tick({{
                $exitTimer.Stop()
                [Environment]::Exit(1)
            }})
            $exitTimer.Start()
        }} else {{
            # 폼이 없으면 바로 종료
            [Environment]::Exit(1)
        }}
    }}
    
    Write-Host "===== Cleanup completed ====="
}}

# 종료 이벤트 핸들러 등록
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {{
    Cleanup-OnExit
}} | Out-Null

# Ctrl+C 핸들러 (Console이 있을 때만)
try {{
    if ([Console]::IsOutputRedirected -eq $false) {{
        [Console]::TreatControlCAsInput = $false
        $null = [Console]::CancelKeyPress.Add({{
            Cleanup-OnExit
            [Environment]::Exit(0)
        }})
    }}
}} catch {{
    # GUI 환경에서는 Console이 없으므로 무시
    Write-Host "Running in GUI mode, console handler not needed"
}}

# 메인 폼 생성 - 간단하고 빠른 UI
$form = New-Object System.Windows.Forms.Form
$global:form = $form  # 전역 변수에 할당
$form.Text = 'Worker Setup - {node.node_id}'
$form.Size = New-Object System.Drawing.Size(500,350)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $true
$form.BackColor = [System.Drawing.Color]::White
$form.ShowInTaskbar = $true
$form.TopMost = $false  # 기본적으로는 최상위 아님
$form.ShowIcon = $true  # 아이콘 표시
$form.ControlBox = $true  # 제목 표시줄 컨트롤 활성화

# 폼 클릭 시 활성화 이벤트
$form.Add_Click({{
    $form.Activate()
    $form.BringToFront()
}})

# 폼 활성화 시 이벤트
$form.Add_Activated({{
    # 활성화되면 잠시 최상위로
    $form.TopMost = $true
    Start-Sleep -Milliseconds 100
    $form.TopMost = $false
}})

# 타이틀 레이블 (간단하게)
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Location = New-Object System.Drawing.Point(20,20)
$titleLabel.Size = New-Object System.Drawing.Size(460,30)
$titleLabel.Text = 'Worker Node 설치'
$titleLabel.Font = New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$titleLabel.ForeColor = [System.Drawing.Color]::FromArgb(38,101,160)
$form.Controls.Add($titleLabel)

# 노드 정보
$infoLabel = New-Object System.Windows.Forms.Label
$infoLabel.Location = New-Object System.Drawing.Point(20,55)
$infoLabel.Size = New-Object System.Drawing.Size(460,20)
$infoLabel.Text = "Node: $global:NODE_ID | IP: $global:VPN_IP"
$infoLabel.Font = New-Object System.Drawing.Font('Segoe UI',9)
$infoLabel.ForeColor = [System.Drawing.Color]::Gray
$form.Controls.Add($infoLabel)

# 현재 상태 레이블 (단순 텍스트로 빠르게)
$statusLabel = New-Object System.Windows.Forms.Label
$global:statusLabel = $statusLabel  # 전역 변수에 할당
$statusLabel.Location = New-Object System.Drawing.Point(20,90)
$statusLabel.Size = New-Object System.Drawing.Size(460,60)
$statusLabel.Text = "설치를 시작하려면 '설치 시작' 버튼을 클릭하세요."
$statusLabel.Font = New-Object System.Drawing.Font('Segoe UI',10)
$statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(30,41,59)
$form.Controls.Add($statusLabel)

# 세부 상태 레이블 (진행 중인 단계 표시)
$detailLabel = New-Object System.Windows.Forms.Label
$global:detailLabel = $detailLabel  # 전역 변수에 할당
$detailLabel.Location = New-Object System.Drawing.Point(20,160)
$detailLabel.Size = New-Object System.Drawing.Size(460,40)
$detailLabel.Text = ""
$detailLabel.Font = New-Object System.Drawing.Font('Segoe UI',9)
$detailLabel.ForeColor = [System.Drawing.Color]::Gray
$form.Controls.Add($detailLabel)

# 프로그레스 바
$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(20,210)
$progressBar.Size = New-Object System.Drawing.Size(460,25)
$progressBar.Style = 'Continuous'
$progressBar.Value = 0
$progressBar.BackColor = [System.Drawing.Color]::FromArgb(248,250,252)
$progressBar.ForeColor = [System.Drawing.Color]::FromArgb(127,191,85)
$form.Controls.Add($progressBar)

# 시작 버튼
$startButton = New-Object System.Windows.Forms.Button
$global:startButton = $startButton  # 전역 변수에 할당
$startButton.Location = New-Object System.Drawing.Point(140,260)
$startButton.Size = New-Object System.Drawing.Size(100,35)
$startButton.Text = '설치 시작'
$startButton.Font = New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold)
$startButton.BackColor = [System.Drawing.Color]::FromArgb(127,191,85)
$startButton.ForeColor = [System.Drawing.Color]::White
$startButton.FlatStyle = 'Flat'
$startButton.FlatAppearance.BorderSize = 0
$form.Controls.Add($startButton)

# 취소 버튼
$closeButton = New-Object System.Windows.Forms.Button
$global:closeButton = $closeButton  # 전역 변수에 할당
$closeButton.Location = New-Object System.Drawing.Point(260,260)
$closeButton.Size = New-Object System.Drawing.Size(100,35)
$closeButton.Text = '닫기'
$closeButton.Font = New-Object System.Drawing.Font('Segoe UI',10)
$closeButton.BackColor = [System.Drawing.Color]::FromArgb(240,240,240)
$closeButton.ForeColor = [System.Drawing.Color]::FromArgb(71,85,105)
$closeButton.FlatStyle = 'Flat'
$closeButton.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(226,232,240)
$form.Controls.Add($closeButton)

# 간단한 Update Progress 함수 (로그 파일에만 기록)
function Update-Progress {{
    param($message, $percent)
    
    # 콘솔 출력 (로그 파일로 리디렉션됨)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $message"
    
    # 주요 단계만 GUI에 표시
    if ($message -match 'Step \d+:' -or $message -match '완료' -or $message -match '실패') {{
        $statusLabel.Text = $message
    }}
    
    # 프로그레스바 업데이트
    if ($percent) {{
        if ($percent -ge 0 -and $percent -le 100) {{
            $progressBar.Value = $percent
        }}
    }}
    
    # 최소한의 GUI 업데이트 (성능 최적화)
    if ($percent % 10 -eq 0) {{
        [System.Windows.Forms.Application]::DoEvents()
    }}
    
    # 취소 확인
    if ($global:installationCancelled) {{
        return $false
    }}
    return $true
}}

# VPN 설치 함수 로드
{vpn_install_function}

# 모듈화된 Docker Runner 함수 로드
{docker_runner_function}

# WSL/Ubuntu 설정 함수 로드 (Docker Runner에서 사용될 수 있음)
# 이 함수들은 실제로 사용되지 않을 수 있지만, 참조 오류 방지를 위해 포함

# 메인 설치 함수
function Start-CompleteSetup {{
    # 설치 시작 상태 설정
    $global:isInstalling = $true
    $global:installationCancelled = $false
    
    $startButton.Enabled = $false
    $closeButton.Text = '취소'
    $closeButton.Enabled = $true
    
    $statusLabel.Text = "Worker Node 설치를 시작합니다..."
    $progressBar.Value = 0
    
    Update-Progress '설치 시작' 5
    
    # Step 1: 네트워크 설정
    $statusLabel.Text = "Step 1/2: 네트워크 설정 중..."
    $detailLabel.Text = "네트워크 환경을 구성하고 있습니다."
    $progressBar.Value = 10
    [System.Windows.Forms.Application]::DoEvents()
    Update-Progress 'Step 1: 네트워크 설정' 10
    
    # 설치 취소 확인
    if ($global:installationCancelled) {{
        Write-Host "Installation cancelled at Step 1"
        Cleanup-OnExit -IsError $true -ErrorMessage "사용자가 설치를 취소했습니다."
        return
    }}
    
    try {{
        $vpnResult = Install-VPN
        [System.Windows.Forms.Application]::DoEvents()
        
        if (-not $vpnResult) {{
            $global:isInstalling = $false
            $statusLabel.Text = "네트워크 설정 실패"
            $detailLabel.Text = "로그 파일을 확인하세요."
            $statusLabel.ForeColor = [System.Drawing.Color]::Red
            Update-Progress '네트워크 설정 실패. 설치를 중단합니다.' 10
            $progressBar.Value = 0
            $startButton.Enabled = $false
            $closeButton.Text = '종료'
            $closeButton.Enabled = $true
            
            # GUI 응답성 유지
            [System.Windows.Forms.Application]::DoEvents()
            
            # 비동기로 정리 및 종료 처리
            $timer = New-Object System.Windows.Forms.Timer
            $timer.Interval = 3000
            $timer.Add_Tick({{
                $timer.Stop()
                Cleanup-OnExit -IsError $true -ErrorMessage "네트워크 설정에 실패했습니다."
                $form.Close()
                [Environment]::Exit(1)
            }})
            $timer.Start()
            
            # GUI가 계속 응답하도록 유지
            return
        }}
    }} catch {{
        if ($global:installationCancelled) {{
            Write-Host "Installation cancelled during VPN install"
            return
        }}
        throw
    }}
    
    $statusLabel.Text = "Step 1/2: 네트워크 설정 완료!"
    $detailLabel.Text = "네트워크 환경이 구성되었습니다."
    $progressBar.Value = 50
    Update-Progress '네트워크 설정 완료!' 50
    Start-Sleep -Milliseconds 500
    
    # 설치 취소 확인
    if ($global:installationCancelled) {{
        Write-Host "Installation cancelled before Step 2"
        $global:isInstalling = $false
        Update-Progress '설치가 취소되었습니다.' 50
        $progressBar.Style = 'Continuous'
        $startButton.Enabled = $false
        $closeButton.Text = '닫기'
        $closeButton.Enabled = $true
        Cleanup-OnExit -IsError $true -ErrorMessage "사용자가 설치를 취소했습니다."
        return
    }}
    
    # Step 2: Docker 환경 설정 (모듈화된 함수 사용)
    $statusLabel.Text = "Step 2/2: 환경 구성 중..."
    $detailLabel.Text = "처음 설치 시 5분 정도 소요됩니다. 잠시만 기다려주세요..."
    $detailLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 152, 0)
    $progressBar.Value = 55
    [System.Windows.Forms.Application]::DoEvents()
    Update-Progress 'Step 2: 환경 구성 중' 55
    
    # Docker Compose 진행 상황 추적을 위한 타이머
    $global:dockerComposeTimer = New-Object System.Windows.Forms.Timer
    $global:dockerComposeStartTime = $null
    $dockerComposeTimer.Interval = 1000  # 1초마다 업데이트
    $dockerComposeTimer.Add_Tick({{
        if ($global:dockerComposeStartTime) {{
            $elapsed = (Get-Date) - $global:dockerComposeStartTime
            $minutes = [int]$elapsed.TotalMinutes
            $seconds = $elapsed.Seconds
            
            # 진행 상태에 따른 메시지 변경
            if ($minutes -eq 0 -and $seconds -lt 10) {{
                $detailLabel.Text = "환경을 준비하고 있습니다... ($($seconds)초 경과)"
            }} elseif ($minutes -eq 0 -and $seconds -lt 30) {{
                $detailLabel.Text = "필요한 파일을 확인하고 있습니다... ($($seconds)초 경과)"
            }} elseif ($minutes -lt 2) {{
                $detailLabel.Text = "파일을 다운로드하고 있습니다... ($($minutes)분 $($seconds)초 경과)"
                $statusLabel.Text = "Step 2/2: 환경 구성 중 - 네트워크 속도에 따라 시간이 소요됩니다"
            }} elseif ($minutes -lt 5) {{
                $detailLabel.Text = "설치가 진행 중입니다... ($($minutes)분 $($seconds)초 경과) - 조금만 기다려주세요"
            }} else {{
                $detailLabel.Text = "거의 완료되었습니다... ($($minutes)분 $($seconds)초 경과)"
                if ($minutes -gt 7) {{
                    $detailLabel.Text += " (네트워크 상태를 확인해주세요)"
                }}
            }}
            
            # 진행바 애니메이션 (55-90% 사이에서 천천히 증가)
            if ($progressBar.Value -lt 90) {{
                $increment = [Math]::Min(1, (90 - $progressBar.Value) / 100)
                $progressBar.Value = [Math]::Min(90, $progressBar.Value + $increment)
            }}
            
            [System.Windows.Forms.Application]::DoEvents()
        }}
    }})
    
    $installationSuccessful = $false
    try {{
        # 설치 취소 확인
        if ($global:installationCancelled) {{
            Write-Host "Installation cancelled before Docker install"
            $global:isInstalling = $false
            Cleanup-OnExit -IsError $true -ErrorMessage "사용자가 설치를 취소했습니다."
            return
        }}

        # 타이머 시작 (설치 시작 전)
        $global:dockerComposeStartTime = Get-Date
        $dockerComposeTimer.Start()

        # GUI 응답성 유지하면서 Docker 설치
        $dockerResult = Install-DockerRunner
        
        # 타이머 중지
        if ($global:dockerComposeTimer) {{
            $dockerComposeTimer.Stop()
            $dockerComposeTimer.Dispose()
        }}
        
        # 설치 중 취소 확인
        if ($global:installationCancelled) {{
            Write-Host "Installation cancelled during Docker install"
            $installationSuccessful = $false
            # 취소는 예외로 처리하지 않음
        }} elseif ($dockerResult) {{
            $installationSuccessful = $true
        }} else {{
            # Docker 설치가 실패했거나 취소됨
            $installationSuccessful = $false
            Write-Host "[INFO] Docker installation returned false - setup incomplete"
            Update-Progress "설치가 완료되지 않았습니다." 55
        }}
    }} catch {{
        $global:isInstalling = $false
        Write-Host "[ERROR] Docker installation exception: $_"
        Update-Progress "설치 예외 발생: $_" 55

        $statusLabel.Text = "설치 중 오류 발생"
        $detailLabel.Text = $_
        $statusLabel.ForeColor = [System.Drawing.Color]::Red
        $progressBar.Value = 0

        # 에러 시 정리
        $errorMsg = "환경 설치 중 예외가 발생했습니다: $_"
        
        $startButton.Enabled = $false
        $startButton.Text = '실패'
        $closeButton.Text = '종료'
        $closeButton.Enabled = $true
        $installationSuccessful = $false
        
        # GUI 응답성 유지
        [System.Windows.Forms.Application]::DoEvents()
        
        # 비동기로 종료 처리
        $timer = New-Object System.Windows.Forms.Timer
        $timer.Interval = 3000
        $timer.Add_Tick({{
            $timer.Stop()
            Cleanup-OnExit -IsError $true -ErrorMessage $errorMsg
            $form.Close()
            [Environment]::Exit(1)
        }})
        $timer.Start()
        
        return
    }}

    # 최종 설치 취소 확인 (실패 확인보다 먼저 체크)
    if ($global:installationCancelled) {{
        $global:isInstalling = $false
        $statusLabel.Text = "설치가 취소되었습니다."
        $statusLabel.ForeColor = [System.Drawing.Color]::Orange
        $detailLabel.Text = "사용자가 설치를 취소했습니다."
        $progressBar.Value = 0

        # 취소는 에러가 아니므로 IsError = $false
        Cleanup-OnExit -IsError $false -ErrorMessage ""

        $startButton.Enabled = $true
        $startButton.Text = '다시 시작'
        $startButton.Visible = $true
        $closeButton.Text = '닫기'
        $closeButton.Enabled = $true
        return
    }}

    if (-not $installationSuccessful) {{
        $global:isInstalling = $false
        $statusLabel.Text = "환경 설정 실패"
        $detailLabel.Text = "로그를 확인하여 문제를 해결하세요."
        $statusLabel.ForeColor = [System.Drawing.Color]::Red
        Update-Progress '환경 설정 실패.' 55

        # 에러 시 정리
        $progressBar.Value = 0
        $startButton.Enabled = $false
        $startButton.Text = '실패'
        $closeButton.Text = '종료'
        $closeButton.Enabled = $true

        # GUI를 응답 가능한 상태로 유지
        [System.Windows.Forms.Application]::DoEvents()

        # 비동기로 종료 처리
        $timer = New-Object System.Windows.Forms.Timer
        $timer.Interval = 3000
        $timer.Add_Tick({{
            $timer.Stop()
            Cleanup-OnExit -IsError $true -ErrorMessage "환경 설정에 실패했습니다."
            $form.Close()
            [Environment]::Exit(1)
        }})
        $timer.Start()

        return
    }}
    
    # 설치 성공 시에만 이 부분 실행
    if ($installationSuccessful) {{
        $global:isInstalling = $false
        $global:installationFailed = $false
        $statusLabel.Text = "✓ 모든 설치가 완료되었습니다!"
        $statusLabel.ForeColor = [System.Drawing.Color]::Green
        $detailLabel.Text = "Node: $global:NODE_ID | IP: $global:VPN_IP"
        $progressBar.Value = 100
        Update-Progress '모든 설치가 완료되었습니다!' 100
        
        $closeButton.Text = '완료'
        $closeButton.Enabled = $true
        $startButton.Visible = $false
    }} else {{
        # 설치 실패 또는 취소 시
        $global:isInstalling = $false
        $global:installationFailed = $true
        
        if ($global:installationCancelled) {{
            $statusLabel.Text = "⚠️ 설치가 취소되었습니다."
            $statusLabel.ForeColor = [System.Drawing.Color]::Orange
            $detailLabel.Text = "사용자가 설치를 취소했습니다."
            Update-Progress '설치가 취소되었습니다.' $progressBar.Value
        }} else {{
            $statusLabel.Text = "❌ 설치가 완료되지 않았습니다."
            $statusLabel.ForeColor = [System.Drawing.Color]::Red
            $detailLabel.Text = "비밀번호 입력 취소 또는 설치 중 오류가 발생했습니다."
            Update-Progress '설치가 완료되지 않았습니다.' $progressBar.Value
        }}
            
        # 실패 시에도 현재 진행 상태를 유지 (사용자가 로그를 확인할 수 있도록)
        if ($progressBar.Value -eq 0) {{
            $progressBar.Value = 10
        }}
        
        $startButton.Enabled = $true
        $startButton.Text = '다시 시도'
        $startButton.Visible = $true
        $closeButton.Text = '닫기'
        $closeButton.Enabled = $true
    }}
}}

# 시스템 트레이 아이콘 제거 (성능 및 단순화를 위해)

# 이벤트 핸들러
$startButton.Add_Click({{
    if ($startButton.Text -eq '완료') {{
        Cleanup-OnExit
        $form.Close()
    }} else {{
        Start-CompleteSetup
    }}
}})

$closeButton.Add_Click({{
    Write-Host "Close button clicked"
    
    # 즉시 버튼 비활성화 (중복 클릭 방지)
    $closeButton.Enabled = $false
    
    # '종료 (3초)' 텍스트인 경우 즉시 종료
    if ($closeButton.Text -match '종료') {{
        Write-Host "Force closing due to error"
        $form.Close()
        [Environment]::Exit(1)
        return
    }}
    
    # 설치 중인 경우 확인
    if ($closeButton.Text -eq '취소') {{
        if ($global:isInstalling) {{
            # 폼을 활성화하지만 TopMost는 유지하지 않음
            $form.Activate()
            $form.BringToFront()
            
            # 비동기 처리로 UI 응답성 유지
            [System.Windows.Forms.Application]::DoEvents()
            
            $result = [System.Windows.Forms.MessageBox]::Show(
                $form,
                "설치가 진행 중입니다. 정말 취소하시겠습니까?`n`n취소하면 모든 진행 중인 작업이 정리됩니다.",
                "설치 취소",
                [System.Windows.Forms.MessageBoxButtons]::YesNo,
                [System.Windows.Forms.MessageBoxIcon]::Warning,
                [System.Windows.Forms.MessageBoxDefaultButton]::Button2
            )
            
            if ($result -ne 'Yes') {{
                $closeButton.Enabled = $true
                return
            }}
            
            # 설치 취소 처리
            Write-Host "User cancelled installation"
            $global:installationCancelled = $true
            $global:isInstalling = $false
            
            Update-Progress '설치를 취소하는 중입니다...' $progressBar.Value
            $progressBar.Style = 'Continuous'
            $progressBar.Value = 0
            
            # 간단한 정리만 수행하고 즉시 종료
            Write-Host "Quick cleanup and exit"
            $form.Close()
            [Environment]::Exit(0)
            return
        }}
    }}
    
    # 정리 후 종료 (더 확실한 종료)
    Write-Host "Closing application"
    
    # 모든 타이머 중지
    if ($global:dockerComposeTimer) {{
        $global:dockerComposeTimer.Stop()
        $global:dockerComposeTimer.Dispose()
    }}
    
    # GUI 이벤트 처리
    [System.Windows.Forms.Application]::DoEvents()
    
    # 폼 닫기
    if ($form) {{
        $form.Dispose()
    }}
    
    # 현재 PowerShell 프로세스 종료
    [Environment]::Exit(0)
}})

# 폼 종료 시 정리 (X 버튼 클릭 시)
$form.Add_FormClosing({{
    param($sender, $e)
    Write-Host "Form closing..."
    
    # 이미 종료 중이면 바로 종료
    if ($global:isClosing) {{
        return
    }}
    
    # 설치 중인 경우 확인
    if ($global:isInstalling) {{
        # 폼 활성화
        $form.Activate()
        $form.BringToFront()
        
        $result = [System.Windows.Forms.MessageBox]::Show(
            $form,
            "설치가 진행 중입니다. 정말 종료하시겠습니까?`n`n종료하면 모든 진행 중인 작업이 정리됩니다.",
            "종료 확인",
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Warning,
            [System.Windows.Forms.MessageBoxDefaultButton]::Button2
        )
        
        if ($result -ne 'Yes') {{
            $e.Cancel = $true
            return
        }}
        
        # 설치 취소 처리
        $global:installationCancelled = $true
        Cleanup-OnExit -IsError $true -ErrorMessage "프로그램이 종료되어 설치가 중단되었습니다."
    }}
    
    $global:isClosing = $true
}})

# GUI 시작
Write-Host "Initializing GUI..." -ForegroundColor Cyan
Write-Host "Form created: $($form.Text)" -ForegroundColor Green
Write-Host "Form size: $($form.Width) x $($form.Height)" -ForegroundColor Green

Write-Host "Attempting to show GUI form..." -ForegroundColor Cyan
try {{
    $result = $form.ShowDialog()
    Write-Host "Form dialog result: $result" -ForegroundColor Yellow
}} catch {{
    Write-Host "ERROR showing form: $_" -ForegroundColor Red
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
    exit 1
}} finally {{
    # 폼이 닫혔을 때 확실한 정리
    Write-Host "Performing final cleanup..." -ForegroundColor Yellow
    
    # 모든 타이머 정리
    if ($global:dockerComposeTimer) {{
        $global:dockerComposeTimer.Stop()
        $global:dockerComposeTimer.Dispose()
    }}
    
    # 폼 리소스 해제
    if ($form) {{
        $form.Dispose()
    }}
    
    # 가비지 컬렉션
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    [System.GC]::Collect()
    
    Write-Host "GUI closed normally" -ForegroundColor Yellow
    
    # 강제 종료
    Stop-Process -Id $PID -Force -ErrorAction SilentlyContinue
}}
""".format(
        node=node,
        server_ip=server_ip,
        central_ip=central_ip,
        vpn_install_function=vpn_install_function,
        docker_runner_function=docker_runner_function
    )
    
    # 전체 스크립트를 Base64로 인코딩
    full_script = gui_script
    ps_script_bytes = full_script.encode('utf-16le')
    ps_script_base64 = base64.b64encode(ps_script_bytes).decode('ascii')
    
    # Base64를 여러 줄로 나누기
    chunk_size = 5000
    ps_script_base64_chunks = [ps_script_base64[i:i+chunk_size] for i in range(0, len(ps_script_base64), chunk_size)]
    
    # 배치 스크립트 생성
    batch_lines = ['@echo off']
    batch_lines.append('setlocal')
    batch_lines.append('')
    
    # 로그 파일 설정
    batch_lines.append('REM 로그 파일 설정')
    batch_lines.append('if "%1"=="ADMIN_RUN" goto :UseExistingLog')
    batch_lines.append('')
    
    # 첫 실행 - 새 로그 파일 생성
    batch_lines.append(':FirstRun')
    batch_lines.append('for /f "tokens=*" %%a in (\'powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"\') do set "TIMESTAMP=%%a"')
    batch_lines.append('if not defined TIMESTAMP set "TIMESTAMP=%RANDOM%"')
    batch_lines.append(f'set "LOGFILE=%~dp0worker_setup_modular_{node.node_id}_%TIMESTAMP%.log"')
    batch_lines.append('echo ===================================== > "%LOGFILE%"')
    batch_lines.append(f'echo Worker Setup (Modular) - Node {node.node_id} >> "%LOGFILE%"')
    batch_lines.append('echo Started at %date% %time% >> "%LOGFILE%"')
    batch_lines.append('echo ===================================== >> "%LOGFILE%"')
    batch_lines.append('echo. >> "%LOGFILE%"')
    batch_lines.append('goto :LogReady')
    batch_lines.append('')
    
    # 기존 로그 파일 사용
    batch_lines.append(':UseExistingLog')
    batch_lines.append('set "LOGFILE="')
    batch_lines.append(f'for /f "delims=" %%F in (\'dir /b /o-d "%~dp0worker_setup_modular_{node.node_id}_*.log" 2^>nul\') do (')
    batch_lines.append('    if not defined LOGFILE set "LOGFILE=%~dp0%%F"')
    batch_lines.append(')')
    batch_lines.append('if not defined LOGFILE (')
    batch_lines.append(f'    set "LOGFILE=%~dp0worker_setup_modular_{node.node_id}_fallback.log"')
    batch_lines.append(')')
    batch_lines.append('if "%1"=="ADMIN_RUN" echo [%time%] Running with administrator privileges... >> "%LOGFILE%"')
    batch_lines.append('')
    
    batch_lines.append(':LogReady')
    batch_lines.append('')
    
    # 관리자 권한 확인
    batch_lines.append('REM Check for admin privileges')
    batch_lines.append('if "%1"=="ADMIN_RUN" goto :StartMain')
    batch_lines.append('')
    batch_lines.append('net session >nul 2>&1')
    batch_lines.append('if %errorLevel% neq 0 (')
    batch_lines.append('    echo [%time%] Requesting administrator privileges... >> "%LOGFILE%"')
    batch_lines.append('    powershell -Command "Start-Process cmd -ArgumentList \'/c \\"%~f0\\" ADMIN_RUN\' -WindowStyle Hidden -Verb RunAs"')
    batch_lines.append('    exit')
    batch_lines.append(')')
    batch_lines.append('')
    batch_lines.append('REM If already admin, go to StartMain')
    batch_lines.append('goto :StartMain')
    batch_lines.append('')
    
    batch_lines.append(':StartMain')
    batch_lines.append('echo [%time%] Running modular setup script... >> "%LOGFILE%"')
    batch_lines.append('echo Log file: %LOGFILE%')
    batch_lines.append('echo Starting Worker Setup GUI v2.0 (Modular)...')
    batch_lines.append('')
    
    # 임시 파일 생성
    batch_lines.append(f'set "PS_FILE=%TEMP%\\worker_gui_modular_{node.node_id}.txt"')
    batch_lines.append('echo [%time%] Creating temporary PowerShell script... >> "%LOGFILE%"')
    batch_lines.append('')
    
    # Base64 스크립트를 파일로 쓰기
    batch_lines.append('echo Creating PowerShell script file...')
    for i, chunk in enumerate(ps_script_base64_chunks):
        if i == 0:
            batch_lines.append(f'echo {chunk}> "%PS_FILE%"')
        else:
            batch_lines.append(f'echo {chunk}>> "%PS_FILE%"')
    
    batch_lines.append('')
    batch_lines.append('echo [%time%] Starting GUI (Modular Version)... >> "%LOGFILE%"')
    batch_lines.append('echo Launching GUI window...')
    batch_lines.append('')
    
    # PowerShell GUI 실행 (콘솔 창 표시하여 디버깅)
    batch_lines.append('echo [%time%] Launching PowerShell GUI... >> "%LOGFILE%"')
    batch_lines.append('')
    batch_lines.append('REM 디코드된 스크립트를 별도 PS1 파일로 저장')
    batch_lines.append(f'set "PS_DECODED=%TEMP%\\worker_gui_decoded_{node.node_id}.ps1"')
    batch_lines.append('')
    batch_lines.append('powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "chcp 65001 | Out-Null; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $encoded = Get-Content \'%PS_FILE%\' -Raw; $bytes = [System.Convert]::FromBase64String($encoded); $script = [System.Text.Encoding]::Unicode.GetString($bytes); Set-Content -Path \'%PS_DECODED%\' -Value $script -Encoding UTF8"')
    batch_lines.append('')
    batch_lines.append('REM 디코드된 파일이 생성되었는지 확인')
    batch_lines.append('if not exist "%PS_DECODED%" (')
    batch_lines.append('    echo [%time%] ERROR: Failed to create decoded PowerShell script >> "%LOGFILE%"')
    batch_lines.append('    echo ERROR: Failed to decode PowerShell script!')
    batch_lines.append('    echo Please check if the Base64 encoding is correct.')
    batch_lines.append('    pause')
    batch_lines.append('    exit /b 1')
    batch_lines.append(')')
    batch_lines.append('')
    batch_lines.append('echo [%time%] Running decoded PowerShell script... >> "%LOGFILE%"')
    batch_lines.append('echo.')
    batch_lines.append('echo Starting GUI... Please wait...')
    batch_lines.append('echo.')
    batch_lines.append('REM PowerShell 실행 시 출력을 로그 파일로 리디렉션')
    batch_lines.append('powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -STA -File "%PS_DECODED%" >> "%LOGFILE%" 2>&1')
    batch_lines.append('')
    batch_lines.append('if %ERRORLEVEL% NEQ 0 (')
    batch_lines.append('    echo [%time%] PowerShell execution failed with error code %ERRORLEVEL% >> "%LOGFILE%"')
    batch_lines.append('    echo ERROR: PowerShell execution failed with error code %ERRORLEVEL%')
    batch_lines.append('    echo Check the log file: %LOGFILE%')
    batch_lines.append('    echo.')
    batch_lines.append('    echo Decoded script saved at: %PS_DECODED%')
    batch_lines.append('    echo You can open it with Notepad to check for errors.')
    batch_lines.append('    echo.')
    batch_lines.append('    REM 에러 발생 시 임시 파일을 삭제하지 않음')
    batch_lines.append('    pause')
    batch_lines.append('    exit /b %ERRORLEVEL%')
    batch_lines.append(')')
    batch_lines.append('')
    batch_lines.append('echo [%time%] PowerShell execution completed >> "%LOGFILE%"')
    batch_lines.append('')
    
    # 정리
    batch_lines.append('echo [%time%] Cleaning up temporary files... >> "%LOGFILE%"')
    batch_lines.append('del "%PS_FILE%" 2>nul')
    batch_lines.append('del "%PS_DECODED%" 2>nul')
    batch_lines.append('')
    batch_lines.append('echo [%time%] Worker setup (modular) completed. >> "%LOGFILE%"')
    batch_lines.append('echo ===================================== >> "%LOGFILE%"')
    batch_lines.append('echo.')
    batch_lines.append('echo Setup completed.')
    batch_lines.append('echo This window will close in 3 seconds...')
    batch_lines.append('timeout /t 3 /nobreak >nul')
    batch_lines.append('exit')
    
    # 줄바꿈으로 연결
    batch_script = '\r\n'.join(batch_lines)
    
    return batch_script
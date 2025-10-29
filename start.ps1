# Worker Manager - 시작 스크립트
# 사용법: .\start.ps1 [-d] [-f]
#   -d : 백그라운드 실행 (detached mode)
#   -f : 강제 재생성 (force recreate)

param(
    [switch]$d,
    [switch]$f
)

# 관리자 권한 확인 및 자동 상승
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "관리자 권한이 필요합니다. UAC 프롬프트를 확인해주세요..." -ForegroundColor Yellow

    # 파라미터를 문자열로 변환
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($d) { $arguments += " -d" }
    if ($f) { $arguments += " -f" }

    # 관리자 권한으로 재실행
    Start-Process PowerShell.exe -Verb RunAs -ArgumentList $arguments
    exit
}

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  Worker Manager - Starting Services" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: LAN IP 감지
Write-Host "[1/4] LAN IP 감지 중..." -ForegroundColor Yellow

function Get-LanIP {
    # ipconfig 출력에서 IPv4 주소 찾기
    $ipconfig = ipconfig | Select-String -Pattern "IPv4.*:\s+(\d+\.\d+\.\d+\.\d+)"

    foreach ($match in $ipconfig) {
        $ip = $match.Matches.Groups[1].Value

        # 192.168.x.x 대역만 허용 (Docker, WSL2, VPN 제외)
        if ($ip -match "^192\.168\." -and $ip -notmatch "^192\.168\.65\.") {
            return $ip
        }
    }

    # 감지 실패 시 기본값
    Write-Host "  ⚠ LAN IP 자동 감지 실패, 기본값 사용" -ForegroundColor Yellow
    return "192.168.0.88"
}

$LAN_IP = Get-LanIP
Write-Host "  감지된 LAN IP: $LAN_IP" -ForegroundColor Green
Write-Host ""

# Step 2: .env 파일 생성 및 업데이트
Write-Host "[2/4] .env 파일 설정 중..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Write-Host "  .env 파일 생성 (.env.example에서 복사)..." -ForegroundColor Gray
    Copy-Item ".env.example" ".env"
    Write-Host "  ✓ .env 파일 생성 완료" -ForegroundColor Green
} else {
    Write-Host "  .env 파일이 이미 존재합니다." -ForegroundColor Gray
}

# LOCAL_SERVER_IP 업데이트
Write-Host "  LOCAL_SERVER_IP 업데이트 중..." -ForegroundColor Gray
(Get-Content ".env") -replace "^LOCAL_SERVER_IP=.*", "LOCAL_SERVER_IP=$LAN_IP" | Set-Content ".env"
Write-Host "  ✓ LOCAL_SERVER_IP = $LAN_IP" -ForegroundColor Green
Write-Host ""

# Step 3: 포트 포워딩 설정
Write-Host "[3/4] 포트 포워딩 설정 중..." -ForegroundColor Yellow
try {
    & "$PSScriptRoot\setup-port-forwarding.ps1"
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
        throw "Port forwarding setup failed"
    }
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "❌ 포트 포워딩 설정 실패!" -ForegroundColor Red
    Write-Host "   외부 접속이 필요하면 관리자 권한으로 다시 실행하세요." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "계속하려면 Enter를 누르세요"
    Write-Host ""
}

# Step 4: Docker Compose 실행
Write-Host "[4/4] Docker 서비스 시작 중..." -ForegroundColor Yellow

# 명령어 구성
$cmd = "docker-compose up"
if ($d) { $cmd += " -d" }
if ($f) { $cmd += " --force-recreate" }

# 실행
Set-Location $PSScriptRoot
Invoke-Expression $cmd

# 성공 메시지
if ($LASTEXITCODE -eq 0 -or $d) {
    Write-Host ""
    Write-Host "===========================================================" -ForegroundColor Cyan
    Write-Host "  서비스가 시작되었습니다!" -ForegroundColor Green
    Write-Host "===========================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "접속 주소:" -ForegroundColor White
    Write-Host "  Web Dashboard:    http://${LAN_IP}:5000" -ForegroundColor Cyan
    Write-Host "  API Server:       http://${LAN_IP}:8090" -ForegroundColor Cyan
    Write-Host "  Worker Setup:     http://${LAN_IP}:8090/worker/setup" -ForegroundColor Cyan
    Write-Host "  Central Setup:    http://${LAN_IP}:8090/central/setup" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "유용한 명령어:" -ForegroundColor Yellow
    Write-Host "  로그 확인:  docker-compose logs -f" -ForegroundColor White
    Write-Host "  중지:       docker-compose down" -ForegroundColor White
    Write-Host ""
}

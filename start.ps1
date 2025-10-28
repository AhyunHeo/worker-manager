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

# Step 1: 포트 포워딩 설정
Write-Host "[1/2] 포트 포워딩 설정 중..." -ForegroundColor Yellow
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

# Step 2: Docker Compose 실행
Write-Host "[2/2] Docker 서비스 시작 중..." -ForegroundColor Yellow

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
    Write-Host "  Web Dashboard:  http://192.168.0.88:5000" -ForegroundColor Cyan
    Write-Host "  API Server:     http://192.168.0.88:8090" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "유용한 명령어:" -ForegroundColor Yellow
    Write-Host "  로그 확인:  docker-compose logs -f" -ForegroundColor White
    Write-Host "  중지:       docker-compose down" -ForegroundColor White
    Write-Host ""
}

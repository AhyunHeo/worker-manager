# Worker Manager - Port Forwarding Setup
# Windows Firewall 규칙 추가 스크립트

# 관리자 권한 확인
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ 오류: 관리자 권한이 필요합니다!" -ForegroundColor Red
    Write-Host "   start.ps1 실행 시 UAC 프롬프트에서 '예'를 눌러주세요." -ForegroundColor Yellow
    throw "Administrator privileges required"
}

Write-Host "포트 포워딩 및 방화벽 규칙 설정 중..." -ForegroundColor Cyan

# 필요한 포트 정의 (VPN 제거, Worker Manager 서비스만)
$ports = @(
    @{Name="Worker-API"; Port=8091; Protocol="TCP"; Description="Worker Manager API Server"},
    @{Name="Worker-Dashboard"; Port=5000; Protocol="TCP"; Description="Worker Manager Web Dashboard"}
)

# 기존 규칙 삭제 (있는 경우)
foreach ($portConfig in $ports) {
    $ruleName = "Worker-Manager-$($portConfig.Name)"

    # 기존 규칙 확인 및 삭제
    $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($existingRule) {
        Write-Host "  - 기존 규칙 삭제: $ruleName" -ForegroundColor Yellow
        Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    }
}

# 새 방화벽 규칙 추가
foreach ($portConfig in $ports) {
    $ruleName = "Worker-Manager-$($portConfig.Name)"

    try {
        # Inbound 규칙 추가 (모든 프로파일에 적용: Domain, Private, Public)
        New-NetFirewallRule `
            -DisplayName $ruleName `
            -Direction Inbound `
            -Protocol $portConfig.Protocol `
            -LocalPort $portConfig.Port `
            -Action Allow `
            -Enabled True `
            -Profile Domain,Private,Public `
            -Description $portConfig.Description `
            -ErrorAction Stop | Out-Null

        Write-Host "  ✓ $($portConfig.Name): $($portConfig.Port)/$($portConfig.Protocol) (모든 네트워크)" -ForegroundColor Green

    } catch {
        Write-Host "  ✗ $($portConfig.Name): 실패 - $_" -ForegroundColor Red
        throw
    }
}

Write-Host "방화벽 규칙 설정 완료!" -ForegroundColor Green
Write-Host ""

# WSL2 포트 포워딩 설정 (Docker Desktop용)
Write-Host "WSL2 포트 포워딩 설정 중..." -ForegroundColor Cyan

# WSL2 IP 주소 가져오기
try {
    $wslIp = (wsl hostname -I).Trim()
    if ($wslIp) {
        Write-Host "  WSL2 IP: $wslIp" -ForegroundColor Gray

        # Windows 호스트 IP 가져오기
        $hostIp = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Ethernet*","Wi-Fi*" | Where-Object {$_.IPAddress -like "192.168.*"} | Select-Object -First 1).IPAddress

        if ($hostIp) {
            Write-Host "  호스트 IP: $hostIp" -ForegroundColor Gray

            # 각 포트에 대해 포트 포워딩 추가
            foreach ($portConfig in $ports) {
                # TCP 포트만 포워딩 (UDP는 netsh portproxy 미지원)
                if ($portConfig.Protocol -eq "TCP") {
                    # 기존 포워딩 삭제 (있는 경우)
                    netsh interface portproxy delete v4tov4 listenport=$($portConfig.Port) listenaddress=$hostIp 2>$null

                    # 새 포워딩 추가
                    netsh interface portproxy add v4tov4 `
                        listenport=$($portConfig.Port) `
                        listenaddress=$hostIp `
                        connectport=$($portConfig.Port) `
                        connectaddress=$wslIp | Out-Null

                    Write-Host "  ✓ $hostIp`:$($portConfig.Port) -> WSL2:$($portConfig.Port)" -ForegroundColor Green
                }
            }
        } else {
            Write-Host "  ⚠ 호스트 IP를 찾을 수 없습니다 (포트 포워딩 건너뜀)" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "  ⚠ WSL2 포트 포워딩 설정 실패 (WSL2 미사용 시 무시)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "포트 포워딩 설정 완료!" -ForegroundColor Green
Write-Host ""

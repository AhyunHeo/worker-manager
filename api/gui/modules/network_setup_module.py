"""
Network Setup Module
네트워크 설정 및 포트 포워딩 관련 모든 로직
"""

def get_network_setup_function(worker_ip: str) -> str:
    """네트워크 설정 및 포트 포워딩 함수 반환"""

    return """
# Worker IP 확인 함수 (VPN 제거됨 - 간소화)
function Test-WorkerIPConnection {
    param(
        [Parameter(Mandatory=$true)]
        [string]$WorkerIP
    )

    try {
        Write-Host "[DEBUG] Checking Worker IP: $WorkerIP"

        # Worker IP가 유효한 LAN IP 형식인지 확인
        if ($WorkerIP -match '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$') {
            Write-Host "[DEBUG] Worker IP format is valid"

            # 간단한 핑 테스트 (선택적)
            $pingTest = Test-Connection -ComputerName $WorkerIP -Count 1 -Quiet -ErrorAction SilentlyContinue
            if ($pingTest) {
                Write-Host "[SUCCESS] Worker IP is reachable"
                return @{
                    Connected = $true
                    ServiceRunning = $true
                    InterfaceExists = $true
                    Message = "워커 IP가 정상적으로 연결되어 있습니다."
                }
            } else {
                Write-Host "[INFO] Worker IP ping test failed (may be normal)"
                # 핑이 실패해도 연결된 것으로 간주 (방화벽 등의 이유로 핑이 막힐 수 있음)
                return @{
                    Connected = $true
                    ServiceRunning = $true
                    InterfaceExists = $true
                    Message = "워커 IP가 설정되었습니다 (핑 실패는 정상일 수 있음)."
                }
            }
        } else {
            Write-Host "[ERROR] Invalid Worker IP format: $WorkerIP"
            return @{
                Connected = $false
                ServiceRunning = $false
                InterfaceExists = $false
                Message = "유효하지 않은 워커 IP 형식입니다: $WorkerIP"
            }
        }

    } catch {
        Write-Host "[ERROR] Test-WorkerIPConnection failed: $_"
        return @{
            Connected = $false
            ServiceRunning = $false
            InterfaceExists = $false
            Message = "워커 IP 확인 중 오류 발생: $_"
        }
    }
}

# WSL2 IP 주소 가져오기 함수
function Get-WSL2IPAddress {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DistroName
    )
    
    try {
        Write-Host "[DEBUG] Getting WSL2 IP address for distro: $DistroName"
        
        # UTF-8 인코딩 설정
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $OutputEncoding = [System.Text.Encoding]::UTF8
        $env:WSL_UTF8 = 1
        
        # 배포판 이름 표준화 및 확인
        Write-Host "[DEBUG] Checking for distro: $DistroName"
        
        # 주어진 배포판 이름이 작동하는지 확인
        $originalDistroWorks = $false
        if ($DistroName) {
            $testOriginal = wsl -d $DistroName -- echo "test" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $originalDistroWorks = $true
                Write-Host "[DEBUG] Original distro name works: $DistroName"
            }
        }
        
        if (-not $originalDistroWorks) {
            # 표준 이름들 시도
            $standardNames = @("Ubuntu-22.04", "Ubuntu", "Ubuntu-20.04", "Ubuntu-24.04")
            foreach ($name in $standardNames) {
                Write-Host "[DEBUG] Testing $name..."
                $testResult = wsl -d $name -- echo "test" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $DistroName = $name
                    Write-Host "[DEBUG] Found working distro: $DistroName"
                    break
                }
            }
        }
        
        # 여전히 못 찾았으면 목록에서 검색
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[DEBUG] Searching in WSL list..."
            $distros = @()
            
            # wsl.exe를 직접 실행하여 UTF-8 처리
            $wslExe = "$env:SystemRoot\System32\wsl.exe"
            $wslOutput = & $wslExe -l -q 2>$null
            
            foreach ($line in $wslOutput) {
                # BOM 및 특수 문자 제거
                $cleanLine = $line.Trim()
                $cleanLine = $cleanLine -replace '^\xEF\xBB\xBF', ''
                $cleanLine = $cleanLine -replace '[^\x20-\x7E]', ''
                
                if ($cleanLine -and $cleanLine -ne '' -and $cleanLine -notmatch 'docker-desktop') {
                    Write-Host "[DEBUG] Testing distro from list: $cleanLine"
                    $testDistro = wsl -d $cleanLine -- echo "test" 2>$null
                    if ($LASTEXITCODE -eq 0) {
                        $distros += $cleanLine
                        if ($cleanLine -match "Ubuntu") {
                            $DistroName = $cleanLine
                            Write-Host "[DEBUG] Selected Ubuntu variant: $DistroName"
                            break
                        }
                    }
                }
            }
            
            # Ubuntu가 없으면 첫 번째 사용 가능한 배포판 사용
            if (-not $DistroName -and $distros.Count -gt 0) {
                $DistroName = $distros[0]
                Write-Host "[DEBUG] Using first available distro: $DistroName"
            }
        }
        
        if (-not $DistroName) {
            Write-Host "[ERROR] No working Linux distro found"
            return @{
                Success = $false
                IPAddress = $null
                Message = "Ubuntu 배포판을 찾을 수 없습니다."
            }
        }
        
        # WSL2 내부 IP 주소 가져오기
        Write-Host "[DEBUG] Getting IP address from $DistroName"
        
        # 먼저 배포판이 실행 가능한지 확인
        $testDistro = wsl -d $DistroName -- echo "test" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Cannot access distro $DistroName`: $testDistro"
            return @{
                Success = $false
                IPAddress = $null
                Message = "$DistroName 배포판에 접근할 수 없습니다: $testDistro"
            }
        }
        
        $wslIP = wsl -d $DistroName -- bash -c "ip addr show eth0 2>/dev/null | grep 'inet ' | cut -d' ' -f6 | cut -d/ -f1" 2>$null
        
        if ([string]::IsNullOrWhiteSpace($wslIP)) {
            Write-Host "[WARNING] Could not get WSL2 IP from eth0, trying alternative method"
            
            # 대체 방법: hostname -I 사용
            $wslIP = wsl -d $DistroName -- hostname -I 2>$null
            if ($wslIP) {
                $wslIP = $wslIP.Trim().Split(' ')[0]
            }
        }
        
        if ([string]::IsNullOrWhiteSpace($wslIP)) {
            Write-Host "[ERROR] Failed to get WSL2 IP address"
            return @{
                Success = $false
                IPAddress = $null
                Message = "WSL2 IP 주소를 가져올 수 없습니다."
            }
        }
        
        Write-Host "[DEBUG] WSL2 IP address: $wslIP"
        return @{
            Success = $true
            IPAddress = $wslIP.Trim()
            Message = "WSL2 IP 주소를 성공적으로 가져왔습니다."
        }
        
    } catch {
        Write-Host "[ERROR] Get-WSL2IPAddress failed: $_"
        return @{
            Success = $false
            IPAddress = $null
            Message = "WSL2 IP 주소 가져오기 중 오류 발생: $_"
        }
    }
}

# 포트 포워딩 설정 함수
function Setup-PortForwarding {
    param(
        [Parameter(Mandatory=$true)]
        [string]$WorkerIP,
        [Parameter(Mandatory=$true)]
        [string]$WslIP,
        [Parameter(Mandatory=$false)]
        # Ray 및 DDP 포트 포함: 6379(GCS), 10001(Client), 8265(Dashboard), 11000-11049(Worker), 29500-29509(DDP)
        [int[]]$Ports = @(
            3030, 6006, 6007,  # 일반 서비스 (3000 제외 - 중앙 플랫폼 포트)
            6379, 10001, 8265, 8076, 8077,  # Ray Core (GCS, Client, Dashboard, ObjectManager, NodeManager)
            7860, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089,  # 웹 서비스 (8091 제외 - 워커 매니저 포트)
            8888, 9090,  # Jupyter, Prometheus
            8001,  # Flask Worker API
            29500, 29501, 29502, 29503, 29504, 29505, 29506, 29507, 29508, 29509,  # DDP TCPStore
            11000, 11001, 11002, 11003, 11004, 11005, 11006, 11007, 11008, 11009,  # Ray Workers (일부)
            11434  # Ollama
        )
    )
    
    try {
        Write-Host "[DEBUG] Setting up port forwarding from VPN IP ($WorkerIP) to WSL2 IP ($WslIP)"
        
        $successCount = 0
        $failCount = 0
        
        foreach ($port in $Ports) {
            # 기존 규칙 제거
            $existingRule = netsh interface portproxy show v4tov4 | Select-String "$WorkerIP\\s+$port"
            if ($existingRule) {
                Write-Host "[DEBUG] Removing existing rule for port $port"
                netsh interface portproxy delete v4tov4 listenport=$port listenaddress=$WorkerIP 2>$null | Out-Null
            }
            
            # WSL IP 대상 결정 (특별 처리가 필요한 포트들)
            $targetIP = $WslIP
            
            # 새 규칙 추가
            Write-Host "[DEBUG] Adding port forwarding rule: $WorkerIP`:$port -> $targetIP`:$port"
            $result = netsh interface portproxy add v4tov4 listenport=$port listenaddress=$WorkerIP connectport=$port connectaddress=$targetIP 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                $successCount++
            } else {
                Write-Host "[WARNING] Failed to add rule for port $port`: $result"
                $failCount++
            }
        }
        
        # Ray 워커 포트 범위 (11000-11049) 추가 - 범위가 큰 경우 개별 처리
        Write-Host "[DEBUG] Adding Ray worker port range (11010-11049)..."
        for ($port = 11010; $port -le 11049; $port++) {
            # 기존 규칙 제거
            netsh interface portproxy delete v4tov4 listenport=$port listenaddress=$WorkerIP 2>$null | Out-Null
            
            # 새 규칙 추가 (에러 출력 억제)
            $result = netsh interface portproxy add v4tov4 listenport=$port listenaddress=$WorkerIP connectport=$port connectaddress=$WslIP 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                $successCount++
            } else {
                $failCount++
            }
        }
        
        Write-Host "[DEBUG] Port forwarding setup complete. Success: $successCount, Failed: $failCount"
        
        # 포트 포워딩 검증 (특히 Ray 포트들)
        Write-Host "[DEBUG] Verifying critical port forwarding rules..."
        $criticalPorts = @(6379, 10001, 29500, 8001)  # Ray GCS, Client, DDP, Flask
        
        foreach ($port in $criticalPorts) {
            $rule = netsh interface portproxy show v4tov4 | Select-String "$WorkerIP\s+$port\s+$WslIP\s+$port"
            if ($rule) {
                Write-Host "[SUCCESS] Port $port`: $WorkerIP`:$port -> $WslIP`:$port ✓"
            } else {
                Write-Host "[WARNING] Port $port forwarding not properly configured"
                # 재시도
                Write-Host "[DEBUG] Retrying port $port..."
                netsh interface portproxy delete v4tov4 listenport=$port listenaddress=$WorkerIP 2>$null | Out-Null
                netsh interface portproxy add v4tov4 listenport=$port listenaddress=$WorkerIP connectport=$port connectaddress=$WslIP 2>&1 | Out-Null
            }
        }
        
        # Windows Firewall 규칙 추가
        Write-Host "[DEBUG] Configuring Windows Firewall rules"
        
        # WSL 인바운드 규칙
        $firewallRuleName = "WSL2 VPN Port Forwarding - $WorkerIP"
        Remove-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue
        $firewallResult = New-NetFirewallRule -DisplayName $firewallRuleName `
            -Direction Inbound `
            -Protocol TCP `
            -LocalAddress $WorkerIP `
            -LocalPort $Ports `
            -Action Allow `
            -Profile Any `
            -ErrorAction SilentlyContinue
        
        if ($firewallResult) {
            Write-Host "[DEBUG] Firewall rule added successfully"
        } else {
            Write-Host "[WARNING] Failed to add firewall rule"
        }
        
        # Ray 분산학습 전용 방화벽 규칙 추가
        $rayFirewallRuleName = "Ray Distributed Training - $WorkerIP"
        Remove-NetFirewallRule -DisplayName $rayFirewallRuleName -ErrorAction SilentlyContinue
        
        # Ray 워커 포트 범위 (11000-11049) 및 DDP 포트 (29500-29509)
        $rayWorkerPorts = 11000..11049
        $ddpPorts = 29500..29509
        
        # Ray 워커 포트용 방화벽 규칙
        $rayFirewallResult = New-NetFirewallRule -DisplayName $rayFirewallRuleName `
            -Direction Inbound `
            -Protocol TCP `
            -LocalAddress $WorkerIP `
            -LocalPort $rayWorkerPorts `
            -Action Allow `
            -Profile Any `
            -Description "Ray distributed training worker ports" `
            -ErrorAction SilentlyContinue
        
        # DDP 포트용 방화벽 규칙 추가
        $ddpFirewallRuleName = "DDP Training - $WorkerIP"
        Remove-NetFirewallRule -DisplayName $ddpFirewallRuleName -ErrorAction SilentlyContinue
        
        $ddpFirewallResult = New-NetFirewallRule -DisplayName $ddpFirewallRuleName `
            -Direction Inbound `
            -Protocol TCP `
            -LocalAddress $WorkerIP `
            -LocalPort $ddpPorts `
            -Action Allow `
            -Profile Any `
            -Description "PyTorch DDP training ports" `
            -ErrorAction SilentlyContinue
        
        if ($rayFirewallResult) {
            Write-Host "[DEBUG] Ray firewall rule added successfully (ports 11000-11049)"
        } else {
            Write-Host "[WARNING] Failed to add Ray firewall rule"
        }
        
        # 설정 확인
        $activeRules = netsh interface portproxy show v4tov4 | Select-String $WorkerIP
        $activeCount = ($activeRules | Measure-Object).Count
        
        if ($activeCount -gt 0) {
            Write-Host "[DEBUG] Total active port forwarding rules: $activeCount"
            return @{
                Success = $true
                SuccessCount = $successCount
                FailCount = $failCount
                TotalActive = $activeCount
                Message = "포트 포워딩이 설정되었습니다. (성공: $successCount, 실패: $failCount)"
            }
        } else {
            Write-Host "[ERROR] No active port forwarding rules"
            return @{
                Success = $false
                SuccessCount = $successCount
                FailCount = $failCount
                TotalActive = 0
                Message = "포트 포워딩 규칙을 생성할 수 없습니다."
            }
        }
        
    } catch {
        Write-Host "[ERROR] Setup-PortForwarding failed: $_"
        return @{
            Success = $false
            SuccessCount = 0
            FailCount = $($Ports.Count)
            TotalActive = 0
            Message = "포트 포워딩 설정 중 오류 발생: $_"
        }
    }
}

# 포트 포워딩 제거 함수
function Remove-PortForwarding {
    param(
        [Parameter(Mandatory=$true)]
        [string]$WorkerIP
    )
    
    try {
        Write-Host "[DEBUG] Removing port forwarding rules for VPN IP: $WorkerIP"
        
        # 모든 포트 포워딩 규칙 가져오기
        $rules = netsh interface portproxy show v4tov4 | Select-String $WorkerIP
        $count = 0
        
        foreach ($rule in $rules) {
            if ($rule -match "$WorkerIP\\s+(\\d+)") {
                $port = $matches[1]
                Write-Host "[DEBUG] Removing rule for port $port"
                netsh interface portproxy delete v4tov4 listenport=$port listenaddress=$WorkerIP 2>$null | Out-Null
                $count++
            }
        }
        
        # Firewall 규칙 제거
        $firewallRuleName = "WSL2 VPN Port Forwarding - $WorkerIP"
        Remove-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue
        
        # Ray 방화벽 규칙도 제거
        $rayFirewallRuleName = "Ray Distributed Training - $WorkerIP"
        Remove-NetFirewallRule -DisplayName $rayFirewallRuleName -ErrorAction SilentlyContinue
        
        Write-Host "[DEBUG] Removed $count port forwarding rules"
        return @{
            Success = $true
            RulesRemoved = $count
            Message = "$count개의 포트 포워딩 규칙이 제거되었습니다."
        }
        
    } catch {
        Write-Host "[ERROR] Remove-PortForwarding failed: $_"
        return @{
            Success = $false
            RulesRemoved = 0
            Message = "포트 포워딩 제거 중 오류 발생: $_"
        }
    }
}

# 포트 포워딩 업데이트 함수 (기존 규칙 수정용)
function Update-PortForwarding {
    param(
        [Parameter(Mandatory=$true)]
        [string]$WorkerIP,
        [Parameter(Mandatory=$true)]
        [string]$WslIP
    )
    
    try {
        Write-Host "[DEBUG] Updating existing port forwarding rules..."
        
        # 현재 설정된 모든 포트 포워딩 규칙 가져오기
        $existingRules = netsh interface portproxy show v4tov4
        $updatedCount = 0
        
        # Ray 및 DDP 관련 중요 포트들
        $criticalPorts = @(6379, 10001, 8265, 8076, 8077, 29500, 29501, 29502, 29503, 8001)
        
        foreach ($port in $criticalPorts) {
            # 기존 규칙이 잘못된 대상을 가리키는지 확인
            $wrongRule = $existingRules | Select-String "$WorkerIP\s+$port\s+(?!$WslIP)"
            
            if ($wrongRule) {
                Write-Host "[DEBUG] Fixing port $port forwarding (was pointing to wrong IP)"
                # 기존 규칙 삭제
                netsh interface portproxy delete v4tov4 listenport=$port listenaddress=$WorkerIP 2>$null | Out-Null
                # 올바른 규칙 추가
                netsh interface portproxy add v4tov4 listenport=$port listenaddress=$WorkerIP connectport=$port connectaddress=$WslIP 2>&1 | Out-Null
                $updatedCount++
            }
        }
        
        Write-Host "[DEBUG] Updated $updatedCount port forwarding rules"
        
        return @{
            Success = $true
            UpdatedCount = $updatedCount
            Message = "$updatedCount개의 포트 포워딩 규칙이 업데이트되었습니다."
        }
        
    } catch {
        Write-Host "[ERROR] Update-PortForwarding failed: $_"
        return @{
            Success = $false
            UpdatedCount = 0
            Message = "포트 포워딩 업데이트 중 오류 발생: $_"
        }
    }
}

# Windows 호스트의 실제 LAN IP 감지 함수
function Get-WindowsLANIP {
    try {
        Write-Host "[DEBUG] Detecting Windows host LAN IP address..."

        # 방법 1: Get-NetIPAddress로 Ethernet/Wi-Fi 어댑터의 192.168.x.x IP 조회
        # Docker(172.16-31.x.x), WSL2(192.168.65.x), VPN(10.x.x.x) 대역 제외
        $lanIP = (Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object {
                $_.InterfaceAlias -match 'Ethernet|Wi-Fi|이더넷|무선' -and
                $_.IPAddress -match '^192\.168\.' -and
                $_.IPAddress -notmatch '^192\.168\.65\.' -and
                $_.IPAddress -notmatch '^172\.(1[6-9]|2[0-9]|3[0-1])\.' -and
                $_.IPAddress -notmatch '^10\.' -and
                ($_.PrefixOrigin -eq 'Dhcp' -or $_.PrefixOrigin -eq 'Manual')
            } |
            Select-Object -First 1).IPAddress

        if ($lanIP) {
            Write-Host "[SUCCESS] Windows LAN IP detected: $lanIP"
            return @{
                Success = $true
                LANIP = $lanIP
                Message = "Windows LAN IP를 성공적으로 감지했습니다: $lanIP"
            }
        }

        # 방법 2: ipconfig으로 재시도 (Get-NetIPAddress 실패 시)
        Write-Host "[DEBUG] Trying ipconfig method..."
        $ipconfigOutput = ipconfig | Out-String

        # IPv4 주소 중 192.168로 시작하는 것 찾기 (Docker/WSL2/VPN 대역 제외)
        if ($ipconfigOutput -match 'IPv4.*?:\s*(192\.168\.\d{1,3}\.\d{1,3})') {
            $lanIP = $matches[1]
            # Docker(172.16-31.x.x), WSL2(192.168.65.x), VPN(10.x.x.x) 제외
            if ($lanIP -notmatch '^192\.168\.65\.' -and
                $lanIP -notmatch '^172\.(1[6-9]|2[0-9]|3[0-1])\.' -and
                $lanIP -notmatch '^10\.') {
                Write-Host "[SUCCESS] Windows LAN IP detected (ipconfig): $lanIP"
                return @{
                    Success = $true
                    LANIP = $lanIP
                    Message = "Windows LAN IP를 성공적으로 감지했습니다: $lanIP"
                }
            }
        }

        # 방법 3: 기본 게이트웨이 인터페이스에서 IP 찾기
        Write-Host "[DEBUG] Trying default gateway interface method..."
        $defaultInterface = Get-NetRoute -DestinationPrefix 0.0.0.0/0 |
            Select-Object -First 1 -ExpandProperty InterfaceIndex

        if ($defaultInterface) {
            $lanIP = (Get-NetIPAddress -InterfaceIndex $defaultInterface -AddressFamily IPv4 |
                Where-Object {
                    $_.IPAddress -match '^192\.168\.' -and
                    $_.IPAddress -notmatch '^192\.168\.65\.' -and
                    $_.IPAddress -notmatch '^172\.(1[6-9]|2[0-9]|3[0-1])\.' -and
                    $_.IPAddress -notmatch '^10\.'
                } |
                Select-Object -First 1).IPAddress

            if ($lanIP) {
                Write-Host "[SUCCESS] Windows LAN IP detected (gateway interface): $lanIP"
                return @{
                    Success = $true
                    LANIP = $lanIP
                    Message = "Windows LAN IP를 성공적으로 감지했습니다: $lanIP"
                }
            }
        }

        Write-Host "[ERROR] Could not detect Windows LAN IP"
        return @{
            Success = $false
            LANIP = $null
            Message = "Windows LAN IP를 감지할 수 없습니다."
        }

    } catch {
        Write-Host "[ERROR] Get-WindowsLANIP failed: $_"
        return @{
            Success = $false
            LANIP = $null
            Message = "Windows LAN IP 감지 중 오류 발생: $_"
        }
    }
}

# 네트워크 연결 테스트 함수
function Test-NetworkConnectivity {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DistroName,
        [Parameter(Mandatory=$false)]
        [string]$TestHost = "8.8.8.8"
    )

    try {
        Write-Host "[DEBUG] Testing network connectivity from WSL"

        # 배포판 이름 확인
        Write-Host "[DEBUG] Testing network connectivity from $DistroName"

        # 기본 연결 테스트
        $pingResult = wsl -d $DistroName -- ping -c 1 -W 2 $TestHost 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[DEBUG] Network connectivity test successful"

            # DNS 테스트 (nslookup이 없을 수 있으므로 getent 사용)
            $dnsResult = wsl -d $DistroName -- bash -c "getent hosts google.com || host google.com || nslookup google.com" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[DEBUG] DNS resolution working"
                return @{
                    Success = $true
                    InternetAccess = $true
                    DNSWorking = $true
                    Message = "네트워크 연결이 정상입니다."
                }
            } else {
                Write-Host "[WARNING] DNS resolution failed"
                return @{
                    Success = $true
                    InternetAccess = $true
                    DNSWorking = $false
                    Message = "인터넷 연결은 되지만 DNS 해석에 문제가 있습니다."
                }
            }
        } else {
            Write-Host "[ERROR] Network connectivity test failed"
            return @{
                Success = $false
                InternetAccess = $false
                DNSWorking = $false
                Message = "네트워크 연결을 확인할 수 없습니다."
            }
        }

    } catch {
        Write-Host "[ERROR] Test-NetworkConnectivity failed: $_"
        return @{
            Success = $false
            InternetAccess = $false
            DNSWorking = $false
            Message = "네트워크 테스트 중 오류 발생: $_"
        }
    }
}
"""
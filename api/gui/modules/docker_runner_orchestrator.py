"""
Docker Runner Orchestrator - 간소화된 버전
WSL2 → Ubuntu → Docker → Container 직관적인 설치 흐름
"""

from .wsl_setup_module import get_wsl_setup_function
from .ubuntu_setup_module import get_ubuntu_setup_function
from .docker_setup_module import get_docker_setup_function
from .network_setup_module import get_network_setup_function
from .container_deploy_module import get_container_deploy_function

def get_docker_runner_orchestrator(server_ip: str, node_id: str, worker_ip: str, central_ip: str, metadata: dict, lan_ip: str = None) -> str:
    """간소화된 Docker 설치 흐름 - WSL2 → Ubuntu → Docker → Container"""

    # 각 모듈에서 함수 가져오기
    wsl_setup = get_wsl_setup_function()
    ubuntu_setup = get_ubuntu_setup_function(worker_ip)
    docker_setup = get_docker_setup_function()
    network_setup = get_network_setup_function(worker_ip)
    container_deploy = get_container_deploy_function(node_id, worker_ip, central_ip, metadata, lan_ip)
    
    return f"""
# 간소화된 Docker Runner 설치 - 직관적인 WSL2 → Ubuntu → Docker 흐름
function Install-DockerRunner {{
    try {{
        # Windows Forms 어셈블리 로드 (이미 로드된 경우 무시)
        try {{
            Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
        }} catch {{
            # 이미 로드된 경우 무시
        }}
        
        $global:NODE_ID = '{node_id}'
        $global:WORKER_IP = '{worker_ip}'
        $global:CENTRAL_IP = '{central_ip}'
        $global:SERVER_IP = '{server_ip}'
        
        # 모든 모듈 함수 로드
        {wsl_setup}
        {ubuntu_setup}
        {docker_setup}
        {network_setup}
        {container_deploy}
        
        # ============================================
        # Step 1: WSL2 설치 확인 (필수)
        # ============================================
        Update-Progress 'Step 1/5: WSL2 환경 확인 및 설치' 20
        
        Write-Host "[INFO] Checking WSL2 installation..."
        
        # GUI 응답성 유지
        [System.Windows.Forms.Application]::DoEvents()
        
        $wslResult = Setup-WSL2
        
        # GUI 응답성 유지
        [System.Windows.Forms.Application]::DoEvents()
        
        if ($wslResult -and $wslResult.NeedsReboot) {{
            Update-Progress 'WSL2 설치를 위해 재시작이 필요합니다.' 25
            $rebootChoice = [System.Windows.Forms.MessageBox]::Show(
                "WSL2 설치를 위해 시스템 재시작이 필요합니다.`n`n지금 재시작하시겠습니까?",
                "시스템 재시작 필요",
                [System.Windows.Forms.MessageBoxButtons]::YesNo,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            )
            
            if ($rebootChoice -eq 'Yes') {{
                Start-Process -FilePath "shutdown.exe" -ArgumentList "/r /t 3"
                if ($form) {{ $form.Close() }}
                exit
            }}
            return $false
        }} elseif ($wslResult -and -not $wslResult.Success) {{
            Update-Progress "WSL2 설치 실패: $($wslResult.Message)" 25
            [System.Windows.Forms.MessageBox]::Show(
                "WSL2 설치에 실패했습니다.`n`n$($wslResult.Message)",
                "WSL2 설치 실패",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Error
            )
            return $false
        }}
        
        Update-Progress '✓ WSL2가 준비되었습니다.' 30

        # ============================================
        # Windows LAN IP 감지 (Ray 분산학습용)
        # ============================================
        Write-Host "[INFO] Detecting Windows host LAN IP for distributed training..."

        $lanIPResult = Get-WindowsLANIP
        $global:LAN_IP = $null

        if ($lanIPResult.Success) {{
            $global:LAN_IP = $lanIPResult.LANIP
            Write-Host "[SUCCESS] Windows LAN IP detected: $($global:LAN_IP)"
            Write-Host "[INFO] This IP will be used for Ray distributed training connections"
        }} else {{
            Write-Host "[WARNING] Could not detect Windows LAN IP: $($lanIPResult.Message)"
            Write-Host "[INFO] Will use VPN IP ($($global:VPN_IP)) as fallback"
            $global:LAN_IP = $global:VPN_IP
        }}

        # ============================================
        # Step 2: Ubuntu 설치 (NVIDIA Container Toolkit 필수)
        # ============================================
        Update-Progress 'Step 2/5: Ubuntu 배포판 설치 (NVIDIA 지원 필수)' 35
        
        Write-Host "[INFO] Installing Ubuntu for NVIDIA Container Toolkit support..."
        
        # GUI 응답성 유지
        [System.Windows.Forms.Application]::DoEvents()
        
        $ubuntuResult = Setup-Ubuntu
        
        # GUI 응답성 유지
        [System.Windows.Forms.Application]::DoEvents()
        
        $distroName = $null
        if (-not $ubuntuResult.Success) {{
            Update-Progress "Ubuntu 설치 확인 중..." 40
            
            # Ubuntu 찾기 시도
            $standardNames = @("Ubuntu-22.04", "Ubuntu", "Ubuntu-20.04", "Ubuntu-24.04")
            
            foreach ($name in $standardNames) {{
                $testResult = wsl -d $name -- echo "test" 2>$null
                if ($LASTEXITCODE -eq 0) {{
                    $distroName = $name
                    Write-Host "[INFO] Found Ubuntu: $distroName"
                    break
                }}
            }}
            
            if (-not $distroName) {{
                Update-Progress "Ubuntu가 설치되지 않았습니다. 자동 설치를 시작합니다..." 40
                Write-Host "[INFO] Ubuntu not found, installing Ubuntu-22.04..."
                
                # Ubuntu 22.04 자동 설치
                wsl --install -d Ubuntu-22.04 --no-launch 2>&1 | Out-Null
                
                # GUI 응답성 유지
                for ($i = 0; $i -lt 5; $i++) {{
                    Start-Sleep -Seconds 1
                    [System.Windows.Forms.Application]::DoEvents()
                }}
                
                # 재확인
                $testResult = wsl -d Ubuntu-22.04 -- echo "test" 2>$null
                if ($LASTEXITCODE -eq 0) {{
                    $distroName = "Ubuntu-22.04"
                }} else {{
                    # 추가 복구 시도
                    Write-Host "[WARNING] Ubuntu 설치 실패, 복구 시도 중..."
                    
                    # WSL 재시작
                    wsl --shutdown 2>$null
                    
                    # GUI 응답성 유지
                    for ($i = 0; $i -lt 5; $i++) {{
                        Start-Sleep -Seconds 1
                        [System.Windows.Forms.Application]::DoEvents()
                    }}
                    
                    # wsl -l -v로 실제 설치 확인
                    $wslListVerbose = wsl -l -v 2>$null
                    $ubuntuFound = $false
                    foreach ($line in $wslListVerbose) {{
                        if ($line -match "Ubuntu") {{
                            Write-Host "[INFO] Ubuntu가 목록에 있음: $line"
                            $ubuntuFound = $true
                            
                            # 패턴 매칭으로 배포판 이름 추출
                            # 라인의 첫 번째 단어 추출 (WSL 배포판 이름)
                            $lineWords = $line.Trim() -split ' +'
                            if ($lineWords.Count -gt 0) {{
                                $extractedName = $lineWords[0]
                                Write-Host "[INFO] 추출된 배포판 이름: $extractedName"
                                
                                # 테스트
                                $testCmd = wsl -d $extractedName -- echo "test" 2>$null
                                if ($LASTEXITCODE -eq 0) {{
                                    $distroName = $extractedName
                                    Write-Host "[SUCCESS] Ubuntu 복구 성공: $distroName"
                                    break
                                }}
                            }}
                        }}
                    }}
                    
                    # 여전히 실패하면 에러 메시지
                    if (-not $distroName) {{
                        Update-Progress "Ubuntu 설치 실패" 40
                        [System.Windows.Forms.MessageBox]::Show(
                            "Ubuntu 설치에 실패했습니다.`n`nNVIDIA Container Toolkit 지원을 위해 Ubuntu가 필요합니다.",
                            "Ubuntu 설치 실패",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Error
                        )
                        return $false
                    }}
                }}
            }}
        }} else {{
            $distroName = $ubuntuResult.DistroName
        }}
        
        # distroName 정리 (괄호, 특수문자 제거)
        if ($distroName) {{
            $cleanDistroName = $distroName -replace '\\(.*?\\)', '' -replace '[^\\w\\d\\.-]', ''
            $cleanDistroName = $cleanDistroName.Trim()
            
            # 표준 이름으로 정리
            if ($cleanDistroName -match "Ubuntu-?22\\.?04") {{
                $distroName = "Ubuntu-22.04"
            }} elseif ($cleanDistroName -eq "Ubuntu") {{
                $distroName = "Ubuntu"
            }} else {{
                $distroName = $cleanDistroName
            }}
        }}
        
        Update-Progress "✓ Ubuntu 준비 완료: $distroName" 45
        
        # Ubuntu 사용자 설정 (GUI 입력 필수)
        if ($distroName) {{
            Update-Progress 'Ubuntu 사용자 설정 중...' 50
            $currentUser = wsl -d $distroName -- whoami 2>$null
            
            if ($currentUser -eq "root" -or [string]::IsNullOrEmpty($currentUser)) {{
                # 사용자 계정 생성 - 무조건 GUI 입력 받기
                Update-Progress 'Ubuntu 사용자 계정 생성 중...' 50
                Write-Host "[INFO] Ubuntu 사용자 계정 생성 필요 - GUI 입력 대기..."
                
                # Initialize-UbuntuUser 함수 호출 (GUI 입력 포함)
                $initResult = Initialize-UbuntuUser -DistroName $distroName
                if ($initResult.Success) {{
                    $global:WSLUsername = $initResult.Username
                    Update-Progress "✓ Ubuntu 사용자 생성 완료: $($initResult.Username)" 55
                }} else {{
                    Write-Host "[ERROR] Ubuntu 사용자 생성 취소됨"
                    Update-Progress "Ubuntu 사용자 설정 실패" 55
                    
                    # 사용자가 취소한 경우 설치 중단
                    [System.Windows.Forms.MessageBox]::Show(
                        "Ubuntu 사용자 계정 생성이 취소되었습니다.`n`n설치를 계속할 수 없습니다.",
                        "설치 취소",
                        [System.Windows.Forms.MessageBoxButtons]::OK,
                        [System.Windows.Forms.MessageBoxIcon]::Warning
                    )
                    return $false
                }}
            }} else {{
                $global:WSLUsername = $currentUser
                Update-Progress "✓ 기존 사용자 사용: $currentUser" 55
                
                # 비밀번호 입력 GUI (최대 5번 시도) - 마스킹 지원
                Add-Type -AssemblyName System.Windows.Forms
                Add-Type -AssemblyName System.Drawing
                
                # 비밀번호 입력 함수
                function Get-PasswordInput {{
                    param(
                        [string]$Message,
                        [string]$Title
                    )
                    
                    $form = New-Object System.Windows.Forms.Form
                    $form.Text = $Title
                    $form.Size = New-Object System.Drawing.Size(450, 200)
                    $form.StartPosition = "CenterScreen"
                    $form.FormBorderStyle = "FixedDialog"
                    $form.MaximizeBox = $false
                    $form.MinimizeBox = $false
                    $form.TopMost = $true
                    
                    # 메시지 레이블
                    $label = New-Object System.Windows.Forms.Label
                    $label.Location = New-Object System.Drawing.Point(10, 15)
                    $label.Size = New-Object System.Drawing.Size(420, 60)
                    $label.Text = $Message
                    $form.Controls.Add($label)
                    
                    # 비밀번호 입력 텍스트박스 (마스킹)
                    $textBox = New-Object System.Windows.Forms.TextBox
                    $textBox.Location = New-Object System.Drawing.Point(10, 85)
                    $textBox.Size = New-Object System.Drawing.Size(420, 25)
                    $textBox.PasswordChar = '*'
                    $textBox.Font = New-Object System.Drawing.Font("Segoe UI", 10)
                    $form.Controls.Add($textBox)
                    
                    # OK 버튼
                    $okButton = New-Object System.Windows.Forms.Button
                    $okButton.Location = New-Object System.Drawing.Point(260, 120)
                    $okButton.Size = New-Object System.Drawing.Size(80, 30)
                    $okButton.Text = "확인"
                    $okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
                    $form.AcceptButton = $okButton
                    $form.Controls.Add($okButton)
                    
                    # Cancel 버튼
                    $cancelButton = New-Object System.Windows.Forms.Button
                    $cancelButton.Location = New-Object System.Drawing.Point(350, 120)
                    $cancelButton.Size = New-Object System.Drawing.Size(80, 30)
                    $cancelButton.Text = "취소"
                    $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
                    $form.CancelButton = $cancelButton
                    $form.Controls.Add($cancelButton)
                    
                    # 포커스 설정
                    $form.Add_Shown({{ $textBox.Select() }})
                    
                    $result = $form.ShowDialog()
                    
                    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
                        return $textBox.Text
                    }}
                    return $null
                }}
                
                $maxAttempts = 5
                $attemptCount = 0
                $passwordSuccess = $false
                
                while ($attemptCount -lt $maxAttempts -and -not $passwordSuccess) {{
                    $attemptCount++
                    
                    # 남은 시도 횟수 표시
                    $attemptsRemaining = $maxAttempts - $attemptCount + 1
                    $promptMessage = "Ubuntu 사용자 '$currentUser'의 sudo 비밀번호를 입력하세요.`n`n"
                    $promptMessage += "이 비밀번호는 Docker 설치 권한을 위해 필요합니다."
                    if ($attemptCount -gt 1) {{
                        $promptMessage += "`n`n⚠️ 비밀번호가 틀렸습니다. 남은 시도 횟수: $attemptsRemaining회"
                    }}
                    
                    $password = Get-PasswordInput -Message $promptMessage -Title "Ubuntu 사용자 비밀번호 (시도 $attemptCount/$maxAttempts)"
                    
                    if ([string]::IsNullOrWhiteSpace($password)) {{
                        # 사용자가 취소한 경우
                        Update-Progress "비밀번호 입력이 취소되었습니다." 55
                        $cancelChoice = [System.Windows.Forms.MessageBox]::Show(
                            "비밀번호 입력을 취소하시겠습니까?`n`n취소하면 설치를 계속할 수 없습니다.",
                            "입력 취소 확인",
                            [System.Windows.Forms.MessageBoxButtons]::YesNo,
                            [System.Windows.Forms.MessageBoxIcon]::Question
                        )
                        if ($cancelChoice -eq 'Yes') {{
                            $global:installationCancelled = $true
                            return $false
                        }}
                        $attemptCount-- # 취소 선택시 시도 횟수 복구
                        continue
                    }}
                    
                    # sudo 권한 설정 시도
                    Update-Progress "비밀번호 확인 중... (시도 $attemptCount/$maxAttempts)" 55
                    $sudoResult = wsl -d $distroName -- bash -c "echo '$password' | sudo -S echo 'Password check successful' 2>&1"
                    
                    if ($sudoResult -like "*Password check successful*") {{
                        # 비밀번호 성공
                        $passwordSuccess = $true
                        
                        # NOPASSWD 설정 추가
                        Update-Progress "sudo 권한 설정 중..." 55
                        wsl -d $distroName -- bash -c "echo '$password' | sudo -S bash -c 'echo `"$currentUser ALL=(ALL) NOPASSWD:ALL`" >> /etc/sudoers'" 2>&1 | Out-Null
                        Update-Progress "✓ sudo 권한 설정 완료" 55
                    }} else {{
                        # 비밀번호 실패
                        if ($attemptCount -eq $maxAttempts) {{
                            # 최대 시도 횟수 초과
                            Update-Progress "비밀번호 인증 실패 (최대 시도 횟수 초과)" 55
                            [System.Windows.Forms.MessageBox]::Show(
                                "비밀번호가 $maxAttempts회 모두 틀렸습니다.`n`n설치를 계속할 수 없습니다.",
                                "인증 실패",
                                [System.Windows.Forms.MessageBoxButtons]::OK,
                                [System.Windows.Forms.MessageBoxIcon]::Error
                            )
                            return $false
                        }}
                        # 다시 시도
                        Write-Host "[WARNING] 비밀번호가 틀렸습니다. (시도 $attemptCount/$maxAttempts)"
                    }}
                }}
                
                if (-not $passwordSuccess) {{
                    # 모든 시도 실패 또는 취소
                    return $false
                }}
            }}
        }}
        
        # ============================================
        # Step 3: Docker 설치 (Ubuntu 내부에 Docker CE)
        # ============================================
        Update-Progress 'Step 3/5: Ubuntu 내부에 Docker 설치' 60
        
        Write-Host "[INFO] Installing Docker CE in Ubuntu..."
        
        # Docker 확인 및 설치
        $dockerCheck = wsl -d $distroName -- which docker 2>$null
        if ([string]::IsNullOrEmpty($dockerCheck)) {{
            Update-Progress 'Docker 설치 중 (몇 분 소요)...' 60
            
            # Docker CE 설치 스크립트
            $installScript = @'
#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -qq
sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
'@
            
            # 스크립트 실행 (비동기 처리로 GUI 응답성 유지)
            $scriptBlock = {{
                param($distro, $script)
                wsl -d $distro -- bash -c $script 2>&1
            }}
            
            $job = Start-Job -ScriptBlock $scriptBlock -ArgumentList $distroName, $installScript
            
            # Docker 설치 대기 (최대 2분, GUI 응답성 유지)
            $timeout = 120  # 120초 (2분)
            $elapsed = 0
            while ($job.State -eq 'Running' -and $elapsed -lt $timeout) {{
                Start-Sleep -Seconds 1
                $elapsed++
                
                # 매 초마다 GUI 업데이트
                [System.Windows.Forms.Application]::DoEvents()
                
                # 10초마다 진행상황 표시
                if ($elapsed % 10 -eq 0) {{
                    Update-Progress "Docker 설치 중... ($elapsed/120초)" 60
                }}
            }}
            
            # Job 결과 확인
            if ($job.State -eq 'Running') {{
                Stop-Job $job
                Remove-Job $job -Force
                Write-Host "[WARNING] Docker installation timed out after 2 minutes"
            }} else {{
                $result = Receive-Job $job
                Remove-Job $job
                Write-Host "[INFO] Docker installation completed"
            }}
            
            # GUI 응답성 유지
            [System.Windows.Forms.Application]::DoEvents()
            
            # Docker 설치 확인
            $dockerCheck = wsl -d $distroName -- which docker 2>$null
            if ([string]::IsNullOrEmpty($dockerCheck)) {{
                Update-Progress 'Docker 설치 실패' 65
                [System.Windows.Forms.MessageBox]::Show(
                    "Docker 설치에 실패했습니다.",
                    "Docker 설치 실패",
                    [System.Windows.Forms.MessageBoxButtons]::OK,
                    [System.Windows.Forms.MessageBoxIcon]::Error
                )
                return $false
            }}
        }}
        
        Update-Progress '✓ Docker 설치 완료' 65
        
        # Docker 작동 확인 (Docker Desktop WSL 통합 또는 Docker CE)
        Update-Progress 'Docker 작동 확인 중...' 70
        
        # Docker 테스트
        $dockerTest = wsl -d $distroName -- docker version 2>&1
        if ($LASTEXITCODE -ne 0) {{
            Write-Host "[INFO] Docker needs configuration, checking Docker Desktop integration..."
            
            # Docker Desktop WSL 통합 확인
            $dockerDesktopRunning = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
            if ($dockerDesktopRunning) {{
                Write-Host "[INFO] Docker Desktop is running, testing WSL integration..."
                Start-Sleep -Seconds 3
                
                # 재시도
                $dockerTest = wsl -d $distroName -- docker version 2>&1
                if ($LASTEXITCODE -eq 0) {{
                    Write-Host "[SUCCESS] Docker Desktop WSL integration is working"
                }} else {{
                    Write-Host "[WARNING] Docker Desktop WSL integration may need configuration"
                }}
            }} else {{
                # Docker CE 서비스 시작 시도 (Docker Desktop이 없는 경우)
                Write-Host "[INFO] Starting Docker CE service..."
                wsl -d $distroName -- sudo service docker start 2>&1 | Out-Null
                
                # GUI 응답성 유지
                for ($i = 0; $i -lt 2; $i++) {{
                    Start-Sleep -Seconds 1
                    [System.Windows.Forms.Application]::DoEvents()
                }}
            }}
        }} else {{
            Write-Host "[SUCCESS] Docker is already working"
        }}
        
        Update-Progress '✓ Docker 준비 완료' 70
        
        # ============================================
        # Step 4: NVIDIA Container Toolkit 설치 (GPU 지원)
        # ============================================
        Update-Progress 'Step 4/5: NVIDIA Container Toolkit 설치' 75
        
        $workerType = '{metadata.get("worker_type", "gpu")}'
        if ($workerType -eq 'gpu') {{
            Write-Host "[INFO] Installing NVIDIA Container Toolkit for GPU support..."
            
            # NVIDIA Container Toolkit 설치 스크립트 (진행 상황 표시)
            Update-Progress 'NVIDIA GPG 키 추가 중...' 75
            $nvidiaScript = @'
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "[1/5] Adding NVIDIA GPG key..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg 2>/dev/null

echo "[2/5] Adding NVIDIA repository..."
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \\
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \\
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

echo "[3/5] Updating package list..."
sudo apt-get update -qq 2>/dev/null

echo "[4/5] Installing NVIDIA Container Toolkit..."
sudo apt-get install -y -qq nvidia-container-toolkit 2>/dev/null || echo "Installation may have warnings"

echo "[5/5] Configuring Docker runtime..."
sudo nvidia-ctk runtime configure --runtime=docker 2>/dev/null || echo "Configuration may have warnings"

# Docker 재시작 (systemctl 또는 service)
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl restart docker 2>/dev/null || sudo service docker restart
else
    sudo service docker restart
fi

echo "NVIDIA Container Toolkit installation completed"
'@
            
            # 백그라운드에서 실행 (시간이 오래 걸릴 수 있음)
            $job = Start-Job -ScriptBlock {{
                param($distro, $script)
                wsl -d $distro -- bash -c $script 2>&1
            }} -ArgumentList $distroName, $nvidiaScript
            
            $elapsed = 0
            $dotCount = 0
            Write-Host "[INFO] NVIDIA Container Toolkit 설치 중 (최대 20분 소요될 수 있습니다)"
            
            # 설치가 완료될 때까지 대기 (GUI 응답성 유지)
            while ($job.State -eq 'Running') {{
                # GUI 응답성을 위해 1초마다 체크
                for ($i = 0; $i -lt 10; $i++) {{
                    Start-Sleep -Seconds 1
                    [System.Windows.Forms.Application]::DoEvents()
                    
                    # Job 상태 재확인
                    if ($job.State -ne 'Running') {{
                        break
                    }}
                }}
                
                if ($job.State -ne 'Running') {{
                    break
                }}
                
                $elapsed += 10
                $dotCount = ($dotCount + 1) % 4
                $dots = "." * $dotCount
                $spaces = " " * (3 - $dotCount)
                
                # 진행률 업데이트 (75-80% 범위, 천천히 증가)
                $progress = [int](75 + ([Math]::Min($elapsed, 600) / 600 * 5))
                
                # 분:초 형식으로 시간 표시
                $minutes = [int]($elapsed / 60)
                $seconds = $elapsed % 60
                $timeStr = "{{0}}분 {{1}}초" -f $minutes, $seconds
                
                Update-Progress "NVIDIA Container Toolkit 설치 중$dots$spaces ($timeStr)" $progress
                
                # 1분마다 상태 메시지 출력
                if ($elapsed % 60 -eq 0) {{
                    Write-Host "[INFO] NVIDIA 설치 진행 중... ($timeStr 경과)"
                }}
            }}
            
            # 작업 완료 - 결과 확인
            $result = Receive-Job $job
            $jobState = $job.State
            Remove-Job $job -Force
            
            if ($jobState -eq 'Completed') {{
                # 설치 결과 확인
                if ($result -match "completed|successfully" -or $result -notmatch "error|fail") {{
                    Write-Host "[SUCCESS] NVIDIA Container Toolkit installation completed"
                    Write-Host "[INFO] Installation output: $($result -split "`n" | Select-Object -Last 1)"
                    Update-Progress '✓ NVIDIA Container Toolkit 설치 완료' 80
                }} else {{
                    Write-Host "[WARNING] NVIDIA installation may have issues: $result"
                    Update-Progress 'NVIDIA 설치 완료 (경고 있음)' 80
                }}
            }} else {{
                Write-Host "[ERROR] NVIDIA installation job ended with state: $jobState"
                Update-Progress 'NVIDIA 설치 실패' 80
                
                # 에러지만 계속 진행 (Docker Desktop이 GPU 지원 가능)
                Write-Host "[INFO] Continuing with Docker Desktop GPU support..."
            }}
        }} else {{
            Update-Progress 'CPU 모드 - NVIDIA 설정 건너뜀' 80
        }}
        
        # ============================================
        # Step 5: Worker 컨테이너 배포 (docker-compose up)
        # ============================================
        Update-Progress 'Step 5/5: Worker 컨테이너 배포' 85
        
        Write-Host "[INFO] Deploying worker container with docker-compose..."
        Write-Host "[DEBUG] Calling Deploy-Container with:"
        Write-Host "  - DistroName: $distroName"
        Write-Host "  - VpnIP: $global:VPN_IP"
        Write-Host "  - LanIP: $global:LAN_IP"
        Write-Host "  - WorkerType: $workerType"

        # Deploy-Container 함수 호출 전 확인
        try {{
            # GUI 응답성 유지
            [System.Windows.Forms.Application]::DoEvents()

            # Deploy-Container 함수 호출
            Write-Host "[DEBUG] Invoking Deploy-Container function..."
            $deployResult = Deploy-Container -DistroName $distroName -VpnIP $global:VPN_IP -LanIP $global:LAN_IP -WorkerType $workerType
            
            # GUI 응답성 유지
            [System.Windows.Forms.Application]::DoEvents()
            
            Write-Host "[DEBUG] Deploy-Container returned: Success=$($deployResult.Success), Message=$($deployResult.Message)"
        }} catch {{
            Write-Host "[ERROR] Deploy-Container failed with exception: $_"
            $deployResult = @{{ Success = $false; Message = $_.ToString() }}
        }}
        
        if (-not $deployResult.Success) {{
            Update-Progress "컨테이너 배포 실패: $($deployResult.Message)" 90
            
            # 간단한 재시도
            Write-Host "[INFO] Retrying container deployment..."
            
            # GUI 응답성 유지
            [System.Windows.Forms.Application]::DoEvents()
            
            wsl -d $distroName -- sudo systemctl restart docker 2>&1 | Out-Null
            
            # GUI 응답성 유지 (짧은 대기 시간 분할)
            for ($i = 0; $i -lt 3; $i++) {{
                Start-Sleep -Seconds 1
                [System.Windows.Forms.Application]::DoEvents()
            }}
            
            $deployResult = Deploy-Container -DistroName $distroName -VpnIP $global:VPN_IP -LanIP $global:LAN_IP -WorkerType $workerType
            
            if (-not $deployResult.Success) {{
                Update-Progress "컨테이너 배포 실패" 0
                
                # 설치 실패 플래그 설정
                $global:isInstalling = $false
                $global:installationFailed = $true
                
                # 에러 메시지 표시 (타이머 사용으로 GUI 블로킹 방지)
                $errorMessage = "컨테이너 배포에 실패했습니다.`n`n오류: $($deployResult.Message)`n`n10초 후 자동으로 종료됩니다."
                
                # GUI 업데이트
                if ($global:statusLabel) {{
                    $global:statusLabel.Text = "배포 실패 - 자동 종료 대기 중..."
                    $global:statusLabel.ForeColor = [System.Drawing.Color]::Red
                }}
                if ($global:detailLabel) {{
                    $global:detailLabel.Text = $deployResult.Message
                }}
                
                # 즉시 종료 처리 (메시지 박스 없이)
                Write-Host "[ERROR] Container deployment failed, terminating..."
                
                # 버튼 상태 변경
                if ($global:startButton) {{
                    $global:startButton.Enabled = $false
                    $global:startButton.Text = "실패"
                }}
                if ($global:closeButton) {{
                    $global:closeButton.Enabled = $true
                    $global:closeButton.Text = "종료"
                }}
                
                # 3초 후 자동 종료
                $global:autoExitTimer = New-Object System.Windows.Forms.Timer
                $global:autoExitTimer.Interval = 3000
                $global:autoExitTimer.Add_Tick({{
                    $global:autoExitTimer.Stop()
                    Write-Host "[INFO] Auto-closing after deployment failure..."
                    
                    # Cleanup
                    Cleanup-OnExit -IsError $true -ErrorMessage "컨테이너 배포 실패"
                    
                    # 강제 종료
                    if ($global:form) {{
                        $global:form.Close()
                    }}
                    Stop-Process -Id $PID -Force
                }})
                $global:autoExitTimer.Start()
                
                Write-Host "[INFO] Application will close in 3 seconds..."
                
                return $false
            }}
        }}
        
        Update-Progress "✓ 컨테이너 배포 완료" 95
        
        # ============================================
        # 최종 상태 확인
        # ============================================
        Update-Progress '설치 완료 확인 중...' 98
        
        # 컨테이너 실행 확인
        $containerCheck = wsl -d $distroName -- docker ps --format "table {{{{.Names}}}}\\t{{{{.Status}}}}" 2>$null | Select-String "node-server"
        
        if ($containerCheck) {{
            Update-Progress '✅ 설치 완료! Worker 노드가 실행 중입니다.' 100
            
            [System.Windows.Forms.MessageBox]::Show(
                "Worker Node 설치가 완료되었습니다!`n`nNode ID: $global:NODE_ID`nVPN IP: $global:VPN_IP`nStatus: Running",
                "설치 완료",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Information
            )
            return $true
        }} else {{
            Update-Progress '⚠️ 컨테이너 상태 확인 필요' 100
            
            [System.Windows.Forms.MessageBox]::Show(
                "설치는 완료되었지만 컨테이너 상태를 확인해주세요.",
                "확인 필요",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            )
            return $true
        }}
        
    }} catch {{
        Update-Progress "오류 발생: $_" 50
        Write-Host "[ERROR] Installation failed: $_"
        
        [System.Windows.Forms.MessageBox]::Show(
            "설치 중 오류가 발생했습니다.`n`n$_",
            "설치 오류",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        )
        
        return $false
    }}
}}
"""
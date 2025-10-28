"""
Docker Setup Module
Docker Desktop 확인 및 Docker 설치 관련 모든 로직
"""

def get_docker_setup_function() -> str:
    """Docker 설치 및 설정 함수 반환"""
    
    return """
# Docker Desktop WSL Integration 자동 설정 함수
function Enable-DockerWSLIntegration {
    try {
        Write-Host "[DEBUG] Configuring Docker Desktop WSL Integration"
        
        $settingsPath = "$env:APPDATA\Docker\settings.json"
        
        # Docker Desktop 설정 수정 (종료하지 않고 설정만 변경)
        $dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
        $dockerRunning = $false
        
        if ($dockerProcess) {
            Write-Host "[DEBUG] Docker Desktop is running, will update settings without stopping"
            $dockerRunning = $true
        }
        
        # settings.json 파일 확인
        if (Test-Path $settingsPath) {
            Write-Host "[DEBUG] Found Docker settings at: $settingsPath"
            
            # 기존 설정 읽기
            $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
            
            # WSL2 통합 활성화
            $settings.integratedWslDistros = @{}
            
            # 모든 Ubuntu 배포판 활성화
            $wslDistros = wsl -l -q 2>$null
            foreach ($distro in $wslDistros) {
                $distroName = $distro.Trim()
                if ($distroName -match "Ubuntu" -or $distroName -match "ubuntu") {
                    Write-Host "[DEBUG] Enabling WSL integration for: $distroName"
                    $settings.integratedWslDistros | Add-Member -MemberType NoteProperty -Name $distroName -Value $true -Force
                }
            }
            
            # WSL2 백엔드 활성화
            $settings.wslEngineEnabled = $true
            
            # 설정 저장
            $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8
            Write-Host "[DEBUG] Docker settings updated successfully"
            
        } else {
            Write-Host "[DEBUG] Docker settings file not found, creating new one"
            
            # 새 설정 파일 생성
            $newSettings = @{
                wslEngineEnabled = $true
                integratedWslDistros = @{}
            }
            
            # Ubuntu 배포판 추가
            $wslDistros = wsl -l -q 2>$null
            foreach ($distro in $wslDistros) {
                $distroName = $distro.Trim()
                if ($distroName -match "Ubuntu" -or $distroName -match "ubuntu") {
                    $newSettings.integratedWslDistros.$distroName = $true
                }
            }
            
            # 디렉토리 생성
            $dockerDir = Split-Path $settingsPath -Parent
            if (-not (Test-Path $dockerDir)) {
                New-Item -ItemType Directory -Path $dockerDir -Force | Out-Null
            }
            
            # 설정 저장
            $newSettings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8
        }
        
        # Docker Desktop이 실행 중이면 설정만 적용 (재시작 안 함)
        if ($dockerRunning) {
            Write-Host "[DEBUG] Docker Desktop settings updated. Manual restart may be required for changes to take effect."
            Write-Host "[INFO] Docker Desktop is running with updated WSL Integration settings"
        } else {
            Write-Host "[DEBUG] Docker Desktop not running. Settings will be applied on next start."
        }
        
        Write-Host "[DEBUG] WSL Integration configuration completed"
        return $true
        
    } catch {
        Write-Host "[ERROR] Failed to configure WSL Integration: $_"
        return $false
    }
}

# Docker Desktop 확인 함수
function Check-DockerDesktop {
    try {
        Write-Host "[DEBUG] Checking Docker Desktop installation"
        
        $dockerDesktopPath = "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"
        $dockerDesktopInstalled = Test-Path $dockerDesktopPath
        
        if (-not $dockerDesktopInstalled) {
            Write-Host "[DEBUG] Docker Desktop not found"
            return @{
                Installed = $false
                Running = $false
                WSLIntegrated = $false
                Message = "Docker Desktop이 설치되지 않았습니다."
                }
        }
        
        # Docker Desktop 실행 확인
        $dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
        if (-not $dockerProcess) {
            Write-Host "[DEBUG] Docker Desktop is not running"
            Write-Host "[INFO] Attempting to start Docker Desktop gently..."
            
            # Docker Desktop을 조심스럽게 시작 (기존 프로세스가 있을 수 있음)
            try {
                # 이미 실행 중인지 확인
                $dockerService = Get-Process -Name "com.docker.service" -ErrorAction SilentlyContinue
                $dockerBackend = Get-Process -Name "Docker.Backend" -ErrorAction SilentlyContinue
                
                if ($dockerService -or $dockerBackend) {
                    Write-Host "[DEBUG] Docker backend process found, waiting for UI..."
                    Write-Host "[INFO] Docker Desktop backend is running, UI may take time to appear"
                    Start-Sleep -Seconds 3
                } else {
                    # 새로 시작
                    Write-Host "[INFO] Starting Docker Desktop..."
                    Start-Process -FilePath $dockerDesktopPath
                    Write-Host "[DEBUG] Docker Desktop start command sent"
                    Start-Sleep -Seconds 2
                }
            } catch {
                Write-Host "[WARNING] Could not start Docker Desktop: $_"
            }
            
            # Docker Desktop 시작 대기 (더 짧게)
            $maxWait = 15
            $waited = 0
            while ($waited -lt $maxWait) {
                Start-Sleep -Seconds 3
                $waited += 3
                $dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
                if ($dockerProcess) {
                    Write-Host "[DEBUG] Docker Desktop UI detected"
                    break
                }
            }
            
            if (-not $dockerProcess) {
                Write-Host "[INFO] Docker Desktop UI not detected, but may be running in background"
                # Docker Desktop이 없어도 계속 진행 (대체 방법 사용)
                return @{
                    Installed = $true
                    Running = $false
                    WSLIntegrated = $false
                    Message = "Docker Desktop이 백그라운드에서 실행 중이거나 시작되지 않았습니다."
                    }
            }
            
            # Docker 엔진 시작 대기 (짧게)
            Write-Host "[DEBUG] Waiting for Docker engine to be ready"
            Start-Sleep -Seconds 5
        }
        
        Write-Host "[DEBUG] Docker Desktop is running"
        
        # WSL 통합 확인
        $wslIntegration = $false
        $dockerDistros = wsl -l -q 2>$null | Where-Object { $_ -match 'docker-desktop' }
        if ($dockerDistros) {
            $wslIntegration = $true
            Write-Host "[DEBUG] Docker Desktop WSL integration detected"
        }
        
        return @{
            Installed = $true
            Running = $true
            WSLIntegrated = $wslIntegration
            Message = "Docker Desktop이 실행 중입니다."
            }
        
    } catch {
        Write-Host "[ERROR] Check-DockerDesktop failed: $_"
        return @{
            Installed = $false
            Running = $false
            WSLIntegrated = $false
            Message = "Docker Desktop 확인 중 오류 발생: $_"
            }
    }
}

# WSL에서 Docker 설치 함수
function Install-DockerInWSL {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DistroName,
        [Parameter(Mandatory=$false)]
        [bool]$UseDockerDesktop = $true
    )
    
    try {
        Write-Host "[DEBUG] Checking Docker in WSL distro: $DistroName"
        
        # Docker Desktop 통합 확인
        if ($UseDockerDesktop) {
            # Docker Desktop의 docker.sock 확인 및 권한 설정
            $dockerSock = wsl -d $DistroName -- bash -c "test -S /var/run/docker.sock && echo 'exists'" 2>$null
            
            if ($dockerSock -eq 'exists') {
                Write-Host "[DEBUG] Docker Desktop integration is active"
                
                # 소켓 권한 설정
                wsl -d $DistroName -- bash -c "sudo chmod 666 /var/run/docker.sock 2>/dev/null" 2>$null
                wsl -d $DistroName -- bash -c "sudo chgrp docker /var/run/docker.sock 2>/dev/null" 2>$null
                
                # Docker 작동 확인
                $dockerTest = wsl -d $DistroName -- docker version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[DEBUG] Docker Desktop integration working without sudo"
                    return @{
                        Success = $true
                        DockerType = "DockerDesktop"
                        Version = "Docker Desktop"
                        Message = "Docker Desktop 통합이 활성화되어 있습니다."
                        }
                } else {
                    # sudo로 재시도
                    $dockerTest = wsl -d $DistroName -- sudo docker version 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "[DEBUG] Docker Desktop integration requires sudo"
                        return @{
                            Success = $true
                            DockerType = "DockerDesktop"
                            Version = "Docker Desktop"
                            Message = "Docker Desktop 통합이 활성화되어 있습니다 (sudo 필요)."
                            }
                    }
                }
            }
            
            Write-Host "[DEBUG] Docker Desktop integration not available, checking Docker CE"
        }
        
        # Docker CE 설치 확인
        $dockerCheck = wsl -d $DistroName -- which docker 2>$null
        if ($dockerCheck) {
            Write-Host "[DEBUG] Docker is already installed in WSL at: $dockerCheck"
            
            # Docker 서비스 시작 및 권한 설정
            Write-Host "[DEBUG] Ensuring Docker service is running..."
            
            # Docker 서비스 시작 스크립트
            $serviceScript = @'
#!/bin/bash
# Docker 서비스 시작 및 권한 설정
sudo service docker start 2>/dev/null || sudo dockerd --group=docker > /dev/null 2>&1 &
sleep 2
# 소켓 권한 설정
if [ -S /var/run/docker.sock ]; then
    sudo chmod 666 /var/run/docker.sock
    sudo chgrp docker /var/run/docker.sock 2>/dev/null || true
fi
# 그룹 추가
sudo usermod -aG docker $USER 2>/dev/null || true
# 테스트
docker version >/dev/null 2>&1 && echo "success" || echo "failed"
'@
            
            $result = $serviceScript | wsl -d $DistroName -- bash 2>$null
            
            if ($result -match "success") {
                Write-Host "[DEBUG] Docker CE is working"
                return @{
                    Success = $true
                    DockerType = "DockerCE"
                    Version = "Installed"
                    Message = "Docker CE가 설치되어 있습니다."
                    }
            } else {
                Write-Host "[DEBUG] Docker CE found but needs configuration"
                # 설정이 필요하지만 설치는 되어 있음
                return @{
                    Success = $true
                    DockerType = "DockerCE"
                    Version = "Installed"
                    Message = "Docker CE가 설치되어 있습니다 (설정 필요)."
                    }
            }
        }
        
        # Docker CE 설치
        Write-Host "[DEBUG] Installing Docker CE in WSL"
        
        # Docker 설치 스크립트 (sudo 직접 사용 버전)
        $dockerInstallScript = @'
#!/bin/bash
set -e

# Update package list
echo "Updating package list..."
export DEBIAN_FRONTEND=noninteractive
export NONINTERACTIVE=1
sudo apt-get update -qq

# Install prerequisites
echo "Installing prerequisites..."
sudo apt-get install -y -qq \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
echo "Adding Docker GPG key..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo "Setting up Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package list again
echo "Updating package list with Docker repository..."
sudo apt-get update -qq

# Install Docker Engine and docker-compose
echo "Installing Docker Engine and docker-compose..."
sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-compose

# Add current user to docker group
echo "Adding user to docker group..."
sudo usermod -aG docker $USER

# Fix docker socket permissions
echo "Fixing docker socket permissions..."
sudo chmod 666 /var/run/docker.sock 2>/dev/null || true

# Start Docker service
echo "Starting Docker service..."
sudo service docker start || sudo dockerd > /dev/null 2>&1 &
sleep 3

# Enable Docker to start on boot
echo "Enabling Docker service..."
sudo systemctl enable docker 2>/dev/null || true

# Test Docker
echo "Testing Docker..."
sudo docker version > /dev/null 2>&1 && echo "Docker is working!" || echo "Docker test failed"

echo "Docker installation completed"
'@
        
        # 스크립트 실행
        $installResult = $dockerInstallScript | wsl -d $DistroName -- bash 2>&1
        Write-Host "[DEBUG] Docker install output: $installResult"
        
        # Docker 서비스 시작
        wsl -d $DistroName -- sudo service docker start 2>$null
        Start-Sleep -Seconds 3
        
        # 설치 확인
        $dockerVersion = wsl -d $DistroName -- docker version --format '{.Server.Version}' 2>$null
        if ($dockerVersion) {
            Write-Host "[DEBUG] Docker CE successfully installed: $dockerVersion"
            return @{
                Success = $true
                DockerType = "DockerCE"
                Version = $dockerVersion
                Message = "Docker CE가 성공적으로 설치되었습니다."
                }
        } else {
            # sudo로 재시도
            $dockerVersion = wsl -d $DistroName -- sudo docker version --format '{.Server.Version}' 2>$null
            if ($dockerVersion) {
                Write-Host "[DEBUG] Docker CE installed (requires sudo): $dockerVersion"
                
                # Docker 그룹 권한 재설정
                wsl -d $DistroName -- bash -c "sudo usermod -aG docker \$USER && newgrp docker" 2>$null
                
                return @{
                    Success = $true
                    DockerType = "DockerCE"
                    Version = $dockerVersion
                    Message = "Docker CE가 설치되었습니다. WSL 재시작이 필요할 수 있습니다."
                    }
            }
        }
        
        Write-Host "[ERROR] Docker installation verification failed"
        return @{
            Success = $false
            DockerType = $null
            Version = $null
            Message = "Docker 설치 확인 실패"
            }
        
    } catch {
        Write-Host "[ERROR] Install-DockerInWSL failed: $_"
        return @{
            Success = $false
            DockerType = $null
            Version = $null
            Message = "Docker 설치 중 오류 발생: $_"
            }
    }
    
    # 기본 반환값 (여기까지 오면 안됨)
    Write-Host "[ERROR] Unexpected end of Install-DockerInWSL function"
    return @{
        Success = $false
        DockerType = $null
        Version = $null
        Message = "Docker 설치 함수 종료"
        }
}

# Docker 서비스 상태 확인 및 시작 함수
function Start-DockerService {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DistroName
    )
    
    try {
        Write-Host "[DEBUG] Checking Docker service status"
        
        # Docker 데몬 상태 확인
        $dockerPid = wsl -d $DistroName -- bash -c "sudo cat /var/run/docker.pid 2>/dev/null"
        
        if (-not $dockerPid) {
            Write-Host "[DEBUG] Docker daemon not running, starting..."
            
            # Docker 서비스 시작
            wsl -d $DistroName -- bash -c "sudo service docker start" 2>$null
            Start-Sleep -Seconds 3
            
            # 재확인
            $dockerPid = wsl -d $DistroName -- bash -c "sudo cat /var/run/docker.pid 2>/dev/null"
            if ($dockerPid) {
                Write-Host "[DEBUG] Docker daemon started successfully (PID: $dockerPid)"
                return @{
                    Success = $true
                    Pid = $dockerPid
                    Message = "Docker 서비스가 시작되었습니다."
                    }
            } else {
                # systemctl로 재시도
                wsl -d $DistroName -- bash -c "sudo systemctl start docker" 2>$null
                Start-Sleep -Seconds 3
                
                $dockerPid = wsl -d $DistroName -- bash -c "sudo cat /var/run/docker.pid 2>/dev/null"
                if ($dockerPid) {
                    Write-Host "[DEBUG] Docker daemon started via systemctl (PID: $dockerPid)"
                    return @{
                        Success = $true
                        Pid = $dockerPid
                        Message = "Docker 서비스가 시작되었습니다."
                        }
                }
            }
            
            # Docker 데몬 직접 실행 시도
            Write-Host "[DEBUG] Attempting to start Docker daemon directly..."
            
            # Docker 데몬을 백그라운드로 직접 실행 (WSL 환경용 개선된 버전)
            $startDockerCmd = @'
#!/bin/bash
# Docker 데몬 직접 시작 (WSL 환경 최적화)
sudo mkdir -p /var/run/docker /var/lib/docker
sudo rm -f /var/run/docker.pid /var/run/docker.sock 2>/dev/null

# 현재 사용자를 docker 그룹에 추가
sudo groupadd docker 2>/dev/null || true
sudo usermod -aG docker $USER 2>/dev/null || true

# systemd가 없는 환경을 위한 Docker 데몬 실행
# iptables-legacy 사용
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy 2>/dev/null || true
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy 2>/dev/null || true

# Docker Desktop WSL 통합 먼저 확인
if [ -S /var/run/docker.sock ]; then
    echo "Docker Desktop WSL integration detected"
    # 소켓 권한 설정
    sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
    if sudo docker version >/dev/null 2>&1; then
        echo "DockerDesktop"
        exit 0
    fi
fi

# Docker Desktop이 없으면 직접 실행
sudo dockerd \
    --storage-driver=overlay2 \
    --iptables=false \
    --group=docker \
    --pidfile=/var/run/docker.pid \
    > /tmp/docker.log 2>&1 &

DOCKER_PID=$!
echo $DOCKER_PID | sudo tee /var/run/docker.pid

# Docker 데몬이 시작될 때까지 대기
for i in {1..20}; do
    if [ -S /var/run/docker.sock ]; then
        # 소켓 권한 설정
        sudo chmod 666 /var/run/docker.sock
        if sudo docker version >/dev/null 2>&1; then
            echo "Docker daemon started successfully"
            break
        fi
    fi
    sleep 1
done

# PID 출력
cat /var/run/docker.pid
'@
            
            $dockerPid = $startDockerCmd | wsl -d $DistroName -- bash 2>$null
            
            if ($dockerPid) {
                Write-Host "[DEBUG] Docker daemon started directly (PID: $dockerPid)"
                
                # Docker 작동 확인
                $dockerTest = wsl -d $DistroName -- sudo docker version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[DEBUG] Docker is working properly"
                    return @{
                        Success = $true
                        Pid = $dockerPid
                        Message = "Docker 데몬이 직접 시작되었습니다."
                        }
                }
            }
            
            # 마지막 시도: Docker Desktop WSL 통합 체크
            Write-Host "[DEBUG] Checking for Docker Desktop WSL integration..."
            
            # Docker Desktop의 docker.sock 확인
            $dockerSockCheck = wsl -d $DistroName -- bash -c "test -S /var/run/docker.sock && echo 'exists'" 2>$null
            if ($dockerSockCheck -eq 'exists') {
                Write-Host "[SUCCESS] Docker Desktop WSL integration is available"
                
                # Docker Desktop 통합 테스트
                $dockerTest = wsl -d $DistroName -- docker version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[SUCCESS] Docker Desktop integration is working"
                    return @{
                        Success = $true
                        Pid = "DockerDesktop"
                        Message = "Docker Desktop WSL 통합을 사용합니다."
                        }
                }
            }
            
            Write-Host "[ERROR] Failed to start Docker daemon"
            return @{
                Success = $false
                Pid = $null
                Message = "Docker 서비스를 시작할 수 없습니다. Docker Desktop을 사용하거나 수동으로 시작해주세요."
                }
        } else {
            Write-Host "[DEBUG] Docker daemon is already running (PID: $dockerPid)"
            return @{
                Success = $true
                Pid = $dockerPid
                Message = "Docker 서비스가 이미 실행 중입니다."
                }
        }
        
    } catch {
        Write-Host "[ERROR] Start-DockerService failed: $_"
        return @{
            Success = $false
            Pid = $null
            Message = "Docker 서비스 시작 중 오류 발생: $_"
            }
    }
}

# NVIDIA Container Toolkit 설치 함수
function Install-NvidiaContainerToolkit {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DistroName,
        [Parameter(Mandatory=$false)]
        [switch]$SkipIfNotNeeded = $true
    )
    
    try {
        Write-Host "[DEBUG] Checking NVIDIA GPU support"
        
        # NVIDIA GPU 확인 (선택적)
        if ($SkipIfNotNeeded) {
            $nvidiaGpu = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -match "NVIDIA" }
            if (-not $nvidiaGpu) {
                Write-Host "[DEBUG] No NVIDIA GPU detected, skipping NVIDIA Container Toolkit"
                return @{
                    Success = $true
                    Installed = $false
                    Message = "NVIDIA GPU가 감지되지 않아 설치를 건너뜁니다."
                    }
            }
        }
        
        Write-Host "[DEBUG] Installing NVIDIA Container Toolkit"
        
        # NVIDIA Container Toolkit 설치 스크립트
        $nvidiaScript = @'
#!/bin/bash
set -e

# NVIDIA Container Toolkit 저장소 추가
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# 패키지 업데이트
sudo apt-get update -qq

# NVIDIA Container Toolkit 설치
sudo apt-get install -y -qq nvidia-container-toolkit

# Docker 설정
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker 2>/dev/null || sudo service docker restart

echo "NVIDIA Container Toolkit installed"
'@
        
        # 스크립트 실행
        $installResult = $nvidiaScript | wsl -d $DistroName -- bash 2>&1
        Write-Host "[DEBUG] NVIDIA install output: $installResult"
        
        # 설치 확인
        $nvidiaCheck = wsl -d $DistroName -- which nvidia-container-toolkit 2>$null
        if ($nvidiaCheck) {
            Write-Host "[DEBUG] NVIDIA Container Toolkit successfully installed"
            return @{
                Success = $true
                Installed = $true
                Message = "NVIDIA Container Toolkit이 설치되었습니다."
                }
        } else {
            Write-Host "[WARNING] NVIDIA Container Toolkit installation could not be verified"
            return @{
                Success = $true
                Installed = $false
                Message = "NVIDIA Container Toolkit 설치를 확인할 수 없습니다."
                }
        }
        
    } catch {
        Write-Host "[ERROR] Install-NvidiaContainerToolkit failed: $_"
        return @{
            Success = $false
            Installed = $false
            Message = "NVIDIA Container Toolkit 설치 중 오류 발생: $_"
            }
    }
}
"""
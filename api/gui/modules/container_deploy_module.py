"""
Container Deploy Module
Docker 컨테이너 배포 및 관리 관련 모든 로직
"""

def get_container_deploy_function(node_id: str, worker_ip: str, central_ip: str, metadata: dict, lan_ip: str = None) -> str:
    """컨테이너 배포 함수 반환"""

    # Metadata에서 필요한 값 추출
    # GPU를 기본으로 설정 (NVIDIA GPU가 있는 경우에만 실제로 사용됨)
    worker_type = metadata.get('worker_type', 'gpu')
    description = metadata.get('description', f'Worker Node {node_id}')
    api_token = metadata.get('api_token', '')
    docker_image = metadata.get('docker_image', 'heoaa/worker-node-prod:latest')
    memory_limit = metadata.get('memory_limit', '64g')  # 워커노드는 학습 수행으로 더 많은 메모리 필요

    # LAN IP가 None이면 Worker IP를 기본값으로 사용 (PowerShell 치환이 작동하도록)
    # PowerShell에서 감지된 실제 LAN IP로 치환됨
    effective_lan_ip = lan_ip if lan_ip else worker_ip
    effective_worker_ip = worker_ip if worker_ip else ""

    # Docker Compose 설정 (bridge 네트워크 모드 - 이전 버전과 동일)
    docker_compose_content = f"""services:
  server:
    image: {docker_image}
    container_name: node-server-{node_id}
    # bridge 네트워크 모드 사용 - 컨테이너가 독립적인 네트워크 사용
    # network_mode: host는 사용하지 않음 (포트 포워딩으로 외부 접근)

    environment:
      # 기본 워커노드 설정
      - NODE_ID={node_id}
      - DESCRIPTION={description}
      - CENTRAL_SERVER_IP={central_ip}
      - CENTRAL_SERVER_URL=http://{central_ip}:8000
      - API_TOKEN={api_token}

      # 네트워크 설정
      - LAN_IP={effective_lan_ip}
      - WORKER_IP={effective_worker_ip}
      - HOST_IP={effective_lan_ip}

      # Docker 환경 플래그
      - DOCKER_CONTAINER=true

      # NCCL 설정 (분산 학습용)
      - NCCL_DEBUG=INFO
      - NCCL_DEBUG_SUBSYS=ALL
      - TORCH_DISTRIBUTED_DEBUG=DETAIL

      # Python 설정
      - PYTHONUNBUFFERED=1
      - PYTHONPATH=/app
      - PYTHONDONTWRITEBYTECODE=1

      # NCCL 상세 설정
      - NCCL_SOCKET_FAMILY=AF_INET
      - NCCL_ASYNC_ERROR_HANDLING=1
      - NCCL_TIMEOUT=600
      - NCCL_RETRY_COUNT=10
      - NCCL_TREE_THRESHOLD=0
      - NCCL_BUFFSIZE=8388608
      - NCCL_IB_DISABLE=1
      - NCCL_P2P_DISABLE=1
      - NCCL_NSOCKS_PERTHREAD=4
      - NCCL_SOCKET_NTHREADS=1
      - NCCL_MAX_NCHANNELS=16
      - NCCL_MIN_NCHANNELS=4
      - NCCL_NET_GDR_LEVEL=0
      - NCCL_CHECKS_DISABLE=0
      - OMP_NUM_THREADS=1
      - MKL_NUM_THREADS=1

      # Ray 설정
      - RAY_DISABLE_DASHBOARD=1
      
    volumes:
      # 캐시와 임시 파일
      - ~/.cache/torch:/root/.cache/torch
      - ~/.cache/huggingface:/root/.cache/huggingface
      - /tmp/ray:/tmp/ray
      - /tmp/ray_tmp:/tmp/ray_tmp
      - /var/run/docker.sock:/var/run/docker.sock
      
      # 로그 및 결과 (옵션)
      - ./logs:/app/logs
      - ./models:/app/models
      - ./results:/app/results
      
    shm_size: '32gb'

    ulimits:
      memlock:
        soft: -1
        hard: -1
      stack:
        soft: 67108864
        hard: 67108864

    sysctls:
      net.ipv6.conf.all.disable_ipv6: "1"
      net.ipv6.conf.default.disable_ipv6: "1"
      net.ipv6.conf.lo.disable_ipv6: "1"

    # 포트 매핑 (bridge 모드)
    ports:
      - "8001:8001"       # Flask API
      - "6379:6379"       # Ray GCS/Redis
      - "10001:10001"     # Ray Client
      - "8265:8265"       # Ray Dashboard
      - "8076:8076"       # Ray Object Manager
      - "8077:8077"       # Ray Node Manager
      # - "52365:52365"     # Ray Dashboard Agent
      # - "52366:52366"     # Ray Dashboard Agent
      # - "52367:52367"     # Ray Runtime Env Agent
      - "8090:8091"       # Ray Metrics Export
      - "29500-29509:29500-29509"  # DDP TCPStore
      - "29510:29510"     # NCCL Socket
      - "11000-11049:11000-11049"  # Ray Worker Ports
      - "30000-30049:30000-30049"  # Ephemeral/Raylet Ports

    restart: unless-stopped
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
"""
    
    # GPU 지원 추가 (호스트 모드에서도 필요)
    if worker_type == 'gpu':
        # runtime 추가
        docker_compose_content += f"""    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
              count: all
        limits:
          memory: {memory_limit}
"""
    else:
        docker_compose_content += f"""    deploy:
      resources:
        limits:
          memory: {memory_limit}
"""

    # PowerShell 함수를 일반 문자열로 반환 (중괄호 이슈 해결)
    result = """
# 컨테이너 배포 함수
function Deploy-Container {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DistroName,
        [Parameter(Mandatory=$true)]
        [string]$WorkerIP,
        [Parameter(Mandatory=$false)]
        [string]$LanIP = $null,
        [Parameter(Mandatory=$false)]
        [string]$WorkerType = '""" + worker_type + """'
    )
    
    # 현재 작업 중인 배포판을 전역 변수로 저장 (Cleanup에서 사용)
    $global:currentDistro = $DistroName

    Write-Host "[Deploy-Container] Function started" -ForegroundColor Cyan
    Write-Host "[Deploy-Container] Distro: $DistroName, VPN IP: $WorkerIP, LAN IP: $LanIP, Type: $WorkerType" -ForegroundColor Yellow
    
    try {
        Write-Host "[DEBUG] Starting container deployment for distro: $DistroName"
        Write-Host "[DEBUG] Creating Docker Compose configuration..."
        
        # docker-desktop일 경우 특별 처리
        if ($DistroName -eq "docker-desktop") {
            Write-Host "[WARNING] Using Docker Desktop backend, skipping WSL directory creation"
            # Docker Desktop은 호스트 볼륨을 사용
            $dockerComposeDir = "$env:USERPROFILE\\.docker\\worker"
            if (-not (Test-Path $dockerComposeDir)) {
                New-Item -ItemType Directory -Path $dockerComposeDir -Force | Out-Null
            }
        } else {
            # WSL 내부 디렉토리 생성 (홈 디렉토리에 생성)
            Write-Host "[DEBUG] Creating directories in WSL home directory"
            $directories = @(
                "~/worker",
                "~/worker/models",
                "~/worker/outputs",
                "~/worker/logs"
            )
            
            foreach ($dir in $directories) {
                Write-Host "[DEBUG] Creating directory: $dir"
                
                # 홈 디렉토리는 sudo 없이 생성 가능
                try {
                    $mkdirScript = "mkdir -p $dir 2>/dev/null && echo SUCCESS || echo FAILED"
                    $result = wsl -d $DistroName -- bash -c $mkdirScript 2>&1
                    
                    if ($result -match "SUCCESS") {
                        Write-Host "[DEBUG] Directory created: $dir"
                    } else {
                        Write-Host "[WARNING] Directory may already exist: $dir"
                    }
                } catch {
                    Write-Host "[WARNING] Error creating directory $dir : $_"
                }
            }
            Write-Host "[DEBUG] Directories created successfully"
        }
        
        # Docker Compose 파일 생성
        Write-Host "[DEBUG] Creating docker-compose.yml"
        $dockerComposeContent = @'
""" + docker_compose_content + """'@

        # LAN IP가 감지되었으면 docker-compose 내용에서 대체
        if ($LanIP -and $LanIP -ne $WorkerIP) {
            Write-Host "[INFO] Substituting LAN_IP in docker-compose.yml: $WorkerIP -> $LanIP"
            # VPN IP로 설정된 LAN_IP 환경변수를 실제 감지된 LAN IP로 대체
            $dockerComposeContent = $dockerComposeContent -replace "LAN_IP=$WorkerIP", "LAN_IP=$LanIP"
            Write-Host "[SUCCESS] Docker compose content updated with detected LAN IP"
        } else {
            Write-Host "[INFO] Using VPN IP as LAN IP (no separate LAN IP detected)"
        }

        if ($DistroName -eq "docker-desktop") {
            # Windows 호스트에 직접 파일 생성
            $composeFile = "$env:USERPROFILE\\.docker\\worker\\docker-compose.yml"
            Set-Content -Path $composeFile -Value $dockerComposeContent -Encoding UTF8
            Write-Host "[DEBUG] Created compose file at: $composeFile"
        } else {
            # WSL에 파일 직접 생성
            Write-Host "[DEBUG] Writing docker-compose.yml to WSL"
            
            # 임시 파일로 먼저 생성
            $tempFile = "$env:TEMP\\docker-compose-temp.yml"
            
            # TEMP 환경 변수 확인
            if (-not $env:TEMP) {
                Write-Host "[ERROR] TEMP environment variable is not set"
                return @{
                    Success = $false
                    Message = "TEMP 환경 변수가 설정되지 않음"
                }
            }
            
            try {
                # BOM 없는 UTF-8로 저장
                $utf8NoBom = New-Object System.Text.UTF8Encoding $false
                [System.IO.File]::WriteAllText($tempFile, $dockerComposeContent, $utf8NoBom)
                Write-Host "[DEBUG] Temp file created: $tempFile (No BOM)"
            } catch {
                Write-Host "[ERROR] Failed to create temp file: $_"
                return @{
                    Success = $false
                    Message = "임시 파일 생성 실패: $_"
                }
            }
            
            # Windows 파일을 WSL로 복사
            if (Test-Path $tempFile) {
                # 안전한 경로 변환
                $windowsPath = $tempFile.Replace([char]92, [char]47)
                if ($windowsPath -and $windowsPath.Length -gt 3) {
                    $driveLetter = $windowsPath.Substring(0,1).ToLower()
                    $pathWithoutDrive = $windowsPath.Substring(2)
                    $wslPath = "/mnt/" + $driveLetter + $pathWithoutDrive
                    Write-Host "[DEBUG] WSL path: $wslPath"
                } else {
                    Write-Host "[ERROR] Invalid temp file path: $tempFile"
                    return @{
                        Success = $false
                        Message = "임시 파일 경로 오류"
                    }
                }
            } else {
                Write-Host "[ERROR] Temp file does not exist: $tempFile"
                return @{
                    Success = $false
                    Message = "임시 파일이 존재하지 않음"
                }
            }
            
            Write-Host "[DEBUG] Copying from Windows temp to WSL..."
            $copyResult = wsl -d $DistroName -- bash -c "cp '$wslPath' ~/worker/docker-compose.yml" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[DEBUG] docker-compose.yml created successfully"
                wsl -d $DistroName -- bash -c "chmod 644 ~/worker/docker-compose.yml" 2>$null
                
                # 임시 파일 삭제
                Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
            } else {
                Write-Host "[ERROR] Failed to copy docker-compose.yml: $copyResult"
            }
        }
        
        # Docker 이미지 확인
        Write-Host "[DEBUG] Checking Docker image: """ + docker_image + """"
        
        # GUI 업데이트
        if ($global:detailLabel) {
            $global:detailLabel.Text = "Docker 이미지 확인 중..."
        }
        [System.Windows.Forms.Application]::DoEvents()
        
        # 이미지가 이미 있는지 확인
        $imageExists = wsl -d $DistroName -- docker images -q """ + docker_image + """ 2>$null
        if ($imageExists) {
            Write-Host "[DEBUG] Docker image already exists - skipping download" -ForegroundColor Green
            
            # GUI 업데이트
            if ($global:detailLabel) {
                $global:detailLabel.Text = "기존 이미지 사용 중..."
            }
            [System.Windows.Forms.Application]::DoEvents()
        } else {
            Write-Host "[DEBUG] Image not found - will be pulled by docker-compose" -ForegroundColor Yellow
            
            # GUI 업데이트
            if ($global:detailLabel) {
                $global:detailLabel.Text = "새 이미지 다운로드 필요..."
            }
            [System.Windows.Forms.Application]::DoEvents()
        }
        
        # Docker Compose 실행 전 기존 컨테이너 정리
        Write-Host "[DEBUG] Checking existing containers..."
        
        # 기존 컨테이너 확인 및 정지
        $containerName = "node-server-""" + node_id + """"
        $existingContainers = wsl -d $DistroName -- docker ps -a --filter "name=$containerName" --format "{{.Names}}" 2>$null
        if ($existingContainers) {
            Write-Host "[DEBUG] Found existing container(s): $existingContainers"
            Write-Host "[DEBUG] Stopping and removing existing containers..."
            wsl -d $DistroName -- docker stop $containerName 2>$null
            wsl -d $DistroName -- docker rm -f $containerName 2>$null
            Start-Sleep -Seconds 1
        }
        
        # Docker Compose 실행
        Write-Host "[DEBUG] Starting container with Docker Compose"
        
        # GUI 업데이트
        if ($global:statusLabel) {
            $global:statusLabel.Text = "Worker 컨테이너 시작 중..."
        }
        if ($global:detailLabel) {
            $global:detailLabel.Text = "docker-compose up 실행 중..."
        }
        [System.Windows.Forms.Application]::DoEvents()
        
        # dockerStatus 변수 초기화
        $dockerStatus = "docker_desktop"
        
        if ($DistroName -eq "docker-desktop") {
            # Docker Desktop을 통해 직접 실행
            Write-Host "[DEBUG] Using Docker Desktop to run container"
            $composeDir = "$env:USERPROFILE\\.docker\\worker"
            
            # 이미지 확인
            $existingImages = docker images --format "table {{.Repository}}:{{.Tag}}" 2>$null
            if ($existingImages -match "heoaa/worker-node-prod") {
                Write-Host "기존 이미지를 사용하여 컨테이너를 시작합니다..." -ForegroundColor Green
            } else {
                Write-Host "Docker 이미지를 다운로드합니다..." -ForegroundColor Cyan
            }
            
            # Docker Compose 실행
            Write-Host "[DEBUG] Running docker-compose..."
            $composeResult = docker compose -f "$composeDir\\docker-compose.yml" up -d --remove-orphans 2>&1
            Write-Host "[DEBUG] Docker Compose output:"
            Write-Host $composeResult
            
        } else {
            # WSL을 통해 실행
            # docker compose 명령 확인
            $dockerComposeCmd = "docker-compose"
            $testNewCompose = wsl -d $DistroName -- which "docker-compose" 2>$null
            if ($testNewCompose) {
                # Docker CLI에 compose 플러그인이 있는지 확인
                $composePlugin = wsl -d $DistroName -- docker compose version 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $dockerComposeCmd = "docker compose"
                    Write-Host "[DEBUG] Using new 'docker compose' command"
                } else {
                    Write-Host "[DEBUG] Using legacy 'docker-compose' command"
                }
            }
            
            # Docker 소켓 권한 확인 및 설정 (타임아웃 포함)
            Write-Host "[DEBUG] Checking Docker socket permissions..."
            
            # 간단한 Docker 테스트로 변경
            $dockerStatus = "docker_sudo"  # 기본값: sudo 필요
            
            try {
                # Docker 작동 테스트 (타임아웃 3초)
                $testJob = Start-Job -ScriptBlock {
                    param($distro)
                    $result = wsl -d $distro -- bash -c "docker ps >/dev/null 2>&1 && echo 'docker_ok' || echo 'docker_sudo'" 2>$null
                    return $result
                } -ArgumentList $DistroName
                
                $waited = Wait-Job -Job $testJob -Timeout 3
                if ($waited) {
                    $dockerStatus = Receive-Job $testJob
                    Remove-Job $testJob -Force
                } else {
                    Stop-Job $testJob
                    Remove-Job $testJob -Force
                    Write-Host "[WARNING] Docker test timed out, assuming sudo required"
                }
            } catch {
                Write-Host "[WARNING] Docker test failed: $_, assuming sudo required"
            }
            
            Write-Host "[DEBUG] Docker socket status: $dockerStatus"
            
            # docker-compose.yml 파일 존재 확인 (빠른 확인)
            $fileCheck = wsl -d $DistroName -- bash -c "test -f ~/worker/docker-compose.yml && echo 'exists' || echo 'not found'" 2>$null
            if ($fileCheck -eq 'exists') {
                Write-Host "[DEBUG] docker-compose.yml verified: exists"
            } else {
                Write-Host "[ERROR] docker-compose.yml not found!"
            }
            
            # 기존 컨테이너 정리
            Write-Host "[DEBUG] Checking and cleaning up existing containers..."
            
            # 기존 컨테이너 확인 및 정지
            $containerName = "node-server-""" + node_id + """"
            $existingContainers = wsl -d $DistroName -- docker ps -a --filter "name=$containerName" --format "{{.Names}}" 2>$null
            if ($existingContainers) {
                Write-Host "[DEBUG] Removing existing container: $existingContainers"
                wsl -d $DistroName -- docker stop $containerName 2>$null
                wsl -d $DistroName -- docker rm -f $containerName 2>$null
                Start-Sleep -Seconds 1
            }
            
            # 이미지 체크
            Write-Host "[DEBUG] Checking existing Docker images..."
            $existingImages = wsl -d $DistroName -- docker images --format "table {{.Repository}}:{{.Tag}}" 2>$null
            if ($existingImages) {
                Write-Host "[DEBUG] Existing images found:"
                Write-Host $existingImages
            }
            
            # Docker Compose 실행 준비
            Write-Host "[DEBUG] Preparing to run Docker Compose..."
            
            if ($existingImages -match "heoaa/worker-node-prod") {
                Write-Host "기존 이미지를 사용하여 컨테이너를 시작합니다..." -ForegroundColor Green
            } else {
                Write-Host "Docker 이미지 다운로드 중... (최대 10분 소요)" -ForegroundColor Cyan
            }
            
            # GUI 업데이트
            if ($global:detailLabel) {
                $global:detailLabel.Text = "컨테이너 생성 중... (잠시만 기다려주세요)"
            }
            Update-Progress "Docker 컨테이너 시작 중..." 90
            [System.Windows.Forms.Application]::DoEvents()
            
            # Docker Compose 실행 (대부분 sudo가 필요함)
            if ($dockerStatus -eq "docker_ok") {
                # sudo 없이 시도 (드물지만 가능)
                Write-Host "[DEBUG] Running docker-compose without sudo..."
                $composeCmd = "cd ~/worker && $dockerComposeCmd up -d --remove-orphans"
                Write-Host "[DEBUG] Command: $composeCmd"
                
                $composeResult = wsl -d $DistroName -- bash -c "$composeCmd 2>&1"
                $exitCode = $LASTEXITCODE
                
                if ($exitCode -ne 0 -or $composeResult -match "permission denied|Permission denied") {
                    Write-Host "[WARNING] Permission denied, retrying with sudo..."
                    $dockerStatus = "docker_sudo"
                } else {
                    Write-Host "[SUCCESS] Docker Compose executed without sudo"
                    Write-Host "Output: $composeResult"
                }
            }
            
            # sudo로 실행 (대부분의 경우)
            if ($dockerStatus -eq "docker_sudo") {
                Write-Host "[DEBUG] Running docker-compose with sudo..."
                $composeCmd = "cd ~/worker && sudo $dockerComposeCmd up -d --remove-orphans"
                Write-Host "[DEBUG] Command: $composeCmd"
                
                # 실행 (타임아웃 없이 - 이미지 다운로드 시간 고려)
                $composeResult = wsl -d $DistroName -- bash -c "$composeCmd 2>&1"
                
                Write-Host "[DEBUG] Docker Compose output:"
                Write-Host "----------------------------------------"
                Write-Host $composeResult
                Write-Host "----------------------------------------"
                
            }
        }
        
        # 실행 후 컨테이너 상태 즉시 확인
        Write-Host "[DEBUG] Checking container status after docker-compose..."
        Start-Sleep -Seconds 2
        
        # 컨테이너 목록 확인
        $allContainers = wsl -d $DistroName -- docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.State}}" 2>&1
        Write-Host "[DEBUG] All containers:"
        Write-Host $allContainers
        
        # Docker Compose 실행 결과 확인
        if ($composeResult -match "Created|Started|Running" -or $composeResult -match "is up-to-date" -or $composeResult -match "Exit Code: 0") {
            Write-Host "[DEBUG] Container deployment appears successful based on output"
            
            # 컨테이너가 실제로 시작될 때까지 대기
            Write-Host "[DEBUG] Waiting for container to be ready..."
            Start-Sleep -Seconds 5
            
            # Docker ps 명령
            if ($DistroName -eq "docker-desktop") {
                # Docker Desktop 사용
                $containerStatus = docker ps --filter "name=node-server-""" + node_id + """" --format "table {{.Names}}\t{{.Status}}" 2>$null
            } elseif ($dockerStatus -match "docker_ok") {
                $containerStatus = wsl -d $DistroName -- docker ps --filter "name=node-server-""" + node_id + """" --format "table {{.Names}}\t{{.Status}}" 2>$null
            } else {
                $containerStatus = wsl -d $DistroName -- sudo docker ps --filter "name=node-server-""" + node_id + """" --format "table {{.Names}}\t{{.Status}}" 2>$null
            }
            
            if ($containerStatus -match "Up") {
                Write-Host "[DEBUG] Container is running"
                return @{
                    Success = $true
                    ContainerName = "node-server-""" + node_id + """"
                    Status = "Running"
                    Message = "컨테이너가 성공적으로 배포되었습니다."
                }
            } else {
                Write-Host "[WARNING] Container started but not running"
                return @{
                    Success = $true
                    ContainerName = "node-server-""" + node_id + """"
                    Status = "Started"
                    Message = "컨테이너가 시작되었지만 상태 확인이 필요합니다."
                }
            }
        } else {
            Write-Host "[ERROR] Docker Compose failed: $composeResult"
            
            # 에러 로그 확인
            if ($DistroName -eq "docker-desktop") {
                $composeDir = "$env:USERPROFILE\\.docker\\worker"
                $errorLog = docker compose -f "$composeDir\\docker-compose.yml" logs --tail=50 2>&1
            } elseif ($dockerStatus -match "docker_ok") {
                $errorLog = wsl -d $DistroName -- bash -c "cd ~/worker && docker-compose logs --tail=50" 2>&1
            } else {
                $errorLog = wsl -d $DistroName -- bash -c "cd ~/worker && sudo docker-compose logs --tail=50" 2>&1
            }
            Write-Host "[ERROR] Container logs: $errorLog"
            
            return @{
                Success = $false
                ContainerName = "node-server-""" + node_id + """"
                Status = "Failed"
                Message = "컨테이너 배포 실패: $composeResult"
            }
        }
        
    } catch {
        Write-Host "[ERROR] Deploy-Container failed: $_"
        return @{
            Success = $false
            ContainerName = "node-server-""" + node_id + """"
            Status = "Error"
            Message = "컨테이너 배포 중 오류 발생: $_"
        }
    }
}

# 컨테이너 상태 확인 함수
function Check-ContainerStatus {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DistroName,
        [Parameter(Mandatory=$false)]
        [string]$ContainerName = "node-server-""" + node_id + """"
    )
    
    try {
        Write-Host "[DEBUG] Checking container status: $ContainerName"
        
        # 컨테이너 상태 확인
        $containerInfo = wsl -d $DistroName -- sudo docker inspect $ContainerName 2>$null | ConvertFrom-Json
        
        if ($containerInfo) {
            $state = $containerInfo[0].State
            $running = $state.Running
            $status = $state.Status
            $startedAt = $state.StartedAt
            
            Write-Host "[DEBUG] Container state: Running=$running, Status=$status"
            
            if ($running) {
                # 컨테이너 로그 마지막 몇 줄 확인
                $logs = wsl -d $DistroName -- sudo docker logs --tail=10 $ContainerName 2>&1
                
                return @{
                    Success = $true
                    Running = $true
                    Status = $status
                    StartedAt = $startedAt
                    Logs = $logs
                    Message = "컨테이너가 정상적으로 실행 중입니다."
                }
            } else {
                return @{
                    Success = $true
                    Running = $false
                    Status = $status
                    StartedAt = $null
                    Logs = $null
                    Message = "컨테이너가 중지된 상태입니다."
                }
            }
        } else {
            Write-Host "[WARNING] Container not found: $ContainerName"
            return @{
                Success = $false
                Running = $false
                Status = "NotFound"
                StartedAt = $null
                Logs = $null
                Message = "컨테이너를 찾을 수 없습니다."
            }
        }
        
    } catch {
        Write-Host "[ERROR] Check-ContainerStatus failed: $_"
        return @{
            Success = $false
            Running = $false
            Status = "Error"
            StartedAt = $null
            Logs = $null
            Message = "컨테이너 상태 확인 중 오류 발생: $_"
        }
    }
}
"""
    
    return result